# 🏙️ CivicIQ — AI-Powered Civic Issue Prioritization Platform

CivicIQ is a production-ready MVP that lets citizens report civic problems and uses Google's Gemini AI to automatically categorize, summarize, and priority-score them. The most urgent issues float to the top for administrators to address.

---

## 🏗️ Architecture Overview

```
civic-platform/
├── backend/                    # FastAPI Python backend
│   ├── main.py                 # App entry point, router registration
│   ├── config.py               # Environment variable settings (pydantic-settings)
│   ├── routes/
│   │   ├── auth.py             # POST /auth/register, /auth/login
│   │   ├── complaints.py       # CRUD + vote + resolve
│   │   └── analytics.py        # GET /analytics, /analytics/locality-summary
│   ├── services/
│   │   ├── auth_service.py     # Supabase Auth integration
│   │   ├── complaint_service.py# Full AI pipeline + CRUD
│   │   └── analytics_service.py# Aggregate stats + AI summary
│   ├── ai/
│   │   ├── gemini_service.py   # Gemini API calls (analysis + locality summary)
│   │   ├── embeddings.py       # Vector embeddings + cosine similarity
│   │   └── priority.py         # Priority score formula
│   ├── utils/
│   │   ├── auth.py             # JWT verification FastAPI dependencies
│   │   └── rate_limiter.py     # In-memory per-user rate limiting
│   ├── schemas/
│   │   ├── auth.py             # Pydantic auth models
│   │   ├── complaint.py        # Pydantic complaint models + enums
│   │   └── analytics.py        # Pydantic analytics response models
│   ├── database/
│   │   ├── client.py           # Supabase client singleton
│   │   └── schema.sql          # Full DB schema with RLS policies
│   └── requirements.txt
│
├── frontend/
│   ├── index.html              # Landing page + Login/Register
│   ├── dashboard.html          # Citizen dashboard (complaints + voting)
│   ├── admin.html              # Admin panel (management + analytics + AI)
│   └── js/
│       ├── api.js              # API client (all fetch calls)
│       ├── realtime.js         # Supabase Realtime subscriptions
│       └── ui.js               # Shared utilities (toasts, dark mode, badges)
│
├── .env.example                # Environment variable template
└── README.md
```

---

## 🤖 AI Pipeline (Per Complaint Submission)

```
User submits complaint
        ↓
[1] Gemini API → category, severity, summary, keywords
        ↓
[2] text-embedding-004 → vector embedding
        ↓
[3] Cosine similarity check against stored vectors
        ↓ (if similarity > 0.85)
    Flag as duplicate, reference parent complaint
        ↓
[4] Priority Score = severity_weight + (votes×2) + (duplicates×1.5) + time_decay
        ↓
[5] Save to Supabase + store embedding
        ↓
[6] Supabase Realtime broadcasts INSERT to connected dashboards
```

---

## 📐 Priority Score Formula

```
priority_score =
    severity_weight           (Low=1, Medium=5, High=10)
    + (vote_count × 2)
    + (duplicate_count × 1.5)
    + time_decay              (0.5/day unresolved, max 20)
```

---

## 🚀 Local Development Setup

### Prerequisites
- Python 3.11+
- A Supabase project (free tier works)
- A Google AI Studio account (for Gemini API key)
- Live Server or any static file server for frontend

### 1. Clone & Install Backend

```bash
git clone <repo-url> civic-platform
cd civic-platform/backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# From project root
cp .env.example .env
# Edit .env with your actual keys (see Supabase Setup below)
```

### 3. Run the Backend

```bash
# From project root
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: `http://localhost:8000/docs`

### 4. Serve the Frontend

```bash
# Option A: Python simple server
cd frontend && python -m http.server 3000

# Option B: VS Code Live Server (recommended)
# Install "Live Server" extension, right-click index.html → Open with Live Server
```

### 5. Update Frontend Config

Edit the `<script>` block at the bottom of each HTML file:

```javascript
window.CIVICIQ_API_URL = "http://localhost:8000";
window.SUPABASE_URL = "https://your-project.supabase.co";
window.SUPABASE_ANON_KEY = "your-anon-key";
```

---

## 🗄️ Supabase Setup Guide

### 1. Create a Supabase Project
1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note your **Project URL** and **API Keys** (Settings → API)

### 2. Run the Schema
1. Go to **SQL Editor** in your Supabase dashboard
2. Open `backend/database/schema.sql`
3. Paste the entire contents and click **Run**

This creates:
- `users` table with auth trigger
- `complaints` table with all indexes
- `votes` table with unique constraint (prevents double-voting)
- `complaint_vectors` for embeddings
- `resolution_logs` for audit trail
- Row Level Security policies
- Realtime publication for live updates

### 3. Get Your Keys

From **Project Settings → API**:
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...           (safe for frontend)
SUPABASE_SERVICE_ROLE_KEY=eyJ...   (backend only — never expose)
```

From **Project Settings → API → JWT Settings**:
```
JWT_SECRET=your-jwt-secret
```

### 4. Create an Admin User
1. Register through the app normally
2. In Supabase dashboard → **Table Editor → users**
3. Find your user → edit `role` field to `admin`
4. In **Authentication → Users** → click your user → **Edit** → User Metadata → add `"role": "admin"`

---

## 🔑 Gemini API Key Setup

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API Key** → Create API key
3. Add to `.env`:
   ```
   GEMINI_API_KEY=AIza...
   ```

The platform uses two Gemini models:
- **gemini-1.5-flash** — complaint analysis (fast, cheap)
- **text-embedding-004** — duplicate detection embeddings

---

## 📡 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | — | Register citizen |
| POST | `/auth/login` | — | Login, get JWT |
| POST | `/complaints` | 🔑 Citizen | Submit complaint (AI pipeline) |
| GET | `/complaints` | — | List (paginated, filtered) |
| GET | `/complaints/{id}` | — | Get single complaint |
| POST | `/complaints/{id}/vote` | 🔑 Citizen | Upvote |
| PATCH | `/complaints/{id}/resolve` | 🔑 Admin | Mark resolved |
| GET | `/analytics` | 🔑 Admin | Aggregate metrics |
| GET | `/analytics/locality-summary` | 🔑 Admin | AI-generated locality report |
| GET | `/health` | — | Health probe |

---

## 🌐 Deployment

### Backend (Railway / Render / Fly.io)

```bash
# Dockerfile-ready — uses uvicorn
# Set all environment variables in your hosting dashboard
# Start command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### Frontend (Netlify / Vercel / GitHub Pages)

1. Update the config block in each HTML file to point to your deployed backend URL
2. Deploy the `frontend/` directory as a static site

### Environment Variables for Production

Set all variables from `.env.example` in your hosting platform's environment configuration.
Set `APP_ENV=production` to disable Swagger UI.
Set `CORS_ORIGINS` to your frontend domain.

---

## 🔒 Security Notes

- **Service role key** is only used server-side. Never expose in frontend.
- **JWT verification** on all protected routes using the Supabase JWT secret.
- **Row Level Security** enforced in Supabase — users can only vote once per complaint.
- **Pydantic validation** on all request bodies.
- **Rate limiting** prevents spam (5 complaints/user/hour, configurable).
- **Input sanitization** via HTML escaping on all frontend-rendered user content.

---

## 🧪 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11+) |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth + JWT |
| Realtime | Supabase Realtime (WebSockets) |
| AI Analysis | Google Gemini 1.5 Flash |
| Embeddings | Google text-embedding-004 |
| Frontend | HTML5 + Tailwind CSS (CDN) + Vanilla JS |
| Charts | Chart.js |
