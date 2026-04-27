from __future__ import annotations

import os
from typing import Literal

import httpx
import numpy as np
from dotenv import find_dotenv, load_dotenv
from huggingface_hub import InferenceClient


EmbeddingTask = Literal["query", "document"]

load_dotenv(find_dotenv(usecwd=True), override=True)

PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").strip().lower()
GOOGLE_MODEL = os.getenv("GOOGLE_EMBEDDING_MODEL", "gemini-embedding-001").strip()
HF_MODEL = os.getenv("HF_EMBEDDING_MODEL", "microsoft/harrier-oss-v1-0.6b").strip()
REQUEST_TIMEOUT = float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "60"))


class EmbeddingError(RuntimeError):
    """Raised when the configured embedding provider cannot produce vectors."""


def _as_float32_matrix(vectors: list[list[float]]) -> np.ndarray:
    if not vectors:
        raise EmbeddingError("Embedding provider returned no vectors.")
    return np.asarray(vectors, dtype="float32")


def _google_task(task: EmbeddingTask) -> str:
    return "RETRIEVAL_QUERY" if task == "query" else "RETRIEVAL_DOCUMENT"


def _embed_google(texts: list[str], task: EmbeddingTask) -> np.ndarray:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EmbeddingError("GOOGLE_API_KEY is required when EMBEDDING_PROVIDER=google.")

    model = f"models/{GOOGLE_MODEL}"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:batchEmbedContents"
    body = {
        "requests": [
            {
                "model": model,
                "content": {"parts": [{"text": text}]},
                "taskType": _google_task(task),
            }
            for text in texts
        ]
    }

    response = httpx.post(
        url,
        params={"key": api_key},
        json=body,
        timeout=REQUEST_TIMEOUT,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise EmbeddingError(f"Google embedding request failed: {response.text}") from exc

    payload = response.json()
    vectors = [item["values"] for item in payload.get("embeddings", [])]
    return _as_float32_matrix(vectors)


def _embed_huggingface(texts: list[str], task: EmbeddingTask) -> np.ndarray:
    token = os.getenv("HF_API_TOKEN") or os.getenv("HF_TOKEN")
    if not token:
        raise EmbeddingError(
            "HF_API_TOKEN or HF_TOKEN is required when EMBEDDING_PROVIDER=huggingface."
        )
    if HF_MODEL == "sentence-transformers/all-MiniLM-L6-v2":
        raise EmbeddingError(
            "HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 is routed "
            "by Hugging Face as sentence-similarity, not feature-extraction. Use "
            "HF_EMBEDDING_MODEL=microsoft/harrier-oss-v1-0.6b."
        )

    if HF_MODEL.startswith("intfloat/") and "e5" in HF_MODEL:
        inputs = [
            f"{'query' if task == 'query' else 'passage'}: {text}"
            for text in texts
        ]
    else:
        inputs = texts

    client = InferenceClient(provider="hf-inference", api_key=token)
    try:
        payload = client.feature_extraction(
            inputs,
            model=HF_MODEL,
            normalize=True,
            truncate=True,
        )
    except Exception as exc:
        raise EmbeddingError(f"Hugging Face feature extraction failed: {exc}") from exc

    vectors = np.asarray(payload, dtype="float32")
    if vectors.ndim == 3:
        vectors = vectors.mean(axis=1)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    if vectors.ndim != 2:
        raise EmbeddingError(
            f"Hugging Face returned an unexpected embedding shape: {vectors.shape}"
        )
    return vectors.astype("float32")


def embed_texts(texts: list[str], task: EmbeddingTask = "document") -> np.ndarray:
    cleaned = [text.strip() for text in texts if text and text.strip()]
    if not cleaned:
        raise EmbeddingError("No text supplied for embedding.")

    if PROVIDER == "google":
        return _embed_google(cleaned, task)
    if PROVIDER in {"huggingface", "hf"}:
        return _embed_huggingface(cleaned, task)

    raise EmbeddingError(
        "Unsupported EMBEDDING_PROVIDER. Use 'google' or 'huggingface'."
    )
