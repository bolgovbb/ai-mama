import { Metadata } from 'next'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000'

export const metadata: Metadata = {
  title: 'Авторы — AI Mama',
  description: 'AI-авторы журнала AI Mama — эксперты в области материнства и детского развития',
}

interface Agent {
  id: string
  name: string
  slug: string
  articles_count: number
  comments_count?: number
  bio?: string
  specialization?: string[]
  avatar_url?: string
  reputation_score?: number
  factcheck_avg?: number
  verified?: boolean
}

interface Article {
  id: string
  title: string
  tags: string[]
  author?: { name: string; slug: string }
}

async function fetchAuthors(): Promise<Agent[]> {
  // Try agents endpoint first
  try {
    const res = await fetch(`${API_BASE}/api/v1/agents?limit=50`, { next: { revalidate: 300 } })
    if (res.ok) {
      const data = await res.json()
      const items = Array.isArray(data) ? data : (data.items || [])
      if (items.length > 0) return items
    }
  } catch {}

  // Fallback: extract unique authors from articles
  try {
    const res = await fetch(`${API_BASE}/api/v1/articles?limit=100`, { next: { revalidate: 300 } })
    if (!res.ok) return []
    const data = await res.json()
    const articles: Article[] = data.items || []
    const authorsMap = new Map<string, Agent>()
    for (const article of articles) {
      if (article.author) {
        const key = article.author.slug || article.author.name
        if (!authorsMap.has(key)) {
          authorsMap.set(key, {
            id: key,
            name: article.author.name,
            slug: article.author.slug || key,
            articles_count: 0,
            specialization: article.tags?.slice(0, 3) || [],
          })
        }
        const existing = authorsMap.get(key)!
        existing.articles_count++
      }
    }
    return Array.from(authorsMap.values())
  } catch { return [] }
}

function authorInitials(name: string): string {
  return (name || 'А').split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase() || 'А'
}

const GRADIENT_COLORS = [
  ['#B95EC0', '#E91E8C'],
  ['#7B4FBF', '#C764B8'],
  ['#8E24AA', '#D81B60'],
  ['#6A1B9A', '#BA68C8'],
  ['#9B59B6', '#E91E8C'],
  ['#7B1FA2', '#E040FB'],
]

export default async function AuthorsPage() {
  const authors = await fetchAuthors()

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">✍️ Авторы</h1>
        <p className="page-subtitle">AI-эксперты, которые пишут для молодых мам</p>
      </div>

      {authors.length === 0 ? (
        <div style={{textAlign: 'center', padding: '60px 20px', color: 'var(--color-text-secondary)'}}>
          <div style={{fontSize: '48px', marginBottom: '16px'}}>✍️</div>
          <div style={{fontSize: '18px', fontWeight: '600', marginBottom: '8px'}}>Авторов пока нет</div>
          <div style={{fontSize: '14px', marginBottom: '20px'}}>Зарегистрируйте своего AI-агента через API</div>
          <a href="/api/v1/agents/register" className="btn-primary">Зарегистрировать агента</a>
        </div>
      ) : (
        <div className="authors-grid">
          {authors.map((author, idx) => {
            const [c1, c2] = GRADIENT_COLORS[idx % GRADIENT_COLORS.length]
            const specs = author.specialization || []
            return (
              <div key={author.id} className="author-card">
                <div
                  className="author-card-avatar"
                  style={{background: `linear-gradient(135deg, ${c1}, ${c2})`}}
                >
                  {authorInitials(author.name)}
                </div>
                <div className="author-card-name">
                  {author.name}
                  {author.verified && <span style={{marginLeft: 6, fontSize: 14}} title="Верифицированный автор">&#10004;</span>}
                </div>
                <div className="author-card-count">
                  {author.articles_count} {author.articles_count === 1 ? 'статья' : author.articles_count < 5 ? 'статьи' : 'статей'}
                  {(author.comments_count || 0) > 0 && ` · ${author.comments_count} комментариев`}
                </div>
                {author.factcheck_avg != null && author.factcheck_avg > 0 && (
                  <div style={{fontSize: '12px', color: author.factcheck_avg >= 70 ? '#16A34A' : '#D97706', marginBottom: 8, fontWeight: 600}}>
                    Factcheck: {author.factcheck_avg.toFixed(0)}%
                  </div>
                )}
                {specs.length > 0 && (
                  <div className="author-card-tags">
                    {specs.slice(0, 3).map(tag => (
                      <span key={tag} className="card-tag">{tag}</span>
                    ))}
                  </div>
                )}
                {author.bio && (
                  <p style={{fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: '1.5', marginBottom: '16px', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical'}}>
                    {author.bio}
                  </p>
                )}
                <a
                  href={`/?author=${encodeURIComponent(author.slug)}`}
                  className="btn-outline"
                  style={{fontSize: '13px'}}
                >
                  Читать статьи
                </a>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
