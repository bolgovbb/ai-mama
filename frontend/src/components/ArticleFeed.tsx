"use client"
import { useState, useEffect } from "react"
import DateFilter, { getPeriodDate } from "./DateFilter"

interface Author { name: string; slug: string }
interface Article {
  id: string; title: string; slug: string; published_at: string;
  body_md?: string; meta_description?: string; tags: string[];
  views_count: number; comments_count: number; reactions_count: number;
  cover_image?: string; is_verified?: boolean; author?: Author;
}

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr); const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diff < 60) return 'только что'
  if (diff < 3600) return `${Math.floor(diff / 60)}м`
  if (diff < 86400) return `${Math.floor(diff / 3600)}ч`
  if (diff < 2592000) return `${Math.floor(diff / 86400)}д`
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

function authorInitials(name: string): string {
  return (name || 'А').split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase() || 'А'
}

function VerifiedBadge() {
  return (
    <span style={{display:'inline-flex',alignItems:'center',gap:'3px',fontSize:'12px',color:'#1D9BF0',fontWeight:600}} title="Проверено экспертом">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="8" fill="#1D9BF0"/>
        <path d="M5 8l2 2 4-4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </span>
  )
}

/* ===== Compact headline row (vc.ru style) ===== */
function HeadlineRow({ article }: { article: Article }) {
  return (
    <a href={`/articles/${article.slug}`} className="headline-row">
      <span className="headline-title">{article.title}</span>
      <span className="headline-stats">
        <span className="headline-stat" title="Просмотры">👁 {article.views_count}</span>
        <span className="headline-stat" title="Комментарии">💬 {article.comments_count || 0}</span>
      </span>
    </a>
  )
}

/* ===== Full article card ===== */
function ArticleCard({ article }: { article: Article }) {
  const authorName = article.author?.name || 'AI Автор'
  const excerpt = ((article.meta_description || article.body_md) || '').replace(/^#+\s.*/gm,'').replace(/\*\*/g,'').replace(/\n+/g,' ').trim().slice(0,140) || ''
  return (
    <article className="article-card" onClick={(e) => { if ((e.target as HTMLElement).tagName !== "A") window.location.href = "/articles/" + article.slug; }} style={{cursor: "pointer"}}>
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
              {(article.tags || []).slice(0,2).map(tag => (
                <a key={tag} href={`/?tag=${encodeURIComponent(tag)}`} className="card-tag">{tag}</a>
              ))}
            </div>
            <div className="card-stats">
              {article.is_verified && <VerifiedBadge />}
              <span className="stat-item">👁 {article.views_count}</span>
              <span className="stat-item">💬 {article.comments_count || 0}</span>
            </div>
          </div>
        </div>
        {article.cover_image && (
          <div className="card-cover-wrap">
            <img src={article.cover_image} alt="" className="card-cover" loading="lazy" />
          </div>
        )}
      </div>
    </article>
  )
}

function findBestPeriod(articles: Article[]): string {
  const fallback = ["today", "yesterday", "week", "month", "all"];
  for (const p of fallback) {
    const cutoff = getPeriodDate(p);
    if (!cutoff) return p;
    const count = articles.filter(a => new Date(a.published_at) >= cutoff).length;
    if (count > 0) return p;
  }
  return "all";
}

export default function ArticleFeed({ articles }: { articles: Article[] }) {
  const [period, setPeriod] = useState("today")
  const [initialized, setInitialized] = useState(false)

  // On client mount: find best period with fallback
  useEffect(() => {
    if (!initialized) {
      const best = findBestPeriod(articles);
      setPeriod(best);
      setInitialized(true);
    }
  }, [articles, initialized])

  const filtered = articles.filter(a => {
    const cutoff = getPeriodDate(period)
    if (!cutoff) return true
    return new Date(a.published_at) >= cutoff
  })

  // Popular = all articles sorted by views
  const popular = [...articles].sort((a, b) => b.views_count - a.views_count)

  return (
    <div>
      {/* ===== Compact headlines block (vc.ru style) ===== */}
      <div className="headlines-block">
        <DateFilter onChange={setPeriod} initialPeriod={period} />
        {filtered.length === 0 ? (
          <div style={{padding:'20px 0',color:'var(--color-text-secondary)',fontSize:14}}>
            Статей за этот период пока нет
          </div>
        ) : (
          <div className="headlines-list">
            {filtered.slice(0, 8).map(a => <HeadlineRow key={a.id} article={a} />)}
            {filtered.length > 8 && (
              <div style={{fontSize:13,color:'var(--color-text-secondary)',padding:'8px 0',cursor:'pointer'}}>
                Ещё {filtered.length - 8} статей...
              </div>
            )}
          </div>
        )}
      </div>

      {/* ===== Separator ===== */}
      <div style={{borderTop:'1px solid var(--color-border)',margin:'20px 0'}} />

      {/* ===== Full cards: Popular ===== */}
      <div style={{fontSize:15,fontWeight:600,color:'var(--color-text)',marginBottom:12}}>
        🔥 Популярное
      </div>
      {popular.map(a => <ArticleCard key={a.id} article={a} />)}
    </div>
  )
}
