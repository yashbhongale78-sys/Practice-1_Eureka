"""
services/complaint_service.py — Business logic for complaint lifecycle.

Flow for new complaint:
  1. AI analysis (Gemini) → category, severity, summary, keywords
  2. Generate embedding for duplicate detection
  3. Check against existing vectors → flag if duplicate
  4. Compute priority score
  5. Save to Supabase
"""

import json
from datetime import datetime, timezone
from fastapi import HTTPException, status

from backend.database.client import get_supabase
from backend.schemas.complaint import ComplaintCreate, ComplaintResponse
from backend.ai.gemini_service import analyze_complaint
from backend.ai.embeddings import get_embedding, find_duplicate
from backend.ai.priority import compute_priority_score


async def create_complaint(data: ComplaintCreate, user_id: str) -> dict:
    """Full pipeline: AI analysis → duplicate check → save."""
    sb = get_supabase()

    # ── Step 1: AI analysis ──────────────────────────────────────────
    try:
        ai_result = await analyze_complaint(data.title, data.description)
    except Exception as e:
        # AI failure is non-blocking — use defaults
        ai_result = {
            "category": data.category.value,
            "severity": data.severity.value,
            "summary": data.description[:200],
            "keywords": []
        }

    # Override category/severity with AI if it differs (AI may be more accurate)
    effective_category = ai_result.get("category", data.category.value)
    effective_severity = ai_result.get("severity", data.severity.value)

    # ── Step 2: Embedding generation ────────────────────────────────
    full_text = f"{data.title} {data.description}"
    embedding = await get_embedding(full_text)

    # ── Step 3: Duplicate detection ─────────────────────────────────
    is_duplicate = False
    duplicate_of = None
    duplicate_count = 0

    if embedding:
        # Fetch existing vectors from DB
        vector_rows = sb.table("complaint_vectors").select("complaint_id, embedding").execute()
        stored = vector_rows.data or []

        dup = await find_duplicate(embedding, stored)
        if dup:
            is_duplicate = True
            duplicate_of = dup["complaint_id"]
            # Count how many times this parent has been reported
            dup_count_res = (
                sb.table("complaints")
                .select("id", count="exact")
                .eq("duplicate_of", duplicate_of)
                .execute()
            )
            duplicate_count = dup_count_res.count or 0

    # ── Step 4: Priority score ───────────────────────────────────────
    priority = compute_priority_score(
        severity=effective_severity,
        vote_count=0,
        duplicate_count=duplicate_count,
        created_at=datetime.now(timezone.utc),
        status="pending"
    )

    # ── Step 5: Insert complaint ─────────────────────────────────────
    complaint_row = {
        "user_id": user_id,
        "title": data.title,
        "description": data.description,
        "category": effective_category,
        "severity": effective_severity,
        "priority_score": priority,
        "location": data.location,
        "status": "pending",
        "image_url": data.image_url,
        "ai_summary": ai_result.get("summary"),
        "keywords": ai_result.get("keywords", []),
        "is_duplicate": is_duplicate,
        "duplicate_of": duplicate_of,
    }

    result = sb.table("complaints").insert(complaint_row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save complaint")

    new_complaint = result.data[0]
    complaint_id = new_complaint["id"]

    # ── Step 6: Save embedding for future duplicate detection ────────
    if embedding:
        try:
            sb.table("complaint_vectors").insert({
                "complaint_id": complaint_id,
                "embedding": json.dumps(embedding)  # Store as JSON string
            }).execute()
        except Exception:
            pass  # Non-fatal

    # ── Step 7: If duplicate, bump parent's priority score ───────────
    if duplicate_of:
        _refresh_priority(duplicate_of)

    return new_complaint


def _refresh_priority(complaint_id: str) -> None:
    """Recalculate and update priority score for a given complaint."""
    sb = get_supabase()
    try:
        row = sb.table("complaints").select("*").eq("id", complaint_id).single().execute()
        if not row.data:
            return
        c = row.data

        # Count votes
        vote_res = sb.table("votes").select("id", count="exact").eq("complaint_id", complaint_id).execute()
        votes = vote_res.count or 0

        # Count duplicates
        dup_res = sb.table("complaints").select("id", count="exact").eq("duplicate_of", complaint_id).execute()
        dups = dup_res.count or 0

        new_score = compute_priority_score(
            severity=c["severity"],
            vote_count=votes,
            duplicate_count=dups,
            created_at=c["created_at"],
            status=c["status"]
        )
        sb.table("complaints").update({"priority_score": new_score}).eq("id", complaint_id).execute()
    except Exception:
        pass


async def get_complaints(
    page: int = 1,
    page_size: int = 20,
    location: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    sort_by: str = "priority_score"
) -> dict:
    """Fetch paginated complaints with optional filters."""
    sb = get_supabase()
    query = sb.table("complaints").select("*, votes(count)")

    if location:
        query = query.ilike("location", f"%{location}%")
    if category:
        query = query.eq("category", category)
    if status_filter:
        query = query.eq("status", status_filter)

    # Sort
    desc = sort_by in ("priority_score", "created_at")
    query = query.order(sort_by, desc=desc)

    # Pagination
    offset = (page - 1) * page_size
    query = query.range(offset, offset + page_size - 1)

    result = query.execute()
    complaints = result.data or []

    # Attach vote count
    for c in complaints:
        votes_data = c.pop("votes", [])
        c["vote_count"] = votes_data[0]["count"] if votes_data else 0

    # Total count
    count_result = sb.table("complaints").select("id", count="exact")
    if location:
        count_result = count_result.ilike("location", f"%{location}%")
    if category:
        count_result = count_result.eq("category", category)
    if status_filter:
        count_result = count_result.eq("status", status_filter)
    total = count_result.execute().count or 0

    return {"complaints": complaints, "total": total, "page": page, "page_size": page_size}


async def get_complaint_by_id(complaint_id: str) -> dict:
    """Fetch single complaint by ID with vote count."""
    sb = get_supabase()
    result = sb.table("complaints").select("*, votes(count)").eq("id", complaint_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Complaint not found")
    c = result.data
    votes_data = c.pop("votes", [])
    c["vote_count"] = votes_data[0]["count"] if votes_data else 0
    return c


async def vote_on_complaint(complaint_id: str, user_id: str) -> dict:
    """Add a vote. Prevents duplicate voting. Refreshes priority score."""
    sb = get_supabase()

    # Check if already voted
    existing = (
        sb.table("votes")
        .select("id")
        .eq("complaint_id", complaint_id)
        .eq("user_id", user_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already voted on this complaint"
        )

    # Check complaint exists
    complaint = sb.table("complaints").select("id").eq("id", complaint_id).execute()
    if not complaint.data:
        raise HTTPException(status_code=404, detail="Complaint not found")

    sb.table("votes").insert({
        "complaint_id": complaint_id,
        "user_id": user_id
    }).execute()

    # Recalculate priority
    _refresh_priority(complaint_id)

    # Return updated vote count
    vote_count = (
        sb.table("votes").select("id", count="exact").eq("complaint_id", complaint_id).execute().count or 0
    )
    return {"complaint_id": complaint_id, "vote_count": vote_count}


async def resolve_complaint(complaint_id: str, admin_id: str, note: str) -> dict:
    """Mark complaint as resolved and log the resolution."""
    sb = get_supabase()

    # Verify complaint exists
    complaint = sb.table("complaints").select("id, status").eq("id", complaint_id).execute()
    if not complaint.data:
        raise HTTPException(status_code=404, detail="Complaint not found")

    sb.table("complaints").update({
        "status": "resolved",
    }).eq("id", complaint_id).execute()

    # Log the resolution
    sb.table("resolution_logs").insert({
        "complaint_id": complaint_id,
        "resolved_by": admin_id,
        "resolution_note": note,
    }).execute()

    return {"complaint_id": complaint_id, "status": "resolved"}
