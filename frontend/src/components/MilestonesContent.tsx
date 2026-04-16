"use client";
import { useState } from "react";
import MilestoneCard from "@/components/MilestoneCard";

interface Exercise {
  title: string;
  description: string;
  frequency?: string;
}

interface MilestoneData {
  code: string;
  domain: string;
  title: string;
  description: string | null;
  age_months_min: number;
  age_months_max: number;
  age_months_concern: number | null;
  source: string;
  norm_text: string | null;
  concern_text: string | null;
  exercises: Exercise[] | null;
}

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

const AGE_OPTIONS = [
  { key: "all", label: "Все возрасты" },
  { key: "0-3", label: "0–3 мес" },
  { key: "3-6", label: "3–6 мес" },
  { key: "6-9", label: "6–9 мес" },
  { key: "9-12", label: "9–12 мес" },
  { key: "12-18", label: "12–18 мес" },
  { key: "18-24", label: "18–24 мес" },
  { key: "24-36", label: "2–3 года" },
];

const AGE_LABELS: Record<string, string> = {
  "0-3": "0–3 месяца",
  "3-6": "3–6 месяцев",
  "6-9": "6–9 месяцев",
  "9-12": "9–12 месяцев",
  "12-18": "12–18 месяцев",
  "18-24": "18–24 месяца",
  "24-36": "2–3 года",
};

const DOMAIN_ORDER = ["speech", "motor_gross", "motor_fine", "cognitive", "social", "emotional"];

function getAgeGroup(min: number, max: number): string {
  if (max <= 3) return "0-3";
  if (max <= 6) return "3-6";
  if (max <= 9) return "6-9";
  if (max <= 12) return "9-12";
  if (max <= 18) return "12-18";
  if (max <= 24) return "18-24";
  return "24-36";
}

export default function MilestonesContent({ milestones }: { milestones: MilestoneData[] }) {
  const [selectedAge, setSelectedAge] = useState("all");

  const filtered = selectedAge === "all"
    ? milestones
    : milestones.filter(m => getAgeGroup(m.age_months_min, m.age_months_max) === selectedAge);

  // Group filtered milestones by domain
  const byDomain: Record<string, MilestoneData[]> = {};
  for (const domain of DOMAIN_ORDER) {
    const items = filtered.filter(m => m.domain === domain);
    if (items.length > 0) byDomain[domain] = items;
  }

  return (
    <div>
      {/* Age Filter — compact horizontal scroll */}
      <div style={{
        background: "var(--color-card, #fff)",
        borderRadius: 12,
        padding: "10px 0",
        marginBottom: 20,
        border: "1px solid var(--color-border, #e5e7eb)",
        position: "sticky",
        top: 56,
        zIndex: 10,
        boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
      }}>
        <div style={{
          display: "flex",
          gap: 6,
          overflowX: "auto",
          WebkitOverflowScrolling: "touch",
          scrollbarWidth: "none",
          padding: "0 14px",
          alignItems: "center",
        }}>
          {AGE_OPTIONS.map(opt => (
            <button
              key={opt.key}
              onClick={() => setSelectedAge(opt.key)}
              style={{
                padding: "6px 16px",
                borderRadius: 20,
                border: "none",
                background: selectedAge === opt.key ? "#B95EC0" : "var(--color-sidebar-bg, #f3f4f6)",
                color: selectedAge === opt.key ? "#fff" : "var(--color-text, #333)",
                fontSize: 13,
                fontWeight: selectedAge === opt.key ? 700 : 500,
                cursor: "pointer",
                transition: "all 0.15s",
                fontFamily: "inherit",
                whiteSpace: "nowrap",
                flexShrink: 0,
              }}
            >
              {opt.label}
            </button>
          ))}
          {selectedAge !== "all" && (
            <span style={{ fontSize: 12, color: "var(--color-text-secondary, #999)", whiteSpace: "nowrap", flexShrink: 0, marginLeft: 4 }}>
              ({filtered.length} вех)
            </span>
          )}
        </div>
      </div>

      {/* No results */}
      {Object.keys(byDomain).length === 0 && (
        <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--color-text-secondary, #666)" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
          <div style={{ fontSize: 16, fontWeight: 600 }}>Нет вех для выбранного возраста</div>
          <div style={{ fontSize: 14, marginTop: 4 }}>Попробуйте выбрать другой период</div>
        </div>
      )}

      {/* Domain sections */}
      {DOMAIN_ORDER.filter(d => byDomain[d]).map(domain => {
        const items = byDomain[domain];
        const color = DOMAIN_COLORS[domain] || "#B95EC0";

        // Group by age within domain
        const byAge: Record<string, MilestoneData[]> = {};
        for (const m of items) {
          const ag = getAgeGroup(m.age_months_min, m.age_months_max);
          if (!byAge[ag]) byAge[ag] = [];
          byAge[ag].push(m);
        }

        const exerciseCount = items.reduce((s, m) => s + (m.exercises?.length || 0), 0);

        return (
          <div key={domain} id={`domain-${domain}`} style={{
            marginBottom: 28,
            background: "var(--color-card, #fff)",
            borderRadius: 16,
            padding: 20,
            border: "1px solid var(--color-border, #e5e7eb)",
          }}>
            {/* Domain header */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 12,
                background: color + "15",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 22,
              }}>
                {DOMAIN_ICONS[domain]}
              </div>
              <div>
                <h3 style={{ fontSize: 17, margin: 0, fontWeight: 700, color: color }}>
                  {DOMAIN_LABELS[domain] || domain}
                </h3>
                <div style={{ fontSize: 12, color: "var(--color-text-secondary, #666)" }}>
                  {items.length} вех &middot; {exerciseCount} упражнений
                </div>
              </div>
            </div>
            <div style={{ height: 3, background: color, borderRadius: 2, marginBottom: 16, opacity: 0.6 }} />

            {/* Age groups */}
            {Object.entries(byAge)
              .sort(([a], [b]) => {
                const order = ["0-3","3-6","6-9","9-12","12-18","18-24","24-36"];
                return order.indexOf(a) - order.indexOf(b);
              })
              .map(([ag, ageItems]) => (
                <div key={ag}>
                  <div style={{
                    display: "inline-flex", alignItems: "center", gap: 6,
                    fontSize: 13, fontWeight: 600, color: color,
                    background: color + "10", padding: "4px 12px", borderRadius: 8,
                    marginBottom: 8, marginTop: 8,
                  }}>
                    📅 {AGE_LABELS[ag] || ag}
                    <span style={{ fontSize: 11, color: "var(--color-text-secondary, #666)", fontWeight: 400 }}>
                      {ageItems.length} {ageItems.length === 1 ? "веха" : "вех"}
                    </span>
                  </div>
                  {ageItems.map((m) => (
                    <MilestoneCard key={m.code} milestone={m} />
                  ))}
                </div>
              ))}
          </div>
        );
      })}
    </div>
  );
}
