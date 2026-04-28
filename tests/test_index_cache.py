"""Tests for index cache: save, retrieve, round-trip."""

import json
from unittest.mock import patch

import pytest


class TestIndexCache:
    def test_save_and_retrieve(self, tmp_path):
        from reddit_cli.index_cache import get_item_by_index, save_index

        cache_file = tmp_path / "index_cache.json"
        items = [
            {"id": "abc", "name": "t3_abc", "title": "Post A", "permalink": "/r/x/abc"},
            {"id": "def", "name": "t3_def", "title": "Post B", "permalink": "/r/x/def"},
        ]
        with patch("reddit_cli.index_cache.INDEX_CACHE_FILE", cache_file):
            save_index(items)
            item = get_item_by_index(1)
            assert item is not None
            assert item["id"] == "abc"

            item2 = get_item_by_index(2)
            assert item2 is not None
            assert item2["id"] == "def"

    def test_index_out_of_range(self, tmp_path):
        from reddit_cli.index_cache import get_item_by_index, save_index

        cache_file = tmp_path / "index_cache.json"
        items = [{"id": "abc", "name": "t3_abc", "title": "Post A"}]
        with patch("reddit_cli.index_cache.INDEX_CACHE_FILE", cache_file):
            save_index(items)
            assert get_item_by_index(0) is None
            assert get_item_by_index(99) is None

    def test_empty_cache(self, tmp_path):
        from reddit_cli.index_cache import get_item_by_index

        cache_file = tmp_path / "nonexistent.json"
        with patch("reddit_cli.index_cache.INDEX_CACHE_FILE", cache_file):
            assert get_item_by_index(1) is None

    def test_save_creates_file(self, tmp_path):
        from reddit_cli.index_cache import save_index

        cache_file = tmp_path / "cache.json"
        with patch("reddit_cli.index_cache.INDEX_CACHE_FILE", cache_file), \
             patch("reddit_cli.index_cache.CONFIG_DIR", tmp_path):
            save_index([{"id": "x", "name": "t3_x", "title": "T"}])
            assert cache_file.exists()
            data = json.loads(cache_file.read_text())
            assert data["count"] == 1
            assert len(data["items"]) == 1

    def test_round_trip_preserves_fields(self, tmp_path):
        from reddit_cli.index_cache import get_item_by_index, save_index

        cache_file = tmp_path / "cache.json"
        items = [{
            "id": "abc", "name": "t3_abc", "title": "Test",
            "subreddit": "python", "author": "user1",
            "score": 42, "num_comments": 5,
            "permalink": "/r/python/abc", "url": "https://reddit.com/r/python/abc",
        }]
        with patch("reddit_cli.index_cache.INDEX_CACHE_FILE", cache_file), \
             patch("reddit_cli.index_cache.CONFIG_DIR", tmp_path):
            save_index(items)
            item = get_item_by_index(1)
            assert item["subreddit"] == "python"
            assert item["score"] == 42


class TestResolveFullnameFromIndex:
    def test_fullname_passthrough(self):
        from reddit_cli.index_cache import resolve_fullname_from_index
        assert resolve_fullname_from_index("t3_abc") == "t3_abc"
        assert resolve_fullname_from_index("t1_xyz") == "t1_xyz"

    def test_bare_id_gets_t3_prefix(self):
        from reddit_cli.index_cache import resolve_fullname_from_index
        assert resolve_fullname_from_index("abc123") == "t3_abc123"

    def test_numeric_resolves_from_cache(self, tmp_path):
        from reddit_cli.index_cache import resolve_fullname_from_index, save_index

        cache_file = tmp_path / "cache.json"
        with patch("reddit_cli.index_cache.INDEX_CACHE_FILE", cache_file), \
             patch("reddit_cli.index_cache.CONFIG_DIR", tmp_path):
            save_index([{"id": "abc", "name": "t3_abc", "title": "T"}])
            assert resolve_fullname_from_index("1") == "t3_abc"

    def test_numeric_cache_miss_exits(self, tmp_path):
        from reddit_cli.index_cache import resolve_fullname_from_index

        cache_file = tmp_path / "nonexistent.json"
        with patch("reddit_cli.index_cache.INDEX_CACHE_FILE", cache_file):
            with pytest.raises(SystemExit) as exc_info:
                resolve_fullname_from_index("99")
            assert exc_info.value.code == 3

    def test_uses_name_field_from_cache(self, tmp_path):
        from reddit_cli.index_cache import resolve_fullname_from_index, save_index

        cache_file = tmp_path / "cache.json"
        with patch("reddit_cli.index_cache.INDEX_CACHE_FILE", cache_file), \
             patch("reddit_cli.index_cache.CONFIG_DIR", tmp_path):
            save_index([{"id": "xyz", "name": "t1_xyz", "title": "Comment"}])
            assert resolve_fullname_from_index("1") == "t1_xyz"

    def test_falls_back_to_t3_id(self, tmp_path):
        from reddit_cli.index_cache import resolve_fullname_from_index, save_index

        cache_file = tmp_path / "cache.json"
        with patch("reddit_cli.index_cache.INDEX_CACHE_FILE", cache_file), \
             patch("reddit_cli.index_cache.CONFIG_DIR", tmp_path):
            save_index([{"id": "abc", "title": "T"}])  # no "name" field
            assert resolve_fullname_from_index("1") == "t3_abc"
