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
  const ref = useRef<HTMLDivElement>(null);
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

  return (
    <div ref={ref} className="header-search" style={{ position: "relative" }}>
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

      {isOpen && (
        <div style={{
          position: "absolute", top: "100%", left: 0, right: 0,
          background: "var(--color-card)", border: "1px solid var(--color-border)",
          borderRadius: 12, marginTop: 6, boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
          zIndex: 1000, maxHeight: 400, overflowY: "auto",
        }}>
          {loading && (
            <div style={{ padding: "12px 16px", color: "var(--color-text-secondary)", fontSize: 13 }}>
              Ищем...
            </div>
          )}
          {!loading && results.length === 0 && query.length >= 2 && (
            <div style={{ padding: "12px 16px", color: "var(--color-text-secondary)", fontSize: 13 }}>
              Ничего не найдено по запросу &laquo;{query}&raquo;
            </div>
          )}
          {results.map((r) => (
            <a
              key={r.slug}
              href={`/articles/${r.slug}`}
              onClick={() => setIsOpen(false)}
              style={{
                display: "block", padding: "10px 16px", textDecoration: "none",
                borderBottom: "1px solid var(--color-border)", color: "inherit",
              }}
            >
              <div style={{ fontWeight: 600, fontSize: 14, color: "var(--color-text)", marginBottom: 3 }}>
                {r.title}
              </div>
              {r.meta_description && (
                <div style={{ fontSize: 12, color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
                  {r.meta_description.slice(0, 100)}...
                </div>
              )}
              {r.tags?.length > 0 && (
                <div style={{ marginTop: 4, display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {r.tags.slice(0, 3).map(t => (
                    <span key={t} style={{ fontSize: 10, background: "var(--color-primary)", color: "#fff", padding: "1px 6px", borderRadius: 8 }}>
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
