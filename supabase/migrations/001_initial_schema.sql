-- Lesson Plan Builder — Initial Database Schema
-- Supabase (Postgres + pgvector)
-- Run this migration after setting up your Supabase project.

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- USERS (linked to Supabase Auth)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_id UUID UNIQUE, -- Supabase Auth user ID
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'member', -- 'member' | 'lead' | 'admin'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- BRIEFS (conversational briefing state)
-- ============================================================
CREATE TABLE IF NOT EXISTS briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'in_progress', -- in_progress | review | confirmed | generating | completed
    data JSONB NOT NULL DEFAULT '{}', -- BriefData JSON
    messages JSONB NOT NULL DEFAULT '[]', -- Array of BriefMessage
    uploaded_files TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_briefs_user ON briefs(user_id);
CREATE INDEX idx_briefs_status ON briefs(status);

-- ============================================================
-- DECKS (indexed from OneDrive repository)
-- ============================================================
CREATE TABLE IF NOT EXISTS decks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    client_id TEXT, -- For data isolation: 'client_a', 'acemac_internal', etc.
    client_name TEXT,
    topic_tags TEXT[] DEFAULT '{}',
    slide_count INTEGER DEFAULT 0,
    analysis JSONB, -- Full DeckAnalysis JSON (10 pedagogical fields)
    summary TEXT, -- 150-200 word natural language summary
    master_template_ref TEXT,
    onedrive_path TEXT,
    onedrive_item_id TEXT,
    last_modified TIMESTAMPTZ,
    indexed_at TIMESTAMPTZ DEFAULT now(),
    analyzed_at TIMESTAMPTZ
);

CREATE INDEX idx_decks_client ON decks(client_id);
CREATE INDEX idx_decks_tags ON decks USING GIN(topic_tags);

-- ============================================================
-- DECK EMBEDDINGS (pgvector for semantic search)
-- ============================================================
CREATE TABLE IF NOT EXISTS deck_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deck_id UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    slide_index INTEGER NOT NULL,
    slide_type TEXT,
    content TEXT NOT NULL, -- The text content that was embedded
    embedding vector(768), -- Gemini text-embedding-004 outputs 768 dimensions
    client_id TEXT, -- Denormalized for query-level isolation
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_embeddings_deck ON deck_embeddings(deck_id);
CREATE INDEX idx_embeddings_client ON deck_embeddings(client_id);
-- Create IVFFlat index for fast similarity search (tune lists based on row count)
-- CREATE INDEX idx_embeddings_vector ON deck_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================
-- SLIDE METADATA (structured per-slide data)
-- ============================================================
CREATE TABLE IF NOT EXISTS slide_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deck_id UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    slide_index INTEGER NOT NULL,
    slide_type TEXT, -- title | objectives | content | activity | quiz | summary | transition
    title TEXT,
    content_text TEXT,
    has_image BOOLEAN DEFAULT false,
    has_chart BOOLEAN DEFAULT false,
    layout_name TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_slides_deck ON slide_metadata(deck_id);
CREATE INDEX idx_slides_type ON slide_metadata(slide_type);

-- ============================================================
-- LIBRARY PROFILE (cross-deck intelligence)
-- ============================================================
CREATE TABLE IF NOT EXISTS library_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile JSONB NOT NULL, -- LibraryProfile JSON
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- GENERATIONS (generation runs)
-- ============================================================
CREATE TABLE IF NOT EXISTS generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_id UUID REFERENCES briefs(id),
    user_id UUID REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'queued', -- queued | retrieving | synthesizing | planning | generating | assembling | completed | failed
    lesson_plan JSONB, -- LessonPlan JSON (approved by user)
    slide_plan JSONB, -- Array of SlidePlan
    teaching_context JSONB, -- TeachingContext JSON
    branding_mode TEXT,
    source_decks TEXT[] DEFAULT '{}',
    models_used TEXT[] DEFAULT '{}',
    output_path TEXT, -- Path to generated PPTX in Supabase Storage
    download_url TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_generations_brief ON generations(brief_id);
CREATE INDEX idx_generations_user ON generations(user_id);
CREATE INDEX idx_generations_status ON generations(status);

-- ============================================================
-- SETTINGS (key-value store for OAuth tokens, config, etc.)
-- ============================================================
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT, -- Serialized data (JSON strings, tokens, etc.)
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_generations_brief ON generations(brief_id);
CREATE INDEX idx_generations_user ON generations(user_id);
CREATE INDEX idx_generations_status ON generations(status);

-- ============================================================
-- GENERATION SLIDES (per-slide content)
-- ============================================================
CREATE TABLE IF NOT EXISTS generation_slides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id UUID NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
    slide_index INTEGER NOT NULL,
    slide_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body JSONB DEFAULT '[]', -- Array of strings
    speaker_notes TEXT,
    activity_instructions TEXT,
    estimated_duration TEXT,
    source_refs JSONB DEFAULT '[]' -- Which source deck slides informed this
);

CREATE INDEX idx_gen_slides_generation ON generation_slides(generation_id);

-- ============================================================
-- HISTORY (searchable generation history)
-- ============================================================
CREATE TABLE IF NOT EXISTS history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    user_name TEXT,
    brief_summary TEXT,
    client_name TEXT,
    client_id TEXT,
    generation_id UUID REFERENCES generations(id),
    slide_count INTEGER DEFAULT 0,
    branding_mode TEXT,
    source_decks TEXT[] DEFAULT '{}',
    models_used TEXT[] DEFAULT '{}',
    download_url TEXT,
    is_expired BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX idx_history_user ON history(user_id);
CREATE INDEX idx_history_client ON history(client_name);
CREATE INDEX idx_history_created ON history(created_at DESC);

-- Full-text search on brief summary
CREATE INDEX idx_history_search ON history USING GIN(to_tsvector('english', coalesce(brief_summary, '') || ' ' || coalesce(client_name, '')));

-- ============================================================
-- ROW LEVEL SECURITY (basic policies)
-- ============================================================
-- Note: Enable RLS on each table in Supabase dashboard
-- These policies are for reference and should be customized

-- Allow authenticated users to read all history (shared across team)
-- ALTER TABLE history ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Team members can view all history" ON history FOR SELECT USING (true);
-- CREATE POLICY "Team members can insert own history" ON history FOR INSERT WITH CHECK (auth.uid() = user_id);
