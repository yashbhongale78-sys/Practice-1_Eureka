"""
schemas/analytics.py — Response models for analytics endpoints.
"""

from pydantic import BaseModel
from typing import Optional


class CategoryCount(BaseModel):
    category: str
    count: int


class LocationCount(BaseModel):
    location: str
    count: int


class AnalyticsResponse(BaseModel):
    total_complaints: int
    pending_complaints: int
    resolved_complaints: int
    high_severity_unresolved: int
    complaints_by_category: list[CategoryCount]
    top_3_locations: list[LocationCount]
    avg_resolution_hours: Optional[float]
    civic_health_score: float  # 100 - (high_severity_unresolved * 5), floor 0


class LocalitySummaryResponse(BaseModel):
    summary: str
    top_issues: list[str]
    recommendations: list[str]
    generated_at: str
