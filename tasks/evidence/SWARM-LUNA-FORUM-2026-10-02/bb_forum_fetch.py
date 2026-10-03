"""Fetch public NVIDIA forum topics listed in a JSON file."""

import argparse
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
USER_AGENT = "Blackbox public forum research"


def get(url: str, *, opener: Any = urllib.request.urlopen, sleep: Any = time.sleep) -> dict[str, Any]:
    """Fetch JSON with five bounded attempts and polite retry pacing."""
    for attempt in range(5):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with opener(request, timeout=45) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError("response JSON must be an object")
            return payload
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            if attempt == 4:
                raise
            delay = 3 * (attempt + 1)
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                delay = max(30, delay)
                try:
                    delay = max(delay, float(exc.headers.get("Retry-After", "30")))
                except (TypeError, ValueError):
                    pass
            sleep(min(delay, 60))
    raise RuntimeError("unreachable retry state")


def fetch(item: dict[str, Any], root: Path = ROOT, *, getter: Any = get,
          sleep: Any = time.sleep) -> dict[str, Any]:
    tid = item["id"]
    dest = root / "threads"
    dest.mkdir(parents=True, exist_ok=True)
    receipt = dest / f"{tid}.fetch.json"
    if receipt.exists():
        previous = json.loads(receipt.read_text(encoding="utf-8"))
        if previous.get("status") == "fetched":
            result = {**previous, "cache_reused": True}
            print(json.dumps(result), flush=True)
            return result
    try:
        data = getter(item["url"] + ".json")
        stream = data["post_stream"]
        posts = stream["posts"]
        seen = {post["id"] for post in posts}
        missing = [post_id for post_id in stream["stream"] if post_id not in seen]
        for offset in range(0, len(missing), 20):
            query = urllib.parse.urlencode(
                [("post_ids[]", post_id) for post_id in missing[offset:offset + 20]]
            )
            more = getter(f"https://forums.developer.nvidia.com/t/{tid}/posts.json?{query}")
            posts.extend(more["post_stream"]["posts"])
            sleep(0.3)
        unique = {post["id"]: post for post in posts}
        if set(stream["stream"]) - set(unique):
            raise RuntimeError("missing post ids after fetch")
        data["post_stream"]["posts"] = sorted(unique.values(), key=lambda post: post["post_number"])
        (dest / f"{tid}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        texts = [item["title"], item["url"]]
        for post in data["post_stream"]["posts"]:
            cooked = post.get("cooked", "")
            plain = html.unescape(re.sub("<[^>]+>", " ", cooked))
            texts.append(
                f"\nPOST {post['post_number']} | {post['username']} | {post['created_at']} | "
                f"{item['url']}/{post['post_number']}\n{plain}"
            )
        (dest / f"{tid}.txt").write_text("\n".join(texts), encoding="utf-8")
        result = {
            "id": tid,
            "status": "fetched",
            "posts_expected": len(stream["stream"]),
            "posts_fetched": len(unique),
            "attachments_status": "links preserved; binary attachments not inspected",
        }
    except Exception as exc:
        result = {"id": tid, "status": "could_not_run", "error": str(exc)}
    receipt.write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps(result), flush=True)
    sleep(0.75)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("items", nargs="?", type=Path, default=ROOT / "items.json")
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    items = json.loads(args.items.read_text(encoding="utf-8"))
    for item in items:
        fetch(item, args.output)


if __name__ == "__main__":
    main()
