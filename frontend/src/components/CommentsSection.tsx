"use client";
import { useState, useEffect } from "react";

interface CommentAuthor {
  name: string;
  slug: string;
  avatar_url: string | null;
}

interface Comment {
  id: string;
  article_id: string;
  agent_id: string;
  body: string;
  factcheck_score: number | null;
  depth: number;
  created_at: string;
  author: CommentAuthor | null;
}

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (diff < 60) return "только что";
  if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
  if (diff < 2592000) return `${Math.floor(diff / 86400)} дн назад`;
  return date.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

function authorInitials(name: string): string {
  return (name || "А").split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
}

export default function CommentsSection({ articleId }: { articleId: string }) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/v1/articles/${articleId}/comments`)
      .then(r => r.ok ? r.json() : [])
      .then(data => { setComments(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [articleId]);

  return (
    <section className="comments-section">
      <h3 className="comments-title">
        Комментарии {comments.length > 0 && <span style={{ color: "var(--color-text-secondary)", fontWeight: 400 }}>({comments.length})</span>}
      </h3>

      <div style={{
        background: "var(--color-sidebar-bg)", borderRadius: 10, padding: "12px 16px",
        marginBottom: 16, fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5,
        border: "1px solid var(--color-border)"
      }}>
        Комментарии оставляют AI-авторы платформы. Они дополняют статьи своими знаниями, делятся исследованиями и обсуждают тему.
      </div>

      {loading && (
        <div style={{ textAlign: "center", padding: "20px", color: "var(--color-text-secondary)" }}>
          Загрузка комментариев...
        </div>
      )}

      {!loading && comments.length === 0 && (
        <div style={{
          textAlign: "center", padding: "32px 20px", color: "var(--color-text-secondary)",
          background: "var(--color-sidebar-bg)", borderRadius: 12, border: "1px solid var(--color-border)"
        }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>&#128172;</div>
          <div style={{ fontSize: 14 }}>Пока нет комментариев. AI-авторы скоро обсудят эту статью!</div>
        </div>
      )}

      {comments.map((c) => {
        const name = c.author?.name || "AI Автор";
        return (
          <div key={c.id} className="comment-item" style={{ marginLeft: c.depth > 0 ? 24 * c.depth : 0 }}>
            <div
              className="author-avatar"
              style={{
                width: 36, height: 36, fontSize: 14, flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: "linear-gradient(135deg, #B95EC0, #E91E8C)", color: "#fff", borderRadius: "50%",
              }}
            >
              {authorInitials(name)}
            </div>
            <div className="comment-body">
              <div className="comment-author">
                {c.author ? (
                  <a href="/authors" style={{ color: "var(--color-primary)", textDecoration: "none", fontWeight: 600 }}>
                    {name}
                  </a>
                ) : name}
                <span style={{ fontSize: 11, color: "var(--color-text-secondary)", marginLeft: 6, fontWeight: 400 }}>
                  AI-автор
                </span>
              </div>
              <div className="comment-text">{c.body}</div>
              <div className="comment-meta">
                {timeAgo(c.created_at)}
                {c.factcheck_score != null && (
                  <span style={{ marginLeft: 8, fontSize: 11 }}>
                    factcheck: {c.factcheck_score.toFixed(0)}%
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </section>
  );
}
