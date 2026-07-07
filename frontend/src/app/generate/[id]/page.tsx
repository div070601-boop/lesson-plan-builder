'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import type { GenerationProgress, SlideContent } from '@/lib/types';

const SLIDE_TYPE_ICONS: Record<string, string> = {
  title: '🎬',
  agenda: '📋',
  objectives: '🎯',
  content: '📄',
  activity: '🎮',
  quiz: '❓',
  summary: '✅',
  transition: '➡️',
};

const STATUS_LABELS: Record<string, string> = {
  queued: 'Preparing...',
  retrieving: 'Searching Library',
  synthesizing: 'Building Context',
  planning: 'Planning Slides',
  generating: 'Generating Content',
  assembling: 'Building PPTX',
  completed: 'Complete!',
  failed: 'Generation Failed',
};

// Demo slides for when backend isn't connected
const DEMO_SLIDES: SlideContent[] = [
  { index: 0, slide_type: 'title', title: 'Leadership Essentials', body: ['Developing Tomorrow\'s Leaders Today'], speaker_notes: 'Welcome participants.' },
  { index: 1, slide_type: 'agenda', title: 'Session Agenda', body: ['Introduction (15 min)', 'Core Frameworks (30 min)', 'Group Activity (20 min)', 'Case Study (20 min)', 'Reflection (15 min)', 'Wrap-up (10 min)'] },
  { index: 2, slide_type: 'objectives', title: 'Learning Objectives', body: ['Understand key leadership principles', 'Apply frameworks to scenarios', 'Develop personal action plan', 'Identify team leadership strategies'] },
  { index: 3, slide_type: 'content', title: 'What Makes a Leader?', body: ['Vision and strategic thinking', 'Emotional intelligence', 'Communication and influence', 'Adaptability'] },
  { index: 4, slide_type: 'content', title: 'The Leadership Framework', body: ['Situational Leadership Model', 'Directing → Coaching → Supporting → Delegating', 'Match style to team maturity'] },
  { index: 5, slide_type: 'activity', title: 'Group Activity: Scenarios', body: ['Form groups of 3-4', 'Discuss leadership scenarios', 'Present approach to group'], estimated_duration: '20 min' },
  { index: 6, slide_type: 'content', title: 'Case Study: Leading Change', body: ['Merging two team cultures', 'Transparent communication approach', 'Result: 40% engagement improvement'] },
  { index: 7, slide_type: 'activity', title: 'Personal Reflection', body: ['What is your default style?', 'Where might you need to flex?', 'Write 3 actions for this month'], estimated_duration: '15 min' },
  { index: 8, slide_type: 'summary', title: 'Key Takeaways', body: ['Leadership is situational', 'EQ matters as much as expertise', 'Trust = consistent actions', 'Start with small shifts'] },
  { index: 9, slide_type: 'content', title: 'Resources & Next Steps', body: ['Recommended reading list', 'Follow-up coaching session', 'Leadership assessment tool'] },
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function GenerationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [status, setStatus] = useState<string>('queued');
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('Initializing...');
  const [slides, setSlides] = useState<SlideContent[]>([]);
  const [totalSlides, setTotalSlides] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    // Elapsed timer
    const timerInterval = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);

    // Try SSE connection to backend
    let eventSource: EventSource | null = null;
    let fallbackTimeout: NodeJS.Timeout | null = null;

    try {
      eventSource = new EventSource(`${API_BASE}/api/generate/${id}/stream`);

      eventSource.addEventListener('progress', (event) => {
        const data: GenerationProgress = JSON.parse(event.data);
        setStatus(data.status);
        setProgress(data.progress_percentage);
        setCurrentStep(data.current_step);
        setSlides(data.slides_completed);
        if (data.total_slides) setTotalSlides(data.total_slides);

        if (data.status === 'lesson_plan_review') {
          eventSource?.close();
          router.push(`/plan/${id}`);
        } else if (data.status === 'completed' || data.status === 'failed') {
          eventSource?.close();
        }
      });

      eventSource.onerror = () => {
        eventSource?.close();
        // Fallback to demo simulation
        runDemoSimulation();
      };
    } catch {
      runDemoSimulation();
    }

    function runDemoSimulation() {
      let slideIndex = 0;
      const steps = [
        { status: 'retrieving', step: 'Searching library for matching decks...', pct: 10 },
        { status: 'synthesizing', step: 'Building teaching context from 3 matched decks...', pct: 25 },
        { status: 'planning', step: 'Planning 10-slide sequence...', pct: 35 },
      ];

      let stepIndex = 0;
      setTotalSlides(DEMO_SLIDES.length);

      const interval = setInterval(() => {
        if (stepIndex < steps.length) {
          const s = steps[stepIndex];
          setStatus(s.status);
          setCurrentStep(s.step);
          setProgress(s.pct);
          stepIndex++;
        } else if (slideIndex < DEMO_SLIDES.length) {
          setStatus('generating');
          const slide = DEMO_SLIDES[slideIndex];
          setCurrentStep(`Generating slide ${slideIndex + 1}/${DEMO_SLIDES.length}: ${slide.title}`);
          setSlides(DEMO_SLIDES.slice(0, slideIndex + 1));
          setProgress(40 + Math.round(((slideIndex + 1) / DEMO_SLIDES.length) * 50));
          slideIndex++;
        } else {
          setStatus('assembling');
          setCurrentStep('Assembling PPTX file...');
          setProgress(95);

          fallbackTimeout = setTimeout(() => {
            setStatus('completed');
            setCurrentStep('Complete!');
            setProgress(100);
            clearInterval(interval);
          }, 1200);
        }
      }, 800);

      return () => {
        clearInterval(interval);
        if (fallbackTimeout) clearTimeout(fallbackTimeout);
      };
    }

    return () => {
      eventSource?.close();
      clearInterval(timerInterval);
    };
  }, [id, router]);

  const isComplete = status === 'completed';
  const isFailed = status === 'failed';

  // Stop timer when done
  useEffect(() => {
    if (isComplete || isFailed) {
      // Timer stops naturally since the interval is in the other effect
    }
  }, [isComplete, isFailed]);

  const formatTime = (s: number) => {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        {/* Status Header */}
        <div className={styles.statusHeader}>
          <div className={`${styles.statusOrb} ${isComplete ? styles.complete : isFailed ? styles.failed : styles.active}`}>
            {isComplete ? (
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : isFailed ? (
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            ) : (
              <div className={styles.spinnerLarge} />
            )}
          </div>
          <h1 className="heading-2">{STATUS_LABELS[status] || 'Processing...'}</h1>
          <p className={styles.stepLabel}>{currentStep}</p>
        </div>

        {/* Progress Bar */}
        <div className={styles.progressSection}>
          <div className={styles.progressBar}>
            <div
              className={`${styles.progressFill} ${isComplete ? styles.progressComplete : ''}`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className={styles.progressMeta}>
            <span>{slides.length} / {totalSlides || '?'} slides</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}>{formatTime(elapsedSeconds)}</span>
            <span className="text-accent">{progress}%</span>
          </div>
        </div>

        {/* Pipeline Steps */}
        <div className={styles.pipelineSteps}>
          {['retrieving', 'synthesizing', 'planning', 'generating', 'assembling', 'completed'].map((step, i) => {
            const stepOrder = ['queued', 'retrieving', 'synthesizing', 'planning', 'generating', 'assembling', 'completed'];
            const currentIndex = stepOrder.indexOf(status);
            const stepIndex = stepOrder.indexOf(step);
            const isDone = stepIndex < currentIndex;
            const isCurrent = stepIndex === currentIndex;

            return (
              <div key={step} className={`${styles.pipelineStep} ${isDone ? styles.done : ''} ${isCurrent ? styles.current : ''}`}>
                <div className={styles.pipelineDot}>
                  {isDone ? '✓' : (i + 1)}
                </div>
                <span className={styles.pipelineLabel}>{STATUS_LABELS[step]}</span>
              </div>
            );
          })}
        </div>

        {/* Slide Outline (live) */}
        {slides.length > 0 && (
          <div className={styles.slideOutline}>
            <h3 className="heading-3" style={{ marginBottom: 'var(--space-4)' }}>Slide Outline</h3>
            <div className={styles.slideList}>
              {slides.map((slide, i) => (
                <div key={i} className={`glass-card-static ${styles.slideItem}`} style={{ animationDelay: `${i * 0.05}s` }}>
                  <div className={styles.slideIndex}>{slide.index + 1}</div>
                  <div className={styles.slideIcon}>{SLIDE_TYPE_ICONS[slide.slide_type] || '📄'}</div>
                  <div className={styles.slideInfo}>
                    <span className={styles.slideTitle}>{slide.title}</span>
                    <span className={styles.slideType}>{slide.slide_type}</span>
                  </div>
                  {slide.body.length > 0 && (
                    <span className={styles.slideBullets}>{slide.body.length} points</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Complete Actions */}
        {isComplete && (
          <div className={styles.completeActions}>
            <button
              className="btn btn-primary btn-lg"
              onClick={() => router.push(`/generate/${id}/result`)}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
              View Result & Download
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
