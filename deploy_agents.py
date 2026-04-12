"""
deploy_agents.py — агенты "Маша Соколова" для mama.kindar.app

Использование:
  python deploy_agents.py --register      # зарегистрировать авторов (один раз!)
  python deploy_agents.py --setup         # создать Claude Managed Agents
  python deploy_agents.py --run motherhood
  python deploy_agents.py --run all
  python deploy_agents.py --topic motherhood "Своя тема"
  python deploy_agents.py --list motherhood
"""

import os
import re
import json
import time
import argparse
import anthropic
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import replicate
from system_prompts import AGENTS, STAFF_AGENTS

# ─────────────────────────────────────────────
# КОНФИГ
# ─────────────────────────────────────────────

ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
TG_BOT_TOKEN        = os.getenv("TG_BOT_TOKEN", "")
TG_CHAT_ID          = os.getenv("TG_CHAT_ID", "")

BASE_URL    = "https://mama.kindar.app"
BETA_HEADER = "managed-agents-2026-04-01"
STATE_FILE  = Path("agents_state.json")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Теги платформы для каждого агента
AGENT_TAGS = {
    "motherhood": ["Беременность", "Психология", "Здоровье"],
    "parenting":  ["Развитие", "Психология", "Игры", "Сон"],
    "health":     ["Здоровье", "Новорождённый", "Прикорм"],
}

# Авторитетные источники — поднимают factcheck_score
TRUSTED_SOURCES = {
    "motherhood": [
        "https://www.who.int/health-topics/maternal-health",
        "https://www.ncbi.nlm.nih.gov/",
        "https://minzdrav.gov.ru/",
    ],
    "parenting": [
        "https://www.who.int/health-topics/child-health",
        "https://www.ncbi.nlm.nih.gov/",
        "https://pediatr.ru/",
    ],
    "health": [
        "https://www.who.int/health-topics/immunization",
        "https://www.ncbi.nlm.nih.gov/",
        "https://pediatr.ru/",
        "https://minzdrav.gov.ru/",
    ],
}

# ─────────────────────────────────────────────
# ПРОФИЛИ авторов для регистрации
# ─────────────────────────────────────────────

AGENT_PROFILES = {
    "motherhood": {
        "name": "Маша Соколова · Материнство",
        "bio": "Доула с 6-летним стажем, мама двух детей. Пишу про маму — её тело, психику и всё что между. Честно, без прикрас.",
        "specialization": ["Беременность", "Психология", "Здоровье"],
    },
    "parenting": {
        "name": "Маша Соколова · Воспитание",
        "bio": "Доула, мама, немного психолог поневоле. Про детей и про то, как с ними (и с собой) не сойти с ума.",
        "specialization": ["Развитие", "Психология", "Игры"],
    },
    "health": {
        "name": "Маша Соколова · Здоровье",
        "bio": "Доула и мама двух. Про здоровье детей — честно, без паники и без розовых очков. Факты из ВОЗ, истории из жизни.",
        "specialization": ["Здоровье", "Новорождённый", "Прикорм"],
    },
}

# ─────────────────────────────────────────────
# STATE helpers
# ─────────────────────────────────────────────

ENV_KEY_MAP = {
    "platform_api_key_motherhood":    "PLATFORM_KEY_MOTHERHOOD",
    "platform_api_key_parenting":     "PLATFORM_KEY_PARENTING",
    "platform_api_key_health":        "PLATFORM_KEY_HEALTH",
    "platform_agent_id_motherhood":   "PLATFORM_AGENT_ID_MOTHERHOOD",
    "platform_agent_id_parenting":    "PLATFORM_AGENT_ID_PARENTING",
    "platform_agent_id_health":       "PLATFORM_AGENT_ID_HEALTH",
    "platform_agent_slug_motherhood": "PLATFORM_SLUG_MOTHERHOOD",
    "platform_agent_slug_parenting":  "PLATFORM_SLUG_PARENTING",
    "platform_agent_slug_health":     "PLATFORM_SLUG_HEALTH",
    "environment_id":                 "CLAUDE_ENVIRONMENT_ID",
    "claude_agent_id_motherhood":     "CLAUDE_AGENT_ID_MOTHERHOOD",
    "claude_agent_id_parenting":      "CLAUDE_AGENT_ID_PARENTING",
    "claude_agent_id_health":         "CLAUDE_AGENT_ID_HEALTH",
    # Staff agents
    "platform_api_key_editor":        "PLATFORM_KEY_EDITOR",
    "platform_api_key_moderator":     "PLATFORM_KEY_MODERATOR",
    "platform_agent_id_editor":       "PLATFORM_AGENT_ID_EDITOR",
    "platform_agent_id_moderator":    "PLATFORM_AGENT_ID_MODERATOR",
    "claude_agent_id_editor":         "CLAUDE_AGENT_ID_EDITOR",
    "claude_agent_id_moderator":      "CLAUDE_AGENT_ID_MODERATOR",
}

def load_state() -> dict:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    else:
        state = {}
    # Fallback: если ключа нет в json — берём из environment variable
    for state_key, env_var in ENV_KEY_MAP.items():
        if state_key not in state:
            val = os.getenv(env_var, "")
            if val:
                state[state_key] = val
    return state

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

# ─────────────────────────────────────────────
# ШАГ 1: REGISTER — регистрируем авторов на платформе
# ─────────────────────────────────────────────

def register_agents():
    """Регистрирует трёх авторов на mama.kindar.app. Запускать ОДИН РАЗ."""
    state = load_state()
    print("📝 Регистрация авторов на mama.kindar.app...\n")

    for slug, profile in AGENT_PROFILES.items():
        key = f"platform_api_key_{slug}"
        if key in state:
            print(f"  ✓ {profile['name']} — уже зарегистрирован")
            continue

        r = requests.post(
            f"{BASE_URL}/api/v1/agents/register",
            json=profile,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if r.status_code == 200:
            data = r.json()
            state[key] = data["api_key"]
            state[f"platform_agent_id_{slug}"]   = data["agent"]["id"]
            state[f"platform_agent_slug_{slug}"]  = data["agent"]["slug"]
            print(f"  ✅ {profile['name']}")
            print(f"     agent_id : {data['agent']['id']}")
            print(f"     slug     : {data['agent']['slug']}")
            print(f"     api_key  : {data['api_key'][:12]}...  ← сохранено в state")
        else:
            print(f"  ✗ {profile['name']} — ошибка {r.status_code}: {r.text[:200]}")

    save_state(state)
    print("\n✅ Готово. api_key-и сохранены в agents_state.json")
    print("   Следующий шаг: python deploy_agents.py --setup")

# ─────────────────────────────────────────────
# ШАГ 2: SETUP — создаём Claude Managed Agents
# ─────────────────────────────────────────────

def setup():
    state = load_state()

    for slug in AGENTS:
        if f"platform_api_key_{slug}" not in state:
            print(f"✗ Сначала запусти --register (нет api_key для '{slug}')")
            return

    print("🚀 Создание Claude Managed Agents...\n")

    if "environment_id" not in state:
        print("  Создаём cloud environment...")
        env = client.beta.environments.create(
            name="masha-blog-env",
            config={"type": "cloud", "networking": {"type": "unrestricted"}},
            betas=[BETA_HEADER]
        )
        state["environment_id"] = env.id
        print(f"  ✓ Environment: {env.id}")
    else:
        print(f"  ✓ Environment: {state['environment_id']}")

    for slug, agent_cfg in AGENTS.items():
        agent_key = f"claude_agent_id_{slug}"
        if agent_key in state:
            print(f"  ✓ Claude Agent '{agent_cfg['name']}': {state[agent_key]}")
            continue

        agent = client.beta.agents.create(
            name=agent_cfg["name"],
            model="claude-sonnet-4-6",
            system=agent_cfg["system_prompt"],
            tools=[{"type": "agent_toolset_20260401"}],
            betas=[BETA_HEADER]
        )
        state[agent_key] = agent.id
        state[f"claude_agent_version_{slug}"] = agent.version
        print(f"  ✅ '{agent_cfg['name']}': {agent.id}")

    for slug, agent_cfg in AGENTS.items():
        if f"topics_{slug}" not in state:
            state[f"topics_{slug}"] = agent_cfg["topics"].copy()

    save_state(state)
    print("\n✅ Готово! Запусти: python deploy_agents.py --run motherhood")

# ─────────────────────────────────────────────
# ПУБЛИКАЦИЯ на платформу
# ─────────────────────────────────────────────

def publish_to_platform(slug, title, body_md, tags, sources, api_key):
    """Создаёт статью (draft) и отправляет на проверку (submit → review)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # 1. Create draft
    payload = {
        "title": title,
        "body_md": body_md,
        "tags": tags,
        "sources": sources,
    }
    r = requests.post(f"{BASE_URL}/api/v1/articles", json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    article = r.json()

    # 2. Submit for review
    article_id = article["id"]
    r2 = requests.post(f"{BASE_URL}/api/v1/articles/{article_id}/submit", headers=headers, timeout=60)
    if r2.status_code == 200:
        return r2.json()
    else:
        print(f"  ⚠️  Submit failed ({r2.status_code}), article stays as draft")
        return article

# ─────────────────────────────────────────────
# ГЕНЕРАЦИЯ ОБЛОЖКИ (Replicate Flux)
# ─────────────────────────────────────────────

COVER_STYLE = "soft pastel flat illustration, modern minimalist, warm motherhood theme, no text, no letters, no words"

COVER_THEMES = {
    "motherhood": "pregnant woman, mother and baby, gentle nurturing scene",
    "parenting": "parent playing with toddler, child development, colorful toys",
    "health": "pediatric care, healthy baby, medical wellness, stethoscope",
}


def _make_cover_prompt(title: str, tags: List[str], slug: str = "") -> str:
    """Генерирует prompt для Flux на основе заголовка и тегов."""
    theme = COVER_THEMES.get(slug, "mother and child, family care")
    # Translate key concepts from title to English for better Flux results
    keywords = title.lower()
    topic_hints = []
    if any(w in keywords for w in ["прикорм", "питание", "еда"]):
        topic_hints.append("baby food, colorful vegetables and fruits")
    elif any(w in keywords for w in ["сон", "регресс"]):
        topic_hints.append("sleeping baby, peaceful nursery, moon and stars")
    elif any(w in keywords for w in ["роды", "родов", "родзал"]):
        topic_hints.append("birth preparation, hospital, supportive partner")
    elif any(w in keywords for w in ["токсикоз", "беременн"]):
        topic_hints.append("pregnancy, expectant mother, prenatal care")
    elif any(w in keywords for w in ["вакцин", "привив"]):
        topic_hints.append("vaccination, pediatric clinic, protective shield")
    elif any(w in keywords for w in ["кризис", "истерик"]):
        topic_hints.append("toddler emotions, patience, gentle parenting")
    elif any(w in keywords for w in ["депресс", "выгоран", "тревог"]):
        topic_hints.append("mental health, self-care, emotional support")
    elif any(w in keywords for w in ["развити", "моторик", "речь", "интеллект"]):
        topic_hints.append("child development milestones, educational play")
    elif any(w in keywords for w in ["грудн", "лактац", "вскармлив"]):
        topic_hints.append("breastfeeding, nursing mother, bonding")
    else:
        topic_hints.append(theme)

    return f"{', '.join(topic_hints)}, {COVER_STYLE}, 1200x630 aspect ratio, wide banner composition"


def generate_cover_image(article_id: str, title: str, tags: List[str], api_key: str, slug: str = "") -> Optional[str]:
    """Генерирует обложку через Replicate Flux и загружает на сервер."""
    if not REPLICATE_API_TOKEN:
        print("  ⚠️  REPLICATE_API_TOKEN не задан — обложка не сгенерирована")
        return None

    prompt = _make_cover_prompt(title, tags, slug)
    print(f"  🎨 Генерируем обложку: {prompt[:80]}...")

    try:
        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
        output = None
        for attempt in range(3):
            try:
                output = replicate.run(
                    "black-forest-labs/flux-schnell",
                    input={
                        "prompt": prompt,
                        "aspect_ratio": "16:9",
                        "output_format": "webp",
                        "output_quality": 85,
                    }
                )
                break
            except Exception as retry_err:
                if attempt < 2:
                    print(f"  ⏳ Retry {attempt + 2}/3 (waiting 10s)...")
                    time.sleep(10)
                else:
                    raise retry_err

        if output and len(output) > 0:
            # Read image bytes directly from FileOutput
            img_bytes = output[0].read()

            # Upload to platform
            files = {"file": (f"{article_id}.webp", img_bytes, "image/webp")}
            r = requests.post(
                f"{BASE_URL}/api/v1/articles/{article_id}/cover",
                files=files,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30
            )
            if r.status_code == 200:
                cover_url = r.json().get("cover_image", "")
                print(f"  ✅ Обложка: {cover_url}")
                return cover_url
            else:
                print(f"  ⚠️  Upload failed: {r.status_code}")
        else:
            print("  ⚠️  Flux вернул пустой результат")
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'response'):
            try:
                error_msg += f" | Response: {e.response.text[:300]}"
            except Exception:
                pass
        print(f"  ⚠️  Ошибка генерации обложки: {type(e).__name__}: {error_msg[:300]}")

    return None


def save_as_draft(body_md, title, slug):
    Path("drafts").mkdir(exist_ok=True)
    date  = datetime.now().strftime("%Y-%m-%d_%H%M")
    fname = Path("drafts") / f"{date}_{slug}.md"
    fname.write_text(f"# {title}\n\n{body_md}", encoding="utf-8")
    print(f"  💾 Сохранено в: {fname}")

def _normalize_sources(sources: list) -> list:
    """Конвертирует list[str] или list[dict] в list[dict] для API."""
    result = []
    seen = set()
    for s in sources:
        if isinstance(s, str):
            url = s.strip()
            if url and url not in seen:
                seen.add(url)
                result.append({"url": url, "title": ""})
        elif isinstance(s, dict):
            url = s.get("url", "").strip()
            if url and url not in seen:
                seen.add(url)
                result.append(s)
    return result


def extract_article_json(text, fallback_title):
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    lines = [l for l in text.strip().split("\n") if l.strip()]
    if lines:
        return {
            "title": lines[0].lstrip("#").strip() or fallback_title,
            "body_md": text,
            "sources": []
        }
    return None

# ─────────────────────────────────────────────
# TELEGRAM уведомление
# ─────────────────────────────────────────────

def notify_telegram(agent_name, topic, result=None, error=""):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    if result and result.get("status") == "published":
        score = result.get("factcheck_score", "?")
        url   = f"{BASE_URL}/articles/{result.get('slug', '')}"
        text  = f"✅ *{agent_name}*\n📝 {topic}\n📊 factcheck: {score}\n🔗 {url}"
    elif result and result.get("status") == "flagged":
        score = result.get("factcheck_score", "?")
        text  = f"⚠️ *{agent_name}* — flagged (score={score})\n📝 {topic}"
    else:
        text  = f"❌ *{agent_name}*\n📝 {topic}\n{error}"
    requests.post(
        f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"},
        timeout=10
    )

# ─────────────────────────────────────────────
# ЗАПУСК агента
# ─────────────────────────────────────────────

def run_agent(slug, custom_topic=None):
    state = load_state()

    claude_agent_id = state.get(f"claude_agent_id_{slug}")
    env_id          = state.get("environment_id")
    platform_key    = state.get(f"platform_api_key_{slug}")
    agent_name      = AGENTS[slug]["name"]

    if not claude_agent_id or not env_id:
        print("✗ Claude Agent не найден. Запусти --setup.")
        return
    if not platform_key:
        print("✗ Platform API key не найден. Запусти --register.")
        return

    # Get existing titles to avoid duplicates
    existing_titles = []
    try:
        r = requests.get(f"{BASE_URL}/api/v1/articles?limit=100", timeout=10)
        if r.status_code == 200:
            existing_titles = [a["title"] for a in r.json().get("items", [])]
    except Exception:
        pass

    if custom_topic:
        topic = custom_topic
    else:
        queue = state.get(f"topics_{slug}", [])
        if queue:
            topic = queue.pop(0)
            state[f"topics_{slug}"] = queue
            save_state(state)
        else:
            topic = f"Придумай актуальную тему для раздела '{slug}' и напиши статью"

    tags    = AGENT_TAGS[slug]
    sources = TRUSTED_SOURCES[slug]

    print(f"\n🖊  {agent_name}")
    print(f"   Тема: {topic}")

    session = client.beta.sessions.create(
        agent=claude_agent_id,
        environment_id=env_id,
        title=topic[:80],
        betas=[BETA_HEADER]
    )

    existing_list = "\n".join(f"- {t}" for t in existing_titles[:30]) if existing_titles else "Нет опубликованных статей"

    task_prompt = f"""Напиши статью для блога mama.kindar.app на тему:

"{topic}"

ВАЖНО — НЕ ДУБЛИРУЙ! Вот статьи, которые УЖЕ опубликованы на платформе:
{existing_list}

Выбери тему, которой НЕТ в этом списке. Если заданная тема похожа на уже опубликованную — выбери другой ракурс или совсем другую тему из своей специализации.

ТРЕБОВАНИЯ ПЛАТФОРМЫ (factcheck_score >= 50 нужен для публикации):
1. Сделай минимум 3 поиска через web_search для сбора актуальных данных
2. Объём — не менее 600 слов
3. Структурируй Markdown-заголовками ## и списками
4. В тексте упомяни источники: ВОЗ, ncbi.nlm.nih.gov, педиатр.ру (где уместно)
5. В конце — дисклеймер (по твоей persona)

СТРУКТУРА статьи:
## [Цепляющий заголовок раздела]
[Лид — 2-3 предложения]
## [Подзаголовок]
...
## Личный момент
...
## Вывод
...
⚠️ [Дисклеймер с нужным специалистом]

После написания верни СТРОГО в этом формате:

```json
{{
  "title": "Заголовок статьи",
  "body_md": "полный текст в markdown",
  "sources": ["url1", "url2", "url3"]
}}
```

sources — реальные URL из твоих поисков.
"""

    client.beta.sessions.events.send(
        session_id=session.id,
        events=[{"type": "user.message", "content": [{"type": "text", "text": task_prompt}]}],
        betas=[BETA_HEADER]
    )

    full_response = ""
    print("  Агент работает", end="", flush=True)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            for event in client.beta.sessions.events.stream(
                session_id=session.id,
                betas=[BETA_HEADER],
                timeout=300.0,
            ):
                if event.type == "agent.message":
                    for block in event.content:
                        if hasattr(block, "text"):
                            full_response += block.text
                            print(".", end="", flush=True)
                elif event.type == "agent.tool_use":
                    print(f"\n  🔍 [{event.name}]", end="", flush=True)
                elif event.type == "session.status_idle":
                    break
            break  # stream completed successfully
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"\n  ⚡ Reconnecting (attempt {attempt + 2}/{max_retries})...", end="", flush=True)
                time.sleep(2)
            else:
                print(f"\n  ⚠️  Stream error after {max_retries} attempts: {e}")
                # Try to get the response via events.list as fallback
                try:
                    events_page = client.beta.sessions.events.list(
                        session_id=session.id,
                        order="desc",
                        limit=20,
                        betas=[BETA_HEADER],
                    )
                    for ev in events_page.data:
                        if hasattr(ev, 'content'):
                            for block in ev.content:
                                if hasattr(block, 'text') and block.text not in full_response:
                                    full_response += block.text
                    if full_response:
                        print("  ✓ Получен ответ через events.list")
                except Exception:
                    pass

    print()

    article = extract_article_json(full_response, topic)
    if not article:
        print("  ✗ Не удалось распарсить ответ агента")
        save_as_draft(full_response, topic, slug)
        notify_telegram(agent_name, topic, error="Ошибка парсинга")
        return

    all_sources = _normalize_sources(article.get("sources", []) + sources)
    print(f"  📤 Публикуем: {article['title'][:60]}...")

    try:
        result = publish_to_platform(
            slug=slug,
            title=article["title"],
            body_md=article["body_md"],
            tags=tags,
            sources=all_sources,
            api_key=platform_key,
        )
        article_id = result.get("id")
        score  = result.get("factcheck_score", 0)
        status = result.get("status")
        print(f"  📊 Factcheck score: {score}")

        # Generate cover image
        if article_id:
            generate_cover_image(article_id, article["title"], tags, platform_key, slug)

        if status == "published":
            print(f"  ✅ Опубликовано: {BASE_URL}/articles/{result.get('slug', '')}")
        elif status == "flagged":
            print(f"  ⚠️  Статья помечена (score < 50). Черновик на платформе — можно улучшить и опубликовать.")

        notify_telegram(agent_name, topic, result)

    except requests.HTTPError as e:
        print(f"  ✗ Ошибка API: {e.response.status_code} — {e.response.text[:300]}")
        save_as_draft(article["body_md"], article["title"], slug)
        notify_telegram(agent_name, topic, error=str(e))

# ─────────────────────────────────────────────
# ОБНОВЛЕНИЕ system_prompt агентов
# ─────────────────────────────────────────────

def update_agents():
    """Обновляет system_prompt существующих Claude Managed Agents."""
    state = load_state()
    print("🔄 Обновление system_prompt агентов...\n")

    for slug, agent_cfg in AGENTS.items():
        agent_id = state.get(f"claude_agent_id_{slug}")
        if not agent_id:
            print(f"  ✗ Agent '{slug}' не найден — запусти --setup")
            continue

        current_version = state.get(f"claude_agent_version_{slug}", 1)
        updated = client.beta.agents.update(
            agent_id=agent_id,
            version=current_version,
            name=agent_cfg["name"],
            model="claude-sonnet-4-6",
            system=agent_cfg["system_prompt"],
            tools=[{"type": "agent_toolset_20260401"}],
            betas=[BETA_HEADER]
        )
        state[f"claude_agent_version_{slug}"] = updated.version
        print(f"  ✅ '{agent_cfg['name']}': version {updated.version}")

    save_state(state)
    print("\n✅ Промпты авторов обновлены!")


def update_staff():
    """Обновляет system_prompt staff-агентов (editor, moderator)."""
    state = load_state()
    print("🔄 Обновление system_prompt staff-агентов...\n")

    for key, cfg in STAFF_AGENTS.items():
        agent_id = state.get(f"claude_agent_id_{key}")
        if not agent_id:
            print(f"  ✗ Staff Agent '{key}' не найден")
            continue

        # Get current version from API to avoid 409 conflict
        try:
            current = client.beta.agents.retrieve(agent_id=agent_id, betas=[BETA_HEADER])
            current_version = current.version
        except Exception:
            current_version = state.get(f"claude_agent_version_{key}", 1)

        updated = client.beta.agents.update(
            agent_id=agent_id,
            version=current_version,
            name=cfg["name"],
            model="claude-sonnet-4-6",
            system=cfg["system_prompt"],
            tools=[{"type": "agent_toolset_20260401"}],
            betas=[BETA_HEADER]
        )
        state[f"claude_agent_version_{key}"] = updated.version
        print(f"  ✅ '{cfg['name']}': v{current_version} → v{updated.version}")

    save_state(state)
    print("\n✅ Промпты staff обновлены!")

# ─────────────────────────────────────────────
# ПЕРЕЗАПИСЬ статей
# ─────────────────────────────────────────────

def rewrite_articles(slug):
    """Получает список статей агента и перезаписывает каждую с новым промптом."""
    state    = load_state()
    api_key  = state.get(f"platform_api_key_{slug}")
    agent_id = state.get(f"claude_agent_id_{slug}")
    env_id   = state.get("environment_id")

    if not api_key or not agent_id or not env_id:
        print("✗ Не хватает данных. Запусти --register и --setup.")
        return

    agent_name = AGENTS[slug]["name"]
    tags       = AGENT_TAGS[slug]
    sources    = TRUSTED_SOURCES[slug]

    # Получаем список статей из ОБОИХ эндпоинтов
    agent_platform_id = state.get(f"platform_agent_id_{slug}")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    all_articles = []
    seen_ids = set()

    # 1. Опубликованные (публичный эндпоинт, фильтр по agent_id)
    r = requests.get(f"{BASE_URL}/api/v1/articles", params={"limit": 50}, timeout=15)
    if r.status_code == 200:
        for a in r.json().get("items", []):
            if (a.get("author") or {}).get("id") == agent_platform_id:
                if a["id"] not in seen_ids:
                    seen_ids.add(a["id"])
                    all_articles.append(a)

    # 2. На доработке (авторизованный эндпоинт)
    r2 = requests.get(
        f"{BASE_URL}/api/v1/articles/my/revisions",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15
    )
    if r2.status_code == 200:
        for a in r2.json():
            if a["id"] not in seen_ids:
                seen_ids.add(a["id"])
                all_articles.append(a)

    # Фильтруем — нельзя редактировать статьи в review
    articles = [a for a in all_articles if a.get("status") != "review"]
    skipped = len(all_articles) - len(articles)

    if not articles:
        print(f"  Нет статей для '{agent_name}'" + (f" ({skipped} в review — пропущены)" if skipped else ""))
        return

    print(f"\n🔄 Перезапись статей '{agent_name}' ({len(articles)} шт.){f', {skipped} в review пропущены' if skipped else ''}...\n")

    for article in articles:
        article_id    = article["id"]
        original_title = article.get("title", "Без названия")
        article_slug  = article.get("slug", "")

        print(f"  📝 Перезаписываем: {original_title[:60]}...")

        # Создаём сессию
        session = client.beta.sessions.create(
            agent=agent_id,
            environment_id=env_id,
            title=f"Rewrite: {original_title[:60]}",
            betas=[BETA_HEADER]
        )

        rewrite_prompt = (
            'Перепиши статью для блога mama.kindar.app на тему:\n\n'
            f'"{original_title}"\n\n'
            'ВАЖНО — НОВЫЕ ТРЕБОВАНИЯ К ТОНУ:\n'
            '1. Ты — автор и исследователь, НЕ мама с личным опытом\n'
            '2. Раздел «Из практики» вместо «Личный момент» — пиши от лица наблюдателя:\n'
            '   «в практике часто встречается...», «многие мамы отмечают...», «часто слышу от женщин...»\n'
            '3. НИКОГДА: «я сама рожала», «мои дети», «когда я была беременна», «мой муж»\n'
            '4. Дисклеймер: «я автор и исследователь темы, не медицинский специалист»\n\n'
            'ТРЕБОВАНИЯ ПЛАТФОРМЫ (factcheck_score >= 50):\n'
            '1. Минимум 3 web_search для актуальных данных\n'
            '2. Объём — не менее 600 слов\n'
            '3. Структурируй Markdown-заголовками ## и списками\n'
            '4. Упомяни источники: ВОЗ, ncbi.nlm.nih.gov, педиатр.ру (где уместно)\n\n'
            'СТРУКТУРА:\n'
            '## [Цепляющий заголовок раздела]\n'
            '[Лид — 2-3 предложения]\n'
            '## [Подзаголовок]\n...\n'
            '## Из практики\n...\n'
            '## Вывод\n...\n'
            '⚠️ [Дисклеймер]\n\n'
            'Верни СТРОГО:\n\n'
            '```json\n'
            '{\n'
            '  "title": "Заголовок статьи",\n'
            '  "body_md": "полный текст в markdown",\n'
            '  "sources": ["url1", "url2", "url3"]\n'
            '}\n'
            '```\n'
        )

        client.beta.sessions.events.send(
            session_id=session.id,
            events=[{"type": "user.message", "content": [{"type": "text", "text": rewrite_prompt}]}],
            betas=[BETA_HEADER]
        )

        full_response = ""
        print("     Агент работает", end="", flush=True)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                for event in client.beta.sessions.events.stream(
                    session_id=session.id,
                    betas=[BETA_HEADER],
                    timeout=300.0,
                ):
                    if event.type == "agent.message":
                        for block in event.content:
                            if hasattr(block, "text"):
                                full_response += block.text
                                print(".", end="", flush=True)
                    elif event.type == "agent.tool_use":
                        print(f"\n     🔍 [{event.name}]", end="", flush=True)
                    elif event.type == "session.status_idle":
                        break
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"\n     ⚡ Reconnecting ({attempt + 2}/{max_retries})...", end="", flush=True)
                    time.sleep(2)
                else:
                    print(f"\n     ⚠️  Stream error: {e}")
                    try:
                        events_page = client.beta.sessions.events.list(
                            session_id=session.id, order="desc", limit=20, betas=[BETA_HEADER],
                        )
                        for ev in events_page.data:
                            if hasattr(ev, 'content'):
                                for block in ev.content:
                                    if hasattr(block, 'text') and block.text not in full_response:
                                        full_response += block.text
                        if full_response:
                            print("  ✓ Получен через events.list")
                    except Exception:
                        pass
        print()

        new_article = extract_article_json(full_response, original_title)
        if not new_article:
            print(f"     ✗ Не удалось распарсить — пропускаем")
            continue

        all_sources = _normalize_sources(new_article.get("sources", []) + sources)

        # Обновляем статью через PATCH → POST /submit (отправка на review)
        try:
            clean_body = new_article["body_md"].replace("\x00", "")
            clean_title = new_article["title"].replace("\x00", "")

            patch_payload = {
                "title": clean_title,
                "body_md": clean_body,
                "tags": tags,
                "sources": all_sources,
            }

            r = requests.patch(
                f"{BASE_URL}/api/v1/articles/{article_id}",
                json=patch_payload,
                headers=headers,
                timeout=60
            )
            if r.status_code >= 400:
                print(f"\n     DEBUG PATCH: {r.status_code} {r.text[:300]}")
            r.raise_for_status()
            result = r.json()
            print(f"     ✏️  PATCH OK | status={result.get('status')}")

            # Отправляем на проверку (factcheck → review)
            r2 = requests.post(
                f"{BASE_URL}/api/v1/articles/{article_id}/submit",
                headers=headers,
                timeout=60
            )
            if r2.status_code == 200:
                submit_result = r2.json()
                score  = submit_result.get("factcheck_score", "?")
                status = submit_result.get("status", "?")
                icon   = "✅" if status == "review" else ("📝" if status == "draft" else "⚠️")
                print(f"     {icon} Submit: score={score} | {status}")
                if status == "draft":
                    note = submit_result.get("moderation_note", "")
                    print(f"        ⚠️  Score слишком низкий: {note[:100]}")
                # Generate cover
                generate_cover_image(article_id, new_article["title"], tags, api_key, slug)
            elif r2.status_code == 400:
                print(f"     ⚠️  Submit: {r2.text[:200]}")
            else:
                print(f"     ✗ Submit failed: {r2.status_code}")
        except Exception as e:
            print(f"     ✗ Ошибка: {e}")

    print(f"\n✅ Перезапись '{agent_name}' завершена!")

# ─────────────────────────────────────────────
# ПРОСМОТР статей
# ─────────────────────────────────────────────

def list_articles(slug):
    state   = load_state()
    api_key = state.get(f"platform_api_key_{slug}")
    agent_id = state.get(f"platform_agent_id_{slug}")
    if not api_key:
        print(f"✗ Нет api_key для '{slug}'")
        return

    # GET /articles — публичный список, фильтруем по agent_id на клиенте
    # + GET /articles/my/revisions — статьи на доработке
    all_articles = []

    # 1. Опубликованные (публичный эндпоинт)
    r = requests.get(
        f"{BASE_URL}/api/v1/articles",
        params={"limit": 50},
        timeout=15
    )
    if r.status_code == 200:
        data = r.json()
        for a in data.get("items", []):
            author = a.get("author") or {}
            if author.get("id") == agent_id:
                a["_source"] = "published"
                all_articles.append(a)

    # 2. На доработке (авторизованный эндпоинт)
    r2 = requests.get(
        f"{BASE_URL}/api/v1/articles/my/revisions",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15
    )
    if r2.status_code == 200:
        for a in r2.json():
            a["_source"] = "revision"
            all_articles.append(a)

    print(f"\n📋 Статьи '{AGENTS[slug]['name']}' (всего: {len(all_articles)}):\n")
    for a in all_articles:
        status = a.get("status", "?")
        score  = a.get("factcheck_score", "?")
        mod    = a.get("moderation_status", "")
        if status == "published" and mod != "rejected":
            icon = "✅"
        elif status == "review":
            icon = "🔍"
        elif status == "revision":
            icon = "✏️"
        elif status == "flagged" or mod == "rejected":
            icon = "⚠️"
        else:
            icon = "📝"
        score_str = f"{score:>5}" if isinstance(score, (int, float)) else f"{'?':>5}"
        print(f"  {icon} [{score_str}] {a.get('title', '?')[:60]}")
        print(f"           status={status} mod={mod}")
        if status == "published":
            print(f"           {BASE_URL}/articles/{a.get('slug', '')}")

# ─────────────────────────────────────────────
# STAFF: регистрация staff-агентов
# ─────────────────────────────────────────────

def register_staff():
    """Регистрирует Редактора и Модератора на mama.kindar.app."""
    state = load_state()
    print("📝 Регистрация staff-агентов...\n")

    for key, cfg in STAFF_AGENTS.items():
        state_key = f"platform_api_key_{key}"
        if state_key in state:
            print(f"  ✓ {cfg['name']} — уже зарегистрирован")
            continue

        payload = {
            "name": cfg["name"],
            "bio": cfg["bio"],
            "specialization": cfg["specialization"],
        }
        r = requests.post(
            f"{BASE_URL}/api/v1/agents/register",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            state[state_key] = data["api_key"]
            state[f"platform_agent_id_{key}"] = data["agent"]["id"]
            state[f"platform_agent_slug_{key}"] = data["agent"]["slug"]
            print(f"  ✅ {cfg['name']}")
            print(f"     agent_id : {data['agent']['id']}")
            print(f"     api_key  : {data['api_key'][:12]}...")

            # Установить role через staff API (нужно вручную в БД при первом запуске)
            print(f"     ⚠️  Не забудь: UPDATE agents SET role='{cfg['role']}' WHERE id='{data['agent']['id']}';")
        else:
            print(f"  ✗ {cfg['name']} — ошибка {r.status_code}: {r.text[:200]}")

    save_state(state)
    print("\n✅ Staff-агенты зарегистрированы.")


def setup_staff():
    """Создаёт Claude Managed Agents для staff."""
    state = load_state()
    env_id = state.get("environment_id")
    if not env_id:
        print("✗ Нет environment_id. Запусти --setup сначала.")
        return

    print("🚀 Создание Claude Managed Agents для staff...\n")

    for key, cfg in STAFF_AGENTS.items():
        agent_key = f"claude_agent_id_{key}"
        if agent_key in state:
            print(f"  ✓ Claude Agent '{cfg['name']}': {state[agent_key]}")
            continue

        agent = client.beta.agents.create(
            name=cfg["name"],
            model="claude-sonnet-4-6",
            system=cfg["system_prompt"],
            tools=[{"type": "agent_toolset_20260401"}],
            betas=[BETA_HEADER]
        )
        state[agent_key] = agent.id
        state[f"claude_agent_version_{key}"] = agent.version
        print(f"  ✅ '{cfg['name']}': {agent.id}")

    save_state(state)
    print("\n✅ Staff agents созданы!")


# ─────────────────────────────────────────────
# STAFF: запуск Редактора
# ─────────────────────────────────────────────

def run_editor():
    """Редактор проверяет pending статьи."""
    state = load_state()
    staff_key = state.get("platform_api_key_editor")
    claude_id = state.get("claude_agent_id_editor")
    env_id    = state.get("environment_id")

    if not staff_key or not claude_id or not env_id:
        print("✗ Нет данных для editor. Запусти --register-staff и --setup-staff.")
        return

    print("📋 Получаем статьи на проверку (review)...")
    r = requests.get(
        f"{BASE_URL}/api/v1/staff/articles/review",
        headers={"Authorization": f"Bearer {staff_key}"},
        params={"limit": 10},
        timeout=15
    )

    if r.status_code != 200:
        print(f"  ✗ Ошибка API: {r.status_code} — {r.text[:200]}")
        return

    articles = r.json()
    if not articles:
        print("  ✓ Нет статей для проверки.")
        return

    print(f"  Найдено {len(articles)} статей на проверку.\n")

    for article in articles:
        article_id = article["id"]
        title = article["title"]
        body_md = article.get("body_md", "")
        sources = article.get("sources", [])

        print(f"  📝 Проверяем: {title[:60]}...")

        # Создаём сессию для review
        session = client.beta.sessions.create(
            agent=claude_id,
            environment_id=env_id,
            title=f"Review: {title[:60]}",
            betas=[BETA_HEADER]
        )

        review_prompt = f"""Проверь эту статью с платформы mama.kindar.app:

ЗАГОЛОВОК: {title}

ТЕКСТ СТАТЬИ:
{body_md[:4000]}

ИСТОЧНИКИ: {json.dumps(sources, ensure_ascii=False)[:500]}

Проведи review по правилам платформы и верни JSON с результатом.
"""

        client.beta.sessions.events.send(
            session_id=session.id,
            events=[{"type": "user.message", "content": [{"type": "text", "text": review_prompt}]}],
            betas=[BETA_HEADER]
        )

        full_response = ""
        for attempt in range(3):
            try:
                for event in client.beta.sessions.events.stream(
                    session_id=session.id, betas=[BETA_HEADER], timeout=120.0,
                ):
                    if event.type == "agent.message":
                        for block in event.content:
                            if hasattr(block, "text"):
                                full_response += block.text
                    elif event.type == "session.status_idle":
                        break
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    print(f"     ⚠️  Stream error: {e}")

        # Парсим review JSON
        review = None
        match = re.search(r"```json\s*(\{.*?\})\s*```", full_response, re.DOTALL)
        if match:
            try:
                review = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        if not review:
            print(f"     ✗ Не удалось распарсить review")
            continue

        action = review.get("action", "approve")
        # Normalize: reject → request_revision
        if action == "reject":
            action = "request_revision"
        score = review.get("factcheck_score")
        note = review.get("note", "")

        review_payload = {
            "action": action,
            "note": note,
        }
        if score is not None:
            review_payload["factcheck_score"] = score

        try:
            rr = requests.post(
                f"{BASE_URL}/api/v1/staff/articles/{article_id}/review",
                json=review_payload,
                headers={"Authorization": f"Bearer {staff_key}", "Content-Type": "application/json"},
                timeout=30
            )
            if rr.status_code == 200:
                icon = "✅" if action == "approve" else "📝"
                label = "published" if action == "approve" else "→ revision"
                print(f"     {icon} {label} | score: {score} | {note[:80]}")
            else:
                print(f"     ✗ Review API error: {rr.status_code}")
        except Exception as e:
            print(f"     ✗ Ошибка: {e}")

    print(f"\n✅ Редактор завершил проверку.")
    notify_telegram("Редактор kinDAR", f"Проверено {len(articles)} статей")


# ─────────────────────────────────────────────
# STAFF: запуск Модератора
# ─────────────────────────────────────────────

def run_moderator():
    """Модератор проверяет последние комментарии."""
    state = load_state()
    staff_key = state.get("platform_api_key_moderator")
    claude_id = state.get("claude_agent_id_moderator")
    env_id    = state.get("environment_id")

    if not staff_key or not claude_id or not env_id:
        print("✗ Нет данных для moderator. Запусти --register-staff и --setup-staff.")
        return

    print("📋 Получаем последние комментарии...")
    r = requests.get(
        f"{BASE_URL}/api/v1/staff/comments/recent",
        headers={"Authorization": f"Bearer {staff_key}"},
        params={"limit": 50},
        timeout=15
    )

    if r.status_code != 200:
        print(f"  ✗ Ошибка API: {r.status_code} — {r.text[:200]}")
        return

    comments = r.json()
    if not comments:
        print("  ✓ Нет комментариев для проверки.")
        return

    print(f"  Найдено {len(comments)} комментариев.\n")

    # Отправляем все комментарии разом в одну сессию
    session = client.beta.sessions.create(
        agent=claude_id,
        environment_id=env_id,
        title="Moderation batch",
        betas=[BETA_HEADER]
    )

    comments_text = "\n\n".join([
        f"[ID: {c['id']}] {c['body'][:300]}"
        for c in comments
    ])

    mod_prompt = f"""Проверь эти комментарии с платформы mama.kindar.app на нарушения правил.

КОММЕНТАРИИ:
{comments_text}

Для каждого комментария верни JSON:
```json
[
  {{"id": "...", "action": "skip"|"delete", "reason": "...", "violation_type": "..."|null}}
]
```

Если комментарий нормальный — action: "skip".
"""

    client.beta.sessions.events.send(
        session_id=session.id,
        events=[{"type": "user.message", "content": [{"type": "text", "text": mod_prompt}]}],
        betas=[BETA_HEADER]
    )

    full_response = ""
    for attempt in range(3):
        try:
            for event in client.beta.sessions.events.stream(
                session_id=session.id, betas=[BETA_HEADER], timeout=120.0,
            ):
                if event.type == "agent.message":
                    for block in event.content:
                        if hasattr(block, "text"):
                            full_response += block.text
                elif event.type == "session.status_idle":
                    break
            break
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"  ⚠️  Stream error: {e}")

    # Парсим результат
    match = re.search(r"```json\s*(\[.*?\])\s*```", full_response, re.DOTALL)
    if not match:
        print("  ✗ Не удалось распарсить результат модерации")
        return

    try:
        results = json.loads(match.group(1))
    except json.JSONDecodeError:
        print("  ✗ JSON parse error")
        return

    deleted_count = 0
    for item in results:
        if item.get("action") == "delete":
            comment_id = item["id"]
            reason = item.get("reason", "Нарушение правил платформы")

            try:
                rr = requests.delete(
                    f"{BASE_URL}/api/v1/staff/comments/{comment_id}",
                    json={"reason": reason},
                    headers={"Authorization": f"Bearer {staff_key}", "Content-Type": "application/json"},
                    timeout=15
                )
                if rr.status_code == 200:
                    print(f"  🚫 Удалён [{comment_id[:8]}]: {reason[:60]}")
                    deleted_count += 1
                else:
                    print(f"  ✗ Delete error for {comment_id[:8]}: {rr.status_code}")
            except Exception as e:
                print(f"  ✗ Ошибка: {e}")

    print(f"\n✅ Модератор завершил. Удалено: {deleted_count}/{len(results)}")
    if deleted_count > 0:
        notify_telegram("Модератор kinDAR", f"Удалено {deleted_count} комментариев")


# ─────────────────────────────────────────────
# ГЕНЕРАЦИЯ ОБЛОЖЕК для существующих статей
# ─────────────────────────────────────────────

def generate_covers():
    """Генерирует обложки Flux для всех статей без обложки (или с SVG-обложкой)."""
    state = load_state()

    # Используем staff API для получения всех статей
    staff_key = state.get("platform_api_key_editor")
    if not staff_key:
        print("✗ Нет staff api_key. Запусти --register-staff.")
        return

    # Получаем все published статьи
    r = requests.get(
        f"{BASE_URL}/api/v1/articles",
        params={"limit": 100},
        timeout=15
    )
    if r.status_code != 200:
        print(f"✗ Ошибка API: {r.status_code}")
        return

    articles = r.json().get("items", [])

    # Filter: no cover or SVG cover
    need_cover = [a for a in articles if not a.get("cover_image") or "/cover-image" in (a.get("cover_image") or "")]

    if not need_cover:
        print("  ✓ Все статьи с обложками")
        return

    print(f"\n🎨 {len(need_cover)} статей без обложки\n")

    # Маппинг agent_id → api_key для upload
    agent_keys = {}
    for slug in AGENTS:
        agent_id = state.get(f"platform_agent_id_{slug}")
        api_key = state.get(f"platform_api_key_{slug}")
        if agent_id and api_key:
            agent_keys[agent_id] = (api_key, slug)

    for article in need_cover:
        article_id = article["id"]
        agent_id = article.get("agent_id", "")
        title = article["title"]
        tags = article.get("tags", [])

        # Найти api_key автора для upload
        api_key, slug = agent_keys.get(agent_id, (staff_key, ""))

        print(f"  📝 {title[:60]}...")
        result = generate_cover_image(article_id, title, tags, api_key, slug)
        if result:
            time.sleep(3)  # Rate limit: wait between Replicate calls

    print(f"\n✅ Генерация обложек завершена.")


# ─────────────────────────────────────────────
# АВТОРЫ: доработка статей (revision → submit)
# ─────────────────────────────────────────────

def run_revisions():
    """Агенты-авторы дорабатывают статьи со статусом revision."""
    state = load_state()

    for slug in AGENTS:
        api_key   = state.get(f"platform_api_key_{slug}")
        claude_id = state.get(f"claude_agent_id_{slug}")
        env_id    = state.get("environment_id")

        if not api_key or not claude_id or not env_id:
            continue

        agent_name = AGENTS[slug]["name"]
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # Получаем revision статьи этого агента
        r = requests.get(
            f"{BASE_URL}/api/v1/articles/my/revisions",
            headers=headers,
            timeout=15
        )
        if r.status_code != 200:
            continue

        revisions = r.json()
        if not revisions:
            continue

        print(f"\n📝 {agent_name}: {len(revisions)} статей на доработку\n")

        for article in revisions:
            article_id = article["id"]
            title = article["title"]
            tags = article.get("tags", [])
            note = article.get("moderation_note", "")
            body_md = article.get("body_md", "")

            print(f"  🔄 Дорабатываем: {title[:60]}...")
            print(f"     Замечание: {note[:100]}")

            session = client.beta.sessions.create(
                agent=claude_id,
                environment_id=env_id,
                title=f"Revision: {title[:60]}",
                betas=[BETA_HEADER]
            )

            revision_prompt = f"""Доработай статью для mama.kindar.app. Редактор вернул её с замечаниями.

ЗАГОЛОВОК: {title}

ЗАМЕЧАНИЯ РЕДАКТОРА:
{note}

ТЕКУЩИЙ ТЕКСТ:
{body_md[:3000]}

ЗАДАЧА:
1. Исправь все замечания редактора
2. Убедись что есть дисклеймер в конце
3. Все медицинские утверждения подкреплены источниками
4. Объём — не менее 600 слов

Верни СТРОГО в формате:
```json
{{
  "title": "Заголовок",
  "body_md": "полный исправленный текст",
  "sources": ["url1", "url2"]
}}
```
"""

            client.beta.sessions.events.send(
                session_id=session.id,
                events=[{"type": "user.message", "content": [{"type": "text", "text": revision_prompt}]}],
                betas=[BETA_HEADER]
            )

            full_response = ""
            for attempt in range(3):
                try:
                    for event in client.beta.sessions.events.stream(
                        session_id=session.id, betas=[BETA_HEADER], timeout=180.0,
                    ):
                        if event.type == "agent.message":
                            for block in event.content:
                                if hasattr(block, "text"):
                                    full_response += block.text
                        elif event.type == "session.status_idle":
                            break
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(2)
                    else:
                        print(f"     ⚠️  Stream error: {e}")

            new_article = extract_article_json(full_response, title)
            if not new_article:
                print(f"     ✗ Не удалось распарсить — пропускаем")
                continue

            # PATCH статью
            patch_payload = {
                "title": new_article["title"],
                "body_md": new_article["body_md"],
                "sources": new_article.get("sources", []),
            }
            try:
                rr = requests.patch(
                    f"{BASE_URL}/api/v1/articles/{article_id}",
                    json=patch_payload,
                    headers=headers,
                    timeout=60
                )
                if rr.status_code != 200:
                    print(f"     ✗ PATCH error: {rr.status_code}")
                    continue

                # Submit для повторной проверки
                rs = requests.post(
                    f"{BASE_URL}/api/v1/articles/{article_id}/submit",
                    headers=headers,
                    timeout=60
                )
                if rs.status_code == 200:
                    result = rs.json()
                    print(f"     ✅ Доработано → {result['status']} | score: {result.get('factcheck_score', '?')}")
                    generate_cover_image(article_id, title, tags, api_key, slug)
                else:
                    print(f"     ⚠️  Submit: {rs.status_code}")
            except Exception as e:
                print(f"     ✗ Ошибка: {e}")

    print(f"\n✅ Доработка завершена.")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Агент Маша Соколова + Staff → mama.kindar.app")
    # Авторы
    parser.add_argument("--register",        action="store_true", help="Зарегистрировать авторов")
    parser.add_argument("--setup",           action="store_true", help="Создать Claude Managed Agents")
    parser.add_argument("--update",          action="store_true", help="Обновить system_prompt агентов")
    parser.add_argument("--run",             metavar="SLUG", help="Запустить агента (slug или all)")
    parser.add_argument("--topic",           nargs=2, metavar=("SLUG", "TOPIC"))
    parser.add_argument("--list",            metavar="SLUG")
    parser.add_argument("--rewrite-all",     metavar="SLUG", help="Перезаписать все статьи агента")
    # Staff
    parser.add_argument("--register-staff",  action="store_true", help="Зарегистрировать staff-агентов")
    parser.add_argument("--setup-staff",     action="store_true", help="Создать Claude Agents для staff")
    parser.add_argument("--run-editor",      action="store_true", help="Запустить Редактора (проверка статей)")
    parser.add_argument("--run-moderator",   action="store_true", help="Запустить Модератора (проверка комментариев)")
    parser.add_argument("--run-revisions",   action="store_true", help="Авторы дорабатывают статьи из revision")
    parser.add_argument("--generate-covers", action="store_true", help="Сгенерировать обложки Flux для всех статей")
    parser.add_argument("--update-staff",    action="store_true", help="Обновить system_prompt staff-агентов")

    args = parser.parse_args()

    if args.register:
        register_agents()
    elif args.setup:
        setup()
    elif args.update:
        update_agents()
    elif args.run:
        slugs = list(AGENTS.keys()) if args.run == "all" else [args.run]
        for s in slugs:
            if s in AGENTS: run_agent(s)
            else: print(f"Неизвестный агент: {s}")
    elif args.topic:
        slug, topic = args.topic
        if slug in AGENTS: run_agent(slug, custom_topic=topic)
    elif args.list:
        if args.list in AGENTS: list_articles(args.list)
    elif args.rewrite_all:
        slug = args.rewrite_all
        if slug == "all":
            for s in AGENTS: rewrite_articles(s)
        elif slug in AGENTS:
            rewrite_articles(slug)
        else:
            print(f"Неизвестный агент: {slug}")
    elif args.register_staff:
        register_staff()
    elif args.setup_staff:
        setup_staff()
    elif args.run_editor:
        run_editor()
    elif args.run_moderator:
        run_moderator()
    elif args.run_revisions:
        run_revisions()
    elif args.generate_covers:
        generate_covers()
    elif args.update_staff:
        update_staff()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
