"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { buildExcerpt } from "@/lib/excerpt";

interface Article {
  id: string;
  title: string;
  slug: string;
  meta_description?: string;
  body_md?: string;
  tags: string[];
  factcheck_score: number;
  views_count: number;
  comments_count: number;
  published_at: string;
  cover_image?: string;
  author?: { name: string; slug: string; articles_count: number };
}

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (diff < 60) return "сейчас";
  if (diff < 3600) return `${Math.floor(diff / 60)}м`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}ч`;
  if (diff < 2592000) return `${Math.floor(diff / 86400)}д`;
  return date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

function authorInitials(name: string): string {
  return (name || "А").split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
}

export default function InfiniteArticles({ excludeSlug }: { excludeSlug: string }) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const loaderRef = useRef<HTMLDivElement>(null);
  const LIMIT = 5;

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/articles?limit=${LIMIT}&offset=${offset}`);
      if (res.ok) {
        const data = await res.json();
        const items: Article[] = (data.items || []).filter((a: Article) => a.slug !== excludeSlug);
        setArticles(prev => [...prev, ...items]);
        setOffset(prev => prev + LIMIT);
        if ((data.items || []).length < LIMIT) setHasMore(false);
      }
    } catch {}
    setLoading(false);
  }, [offset, loading, hasMore, excludeSlug]);

  useEffect(() => {
    loadMore();
  }, []);

  useEffect(() => {
    if (!loaderRef.current || !hasMore) return;
    const observer = new IntersectionObserver(
      entries => { if (entries[0].isIntersecting) loadMore(); },
      { threshold: 0.1 }
    );
    observer.observe(loaderRef.current);
    return () => observer.disconnect();
  }, [loadMore, hasMore]);

  if (articles.length === 0 && !loading) return null;

  return (
    <div style={{ maxWidth: 720, margin: "24px auto 0" }}>
      <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16, color: "#1A1A1A" }}>
        Другие статьи
      </h3>

      {articles.map(article => {
        const authorName = article.author?.name || "AI Автор";
        const excerpt = buildExcerpt(article.meta_description, article.body_md, 140);
        const score = article.factcheck_score || 0;
        const scoreLabel = score >= 70 ? "Проверено" : score >= 50 ? "Частично" : "Проверяется";
        const scoreCls = score >= 70 ? "good" : score >= 50 ? "mid" : "low";

        return (
          <article key={article.id} className="article-card" style={{ marginBottom: 12, cursor: "pointer" }} onClick={(e) => { if ((e.target as HTMLElement).tagName !== "A") window.location.href = "/articles/" + article.slug; }}>
            <div className="card-meta">
              <div className="card-avatar">{authorInitials(authorName)}</div>
              <span className="card-author">{authorName}</span>
              <span className="card-time">{timeAgo(article.published_at)}</span>
            </div>
            <div className="card-body">
              <div className="card-content">
                <a href={`/articles/${article.slug}`} className="card-title">{article.title}</a>
                {excerpt && <p className="card-excerpt">{excerpt}</p>}
                <div className="card-footer">
                  <div>
                    {(article.tags || []).slice(0, 2).map(tag => (
                      <a key={tag} href={`/?tag=${encodeURIComponent(tag)}`} className="card-tag">{tag}</a>
                    ))}
                  </div>
                  <div className="card-stats">
                    <span style={{display:"inline-flex",alignItems:"center",gap:"3px",fontSize:"12px",color:"#1D9BF0",fontWeight:600}}><svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="8" fill="#1D9BF0"/><path d="M5 8l2 2 4-4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg></span>
                    <span className="stat-item">&#128065; {article.views_count}</span>
                    <span className="stat-item">&#128172; {article.comments_count || 0}</span>
                  </div>
                </div>
              </div>
              {article.cover_image && (
                <div className="card-cover-wrap">
                  <img src={article.cover_image} alt={article.title} className="card-cover" />
                </div>
              )}
            </div>
          </article>
        );
      })}

      <div ref={loaderRef} style={{ textAlign: "center", padding: "20px 0" }}>
        {loading && (
          <div style={{ color: "var(--color-text-secondary)", fontSize: 14 }}>
            Загрузка...
          </div>
        )}
        {!hasMore && articles.length > 0 && (
          <div style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
            Статьи закончились, следите за обновлениями!
          </div>
        )}
      </div>
    </div>
  );
}
