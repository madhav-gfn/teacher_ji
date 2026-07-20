"""
Document routes — upload and manage a student's own study material.

Endpoints:
    POST   /documents/upload         → parse, chunk, embed, index, and save an upload
    GET    /documents?student_id=    → list a student's uploaded documents
    GET    /documents/{document_id}  → document detail, including its topic list
    DELETE /documents/{document_id}  → remove a document's index files + DB row

An uploaded document is chunked and embedded into its own FAISS index
(rag/ingest.py:ingest_document) and organized into a short topic list by the
LLM (agents/document_agent.py:extract_topics). Studying it then goes through
the same /session/* flow as an NCERT chapter — see api/routes/session.py.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from agents.document_agent import extract_topics
from api.db import (
    delete_document as db_delete_document,
    get_document,
    insert_document,
    list_documents,
)
from api.models import DocumentDetail, DocumentSummary, UploadDocumentResponse
from rag.ingest import SUPPORTED_UPLOAD_EXTENSIONS, ingest_document
from rag.retriever import custom_index_paths, evict_document_index

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


# ---------------------------------------------------------------------------
# POST /documents/upload
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(
    student_id: str = Form(...),
    title: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> UploadDocumentResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {allowed}.",
        )

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB).")

    document_id = uuid.uuid4().hex
    filename = file.filename or f"{document_id}{suffix}"
    fallback_title = (title or Path(filename).stem).strip() or filename

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        tmp_path.write_bytes(raw_bytes)

        try:
            chunks = await asyncio.to_thread(ingest_document, document_id, tmp_path, fallback_title)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 — surface as a clean 500, log the real cause
            logger.error("Ingestion failed for '%s': %s", filename, exc)
            raise HTTPException(status_code=500, detail="Failed to process the uploaded file.") from exc

        try:
            extracted_title, topics = await asyncio.to_thread(extract_topics, chunks, filename)
        except Exception as exc:  # noqa: BLE001 — topic extraction is best-effort
            logger.warning("Topic extraction failed for '%s', using fallback: %s", filename, exc)
            extracted_title, topics = fallback_title, ["Overview"]

    final_title = (title or extracted_title or fallback_title).strip() or fallback_title

    await insert_document(
        document_id=document_id,
        student_id=student_id,
        title=final_title,
        filename=filename,
        topics=topics,
        chunk_count=len(chunks),
    )

    row = await get_document(document_id)
    if row is None:
        raise HTTPException(status_code=500, detail="Document was saved but could not be reloaded.")
    return UploadDocumentResponse(
        document_id=row["document_id"],
        title=row["title"],
        filename=row["filename"],
        topic_count=len(row["topics"]),
        chunk_count=row["chunk_count"],
        created_at=row["created_at"],
        topics=row["topics"],
    )


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------


@router.get("", response_model=list[DocumentSummary])
async def get_student_documents(student_id: str) -> list[DocumentSummary]:
    rows = await list_documents(student_id)
    return [
        DocumentSummary(
            document_id=row["document_id"],
            title=row["title"],
            filename=row["filename"],
            topic_count=len(row["topics"]),
            chunk_count=row["chunk_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# GET /documents/{document_id}
# ---------------------------------------------------------------------------


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document_detail(document_id: str) -> DocumentDetail:
    row = await get_document(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    return DocumentDetail(
        document_id=row["document_id"],
        title=row["title"],
        filename=row["filename"],
        topic_count=len(row["topics"]),
        chunk_count=row["chunk_count"],
        created_at=row["created_at"],
        topics=row["topics"],
    )


# ---------------------------------------------------------------------------
# DELETE /documents/{document_id}
# ---------------------------------------------------------------------------


@router.delete("/{document_id}")
async def remove_document(document_id: str) -> dict[str, str]:
    row = await get_document(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    faiss_path, meta_path = custom_index_paths(document_id)
    faiss_path.unlink(missing_ok=True)
    meta_path.unlink(missing_ok=True)
    evict_document_index(document_id)

    await db_delete_document(document_id)

    return {"status": "deleted", "document_id": document_id}
