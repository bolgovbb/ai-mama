/**
 * Build a clean snippet/excerpt for article cards.
 *
 * Strategy:
 *  1. Prefer body_md's first paragraph after stripping the leading
 *     markdown heading (body_md reliably has newlines, so heading
 *     stripping is safe).
 *  2. Fall back to meta_description, stripping stray "##" markers at
 *     the start (some auto-generated meta fields still have them).
 */
export function buildExcerpt(
  meta: string | null | undefined,
  body: string | null | undefined,
  maxLen = 160,
): string {
  const stripCommon = (t: string) =>
    t
      .replace(/\*\*/g, "")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/\s+/g, " ")
      .trim();

  // Try body first — strip complete heading lines (requires a newline)
  const rawBody = (body || "").trim();
  if (rawBody) {
    const withoutHeadings = rawBody.replace(/^\s*#+\s+[^\n]*\n+/gm, "");
    const cleaned = stripCommon(withoutHeadings);
    if (cleaned.length >= 40) {
      return truncate(cleaned, maxLen);
    }
  }

  // Fallback: meta_description, strip any leading "# " prefix
  const rawMeta = (meta || "").trim();
  if (rawMeta) {
    const withoutLeadingHash = rawMeta.replace(/^#+\s+/, "");
    const cleaned = stripCommon(withoutLeadingHash);
    if (cleaned.length > 0) {
      return truncate(cleaned, maxLen);
    }
  }

  return "";
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  const cut = text.slice(0, maxLen);
  // Try to break on a word boundary
  const lastSpace = cut.lastIndexOf(" ");
  const base = lastSpace > maxLen * 0.6 ? cut.slice(0, lastSpace) : cut;
  return base.replace(/[,;:\s]+$/, "") + "…";
}
