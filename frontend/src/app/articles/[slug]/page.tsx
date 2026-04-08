import { fetchArticle } from "@/lib/api";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import ReadingProgressBar from "@/components/ReadingProgressBar";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://5.129.205.143";

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const article = await fetchArticle(params.slug);
  if (!article) return {};
  const coverImageUrl = article.cover_image
    ? `${SITE_URL}${article.cover_image}`
    : undefined;
  return {
    title: `${article.title} — AI Mama`,
    description: article.meta_description,
    openGraph: {
      title: article.title,
      description: article.meta_description ?? undefined,
      type: "article",
      images: coverImageUrl ? [{ url: coverImageUrl, width: 1200, height: 630 }] : [],
    },
    twitter: {
      card: "summary_large_image",
      title: article.title,
      description: article.meta_description ?? undefined,
      images: coverImageUrl ? [coverImageUrl] : [],
    },
  };
}

function extractHeadings(html: string): { id: string; text: string }[] {
  const headings: { id: string; text: string }[] = [];
  const re = /<h2[^>]*>(.*?)<\/h2>/gi;
  let match;
  let idx = 0;
  while ((match = re.exec(html)) !== null) {
    const text = match[1].replace(/<[^>]+>/g, "").trim();
    const id = `heading-${idx++}`;
    headings.push({ id, text });
  }
  return headings;
}

function injectHeadingIds(html: string): string {
  let idx = 0;
  return html.replace(/<h2([^>]*)>/gi, (_match, attrs) => {
    const id = `heading-${idx++}`;
    return `<h2${attrs} id="${id}">`;
  });
}

export default async function ArticlePage({ params }: { params: { slug: string } }) {
  const article = await fetchArticle(params.slug);
  if (!article) notFound();

  const bodyHtml = article.body_html || article.body_md || "";
  const headings = extractHeadings(bodyHtml);
  const bodyWithIds = injectHeadingIds(bodyHtml);

  const schemaOrg = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: article.title,
    description: article.meta_description,
    image: article.cover_image ? `${SITE_URL}${article.cover_image}` : undefined,
    datePublished: article.published_at,
    author: { "@type": "Person", name: "AI Agent" },
  };

  const publishedDate = article.published_at
    ? new Date(article.published_at).toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <div className="article-wrapper">
      <ReadingProgressBar />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaOrg) }}
      />

      {/* Hero cover image */}
      {article.cover_image ? (
        <div className="article-hero">
          <img
            src={`${SITE_URL}${article.cover_image}`}
            alt={article.title}
          />
        </div>
      ) : (
        <div className="article-hero" />
      )}

      {/* Meta: tags, date, views */}
      <div className="article-meta">
        {article.tags?.map((tag: string) => (
          <span key={tag} className="article-meta__tag">{tag}</span>
        ))}
        {publishedDate && (
          <>
            <span className="article-meta__dot">·</span>
            <time dateTime={article.published_at}>{publishedDate}</time>
          </>
        )}
        {article.views_count != null && (
          <>
            <span className="article-meta__dot">·</span>
            <span className="article-meta__views">{article.views_count.toLocaleString("ru-RU")} просмотров</span>
          </>
        )}
        {article.factcheck_score != null && (
          <>
            <span className="article-meta__dot">·</span>
            <span className="article-meta__factcheck">
              ✓ Достоверность {article.factcheck_score.toFixed(0)}%
            </span>
          </>
        )}
      </div>

      {/* Title */}
      <h1 className="article-title">{article.title}</h1>

      {/* 2-col layout: content + sidebar */}
      <div className="article-layout">
        {/* Main content */}
        <main>
          <article
            className="article-content"
            dangerouslySetInnerHTML={{ __html: bodyWithIds }}
          />

          {/* Sources */}
          {article.sources?.length > 0 && (
            <section className="article-sources">
              <h2 className="article-sources__title">Источники</h2>
              <ul className="article-sources__list">
                {article.sources.map((s: any, i: number) => (
                  <li key={i} className="article-sources__item">
                    <span className="article-sources__item-num">{i + 1}</span>
                    <div>
                      <a href={s.url} target="_blank" rel="noopener noreferrer">
                        {s.title || s.url}
                      </a>
                      {s.type && (
                        <div className="article-sources__item-type">{s.type}</div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </main>

        {/* Sidebar: TOC + factcheck score */}
        <aside className="article-sidebar">
          {headings.length > 0 && (
            <div className="article-sidebar__toc">
              <p className="article-sidebar__toc-title">Содержание</p>
              <ul className="article-sidebar__toc-list">
                {headings.map((h) => (
                  <li key={h.id}>
                    <a href={`#${h.id}`}>{h.text}</a>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {article.factcheck_score != null && (
            <div className="article-sidebar__factcheck">
              <div className="article-sidebar__factcheck-score">
                {article.factcheck_score.toFixed(0)}%
              </div>
              <div className="article-sidebar__factcheck-label">Достоверность</div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
