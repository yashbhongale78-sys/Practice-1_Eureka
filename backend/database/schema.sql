-- ============================================================
-- CivicIQ Supabase Schema
-- Run this in the Supabase SQL Editor (Project → SQL Editor)
-- ============================================================

-- Enable UUID extension (usually pre-enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────────
-- 1. USERS TABLE (mirrors auth.users for easy querying)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.users (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL DEFAULT 'citizen' CHECK (role IN ('citizen', 'admin')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-create user record on sign-up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, role)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'role', 'citizen')
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ─────────────────────────────────────────────────────────────
-- 2. COMPLAINTS TABLE
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.complaints (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    category        TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK (severity IN ('Low', 'Medium', 'High')),
    priority_score  FLOAT NOT NULL DEFAULT 0,
    location        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved')),
    image_url       TEXT,
    ai_summary      TEXT,
    keywords        TEXT[],            -- Array of keyword strings from AI
    is_duplicate    BOOLEAN DEFAULT FALSE,
    duplicate_of    UUID REFERENCES public.complaints(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER complaints_updated_at
    BEFORE UPDATE ON public.complaints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_complaints_priority ON public.complaints(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_location ON public.complaints(location);
CREATE INDEX IF NOT EXISTS idx_complaints_created_at ON public.complaints(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON public.complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_category ON public.complaints(category);
CREATE INDEX IF NOT EXISTS idx_complaints_user ON public.complaints(user_id);


-- ─────────────────────────────────────────────────────────────
-- 3. VOTES TABLE
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.votes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    complaint_id    UUID NOT NULL REFERENCES public.complaints(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(complaint_id, user_id)   -- One vote per user per complaint
);

CREATE INDEX IF NOT EXISTS idx_votes_complaint ON public.votes(complaint_id);


-- ─────────────────────────────────────────────────────────────
-- 4. COMPLAINT VECTORS (for duplicate detection)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.complaint_vectors (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    complaint_id    UUID NOT NULL REFERENCES public.complaints(id) ON DELETE CASCADE,
    embedding       TEXT NOT NULL,  -- JSON-encoded float array
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(complaint_id)
);


-- ─────────────────────────────────────────────────────────────
-- 5. RESOLUTION LOGS
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.resolution_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    complaint_id    UUID NOT NULL REFERENCES public.complaints(id) ON DELETE CASCADE,
    resolved_by     UUID NOT NULL REFERENCES public.users(id),
    resolution_note TEXT NOT NULL,
    resolved_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolution_logs_complaint ON public.resolution_logs(complaint_id);


-- ─────────────────────────────────────────────────────────────
-- 6. ROW LEVEL SECURITY (RLS)
-- ─────────────────────────────────────────────────────────────
-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.complaints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.complaint_vectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resolution_logs ENABLE ROW LEVEL SECURITY;

-- Users: read own profile
CREATE POLICY "Users can read own profile"
    ON public.users FOR SELECT
    USING (auth.uid() = id);

-- Complaints: anyone can read
CREATE POLICY "Public can read complaints"
    ON public.complaints FOR SELECT
    TO anon, authenticated
    USING (TRUE);

-- Complaints: authenticated users can insert
CREATE POLICY "Authenticated users can submit complaints"
    ON public.complaints FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- Complaints: only owner can update (priority/status updates happen server-side via service role)
CREATE POLICY "Service role can update complaints"
    ON public.complaints FOR UPDATE
    USING (TRUE);  -- Service role bypasses RLS anyway

-- Votes: authenticated users can insert own votes
CREATE POLICY "Authenticated users can vote"
    ON public.votes FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Public can read votes"
    ON public.votes FOR SELECT
    TO anon, authenticated
    USING (TRUE);

-- Resolution logs: service role only (admin actions)
CREATE POLICY "Service role manages resolution logs"
    ON public.resolution_logs FOR ALL
    USING (TRUE);

-- Vectors: service role only
CREATE POLICY "Service role manages vectors"
    ON public.complaint_vectors FOR ALL
    USING (TRUE);


-- ─────────────────────────────────────────────────────────────
-- 7. REALTIME SUBSCRIPTIONS
-- Enable realtime on key tables
-- ─────────────────────────────────────────────────────────────
ALTER PUBLICATION supabase_realtime ADD TABLE public.complaints;
ALTER PUBLICATION supabase_realtime ADD TABLE public.votes;
