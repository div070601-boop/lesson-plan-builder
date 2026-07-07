'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import styles from './page.module.css';

interface ReviewField {
  key: string;
  label: string;
  value: string;
  icon: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function BriefReviewContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const briefId = searchParams.get('id');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Demo data — replaced by API data when backend is connected
  const [fields, setFields] = useState<ReviewField[]>([
    { key: 'client', label: 'Client & Industry', value: 'Acme Corp, Financial Services', icon: '🏢' },
    { key: 'audience', label: 'Target Audience', value: 'Mid-level managers, L&D function, intermediate knowledge', icon: '👥' },
    { key: 'objectives', label: 'Learning Objectives', value: 'Understand leadership principles, Apply frameworks to real scenarios, Build personal action plan', icon: '🎯' },
    { key: 'format', label: 'Session Format', value: 'In-person, 2 hours, standalone session', icon: '📋' },
    { key: 'branding', label: 'Branding Mode', value: 'Acemac Default', icon: '🎨' },
    { key: 'notes', label: 'Additional Notes', value: 'Include Situational Leadership model. Focus on practical activities.', icon: '📝' },
  ]);

  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  useEffect(() => {
    const fetchBriefData = async (id: string) => {
      try {
        const response = await fetch(`${API_BASE}/api/brief/${id}`);
        if (response.ok) {
          const brief = await response.json();
          const data = brief.data;
          setFields([
            { key: 'client', label: 'Client & Industry', value: `${data.client_name || 'Not specified'}${data.client_industry ? ', ' + data.client_industry : ''}`, icon: '🏢' },
            { key: 'audience', label: 'Target Audience', value: [data.target_audience, data.audience_seniority, data.audience_function, data.prior_knowledge_level].filter(Boolean).join(', ') || 'Not specified', icon: '👥' },
            { key: 'objectives', label: 'Learning Objectives', value: data.learning_objectives?.join(', ') || 'Not specified', icon: '🎯' },
            { key: 'format', label: 'Session Format', value: [data.session_format, data.session_duration, data.is_standalone ? 'standalone' : null].filter(Boolean).join(', ') || 'Not specified', icon: '📋' },
            { key: 'branding', label: 'Branding Mode', value: data.branding_mode || 'Acemac Default', icon: '🎨' },
            { key: 'notes', label: 'Additional Notes', value: data.additional_context || 'None', icon: '📝' },
          ]);
        }
      } catch {
        // Backend not available, use demo data
      }
      setIsLoading(false);
    };

    if (briefId) {
      fetchBriefData(briefId);
    } else {
      queueMicrotask(() => setIsLoading(false));
    }
  }, [briefId]);

  const startEdit = (field: ReviewField) => {
    setEditingField(field.key);
    setEditValue(field.value);
  };

  const saveEdit = () => {
    if (editingField) {
      setFields(prev =>
        prev.map(f => f.key === editingField ? { ...f, value: editValue } : f)
      );
      setEditingField(null);
    }
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    const useBriefId = briefId || 'demo-brief';
    
    try {
      // If we have a real brief, confirm it first
      if (briefId) {
        await fetch(`${API_BASE}/api/brief/${briefId}/confirm`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            data: {
              client_name: fields.find(f => f.key === 'client')?.value.split(',')[0].trim(),
              learning_objectives: fields.find(f => f.key === 'objectives')?.value.split(',').map(s => s.trim()) || [],
              branding_mode: fields.find(f => f.key === 'branding')?.value.toLowerCase().includes('client') ? 'client' : 'acemac_default',
            }
          }),
        });
      }

      const response = await fetch(`${API_BASE}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief_id: useBriefId }),
      });

      if (response.ok) {
        const data = await response.json();
        router.push(`/generate/${data.id}`);
      } else {
        router.push('/generate/demo');
      }
    } catch {
      router.push('/generate/demo');
    }
  };

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.content}>
          <div className={styles.titleSection}>
            <div className="skeleton" style={{ width: '300px', height: '32px', marginBottom: '12px' }} />
            <div className="skeleton" style={{ width: '500px', height: '20px' }} />
          </div>
          <div className={styles.fieldsGrid}>
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="glass-card-static" style={{ padding: 'var(--space-6)' }}>
                <div className="skeleton" style={{ width: '40%', height: '16px', marginBottom: '12px' }} />
                <div className="skeleton" style={{ width: '80%', height: '20px' }} />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <button className="btn btn-ghost" onClick={() => router.push('/brief')}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          Back to Chat
        </button>
        <span className="badge badge-warning">Review Required</span>
      </header>

      <div className={styles.content}>
        <div className={styles.titleSection}>
          <h1 className="heading-2">Review Your Brief</h1>
          <p className="text-muted" style={{ maxWidth: '600px', marginTop: 'var(--space-2)' }}>
            Confirm the details below before generation begins. Click any field to edit it inline.
          </p>
        </div>

        <div className={styles.fieldsGrid}>
          {fields.map((field, i) => (
            <div
              key={field.key}
              className={`glass-card ${styles.fieldCard} ${editingField === field.key ? styles.editing : ''}`}
              style={{ animationDelay: `${i * 0.05}s` }}
              onClick={() => !editingField && startEdit(field)}
            >
              <div className={styles.fieldHeader}>
                <span className={styles.fieldIcon}>{field.icon}</span>
                <span className={styles.fieldLabel}>{field.label}</span>
                {editingField === field.key ? (
                  <button className="btn btn-sm btn-primary" onClick={(e) => { e.stopPropagation(); saveEdit(); }}>
                    Save
                  </button>
                ) : (
                  <button className={`btn btn-sm btn-ghost ${styles.editBtn}`} onClick={(e) => { e.stopPropagation(); startEdit(field); }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                  </button>
                )}
              </div>
              {editingField === field.key ? (
                <textarea
                  className={styles.editTextarea}
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  autoFocus
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); saveEdit(); }}}
                />
              ) : (
                <p className={styles.fieldValue}>{field.value}</p>
              )}
            </div>
          ))}
        </div>

        <div className={styles.actions}>
          <button
            className="btn btn-primary btn-lg"
            onClick={handleGenerate}
            disabled={isGenerating}
          >
            {isGenerating ? (
              <>
                <span className={styles.spinner} />
                Starting Generation...
              </>
            ) : (
              <>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
                Generate Lesson Plan
              </>
            )}
          </button>
          <p className={styles.disclaimer}>
            Generation typically takes 30–90 seconds. You&apos;ll see slide-by-slide progress in real time.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function BriefReviewPage() {
  return (
    <Suspense fallback={<div className={styles.container}>Loading brief review...</div>}>
      <BriefReviewContent />
    </Suspense>
  );
}
