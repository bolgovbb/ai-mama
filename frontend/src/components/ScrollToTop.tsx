"use client";
import { useState, useEffect } from "react";

export default function ScrollToTop() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 600);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible) return null;

  return (
    <button
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      aria-label="Наверх"
      style={{
        position: "fixed",
        bottom: 80,
        right: 24,
        width: 44,
        height: 44,
        borderRadius: "50%",
        background: "#B95EC0",
        color: "#fff",
        border: "none",
        cursor: "pointer",
        fontSize: 20,
        boxShadow: "0 4px 12px rgba(185,94,192,0.4)",
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transition: "opacity 0.2s",
      }}
    >
      ↑
    </button>
  );
}
