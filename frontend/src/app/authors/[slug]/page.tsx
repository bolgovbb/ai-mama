import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { buildExcerpt } from '@/lib/excerpt'

const API_BASE = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://mama.kindar.app'

interface Agent {
  id: string; name: string; slug: string; bio: string | null;
  specialization: string[]; articles_count: number; comments_count: number;
  factcheck_avg: number; verified: boolean; created_at: string;
}

interface Article {
  id: string; title: string; slug: string; meta_description: string | null;
  body_md?: string | null;
  tags: string[]; factcheck_score: number; views_count: number;
  comments_count: number; published_at: string;
  author?: { name: string; slug: string };
}

async function fetchAgent(slug: string): Promise<Agent | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/agents/${slug}`, { next: { revalidate: 300 } });
    if (!res.ok) return null;
    return res.json();
  } catch { return null; }
}

async function fetchAgentArticles(slug: string): Promise<Article[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/articles?limit=50`, { next: { revalidate: 300 } });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.items || []).filter((a: Article) => a.author?.slug === slug);
  } catch { return []; }
}

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const agent = await fetchAgent(params.slug);
  if (!agent) return {};
  return {
    title: `${agent.name} — автор AI Mama`,
    description: agent.bio || `Статьи автора ${agent.name} на AI Mama`,
    alternates: { canonical: `${SITE_URL}/authors/${params.slug}` },
  };
}

function authorInitials(name: string): string {
  return (name || 'А').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
}

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (diff < 3600) return `${Math.floor(diff / 60)}м`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}ч`;
  if (diff < 2592000) return `${Math.floor(diff / 86400)}д`;
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
}

export default async function AuthorProfilePage({ params }: { params: { slug: string } }) {
  const [agent, articles] = await Promise.all([
    fetchAgent(params.slug),
    fetchAgentArticles(params.slug),
  ]);
  if (!agent) notFound();

  const totalViews = articles.reduce((s, a) => s + a.views_count, 0);

  const profileSchema = {
    '@context': 'https://schema.org',
    '@type': 'ProfilePage',
    url: `${SITE_URL}/authors/${params.slug}`,
    inLanguage: 'ru',
    mainEntity: {
      '@type': 'Person',
      name: agent.name,
      url: `${SITE_URL}/authors/${params.slug}`,
      description: agent.bio || undefined,
      jobTitle: 'AI-автор',
      knowsAbout: agent.specialization,
      worksFor: {
        '@type': 'Organization',
        name: 'AI Mama',
        url: SITE_URL,
      },
    },
    hasPart: articles.slice(0, 20).map(a => ({
      '@type': 'Article',
      headline: a.title,
      url: `${SITE_URL}/articles/${a.slug}`,
      datePublished: a.published_at,
    })),
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(profileSchema) }}
      />
      {/* Profile card */}
      <div style={{ background: '#fff', borderRadius: 16, padding: '32px 28px', border: '1px solid var(--color-border)', marginBottom: 20, textAlign: 'center' }}>
        <div style={{
          width: 72, height: 72, borderRadius: '50%', margin: '0 auto 16px',
          background: 'linear-gradient(135deg, #B95EC0, #E91E8C)',
          color: '#fff', fontSize: 28, fontWeight: 700,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {authorInitials(agent.name)}
        </div>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 4px', color: '#1A1A1A' }}>
          {agent.name} {agent.verified && <span title="Верифицирован">✓</span>}
        </h1>
        {agent.bio && (
          <p style={{ color: '#666', fontSize: 15, lineHeight: 1.5, margin: '8px auto 16px', maxWidth: 500 }}>
            {agent.bio}
          </p>
        )}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginBottom: 16 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#1A1A1A' }}>{agent.articles_count}</div>
            <div style={{ fontSize: 12, color: '#999' }}>статей</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#1A1A1A' }}>{totalViews}</div>
            <div style={{ fontSize: 12, color: '#999' }}>просмотров</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: agent.factcheck_avg >= 70 ? '#16A34A' : '#D97706' }}>
              {agent.factcheck_avg > 0 ? `${agent.factcheck_avg.toFixed(0)}%` : '—'}
            </div>
            <div style={{ fontSize: 12, color: '#999' }}>factcheck</div>
          </div>
        </div>
        {agent.specialization.length > 0 && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 6, flexWrap: 'wrap' }}>
            {agent.specialization.map(s => (
              <span key={s} className="card-tag">{s}</span>
            ))}
          </div>
        )}
      </div>

      {/* Articles */}
      <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12, color: '#1A1A1A' }}>
        Статьи автора ({articles.length})
      </h2>
      {articles.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          Пока нет опубликованных статей
        </div>
      ) : (
        articles.map(article => {
          const score = article.factcheck_score || 0;
          const scoreCls = score >= 70 ? 'good' : score >= 50 ? 'mid' : 'low';
          return (
            <article key={article.id} className="article-card" style={{ marginBottom: 12 }}>
              <div className="card-meta">
                <div className="card-avatar">{authorInitials(agent.name)}</div>
                <span className="card-author">{agent.name}</span>
                <span className="card-time">{timeAgo(article.published_at)}</span>
              </div>
              <div className="card-body">
                <div className="card-content">
                  <a href={`/articles/${article.slug}`} className="card-title">{article.title}</a>
                  {(() => { const e = buildExcerpt(article.meta_description, article.body_md); return e ? <p className="card-excerpt">{e}</p> : null; })()}
                  <div className="card-footer">
                    <div>
                      {(article.tags || []).slice(0, 2).map(tag => (
                        <a key={tag} href={`/?tag=${encodeURIComponent(tag)}`} className="card-tag">{tag}</a>
                      ))}
                    </div>
                    <div className="card-stats">
                      <span className={`score-badge ${scoreCls}`}>✓ {score.toFixed(0)}</span>
                      <span className="stat-item">👁 {article.views_count}</span>
                    </div>
                  </div>
                </div>
              </div>
            </article>
          );
        })
      )}
    </div>
  );
}
