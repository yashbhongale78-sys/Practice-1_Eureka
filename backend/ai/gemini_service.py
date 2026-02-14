"""
ai/gemini_service.py — Gemini API integration for complaint analysis.
Analyzes text → returns structured JSON (category, severity, summary, keywords).
Also generates locality summaries for the admin dashboard.
"""

import json
import httpx
from backend.config import get_settings


GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL = "gemini-1.5-flash"  # Fast, cost-effective for this use case


async def analyze_complaint(title: str, description: str) -> dict:
    """
    Send complaint text to Gemini and get structured analysis.

    Returns:
        {
            "category": str,
            "severity": "Low" | "Medium" | "High",
            "summary": str,
            "keywords": [str]
        }
    """
    settings = get_settings()
    prompt = f"""
You are a civic complaint analysis AI. Analyze this complaint and return ONLY valid JSON.

Complaint Title: {title}
Complaint Description: {description}

Return exactly this JSON structure (no markdown, no explanation):
{{
  "category": "<one of: Road & Infrastructure, Water Supply, Sanitation, Electricity, Public Safety, Parks & Green Spaces, Noise Pollution, Other>",
  "severity": "<one of: Low, Medium, High>",
  "summary": "<1-2 sentence summary of the core issue>",
  "keywords": ["<keyword1>", "<keyword2>", "<keyword3>"]
}}

Severity guide:
- High: immediate safety risk, water/power outage, major road damage
- Medium: recurring issue, moderate inconvenience, health risk
- Low: minor issue, aesthetic problem, low urgency
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 512,
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GEMINI_BASE}/{GEMINI_MODEL}:generateContent?key={settings.gemini_api_key}",
            json=payload
        )
        resp.raise_for_status()
        data = resp.json()

    # Extract text from Gemini response structure
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Strip any accidental markdown code fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]

    return json.loads(raw_text.strip())


async def generate_locality_summary(complaints_data: list[dict]) -> dict:
    """
    Generate an AI summary of civic issues in the locality based on recent complaints.

    Args:
        complaints_data: List of complaint dicts (title, description, category, location, severity)

    Returns:
        { "summary": str, "top_issues": [str], "recommendations": [str] }
    """
    settings = get_settings()

    if not complaints_data:
        return {
            "summary": "No complaints found in the system yet.",
            "top_issues": [],
            "recommendations": ["Encourage citizens to report civic issues."]
        }

    # Format complaints for the prompt (limit to 20 most recent to stay within token limits)
    complaints_text = "\n".join([
        f"- [{c.get('category', 'Other')}] {c.get('title', '')} "
        f"(Severity: {c.get('severity', 'Low')}, Location: {c.get('location', 'Unknown')})"
        for c in complaints_data[:20]
    ])

    prompt = f"""
You are a civic intelligence analyst. Based on these reported civic complaints, generate an insightful locality report.

Recent Complaints:
{complaints_text}

Return ONLY valid JSON (no markdown):
{{
  "summary": "<2-3 paragraph analysis of the main civic problems>",
  "top_issues": ["<issue 1>", "<issue 2>", "<issue 3>"],
  "recommendations": ["<recommendation 1>", "<recommendation 2>", "<recommendation 3>"]
}}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GEMINI_BASE}/{GEMINI_MODEL}:generateContent?key={settings.gemini_api_key}",
            json=payload
        )
        resp.raise_for_status()
        data = resp.json()

    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]

    return json.loads(raw_text.strip())
