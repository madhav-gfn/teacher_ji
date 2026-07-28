"""
Phase 4B: offline RAG retrieval-relevance eval.

Runs `rag.retriever.retrieve` (the same function search_ncert/tools.py calls)
against a small hand-labeled question set (rag_eval_set.json, 15 questions
across the three ingested class6 indexes) and scores each result on keyword
recall - the fraction of hand-picked, topic-grounded terms that show up
somewhere in the top-k retrieved chunks.

Deliberately does NOT filter by chapter: search_ncert already falls back to an
unfiltered subject/grade search whenever a chapter-scoped one comes up empty
(see agents/tools.py:search_ncert), and the ingested chapter_title metadata is
inconsistent (science's is entirely un-chunked into per-chapter numbers - see
the README note below) - scoring the unfiltered path is what the system
actually falls back to, so it's the fairer thing to measure.

Usage:
    python -m eval.rag_eval
    python -m eval.rag_eval --top-k 8 --threshold 0.6
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.retriever import NCERTIndexNotFound, retrieve  # noqa: E402

EVAL_SET_PATH = Path(__file__).resolve().parent / "rag_eval_set.json"


def _keyword_recall(chunks: list[dict], expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0
    haystack = " ".join(str(c.get("text", "")) for c in chunks).lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in haystack)
    return hits / len(expected_keywords)


def run_eval(top_k: int = 5, pass_threshold: float = 0.5) -> dict:
    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    results = []

    for item in eval_set:
        try:
            chunks = retrieve(item["query"], item["subject"], item["grade"], chapter=None, top_k=top_k)
        except NCERTIndexNotFound as exc:
            results.append({**item, "error": str(exc), "keyword_recall": 0.0, "passed": False})
            continue

        recall = _keyword_recall(chunks, item["expected_keywords"])
        results.append(
            {
                "id": item["id"],
                "subject": item["subject"],
                "query": item["query"],
                "keyword_recall": round(recall, 2),
                "passed": recall >= pass_threshold,
                "num_chunks_retrieved": len(chunks),
                "top_chunk_preview": (chunks[0]["text"][:120] if chunks else None),
            }
        )

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    avg_recall = sum(r["keyword_recall"] for r in results) / total if total else 0.0

    by_subject: dict[str, list[dict]] = {}
    for r in results:
        by_subject.setdefault(r["subject"], []).append(r)

    subject_summary = {
        subject: {
            "n": len(items),
            "passed": sum(1 for i in items if i["passed"]),
            "avg_recall": round(sum(i["keyword_recall"] for i in items) / len(items), 2),
        }
        for subject, items in by_subject.items()
    }

    return {
        "top_k": top_k,
        "pass_threshold": pass_threshold,
        "total": total,
        "passed": passed,
        "hit_rate": round(passed / total, 2) if total else 0.0,
        "avg_keyword_recall": round(avg_recall, 2),
        "by_subject": subject_summary,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG retrieval-relevance eval")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.5, help="Min keyword recall to count as a pass")
    args = parser.parse_args()

    report = run_eval(top_k=args.top_k, pass_threshold=args.threshold)

    print(f"\nRAG retrieval eval - top_k={report['top_k']}, pass_threshold={report['pass_threshold']}")
    print(f"Overall: {report['passed']}/{report['total']} passed (hit rate {report['hit_rate']:.0%}), "
          f"avg keyword recall {report['avg_keyword_recall']:.0%}\n")
    for subject, summary in report["by_subject"].items():
        print(f"  {subject:8s} {summary['passed']}/{summary['n']} passed, avg recall {summary['avg_recall']:.0%}")

    print("\nFailing items:")
    failures = [r for r in report["results"] if not r["passed"]]
    if not failures:
        print("  (none)")
    for r in failures:
        print(f"  [{r['id']}] recall={r['keyword_recall']:.0%} query={r['query']!r}")
        if r.get("error"):
            print(f"    error: {r['error']}")


if __name__ == "__main__":
    main()
