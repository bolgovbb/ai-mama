import { Metadata } from 'next'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000'

export const metadata: Metadata = {
  title: 'Темы — AI Mama',
  description: 'Все темы и разделы журнала AI Mama для молодых мам',
}

interface Article {
  id: string
  title: string
  tags: string[]
}

const TOPIC_ICONS: Record<string, string> = {
  'беременность': '🤰',
  'роды': '👶',
  'новорождённый': '🍼',
  'новорожденный': '🍼',
  'грудное вскармливание': '🤱',
  'прикорм': '🥕',
  'развитие': '🧸',
  'здоровье': '💊',
  'психология': '🧠',
  'сон': '😴',
  'игры': '🎮',
  'питание': '🥗',
  'безопасность': '🛡️',
  'образование': '📚',
  'уход': '🛁',
  'вакцинация': '💉',
  'аллергия': '🌿',
}

function getTopicIcon(topic: string): string {
  const lower = topic.toLowerCase()
  for (const [key, icon] of Object.entries(TOPIC_ICONS)) {
    if (lower.includes(key) || key.includes(lower)) return icon
  }
  return '📌'
}

async function fetchTopics(): Promise<Array<{name: string; count: number}>> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/articles?limit=200`, { next: { revalidate: 300 } })
    if (!res.ok) return []
    const data = await res.json()
    const articles: Article[] = data.items || []
    const topicsMap = new Map<string, number>()
    for (const article of articles) {
      for (const tag of (article.tags || [])) {
        topicsMap.set(tag, (topicsMap.get(tag) || 0) + 1)
      }
    }
    return Array.from(topicsMap.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
  } catch { return [] }
}

const DEFAULT_TOPICS = [
  'Беременность', 'Роды', 'Новорождённый', 'Грудное вскармливание',
  'Прикорм', 'Развитие', 'Здоровье', 'Психология', 'Сон', 'Игры',
  'Питание', 'Безопасность'
]

export default async function TopicsPage() {
  let topics = await fetchTopics()

  if (topics.length === 0) {
    topics = DEFAULT_TOPICS.map(name => ({ name, count: 0 }))
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">🏷️ Темы</h1>
        <p className="page-subtitle">Все разделы журнала AI Mama</p>
      </div>

      <div className="topics-grid">
        {topics.map(topic => (
          <a
            key={topic.name}
            href={`/?tag=${encodeURIComponent(topic.name)}`}
            className="topic-card"
          >
            <div className="topic-card-icon">{getTopicIcon(topic.name)}</div>
            <div className="topic-card-name">{topic.name}</div>
            {topic.count > 0 && (
              <div className="topic-card-count">
                {topic.count} {topic.count === 1 ? 'статья' : topic.count < 5 ? 'статьи' : 'статей'}
              </div>
            )}
          </a>
        ))}
      </div>
    </div>
  )
}
