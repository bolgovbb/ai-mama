import { notFound } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

const DOMAIN_LABELS: Record<string, string> = {
  speech: "Речь",
  motor_fine: "Мелкая моторика",
  motor_gross: "Крупная моторика",
  cognitive: "Когниция",
  social: "Социализация",
  emotional: "Эмоции",
};

const DOMAIN_ICONS: Record<string, string> = {
  speech: "💬",
  motor_fine: "✋",
  motor_gross: "🏃",
  cognitive: "🧠",
  social: "👫",
  emotional: "💛",
};

function scoreColor(score: number): string {
  if (score >= 80) return "#22C55E";
  if (score >= 50) return "#F59E0B";
  return "#EF4444";
}

function ageLabel(months: number): string {
  if (months < 12) return `${months} мес.`;
  const y = Math.floor(months / 12);
  const m = months % 12;
  if (m === 0) return `${y} ${y === 1 ? "год" : y < 5 ? "года" : "лет"}`;
  return `${y} г. ${m} мес.`;
}

async function fetchChildMap(childId: string, agentKey?: string) {
  if (!agentKey) return null;
  try {
    const [childRes, mapRes, recsRes] = await Promise.all([
      fetch(`${API_BASE}/api/v1/children/${childId}`, {
        headers: { Authorization: `Bearer ${agentKey}` },
        next: { revalidate: 0 },
      }),
      fetch(`${API_BASE}/api/v1/children/${childId}/map`, {
        headers: { Authorization: `Bearer ${agentKey}` },
        next: { revalidate: 0 },
      }),
      fetch(`${API_BASE}/api/v1/children/${childId}/recommendations`, {
        headers: { Authorization: `Bearer ${agentKey}` },
        next: { revalidate: 0 },
      }),
    ]);
    if (!childRes.ok || !mapRes.ok) return null;
    const [child, map, recs] = await Promise.all([
      childRes.json(),
      mapRes.json(),
      recsRes.ok ? recsRes.json() : [],
    ]);
    return { child, map, recs };
  } catch {
    return null;
  }
}

export default async function ChildPage({ params, searchParams }: {
  params: { id: string };
  searchParams: { key?: string };
}) {
  const agentKey = searchParams.key;
  const data = await fetchChildMap(params.id, agentKey);

  // Без ключа — показываем демо/инструкцию
  if (!data) {
    return (
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
          <a href="/children" style={{ color: "#FF6B9D", textDecoration: "none", fontSize: 14 }}>← Карта развития</a>
        </div>
        <div style={{ background: "#FFF0F8", borderRadius: 12, padding: 32, textAlign: "center" }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🔐</div>
          <h2 style={{ margin: "0 0 8px" }}>Требуется API-ключ агента</h2>
          <p style={{ color: "#666", marginBottom: 20 }}>
            Карта развития персонализирована и доступна только через API-ключ агента AI Mama.
          </p>
          <div style={{ background: "#fff", borderRadius: 8, padding: "14px 16px", fontFamily: "monospace", fontSize: 13, textAlign: "left", maxWidth: 480, margin: "0 auto" }}>
            <div style={{ color: "#888" }}># Получить карту через API</div>
            <div>GET /api/v1/children/{params.id}/map</div>
            <div style={{ color: "#888", marginTop: 8 }}># Или добавить ключ к URL</div>
            <div>/children/{params.id}?key=YOUR_API_KEY</div>
          </div>
        </div>
      </div>
    );
  }

  const { child, map, recs } = data;
  const childName = child.name || "Ребёнок";
  const birthDate = new Date(child.birth_date);
  const redFlagRecs = recs.filter((r: any) => r.is_red_flag);
  const normalRecs = recs.filter((r: any) => !r.is_red_flag);

  return (
    <div>
      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
        <a href="/children" style={{ color: "#FF6B9D", textDecoration: "none", fontSize: 14 }}>← Карта развития</a>
      </div>

      {/* Header */}
      <div style={{ background: "linear-gradient(135deg, #FFE4EE 0%, #FFF0F8 100%)", borderRadius: 16, padding: "24px", marginBottom: 24, display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#FF6B9D", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28, flexShrink: 0 }}>
          🌱
        </div>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: 24, margin: "0 0 4px" }}>{childName}</h1>
          <div style={{ color: "#666", fontSize: 14 }}>
            Возраст: {ageLabel(map.age_months)} · Дата рождения: {birthDate.toLocaleDateString("ru-RU")}
          </div>
          {child.gender && (
            <div style={{ color: "#999", fontSize: 12, marginTop: 2 }}>
              {child.gender === "male" ? "Мальчик" : child.gender === "female" ? "Девочка" : child.gender}
            </div>
          )}
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 36, fontWeight: 700, color: scoreColor(map.overall_score) }}>{map.overall_score.toFixed(0)}%</div>
          <div style={{ fontSize: 12, color: "#888" }}>Общий прогресс</div>
        </div>
      </div>

      {/* Красные флаги */}
      {redFlagRecs.length > 0 && (
        <div style={{ background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: 12, padding: 16, marginBottom: 24 }}>
          <h3 style={{ color: "#DC2626", margin: "0 0 10px", fontSize: 16 }}>⚠️ Обратитесь к специалисту</h3>
          {redFlagRecs.map((r: any) => (
            <div key={r.id} style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 500, color: "#991B1B", fontSize: 14 }}>{r.activity_title}</div>
              <div style={{ color: "#7F1D1D", fontSize: 13 }}>{r.activity_description}</div>
            </div>
          ))}
        </div>
      )}

      {/* Карта доменов */}
      <h2 style={{ fontSize: 20, marginBottom: 16 }}>Карта развития по доменам</h2>
      <div style={{ display: "grid", gap: 12, marginBottom: 32 }}>
        {map.domains.map((d: any) => {
          const color = scoreColor(d.score);
          return (
            <div key={d.domain} style={{ background: "#fff", borderRadius: 12, padding: "16px 20px", border: "1px solid #eee" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <span style={{ fontSize: 20 }}>{DOMAIN_ICONS[d.domain] || "📌"}</span>
                <span style={{ fontWeight: 600, fontSize: 15 }}>{DOMAIN_LABELS[d.domain] || d.domain}</span>
                <span style={{ marginLeft: "auto", fontWeight: 700, color, fontSize: 16 }}>{d.score.toFixed(0)}%</span>
                {d.red_flags > 0 && (
                  <span style={{ background: "#FEF2F2", color: "#DC2626", fontSize: 12, padding: "2px 8px", borderRadius: 4 }}>
                    ⚠ {d.red_flags}
                  </span>
                )}
              </div>
              {/* Progress bar */}
              <div style={{ background: "#f5f5f5", borderRadius: 4, overflow: "hidden", height: 8 }}>
                <div style={{ background: color, width: `${d.score}%`, height: "100%", transition: "width 0.3s" }} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 12, color: "#999" }}>
                <span>Освоено: {d.achieved} из {d.expected}</span>
                <span>Возраст: {ageLabel(map.age_months)}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Рекомендации */}
      {normalRecs.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, marginBottom: 16 }}>💡 Рекомендуемые активности</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
            {normalRecs.slice(0, 6).map((r: any) => (
              <div key={r.id} style={{ background: "#fff", borderRadius: 12, padding: 16, border: "1px solid #eee" }}>
                <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                  <span style={{ fontSize: 18 }}>{DOMAIN_ICONS[r.domain] || "📌"}</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{r.activity_title}</div>
                    <div style={{ fontSize: 12, color: "#999" }}>{DOMAIN_LABELS[r.domain] || r.domain}</div>
                  </div>
                </div>
                <p style={{ color: "#555", fontSize: 13, margin: 0, lineHeight: 1.5 }}>{r.activity_description}</p>
                <div style={{ marginTop: 10 }}>
                  <span style={{
                    fontSize: 11,
                    padding: "2px 8px",
                    borderRadius: 4,
                    background: r.priority === "high" ? "#FEF2F2" : r.priority === "medium" ? "#FFFBEB" : "#F0FDF4",
                    color: r.priority === "high" ? "#DC2626" : r.priority === "medium" ? "#92400E" : "#166534",
                  }}>
                    {r.priority === "high" ? "Высокий приоритет" : r.priority === "medium" ? "Средний" : "Низкий"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dialog link */}
      <div style={{ background: "#1C1418", color: "#fff", borderRadius: 12, padding: 20 }}>
        <h3 style={{ color: "#FF6B9D", margin: "0 0 8px", fontSize: 16 }}>💬 Обновить карту через диалог</h3>
        <p style={{ color: "#ccc", fontSize: 13, margin: "0 0 12px" }}>
          Расскажите AI Mama о новых навыках ребёнка — карта обновится автоматически.
        </p>
        <div style={{ background: "#2a2022", borderRadius: 8, padding: "12px 14px", fontFamily: "monospace", fontSize: 12, color: "#e0e0e0" }}>
          POST /api/v1/children/{params.id}/dialog<br />
          {'{ "message": "Миша сегодня сказал первое слово!" }'}
        </div>
      </div>
    </div>
  );
}
