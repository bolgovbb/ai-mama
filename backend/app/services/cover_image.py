import html
import hashlib
from typing import Optional


# 8 diverse gradient themes in kindar.app style
GRADIENT_THEMES = [
    {
        "id": "violet_pink",
        "from": "#B95EC0", "to": "#E91E8C",
        "circle1": "rgba(255,255,255,0.12)", "circle2": "rgba(255,255,255,0.07)",
        "wave": "rgba(0,0,0,0.18)",
    },
    {
        "id": "deep_purple",
        "from": "#7B4FBF", "to": "#C764B8",
        "circle1": "rgba(255,255,255,0.10)", "circle2": "rgba(255,255,255,0.06)",
        "wave": "rgba(0,0,0,0.20)",
    },
    {
        "id": "magenta_violet",
        "from": "#9B59B6", "to": "#E91E8C",
        "circle1": "rgba(255,255,255,0.09)", "circle2": "rgba(255,255,255,0.05)",
        "wave": "rgba(0,0,0,0.15)",
    },
    {
        "id": "royal_purple",
        "from": "#6C3483", "to": "#B95EC0",
        "circle1": "rgba(255,255,255,0.11)", "circle2": "rgba(255,255,255,0.07)",
        "wave": "rgba(0,0,0,0.22)",
    },
    {
        "id": "hot_pink",
        "from": "#8E24AA", "to": "#D81B60",
        "circle1": "rgba(255,255,255,0.10)", "circle2": "rgba(255,255,255,0.06)",
        "wave": "rgba(0,0,0,0.18)",
    },
    {
        "id": "electric_violet",
        "from": "#7B1FA2", "to": "#E040FB",
        "circle1": "rgba(255,255,255,0.08)", "circle2": "rgba(255,255,255,0.05)",
        "wave": "rgba(0,0,0,0.16)",
    },
    {
        "id": "rose_purple",
        "from": "#9C27B0", "to": "#F06292",
        "circle1": "rgba(255,255,255,0.12)", "circle2": "rgba(255,255,255,0.07)",
        "wave": "rgba(0,0,0,0.20)",
    },
    {
        "id": "orchid",
        "from": "#6A1B9A", "to": "#BA68C8",
        "circle1": "rgba(255,255,255,0.09)", "circle2": "rgba(255,255,255,0.06)",
        "wave": "rgba(0,0,0,0.18)",
    },
]


def _get_theme_by_slug(slug: str, tags: list[str]) -> dict:
    """Pick one of 8 themes based on slug hash for variety."""
    hash_input = (slug or '') + (''.join(tags or []))
    hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    return GRADIENT_THEMES[hash_val % len(GRADIENT_THEMES)]


def _wrap_text(text: str, max_chars: int = 38) -> list[str]:
    """Wrap text into lines of max_chars, split by words."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= 3:
            break
    if current and len(lines) < 3:
        lines.append(current)
    return lines[:3]


def generate_cover_svg(
    title: str,
    tags: Optional[list[str]] = None,
    category_label: Optional[str] = None,
    slug: Optional[str] = None,
) -> str:
    """
    Generate a 800x400 SVG cover image for an article.
    Uses 8 rotating gradient themes in kindar.app style.
    Includes decorative geometric elements.
    """
    theme = _get_theme_by_slug(slug or title, tags or [])
    label = category_label or (tags[0] if tags else "AI Mama")
    label = label[:24]  # Limit label length

    safe_title = html.escape(title)
    safe_label = html.escape(label)

    lines = _wrap_text(title, 38)
    safe_lines = [html.escape(line) for line in lines]

    # Text Y positions (lower third ~250-370)
    base_y = 255 if len(safe_lines) == 3 else (270 if len(safe_lines) == 2 else 290)
    line_height = 52
    text_elements = ""
    for i, line in enumerate(safe_lines):
        y = base_y + i * line_height
        text_elements += f'  <text x="56" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="38" font-weight="700" fill="white">{line}</text>\n'

    # Label pill width estimate
    label_width = len(safe_label) * 11 + 28

    svg = f"""<svg width="800" height="400" viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{theme['from']}"/>
      <stop offset="100%" stop-color="{theme['to']}"/>
    </linearGradient>
    <linearGradient id="overlay" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="20%" stop-color="rgba(0,0,0,0)"/>
      <stop offset="100%" stop-color="rgba(0,0,0,0.55)"/>
    </linearGradient>
    <filter id="blur1">
      <feGaussianBlur stdDeviation="2"/>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="800" height="400" fill="url(#bg)"/>

  <!-- Decorative circles (large, blurred) -->
  <circle cx="680" cy="70" r="140" fill="{theme['circle1']}" filter="url(#blur1)"/>
  <circle cx="720" cy="320" r="90" fill="{theme['circle2']}" filter="url(#blur1)"/>
  <circle cx="90" cy="40" r="75" fill="{theme['circle1']}" filter="url(#blur1)"/>
  <circle cx="790" cy="200" r="160" fill="{theme['circle2']}" filter="url(#blur1)"/>

  <!-- Small accent circles -->
  <circle cx="160" cy="340" r="30" fill="rgba(255,255,255,0.08)"/>
  <circle cx="600" cy="60" r="20" fill="rgba(255,255,255,0.10)"/>
  <circle cx="400" cy="30" r="40" fill="rgba(255,255,255,0.06)"/>

  <!-- Wave decoration at bottom -->
  <path d="M0 280 Q160 250 320 275 Q480 300 640 270 Q720 255 800 265 L800 400 L0 400 Z" fill="{theme['wave']}"/>
  <path d="M0 305 Q200 285 400 300 Q600 315 800 295 L800 400 L0 400 Z" fill="rgba(0,0,0,0.10)"/>

  <!-- Gradient overlay for text readability -->
  <rect width="800" height="400" fill="url(#overlay)"/>

  <!-- Tag/Category label pill -->
  <rect x="48" y="44" width="{label_width}" height="30" rx="15" fill="rgba(255,255,255,0.22)"/>
  <text x="62" y="64" font-family="Arial, Helvetica, sans-serif" font-size="13" fill="white" font-weight="600">{safe_label}</text>

  <!-- Title text -->
{text_elements}
  <!-- Bottom accent line -->
  <rect x="56" y="{base_y + len(safe_lines) * line_height + 8}" width="60" height="3" rx="2" fill="rgba(255,255,255,0.5)"/>
</svg>"""

    return svg
