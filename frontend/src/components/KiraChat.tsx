"use client";

import { useState, useEffect, useRef } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  error?: boolean;
}

export interface KiraChatProps {
  suggestionsUrl: string;
  askUrl: string;
  title?: string;
  subtitle?: string;
  welcome?: string;
  placeholder?: string;
  /** Narrow the chat panel height — useful on a dedicated page */
  variant?: "compact" | "page";
}

const VISIBLE_SUGGESTIONS = 3;

function KiraOrb({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 80 80" aria-hidden="true">
      <defs>
        <linearGradient id={`kira-orb-${size}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#D63AA0" />
          <stop offset="100%" stopColor="#7B2FBE" />
        </linearGradient>
      </defs>
      <polygon points="40,4 76,40 40,76 4,40" fill={`url(#kira-orb-${size})`} />
      <polygon points="40,18 62,40 40,62 18,40" fill="white" opacity="0.15" />
      <circle cx="40" cy="40" r="11" fill="white" opacity="0.92" />
    </svg>
  );
}

function TypingDots() {
  return (
    <span className="kira-typing" aria-label="Кира печатает">
      <span /> <span /> <span />
    </span>
  );
}

export default function KiraChat({
  suggestionsUrl,
  askUrl,
  title = "Задай вопрос по исследованию: KinDAR AI · Кира",
  subtitle = "Всегда рядом · онлайн",
  welcome = "Привет! 🌸 Я Кира. Задай вопрос — или выбери подсказку ниже.",
  placeholder = "Спроси Киру...",
  variant = "compact",
}: KiraChatProps) {
  const [pool, setPool] = useState<string[]>([]);
  const [shown, setShown] = useState<string[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [focused, setFocused] = useState(false);
  const [regenIdx, setRegenIdx] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(suggestionsUrl)
      .then((r) => (r.ok ? r.json() : { questions: [] }))
      .then((d) => {
        if (cancelled) return;
        const qs: string[] = (d?.questions || []).slice(0, 5);
        setPool(qs);
        setShown(qs.slice(0, VISIBLE_SUGGESTIONS));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [suggestionsUrl]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  const collapseIfFirstInteraction = () => {
    if (!hasInteracted) {
      setHasInteracted(true);
      setCollapsed(true);
    }
  };

  const handleChipClick = (text: string) => {
    setInput(text);
    collapseIfFirstInteraction();
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const handleRegenerate = (idx: number) => {
    if (regenIdx !== null) return;
    const unused = pool.filter((q) => !shown.includes(q));
    if (unused.length === 0) return;
    setRegenIdx(idx);
    setTimeout(() => {
      setShown((prev) => {
        const next = [...prev];
        next[idx] = unused[Math.floor(Math.random() * unused.length)];
        return next;
      });
      setRegenIdx(null);
    }, 280);
  };

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || loading) return;
    collapseIfFirstInteraction();
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      text: question,
    };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch(askUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error("bad response");
      const data = await res.json();
      setMessages((m) => [
        ...m,
        { id: `a-${Date.now()}`, role: "assistant", text: data.answer || "" },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          text: "Не получилось ответить — попробуй ещё раз чуть позже.",
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const hasSuggestions = shown.length > 0;
  const canRegenerate = pool.length > shown.length;

  return (
    <section className={`article-chat${variant === "page" ? " article-chat--page" : ""}`}>
      {/* Header */}
      <div className="article-chat__header">
        <KiraOrb size={36} />
        <div className="article-chat__heading">
          <div className="article-chat__title">
            <span className="article-chat__spark">✦</span>
            {title}
          </div>
          <div className="article-chat__subtitle">
            <span className="article-chat__dot" />
            {subtitle}
          </div>
        </div>
      </div>

      {/* Chat area */}
      <div className="article-chat__body" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="article-chat__welcome">
            <div className="article-chat__welcome-avatar">
              <KiraOrb size={20} />
            </div>
            <div className="article-chat__welcome-bubble">{welcome}</div>
          </div>
        )}

        {messages.map((m) => (
          <div
            key={m.id}
            className={`article-chat__row article-chat__row--${m.role}`}
          >
            {m.role === "assistant" && (
              <div className="article-chat__avatar">
                <KiraOrb size={20} />
              </div>
            )}
            <div
              className={`article-chat__bubble article-chat__bubble--${m.role}${m.error ? " article-chat__bubble--error" : ""}`}
            >
              {m.text}
            </div>
          </div>
        ))}

        {loading && (
          <div className="article-chat__row article-chat__row--assistant">
            <div className="article-chat__avatar">
              <KiraOrb size={20} />
            </div>
            <div className="article-chat__bubble article-chat__bubble--assistant">
              <TypingDots />
            </div>
          </div>
        )}
      </div>

      {/* Suggestions dock — collapsible */}
      {hasSuggestions && (
        <div
          className={`kira-hints${collapsed ? " kira-hints--collapsed" : ""}`}
        >
          <button
            type="button"
            className="kira-hints__header"
            onClick={() => setCollapsed((c) => !c)}
            aria-expanded={!collapsed}
          >
            <span className="kira-hints__avatar">✨</span>
            <span className="kira-hints__meta">
              <span className="kira-hints__title">
                {collapsed ? "Кира AI — готова помочь" : "Кира AI — подсказывает:"}
              </span>
              <span className="kira-hints__subtitle">
                {collapsed
                  ? "Посмотри, какие варианты вопросов есть"
                  : "Нажми, чтобы вставить в поле ввода"}
              </span>
            </span>
            <span className="kira-hints__toggle" aria-hidden="true">
              {collapsed ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M6 6 L18 18 M18 6 L6 18" />
                </svg>
              )}
            </span>
          </button>

          {!collapsed && (
            <div className="kira-hints__body">
              {shown.map((q, i) => (
                <div key={`${q}-${i}`} className="kira-hints__row">
                  <button
                    type="button"
                    className="kira-hints__item"
                    onClick={() => handleChipClick(q)}
                    disabled={loading}
                  >
                    {q}
                  </button>
                  {canRegenerate && (
                    <button
                      type="button"
                      className="kira-hints__regen"
                      onClick={() => handleRegenerate(i)}
                      aria-label="Другой вариант"
                      disabled={regenIdx !== null}
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className={regenIdx === i ? "kira-hints__regen-icon--spinning" : ""}
                      >
                        <path d="M21 2v6h-6" />
                        <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
                        <path d="M3 22v-6h6" />
                        <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
                      </svg>
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Input */}
      <div className="article-chat__input-row">
        <input
          ref={inputRef}
          type="text"
          className="article-chat__input"
          value={input}
          placeholder={placeholder}
          onChange={(e) => setInput(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
          data-focused={focused ? "true" : "false"}
          disabled={loading}
          maxLength={500}
        />
        <button
          type="button"
          className="article-chat__send"
          onClick={() => send(input)}
          disabled={!input.trim() || loading}
          aria-label="Отправить"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path
              d="M5 12h14m0 0-6-6m6 6-6 6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </section>
  );
}
