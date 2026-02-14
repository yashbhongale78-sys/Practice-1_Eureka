"""
services/analytics_service.py — Aggregate analytics for the admin dashboard.
Also triggers the AI locality summary generation.
"""

from datetime import datetime, timezone
from backend.database.client import get_supabase
from backend.ai.gemini_service import generate_locality_summary


async def get_analytics() -> dict:
    """Compute all analytics metrics from the database."""
    sb = get_supabase()

    # ── Totals ───────────────────────────────────────────────────────
    total_res = sb.table("complaints").select("id", count="exact").execute()
    total = total_res.count or 0

    pending_res = sb.table("complaints").select("id", count="exact").eq("status", "pending").execute()
    pending = pending_res.count or 0

    resolved_res = sb.table("complaints").select("id", count="exact").eq("status", "resolved").execute()
    resolved = resolved_res.count or 0

    high_unresolved_res = (
        sb.table("complaints")
        .select("id", count="exact")
        .eq("severity", "High")
        .neq("status", "resolved")
        .execute()
    )
    high_unresolved = high_unresolved_res.count or 0

    # ── Complaints by category ───────────────────────────────────────
    all_complaints = sb.table("complaints").select("category, location, created_at, status").execute()
    complaints = all_complaints.data or []

    category_counts: dict[str, int] = {}
    location_counts: dict[str, int] = {}
    for c in complaints:
        cat = c.get("category", "Other")
        category_counts[cat] = category_counts.get(cat, 0) + 1

        loc = c.get("location", "Unknown")
        # Normalize location to first segment (city/area)
        loc_key = loc.split(",")[0].strip()
        location_counts[loc_key] = location_counts.get(loc_key, 0) + 1

    # Sort categories and top locations
    by_category = [
        {"category": k, "count": v}
        for k, v in sorted(category_counts.items(), key=lambda x: -x[1])
    ]
    top_3_locations = [
        {"location": k, "count": v}
        for k, v in sorted(location_counts.items(), key=lambda x: -x[1])[:3]
    ]

    # ── Average resolution time ──────────────────────────────────────
    logs = sb.table("resolution_logs").select("resolved_at, complaint_id").execute()
    avg_hours = None
    if logs.data:
        durations = []
        for log in logs.data:
            resolved_at_str = log.get("resolved_at")
            # Get complaint creation time
            try:
                comp = (
                    sb.table("complaints")
                    .select("created_at")
                    .eq("id", log["complaint_id"])
                    .single()
                    .execute()
                )
                if comp.data and resolved_at_str:
                    created = datetime.fromisoformat(comp.data["created_at"].replace("Z", "+00:00"))
                    resolved = datetime.fromisoformat(resolved_at_str.replace("Z", "+00:00"))
                    hours = (resolved - created).total_seconds() / 3600
                    durations.append(hours)
            except Exception:
                pass
        if durations:
            avg_hours = round(sum(durations) / len(durations), 1)

    # ── Civic health score ───────────────────────────────────────────
    civic_health = max(0.0, 100.0 - (high_unresolved * 5))

    return {
        "total_complaints": total,
        "pending_complaints": pending,
        "resolved_complaints": resolved,
        "high_severity_unresolved": high_unresolved,
        "complaints_by_category": by_category,
        "top_3_locations": top_3_locations,
        "avg_resolution_hours": avg_hours,
        "civic_health_score": civic_health
    }


async def get_locality_summary() -> dict:
    """Generate AI-powered locality summary from recent complaints."""
    sb = get_supabase()

    # Fetch 20 most recent unresolved complaints
    result = (
        sb.table("complaints")
        .select("title, description, category, location, severity")
        .neq("status", "resolved")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    complaints_data = result.data or []

    try:
        ai_summary = await generate_locality_summary(complaints_data)
    except Exception as e:
        ai_summary = {
            "summary": "Unable to generate summary at this time.",
            "top_issues": [],
            "recommendations": []
        }

    ai_summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    return ai_summary
