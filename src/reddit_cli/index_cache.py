"""Short-index cache for listing results."""

from __future__ import annotations

import json
import time
from typing import Any

from reddit_cli.constants import CONFIG_DIR, INDEX_CACHE_FILE


def save_index(items: list[dict[str, Any]]) -> None:
    """Save listing items to index cache for `reddit show <N>` access."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "saved_at": time.time(),
        "count": len(items),
        "items": items,
    }
    INDEX_CACHE_FILE.write_text(json.dumps(data, indent=2, default=str))


def get_item_by_index(index: int) -> dict[str, Any] | None:
    """Retrieve item by 1-based index from cache. Returns None if not found."""
    if index < 1:
        return None
    try:
        data = json.loads(INDEX_CACHE_FILE.read_text())
        items = data.get("items", [])
        if index > len(items):
            return None
        return items[index - 1]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def resolve_fullname_from_index(id_or_index: str) -> str:
    """Resolve an ID, fullname, or numeric index to a Reddit fullname.

    Handles: "t3_abc" -> "t3_abc", "abc" -> "t3_abc", "3" -> lookup from cache.
    Raises SystemExit(3) if numeric index not found in cache.
    """
    from reddit_cli.client import resolve_fullname

    fullname = resolve_fullname(id_or_index)
    if not fullname.isdigit():
        return fullname

    item = get_item_by_index(int(fullname))
    if not item:
        from reddit_cli.output import output_error
        output_error("not_found", f"No item at index {fullname}. Run a listing command first.")
        raise SystemExit(3)
    return item.get("name", f"t3_{item['id']}")
