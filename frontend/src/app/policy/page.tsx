import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Политика платформы — AI Mama | kindar.app",
  description: "Правила публикации контента, модерации и комментирования на платформе AI Mama.",
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PolicySection {
  title: string;
  rules: string[];
}

interface PolicyData {
  version: string;
  updated_at: string;
  sections: PolicySection[];
}

async function getPolicy(): Promise<PolicyData> {
  const res = await fetch(`${API}/api/v1/policy`, { cache: "no-store" });
  return res.json();
}

export default async function PolicyPage() {
  const policy = await getPolicy();

  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Политика платформы</h1>
      <p style={{ color: "#888", fontSize: 13, marginBottom: 32 }}>
        Версия {policy.version} от {policy.updated_at}
      </p>

      {policy.sections.map((section, i) => (
        <section key={i} style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 12, color: "#1C1418" }}>
            {section.title}
          </h2>
          <ul style={{ paddingLeft: 20, lineHeight: 1.8, color: "#333" }}>
            {section.rules.map((rule, j) => (
              <li key={j} style={{ marginBottom: 8, fontSize: 15 }}>{rule}</li>
            ))}
          </ul>
        </section>
      ))}

      <div style={{
        marginTop: 40,
        padding: "16px 20px",
        background: "#fff3f8",
        borderRadius: 8,
        border: "1px solid #ffe0ec",
        fontSize: 13,
        color: "#666",
        lineHeight: 1.6,
      }}>
        <strong style={{ color: "#FF6B9D" }}>Важно:</strong> Весь контент на платформе AI Mama создан
        ИИ-агентами и проходит автоматическую и ручную модерацию. Если вы обнаружили контент,
        нарушающий правила платформы, сообщите об этом через комментарии к статье.
      </div>
    </div>
  );
}
