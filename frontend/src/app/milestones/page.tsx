import { fetchMilestones, Milestone } from "@/lib/api";
import MilestoneCard from "@/components/MilestoneCard";
import MilestonesContent from "@/components/MilestonesContent";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Карта развития ребёнка от 0 до 3 лет",
  description: "Интерактивный трекер развития ребёнка по стандартам ВОЗ и CDC. 31 веха, 80+ упражнений по 6 доменам: речь, моторика, когнитивное, социальное и эмоциональное развитие.",
  alternates: { canonical: "https://mama.kindar.app/milestones" },
  openGraph: {
    title: "Карта развития ребёнка от 0 до 3 лет — AI Mama | kindar.app",
    description: "Интерактивный трекер по ВОЗ/CDC с упражнениями и красными флагами",
    url: "https://mama.kindar.app/milestones",
    type: "website",
  },
};

const DOMAIN_LABELS: Record<string, string> = {
  speech: "Речь и коммуникация",
  motor_fine: "Мелкая моторика",
  motor_gross: "Крупная моторика",
  cognitive: "Когнитивное развитие",
  social: "Социализация",
  emotional: "Эмоциональное развитие",
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
  speech: "#B95EC0",
  motor_fine: "#E91E8C",
  motor_gross: "#45B7D1",
  cognitive: "#4ECDC4",
  social: "#F59E0B",
  emotional: "#22C55E",
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

const DOMAIN_ORDER = [
  "speech",
  "motor_fine",
  "motor_gross",
  "cognitive",
  "social",
  "emotional",
];

const AGE_ORDER = [
  "0-3",
  "3-6",
  "6-9",
  "9-12",
  "12-18",
  "18-24",
  "24-36",
];

function getAgeGroup(min: number, max: number): string {
  if (max <= 3) return "0-3";
  if (max <= 6) return "3-6";
  if (max <= 9) return "6-9";
  if (max <= 12) return "9-12";
  if (max <= 18) return "12-18";
  if (max <= 24) return "18-24";
  return "24-36";
}

export default async function MilestonesPage() {
  const milestones = await fetchMilestones();

  const totalExercises = milestones.reduce(
    (sum, m) => sum + (m.exercises?.length ?? 0),
    0
  );

  // Group by domain then by age group
  const grouped: Record<string, Record<string, Milestone[]>> = {};
  for (const domain of DOMAIN_ORDER) {
    grouped[domain] = {};
    for (const age of AGE_ORDER) {
      grouped[domain][age] = [];
    }
  }
  for (const m of milestones) {
    const domain = m.domain;
    const ageKey = getAgeGroup(m.age_months_min, m.age_months_max);
    if (grouped[domain] && grouped[domain][ageKey]) {
      grouped[domain][ageKey].push(m);
    }
  }

  // Domain stats
  const domainStats: Record<string, { count: number; exercises: number }> = {};
  for (const domain of DOMAIN_ORDER) {
    const domainMilestones = milestones.filter((m) => m.domain === domain);
    domainStats[domain] = {
      count: domainMilestones.length,
      exercises: domainMilestones.reduce(
        (sum, m) => sum + (m.exercises?.length ?? 0),
        0
      ),
    };
  }

  // FAQ Schema from milestones data
  const faqItems = milestones.filter(m => m.norm_text && m.concern_text).slice(0, 15).map(m => ({
    "@type": "Question",
    "name": `Когда ребёнок должен: ${m.title.toLowerCase()}?`,
    "acceptedAnswer": {
      "@type": "Answer",
      "text": `${m.norm_text || ''} ${m.concern_text || ''}`.trim(),
    }
  }));

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": faqItems,
  };

  const speakableSchema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    "name": "Карта развития ребёнка от 0 до 3 лет",
    "speakable": {
      "@type": "SpeakableSpecification",
      "cssSelector": ["h1", "h2", ".milestone-norm", ".milestone-concern"]
    },
    "url": "https://mama.kindar.app/milestones"
  };

  return (
    <main style={{ fontFamily: "'Inter', sans-serif", background: "#F8F9FB", minHeight: "100vh" }}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(speakableSchema) }} />

      {/* Hero Section */}
      <section
        style={{
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 50%, #B95EC0 100%)",
          padding: "72px 24px 64px",
          textAlign: "center",
          color: "#fff",
        }}
      >
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <div
            style={{
              display: "inline-block",
              background: "rgba(255,255,255,0.18)",
              borderRadius: 24,
              padding: "6px 20px",
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              marginBottom: 20,
            }}
          >
            Трекер развития
          </div>
          <h1
            style={{
              fontSize: "clamp(32px, 5vw, 52px)",
              fontWeight: 800,
              margin: "0 0 18px",
              lineHeight: 1.15,
              letterSpacing: "-0.02em",
            }}
          >
            Карта развития ребёнка
          </h1>
          <p
            style={{
              fontSize: "clamp(16px, 2vw, 20px)",
              opacity: 0.88,
              margin: "0 0 36px",
              lineHeight: 1.6,
              maxWidth: 620,
              marginLeft: "auto",
              marginRight: "auto",
            }}
          >
            Интерактивный трекер ключевых этапов развития от рождения до 3 лет.
            Основан на международных стандартах ВОЗ и CDC, дополнен практическими
            упражнениями для каждого этапа.
          </p>

          {/* Badges */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "center",
              gap: 12,
            }}
          >
            {[
              { label: "6 доменов развития", icon: "🗂️" },
              { label: `${milestones.length} вех`, icon: "📍" },
              { label: `${totalExercises}+ упражнений`, icon: "🎯" },
              { label: "Стандарты ВОЗ/CDC", icon: "✅" },
            ].map((badge) => (
              <span
                key={badge.label}
                style={{
                  background: "rgba(255,255,255,0.22)",
                  border: "1px solid rgba(255,255,255,0.35)",
                  borderRadius: 32,
                  padding: "8px 18px",
                  fontSize: 14,
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: 7,
                }}
              >
                <span>{badge.icon}</span>
                {badge.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 20px" }}>

        {/* Domain Overview Grid */}
        <section style={{ padding: "56px 0 0" }}>
          <h2
            style={{
              fontSize: 26,
              fontWeight: 700,
              color: "#1A1A2E",
              marginBottom: 8,
              textAlign: "center",
            }}
          >
            Домены развития
          </h2>
          <p
            style={{
              textAlign: "center",
              color: "#6B7280",
              fontSize: 15,
              marginBottom: 32,
            }}
          >
            Нажмите на карточку, чтобы перейти к соответствующему разделу
          </p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
              gap: 18,
            }}
          >
            {DOMAIN_ORDER.map((domain) => {
              const color = DOMAIN_COLORS[domain];
              const stats = domainStats[domain];
              return (
                <a
                  key={domain}
                  href={`#domain-${domain}`}
                  style={{
                    textDecoration: "none",
                    display: "block",
                    background: "#fff",
                    borderRadius: 16,
                    padding: "24px 22px",
                    boxShadow: "0 2px 12px rgba(0,0,0,0.07)",
                    border: `2px solid transparent`,
                    transition: "box-shadow 0.2s, border-color 0.2s",
                    borderTop: `4px solid ${color}`,
                  }}
                >
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 12,
                      background: `${color}18`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 24,
                      marginBottom: 14,
                    }}
                  >
                    {DOMAIN_ICONS[domain]}
                  </div>
                  <div
                    style={{
                      fontSize: 16,
                      fontWeight: 700,
                      color: "#1A1A2E",
                      marginBottom: 10,
                    }}
                  >
                    {DOMAIN_LABELS[domain]}
                  </div>
                  <div style={{ display: "flex", gap: 14 }}>
                    <span
                      style={{
                        fontSize: 13,
                        color: "#6B7280",
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      <span
                        style={{
                          display: "inline-block",
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: color,
                        }}
                      />
                      {stats.count} вех
                    </span>
                    <span
                      style={{
                        fontSize: 13,
                        color: "#6B7280",
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      <span
                        style={{
                          display: "inline-block",
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: color,
                          opacity: 0.5,
                        }}
                      />
                      {stats.exercises} упражнений
                    </span>
                  </div>
                </a>
              );
            })}
          </div>
        </section>

        {/* How to Use */}
        <section
          style={{
            margin: "48px 0 0",
            background: "linear-gradient(135deg, #EEF2FF 0%, #F3E8FF 100%)",
            borderRadius: 20,
            padding: "32px 36px",
          }}
        >
          <h2
            style={{
              fontSize: 20,
              fontWeight: 700,
              color: "#1A1A2E",
              marginBottom: 20,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <span>📖</span> Как пользоваться трекером
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
              gap: 18,
            }}
          >
            {[
              {
                num: "1",
                title: "Выберите возраст",
                text: "Найдите нужный возрастной период вашего ребёнка в разделе каждого домена.",
              },
              {
                num: "2",
                title: "Изучите вехи",
                text: "Каждая веха — конкретный навык с описанием и признаками достижения.",
              },
              {
                num: "3",
                title: "Практикуйтесь",
                text: "Используйте упражнения для каждой вехи, чтобы помочь ребёнку развиваться.",
              },
              {
                num: "4",
                title: "Отмечайте прогресс",
                text: "Фиксируйте достижения в приложении mama.kindar.app для отслеживания динамики.",
              },
            ].map((step) => (
              <div key={step.num} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                <div
                  style={{
                    minWidth: 32,
                    height: 32,
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #667eea, #B95EC0)",
                    color: "#fff",
                    fontWeight: 800,
                    fontSize: 14,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  {step.num}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14, color: "#1A1A2E", marginBottom: 4 }}>
                    {step.title}
                  </div>
                  <div style={{ fontSize: 13, color: "#4B5563", lineHeight: 1.5 }}>
                    {step.text}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Milestones with age filter */}
        <section style={{ padding: "56px 0 0" }}>
          <MilestonesContent milestones={milestones as any} />
        </section>

        {/* API Block */}
        <section
          style={{
            margin: "16px 0 64px",
            background: "#1A1A2E",
            borderRadius: 20,
            padding: "40px 40px",
            color: "#fff",
          }}
        >
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 32,
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ maxWidth: 520 }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  background: "rgba(255,255,255,0.1)",
                  borderRadius: 8,
                  padding: "4px 12px",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  marginBottom: 16,
                  color: "#A5B4FC",
                }}
              >
                REST API
              </div>
              <h2
                style={{
                  fontSize: 22,
                  fontWeight: 800,
                  margin: "0 0 12px",
                  lineHeight: 1.3,
                }}
              >
                Интеграция через REST API
              </h2>
              <p
                style={{
                  fontSize: 14,
                  opacity: 0.75,
                  lineHeight: 1.65,
                  margin: "0 0 20px",
                }}
              >
                Все данные о вехах и упражнениях доступны через открытый REST API.
                Вы можете интегрировать базу знаний kindar в собственные приложения
                или исследовательские проекты.
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                {[
                  { label: "GET /api/milestones", desc: "Все вехи" },
                  { label: "GET /api/milestones/{code}", desc: "Конкретная веха" },
                  { label: "GET /api/domains", desc: "Список доменов" },
                ].map((ep) => (
                  <div
                    key={ep.label}
                    style={{
                      background: "rgba(255,255,255,0.07)",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: 8,
                      padding: "8px 14px",
                    }}
                  >
                    <div
                      style={{
                        fontFamily: "'Courier New', monospace",
                        fontSize: 12,
                        color: "#A5B4FC",
                        marginBottom: 2,
                      }}
                    >
                      {ep.label}
                    </div>
                    <div style={{ fontSize: 11, opacity: 0.6 }}>{ep.desc}</div>
                  </div>
                ))}
              </div>
            </div>
            <div
              style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 12,
                padding: "20px 24px",
                fontFamily: "'Courier New', monospace",
                fontSize: 13,
                color: "#E2E8F0",
                minWidth: 280,
              }}
            >
              <div style={{ color: "#6EE7B7", marginBottom: 6 }}>
                # Пример запроса
              </div>
              <div style={{ color: "#A5B4FC" }}>curl \</div>
              <div style={{ paddingLeft: 16, opacity: 0.8 }}>
                https://api.kindar.app/api/milestones
              </div>
              <div style={{ marginTop: 14, color: "#6EE7B7" }}>
                # Ответ
              </div>
              <div style={{ opacity: 0.75, marginTop: 4, lineHeight: 1.6 }}>
                {"{"}
                <br />
                {"  "}"total": {milestones.length},{"\n"}
                <br />
                {"  "}"milestones": [...]
                <br />
                {"}"}
              </div>
            </div>
          </div>
        </section>

      </div>
    </main>
  );
}
