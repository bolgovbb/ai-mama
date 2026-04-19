"""Vision-based moderation of article cover images.

Uses OpenRouter → Claude Haiku 4.5 (vision) to spot the typical
generative-AI artifacts on illustrations: detached limbs, extra
limbs, mangled hands/fingers, distorted faces, stray objects that
don't match the topic. Returns a cheap yes/no decision with a short
list of human-readable issues.

Falls back to a no-op "ok" when the image is unreachable or the LLM
call fails — we never want a broken image-check step to stall the
editor pipeline.
"""
from __future__ import annotations

import base64
import json
import os
import re
from typing import Optional

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Gemini 2.5 Flash catches generative-AI anatomy artifacts more reliably
# than Claude Haiku/Sonnet in side-by-side testing on our own covers.
OPENROUTER_VISION_MODEL = os.environ.get(
    "OPENROUTER_VISION_MODEL", "google/gemini-2.5-flash"
)

SYSTEM_PROMPT = (
    "Ты — редактор обложек детского журнала AI Mama. Проверяешь иллюстрации, "
    "сгенерированные нейросетью, ТОЛЬКО на анатомические и генеративные "
    "дефекты. Темой и смыслом обложки НЕ занимайся — это отдельная роль.\n\n"
    "ЧЕК-ЛИСТ (отметь только то, что реально видно):\n"
    "A) Отдельные / плавающие части тела (руки, кисти, ноги, стопы, пальцы), "
    "которые не принадлежат ни одному из видимых персонажей.\n"
    "B) Частичные фигуры взрослых / врачей / родителей: торчащая рука, плечо, "
    "кусок халата или одежды без головы / без туловища на заднем плане или сбоку.\n"
    "C) Лишние конечности у персонажей (3+ руки, 3+ ноги, дубли).\n"
    "D) Деформированные кисти и пальцы: 6+ пальцев, сросшиеся, искривлённые, "
    "непонятная форма кисти.\n"
    "E) Два носа, два рта, искажённые глаза, сдвинутые черты лица.\n"
    "F) Предметы, проходящие сквозь тела (стетоскоп сквозь шею и т.п.).\n"
    "G) Непонятные мягкие объекты, которые явно выглядят как отвалившаяся "
    "часть тела или одежды без владельца.\n\n"
    "НЕ ФЛАГАЙ следующее (это НЕ дефект):\n"
    "— Стилизованную мультяшную анатомию: короткие ножки-сосиски, круглые "
    "кисти без разделённых пальцев в едином стиле, большие головы.\n"
    "— Размытые / неразборчивые надписи и лейблы.\n"
    "— Несоответствие обложки теме, отсутствие гаджетов/предметов из заголовка.\n"
    "— Настроение/эмоции персонажей, композицию, цвет.\n"
    "— Частично обрезанные рамкой фигуры (это кадрирование, а не дефект).\n\n"
    "Отвечай СТРОГО одним JSON-объектом, без markdown-обёртки и без прозы:\n"
    '{"ok": true|false, "issues": ["короткое описание дефекта на русском", "..."]}\n\n'
    "Правила решения:\n"
    "— Если нашёл хотя бы один дефект из A–G — ok=false и опиши его.\n"
    "— Иначе — ok=true, issues=[]."
)


def _extract_json(raw: str) -> dict | None:
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    start = raw.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(raw)):
            c = raw[i]
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
                    try:
                        v = json.loads(raw[start : i + 1])
                        if isinstance(v, dict):
                            return v
                    except json.JSONDecodeError:
                        pass
                    break
        start = raw.find("{", start + 1)
    return None


_EXT_MIME = {
    "webp": "image/webp",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
}


async def _fetch_image_bytes(url: str, timeout: int = 20) -> Optional[tuple[bytes, str]]:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
        resp = await http.get(url)
        if resp.status_code != 200:
            return None
        # Prefer content-type header when it's actually an image; otherwise
        # infer from the URL extension (our nginx mis-serves .webp as
        # text/plain but the bytes are valid).
        hdr = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        if hdr.startswith("image/"):
            ctype = hdr
        else:
            ext = re.sub(r"^.*\.", "", url.split("?", 1)[0]).lower()
            ctype = _EXT_MIME.get(ext)
            if not ctype:
                # Last resort: check magic bytes.
                head = resp.content[:16]
                if head.startswith(b"RIFF") and b"WEBP" in head:
                    ctype = "image/webp"
                elif head.startswith(b"\xff\xd8\xff"):
                    ctype = "image/jpeg"
                elif head.startswith(b"\x89PNG"):
                    ctype = "image/png"
                else:
                    return None
        return resp.content, ctype


async def review_cover_image(image_url: str, article_title: str = "") -> dict:
    """Return {'ok': bool, 'issues': list[str], 'reviewed': bool}.

    'reviewed' is False when the image can't be fetched or the model can't
    be reached — callers should treat that as "unknown, don't touch".
    """
    default_ok = {"ok": True, "issues": [], "reviewed": False}

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key or not image_url:
        return default_ok

    fetched = await _fetch_image_bytes(image_url)
    if not fetched:
        return default_ok
    img_bytes, ctype = fetched
    b64 = base64.b64encode(img_bytes).decode("ascii")
    data_url = f"data:{ctype};base64,{b64}"

    user_content = [
        {
            "type": "text",
            "text": (
                f"Заголовок статьи: «{article_title}».\n"
                "Проверь обложку и верни JSON по правилам из system-промпта."
            ),
        },
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    try:
        async with httpx.AsyncClient(timeout=45) as http:
            resp = await http.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://mama.kindar.app",
                    "X-Title": "AI Mama (cover review)",
                },
                json={
                    "model": OPENROUTER_VISION_MODEL,
                    "max_tokens": 300,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            if resp.status_code != 200:
                print(f"[image_review] {resp.status_code}: {resp.text[:200]}")
                return default_ok
            content = resp.json()["choices"][0]["message"].get("content") or ""
    except Exception as e:
        print(f"[image_review] request failed: {e}")
        return default_ok

    parsed = _extract_json(content)
    if not parsed:
        print(f"[image_review] JSON parse fail, raw head: {content[:160]!r}")
        return default_ok

    ok = bool(parsed.get("ok", True))
    issues_raw = parsed.get("issues") or []
    if not isinstance(issues_raw, list):
        issues_raw = []
    issues = [str(i).strip() for i in issues_raw if str(i).strip()]
    return {"ok": ok, "issues": issues[:5], "reviewed": True}
