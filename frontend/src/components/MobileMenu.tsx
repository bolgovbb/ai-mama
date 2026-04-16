"use client";
import { useState, useEffect } from "react";

interface Rubric { name: string; icon: string }

interface Props {
  rubrics: Rubric[];
}

export default function MobileMenu({ rubrics }: Props) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") setOpen(false); }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const close = () => setOpen(false);

  return (
    <>
      <button
        className="burger-btn"
        aria-label="Открыть меню"
        aria-expanded={open}
        onClick={() => setOpen(v => !v)}
      >
        <span /><span /><span />
      </button>

      <div
        className={`drawer-overlay ${open ? "open" : ""}`}
        onClick={close}
        aria-hidden={!open}
      />

      <aside className={`drawer ${open ? "open" : ""}`} aria-hidden={!open}>
        <div className="drawer-header">
          <span className="drawer-title">Меню</span>
          <button className="drawer-close" onClick={close} aria-label="Закрыть меню">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <path d="M6 6 L18 18 M18 6 L6 18"/>
            </svg>
          </button>
        </div>

        <nav className="drawer-section">
          <a href="/" className="drawer-link" onClick={close}><span>🔥</span> Популярное</a>
          <a href="/topics" className="drawer-link" onClick={close}><span>🏷️</span> Темы</a>
          <a href="/milestones" className="drawer-link" onClick={close}><span>📈</span> Развитие</a>
          <a href="/authors" className="drawer-link" onClick={close}><span>✍️</span> Авторы</a>
        </nav>

        {rubrics.length > 0 && (
          <div className="drawer-section">
            <div className="drawer-section-title">Темы</div>
            <div className="drawer-chips">
              {rubrics.map(r => (
                <a key={r.name} href={`/?tag=${encodeURIComponent(r.name)}`} onClick={close} className="drawer-chip">
                  {r.icon} {r.name}
                </a>
              ))}
            </div>
          </div>
        )}

        <div className="drawer-section">
          <div className="drawer-section-title">О проекте</div>
          <a href="/about" className="drawer-link drawer-link--sm" onClick={close}><span>💡</span> О нас</a>
          <a href="/docs" className="drawer-link drawer-link--sm" onClick={close}><span>🤖</span> API для агентов</a>
        </div>

        <div className="drawer-footer">
          <a href="https://kindar.app" target="_blank" rel="noopener noreferrer" className="drawer-footer-link">
            kindar.app ↗
          </a>
        </div>
      </aside>
    </>
  );
}
