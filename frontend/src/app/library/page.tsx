'use client';

import { useState, useEffect } from 'react';
import styles from './page.module.css';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface DeckItem {
  id: string;
  filename: string;
  client: string;
  module: string;
  fileSize: number | null;
  slideTitles: string[];
  tags: string[];
  slides: number;
  arc: string;
  tone: string;
  knowledgeLevel: string;
  activityDesign: string;
  frameworks: string[];
  summary: string;
}

function formatBytes(bytes: number | null) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function LibraryPage() {
  const [decks, setDecks] = useState<DeckItem[]>([]);
  const [search, setSearch] = useState('');
  const [expandedDeck, setExpandedDeck] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchDecks() {
      try {
        const response = await fetch(`${API_BASE}/api/library/decks?per_page=100`);
        if (response.ok) {
          const data = await response.json();
          if (data.decks && data.decks.length > 0) {
            setDecks(data.decks.map((d: Record<string, unknown>) => {
              const analysis = (d.analysis as Record<string, unknown>) || {};
              return {
                id: d.id as string,
                filename: d.filename as string,
                client: (d.client_name as string) || 'Acemac Corporate',
                module: (d.module_name as string) || (d.client_name as string) || 'General Module',
                fileSize: (d.file_size as number) || null,
                slideTitles: (d.slide_titles as string[]) || [],
                tags: (d.topic_tags as string[]) || [],
                slides: (d.slide_count as number) || 0,
                arc: (analysis.learning_arc as string) || 'Unknown',
                tone: (analysis.tone_profile as string) || 'Unknown',
                knowledgeLevel: (analysis.assumed_knowledge_level as string) || 'Intermediate',
                activityDesign: (analysis.activity_design as string) || '',
                frameworks: (analysis.frameworks_and_models as string[]) || [],
                summary: (d.summary as string) || '',
              };
            }));
          }
        }
      } catch {
        // Leave empty on network error
      }
      setIsLoading(false);
    }
    fetchDecks();
  }, []);

  const filtered = decks.filter(d =>
    d.filename.toLowerCase().includes(search.toLowerCase()) ||
    d.client.toLowerCase().includes(search.toLowerCase()) ||
    d.module.toLowerCase().includes(search.toLowerCase()) ||
    d.summary.toLowerCase().includes(search.toLowerCase()) ||
    d.tags.some(t => t.includes(search.toLowerCase())) ||
    d.slideTitles.some(t => t.toLowerCase().includes(search.toLowerCase()))
  );

  const isDemo = decks.some(d => d.id === 'deck_001' || d.id === 'deck_002' || d.id === 'deck_003');

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className="heading-2">Deck Library</h1>
          <p className="text-muted" style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)' }}>
            Browse indexed presentation decks and deep pedagogical analysis
          </p>
        </div>
        <span className="badge badge-info">
          {filtered.length} decks indexed {isLoading ? '' : (isDemo ? '(demo data)' : '(live from OneDrive)')}
        </span>
      </header>

      {/* Search Bar */}
      <div className={styles.searchBar}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search decks by name, module, slide title, framework, or keyword..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {isLoading ? (
        <div className={styles.deckGrid}>
          {[1, 2, 3].map(i => (
            <div key={i} className="glass-card-static" style={{ padding: 'var(--space-6)' }}>
              <div className="skeleton" style={{ width: '60%', height: '20px', marginBottom: '10px' }} />
              <div className="skeleton" style={{ width: '40%', height: '14px', marginBottom: '16px' }} />
              <div className="skeleton" style={{ width: '100%', height: '40px' }} />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass-card-static" style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
          <h3 style={{ marginBottom: 'var(--space-2)' }}>No decks indexed yet</h3>
          <p className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>
            Go to the Admin Panel and click &quot;Trigger Re-Index&quot; to crawl and analyze presentation decks from your OneDrive repository.
          </p>
        </div>
      ) : (
        <div className={styles.deckGrid}>
          {filtered.map((deck, i) => (
            <div
              key={deck.id}
              className={`glass-card ${styles.deckCard} ${expandedDeck === deck.id ? styles.expanded : ''}`}
              style={{ animationDelay: `${i * 0.08}s` }}
              onClick={() => setExpandedDeck(expandedDeck === deck.id ? null : deck.id)}
            >
              <div className={styles.deckHeader}>
                <div className={styles.deckIcon}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="8" y1="21" x2="16" y2="21" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="12" y1="17" x2="12" y2="21" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div className={styles.deckMeta}>
                  <h3 className={styles.deckTitle}>{deck.filename}</h3>
                  <div className={styles.deckSubMeta}>
                    <span style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>{deck.module}</span>
                    <span>·</span>
                    <span>{deck.slides} slides</span>
                    {deck.fileSize && (
                      <>
                        <span>·</span>
                        <span>{formatBytes(deck.fileSize)}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <p className={styles.deckSummary}>{deck.summary}</p>

              <div className={styles.deckAnalysis}>
                <div className={styles.analysisPill}>
                  <span className={styles.pillLabel}>Arc</span>
                  <span className={styles.pillValue}>{deck.arc}</span>
                </div>
                <div className={styles.analysisPill}>
                  <span className={styles.pillLabel}>Tone</span>
                  <span className={styles.pillValue}>{deck.tone}</span>
                </div>
                <div className={styles.analysisPill}>
                  <span className={styles.pillLabel}>Level</span>
                  <span className={styles.pillValue}>{deck.knowledgeLevel}</span>
                </div>
              </div>

              <div className={styles.deckTags}>
                {deck.frameworks.map((fw, j) => (
                  <span key={j} className="badge badge-primary">{fw}</span>
                ))}
                {deck.tags.map((tag, j) => (
                  <span key={j} className="badge badge-info">{tag}</span>
                ))}
              </div>

              {expandedDeck === deck.id && (
                <div className={styles.deckExpandedDetails} onClick={(e) => e.stopPropagation()}>
                  {deck.slideTitles && deck.slideTitles.length > 0 && (
                    <div>
                      <div className={styles.expandedSectionHeader}>📑 Key Slide Titles Extracted ({deck.slideTitles.length})</div>
                      <ul className={styles.slideTitlesList}>
                        {deck.slideTitles.slice(0, 7).map((t, idx) => (
                          <li key={idx} className={styles.slideTitleItem}>{t}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {deck.activityDesign && (
                    <div>
                      <div className={styles.expandedSectionHeader}>🎯 Pedagogical Activity Design</div>
                      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
                        {deck.activityDesign}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
