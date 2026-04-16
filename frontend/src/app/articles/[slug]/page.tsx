import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import ReadingProgressBar from '@/components/ReadingProgressBar'
import CommentsSection from '@/components/CommentsSection'
import InfiniteArticles from '@/components/InfiniteArticles'
import ArticleActions from '@/components/ArticleActions'
import ArticleChat from '@/components/ArticleChat'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000'
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://5.129.205.143'

interface Article {
  id: string
  title: string
  slug: string
  body_html?: string
  body_md?: string
  meta_description?: string
  tags: string[]
  factcheck_score: number
  is_verified?: boolean
  views_count: number
  comments_count: number
  reactions_count: number
  published_at: string
  cover_image?: string
  audio_url?: string
  video_url?: string
  sources?: Array<string | { url: string; title?: string; type?: string }>
  author?: { name: string; slug: string; articles_count: number }
}

async function fetchArticle(slug: string): Promise<Article | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/articles/${slug}`, { next: { revalidate: 60 } })
    if (!res.ok) return null
    return res.json()
  } catch { return null }
}

async function fetchRelated(currentSlug: string): Promise<Article[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/articles?limit=4`, { next: { revalidate: 300 } })
    if (!res.ok) return []
    const data = await res.json()
    const items: Article[] = data.items || []
    return items.filter(a => a.slug !== currentSlug).slice(0, 3)
  } catch { return [] }
}

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const { slug } = params
  const article = await fetchArticle(slug)
  if (!article) return {}
  const coverImageUrl = article.cover_image ? `${SITE_URL}${article.cover_image}` : undefined
  return {
    title: article.title,
    description: article.meta_description,
    alternates: {
      canonical: `https://mama.kindar.app/articles/${slug}`,
    },
    openGraph: {
      title: article.title,
      description: article.meta_description ?? undefined,
      type: 'article',
      url: `https://mama.kindar.app/articles/${slug}`,
      siteName: 'AI Mama',
      locale: 'ru_RU',
      publishedTime: article.published_at,
      authors: [article.author?.name || 'AI Mama'],
      tags: article.tags,
      images: coverImageUrl ? [{ url: coverImageUrl, width: 1200, height: 630, alt: article.title }] : [],
    },
    twitter: {
      card: 'summary_large_image',
      title: article.title,
      description: article.meta_description ?? undefined,
      images: coverImageUrl ? [coverImageUrl] : [],
    },
  }
}

function injectHeadingIds(html: string): string {
  let idx = 0
  return html.replace(/<h2([^>]*)>/gi, (_match, attrs) => {
    const id = `heading-${idx++}`
    return `<h2${attrs} id="${id}">`
  })
}

function authorInitials(name: string): string {
  return (name || 'А').split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase() || 'А'
}

function timeAgo(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diff < 60) return 'только что'
  if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`
  if (diff < 2592000) return `${Math.floor(diff / 86400)} дн назад`
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}


function VerifiedBadge() {
  return (
    <span style={{display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '13px', color: '#1D9BF0', fontWeight: 600}} title="Проверено экспертом">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="8" fill="#1D9BF0"/>
        <path d="M5 8l2 2 4-4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
      Проверено
    </span>
  )
}

function ScoreBadge({ score }: { score: number }) {
  const cls = score >= 70 ? 'good' : score >= 50 ? 'mid' : 'low'
  const label = score >= 70 ? '✓ Проверено' : score >= 50 ? '~ Частично проверено' : '! Проверяется'
  return <span className={`score-badge ${cls}`}>{label} {score.toFixed(0)}%</span>
}

function generateHeroSVG(title: string, tags: string[]): string {
  const gradients = [
    ['#B95EC0', '#E91E8C'],
    ['#7B4FBF', '#C764B8'],
    ['#9B59B6', '#E91E8C'],
    ['#6C3483', '#B95EC0'],
    ['#8E24AA', '#D81B60'],
    ['#7B1FA2', '#E040FB'],
    ['#9C27B0', '#F06292'],
    ['#6A1B9A', '#BA68C8'],
  ]
  // Pick gradient by title length
  const idx = (title.length + (tags[0] || '').length) % gradients.length
  const [c1, c2] = gradients[idx]
  const tag = tags[0] || 'AI Mama'
  const safeTitle = title.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  const safeTag = tag.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  // Wrap title to ~35 chars per line
  const words = safeTitle.split(' ')
  const lines: string[] = []
  let current = ''
  for (const word of words) {
    if ((current + ' ' + word).trim().length <= 35) {
      current = (current + ' ' + word).trim()
    } else {
      if (current) lines.push(current)
      current = word
    }
    if (lines.length >= 3) break
  }
  if (current && lines.length < 3) lines.push(current)

  const textLines = lines.map((line, i) =>
    `<text x="60" y="${300 + i * 52}" font-family="Arial, sans-serif" font-size="40" font-weight="700" fill="white" opacity="0.95">${line}</text>`
  ).join('\n  ')

  return `<svg width="800" height="400" viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="${c1}"/>
      <stop offset="100%" stop-color="${c2}"/>
    </linearGradient>
    <linearGradient id="overlayGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="rgba(0,0,0,0)"/>
      <stop offset="100%" stop-color="rgba(0,0,0,0.5)"/>
    </linearGradient>
  </defs>
  <rect width="800" height="400" fill="url(#heroGrad)"/>
  <!-- Decorative circles -->
  <circle cx="650" cy="80" r="120" fill="white" opacity="0.07"/>
  <circle cx="700" cy="300" r="80" fill="white" opacity="0.05"/>
  <circle cx="100" cy="50" r="60" fill="white" opacity="0.06"/>
  <circle cx="780" cy="180" r="150" fill="white" opacity="0.04"/>
  <!-- Wave decoration -->
  <path d="M0 250 Q200 200 400 260 Q600 320 800 270 L800 400 L0 400 Z" fill="rgba(0,0,0,0.2)"/>
  <!-- Overlay gradient -->
  <rect width="800" height="400" fill="url(#overlayGrad)"/>
  <!-- Tag label -->
  <rect x="50" y="50" width="${safeTag.length * 12 + 24}" height="32" rx="16" fill="rgba(255,255,255,0.25)"/>
  <text x="62" y="71" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="600">${safeTag}</text>
  <!-- Title -->
  ${textLines}
</svg>`
}

export default async function ArticlePage({ params }: { params: { slug: string } }) {
  const { slug } = params
  const article = await fetchArticle(slug)
  if (!article) notFound()

  const rawHtml = article.body_html || article.body_md || ''
  // Remove duplicate H1 from body (already shown as article-title)
  const bodyHtml = rawHtml.replace(/^\s*<h1[^>]*>.*?<\/h1>\s*/i, '')
  // Open external links in new tab
  const bodyExtLinks = bodyHtml.replace(
    /<a\s+href="(https?:\/\/(?!mama\.kindar\.app)[^"]+)"/gi,
    '<a href="$1" target="_blank" rel="noopener noreferrer"'
  )
  const bodyWithIds = injectHeadingIds(bodyExtLinks)
  const authorName = article.author?.name || 'AI Автор'
  const heroSvg = generateHeroSVG(article.title, article.tags || [])

  // Plain-text body for Schema.org Article.articleBody — Yandex content
  // analytics and Google need it as clean text, without HTML/markdown noise.
  const plainBody = (article.body_md || '')
    .replace(/```[\s\S]*?```/g, ' ')          // code blocks
    .replace(/!\[[^\]]*\]\([^)]+\)/g, ' ')     // images
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')   // links → text
    .replace(/[#*_`>~]/g, '')                  // md markers
    .replace(/<[^>]+>/g, ' ')                  // any stray HTML
    .replace(/\s+/g, ' ')
    .trim()
  const wordCount = plainBody ? plainBody.split(/\s+/).length : 0

  const schemaOrg = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: article.title,
    description: article.meta_description,
    image: article.cover_image ? `${SITE_URL}${article.cover_image}` : undefined,
    datePublished: article.published_at,
    dateModified: article.published_at,
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `https://mama.kindar.app/articles/${slug}`,
    },
    author: {
      '@type': 'Person',
      name: authorName,
      url: article.author?.slug
        ? `https://mama.kindar.app/authors/${article.author.slug}`
        : `https://mama.kindar.app/authors`,
    },
    publisher: {
      '@type': 'Organization',
      name: 'AI Mama',
      url: 'https://mama.kindar.app',
      logo: {
        '@type': 'ImageObject',
        url: 'https://mama.kindar.app/favicon.svg',
      },
    },
    articleSection: (article.tags || [])[0] || 'Материнство',
    keywords: (article.tags || []).join(', '),
    inLanguage: 'ru',
    articleBody: plainBody,
    wordCount,
    speakable: {
      '@type': 'SpeakableSpecification',
      cssSelector: ['.article-title', '.article-content h2', '.article-content p:first-of-type'],
    },
  }

  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Главная', item: 'https://mama.kindar.app' },
      ...(article.tags?.length ? [{ '@type': 'ListItem', position: 2, name: article.tags[0], item: `https://mama.kindar.app/?tag=${encodeURIComponent(article.tags[0])}` }] : []),
      { '@type': 'ListItem', position: article.tags?.length ? 3 : 2, name: article.title },
    ],
  }

  return (
    <>
    <div className="article-page">
      <ReadingProgressBar />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaOrg) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />

      {/* Breadcrumbs */}
      <nav className="article-breadcrumb">
        <a href="/">Лента</a>
        <span>›</span>
        {(article.tags || []).length > 0 && (
          <>
            <a href={`/?tag=${encodeURIComponent(article.tags[0])}`}>{article.tags[0]}</a>
            <span>›</span>
          </>
        )}
        <span style={{color: 'var(--color-text)', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>{article.title}</span>
      </nav>

      {/* Author bar */}
      <div className="article-author-bar">
        <div className="author-avatar-lg">{authorInitials(authorName)}</div>
        <div>
          <div className="author-info-name">{authorName}</div>
          <div className="author-info-meta">
            {timeAgo(article.published_at)} · {article.views_count} просмотров · {Math.max(1, Math.ceil((article.body_md || '').split(/\s+/).length / 200))} мин чтения
          </div>
        </div>
      </div>

      {/* Title */}
      <h1 className="article-title">{article.title}</h1>

      {/* Hero image */}
      <div className="article-hero">
        {article.cover_image ? (
          <img
            src={`${SITE_URL}${article.cover_image}`}
            alt={article.title}
          />
        ) : (
          <div dangerouslySetInnerHTML={{ __html: heroSvg }} style={{width: '100%', height: '100%'}} />
        )}
      </div>

      {/* Meta bar */}
      {/* Audio podcast player */}
      {article.audio_url && (
        <div className="article-audio">
          <span className="article-audio__label">🎧 Послушать статью</span>
          <audio controls preload="none" className="article-audio__player">
            <source src={`${SITE_URL}${article.audio_url}`} type="audio/mpeg" />
          </audio>
        </div>
      )}
      <div className="article-meta-bar">
        {(article.tags || []).map(tag => (
          <a key={tag} href={`/?tag=${encodeURIComponent(tag)}`} className="card-tag">{tag}</a>
        ))}
        {article.is_verified && <VerifiedBadge />}
        {article.published_at && (
          <span>{new Date(article.published_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })}</span>
        )}
      </div>

      {/* Article content */}
      <article
        className="article-content"
        dangerouslySetInnerHTML={{ __html: bodyWithIds }}
      />

      {/* Reactions bar */}
      <ArticleActions articleId={article.id} slug={slug} title={article.title} initialViews={article.views_count} />

    </div>
    {/* === End of main article card === */}

      {/* Sources */}
      {article.sources && article.sources.length > 0 && (
        <section className="sources-section" style={{maxWidth: 720, margin: '20px auto 0'}}>
          <h3 className="sources-title">📚 Источники</h3>
          {article.sources.map((s, i) => {
            const url = typeof s === "string" ? s : s.url;
            const title = typeof s === "string" ? undefined : s.title;
            if (!url) return null;
            return (
            <div key={i} className="source-item">
              <div className="source-num">{i + 1}</div>
              <div>
                <a href={url} target="_blank" rel="noopener noreferrer" className="source-link">
                  {title || (() => { try { return new URL(url).hostname.replace("www.", ""); } catch { return url.slice(0, 60); } })()}
                </a>
              </div>
            </div>
            );
          })}
        </section>
      )}

      {/* Ask Кира — AI chat about this specific article */}
      <div style={{maxWidth: 720, margin: '0 auto'}}>
        <ArticleChat slug={slug} />
      </div>

      {/* Comments — separate card */}
      <div style={{maxWidth: 720, margin: '20px auto 0'}}>
        <CommentsSection articleId={article.id} />
      </div>

      {/* Infinite scroll articles — same cards as feed */}
      <InfiniteArticles excludeSlug={slug} />
    </>
  )
}
