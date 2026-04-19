# ТЗ: SEO + GEO для AI Mama (mama.kindar.app)

_Дата аудита: 2026-04-20. Автор: Claude Opus 4.6._

## 0. Что такое SEO и GEO

- **SEO** — классическое продвижение в Google / Yandex / Bing.
- **GEO** (Generative Engine Optimization) — оптимизация под ответные движки на базе LLM: ChatGPT Search, Perplexity, Google AI Overview, Yandex Нейро, Bing Copilot. LLM ходят по сайту как обычные краулеры + читают специальные файлы (`llms.txt`), прямо цитируют контент и ставят ссылки в ответ пользователю.

Ключевая разница: для SEO важны ранги и клики; для GEO важно, чтобы LLM **взял готовый факт** из статьи и **сослался на неё по имени** в ответе.

---

## 1. Находки аудита

### 🔴 Критичные (ломают SEO прямо сейчас)

| # | Находка | Следствие |
|---|---|---|
| C1 | `sitemap.xml` выдаёт URL'ы с **`http://5.129.205.143/…`** вместо `https://mama.kindar.app/…` | Google/Yandex идут по IP → получают другой хост → URL не индексируется |
| C2 | `/robots.txt` — **404** | Краулеры не знают правила, sitemap не заявлен |
| C3 | На главной `/` — **0 `<h1>`**, **нет `og:image`** | Главная плохо ранжируется, нет превью в соцсетях |
| C4 | Нет **HSTS** заголовка | Понижает trust у Google, уязвимость перед SSL stripping |

### 🟡 Важные (ухудшают позиции и цитируемость LLM)

| # | Находка | Следствие |
|---|---|---|
| W1 | На статьях только 4 базовых JSON-LD (`Organization`, `WebSite`, `Article`, `BreadcrumbList`). Нет `MedicalWebPage` / `FAQPage` / `HowTo` | Google'у сложнее показать rich-snippet, LLM не может быстро извлечь FAQ-пары |
| W2 | Нет `/llms.txt` и `/llms-full.txt` | ChatGPT/Perplexity/Yandex Нейро проходят мимо рекомендованной для них индексации |
| W3 | Нет verification-меток Yandex Вебмастер / Google Search Console | Мы не видим, как поисковики нас видят, и не получаем сигналы индексации |
| W4 | На странице автора нет JSON-LD `Person` / `ProfilePage` | E-E-A-T хромает — "кто написал?" непонятно |
| W5 | Часть обложек `.webp` шла с `Content-Type: text/plain` | **(уже починено в предыдущих коммитах)** |
| W6 | `meta_description` иногда начинается с `##` markdown-мусора | OG preview на ссылках показывает `## Title…` |

### 🟢 То, что уже сделано хорошо

- SSR — весь контент виден без JS (самое важное для LLM-краулеров: OpenAI `GPTBot` и Google `Google-Extended` не умеют JS).
- Canonical URL на статьях, `<html lang="ru">`, `robots: index, follow`.
- Open Graph / Twitter полные (включая `article:published_time`, `article:author`, `article:tag`).
- Article JSON-LD с `articleBody` (критично для content analytics у Яндекса + для цитируемости у LLM).
- Все image-обложки теперь `image/webp` (после фикса mime-types).
- Sitemap существует, даже если с битыми URL'ами — багу легко фиксить.

---

## 2. План

### Этап 1 — критичные правки (делаем сразу)

- [x] **Fix sitemap.xml**: использовать `settings.site_url` (`https://mama.kindar.app`), добавить `<lastmod>` из `published_at`, включить `/`, `/topics`, `/authors`, `/milestones`, `/ai`, `/about`, `/articles/*`, `/authors/*`.
- [x] **Add `/robots.txt`** endpoint с правилами: разрешить всё, запретить `/api/`, указать `Sitemap:`, отдельно разрешить `GPTBot`, `ClaudeBot`, `PerplexityBot`, `YandexBot`, `Google-Extended`.
- [x] **Home page (`/`)**: добавить `<h1>AI Mama — умный журнал для молодых мам</h1>` и `og:image`.
- [x] **HSTS**: `Strict-Transport-Security: max-age=31536000; includeSubDomains` через FastAPI middleware.

### Этап 2 — GEO для LLM-движков (делаем сразу)

- [x] **`/llms.txt`** — короткая TLDR платформы + ссылки на ключевые разделы. Стандарт от llmstxt.org.
- [x] **`/llms-full.txt`** — полный каталог опубликованных статей с заголовками и URL. Это «карта контента для LLM», которую Perplexity/ChatGPT подхватывают.
- [x] **Article JSON-LD → `@type: MedicalWebPage`** + наследуется от Article. Добавить `medicalAudience: Parent`, `lastReviewed`, `reviewedBy` (редактор-агент).
- [x] **FAQPage schema**: если в body_md есть H2, которые звучат как вопросы («Когда…?», «Почему…?», «Сколько…?»), автоматически собирать `FAQPage` с `mainEntity: Question[]` с первым абзацем после H2 как `acceptedAnswer.text`.
- [x] **Enriched article front matter**: перед телом статьи добавить видимый блок `TL;DR` — 2-3 предложения с ответом на главный вопрос статьи. LLM извлекает именно такие блоки в первую очередь. (Реализация: на фронте чекать, есть ли в `meta_description` строка длиной 120-250 символов — выводить её в рамке перед `article-content`.)

### Этап 3 — E-E-A-T / авторитетность

- [x] **Author page JSON-LD**: `ProfilePage` + `mainEntity: { @type: Person, knowsAbout, affiliation: Organization }`.
- [x] **Yandex Вебмастер + Google Search Console verification**: добавить `<meta name="yandex-verification" content="__"/>` и `<meta name="google-site-verification" content="__"/>` как пустые placeholders, чтобы пользователь вставил настоящие коды.

### Этап 4 — точечные правки контента (опционально)

- [ ] Очистить `meta_description` у статей, где начинается с `## ` (для всей таблицы articles — `UPDATE articles SET meta_description = regexp_replace(meta_description, '^#+\s+', '')`).
- [ ] Добавить `alt` для всех img внутри `.article-content` на уровне markdown→html конвертации.
- [ ] Для обложек, сгенерированных Flux/Imagen, задавать `alt = title` (сейчас alt пустой).

### Этап 5 — мониторинг

- Яндекс.Метрика **Контентная аналитика** уже подключена (schema.org/json-ld).
- Проверять в Yandex Вебмастере индексацию.
- Раз в месяц — ручной тест: «спроси ChatGPT про прикорм — сошлётся ли он на mama.kindar.app?»

---

## 3. Ожидаемый эффект

- Google + Yandex начнут индексировать все URL корректно (вместо IP).
- Rich-snippets у ~20 статей с FAQ-like структурой (вопрос-ответ в SERP).
- ChatGPT / Perplexity / Яндекс Нейро получают `llms.txt` → при запросах про материнство чаще ссылаются на нас по имени.
- На странице автора виден авторитет (E-E-A-T), что повышает rank для YMYL-тем (health-related).
