from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests


NOTION_VERSION = "2022-06-28"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish a step markdown note to Notion with 400-retry.")
    parser.add_argument("--token", required=True, help="Notion integration token")
    parser.add_argument("--parent-page-id", required=True, help="Parent page id (UUID with/without dashes)")
    parser.add_argument("--title", required=True, help="Page title")
    parser.add_argument("--content-file", required=True, help="Markdown file path")
    parser.add_argument("--retry-count", type=int, default=2, help="Number of retries when 400 occurs")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="Base delay seconds")
    return parser.parse_args()


def _clean_text(value: str, max_len: int = 1800) -> str:
    cleaned = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = "".join(ch for ch in cleaned if ch == "\n" or (31 < ord(ch) < 55296) or ord(ch) > 57343)
    cleaned = cleaned.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def _mk_rich(text: str) -> list[dict]:
    return [{"type": "text", "text": {"content": text}}]


def markdown_to_blocks(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": _mk_rich(_clean_text(line[4:]))},
                }
            )
            continue
        if line.startswith("## "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": _mk_rich(_clean_text(line[3:]))},
                }
            )
            continue
        if line.startswith("# "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": _mk_rich(_clean_text(line[2:]))},
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


def normalize_payload(payload: dict) -> dict:
    """Strip risky content lengths for retry."""
    normalized = json.loads(json.dumps(payload))
    title = normalized["properties"]["title"]["title"][0]["text"]["content"]
    normalized["properties"]["title"]["title"][0]["text"]["content"] = _clean_text(title, max_len=120)

    for block in normalized.get("children", []):
        block_type = block.get("type")
        if not block_type:
            continue
        body = block.get(block_type)
        if not isinstance(body, dict):
            continue
        rich = body.get("rich_text")
        if not isinstance(rich, list):
            continue
        for chunk in rich:
            text_obj = chunk.get("text")
            if isinstance(text_obj, dict) and "content" in text_obj:
                text_obj["content"] = _clean_text(str(text_obj.get("content", "")))
    return normalized


def main() -> None:
    args = parse_args()
    markdown = Path(args.content_file).read_text(encoding="utf-8", errors="replace")
    blocks = markdown_to_blocks(markdown)
    if not blocks:
        raise SystemExit("no content blocks generated from markdown")

    payload = {
        "parent": {"page_id": args.parent_page_id},
        "properties": {"title": {"title": _mk_rich(_clean_text(args.title, max_len=120))}},
        "children": blocks,
    }

    headers = {
        "Authorization": f"Bearer {args.token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    url = "https://api.notion.com/v1/pages"
    attempts = args.retry_count + 1
    for attempt in range(1, attempts + 1):
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.ok:
            body = response.json()
            print(json.dumps({"status": "ok", "id": body.get("id"), "url": body.get("url")}, ensure_ascii=False))
            return

        if response.status_code == 400 and attempt < attempts:
            payload = normalize_payload(payload)
            wait_sec = max(0.1, args.retry_delay * attempt)
            print(
                json.dumps(
                    {
                        "status": "retry",
                        "attempt": attempt,
                        "reason": "400 Bad Request",
                        "wait_sec": wait_sec,
                        "response": response.text[:500],
                    },
                    ensure_ascii=False,
                )
            )
            time.sleep(wait_sec)
            continue

        print(
            json.dumps(
                {
                    "status": "failed",
                    "http_status": response.status_code,
                    "response": response.text[:2000],
                },
                ensure_ascii=False,
            )
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
