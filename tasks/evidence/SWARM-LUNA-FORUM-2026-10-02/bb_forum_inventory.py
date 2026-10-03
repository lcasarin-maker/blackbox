"""Inventory public topics in NVIDIA's DGX Spark forum category."""

import argparse
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BASE = "https://forums.developer.nvidia.com"
START_URL = "/c/accelerated-computing/dgx-spark-gb10/dgx-spark-gb10/721.json"


def inventory(root: Path = ROOT, *, opener: Any = urllib.request.urlopen,
              sleep: Any = time.sleep) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    url: str | None = START_URL
    items: dict[str, dict[str, Any]] = {}
    pages: list[dict[str, Any]] = []
    while url:
        request = urllib.request.Request(
            BASE + url, headers={"User-Agent": "Blackbox research; public read-only"}
        )
        try:
            with opener(request, timeout=40) as response:
                data = json.load(response)
        except Exception as exc:
            (root / "inventory-error.json").write_text(
                json.dumps({"url": url, "error": str(exc)}), encoding="utf-8"
            )
            raise
        (root / f"category-{len(pages):03}.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        topics = data["topic_list"]["topics"]
        new = 0
        for topic in topics:
            tid = str(topic["id"])
            if tid not in items:
                new += 1
            items[tid] = {
                "id": tid,
                "title": topic["title"],
                "url": f"{BASE}/t/{topic['slug']}/{tid}",
                "posts_count": topic["posts_count"],
                "category_id": topic.get("category_id"),
            }
        pages.append({"url": url, "topics": len(topics), "new": new})
        (root / "items.json").write_text(
            json.dumps(list(items.values()), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        next_url = data["topic_list"].get("more_topics_url")
        if next_url and new == 0:
            raise RuntimeError("Pagination repeated without new topics")
        if next_url:
            path, _, query = next_url.partition("?")
            url = path + ("" if path.endswith(".json") else ".json") + ("?" + query if query else "")
        else:
            url = None
        print(f"page={len(pages)} topics={len(items)} next={bool(url)}", flush=True)
        if url:
            sleep(0.4)
    result = {"category_id": 721, "pages": pages, "topics": len(items), "pagination_exhausted": True}
    (root / "inventory.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    inventory(args.output)


if __name__ == "__main__":
    main()
