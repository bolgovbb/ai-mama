"""LLM access layer. Prefers OpenRouter when OPENROUTER_API_KEY is set,
falls back to Anthropic's native API if ANTHROPIC_API_KEY is present."""
import json
import os
import re
import httpx
from app.config import settings

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-haiku-4.5")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


def _extract_json_object(text: str) -> dict | None:
    """Pull the first well-formed JSON object out of an LLM response.

    Handles: raw JSON, ```json … ``` fences, trailing prose after the
    object, and objects embedded mid-text. Returns None if nothing
    parseable is found.
    """
    if not text:
        return None
    # Strip any ```json / ``` fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1))
    # Fallback: first '{' to the matching '}' via brace balance
    first = text.find("{")
    while first != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(first, len(text)):
            c = text[i]
            if esc:
                esc = False
                continue
            if c == "\\":
                esc = True
                continue
            if c == '"' and not esc:
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[first:i + 1])
                    break
        first = text.find("{", first + 1)
        if len(candidates) > 3:
            break
    for raw in candidates:
        try:
            v = json.loads(raw)
            if isinstance(v, dict):
                return v
        except json.JSONDecodeError:
            continue
    return None

async def verify_sources(sources: list) -> dict:
    if not sources:
        return {"verified": 0, "total": 0, "score": 0.0}
    verified = sum(1 for s in sources if isinstance(s, dict) and s.get("url") and s.get("title"))
    score = min(1.0, verified / max(len(sources), 1))
    return {"verified": verified, "total": len(sources), "score": score}


async def _call_openrouter(
    system: str, user: str, max_tokens: int, api_key: str, *, json_mode: bool = False
) -> str:
    payload: dict = {
        "model": OPENROUTER_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=45) as http:
        resp = await http.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://mama.kindar.app",
                "X-Title": "AI Mama (KinDAR)",
            },
            json=payload,
        )
        if resp.status_code != 200:
            print(f"[rag] OpenRouter {resp.status_code}: {resp.text[:200]}")
            return ""
        try:
            return resp.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, ValueError) as e:
            print(f"[rag] OpenRouter parse error: {e}")
            return ""


async def _call_anthropic_direct(system: str, user: str, max_tokens: int, api_key: str) -> str:
    async with httpx.AsyncClient(timeout=45) as http:
        resp = await http.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        if resp.status_code != 200:
            print(f"[rag] Anthropic {resp.status_code}: {resp.text[:200]}")
            return ""
        try:
            return resp.json()["content"][0]["text"] or ""
        except (KeyError, IndexError, ValueError) as e:
            print(f"[rag] Anthropic parse error: {e}")
            return ""


async def _call_claude(
    system: str, user: str, max_tokens: int = 512, *, json_mode: bool = False
) -> str:
    """Generate a response via the first configured LLM provider.

    Priority: OpenRouter (OPENROUTER_API_KEY) → Anthropic direct
    (ANTHROPIC_API_KEY). Returns "" when neither is configured or when
    the call fails, so callers can keep their existing fallback logic.

    Pass ``json_mode=True`` to hint the provider to return valid JSON
    (OpenRouter will set ``response_format: json_object``). The raw
    string is still returned — use :func:`_extract_json_object` to
    parse it robustly.
    """
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    if openrouter_key:
        out = await _call_openrouter(system, user, max_tokens, openrouter_key, json_mode=json_mode)
        if out:
            return out
        # If OpenRouter fails, fall through to Anthropic if configured
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "") or settings.anthropic_api_key
    if anthropic_key:
        return await _call_anthropic_direct(system, user, max_tokens, anthropic_key)
    return ""

async def factcheck_article(title: str, body_md: str, sources: list) -> dict:
    src_check = await verify_sources(sources)
    base_score = 40.0 + src_check["score"] * 40.0

    has_llm = bool(
        os.environ.get("OPENROUTER_API_KEY", "")
        or os.environ.get("ANTHROPIC_API_KEY", "")
        or settings.anthropic_api_key
    )
    if not has_llm:
        final_score = min(100.0, base_score + len(sources) * 3)
        return {
            "score": final_score,
            "confidence": 0.6,
            "reflection_rounds": 0,
            "sources_verified": src_check["verified"],
            "sources_total": src_check["total"],
            "flags": [] if final_score >= 70 else ["low_score"],
        }

    system1 = (
        "You are a medical/parenting fact-checker. "
        "Assess factual accuracy of the article. "
        'Return ONLY a single JSON object, no prose, no markdown fences: '
        '{"score": 0-100, "flags": [list of short strings], "confidence": 0-1}'
    )
    snippet = body_md[:800]
    sources_str = json.dumps(sources[:5], ensure_ascii=False)
    prompt1 = f"Title: {title}\nSources: {sources_str}\nExcerpt:\n{snippet}"

    r1_raw = await _call_claude(system1, prompt1, json_mode=True)
    r1 = _extract_json_object(r1_raw) or {}
    try:
        r1_score = float(r1.get("score", base_score))
    except (TypeError, ValueError):
        r1_score = base_score
    r1_flags = r1.get("flags") or []
    if not isinstance(r1_flags, list):
        r1_flags = []
    try:
        r1_conf = float(r1.get("confidence", 0.7))
    except (TypeError, ValueError):
        r1_conf = 0.7
    if not r1:
        print(f"[factcheck] round1 JSON not parseable, raw head: {(r1_raw or '')[:140]!r}")

    system2 = (
        "You are reviewing a fact-check. Critique and refine. "
        'Return ONLY a single JSON object, no prose, no markdown fences: '
        '{"score": 0-100, "flags": [list], "confidence": 0-1}'
    )
    prompt2 = (
        f"Initial score: {r1_score}\n"
        f"Initial flags: {r1_flags}\n"
        f"Title: {title}\n"
        f"Sources: total={src_check['total']} verified={src_check['verified']}"
    )
    r2_raw = await _call_claude(system2, prompt2, json_mode=True)
    r2 = _extract_json_object(r2_raw) or {}
    try:
        final_score = float(r2.get("score", r1_score))
    except (TypeError, ValueError):
        final_score = r1_score
    r2_flags = r2.get("flags") or []
    if not isinstance(r2_flags, list):
        r2_flags = []
    final_flags = list({*r1_flags, *r2_flags})
    try:
        final_conf = float(r2.get("confidence", r1_conf))
    except (TypeError, ValueError):
        final_conf = r1_conf
    if not r2:
        print(f"[factcheck] round2 JSON not parseable, raw head: {(r2_raw or '')[:140]!r}")

    final_score = 0.7 * final_score + 0.3 * base_score
    if final_score < 70:
        final_flags.append("low_score")

    return {
        "score": round(final_score, 1),
        "confidence": round(final_conf, 2),
        "reflection_rounds": 2,
        "sources_verified": src_check["verified"],
        "sources_total": src_check["total"],
        "flags": final_flags,
    }

async def detect_cascade(article_id: str, reactions_count: int, comments_count: int,
                          factcheck_score: float, time_window_hours: float = 1.0) -> dict:
    velocity = (reactions_count + comments_count * 2) / max(time_window_hours, 0.1)
    risk_score = 0.0
    if velocity > 100 and factcheck_score < 60:
        risk_score = 0.9
    elif velocity > 50 and factcheck_score < 70:
        risk_score = 0.7
    elif velocity > 20 and factcheck_score < 75:
        risk_score = 0.4
    elif factcheck_score < 50:
        risk_score = 0.5
    else:
        risk_score = max(0.0, (velocity / 200) * (1 - factcheck_score / 100))

    return {
        "article_id": article_id,
        "risk_score": round(risk_score, 3),
        "velocity": round(velocity, 1),
        "flagged": risk_score > 0.6,
        "reason": "high_velocity_low_factcheck" if risk_score > 0.6 else "ok",
    }
