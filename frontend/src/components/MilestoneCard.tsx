"use client";
import { useState } from "react";

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

const DOMAIN_COLORS: Record<string, string> = {
  speech: "#B95EC0",
  motor_fine: "#E91E8C",
  motor_gross: "#45B7D1",
  cognitive: "#4ECDC4",
  social: "#F59E0B",
  emotional: "#22C55E",
};

export default function MilestoneCard({ milestone }: { milestone: MilestoneData }) {
  const [isOpen, setIsOpen] = useState(false);
  const color = DOMAIN_COLORS[milestone.domain] || "#B95EC0";
  const hasContent = milestone.norm_text || milestone.exercises?.length || milestone.concern_text;

  return (
    <div
      style={{
        background: "var(--color-sidebar-bg)",
        borderRadius: 12,
        border: `1px solid ${isOpen ? color + "40" : "var(--color-border)"}`,
        marginBottom: 8,
        overflow: "hidden",
        transition: "border-color 0.2s",
      }}
    >
      <button
        onClick={() => hasContent && setIsOpen(!isOpen)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "flex-start",
          gap: 10,
          padding: "12px 14px",
          background: "transparent",
          border: "none",
          cursor: hasContent ? "pointer" : "default",
          textAlign: "left",
          color: "inherit",
          fontFamily: "inherit",
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: color,
            marginTop: 5,
            flexShrink: 0,
          }}
        />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: "var(--color-text)" }}>
            {milestone.title}
          </div>
          {milestone.description && (
            <div style={{ color: "var(--color-text-secondary)", fontSize: 13, marginTop: 2 }}>
              {milestone.description}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 5, flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, background: color + "15", color: color, padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
              {milestone.age_months_min}&ndash;{milestone.age_months_max} мес
            </span>
            {milestone.age_months_concern && (
              <span style={{ fontSize: 11, background: "#FEF3C7", color: "#D97706", padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
                к врачу после {milestone.age_months_concern} мес
              </span>
            )}
            <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{milestone.source}</span>
          </div>
        </div>
        {hasContent && (
          <div style={{ fontSize: 18, color: "var(--color-text-secondary)", transition: "transform 0.2s", transform: isOpen ? "rotate(180deg)" : "rotate(0deg)", flexShrink: 0, marginTop: 2 }}>
            &#9660;
          </div>
        )}
      </button>

      {isOpen && hasContent && (
        <div style={{ padding: "0 14px 16px 32px" }}>
          {milestone.norm_text && (
            <div style={{ background: "#F0FDF4", borderRadius: 10, padding: "12px 14px", marginBottom: 10, border: "1px solid #BBF7D0" }}>
              <div style={{ fontWeight: 700, fontSize: 12, color: "#16A34A", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>
                Норма ВОЗ
              </div>
              <div style={{ fontSize: 13, color: "#15803D", lineHeight: 1.5 }}>{milestone.norm_text}</div>
            </div>
          )}

          {milestone.exercises && milestone.exercises.length > 0 && (
            <div style={{ background: "#F0E4F7", borderRadius: 10, padding: "12px 14px", marginBottom: 10, border: "1px solid #E2C6F0" }}>
              <div style={{ fontWeight: 700, fontSize: 12, color: "#7E22CE", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>
                Упражнения
              </div>
              {milestone.exercises.map((ex, i) => (
                <div key={i} style={{ marginBottom: i < milestone.exercises!.length - 1 ? 10 : 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, color: "#581C87" }}>
                    {i + 1}. {ex.title}
                  </div>
                  <div style={{ fontSize: 13, color: "#6B21A8", lineHeight: 1.5, marginTop: 2 }}>
                    {ex.description}
                  </div>
                  {ex.frequency && (
                    <div style={{ fontSize: 11, color: "#9333EA", marginTop: 3, fontStyle: "italic" }}>
                      {ex.frequency}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {milestone.concern_text && (
            <div style={{ background: "#FFF7ED", borderRadius: 10, padding: "12px 14px", border: "1px solid #FED7AA" }}>
              <div style={{ fontWeight: 700, fontSize: 12, color: "#C2410C", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>
                Когда к врачу
              </div>
              <div style={{ fontSize: 13, color: "#9A3412", lineHeight: 1.5 }}>{milestone.concern_text}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
