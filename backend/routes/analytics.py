"""
routes/analytics.py — Analytics and AI locality summary endpoints.
Admin-only access.
"""

from fastapi import APIRouter, Depends
from backend.services.analytics_service import get_analytics, get_locality_summary
from backend.utils.auth import require_admin

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("")
async def analytics(admin: dict = Depends(require_admin)):
    """
    Return aggregate analytics:
    - Total/pending/resolved complaint counts
    - Category breakdown
    - Top 3 affected locations
    - Average resolution time
    - Civic health score
    """
    return await get_analytics()


@router.get("/locality-summary")
async def locality_summary(admin: dict = Depends(require_admin)):
    """
    Generate an AI-powered summary of current civic issues in the locality.
    Based on the 20 most recent unresolved complaints.
    """
    return await get_locality_summary()
