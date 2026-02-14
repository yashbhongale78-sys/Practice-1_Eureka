"""
routes/complaints.py — CRUD endpoints for civic complaints.
All write operations require authentication. Admin routes require admin role.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from backend.schemas.complaint import ComplaintCreate, ComplaintResolve
from backend.services.complaint_service import (
    create_complaint, get_complaints, get_complaint_by_id,
    vote_on_complaint, resolve_complaint
)
from backend.utils.auth import get_current_user, require_admin
from backend.utils.rate_limiter import check_complaint_rate_limit

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", status_code=201)
async def submit_complaint(
    data: ComplaintCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit a new civic complaint.
    Triggers AI analysis, duplicate detection, and priority scoring.
    Rate limited to 5 complaints per user per hour.
    """
    check_complaint_rate_limit(current_user["user_id"])
    return await create_complaint(data, current_user["user_id"])


@router.get("")
async def list_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    location: Optional[str] = Query(None, description="Filter by location substring"),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="pending | in_progress | resolved"),
    sort_by: str = Query("priority_score", description="priority_score | created_at")
):
    """
    List complaints with optional filters.
    Public endpoint — no auth required for viewing.
    Sorted by priority score by default.
    """
    return await get_complaints(
        page=page,
        page_size=page_size,
        location=location,
        category=category,
        status_filter=status,
        sort_by=sort_by
    )


@router.get("/{complaint_id}")
async def get_complaint(complaint_id: str):
    """Retrieve a single complaint by ID."""
    return await get_complaint_by_id(complaint_id)


@router.post("/{complaint_id}/vote")
async def vote(
    complaint_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Upvote a complaint. Each user can vote once per complaint.
    Voting triggers a priority score refresh.
    """
    return await vote_on_complaint(complaint_id, current_user["user_id"])


@router.patch("/{complaint_id}/resolve")
async def resolve(
    complaint_id: str,
    data: ComplaintResolve,
    admin: dict = Depends(require_admin)
):
    """
    Mark a complaint as resolved (admin only).
    Logs the resolution with notes.
    """
    return await resolve_complaint(complaint_id, admin["user_id"], data.resolution_note)
