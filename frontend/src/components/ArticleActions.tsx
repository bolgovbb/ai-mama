"use client";
import { useState, useEffect } from "react";

interface Props {
  articleId: string;
  slug: string;
  title: string;
  initialViews: number;
}

export default function ArticleActions({ articleId, slug, title, initialViews }: Props) {
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Load from localStorage
    const likes = JSON.parse(localStorage.getItem("ai-mama-likes") || "{}");
    const bookmarks = JSON.parse(localStorage.getItem("ai-mama-bookmarks") || "[]");
    if (likes[articleId]) setLiked(true);
    if (bookmarks.includes(articleId)) setSaved(true);

    // Load like count from API
    fetch(`/api/v1/articles/${slug}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setLikeCount(data.reactions_count || 0); })
      .catch(() => {});
  }, [articleId, slug]);

  const handleLike = () => {
    const likes = JSON.parse(localStorage.getItem("ai-mama-likes") || "{}");
    if (liked) {
      delete likes[articleId];
      setLikeCount(prev => Math.max(0, prev - 1));
    } else {
      likes[articleId] = true;
      setLikeCount(prev => prev + 1);
    }
    localStorage.setItem("ai-mama-likes", JSON.stringify(likes));
    setLiked(!liked);
  };

  const handleSave = () => {
    const bookmarks: string[] = JSON.parse(localStorage.getItem("ai-mama-bookmarks") || "[]");
    if (saved) {
      const filtered = bookmarks.filter(id => id !== articleId);
      localStorage.setItem("ai-mama-bookmarks", JSON.stringify(filtered));
    } else {
      bookmarks.push(articleId);
      localStorage.setItem("ai-mama-bookmarks", JSON.stringify(bookmarks));
    }
    setSaved(!saved);
  };

  const handleShare = async () => {
    const url = `https://mama.kindar.app/articles/${slug}`;
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
        return;
      } catch {}
    }
    // Fallback: copy to clipboard
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  return (
    <div className="reactions-bar">
      <button
        className={`reaction-btn ${liked ? "active" : ""}`}
        onClick={handleLike}
        style={{
          background: liked ? "#F0E4F7" : "transparent",
          color: liked ? "#B95EC0" : "inherit",
          borderColor: liked ? "#B95EC0" : undefined,
        }}
      >
        {liked ? "❤️" : "🤍"} {likeCount > 0 ? likeCount : "Нравится"}
      </button>
      <button
        className={`reaction-btn ${saved ? "active" : ""}`}
        onClick={handleSave}
        style={{
          background: saved ? "#FEF3C7" : "transparent",
          color: saved ? "#D97706" : "inherit",
          borderColor: saved ? "#D97706" : undefined,
        }}
      >
        {saved ? "★" : "☆"} {saved ? "Сохранено" : "Сохранить"}
      </button>
      <button className="reaction-btn" onClick={handleShare}>
        {copied ? "✓ Скопировано" : "↗ Поделиться"}
      </button>
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12, color: "var(--color-text-secondary)", fontSize: 13 }}>
        <span>👁 {initialViews}</span>
      </div>
    </div>
  );
}
