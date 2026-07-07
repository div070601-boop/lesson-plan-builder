/* ============================================================
   Shared TypeScript Types — Mirrors backend Pydantic models
   ============================================================ */

// ---- Enums ----

export type BrandingMode = 'client' | 'acemac_default' | 'mixed';
export type SessionFormat = 'in_person' | 'virtual' | 'hybrid';
export type AudienceLevel = 'introductory' | 'intermediate' | 'advanced';

export type SlideType =
  | 'title'
  | 'objectives'
  | 'content'
  | 'activity'
  | 'quiz'
  | 'summary'
  | 'transition'
  | 'agenda';

export type GenerationStatus =
  | 'queued'
  | 'retrieving'
  | 'synthesizing'
  | 'planning_lesson'
  | 'lesson_plan_review'
  | 'planning_slides'
  | 'planning'
  | 'generating'
  | 'assembling'
  | 'completed'
  | 'failed';

// ---- Brief ----

export interface BriefData {
  client_name?: string;
  client_industry?: string;
  target_audience?: string;
  audience_seniority?: string;
  audience_function?: string;
  prior_knowledge_level?: AudienceLevel;
  learning_objectives: string[];
  session_duration?: string;
  session_format?: SessionFormat;
  is_standalone?: boolean;
  branding_mode?: BrandingMode;
  reference_deck_id?: string;
  additional_context?: string;
}

export interface BriefMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  attachments: string[];
}

export interface Brief {
  id: string;
  user_id?: string;
  status: string;
  messages: BriefMessage[];
  data: BriefData;
  uploaded_files: string[];
  created_at: string;
  updated_at: string;
}

export interface BriefMessageResponse {
  brief_id: string;
  message: BriefMessage;
  brief_data: BriefData;
  is_complete: boolean;
  completion_percentage: number;
}

// ---- Generation ----

export interface LessonPlanModule {
  module_name: string;
  objective: string;
  outline: string[];
  outcomes: string[];
}

export interface LessonPlan {
  title: string;
  modules: LessonPlanModule[];
}

export interface SlideContent {
  index: number;
  slide_type: SlideType;
  title: string;
  body: string[];
  speaker_notes?: string;
  activity_instructions?: string;
  estimated_duration?: string;
}

export interface SlidePlan {
  index: number;
  slide_type: SlideType;
  content_directive: string;
  source_deck_refs: string[];
}

export interface TeachingContext {
  dominant_learning_arc?: string;
  appropriate_tone?: string;
  knowledge_level?: string;
  relevant_frameworks: string[];
  activity_conventions: string[];
  industry_language_patterns: string[];
  library_profile_summary?: string;
}

export interface GenerationProgress {
  generation_id: string;
  status: GenerationStatus;
  current_step: string;
  current_slide?: number;
  total_slides?: number;
  slides_completed: SlideContent[];
  message: string;
  progress_percentage: number;
}

export interface GenerationResult {
  id: string;
  brief_id: string;
  status: GenerationStatus;
  lesson_plan?: LessonPlan;
  slides: SlideContent[];
  slide_plan: SlidePlan[];
  teaching_context?: TeachingContext;
  branding_mode?: string;
  source_decks: string[];
  download_url?: string;
  models_used: string[];
  created_at: string;
  expires_at?: string;
}

// ---- Deck ----

export interface DeckAnalysis {
  learning_arc?: string;
  tone_profile?: string;
  assumed_knowledge_level?: string;
  frameworks_and_models: string[];
  activity_design?: string;
  client_industry_signals?: string;
  content_domain_tags: string[];
  slide_type_sequence: string[];
  complexity_arc?: string;
  recurring_language_patterns: string[];
}

export interface Deck {
  id: string;
  filename: string;
  client_id?: string;
  client_name?: string;
  topic_tags: string[];
  slide_count: number;
  analysis?: DeckAnalysis;
  summary?: string;
  master_template_ref?: string;
  onedrive_path?: string;
  indexed_at?: string;
  analyzed_at?: string;
  last_modified?: string;
}

export interface LibraryProfile {
  common_slide_sequences: string[];
  frequent_frameworks: string[];
  tone_by_industry: Record<string, string>;
  activity_by_format: Record<string, string[]>;
  total_decks_analyzed: number;
  last_updated?: string;
}

// ---- History ----

export interface HistoryEntry {
  id: string;
  user_id?: string;
  user_name?: string;
  brief_summary: string;
  client_name?: string;
  client_id?: string;
  generation_id: string;
  slide_count: number;
  branding_mode?: string;
  source_decks: string[];
  models_used: string[];
  download_url?: string;
  is_expired: boolean;
  created_at: string;
  expires_at?: string;
}

export interface HistoryListResponse {
  entries: HistoryEntry[];
  total: number;
  page: number;
  per_page: number;
}
