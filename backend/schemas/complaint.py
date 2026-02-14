"""
schemas/complaint.py — Pydantic models for complaint-related API request/response.
All user input is validated here before reaching the service layer.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum
from datetime import datetime
import uuid


class ComplaintCategory(str, Enum):
    road = "Road & Infrastructure"
    water = "Water Supply"
    sanitation = "Sanitation"
    electricity = "Electricity"
    public_safety = "Public Safety"
    parks = "Parks & Green Spaces"
    noise = "Noise Pollution"
    other = "Other"


class SeverityLevel(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class ComplaintStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    resolved = "resolved"


# ---- Request schemas ----

class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    category: ComplaintCategory
    severity: SeverityLevel
    location: str = Field(..., min_length=3, max_length=200)
    image_url: Optional[str] = None

    @field_validator("title", "description", "location")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class ComplaintResolve(BaseModel):
    resolution_note: str = Field(..., min_length=5, max_length=1000)


# ---- Response schemas ----

class AIAnalysis(BaseModel):
    category: str
    severity: str
    summary: str
    keywords: list[str]
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None  # complaint_id if duplicate


class ComplaintResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    category: str
    severity: str
    priority_score: float
    location: str
    status: str
    image_url: Optional[str]
    vote_count: int = 0
    created_at: datetime
    ai_summary: Optional[str] = None
    keywords: Optional[list[str]] = None


class ComplaintListResponse(BaseModel):
    complaints: list[ComplaintResponse]
    total: int
    page: int
    page_size: int
