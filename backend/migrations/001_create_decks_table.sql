-- Supabase migration: Create decks table for deck metadata cache
-- Run this in the Supabase SQL Editor: https://supabase.com/dashboard/project/qfylsqexxnpgynyhhkjx/sql/new

CREATE TABLE IF NOT EXISTS public.decks (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_size BIGINT,
    client_id TEXT,
    client_name TEXT,
    module_name TEXT,
    topic_tags JSONB DEFAULT '[]'::jsonb,
    slide_count INTEGER DEFAULT 0,
    slide_titles JSONB DEFAULT '[]'::jsonb,
    analysis JSONB,
    summary TEXT,
    onedrive_path TEXT,
    file_hash TEXT,
    indexed_at TIMESTAMPTZ,
    analyzed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS but allow service role full access
ALTER TABLE public.decks ENABLE ROW LEVEL SECURITY;

-- Allow service role (backend) to do everything
CREATE POLICY decks_service_role_all ON public.decks
    FOR ALL
    USING (true)
    WITH CHECK (true);
