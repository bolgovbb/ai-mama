"use client";

import KiraChat from "./KiraChat";

export default function ArticleChat({ slug }: { slug: string }) {
  return (
    <KiraChat
      suggestionsUrl={`/api/v1/articles/${slug}/suggestions`}
      askUrl={`/api/v1/articles/${slug}/ask`}
      title="Задай вопрос по исследованию: KinDAR AI · Кира"
      welcome="Привет! 🌸 Я Кира. Задай вопрос по этой статье — или выбери подсказку ниже."
    />
  );
}
