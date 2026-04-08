import { fetchMilestones, Milestone } from "@/lib/api";

export const revalidate = 3600;

const DOMAIN_LABELS: Record<string, string> = {
  speech: "Речь и коммуникация",
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

const DOMAIN_COLORS: Record<string, string> = {
  speech: "#FF6B9D",
  motor_fine: "#4ECDC4",
  motor_gross: "#45B7D1",
  cognitive: "#96CEB4",
  social: "#FFEAA7",
  emotional: "#DDA0DD",
};

const AGE_LABELS: Record<string, string> = {
  "0-3": "0–3 месяца",
  "3-6": "3–6 месяцев",
  "6-9": "6–9 месяцев",
  "9-12": "9–12 месяцев",
  "12-18": "12–18 месяцев",
  "18-24": "18–24 месяца",
  "24-36": "2–3 года",
};

function ageGroup(min: number, max: number): string {
  if (max <= 3) return "0-3";
  if (max <= 6) return "3-6";
  if (max <= 9) return "6-9";
  if (max <= 12) return "9-12";
  if (max <= 18) return "12-18";
  if (max <= 24) return "18-24";
  return "24-36";
}

export default async function ChildrenPage() {
  const milestones: Milestone[] = await fetchMilestones();
  
  // Группировка по домену
  const byDomain: Record<string, Milestone[]> = {};
  for (const m of milestones) {
    if (!byDomain[m.domain]) byDomain[m.domain] = [];
    byDomain[m.domain].push(m);
  }
  
  // Группировка по возрасту для каждого домена
  const domainGroups = Object.entries(byDomain).map(([domain, items]) => {
    const byAge: Record<string, Milestone[]> = {};
    for (const m of items) {
      const group = ageGroup(m.age_months_min, m.age_months_max);
      if (!byAge[group]) byAge[group] = [];
      byAge[group].push(m);
    }
    return { domain, items, byAge };
  });

  return (
    <div>
      {/* Hero */}
      <div style={{ background: "linear-gradient(135deg, #FFE4EE 0%, #FFF0F8 100%)", borderRadius: 16, padding: "32px 24px", marginBottom: 32, textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>🌱</div>
        <h1 style={{ fontSize: 32, margin: "0 0 8px", color: "#1C1418" }}>Карта развития ребёнка</h1>
        <p style={{ color: "#666", fontSize: 16, maxWidth: 600, margin: "0 auto 24px" }}>
          Персонализированный трекер прогресса по стандартам ВОЗ/CDC. 
          ИИ-агент AI Mama отслеживает развитие через диалог и строит визуальную карту навыков.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          {["6 доменов развития", "31 ключевая веха", "Стандарты ВОЗ/CDC", "AI-рекомендации"].map(tag => (
            <span key={tag} style={{ background: "#FF6B9D", color: "#fff", padding: "6px 14px", borderRadius: 20, fontSize: 13, fontWeight: 500 }}>
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Домены */}
      <h2 style={{ fontSize: 22, marginBottom: 16 }}>Домены развития</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16, marginBottom: 40 }}>
        {Object.entries(DOMAIN_LABELS).map(([domain, label]) => {
          const count = byDomain[domain]?.length || 0;
          const color = DOMAIN_COLORS[domain] || "#eee";
          return (
            <div key={domain} style={{ background: "#fff", borderRadius: 12, padding: 20, border: `2px solid ${color}`, position: "relative", overflow: "hidden" }}>
              <div style={{ position: "absolute", top: 12, right: 12, fontSize: 28, opacity: 0.2 }}>{DOMAIN_ICONS[domain]}</div>
              <div style={{ fontSize: 24, marginBottom: 8 }}>{DOMAIN_ICONS[domain]}</div>
              <h3 style={{ fontSize: 16, margin: "0 0 6px", fontWeight: 600 }}>{label}</h3>
              <p style={{ color: "#888", fontSize: 13, margin: 0 }}>{count} ключевых вех (0–36 мес)</p>
              <div style={{ marginTop: 10, background: "#f5f5f5", borderRadius: 4, overflow: "hidden", height: 6 }}>
                <div style={{ background: color, width: `${Math.min(count * 15, 100)}%`, height: "100%" }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Таблица milestones по доменам */}
      <h2 style={{ fontSize: 22, marginBottom: 16 }}>Ключевые вехи развития</h2>
      <p style={{ color: "#666", marginBottom: 24 }}>Справочник по стандартам ВОЗ/CDC для детей от 0 до 36 месяцев</p>

      {domainGroups.map(({ domain, byAge }) => (
        <div key={domain} style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <span style={{ fontSize: 24 }}>{DOMAIN_ICONS[domain] || "📌"}</span>
            <h3 style={{ fontSize: 18, margin: 0, color: DOMAIN_COLORS[domain] || "#333" }}>
              {DOMAIN_LABELS[domain] || domain}
            </h3>
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {Object.entries(byAge)
              .sort(([a], [b]) => parseInt(a) - parseInt(b))
              .map(([ageGroup, items]) => (
                <div key={ageGroup}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>
                    {AGE_LABELS[ageGroup] || ageGroup}
                  </div>
                  {items.map(m => (
                    <div key={m.code} style={{ background: "#fff", borderRadius: 8, padding: "10px 14px", marginBottom: 6, border: "1px solid #eee", display: "flex", alignItems: "flex-start", gap: 10 }}>
                      <div style={{ width: 6, height: 6, borderRadius: "50%", background: DOMAIN_COLORS[domain] || "#ccc", marginTop: 6, flexShrink: 0 }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500, fontSize: 14 }}>{m.title}</div>
                        {m.description && <div style={{ color: "#888", fontSize: 12, marginTop: 2 }}>{m.description}</div>}
                        <div style={{ display: "flex", gap: 8, marginTop: 4, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 11, color: "#aaa" }}>{m.age_months_min}–{m.age_months_max} мес</span>
                          {m.age_months_concern && (
                            <span style={{ fontSize: 11, background: "#FFF3CD", color: "#856404", padding: "1px 6px", borderRadius: 4 }}>
                              ⚠ обратитесь к врачу после {m.age_months_concern} мес
                            </span>
                          )}
                          <span style={{ fontSize: 11, color: "#ccc" }}>{m.source}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
          </div>
        </div>
      ))}

      {/* API Info */}
      <div style={{ background: "#1C1418", color: "#fff", borderRadius: 12, padding: "24px", marginTop: 32 }}>
        <h3 style={{ color: "#FF6B9D", marginTop: 0, fontSize: 18 }}>🔌 Интеграция с AI Mama API</h3>
        <p style={{ color: "#ccc", fontSize: 14, marginBottom: 16 }}>
          Карта развития доступна через REST API. Подключите своего AI-агента для диалогового сбора данных и автоматических рекомендаций.
        </p>
        <div style={{ background: "#2a2022", borderRadius: 8, padding: "14px 16px", fontFamily: "monospace", fontSize: 13, color: "#e0e0e0", overflowX: "auto" }}>
          <div style={{ color: "#88cc88" }}># Создать профиль ребёнка</div>
          <div>POST /api/v1/children</div>
          <div style={{ marginTop: 8, color: "#88cc88" }}># Диалог: агент обновляет карту</div>
          <div>POST /api/v1/children/:id/dialog</div>
          <div style={{ marginTop: 8, color: "#88cc88" }}># Получить карту развития</div>
          <div>GET /api/v1/children/:id/map</div>
          <div style={{ marginTop: 8, color: "#88cc88" }}># AI-рекомендации</div>
          <div>POST /api/v1/children/:id/recommendations/refresh</div>
        </div>
        <a href="/api/v1/children/milestones/all" target="_blank" style={{ display: "inline-block", marginTop: 14, color: "#FF6B9D", fontSize: 13 }}>
          → Открыть полный справочник вех (JSON)
        </a>
      </div>
    </div>
  );
}
