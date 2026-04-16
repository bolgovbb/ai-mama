import type { Metadata } from "next";
import KiraChat from "@/components/KiraChat";

export const metadata: Metadata = {
  title: "Кира AI — помощник мамы | AI Mama",
  description:
    "Кира — AI-ассистент журнала AI Mama. Ответит на вопросы о беременности, развитии, материнстве — со ссылками на статьи с проверенными фактами.",
  alternates: { canonical: "https://mama.kindar.app/ai" },
};

export const dynamic = "force-dynamic";

export default function KiraAiPage() {
  return (
    <div className="kira-page">
      <header className="kira-page__hero">
        <div className="kira-page__orb" aria-hidden="true">
          <svg width="56" height="56" viewBox="0 0 80 80">
            <defs>
              <linearGradient id="kira-page-orb" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#E91E8C" />
                <stop offset="100%" stopColor="#7B2FBE" />
              </linearGradient>
            </defs>
            <polygon points="40,4 76,40 40,76 4,40" fill="url(#kira-page-orb)" />
            <polygon points="40,18 62,40 40,62 18,40" fill="white" opacity="0.18" />
            <circle cx="40" cy="40" r="14" fill="white" opacity="0.95" />
            <polygon points="68,6 76,14 68,22 60,14" fill="#F06292" opacity="0.7" />
          </svg>
        </div>
        <h1 className="kira-page__title">
          <span className="kira-page__spark">✦</span> Кира AI
        </h1>
        <p className="kira-page__subtitle">
          Помощница мамы в журнале AI Mama. Ответит на вопросы о беременности,
          развитии и воспитании — со ссылками на статьи с проверкой фактов.
        </p>
      </header>

      <KiraChat
        suggestionsUrl="/api/v1/ai/suggestions"
        askUrl="/api/v1/ai/ask"
        title="KinDAR AI · Кира"
        welcome="Привет! 🌸 Я Кира — AI-ассистент журнала AI Mama. Задай вопрос о беременности, малыше, прикорме или материнстве. Я отвечу со ссылками на статьи."
        placeholder="Задай Кире любой вопрос…"
        variant="page"
      />

      <p className="kira-page__disclaimer">
        Ответы Киры — не медицинская консультация. При сомнениях обращайтесь к врачу.
      </p>
    </div>
  );
}
