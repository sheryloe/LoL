from __future__ import annotations

import json
import re
import time
from typing import Any

import requests

from app.config import (
    BAD_REQUEST_RETRY_COUNT,
    BAD_REQUEST_RETRY_DELAY_SECONDS,
    NOTION_API_BASE_URL,
    NOTION_API_VERSION,
    NOTION_TIMEOUT_SECONDS,
)


NOTION_PAGE_ID_PATTERN = re.compile(r"^[0-9a-fA-F-]{32,36}$")


def _clean_text(value: str, max_len: int = 1800) -> str:
    cleaned = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = "".join(ch for ch in cleaned if ch == "\n" or (31 < ord(ch) < 55296) or ord(ch) > 57343)
    cleaned = cleaned.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def _mk_rich(text: str) -> list[dict]:
    return [{"type": "text", "text": {"content": text}}]


def _markdown_to_blocks(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("### "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": _mk_rich(_clean_text(line[4:], max_len=120))},
                }
            )
            continue
        if line.startswith("## "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": _mk_rich(_clean_text(line[3:], max_len=120))},
                }
            )
            continue
        if line.startswith("# "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": _mk_rich(_clean_text(line[2:], max_len=120))},
                }
            )
            continue
        if line.startswith("- "):
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": _mk_rich(_clean_text(line[2:]))},
                }
            )
            continue
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _mk_rich(_clean_text(line))},
            }
        )
    return blocks[:100]


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))
    title_obj = normalized.get("properties", {}).get("title", {}).get("title", [])
    if title_obj and isinstance(title_obj, list):
        first = title_obj[0]
        if isinstance(first, dict):
            text_obj = first.get("text")
            if isinstance(text_obj, dict):
                text_obj["content"] = _clean_text(str(text_obj.get("content", "")), max_len=120)

    for block in normalized.get("children", []):
        block_type = block.get("type")
        if not block_type:
            continue
        body = block.get(block_type, {})
        rich = body.get("rich_text")
        if not isinstance(rich, list):
            continue
        for item in rich:
            text_obj = item.get("text")
            if isinstance(text_obj, dict):
                text_obj["content"] = _clean_text(str(text_obj.get("content", "")))
    return normalized


def _retry_delay_seconds(base_delay: float, attempt: int) -> float:
    safe_base = max(0.1, float(base_delay))
    return safe_base * max(1, int(attempt))


class NotionService:
    def build_step_markdown(
        self,
        *,
        project_id: str,
        step_title: str,
        one_line_summary: str,
        background: str,
        core_concepts: str,
        implementation_details: str,
        test_notes: str,
        troubleshooting: str,
        next_steps: str,
    ) -> str:
        return (
            f"# 한 줄 요약\n{one_line_summary.strip()}\n\n"
            f"# 문제 배경\n{background.strip()}\n\n"
            f"# 핵심 개념 정리\n{core_concepts.strip()}\n\n"
            f"# 구현 상세\n- project_id: `{project_id}`\n- step: `{step_title.strip()}`\n\n{implementation_details.strip()}\n\n"
            f"# 검증\n{test_notes.strip()}\n\n"
            f"# 트러블슈팅\n{troubleshooting.strip()}\n\n"
            f"# 다음 단계\n{next_steps.strip()}\n"
        )

    def publish_markdown(
        self,
        *,
        notion_token: str,
        parent_page_id: str,
        page_title: str,
        markdown: str,
        retry_count: int = BAD_REQUEST_RETRY_COUNT,
        retry_delay_seconds: float = BAD_REQUEST_RETRY_DELAY_SECONDS,
    ) -> dict[str, Any]:
        token = notion_token.strip()
        parent = parent_page_id.strip()
        title = page_title.strip()
        if not token:
            raise ValueError("notion token is required")
        if not NOTION_PAGE_ID_PATTERN.fullmatch(parent):
            raise ValueError("parent_page_id must be a Notion page id (32-36 hex chars)")
        if not title:
            raise ValueError("page title is required")

        blocks = _markdown_to_blocks(markdown)
        if not blocks:
            raise ValueError("markdown content is empty")

        payload: dict[str, Any] = {
            "parent": {"page_id": parent},
            "properties": {"title": {"title": _mk_rich(_clean_text(title, max_len=120))}},
            "children": blocks,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }
        url = f"{NOTION_API_BASE_URL}/pages"
        max_attempts = max(0, retry_count) + 1
        retry_logs: list[str] = []

        for attempt in range(1, max_attempts + 1):
            response = requests.post(url, headers=headers, json=payload, timeout=NOTION_TIMEOUT_SECONDS)
            if response.ok:
                body = response.json()
                return {
                    "success": True,
                    "page_id": body.get("id"),
                    "page_url": body.get("url"),
                    "attempts": attempt,
                    "bad_request_retries": len(retry_logs),
                    "retry_logs": retry_logs,
                }

            if response.status_code == 400 and attempt < max_attempts:
                payload = _normalize_payload(payload)
                wait_sec = _retry_delay_seconds(retry_delay_seconds, attempt)
                retry_logs.append(
                    f"attempt {attempt}: notion returned 400 bad request -> retry after {wait_sec:.1f}s"
                )
                time.sleep(wait_sec)
                continue

            body_excerpt = response.text[:1000]
            raise RuntimeError(
                f"notion publish failed: status={response.status_code}, attempt={attempt}, body={body_excerpt}"
            )

        raise RuntimeError("notion publish failed after retries")


notion_service = NotionService()
