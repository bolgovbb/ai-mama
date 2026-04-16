"use client"
import { useState, useRef, useEffect } from "react"

const PERIODS = [
  { key: "today", label: "Сегодня" },
  { key: "yesterday", label: "Вчера" },
  { key: "week", label: "Неделя" },
  { key: "month", label: "Месяц" },
  { key: "year", label: "Год" },
  { key: "all", label: "Все время" },
]

export function getPeriodDate(key: string): Date | null {
  const now = new Date()
  switch (key) {
    case "today": { const d = new Date(now); d.setHours(0,0,0,0); return d }
    case "yesterday": { const d = new Date(now); d.setDate(d.getDate()-1); d.setHours(0,0,0,0); return d }
    case "week": { const d = new Date(now); d.setDate(d.getDate()-7); return d }
    case "month": { const d = new Date(now); d.setMonth(d.getMonth()-1); return d }
    case "year": { const d = new Date(now); d.setFullYear(d.getFullYear()-1); return d }
    default: return null
  }
}

export default function DateFilter({ onChange, initialPeriod = "today" }: { onChange: (key: string) => void; initialPeriod?: string }) {
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState(initialPeriod)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener("mousedown", h)
    return () => document.removeEventListener("mousedown", h)
  }, [])

  const label = PERIODS.find(p => p.key === selected)?.label || "Все время"

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-block", marginBottom: 12 }}>
      <button onClick={() => setOpen(!open)} style={{
        background: "none", border: "none", cursor: "pointer",
        fontSize: 15, fontWeight: 600, color: "var(--color-text)",
        display: "flex", alignItems: "center", gap: 6, padding: "6px 0",
        fontFamily: "inherit",
      }}>
        {label}
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      {open && (
        <div style={{
          position: "absolute", top: "100%", left: 0, zIndex: 50,
          background: "white", borderRadius: 12, boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
          border: "1px solid var(--color-border)", padding: "6px 0", minWidth: 160,
        }}>
          {PERIODS.map(p => (
            <button key={p.key} onClick={() => { setSelected(p.key); setOpen(false); onChange(p.key) }} style={{
              display: "block", width: "100%", textAlign: "left", padding: "8px 16px",
              background: p.key === selected ? "var(--color-primary-light)" : "none",
              border: "none", cursor: "pointer", fontSize: 14, fontFamily: "inherit",
              color: p.key === selected ? "var(--color-primary)" : "var(--color-text)",
              fontWeight: p.key === selected ? 600 : 400, borderRadius: 0,
            }}>
              {p.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
