from __future__ import annotations

import json
import os
from pathlib import Path

# Restrict threading at the OS level before importing faiss.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import faiss

from rag.embeddings import embed_texts

INDEX_DIR = Path(__file__).resolve().parent / "index"
_INDEX_CACHE: dict[tuple[str, int], faiss.Index] = {}
_META_CACHE: dict[tuple[str, int], list[dict]] = {}


class NCERTIndexNotFound(FileNotFoundError):
    """Raised when the FAISS index for a subject/grade pair is missing."""


def _normalize_subject(subject: str) -> str:
    return subject.strip().lower()


def _cache_key(subject: str, grade: int) -> tuple[str, int]:
    return (_normalize_subject(subject), int(grade))


def _paths_for(subject: str, grade: int) -> tuple[Path, Path]:
    base_name = f"{_normalize_subject(subject)}_class{grade}"
    return (
        INDEX_DIR / f"{base_name}.faiss",
        INDEX_DIR / f"{base_name}_meta.json",
    )


def _load_index(subject: str, grade: int) -> tuple[faiss.Index, list[dict]]:
    key = _cache_key(subject, grade)
    if key in _INDEX_CACHE and key in _META_CACHE:
        return _INDEX_CACHE[key], _META_CACHE[key]

    index_path, meta_path = _paths_for(subject, grade)
    if not index_path.exists() or not meta_path.exists():
        raise NCERTIndexNotFound(
            f"Missing NCERT index for subject='{_normalize_subject(subject)}', grade={grade}. "
            f"Run `python rag/ingest.py --subject {_normalize_subject(subject)} --grade {grade} "
            f"--pdf_dir data/ncert/class{grade}/{_normalize_subject(subject)}/` first."
        )

    index = faiss.read_index(str(index_path))
    with meta_path.open("r", encoding="utf-8-sig") as meta_file:
        metadata = json.load(meta_file)

    _INDEX_CACHE[key] = index
    _META_CACHE[key] = metadata
    return index, metadata


def _chapter_matches(metadata: dict, chapter: str) -> bool:
    chapter_query = chapter.strip().lower()
    chapter_num = str(metadata.get("chapter_num") or "").strip().lower()
    chapter_title = str(metadata.get("chapter_title") or "").strip().lower()
    return (
        chapter_query == chapter_num
        or chapter_query == chapter_title
        or chapter_query in chapter_title
        or chapter_query == f"chapter {chapter_num}".strip()
    )


def retrieve(
    query: str,
    subject: str,
    grade: int,
    chapter: str = None,
    top_k: int = 5,
) -> list[dict]:
    index, metadata = _load_index(subject, grade)
    query_embedding = embed_texts([query], task="query")

    search_k = index.ntotal if chapter else min(max(top_k, 5), index.ntotal)
    distances, indices = index.search(query_embedding, search_k)

    results: list[dict] = []
    for score, idx in zip(distances[0], indices[0]):
        if idx < 0:
            continue
        item = metadata[idx]
        if chapter and not _chapter_matches(item, chapter):
            continue
        results.append(
            {
                "text": item["text"],
                "chapter_title": item.get("chapter_title"),
                "chapter_num": item.get("chapter_num"),
                "page_start": item.get("page_start"),
                "score": float(score),
            }
        )
        if len(results) >= top_k:
            break

    return sorted(results, key=lambda item: item["score"])
