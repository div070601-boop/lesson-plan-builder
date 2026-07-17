'use client';

import { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import styles from './page.module.css';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ProviderStatus {
  [key: string]: string;
}

interface SystemHealth {
  status: string;
  version: string;
  uptime?: string;
}

interface IndexProgress {
  status: 'idle' | 'crawling' | 'downloading' | 'analyzing' | 'done' | 'error';
  total_remote: number;
  crawled: number;
  downloaded: number;
  analyzed: number;
  cached_hits: number;
  current_file: string;
  started_at: string | null;
  finished_at: string | null;
  errors: string[];
}

function AdminContent() {
  const searchParams = useSearchParams();
  const [providerStatus, setProviderStatus] = useState<ProviderStatus>({
    groq: 'checking...', gemini: 'checking...', cerebras: 'checking...',
  });
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [isTestRunning, setIsTestRunning] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [reindexResult, setReindexResult] = useState<string | null>(null);
  const [libraryCount, setLibraryCount] = useState<number | null>(null);
  const [indexProgress, setIndexProgress] = useState<IndexProgress | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Check for OneDrive callback query params
  useEffect(() => {
    const onedriveStatus = searchParams.get('onedrive');
    if (onedriveStatus === 'connected') {
      queueMicrotask(() => setReindexResult('✅ OneDrive connected successfully! Click "Trigger Re-Index" to sync your files.'));
    } else if (onedriveStatus === 'error') {
      const msg = searchParams.get('msg') || 'Unknown error';
      queueMicrotask(() => setReindexResult(`❌ OneDrive connection failed: ${msg}`));
    }
  }, [searchParams]);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const [healthRes, providerRes, statsRes] = await Promise.all([
          fetch(`${API_BASE}/api/health`),
          fetch(`${API_BASE}/api/admin/provider-status`),
          fetch(`${API_BASE}/api/admin/stats`),
        ]);

        if (healthRes.ok) {
          setHealth(await healthRes.json());
        }

        if (providerRes.ok) {
          setProviderStatus(await providerRes.json());
        } else {
          setProviderStatus({ groq: 'offline', gemini: 'offline', cerebras: 'offline' });
        }

        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setLibraryCount(statsData.total_decks ?? statsData.library?.total_files ?? 0);
          // If there's an active index, start polling
          if (statsData.index_progress && ['crawling', 'downloading', 'analyzing'].includes(statsData.index_progress.status)) {
            setIndexProgress(statsData.index_progress);
            setIsReindexing(true);
            startPolling();
          }
        }
      } catch {
        setProviderStatus({ groq: 'offline', gemini: 'offline', cerebras: 'offline' });
      }
    }
    fetchStatus();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchProgress = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/index-progress`);
      if (res.ok) {
        const data: IndexProgress = await res.json();
        setIndexProgress(data);

        if (data.status === 'done' || data.status === 'error') {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
          setIsReindexing(false);
          // Refresh stats
          const statsRes = await fetch(`${API_BASE}/api/admin/stats`);
          if (statsRes.ok) {
            const statsData = await statsRes.json();
            setLibraryCount(statsData.total_decks ?? 0);
          }
        }
      }
    } catch { /* ignore poll errors */ }
  }, []);

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(fetchProgress, 2000);
  }, [fetchProgress]);

  const handleTestProvider = async () => {
    setIsTestRunning(true);
    setTestResult(null);
    try {
      const response = await fetch(`${API_BASE}/api/admin/test-provider`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: 'Respond with: Hello from Lesson Plan Builder! Include the model name you are.' }),
      });
      if (response.ok) {
        const data = await response.json();
        setTestResult(`✅ ${data.model}: "${data.response}"`);
      } else {
        const errData = await response.json().catch(() => null);
        setTestResult(`❌ Provider error: ${errData?.detail || 'No configured providers responded.'}`);
      }
    } catch {
      setTestResult('❌ Backend is not running. Start it with: cd backend && uvicorn main:app --reload');
    }
    setIsTestRunning(false);
  };

  const handleReindex = async () => {
    setIsReindexing(true);
    setReindexResult(null);
    setIndexProgress(null);
    try {
      const response = await fetch(`${API_BASE}/api/admin/reindex`, { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        if (data.files_found !== undefined) {
          setLibraryCount(data.files_found);
        }
        setReindexResult(data.message || '✅ Re-index started!');
        // Start polling for progress
        startPolling();
      } else {
        const errData = await response.json().catch(() => null);
        setReindexResult(`❌ Re-index failed: ${errData?.detail || 'Unknown error'}`);
        setIsReindexing(false);
      }
    } catch {
      setReindexResult('❌ Backend is not running.');
      setIsReindexing(false);
    }
  };

  const getStatusColor = (status: string) => {
    if (status === 'configured' || status === 'ok') return 'var(--accent-success)';
    if (status === 'checking...') return 'var(--accent-warning)';
    return 'var(--accent-error, #f87171)';
  };

  const getStatusBadge = (status: string) => {
    if (status === 'configured') return 'badge-success';
    if (status === 'checking...') return 'badge-warning';
    return 'badge-warning';
  };

  // Progress ring helpers
  const progressTotal = indexProgress ? indexProgress.total_remote : 0;
  const progressDone = indexProgress ? (indexProgress.downloaded + indexProgress.cached_hits) : 0;
  const progressPct = progressTotal > 0 ? Math.round((progressDone / progressTotal) * 100) : 0;
  const isActive = indexProgress && ['crawling', 'downloading', 'analyzing'].includes(indexProgress.status);

  const getProgressLabel = () => {
    if (!indexProgress) return '';
    switch (indexProgress.status) {
      case 'crawling': return 'Scanning OneDrive...';
      case 'downloading': return `Downloading ${indexProgress.downloaded}/${indexProgress.total_remote}`;
      case 'analyzing': return `Analyzing ${indexProgress.analyzed}/${indexProgress.total_remote}`;
      case 'done': return `✅ Complete! ${indexProgress.downloaded} new, ${indexProgress.cached_hits} cached`;
      case 'error': return `❌ Error — ${indexProgress.errors.length} failures`;
      default: return 'Idle';
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className="heading-2">Admin Panel</h1>
          <p className="text-muted" style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)' }}>
            System configuration and diagnostics
          </p>
        </div>
        <div className={styles.statusRow}>
          <div className={styles.statusDot} style={{ backgroundColor: health ? 'var(--accent-success)' : 'var(--accent-warning)' }} />
          <span>{health ? `v${health.version} — Healthy` : 'Connecting...'}</span>
        </div>
      </header>

      {/* Provider Status */}
      <section className={styles.section}>
        <h2 className="heading-3">AI Providers</h2>
        <div className={styles.providerGrid}>
          {Object.entries(providerStatus).filter(([key]) => key !== 'onedrive').map(([provider, status]) => (
            <div key={provider} className="glass-card-static" style={{ padding: 'var(--space-5)' }}>
              <div className={styles.providerHeader}>
                <div className={styles.statusDot} style={{ backgroundColor: getStatusColor(status) }} />
                <span className={styles.providerName}>{provider.charAt(0).toUpperCase() + provider.slice(1)}</span>
                <span className={`badge ${getStatusBadge(status)}`}>{status}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Diagnostics */}
      <section className={styles.section}>
        <h2 className="heading-3">Diagnostics</h2>
        <div className={styles.diagnosticsGrid}>
          <div className="glass-card-static" style={{ padding: 'var(--space-6)' }}>
            <h4 style={{ marginBottom: 'var(--space-3)', color: 'var(--text-primary)' }}>Test Provider Connection</h4>
            <p className="text-muted" style={{ fontSize: 'var(--text-sm)', marginBottom: 'var(--space-4)' }}>
              Send a test prompt to verify AI providers are working correctly.
            </p>
            <button
              className="btn btn-primary"
              onClick={handleTestProvider}
              disabled={isTestRunning}
            >
              {isTestRunning ? (
                <><span className={styles.spinner} /> Testing...</>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                  </svg>
                  Test Provider
                </>
              )}
            </button>
            {testResult && (
              <div className={styles.testResult}>{testResult}</div>
            )}
          </div>

          {/* Library Re-Index Card with Progress */}
          <div className="glass-card-static" style={{ padding: 'var(--space-6)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
              <h4 style={{ color: 'var(--text-primary)', margin: 0 }}>Library Re-Index</h4>
              {libraryCount !== null && (
                <span className="badge badge-success" style={{ fontSize: '12px', fontWeight: 600 }}>
                  📦 {libraryCount} Decks
                </span>
              )}
            </div>
            <p className="text-muted" style={{ fontSize: 'var(--text-sm)', marginBottom: 'var(--space-4)' }}>
              Sync OneDrive presentations into local library with content analysis.
            </p>
            <button
              className="btn btn-secondary"
              onClick={handleReindex}
              disabled={isReindexing}
            >
              {isReindexing ? (
                <><span className={styles.spinner} /> Indexing...</>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                  </svg>
                  Trigger Re-Index
                </>
              )}
            </button>

            {/* Live Progress Wheel */}
            {(isActive || indexProgress?.status === 'done' || indexProgress?.status === 'error') && (
              <div className={styles.progressContainer}>
                <div className={styles.progressRing}>
                  <svg viewBox="0 0 80 80" className={styles.progressSvg}>
                    <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(124, 92, 252, 0.1)" strokeWidth="6" />
                    <circle
                      cx="40" cy="40" r="34"
                      fill="none"
                      stroke={indexProgress?.status === 'error' ? 'var(--accent-error, #f87171)' : indexProgress?.status === 'done' ? 'var(--accent-success)' : 'var(--accent-primary)'}
                      strokeWidth="6"
                      strokeLinecap="round"
                      strokeDasharray={`${2 * Math.PI * 34}`}
                      strokeDashoffset={`${2 * Math.PI * 34 * (1 - progressPct / 100)}`}
                      className={isActive ? styles.progressCircleAnimated : ''}
                      transform="rotate(-90 40 40)"
                    />
                  </svg>
                  <div className={styles.progressPct}>
                    {indexProgress?.status === 'crawling' ? (
                      <span className={styles.spinner} style={{ width: 18, height: 18 }} />
                    ) : (
                      <span>{progressPct}%</span>
                    )}
                  </div>
                </div>
                <div className={styles.progressDetails}>
                  <span className={styles.progressLabel}>{getProgressLabel()}</span>
                  {indexProgress?.current_file && isActive && (
                    <span className={styles.progressFile}>📄 {indexProgress.current_file}</span>
                  )}
                  {indexProgress && (
                    <div className={styles.progressStats}>
                      {indexProgress.downloaded > 0 && <span>🆕 {indexProgress.downloaded} new</span>}
                      {indexProgress.cached_hits > 0 && <span>⚡ {indexProgress.cached_hits} cached</span>}
                      {indexProgress.analyzed > 0 && <span>🔍 {indexProgress.analyzed} analyzed</span>}
                      {indexProgress.errors.length > 0 && <span>⚠️ {indexProgress.errors.length} errors</span>}
                    </div>
                  )}
                </div>
              </div>
            )}

            {reindexResult && !isActive && (
              <div className={styles.testResult}>{reindexResult}</div>
            )}
          </div>
        </div>
      </section>

      {/* Configuration — derive from live data */}
      <section className={styles.section}>
        <h2 className="heading-3">Configuration</h2>
        <div className="glass-card-static" style={{ padding: 'var(--space-6)' }}>
          <div className={styles.configGrid}>
            <div className={styles.configItem}>
              <span className={styles.configLabel}>Output Expiry</span>
              <span className={styles.configValue}>48 hours</span>
            </div>
            <div className={styles.configItem}>
              <span className={styles.configLabel}>Max Slides</span>
              <span className={styles.configValue}>40</span>
            </div>
            <div className={styles.configItem}>
              <span className={styles.configLabel}>Supabase</span>
              <span className={`badge ${health ? 'badge-success' : 'badge-warning'}`}>
                {health ? 'Connected' : 'Not Connected'}
              </span>
            </div>
            <div className={styles.configItem}>
              <span className={styles.configLabel}>OneDrive</span>
              <span className={`badge ${providerStatus.onedrive === 'configured' ? 'badge-success' : 'badge-warning'}`}>
                {providerStatus.onedrive === 'configured' ? 'Connected' : 'Not Connected'}
              </span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function AdminPage() {
  return (
    <Suspense fallback={<div style={{ padding: 'var(--space-8)', textAlign: 'center' }}>Loading admin panel...</div>}>
      <AdminContent />
    </Suspense>
  );
}
