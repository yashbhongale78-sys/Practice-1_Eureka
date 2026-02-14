"""
utils/rate_limiter.py — Simple in-memory rate limiter per user.
Tracks complaint submissions and rejects if limit exceeded within window.
"""

from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import HTTPException, status
from backend.config import get_settings


# Structure: { user_id: [timestamp, timestamp, ...] }
_submission_log: dict[str, list[datetime]] = defaultdict(list)

WINDOW_HOURS = 1  # Rolling time window


def check_complaint_rate_limit(user_id: str) -> None:
    """
    Raises HTTP 429 if user has exceeded the complaint submission limit
    within the rolling hour window.
    """
    settings = get_settings()
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=WINDOW_HOURS)

    # Remove timestamps outside the window
    _submission_log[user_id] = [
        t for t in _submission_log[user_id] if t > cutoff
    ]

    if len(_submission_log[user_id]) >= settings.rate_limit_complaints:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {settings.rate_limit_complaints} complaints per hour."
        )

    # Record this submission
    _submission_log[user_id].append(now)
