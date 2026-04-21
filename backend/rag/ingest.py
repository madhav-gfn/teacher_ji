from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import faiss
import fitz
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MIN_CHARS = 200
MAX_CHARS = 800
BATCH_SIZE = 32
BOLD_FLAG = 2**4
CHAPTER_RE = re.compile(r"^\s*Chapter\s+(\d+)\b", re.IGNORECASE)


@dataclass
class LineRecord:
    page: int
    text: str
    bold: bool
    separator: bool = False


@dataclass
class Section:
    source_file: str
    heading_lines: list[str]
    body_parts: list[str]
    page_start: int
    page_end: int
    chapter_num: str | None = None
    chapter_title: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest NCERT PDFs into FAISS.")
    parser.add_argument("--subject", required=True, help="Subject name, e.g. math")
    parser.add_argument("--grade", required=True, type=int, help="Class grade, e.g. 6")
    parser.add_argument("--pdf_dir", required=True, help="Directory containing NCERT PDFs")
    return parser.parse_args()


def normalize_subject(subject: str) -> str:
    return subject.strip().lower()


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def is_all_caps(text: str) -> bool:
    letters = re.findall(r"[A-Za-z]", text)
    if not letters:
        return False
    return "".join(letters).upper() == "".join(letters)


def is_heading_line(text: str, bold: bool) -> bool:
    cleaned = normalize_text(text)
    if not cleaned:
        return False
    if not re.search(r"[A-Za-z]", cleaned):
        return False
    return bool(CHAPTER_RE.match(cleaned) or is_all_caps(cleaned) or bold)


def extract_pdf_lines(pdf_path: Path) -> list[LineRecord]:
    records: list[LineRecord] = []
    with fitz.open(pdf_path) as doc:
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            page_num = page_index + 1
            text_dict = page.get_text("dict")
            page_had_text = False

            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue

                block_had_text = False
                for line in block.get("lines", []):
                    spans = [span for span in line.get("spans", []) if span.get("text", "").strip()]
                    if not spans:
                        continue

                    text = normalize_text("".join(span.get("text", "") for span in spans))
                    if not text:
                        continue

                    bold = any(int(span.get("flags", 0)) & BOLD_FLAG for span in spans)
                    records.append(LineRecord(page=page_num, text=text, bold=bold))
                    block_had_text = True
                    page_had_text = True

                if block_had_text:
                    records.append(LineRecord(page=page_num, text="", bold=False, separator=True))

            if page_had_text:
                records.append(LineRecord(page=page_num, text="", bold=False, separator=True))

    return records


def build_sections(source_file: str, lines: list[LineRecord]) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None

    for record in lines:
        if record.separator:
            if current and current.body_parts and current.body_parts[-1] != "":
                current.body_parts.append("")
            continue

        if is_heading_line(record.text, record.bold):
            if current is None:
                current = Section(
                    source_file=source_file,
                    heading_lines=[record.text],
                    body_parts=[],
                    page_start=record.page,
                    page_end=record.page,
                )
            elif current.body_parts:
                sections.append(current)
                current = Section(
                    source_file=source_file,
                    heading_lines=[record.text],
                    body_parts=[],
                    page_start=record.page,
                    page_end=record.page,
                )
            else:
                current.heading_lines.append(record.text)
                current.page_end = record.page
            continue

        if current is None:
            current = Section(
                source_file=source_file,
                heading_lines=[],
                body_parts=[],
                page_start=record.page,
                page_end=record.page,
            )

        current.body_parts.append(record.text)
        current.page_end = record.page

    if current and (current.heading_lines or current.body_parts):
        sections.append(current)

    return sections


def combine_heading_lines(lines: Iterable[str]) -> str | None:
    cleaned = [normalize_text(line) for line in lines if normalize_text(line)]
    if not cleaned:
        return None
    return " ".join(cleaned)


def assign_chapter_metadata(sections: list[Section]) -> list[Section]:
    current_num: str | None = None
    current_title: str | None = None

    for section in sections:
        chapter_match = None
        for heading in section.heading_lines:
            match = CHAPTER_RE.match(heading)
            if match:
                chapter_match = match
                break

        if chapter_match:
            current_num = chapter_match.group(1)
            title_lines = [
                line
                for line in section.heading_lines
                if not CHAPTER_RE.match(line)
            ]
            current_title = combine_heading_lines(title_lines) or f"Chapter {current_num}"
        elif current_title is None and section.heading_lines:
            current_title = combine_heading_lines(section.heading_lines)

        section.chapter_num = current_num
        section.chapter_title = current_title or "Unknown"

    return sections


def body_text_from_parts(parts: list[str]) -> str:
    paragraphs: list[str] = []
    current_lines: list[str] = []

    for part in parts:
        if part == "":
            if current_lines:
                paragraphs.append(" ".join(current_lines).strip())
                current_lines = []
            continue
        current_lines.append(part)

    if current_lines:
        paragraphs.append(" ".join(current_lines).strip())

    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def render_section_text(section: Section) -> str:
    heading_text = combine_heading_lines(section.heading_lines)
    body_text = body_text_from_parts(section.body_parts)
    pieces = [piece for piece in (heading_text, body_text) if piece]
    return "\n\n".join(pieces).strip()


def find_sentence_boundary(text: str, max_chars: int, min_chars: int = MIN_CHARS) -> int:
    if len(text) <= max_chars:
        return len(text)

    limit = min(max_chars, len(text) - 1)
    for idx in range(limit, min_chars - 1, -1):
        if text[idx] in ".!?":
            return idx + 1

    for idx in range(limit, min_chars - 1, -1):
        if text[idx].isspace():
            return idx

    return max_chars


def split_long_paragraph(paragraph: str) -> list[str]:
    pieces: list[str] = []
    remaining = paragraph.strip()

    while remaining:
        if len(remaining) <= MAX_CHARS:
            pieces.append(remaining)
            break

        cut = find_sentence_boundary(remaining, MAX_CHARS)
        piece = remaining[:cut].strip()
        if not piece:
            piece = remaining[:MAX_CHARS].strip()
            cut = len(piece)

        pieces.append(piece)
        remaining = remaining[cut:].lstrip()

    return rebalance_small_chunks(pieces)


def find_balanced_boundary(text: str) -> int:
    max_first = min(MAX_CHARS, len(text) - MIN_CHARS)
    if max_first < MIN_CHARS:
        return max_first

    for idx in range(max_first, MIN_CHARS - 1, -1):
        if text[idx] in ".!?":
            return idx + 1

    for idx in range(max_first, MIN_CHARS - 1, -1):
        if text[idx].isspace():
            return idx

    return max_first


def rebalance_small_chunks(chunks: list[str]) -> list[str]:
    balanced = [chunk.strip() for chunk in chunks if chunk.strip()]
    idx = 1

    while idx < len(balanced):
        current = balanced[idx]
        if len(current) >= MIN_CHARS:
            idx += 1
            continue

        combined = f"{balanced[idx - 1]}\n\n{current}".strip()
        if len(combined) <= MAX_CHARS:
            balanced[idx - 1] = combined
            del balanced[idx]
            continue

        boundary = find_balanced_boundary(combined)
        if MIN_CHARS <= boundary <= MAX_CHARS:
            left = combined[:boundary].strip()
            right = combined[boundary:].strip()
            if (
                left
                and right
                and len(left) >= MIN_CHARS
                and len(left) <= MAX_CHARS
                and len(right) >= MIN_CHARS
                and len(right) <= MAX_CHARS
            ):
                balanced[idx - 1] = left
                balanced[idx] = right
                idx += 1
                continue

        idx += 1

    return balanced


def split_section_text(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    if len(stripped) <= MAX_CHARS:
        return [stripped]

    paragraphs = [para.strip() for para in re.split(r"\n\s*\n", stripped) if para.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= MAX_CHARS:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            current = ""

        if len(paragraph) <= MAX_CHARS:
            current = paragraph
            continue

        chunks.extend(split_long_paragraph(paragraph))

    if current:
        chunks.append(current.strip())

    return rebalance_small_chunks(chunks)


def can_merge(left: dict, right: dict) -> bool:
    return (
        left["source_file"] == right["source_file"]
        and left["chapter_num"] == right["chapter_num"]
        and left["chapter_title"] == right["chapter_title"]
    )


def merge_chunks(left: dict, right: dict) -> dict:
    merged = dict(left)
    merged["text"] = f'{left["text"]}\n\n{right["text"]}'.strip()
    merged["page_end"] = right["page_end"]
    return merged


def build_chunk_records(
    sections: list[Section],
    grade: int,
    subject: str,
) -> list[dict]:
    raw_chunks: list[dict] = []

    for section in sections:
        section_text = render_section_text(section)
        if not section_text:
            continue

        for piece in split_section_text(section_text):
            raw_chunks.append(
                {
                    "text": piece,
                    "source_file": section.source_file,
                    "class_grade": grade,
                    "subject": subject,
                    "chapter_num": section.chapter_num,
                    "chapter_title": section.chapter_title,
                    "page_start": section.page_start,
                    "page_end": section.page_end,
                }
            )

    merged: list[dict] = []
    for chunk in raw_chunks:
        if merged and len(merged[-1]["text"]) < MIN_CHARS and can_merge(merged[-1], chunk):
            candidate = merge_chunks(merged[-1], chunk)
            if len(candidate["text"]) <= MAX_CHARS:
                merged[-1] = candidate
                continue
        merged.append(chunk)

    for idx in range(len(merged) - 1, 0, -1):
        current = merged[idx]
        previous = merged[idx - 1]
        if len(current["text"]) >= MIN_CHARS:
            continue
        if not can_merge(previous, current):
            continue

        candidate = merge_chunks(previous, current)
        if len(candidate["text"]) <= MAX_CHARS:
            merged[idx - 1] = candidate
            del merged[idx]

    for chunk_index, chunk in enumerate(merged):
        chunk["chunk_index"] = chunk_index

    return merged


def load_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_texts(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    embeddings: list[np.ndarray] = []
    for start in tqdm(range(0, len(texts), BATCH_SIZE), desc="Embedding chunks", unit="batch"):
        batch = texts[start : start + BATCH_SIZE]
        batch_embeddings = model.encode(
            batch,
            batch_size=BATCH_SIZE,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        embeddings.append(batch_embeddings.astype("float32"))

    if not embeddings:
        raise ValueError("No embeddings were generated.")

    return np.vstack(embeddings)


def write_index(subject: str, grade: int, embeddings: np.ndarray, metadata: list[dict]) -> None:
    index_dir = Path(__file__).resolve().parent / "index"
    index_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{normalize_subject(subject)}_class{grade}"
    faiss_path = index_dir / f"{base_name}.faiss"
    meta_path = index_dir / f"{base_name}_meta.json"

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, str(faiss_path))

    with meta_path.open("w", encoding="utf-8") as meta_file:
        json.dump(metadata, meta_file, ensure_ascii=True, indent=2)


def ingest_subject(subject: str, grade: int, pdf_dir: Path) -> tuple[int, int]:
    subject = normalize_subject(subject)
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {pdf_dir}")

    all_sections: list[Section] = []
    for pdf_path in tqdm(pdf_files, desc="Parsing PDFs", unit="pdf"):
        lines = extract_pdf_lines(pdf_path)
        sections = build_sections(pdf_path.name, lines)
        all_sections.extend(assign_chapter_metadata(sections))

    metadata = build_chunk_records(all_sections, grade=grade, subject=subject)
    if not metadata:
        raise ValueError("No chunks were generated from the provided PDFs.")

    model = load_model()
    embeddings = embed_texts(model, [item["text"] for item in metadata])
    write_index(subject=subject, grade=grade, embeddings=embeddings, metadata=metadata)
    return len(pdf_files), len(metadata)


def main() -> None:
    args = parse_args()
    pdf_dir = Path(args.pdf_dir).resolve()
    pdf_count, chunk_count = ingest_subject(args.subject, args.grade, pdf_dir)
    print(
        f"Ingested {pdf_count} PDF(s) for subject={normalize_subject(args.subject)} "
        f"class={args.grade} into {chunk_count} chunk(s)."
    )


if __name__ == "__main__":
    main()
