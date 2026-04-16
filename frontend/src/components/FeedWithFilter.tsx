"use client"
import { useState } from "react"
import DateFilter, { getPeriodDate } from "./DateFilter"

interface Article {
  id: string
  title: string
  slug: string
  published_at: string
  [key: string]: any
}

export default function FeedWithFilter({
  articles,
  renderCard,
}: {
  articles: Article[]
  renderCard: (article: Article) => React.ReactNode
}) {
  const [period, setPeriod] = useState("all")

  const filtered = articles.filter(a => {
    const cutoff = getPeriodDate(period)
    if (!cutoff) return true
    return new Date(a.published_at) >= cutoff
  })

  return (
    <div>
      <DateFilter onChange={setPeriod} />
      {filtered.length === 0 ? (
        <div style={{textAlign: "center", padding: "60px 20px", color: "var(--color-text-secondary)"}}>
          <div style={{fontSize: 48, marginBottom: 16}}>📝</div>
          <div style={{fontSize: 18, fontWeight: 600, marginBottom: 8}}>Статей за этот период нет</div>
          <div style={{fontSize: 14}}>Попробуйте выбрать другой период</div>
        </div>
      ) : (
        filtered.map(a => <div key={a.id}>{renderCard(a)}</div>)
      )}
    </div>
  )
}
