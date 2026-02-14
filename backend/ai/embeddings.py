"""
ai/embeddings.py — Lightweight embedding and cosine similarity for duplicate detection.
Uses Gemini's embedding-001 model to embed complaint text, then compares with stored vectors.
Falls back to keyword-based similarity if embedding fails.
"""

import json
import math
import httpx
from backend.config import get_settings


GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
SIMILARITY_THRESHOLD = 0.85  # If cosine similarity > this, flag as duplicate


async def get_embedding(text: str) -> list[float] | None:
    """
    Get a vector embedding for a text string using Gemini's embedding model.
    Returns None on failure (graceful degradation).
    """
    settings = get_settings()
    payload = {
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": text}]}
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GEMINI_BASE}/text-embedding-004:embedContent?key={settings.gemini_api_key}",
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]["values"]
    except Exception:
        return None


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two equal-length vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


async def find_duplicate(
    new_embedding: list[float],
    stored_vectors: list[dict]
) -> dict | None:
    """
    Compare a new complaint's embedding against all stored vectors.

    Args:
        new_embedding: Embedding of the new complaint
        stored_vectors: List of { complaint_id: str, embedding: list[float] }

    Returns:
        The most similar complaint dict if similarity > threshold, else None
    """
    best_match = None
    best_score = 0.0

    for item in stored_vectors:
        try:
            existing = item.get("embedding")
            if isinstance(existing, str):
                existing = json.loads(existing)  # Handle JSON-stored embeddings
            if not existing:
                continue
            score = cosine_similarity(new_embedding, existing)
            if score > best_score:
                best_score = score
                best_match = item
        except Exception:
            continue

    if best_score > SIMILARITY_THRESHOLD and best_match:
        return {
            "complaint_id": best_match["complaint_id"],
            "similarity": best_score
        }
    return None
