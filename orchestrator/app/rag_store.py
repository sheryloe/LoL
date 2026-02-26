from __future__ import annotations

import asyncio
import json
import math
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .security import resolve_under_root

RAG_INDEX_SCHEMA_VERSION = 1
TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "")]


def compact_excerpt(text: str, max_chars: int = 260) -> str:
    clean = " ".join((text or "").replace("\r", " ").replace("\n", " ").split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + "..."


class ProjectRagStore:
    def __init__(
        self,
        projects_dir: Path,
        root_dir: Path,
        *,
        chunk_size: int = 900,
        chunk_overlap: int = 120,
    ) -> None:
        self.projects_dir = projects_dir
        self.root_dir = root_dir
        self.chunk_size = max(200, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, project_id: str) -> asyncio.Lock:
        lock = self._locks.get(project_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[project_id] = lock
        return lock

    def _project_dir(self, project_id: str) -> Path:
        safe = project_id.replace("/", "_").replace("\\", "_")
        return self.projects_dir / safe

    def _index_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "rag_index.json"

    def _default_index(self) -> dict[str, Any]:
        return {
            "schema_version": RAG_INDEX_SCHEMA_VERSION,
            "updated_at": utc_now(),
            "documents": [],
            "chunks": [],
        }

    def _load_index(self, project_id: str) -> dict[str, Any]:
        path = self._index_path(project_id)
        if not path.exists():
            return self._default_index()
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return self._default_index()
        return {
            "schema_version": RAG_INDEX_SCHEMA_VERSION,
            "updated_at": loaded.get("updated_at", utc_now()),
            "documents": list(loaded.get("documents") or []),
            "chunks": list(loaded.get("chunks") or []),
        }

    def _save_index(self, project_id: str, index_data: dict[str, Any]) -> None:
        path = self._index_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": RAG_INDEX_SCHEMA_VERSION,
            "updated_at": utc_now(),
            "documents": index_data.get("documents", []),
            "chunks": index_data.get("chunks", []),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _chunk_text(self, text: str) -> list[tuple[int, int, str]]:
        cleaned = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not cleaned:
            return []
        if len(cleaned) <= self.chunk_size:
            return [(0, len(cleaned), cleaned)]

        chunks: list[tuple[int, int, str]] = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        for start in range(0, len(cleaned), step):
            end = min(len(cleaned), start + self.chunk_size)
            piece = cleaned[start:end].strip()
            if not piece:
                continue
            chunks.append((start, end, piece))
            if end >= len(cleaned):
                break
        return chunks

    async def list_documents(self, project_id: str) -> list[dict[str, Any]]:
        lock = self._lock_for(project_id)
        async with lock:
            index_data = self._load_index(project_id)
        docs = list(index_data.get("documents", []))
        docs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return docs

    async def ingest_text(
        self,
        project_id: str,
        *,
        title: str | None,
        content: str,
        tags: list[str] | None = None,
        source_path: str | None = None,
    ) -> dict[str, Any]:
        raw_content = (content or "").strip()
        if not raw_content:
            raise ValueError("content must not be empty")

        chunk_parts = self._chunk_text(raw_content)
        if not chunk_parts:
            raise ValueError("failed to chunk document")

        now = utc_now()
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        normalized_tags = tags or []
        normalized_title = (title or "").strip() or (source_path or f"document-{document_id}")

        document = {
            "document_id": document_id,
            "title": normalized_title[:180],
            "source_type": "file" if source_path else "text",
            "source_path": source_path,
            "tags": normalized_tags[:12],
            "created_at": now,
            "updated_at": now,
            "char_count": len(raw_content),
            "chunk_count": len(chunk_parts),
        }

        chunk_rows: list[dict[str, Any]] = []
        for index, (start, end, chunk_text) in enumerate(chunk_parts):
            tokens = tokenize(chunk_text)
            term_freq: dict[str, int] = {}
            for token in tokens:
                term_freq[token] = term_freq.get(token, 0) + 1
            chunk_rows.append(
                {
                    "chunk_id": f"c{index + 1}",
                    "document_id": document_id,
                    "title": document["title"],
                    "source_path": source_path,
                    "tags": normalized_tags[:12],
                    "start": start,
                    "end": end,
                    "text": chunk_text,
                    "tokens": len(tokens),
                    "term_freq": term_freq,
                }
            )

        lock = self._lock_for(project_id)
        async with lock:
            index_data = self._load_index(project_id)
            index_data["documents"].append(document)
            index_data["chunks"].extend(chunk_rows)
            self._save_index(project_id, index_data)
        return document

    async def ingest_file(
        self,
        project_id: str,
        *,
        source_path: str,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        rel_path = (source_path or "").strip()
        if not rel_path:
            raise ValueError("source_path must not be empty")
        target = resolve_under_root(self.root_dir, rel_path)
        if not target.exists():
            raise FileNotFoundError(f"source file not found: {rel_path}")
        if not target.is_file():
            raise ValueError(f"source path is not a file: {rel_path}")
        if target.stat().st_size > 1_500_000:
            raise ValueError("source file too large (>1.5MB)")
        content = target.read_text(encoding="utf-8", errors="replace")
        return await self.ingest_text(
            project_id,
            title=title or target.name,
            content=content,
            tags=tags or [],
            source_path=rel_path,
        )

    def _score_chunk(self, query_tokens: list[str], query_phrase: str, row: dict[str, Any]) -> float:
        term_freq = row.get("term_freq") or {}
        token_count = int(row.get("tokens") or 0)
        token_score = 0.0
        for token in query_tokens:
            count = int(term_freq.get(token) or 0)
            if count <= 0:
                continue
            token_score += min(3.0, 1.0 + (count - 1) * 0.35)
        if token_score <= 0:
            return 0.0

        text_lower = str(row.get("text") or "").lower()
        phrase_boost = 1.25 if query_phrase and len(query_phrase) >= 4 and query_phrase in text_lower else 0.0
        length_penalty = 1.0 + math.log(max(1, token_count), 8.0) * 0.15
        return round((token_score + phrase_boost) / length_penalty, 5)

    async def search(self, project_id: str, query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []
        query_tokens = tokenize(cleaned_query)
        if not query_tokens:
            return []

        lock = self._lock_for(project_id)
        async with lock:
            index_data = self._load_index(project_id)

        docs_by_id = {
            item.get("document_id"): item
            for item in index_data.get("documents", [])
            if isinstance(item, dict) and item.get("document_id")
        }

        rows: list[dict[str, Any]] = []
        for row in index_data.get("chunks", []):
            if not isinstance(row, dict):
                continue
            score = self._score_chunk(query_tokens, cleaned_query.lower(), row)
            if score <= 0:
                continue
            document = docs_by_id.get(row.get("document_id"), {})
            rows.append(
                {
                    "document_id": row.get("document_id"),
                    "chunk_id": row.get("chunk_id"),
                    "title": document.get("title") or row.get("title") or "untitled",
                    "source_path": document.get("source_path") or row.get("source_path"),
                    "tags": list(document.get("tags") or row.get("tags") or []),
                    "score": score,
                    "excerpt": compact_excerpt(str(row.get("text") or ""), 320),
                }
            )

        rows.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return rows[:top_k]

    async def build_context(
        self,
        project_id: str,
        query: str,
        *,
        top_k: int = 4,
        max_chars: int = 2400,
    ) -> dict[str, Any]:
        hits = await self.search(project_id, query, top_k=top_k)
        if not hits:
            return {"context": "", "hits": []}

        parts: list[str] = []
        remaining = max_chars
        used_hits: list[dict[str, Any]] = []
        for index, hit in enumerate(hits, start=1):
            source_label = hit.get("source_path") or "inline-text"
            block = (
                f"[{index}] {hit.get('title')} | source={source_label} | "
                f"score={hit.get('score')}\n{hit.get('excerpt')}"
            )
            if len(block) > remaining:
                if remaining < 100:
                    break
                block = block[: remaining - 3].rstrip() + "..."
            parts.append(block)
            used_hits.append(hit)
            remaining -= len(block) + 2
            if remaining <= 0:
                break

        return {"context": "\n\n".join(parts), "hits": used_hits}
