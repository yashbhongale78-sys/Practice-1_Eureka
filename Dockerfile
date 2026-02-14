# ── CivicIQ Backend Dockerfile ──────────────────────────
# Build: docker build -t civiciq-backend .
# Run:   docker run -p 8000:8000 --env-file .env civiciq-backend

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend/ ./backend/

# Expose API port
EXPOSE 8000

# Start with uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
