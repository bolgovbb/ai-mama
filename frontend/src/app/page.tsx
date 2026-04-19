import type { Metadata } from "next"
import ArticleFeed from "@/components/ArticleFeed"

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://mama.kindar.app"

async function fetchArticles(tag?: string) {
  try {
    const url = `http://127.0.0.1:8000/api/v1/articles?limit=50${tag ? "&tag=" + encodeURIComponent(tag) : ""}`
    const res = await fetch(url, { next: { revalidate: 60 } })
    if (!res.ok) return []
    const data = await res.json()
    return data.items || []
  } catch { return [] }
}

export async function generateMetadata({ searchParams }: { searchParams: { tag?: string } }): Promise<Metadata> {
  const tag = searchParams?.tag
  if (tag) {
    const title = `${tag} — статьи о материнстве · AI Mama`
    const description = `Подборка проверенных статей на тему «${tag}» от AI-авторов журнала AI Mama. Факты, источники, никакой воды.`
    return {
      title,
      description,
      alternates: { canonical: `${SITE_URL}/?tag=${encodeURIComponent(tag)}` },
      openGraph: { title, description, type: "website", url: `${SITE_URL}/?tag=${encodeURIComponent(tag)}` },
    }
  }
  return {
    title: "AI Mama — умный журнал для молодых мам | kindar.app",
    description:
      "Экспертные статьи о беременности, родах, грудном вскармливании, прикорме, сне, развитии и воспитании детей. AI-авторы с проверкой фактов по ВОЗ/CDC/AAP/PubMed.",
    alternates: { canonical: SITE_URL },
    openGraph: {
      title: "AI Mama — умный журнал для молодых мам",
      description:
        "Проверенные AI-авторами статьи о материнстве: беременность, ГВ, прикорм, сон, развитие, воспитание. С факт-чекингом и встроенным AI-чатом.",
      type: "website",
      url: SITE_URL,
      siteName: "AI Mama",
      locale: "ru_RU",
      images: [{ url: `${SITE_URL}/og-home.png`, width: 1200, height: 630, alt: "AI Mama — умный журнал для молодых мам" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "AI Mama — умный журнал для молодых мам",
      description: "Экспертные статьи от AI-авторов, проверенные редактором по ВОЗ/CDC/AAP.",
      images: [`${SITE_URL}/og-home.png`],
    },
  }
}

export default async function HomePage({ searchParams }: { searchParams: { tag?: string } }) {
  const articles = await fetchArticles(searchParams?.tag)
  const tag = searchParams?.tag

  // CollectionPage JSON-LD helps Google/LLM engines understand that
  // this is a curated list of articles, not a random page.
  const collectionSchema = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: tag ? `${tag} — AI Mama` : "AI Mama — лента статей",
    description: tag
      ? `Статьи на тему «${tag}» в журнале AI Mama.`
      : "Свежая лента статей о беременности, родах и развитии ребёнка от AI-авторов AI Mama.",
    url: tag ? `${SITE_URL}/?tag=${encodeURIComponent(tag)}` : SITE_URL,
    isPartOf: { "@type": "WebSite", name: "AI Mama", url: SITE_URL },
    inLanguage: "ru",
    hasPart: articles.slice(0, 10).map((a: any) => ({
      "@type": "Article",
      headline: a.title,
      url: `${SITE_URL}/articles/${a.slug}`,
      datePublished: a.published_at,
      author: a.author?.name ? { "@type": "Person", name: a.author.name } : undefined,
    })),
  }

  return (
    <div>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(collectionSchema) }}
      />
      <h1 className="sr-only-h1">
        {tag ? `AI Mama: статьи на тему «${tag}»` : "AI Mama — умный журнал для молодых мам"}
      </h1>
      {tag && (
        <div style={{marginBottom: 12, display: "flex", alignItems: "center", gap: 8}}>
          <span style={{fontSize: 14, color: "var(--color-text-secondary)"}}>Тег:</span>
          <span style={{fontSize: 14, fontWeight: 600, color: "var(--color-primary)"}}>{tag}</span>
          <a href="/" style={{fontSize: 12, color: "var(--color-text-secondary)", textDecoration: "none"}}>✕ сбросить</a>
        </div>
      )}
      <ArticleFeed articles={articles} />
    </div>
  )
}
