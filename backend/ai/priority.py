"""
ai/priority.py — Priority score computation engine.

Formula:
    priority_score =
        severity_weight
        + (vote_count * 2)
        + (duplicate_count * 1.5)
        + time_decay_factor

Severity weights: Low=1, Medium=5, High=10
Time decay: +0.5 per unresolved day, capped at 20
"""

from datetime import datetime, timezone

SEVERITY_WEIGHTS = {
    "Low": 1.0,
    "Medium": 5.0,
    "High": 10.0
}

VOTE_MULTIPLIER = 2.0
DUPLICATE_MULTIPLIER = 1.5
TIME_DECAY_PER_DAY = 0.5
TIME_DECAY_CAP = 20.0


def compute_priority_score(
    severity: str,
    vote_count: int,
    duplicate_count: int,
    created_at: datetime | str,
    status: str = "pending"
) -> float:
    """
    Compute priority score for a complaint.

    Args:
        severity: "Low", "Medium", or "High"
        vote_count: Number of upvotes
        duplicate_count: Number of similar complaints (duplicates referencing this one)
        created_at: ISO string or datetime when complaint was created
        status: "pending" | "in_progress" | "resolved"

    Returns:
        Float priority score (higher = more urgent)
    """
    # Severity base
    severity_weight = SEVERITY_WEIGHTS.get(severity, 1.0)

    # Vote contribution
    vote_score = vote_count * VOTE_MULTIPLIER

    # Duplicate contribution — many reports of same issue = higher priority
    dup_score = duplicate_count * DUPLICATE_MULTIPLIER

    # Time decay — unresolved complaints get higher priority over time
    time_decay = 0.0
    if status != "resolved":
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        days_old = (datetime.now(timezone.utc) - created_at).total_seconds() / 86400
        time_decay = min(days_old * TIME_DECAY_PER_DAY, TIME_DECAY_CAP)

    total = severity_weight + vote_score + dup_score + time_decay
    return round(total, 2)
