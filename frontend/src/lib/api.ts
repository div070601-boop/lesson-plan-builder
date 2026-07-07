/* ============================================================
   API Client — Typed fetch wrappers for the FastAPI backend
   ============================================================ */

import type {
  Brief,
  BriefMessageResponse,
  BriefData,
  GenerationResult,
  GenerationProgress,
  HistoryListResponse,
  HistoryEntry,
  Deck,
  LibraryProfile,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ---- Helpers ----

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

// ---- Briefing ----

export async function sendBriefMessage(
  message: string,
  briefId?: string
): Promise<BriefMessageResponse> {
  return fetchJSON('/api/brief/message', {
    method: 'POST',
    body: JSON.stringify({ message, brief_id: briefId }),
  });
}

export async function getBrief(briefId: string): Promise<Brief> {
  return fetchJSON(`/api/brief/${briefId}`);
}

export async function confirmBrief(
  briefId: string,
  data: BriefData
): Promise<Brief> {
  return fetchJSON(`/api/brief/${briefId}/confirm`, {
    method: 'PUT',
    body: JSON.stringify({ data }),
  });
}

export async function uploadDocument(
  briefId: string,
  file: File
): Promise<{ filename: string; status: string; extracted_entities: Record<string, string> }> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/brief/${briefId}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Upload failed');
  return response.json();
}

// ---- Generation ----

export async function startGeneration(briefId: string): Promise<GenerationResult> {
  return fetchJSON('/api/generate', {
    method: 'POST',
    body: JSON.stringify({ brief_id: briefId }),
  });
}

export function streamGenerationProgress(
  generationId: string,
  onProgress: (progress: GenerationProgress) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  const eventSource = new EventSource(
    `${API_BASE}/api/generate/${generationId}/stream`
  );

  eventSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data) as GenerationProgress;
    onProgress(data);

    if (data.status === 'completed' || data.status === 'failed') {
      eventSource.close();
      onComplete();
    }
  });

  eventSource.onerror = (_event) => {
    eventSource.close();
    onError(new Error('Connection lost'));
  };

  // Return cleanup function
  return () => eventSource.close();
}

export async function getGenerationResult(generationId: string): Promise<GenerationResult> {
  return fetchJSON(`/api/generate/${generationId}/result`);
}

export function getDownloadUrl(generationId: string): string {
  return `${API_BASE}/api/generate/${generationId}/download`;
}

// ---- History ----

export async function getHistory(params?: {
  query?: string;
  client_name?: string;
  page?: number;
}): Promise<HistoryListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.query) searchParams.set('query', params.query);
  if (params?.client_name) searchParams.set('client_name', params.client_name);
  if (params?.page) searchParams.set('page', String(params.page));

  const qs = searchParams.toString();
  return fetchJSON(`/api/history${qs ? `?${qs}` : ''}`);
}

export async function getHistoryEntry(historyId: string): Promise<HistoryEntry> {
  return fetchJSON(`/api/history/${historyId}`);
}

// ---- Library ----

export async function getDecks(params?: {
  query?: string;
  client_id?: string;
  domain?: string;
  page?: number;
}): Promise<{ decks: Deck[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.query) searchParams.set('query', params.query);
  if (params?.client_id) searchParams.set('client_id', params.client_id);
  if (params?.domain) searchParams.set('domain', params.domain);
  if (params?.page) searchParams.set('page', String(params.page));

  const qs = searchParams.toString();
  return fetchJSON(`/api/library/decks${qs ? `?${qs}` : ''}`);
}

export async function getDeck(deckId: string): Promise<Deck> {
  return fetchJSON(`/api/library/decks/${deckId}`);
}

export async function getLibraryProfile(): Promise<LibraryProfile> {
  return fetchJSON('/api/library/profile');
}

// ---- Health ----

export async function healthCheck(): Promise<{ status: string; providers: Record<string, string> }> {
  return fetchJSON('/api/health');
}
