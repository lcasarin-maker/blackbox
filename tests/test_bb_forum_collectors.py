"""Offline behavior checks for the preserved forum research collectors."""

import importlib.util
import io
import json
from email.message import Message
import urllib.error
from pathlib import Path

import pytest

BASE = Path(__file__).parents[1] / "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, BASE / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_fetch_valid_incomplete_error_retry_timeout_and_io(tmp_path):
    fetcher = _load("bb_forum_fetch")
    waits = []
    tries = []

    def timeout(_request, timeout):
        tries.append(timeout)
        raise TimeoutError("offline timeout")

    with pytest.raises(TimeoutError):
        fetcher.get("https://fixture.invalid", opener=timeout, sleep=waits.append)
    assert tries == [45] * 5
    assert waits == [3, 6, 9, 12]

    malformed_calls = []
    malformed_waits = []
    def malformed(_request, timeout):
        malformed_calls.append(timeout)
        return Response(b"[")

    with pytest.raises(json.JSONDecodeError):
        fetcher.get("https://fixture.invalid", opener=malformed, sleep=malformed_waits.append)
    assert malformed_calls == [45] * 5
    assert malformed_waits == [3, 6, 9, 12]

    rate_waits = []
    def rate_limit(_request, timeout):
        headers = Message()
        headers["Retry-After"] = "35"
        raise urllib.error.HTTPError("url", 429, "rate", headers, None)

    with pytest.raises(urllib.error.HTTPError):
        fetcher.get("https://fixture.invalid", opener=rate_limit, sleep=rate_waits.append)
    assert rate_waits == [35, 35, 35, 35]

    def fail_once(_request, timeout):
        if len(tries) < 6:
            tries.append(timeout)
            raise urllib.error.URLError("fixture failure")
        return Response(b'{"ok": true}')

    assert fetcher.get("https://fixture.invalid", opener=fail_once, sleep=lambda _: None) == {"ok": True}

    item = {"id": 77, "title": "Título", "url": "https://fixture.invalid/t/77"}
    payload = {"post_stream": {"stream": [1, 2], "posts": [{
        "id": 1, "post_number": 1, "username": "fixture", "created_at": "now", "cooked": "<p>á</p>"
    }]}}
    more = {"post_stream": {"posts": [{
        "id": 2, "post_number": 2, "username": "fixture", "created_at": "later", "cooked": "<p>ok</p>"
    }]}}
    fetch_waits = []
    responses = iter([payload, more])
    result = fetcher.fetch(item, tmp_path, getter=lambda _url: next(responses), sleep=fetch_waits.append)
    assert result["status"] == "fetched"
    assert fetch_waits == [0.3, 0.75]
    assert (tmp_path / "threads/77.json").exists()
    assert "á" in (tmp_path / "threads/77.txt").read_text(encoding="utf-8")
    assert fetcher.fetch({**item, "id": 78}, tmp_path, getter=lambda _: {"post_stream": {"stream": [2], "posts": []}}, sleep=lambda _: None)["status"] == "could_not_run"
    assert not (tmp_path / "unrelated" / "threads").exists()


def test_inventory_pages_deduplicates_and_rejects_repeated_page(tmp_path):
    inventory = _load("bb_forum_inventory")
    topic = {"id": 7, "title": "Spark", "slug": "spark", "posts_count": 1}
    pages = [
        {"topic_list": {"topics": [topic], "more_topics_url": "/next"}},
        {"topic_list": {"topics": [topic, {**topic, "id": 8}], "more_topics_url": None}},
    ]
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        return Response(json.dumps(pages.pop(0)).encode())

    result = inventory.inventory(tmp_path, opener=opener, sleep=lambda _: None)
    assert result["topics"] == 2
    assert len(calls) == 2 and calls[1][0].endswith("/next.json")
    assert json.loads((tmp_path / "items.json").read_text(encoding="utf-8"))[0]["id"] == "7"

    repeated = {"topic_list": {"topics": [topic], "more_topics_url": "/again"}}
    with pytest.raises(RuntimeError, match="repeated"):
        inventory.inventory(tmp_path / "negative", opener=lambda *_args, **_kwargs: Response(json.dumps(repeated).encode()), sleep=lambda _: None)


def test_collectors_import_without_filesystem_or_network(monkeypatch, tmp_path):
    actions = []

    def observe(action, result):
        def record(*_args, **_kwargs):
            actions.append(action)
            return result

        return record

    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "mkdir", observe("mkdir", None))
        patcher.setattr(Path, "write_text", observe("write_text", 0))
        patcher.setattr(Path, "read_text", observe("read_text", "{}"))
        patcher.setattr("urllib.request.urlopen", observe("urlopen", Response(b"{}")))
        fetcher = _load("bb_forum_fetch")
        inventory = _load("bb_forum_inventory")

    assert actions == []
    assert fetcher.ROOT.resolve() == BASE.resolve()
    assert inventory.ROOT.resolve() == BASE.resolve()
    assert callable(fetcher.get) and callable(fetcher.fetch) and callable(fetcher.main)
    assert callable(inventory.inventory) and callable(inventory.main)

    item = {"id": 9, "title": "fixture", "url": "https://fixture.invalid/t/9"}
    payload = {"post_stream": {"stream": [1], "posts": [{
        "id": 1, "post_number": 1, "username": "fixture", "created_at": "now", "cooked": "valid"
    }]}}
    result = fetcher.fetch(item, tmp_path / "portable-output", getter=lambda _: payload, sleep=lambda _: None)
    assert result["status"] == "fetched"
    assert (tmp_path / "portable-output/threads/9.json").is_file()
    assert (tmp_path / "portable-output/threads/9.txt").is_file()
