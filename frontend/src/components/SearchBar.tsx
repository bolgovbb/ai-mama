"use client";
import { useState, useRef, useEffect } from "react";

interface SearchResult {
  title: string;
  slug: string;
  meta_description: string | null;
  tags: string[];
  factcheck_score: number | null;
}

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") { setMobileOpen(false); setIsOpen(false); } }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (mobileOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [mobileOpen]);

  const doSearch = async (q: string) => {
    if (q.length < 2) { setResults([]); setIsOpen(false); return; }
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/articles/search?q=${encodeURIComponent(q)}&limit=8`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.items || []);
        setIsOpen(true);
      }
    } catch {}
    setLoading(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(val), 300);
  };

  const closeMobile = () => { setMobileOpen(false); setIsOpen(false); };

  const resultsList = isOpen && (
    <div className="search-results">
      {loading && (
        <div className="search-results__msg">Ищем...</div>
      )}
      {!loading && results.length === 0 && query.length >= 2 && (
        <div className="search-results__msg">Ничего не найдено по запросу «{query}»</div>
      )}
      {results.map((r) => (
        <a
          key={r.slug}
          href={`/articles/${r.slug}`}
          onClick={closeMobile}
          className="search-result-item"
        >
          <div className="search-result-item__title">{r.title}</div>
          {r.meta_description && (
            <div className="search-result-item__desc">{r.meta_description.slice(0, 100)}...</div>
          )}
          {r.tags?.length > 0 && (
            <div className="search-result-item__tags">
              {r.tags.slice(0, 3).map(t => (
                <span key={t} className="search-result-item__tag">{t}</span>
              ))}
            </div>
          )}
        </a>
      ))}
    </div>
  );

  return (
    <>
      {/* Desktop inline search + mobile trigger button */}
      <div ref={ref} className="header-search">
        <input
          type="text"
          placeholder="Поиск статей..."
          value={query}
          onChange={handleChange}
          onFocus={() => results.length > 0 && setIsOpen(true)}
        />
        <svg className="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        {resultsList}
      </div>

      <button
        className="search-trigger-mobile"
        aria-label="Поиск"
        onClick={() => setMobileOpen(true)}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
      </button>

      {/* Mobile fullscreen search overlay */}
      {mobileOpen && (
        <div className="search-mobile-overlay" onClick={(e) => { if (e.target === e.currentTarget) closeMobile(); }}>
          <div className="search-mobile-panel">
            <div className="search-mobile-bar">
              <div className="search-mobile-input-wrap">
                <svg className="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                </svg>
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="Поиск статей..."
                  value={query}
                  onChange={handleChange}
                  autoFocus
                />
              </div>
              <button className="search-mobile-cancel" onClick={closeMobile} aria-label="Отмена">
                Отмена
              </button>
            </div>
            <div className="search-mobile-results">
              {loading && <div className="search-results__msg">Ищем...</div>}
              {!loading && results.length === 0 && query.length >= 2 && (
                <div className="search-results__msg">Ничего не найдено по запросу «{query}»</div>
              )}
              {!loading && query.length < 2 && (
                <div className="search-results__msg">Начните вводить, чтобы найти статьи</div>
              )}
              {results.map((r) => (
                <a key={r.slug} href={`/articles/${r.slug}`} onClick={closeMobile} className="search-result-item">
                  <div className="search-result-item__title">{r.title}</div>
                  {r.meta_description && (
                    <div className="search-result-item__desc">{r.meta_description.slice(0, 100)}...</div>
                  )}
                </a>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
