"use client";

import { usePathname, useRouter } from "next/navigation";

const ACTIVE = "#E91E8C";
const INACTIVE = "#9CA3AF";

interface IconProps { active?: boolean; size?: number }

function HomeIcon({ active, size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {active ? (
        <>
          <path d="M3 10.5L12 3L21 10.5V20C21 20.55 20.55 21 20 21H4C3.45 21 3 20.55 3 20V10.5Z" fill={ACTIVE} />
          <rect x="9" y="14" width="6" height="7" rx="1" fill="white" />
        </>
      ) : (
        <>
          <path d="M3 10.5L12 3L21 10.5V20C21 20.55 20.55 21 20 21H4C3.45 21 3 20.55 3 20V10.5Z" stroke={INACTIVE} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          <rect x="9" y="14" width="6" height="7" rx="1" stroke={INACTIVE} strokeWidth="1.5" />
        </>
      )}
    </svg>
  );
}

function TopicsIcon({ active, size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {active ? (
        <>
          <path d="M20.59 13.41L13.42 20.58a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82Z" fill={ACTIVE} />
          <circle cx="7" cy="7" r="1.7" fill="white" />
        </>
      ) : (
        <>
          <path d="M20.59 13.41L13.42 20.58a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82Z" stroke={INACTIVE} strokeWidth="1.8" strokeLinejoin="round" />
          <circle cx="7" cy="7" r="1.7" stroke={INACTIVE} strokeWidth="1.5" />
        </>
      )}
    </svg>
  );
}

function AiIcon({ size = 22 }: IconProps) {
  // Always white on the gradient center
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="4" y="6" width="16" height="13" rx="4" fill="white" opacity="0.95" />
      <circle cx="9" cy="12" r="1.5" fill="#7B2FBE" />
      <circle cx="15" cy="12" r="1.5" fill="#7B2FBE" />
      <rect x="9" y="15.5" width="6" height="1.5" rx="0.75" fill="#7B2FBE" />
      <line x1="12" y1="2" x2="12" y2="6" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="2" r="1.5" fill="white" />
    </svg>
  );
}

function TrendIcon({ active, size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {active ? (
        <>
          <path d="M3 17 L9 11 L13 15 L21 7" stroke={ACTIVE} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          <path d="M15 7 H21 V13" stroke={ACTIVE} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          <circle cx="9" cy="11" r="2" fill={ACTIVE} />
          <circle cx="13" cy="15" r="2" fill={ACTIVE} />
        </>
      ) : (
        <>
          <path d="M3 17 L9 11 L13 15 L21 7" stroke={INACTIVE} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          <path d="M15 7 H21 V13" stroke={INACTIVE} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </>
      )}
    </svg>
  );
}

function AuthorsIcon({ active, size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {active ? (
        <>
          <circle cx="12" cy="8" r="4.5" fill={ACTIVE} />
          <path d="M4 21C4 17.13 7.58 14 12 14C16.42 14 20 17.13 20 21" fill={ACTIVE} />
        </>
      ) : (
        <>
          <circle cx="12" cy="8" r="4" stroke={INACTIVE} strokeWidth="1.8" />
          <path d="M4 21C4 17.13 7.58 14 12 14C16.42 14 20 17.13 20 21" stroke={INACTIVE} strokeWidth="1.8" strokeLinecap="round" />
        </>
      )}
    </svg>
  );
}

export default function MobileBottomNav() {
  const pathname = usePathname() || "/";
  const router = useRouter();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname === href || pathname.startsWith(href + "/");
  };

  // Кира AI center button → dedicated /ai page
  const handleAiClick = (e: React.MouseEvent) => {
    e.preventDefault();
    router.push("/ai");
  };

  type LinkItem = { kind: "link"; href: string; label: string; Icon: (p: IconProps) => JSX.Element };
  type CenterItem = { kind: "center"; label: string; onClick: (e: React.MouseEvent) => void };
  const items: (LinkItem | CenterItem)[] = [
    { kind: "link", href: "/", label: "Лента", Icon: HomeIcon },
    { kind: "link", href: "/topics", label: "Темы", Icon: TopicsIcon },
    { kind: "center", label: "Кира AI", onClick: handleAiClick },
    { kind: "link", href: "/milestones", label: "Развитие", Icon: TrendIcon },
    { kind: "link", href: "/authors", label: "Авторы", Icon: AuthorsIcon },
  ];

  return (
    <nav className="mnav" aria-label="Основная навигация">
      <div className="mnav__bar">
        {items.map((item) => {
          if (item.kind === "center") {
            const active = pathname === "/ai" || pathname.startsWith("/ai/");
            return (
              <a
                key="ai"
                href="#ask"
                onClick={item.onClick}
                className="mnav__item mnav__item--center"
                aria-label={item.label}
              >
                <span
                  className={`mnav__orb${active ? " mnav__orb--active" : ""}`}
                  aria-hidden="true"
                >
                  <span className="mnav__orb-shine" />
                  <span className="mnav__orb-icon">
                    <AiIcon />
                  </span>
                </span>
                <span className={`mnav__label mnav__label--center${active ? " mnav__label--active-center" : ""}`}>
                  {item.label}
                </span>
              </a>
            );
          }
          const active = isActive(item.href);
          const Icon = item.Icon;
          return (
            <a
              key={item.href}
              href={item.href}
              className="mnav__item"
              aria-current={active ? "page" : undefined}
            >
              {active && <span className="mnav__active-pill" aria-hidden="true" />}
              <span className="mnav__icon">
                <Icon active={active} size={22} />
              </span>
              <span className={`mnav__label${active ? " mnav__label--active" : ""}`}>
                {item.label}
              </span>
            </a>
          );
        })}
      </div>
    </nav>
  );
}
