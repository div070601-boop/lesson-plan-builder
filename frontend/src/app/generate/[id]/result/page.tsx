'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import type { SlideContent, GenerationResult } from '@/lib/types';

const SLIDE_TYPE_ICONS: Record<string, string> = {
  title: '🎬', agenda: '📋', objectives: '🎯', content: '📄',
  activity: '🎮', quiz: '❓', summary: '✅', transition: '➡️',
};

const DEMO_SLIDES: SlideContent[] = [
  { index: 0, slide_type: 'title', title: 'Leadership Essentials', body: ['Developing Tomorrow\'s Leaders Today'], speaker_notes: 'Welcome participants and set the tone for an interactive session.' },
  { index: 1, slide_type: 'agenda', title: 'Session Agenda', body: ['Introduction & Context (15 min)', 'Core Leadership Frameworks (30 min)', 'Group Activity: Leadership Scenarios (20 min)', 'Case Study Analysis (20 min)', 'Reflection & Action Planning (15 min)', 'Wrap-up & Resources (10 min)'], speaker_notes: 'Walk through the agenda and set expectations for the session.' },
  { index: 2, slide_type: 'objectives', title: 'Learning Objectives', body: ['Understand the key principles of effective leadership', 'Apply leadership frameworks to real-world scenarios', 'Develop a personal leadership action plan', 'Identify strategies for leading diverse teams'], speaker_notes: 'Review objectives and connect to participants\' goals.' },
  { index: 3, slide_type: 'content', title: 'What Makes a Leader?', body: ['Vision and strategic thinking', 'Emotional intelligence and empathy', 'Communication and influence', 'Adaptability in uncertain environments', 'Building trust through consistency'], speaker_notes: 'Use the iceberg model to illustrate visible vs hidden leadership qualities.' },
  { index: 4, slide_type: 'content', title: 'The Leadership Framework', body: ['Situational Leadership Model (Hersey & Blanchard)', 'Directing → Coaching → Supporting → Delegating', 'Match leadership style to team maturity', 'No single style works for every situation'], speaker_notes: 'Walk through each quadrant with examples from participants\' industries.' },
  { index: 5, slide_type: 'activity', title: 'Group Activity: Leadership Scenarios', body: ['Form groups of 3-4', 'Each group receives a leadership scenario card', 'Discuss: What leadership style would you apply?', 'Present your approach to the wider group'], speaker_notes: 'Allow 10 minutes for group discussion, 10 minutes for presentations.', activity_instructions: 'Distribute scenario cards. Monitor discussions.', estimated_duration: '20 minutes' },
  { index: 6, slide_type: 'content', title: 'Case Study: Leading Through Change', body: ['The challenge: Merging two teams with different cultures', 'Approach: Transparent communication + phased integration', 'Key lesson: Trust is built through action, not words', 'Result: 40% improvement in team engagement scores'], speaker_notes: 'Use this case study to bridge theory with practical application.' },
  { index: 7, slide_type: 'activity', title: 'Personal Reflection', body: ['What is your default leadership style?', 'In what situations does it serve you well?', 'Where might you need to flex your approach?', 'Write down 3 actions you\'ll take this month'], speaker_notes: 'Give participants 5 minutes of quiet reflection time.', estimated_duration: '15 minutes' },
  { index: 8, slide_type: 'summary', title: 'Key Takeaways', body: ['Leadership is situational — adapt your style', 'Emotional intelligence is as important as expertise', 'Trust is built through consistent actions', 'Start with small, intentional leadership shifts'], speaker_notes: 'Recap the main points and connect back to learning objectives.' },
  { index: 9, slide_type: 'content', title: 'Resources & Next Steps', body: ['Recommended reading: \'Leaders Eat Last\' by Simon Sinek', 'Follow-up coaching session available (date TBC)', 'Leadership assessment tool: link in email', 'Questions? Reach out to your L&D team'], speaker_notes: 'Share resource links and next steps for continued development.' },
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [slides, setSlides] = useState<SlideContent[]>(DEMO_SLIDES);
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [expandedSlide, setExpandedSlide] = useState<number | null>(null);
  const [copiedSlide, setCopiedSlide] = useState<number | null>(null);
  const [isBackendConnected, setIsBackendConnected] = useState(false);

  useEffect(() => {
    // Try to fetch real data from backend
    async function fetchResult() {
      try {
        const response = await fetch(`${API_BASE}/api/generate/${id}/result`);
        if (response.ok) {
          const data: GenerationResult = await response.json();
          if (data.slides && data.slides.length > 0) {
            setSlides(data.slides);
          }
          setResult(data);
          setIsBackendConnected(true);
        }
      } catch {
        // Backend not available, use demo data
      }
    }
    fetchResult();
  }, [id]);

  const handleDownload = () => {
    if (isBackendConnected) {
      window.open(`${API_BASE}/api/generate/${id}/download`, '_blank');
    } else {
      alert('PPTX download is available when the backend is running. Start the backend with: cd backend && uvicorn main:app --reload');
    }
  };

  const handleCopySlide = (slide: SlideContent, index: number) => {
    const text = [
      `Slide ${slide.index + 1}: ${slide.title}`,
      `Type: ${slide.slide_type}`,
      '',
      ...slide.body.map(b => `• ${b}`),
      ...(slide.speaker_notes ? ['', `Speaker Notes: ${slide.speaker_notes}`] : []),
      ...(slide.activity_instructions ? [`Activity Setup: ${slide.activity_instructions}`] : []),
      ...(slide.estimated_duration ? [`Duration: ${slide.estimated_duration}`] : []),
    ].join('\n');

    navigator.clipboard.writeText(text).then(() => {
      setCopiedSlide(index);
      setTimeout(() => setCopiedSlide(null), 2000);
    });
  };

  const branding = result?.branding_mode || 'Acemac Default';
  const sourceDecks = result?.source_decks?.length || 3;
  const modelUsed = result?.models_used?.[0] || 'Demo Mode';

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div>
          <h1 className="heading-2">Lesson Plan Ready</h1>
          <p className="text-muted" style={{ marginTop: 'var(--space-1)', fontSize: 'var(--text-sm)' }}>
            {slides.length} slides · {branding} branding · Generated just now
          </p>
        </div>
        <div className={styles.headerActions}>
          <button className="btn btn-secondary" onClick={() => router.push('/brief')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            New Brief
          </button>
          <button className="btn btn-primary" onClick={handleDownload}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
            </svg>
            Download PPTX
          </button>
        </div>
      </header>

      {/* Metadata Strip */}
      <div className={styles.metaStrip}>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Branding</span>
          <span className="badge badge-primary">{branding}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Source Decks</span>
          <span className="badge badge-info">{sourceDecks} matched</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Frameworks</span>
          <span className="badge badge-success">Situational Leadership</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Model</span>
          <span className={`badge ${modelUsed === 'Demo Mode' || modelUsed === 'demo_mode' ? 'badge-warning' : 'badge-success'}`}>{modelUsed}</span>
        </div>
      </div>

      {/* Slide Cards */}
      <div className={styles.slideGrid}>
        {slides.map((slide, i) => {
          const isExpanded = expandedSlide === i;
          return (
            <div
              key={i}
              className={`glass-card ${styles.slideCard} ${isExpanded ? styles.expanded : ''}`}
              style={{ animationDelay: `${i * 0.05}s` }}
              onClick={() => setExpandedSlide(isExpanded ? null : i)}
            >
              <div className={styles.slideHeader}>
                <div className={styles.slideNum}>{slide.index + 1}</div>
                <span className={styles.slideTypeIcon}>{SLIDE_TYPE_ICONS[slide.slide_type]}</span>
                <span className={styles.slideTypeBadge}>{slide.slide_type}</span>
                {slide.estimated_duration && (
                  <span className={styles.slideDuration}>⏱ {slide.estimated_duration}</span>
                )}
                <button
                  className={`btn btn-sm btn-ghost ${styles.copyBtn}`}
                  onClick={(e) => { e.stopPropagation(); handleCopySlide(slide, i); }}
                  title="Copy slide content"
                >
                  {copiedSlide === i ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-success)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                  )}
                </button>
              </div>
              <h3 className={styles.slideTitle}>{slide.title}</h3>
              <ul className={styles.slideBullets}>
                {slide.body.map((point, j) => (
                  <li key={j}>{point}</li>
                ))}
              </ul>
              {(isExpanded || slide.speaker_notes) && slide.speaker_notes && (
                <div className={styles.speakerNotes}>
                  <span className={styles.notesLabel}>Speaker Notes</span>
                  <p>{slide.speaker_notes}</p>
                </div>
              )}
              {isExpanded && slide.activity_instructions && (
                <div className={styles.speakerNotes} style={{ borderColor: 'rgba(74, 222, 128, 0.15)', background: 'rgba(74, 222, 128, 0.03)' }}>
                  <span className={styles.notesLabel} style={{ color: 'var(--accent-success)' }}>Activity Setup</span>
                  <p>{slide.activity_instructions}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
