'use client';

import { useState, useEffect, Suspense } from 'react';
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
        const [healthRes, providerRes] = await Promise.all([
          fetch(`${API_BASE}/api/health`),
          fetch(`${API_BASE}/api/admin/provider-status`),
        ]);

        if (healthRes.ok) {
          setHealth(await healthRes.json());
        }

        if (providerRes.ok) {
          setProviderStatus(await providerRes.json());
        } else {
          setProviderStatus({ groq: 'offline', gemini: 'offline', cerebras: 'offline' });
        }
      } catch {
        setProviderStatus({ groq: 'offline', gemini: 'offline', cerebras: 'offline' });
      }
    }
    fetchStatus();
  }, []);

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
    try {
      const response = await fetch(`${API_BASE}/api/admin/reindex`, { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        if (data.source === 'onedrive') {
          setReindexResult(`✅ OneDrive re-index complete! Found ${data.files_found} files, downloaded ${data.files_downloaded}.`);
        } else {
          setReindexResult(`✅ Local library scanned. Found ${data.files_found} files. Connect OneDrive to sync remote files.`);
        }
      } else {
        const errData = await response.json().catch(() => null);
        setReindexResult(`❌ Re-index failed: ${errData?.detail || 'Unknown error'}`);
      }
    } catch {
      setReindexResult('❌ Backend is not running.');
    }
    setIsReindexing(false);
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

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className="heading-2">Admin Panel</h1>
          <p className="text-muted" style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)' }}>
            System configuration, provider status, and diagnostics
          </p>
        </div>
        {health && (
          <span className="badge badge-success">{health.status} · v{health.version}</span>
        )}
      </header>

      {/* System Health */}
      <div className={`glass-card-static ${styles.systemStatus}`}>
        <div className={styles.statusRow}>
          <div className={styles.statusDot} style={{ background: health ? 'var(--accent-success)' : 'var(--accent-warning)' }} />
          <span>Backend</span>
          <span className={`badge ${health ? 'badge-success' : 'badge-warning'}`}>
            {health ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Provider Status */}
      <section className={styles.section}>
        <h2 className="heading-3">AI Providers</h2>
        <div className={styles.providerGrid}>
          {Object.entries(providerStatus).map(([name, status]) => (
            <div key={name} className={`glass-card ${styles.providerCard}`}>
              <div className={styles.providerHeader}>
                <div className={styles.statusDot} style={{ background: getStatusColor(status) }} />
                <span className={styles.providerName}>{name.charAt(0).toUpperCase() + name.slice(1)}</span>
                <span className={`badge ${getStatusBadge(status)}`}>{status}</span>
              </div>
              {name === 'onedrive' && status !== 'configured' ? (
                <button
                  className="btn btn-primary btn-sm"
                  style={{ marginTop: 'var(--space-3)' }}
                  onClick={async () => {
                    const res = await fetch(`${API_BASE}/api/admin/auth/onedrive/login`);
                    if (res.ok) {
                      const data = await res.json();
                      window.location.href = data.auth_url;
                    }
                  }}
                >
                  Connect OneDrive
                </button>
              ) : (
                <p className={styles.providerHint}>
                  {status === 'configured'
                    ? 'Ready to use for generation'
                    : `Add ${name.toUpperCase()}_API_KEY to backend/.env`}
                </p>
              )}
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

          <div className="glass-card-static" style={{ padding: 'var(--space-6)' }}>
            <h4 style={{ marginBottom: 'var(--space-3)', color: 'var(--text-primary)' }}>Library Re-Index</h4>
            <p className="text-muted" style={{ fontSize: 'var(--text-sm)', marginBottom: 'var(--space-4)' }}>
              Trigger a re-index of the OneDrive deck repository.
            </p>
            <button
              className="btn btn-secondary"
              onClick={handleReindex}
              disabled={isReindexing}
            >
              {isReindexing ? (
                <><span className={styles.spinner} /> Re-indexing...</>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                  </svg>
                  Trigger Re-Index
                </>
              )}
            </button>
            {reindexResult && (
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
    <Suspense fallback={<div className={styles.container}>Loading admin panel...</div>}>
      <AdminContent />
    </Suspense>
  );
}
