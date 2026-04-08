import html
from typing import Optional

# Color schemes by category
CATEGORY_THEMES = {
    "беременность": {"from": "#FFE4EE", "to": "#FFF0F5", "accent": "#FF6B9D", "label": "Беременность"},
    "питание": {"from": "#E8F5E9", "to": "#F1F8E9", "accent": "#43A047", "label": "Питание"},
    "здоровье": {"from": "#E8F5E9", "to": "#F1F8E9", "accent": "#43A047", "label": "Здоровье"},
    "развитие": {"from": "#E3F2FD", "to": "#F3E5F5", "accent": "#7B1FA2", "label": "Развитие"},
    "роды": {"from": "#FFF3E0", "to": "#FFF8E1", "accent": "#EF6C00", "label": "Роды"},
    "новорожденный": {"from": "#E3F2FD", "to": "#EDE7F6", "accent": "#5E35B1", "label": "Новорождённый"},
    "грудное вскармливание": {"from": "#FCE4EC", "to": "#FFF8E1", "accent": "#E91E63", "label": "ГВ"},
    "сон": {"from": "#E8EAF6", "to": "#EDE7F6", "accent": "#3F51B5", "label": "Сон"},
}

DEFAULT_THEME = {"from": "#FFE4EE", "to": "#FAF9F7", "accent": "#FF6B9D", "label": "AI Mama"}


def _get_theme(tags: list[str]) -> dict:
    for tag in (tags or []):
        key = tag.lower().strip()
        for k, v in CATEGORY_THEMES.items():
            if k in key or key in k:
                return v
    return DEFAULT_THEME


def _wrap_text(text: str, max_chars: int = 40) -> list[str]:
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
    if current:
        lines.append(current)
    return lines[:3]  # max 3 lines


def generate_cover_svg(title: str, tags: Optional[list[str]] = None, category_label: Optional[str] = None) -> str:
    """Generate a 1200x630 SVG cover image for an article."""
    theme = _get_theme(tags or [])
    label = category_label or (tags[0].title() if tags else theme["label"])
    
    # Escape HTML entities
    safe_title = html.escape(title)
    safe_label = html.escape(label[:20])
    
    # Wrap title text
    lines = _wrap_text(title, 38)
    safe_lines = [html.escape(l) for l in lines]
    
    # Text Y positions (bottom third area ~430-570)
    base_y = 460
    line_height = 60
    text_elements = ""
    for i, line in enumerate(safe_lines):
        y = base_y + i * line_height
        text_elements += f'''
    <text x="60" y="{y}" 
          font-family="Georgia, 'Times New Roman', serif" 
          font-size="44" font-weight="700" fill="white"
          filter="url(#shadow)">{line}</text>'''

    svg = f'''<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{theme["from"]}" />
      <stop offset="100%" stop-color="{theme["to"]}" />
    </linearGradient>
    <linearGradient id="overlayGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="30%" stop-color="transparent" />
      <stop offset="100%" stop-color="rgba(28,20,24,0.72)" />
    </linearGradient>
    <filter id="shadow">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="rgba(0,0,0,0.4)" />
    </filter>
  </defs>

  <!-- Background gradient -->
  <rect width="1200" height="630" fill="url(#bgGrad)" />

  <!-- Decorative circles -->
  <circle cx="980" cy="120" r="240" fill="white" opacity="0.06" />
  <circle cx="1150" cy="450" r="180" fill="white" opacity="0.04" />
  <circle cx="80"  cy="520" r="120" fill="white" opacity="0.05" />
  <circle cx="600" cy="-30" r="160" fill="{theme["accent"]}" opacity="0.07" />

  <!-- Decorative pattern dots -->
  <circle cx="200" cy="80"  r="4" fill="{theme["accent"]}" opacity="0.2" />
  <circle cx="280" cy="50"  r="3" fill="{theme["accent"]}" opacity="0.15" />
  <circle cx="350" cy="100" r="5" fill="{theme["accent"]}" opacity="0.12" />
  <circle cx="450" cy="60"  r="3" fill="{theme["accent"]}" opacity="0.18" />

  <!-- Heart icon (maternal theme) -->
  <path d="M 1050 160 C 1050 140, 1030 120, 1010 135 C 990 120, 970 140, 970 160 C 970 180, 1010 210, 1010 210 C 1010 210, 1050 180, 1050 160 Z"
        fill="{theme["accent"]}" opacity="0.15" />

  <!-- Bottom overlay for text readability -->
  <rect width="1200" height="630" fill="url(#overlayGrad)" />

  <!-- Logo top-left -->
  <text x="48" y="58" 
        font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
        font-size="30" font-weight="800" fill="{theme["accent"]}">AI Mama</text>

  <!-- Category tag pill -->
  <rect x="48" y="76" width="160" height="34" rx="17" fill="white" opacity="0.9" />
  <text x="128" y="99" text-anchor="middle"
        font-family="-apple-system, BlinkMacSystemFont, sans-serif"
        font-size="14" font-weight="600" fill="{theme["accent"]}">{safe_label}</text>

  <!-- Article title text -->
  {text_elements}
</svg>'''
    return svg.strip()
