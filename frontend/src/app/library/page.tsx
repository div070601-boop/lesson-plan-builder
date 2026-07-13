'use client';

import { useState, useEffect } from 'react';
import styles from './page.module.css';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface DeckItem {
  id: string;
  filename: string;
  client: string;
  tags: string[];
  slides: number;
  arc: string;
  tone: string;
  frameworks: string[];
  summary: string;
}

const MOCK_DECKS: DeckItem[] = [
  {
    id: 'deck_001',
    filename: 'Leadership_Fundamentals_ClientA.pptx',
    client: 'Client A',
    tags: ['leadership', 'management'],
    slides: 24,
    arc: 'Linear Progressive',
    tone: 'Professional Conversational',
    frameworks: ['Situational Leadership', "Bloom's Taxonomy"],
    summary: 'Comprehensive leadership deck for mid-level managers in financial services. Strong balance of theory and practical activities.',
  },
  {
    id: 'deck_002',
    filename: 'Communication_Skills_Workshop.pptx',
    client: 'Acemac Internal',
    tags: ['communication', 'soft_skills'],
    slides: 18,
    arc: 'Spiral',
    tone: 'Motivational Conversational',
    frameworks: ['Active Listening', 'Feedback Sandwich'],
    summary: 'Energetic communication workshop using spiral learning. Heavy on paired activities, ideal for in-person delivery.',
  },
  {
    id: 'deck_003',
    filename: 'Compliance_Training_Healthcare.pptx',
    client: 'Client B',
    tags: ['compliance', 'healthcare'],
    slides: 30,
    arc: 'Framework First',
    tone: 'Formal Instructional',
    frameworks: ['ADDIE', 'Regulatory Compliance'],
    summary: 'Dense compliance training for healthcare. Framework-first approach with knowledge checks after each section.',
  },
];

export default function LibraryPage() {
  const [decks, setDecks] = useState<DeckItem[]>(MOCK_DECKS);
  const [search, setSearch] = useState('');
  const [expandedDeck, setExpandedDeck] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchDecks() {
      try {
        const response = await fetch(`${API_BASE}/api/library/decks`);
        if (response.ok) {
          const data = await response.json();
          if (data.decks && data.decks.length > 0) {
            setDecks(data.decks.map((d: Record<string, unknown>) => ({
              id: d.id as string,
              filename: d.filename as string,
              client: (d.client_name as string) || 'Unknown',
              tags: (d.topic_tags as string[]) || [],
              slides: (d.slide_count as number) || 0,
              arc: (d.analysis as Record<string, unknown>)?.learning_arc as string || 'Unknown',
              tone: (d.analysis as Record<string, unknown>)?.tone_profile as string || 'Unknown',
              frameworks: (d.analysis as Record<string, unknown>)?.frameworks_and_models as string[] || [],
              summary: (d.summary as string) || '',
            })));
          }
        }
      } catch {
        // Use mock data
      }
      setIsLoading(false);
    }
    fetchDecks();
  }, []);

  const filtered = decks.filter(d =>
    d.filename.toLowerCase().includes(search.toLowerCase()) ||
    d.client.toLowerCase().includes(search.toLowerCase()) ||
    d.summary.toLowerCase().includes(search.toLowerCase()) ||
    d.tags.some(t => t.includes(search.toLowerCase()))
  );

  const isDemo = decks.some(d => d.id === 'deck_001' || d.id === 'deck_002' || d.id === 'deck_003');

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className="heading-2">Deck Library</h1>
          <p className="text-muted" style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)' }}>
            Browse indexed decks and their pedagogical analysis
          </p>
        </div>
        <span className="badge badge-info">{filtered.length} decks indexed {isLoading ? '' : (isDemo ? '(demo data)' : '(live from OneDrive)')}</span>
      </header>

      {/* Search Bar */}
      <div className={styles.searchBar}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search decks by name, client, topic, or keyword..."
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
                    <span>{deck.client}</span>
                    <span>·</span>
                    <span>{deck.slides} slides</span>
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
              </div>

              <div className={styles.deckTags}>
                {deck.frameworks.map((fw, j) => (
                  <span key={j} className="badge badge-primary">{fw}</span>
                ))}
                {deck.tags.map((tag, j) => (
                  <span key={j} className="badge badge-info">{tag}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
