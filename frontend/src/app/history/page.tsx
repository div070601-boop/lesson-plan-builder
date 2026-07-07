'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import styles from './page.module.css';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface HistoryItem {
  id: string;
  title: string;
  client: string;
  slides: number;
  branding: string;
  createdAt: string;
  status: string;
  downloadUrl?: string;
}

const DEMO_HISTORY: HistoryItem[] = [
  { id: '1', title: 'Leadership Essentials', client: 'Acme Corp', slides: 10, branding: 'Acemac Default', createdAt: '2 hours ago', status: 'ready' },
  { id: '2', title: 'Communication Skills Workshop', client: 'Client B', slides: 14, branding: 'Client', createdAt: '1 day ago', status: 'expired' },
  { id: '3', title: 'Compliance Training: Healthcare Regulations', client: 'Client C', slides: 22, branding: 'Mixed', createdAt: '3 days ago', status: 'expired' },
];

export default function HistoryPage() {
  const [search, setSearch] = useState('');
  const [history, setHistory] = useState<HistoryItem[]>(DEMO_HISTORY);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchHistory() {
      try {
        const response = await fetch(`${API_BASE}/api/history`);
        if (response.ok) {
          const data = await response.json();
          if (data.entries && data.entries.length > 0) {
            setHistory(data.entries.map((e: Record<string, unknown>) => ({
              id: e.id as string,
              title: (e.brief_summary as string) || 'Untitled',
              client: (e.client_name as string) || 'Unknown',
              slides: (e.slide_count as number) || 0,
              branding: (e.branding_mode as string) || 'Default',
              createdAt: new Date(e.created_at as string).toLocaleDateString(),
              status: (e.is_expired as boolean) ? 'expired' : 'ready',
              downloadUrl: e.download_url as string | undefined,
            })));
          }
        }
      } catch {
        // Use demo data
      }
      setIsLoading(false);
    }
    fetchHistory();
  }, []);

  const filtered = history.filter(h =>
    h.title.toLowerCase().includes(search.toLowerCase()) ||
    h.client.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className="heading-2">Generation History</h1>
          <p className="text-muted" style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)' }}>
            Browse and search past lesson plan generations
          </p>
        </div>
      </header>

      <div className={styles.searchBar}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search by title, client, or keyword..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {isLoading ? (
        <div className={styles.historyList}>
          {[1, 2, 3].map(i => (
            <div key={i} className="glass-card-static" style={{ padding: 'var(--space-6)' }}>
              <div className="skeleton" style={{ width: '50%', height: '20px', marginBottom: '10px' }} />
              <div className="skeleton" style={{ width: '30%', height: '14px' }} />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className={styles.empty}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--text-tertiary)' }}>
            <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
          </svg>
          <h3>No history yet</h3>
          <p className="text-muted">Generate your first lesson plan to see it here.</p>
          <Link href="/brief" className="btn btn-primary" style={{ marginTop: 'var(--space-4)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Start New Brief
          </Link>
        </div>
      ) : (
        <div className={styles.historyList}>
          {filtered.map((item, i) => (
            <div key={item.id} className={`glass-card ${styles.historyCard}`} style={{ animationDelay: `${i * 0.05}s` }}>
              <div className={styles.cardMain}>
                <div className={styles.cardIcon}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
                  </svg>
                </div>
                <div className={styles.cardInfo}>
                  <h3 className={styles.cardTitle}>{item.title}</h3>
                  <div className={styles.cardMeta}>
                    <span>{item.client}</span>
                    <span>·</span>
                    <span>{item.slides} slides</span>
                    <span>·</span>
                    <span>{item.createdAt}</span>
                  </div>
                </div>
                <div className={styles.cardActions}>
                  <span className={`badge ${item.status === 'ready' ? 'badge-success' : 'badge-warning'}`}>
                    {item.status === 'ready' ? 'Available' : 'Expired'}
                  </span>
                  <span className={`badge badge-primary`}>{item.branding}</span>
                  {item.status === 'ready' && item.downloadUrl && (
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => window.open(`${API_BASE}${item.downloadUrl}`, '_blank')}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
