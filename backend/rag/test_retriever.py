from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.retriever import retrieve


def main() -> None:
    results = retrieve("what is a community", "sst", 6, top_k=3)
    for idx, item in enumerate(results, start=1):
        print(
            f"{idx}. chapter={item['chapter_num']} | "
            f"title={item['chapter_title']} | "
            f"score={item['score']:.4f}"
        )
        print(item["text"])
        print("-" * 80)


if __name__ == "__main__":
    main()
