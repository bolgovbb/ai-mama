import ArticleFeed from "@/components/ArticleFeed"

async function fetchArticles(tag?: string) {
  try {
    const url = `http://127.0.0.1:8000/api/v1/articles?limit=50${tag ? "&tag=" + encodeURIComponent(tag) : ""}`
    const res = await fetch(url, { next: { revalidate: 60 } })
    if (!res.ok) return []
    const data = await res.json()
    return data.items || []
  } catch { return [] }
}

export default async function HomePage({ searchParams }: { searchParams: { tag?: string } }) {
  const articles = await fetchArticles(searchParams?.tag)

  return (
    <div>
      {searchParams?.tag && (
        <div style={{marginBottom: 12, display: "flex", alignItems: "center", gap: 8}}>
          <span style={{fontSize: 14, color: "var(--color-text-secondary)"}}>Тег:</span>
          <span style={{fontSize: 14, fontWeight: 600, color: "var(--color-primary)"}}>{searchParams.tag}</span>
          <a href="/" style={{fontSize: 12, color: "var(--color-text-secondary)", textDecoration: "none"}}>✕ сбросить</a>
        </div>
      )}
      <ArticleFeed articles={articles} />
    </div>
  )
}
