'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import type { GenerationResult, LessonPlan } from '@/lib/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function PlanReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [plan, setPlan] = useState<LessonPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function fetchResult() {
      try {
        const res = await fetch(`${API_BASE}/api/generate/${id}/result`);
        if (!res.ok) throw new Error('Failed to load lesson plan');
        const data: GenerationResult = await res.json();
        if (data.lesson_plan) {
          setPlan(data.lesson_plan);
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }
    fetchResult();
  }, [id]);

  const handleApprove = async () => {
    if (!plan) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/generate/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lesson_plan: plan })
      });
      if (!res.ok) throw new Error('Failed to approve');
      router.push(`/generate/${id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to approve');
      setSubmitting(false);
    }
  };

  const handleModuleChange = (index: number, field: string, value: unknown) => {
    if (!plan) return;
    const newModules = [...plan.modules];
    newModules[index] = { ...newModules[index], [field]: value };
    setPlan({ ...plan, modules: newModules });
  };

  const handleOutlineChange = (moduleIndex: number, outlineIndex: number, value: string) => {
    if (!plan) return;
    const newModules = [...plan.modules];
    const newOutline = [...newModules[moduleIndex].outline];
    newOutline[outlineIndex] = value;
    newModules[moduleIndex] = { ...newModules[moduleIndex], outline: newOutline };
    setPlan({ ...plan, modules: newModules });
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingContainer}>
          <div className={styles.spinner}></div>
          <p>Loading Lesson Plan...</p>
        </div>
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div className={styles.page}>
        <div className={styles.errorContainer}>
          <h2>Oops!</h2>
          <p>{error || 'Lesson plan data is missing'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className="heading-1">Review Lesson Plan</h1>
          <p className="text-muted">Review and edit the AI-generated curriculum structure before generating the final presentation.</p>
        </div>

        <div className={styles.planEditor}>
          <div className={styles.planTitleSection}>
            <label>Course Title</label>
            <input 
              type="text" 
              className="input" 
              value={plan.title} 
              onChange={e => setPlan({...plan, title: e.target.value})}
            />
          </div>

          <div className={styles.modulesList}>
            {plan.modules.map((mod, i) => (
              <div key={i} className={`glass-card ${styles.moduleCard}`}>
                <div className={styles.moduleHeader}>
                  <h3>Module {i + 1}</h3>
                  <input 
                    type="text" 
                    className="input" 
                    value={mod.module_name}
                    onChange={e => handleModuleChange(i, 'module_name', e.target.value)}
                  />
                </div>
                
                <div className={styles.moduleBody}>
                  <div className={styles.fieldGroup}>
                    <label>Learning Objective</label>
                    <textarea 
                      className="input" 
                      value={mod.objective}
                      onChange={e => handleModuleChange(i, 'objective', e.target.value)}
                    />
                  </div>
                  
                  <div className={styles.outlineGrid}>
                    <div className={styles.fieldGroup}>
                      <label>Topics / Outline</label>
                      <ul className={styles.bulletList}>
                        {mod.outline.map((point, j) => (
                          <li key={j}>
                            <input 
                              type="text" 
                              className="input input-sm" 
                              value={point}
                              onChange={e => handleOutlineChange(i, j, e.target.value)}
                            />
                          </li>
                        ))}
                      </ul>
                    </div>
                    
                    <div className={styles.fieldGroup}>
                      <label>Expected Outcomes</label>
                      <ul className={styles.bulletList}>
                        {mod.outcomes.map((outcome, j) => (
                          <li key={j}>
                            <input 
                              type="text" 
                              className="input input-sm" 
                              value={outcome}
                              onChange={e => {
                                const newOutcomes = [...mod.outcomes];
                                newOutcomes[j] = e.target.value;
                                handleModuleChange(i, 'outcomes', newOutcomes);
                              }}
                            />
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.actions}>
          <button 
            className="btn btn-secondary" 
            onClick={() => router.push('/history')}
            disabled={submitting}
          >
            Save for Later
          </button>
          <button 
            className="btn btn-primary btn-lg" 
            onClick={handleApprove}
            disabled={submitting}
          >
            {submitting ? 'Approving...' : 'Approve & Generate Content'}
            {!submitting && (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
