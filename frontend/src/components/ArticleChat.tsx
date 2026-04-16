"use client";

import { useState, useEffect, useRef } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  error?: boolean;
}

interface Props {
  slug: string;
}

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

export default function ArticleChat({ slug }: Props) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [focused, setFocused] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Fetch suggestions once on mount
  useEffect(() => {
    let cancelled = false;
    fetch(`/api/v1/articles/${slug}/suggestions`)
      .then((r) => (r.ok ? r.json() : { questions: [] }))
      .then((d) => {
        if (!cancelled) setSuggestions((d?.questions || []).slice(0, 5));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [slug]);

  // Auto-scroll to latest message
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || loading) return;
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      text: question,
    };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/articles/${slug}/ask`, {
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

  return (
    <section className="article-chat">
      {/* Header */}
      <div className="article-chat__header">
        <KiraOrb size={36} />
        <div className="article-chat__heading">
          <div className="article-chat__title">
            <span className="article-chat__spark">✦</span>
            Задай вопрос по исследованию: KinDAR AI · Кира
          </div>
          <div className="article-chat__subtitle">
            <span className="article-chat__dot" />
            Всегда рядом · онлайн
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
            <div className="article-chat__welcome-bubble">
              Привет! 🌸 Я Кира. Задай вопрос по этой статье — или выбери подсказку ниже.
            </div>
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

      {/* Suggestion chips */}
      {suggestions.length > 0 && (
        <div className="article-chat__chips">
          {suggestions.map((q) => (
            <button
              key={q}
              type="button"
              className="article-chat__chip"
              onClick={() => send(q)}
              disabled={loading}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="article-chat__input-row">
        <input
          type="text"
          className="article-chat__input"
          value={input}
          placeholder="Спроси Киру..."
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
