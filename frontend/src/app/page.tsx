'use client';

import { useState, useEffect, useRef } from 'react';
import styles from './page.module.css';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Stats {
  total_decks: number;
  total_generations: number;
  total_users: number;
  indexer_status: string;
}

function AnimatedCounter({ value, duration = 1200 }: { value: number; duration?: number }) {
  const [displayed, setDisplayed] = useState(0);
  const ref = useRef<number>(0);

  useEffect(() => {
    const start = ref.current;
    const diff = value - start;
    if (diff === 0) return;
    const startTime = performance.now();

    function animate(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const current = Math.round(start + diff * eased);
      setDisplayed(current);
      ref.current = current;
      if (progress < 1) requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
  }, [value, duration]);

  return <>{displayed}</>;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>({ total_decks: 3, total_generations: 0, total_users: 0, indexer_status: 'not_configured' });
  const [isOnline, setIsOnline] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [statsRes, healthRes] = await Promise.all([
          fetch(`${API_BASE}/api/admin/stats`),
          fetch(`${API_BASE}/api/health`),
        ]);
        if (statsRes.ok) {
          const data = await statsRes.json();
          setStats(data);
        }
        if (healthRes.ok) {
          setIsOnline(true);
        }
      } catch {
        // Backend not available
      }
      setIsLoading(false);
    }
    fetchStats();
  }, []);

  return (
    <div className={styles.dashboard}>
      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <h1 className={styles.heroTitle}>
            <span className={styles.heroGradient}>Lesson Plan</span>
            <br />Builder
          </h1>
          <p className={styles.heroSubtitle}>
            AI-powered content intelligence from your existing library. 
            Brief it like a colleague, get a fully branded PPTX.
          </p>
          <Link href="/brief" className={`btn btn-primary btn-lg ${styles.heroCta}`}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Start New Brief
          </Link>
        </div>
        <div className={styles.heroVisual}>
          <div className={styles.orb1} />
          <div className={styles.orb2} />
          <div className={styles.orb3} />
          <div className={styles.heroCard}>
            <div className={styles.heroCardHeader}>
              <div className={styles.dot} style={{ background: '#f87171' }} />
              <div className={styles.dot} style={{ background: '#fbbf24' }} />
              <div className={styles.dot} style={{ background: '#4ade80' }} />
            </div>
            <div className={styles.heroCardContent}>
              <div className={styles.heroLine} style={{ width: '80%' }} />
              <div className={styles.heroLine} style={{ width: '60%' }} />
              <div className={styles.heroLine} style={{ width: '90%' }} />
              <div className={styles.heroLine} style={{ width: '45%' }} />
              <div className={styles.heroLine} style={{ width: '70%' }} />
            </div>
          </div>
        </div>
      </section>

      {/* Stats Grid */}
      <section className={styles.statsGrid}>
        <div className={`glass-card ${styles.statCard}`}>
          <div className={styles.statIcon}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
          </div>
          <div className={styles.statValue}>
            {isLoading ? <span className="skeleton" style={{ width: '30px', height: '28px', display: 'inline-block' }} /> : <AnimatedCounter value={stats.total_decks || 3} />}
          </div>
          <div className={styles.statLabel}>Indexed Decks</div>
          <div className={`badge badge-info ${styles.statBadge}`}>{stats.total_decks > 0 ? 'Demo Data' : 'Empty'}</div>
        </div>

        <div className={`glass-card ${styles.statCard}`}>
          <div className={styles.statIcon} style={{ color: 'var(--accent-secondary)' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div className={styles.statValue}>
            {isLoading ? <span className="skeleton" style={{ width: '30px', height: '28px', display: 'inline-block' }} /> : <AnimatedCounter value={stats.total_generations} />}
          </div>
          <div className={styles.statLabel}>Plans Generated</div>
          <div className={`badge badge-primary ${styles.statBadge}`}>Ready</div>
        </div>

        <div className={`glass-card ${styles.statCard}`}>
          <div className={styles.statIcon} style={{ color: 'var(--accent-tertiary)' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v8M8 12h8" />
            </svg>
          </div>
          <div className={styles.statValue}>
            {isLoading ? <span className="skeleton" style={{ width: '30px', height: '28px', display: 'inline-block' }} /> : <AnimatedCounter value={4} />}
          </div>
          <div className={styles.statLabel}>Frameworks Found</div>
          <div className={`badge badge-success ${styles.statBadge}`}>Active</div>
        </div>

        <div className={`glass-card ${styles.statCard}`}>
          <div className={styles.statIcon} style={{ color: 'var(--accent-success)' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <div className={styles.statValue}>
            {isLoading ? <span className="skeleton" style={{ width: '30px', height: '28px', display: 'inline-block' }} /> : <>$0</>}
          </div>
          <div className={styles.statLabel}>Monthly Cost</div>
          <div className={`badge badge-success ${styles.statBadge}`}>Free Tier</div>
        </div>
      </section>

      {/* Backend Status */}
      {!isLoading && (
        <div className={`glass-card-static ${styles.statusBar}`}>
          <div className={styles.statusDot} style={{ background: isOnline ? 'var(--accent-success)' : 'var(--accent-warning)' }} />
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
            Backend: {isOnline ? 'Connected' : 'Offline (using demo mode)'}
          </span>
        </div>
      )}

      {/* Quick Actions */}
      <section className={styles.section}>
        <h2 className="heading-3">Quick Actions</h2>
        <div className={styles.actionsGrid}>
          <Link href="/brief" className={`glass-card ${styles.actionCard}`}>
            <div className={styles.actionIcon}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <h3 className={styles.actionTitle}>Start Briefing</h3>
            <p className={styles.actionDesc}>Brief the AI in conversation to create a new lesson plan</p>
          </Link>

          <Link href="/library" className={`glass-card ${styles.actionCard}`}>
            <div className={styles.actionIcon} style={{ background: 'rgba(92, 225, 230, 0.08)', color: 'var(--accent-secondary)' }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </div>
            <h3 className={styles.actionTitle}>Browse Library</h3>
            <p className={styles.actionDesc}>Explore indexed decks and their pedagogical analysis</p>
          </Link>

          <Link href="/history" className={`glass-card ${styles.actionCard}`}>
            <div className={styles.actionIcon} style={{ background: 'rgba(255, 107, 157, 0.08)', color: 'var(--accent-tertiary)' }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <h3 className={styles.actionTitle}>View History</h3>
            <p className={styles.actionDesc}>Search past generations and download previous outputs</p>
          </Link>
        </div>
      </section>

      {/* How It Works */}
      <section className={styles.section}>
        <h2 className="heading-3">How It Works</h2>
        <div className={styles.stepsGrid}>
          {[
            { num: '01', title: 'Brief', desc: 'Describe your lesson plan in a conversation. Upload supporting docs.' },
            { num: '02', title: 'Match', desc: 'AI searches your library for pedagogically matching decks.' },
            { num: '03', title: 'Generate', desc: 'Content is assembled using your teaching conventions and tone.' },
            { num: '04', title: 'Download', desc: 'Get a fully branded PPTX ready for review and delivery.' },
          ].map((step, i) => (
            <div key={i} className={`glass-card-static ${styles.stepCard}`}>
              <span className={styles.stepNum}>{step.num}</span>
              <h4 className={styles.stepTitle}>{step.title}</h4>
              <p className={styles.stepDesc}>{step.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
