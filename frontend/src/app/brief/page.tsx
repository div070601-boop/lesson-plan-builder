'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import type { BriefMessage, BriefData } from '@/lib/types';

const INITIAL_MESSAGE: BriefMessage = {
  id: 'welcome',
  role: 'assistant',
  content: "👋 Hi! I'm here to help you build a new lesson plan. Let's start with a quick briefing — I'll ask you a few questions, and you can answer in plain language.\n\nLet's start: **Which client is this for? And what industry or niche are they in?**",
  timestamp: new Date().toISOString(),
  attachments: [],
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const generateId = () => Date.now().toString();
const getTimestamp = () => new Date().toISOString();

export default function BriefPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<BriefMessage[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [briefId, setBriefId] = useState<string | null>(null);
  const [_briefData, setBriefData] = useState<BriefData>({ learning_objectives: [] });
  const [completionPct, setCompletionPct] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: BriefMessage = {
      id: generateId(),
      role: 'user',
      content: input.trim(),
      timestamp: getTimestamp(),
      attachments: [],
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/brief/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage.content, brief_id: briefId }),
      });

      if (response.ok) {
        const data = await response.json();
        setBriefId(data.brief_id);
        setBriefData(data.brief_data);
        setCompletionPct(data.completion_percentage);
        setMessages(prev => [...prev, data.message]);

        if (data.is_complete) {
          setTimeout(() => {
            router.push(`/brief/review?id=${data.brief_id}`);
          }, 1500);
        }
      } else {
        // Fallback: simulate AI response when backend isn't running
        simulateResponse(userMessage.content);
      }
    } catch {
      // Backend not running — simulate locally
      simulateResponse(userMessage.content);
    }

    setIsLoading(false);
    inputRef.current?.focus();
  };

  const simulateResponse = (_userMsg: string) => {
    const questions = [
      "Got it! Who's the **audience**? Tell me about their seniority level, function, and how much they already know about the topic.",
      "Great. What should learners **know or be able to do** after this session? Give me the key learning objectives.",
      "How will this session be delivered? **In-person, virtual, or hybrid?** And roughly how long is the session?",
      "For branding — should this use the **client's branding, Acemac's default**, or a mix of both?",
      "Anything else I should know? Any specific **frameworks, activities, or reference materials** you want to include? You can also upload documents here.",
      "✅ I have everything I need for the brief. Here's a summary of what I've captured. Please review it on the next screen and confirm when you're ready to generate.",
    ];

    const qIndex = messages.filter(m => m.role === 'user').length;
    const nextQ = questions[Math.min(qIndex, questions.length - 1)];
    const pct = Math.min(Math.round(((qIndex + 1) / 6) * 100), 100);
    setCompletionPct(pct);

    const aiMsg: BriefMessage = {
      id: `ai-${Date.now()}`,
      role: 'assistant',
      content: nextQ,
      timestamp: new Date().toISOString(),
      attachments: [],
    };

    setTimeout(() => {
      setMessages(prev => [...prev, aiMsg]);
      if (pct >= 100) {
        setTimeout(() => router.push('/brief/review'), 2000);
      }
    }, 600);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      const fileNames = files.map(f => f.name).join(', ');
      setInput(prev => prev + (prev ? '\n' : '') + `[Uploaded: ${fileNames}]`);
    }
  };

  return (
    <div
      className={styles.page}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      {/* Header */}
      <header className={styles.header}>
        <div>
          <h1 className="heading-2">New Brief</h1>
          <p className="text-muted" style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)' }}>
            Describe your lesson plan in conversation
          </p>
        </div>
        <div className={styles.progressSection}>
          <div className={styles.progressLabel}>
            <span>Completion</span>
            <span className="text-accent">{completionPct}%</span>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${completionPct}%` }} />
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <div className={styles.chatArea}>
        <div className={styles.messages}>
          {messages.map((msg, i) => (
            <div
              key={msg.id}
              className={`${styles.message} ${styles[msg.role]}`}
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <div className={styles.messageAvatar}>
                {msg.role === 'assistant' ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                )}
              </div>
              <div className={styles.messageBubble}>
                <div className={styles.messageContent} dangerouslySetInnerHTML={{ 
                  __html: msg.content
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br/>') 
                }} />
              </div>
            </div>
          ))}

          {isLoading && (
            <div className={`${styles.message} ${styles.assistant}`}>
              <div className={styles.messageAvatar}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className={styles.messageBubble}>
                <div className={styles.typingIndicator}>
                  <span /><span /><span />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className={`${styles.inputArea} ${isDragging ? styles.dragging : ''}`}>
        {isDragging && (
          <div className={styles.dropOverlay}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span>Drop files here (PDF, PPTX, DOCX)</span>
          </div>
        )}
        <div className={styles.inputWrapper}>
          <textarea
            ref={inputRef}
            className={styles.textInput}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your response..."
            rows={1}
            disabled={isLoading}
          />
          <button
            className={styles.sendButton}
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <div className={styles.inputHint}>
          Press <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for new line · Drag files to upload
        </div>
      </div>
    </div>
  );
}
