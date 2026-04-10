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
from system_prompts import AGENTS

# ─────────────────────────────────────────────
# КОНФИГ
# ─────────────────────────────────────────────

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TG_BOT_TOKEN      = os.getenv("TG_BOT_TOKEN", "")
TG_CHAT_ID        = os.getenv("TG_CHAT_ID", "")

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
    payload = {
        "title": title,
        "body_md": body_md,
        "tags": tags,
        "sources": sources,
        "auto_publish": True,
    }
    r = requests.post(
        f"{BASE_URL}/api/v1/articles",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=60
    )
    r.raise_for_status()
    return r.json()

def save_as_draft(body_md, title, slug):
    Path("drafts").mkdir(exist_ok=True)
    date  = datetime.now().strftime("%Y-%m-%d_%H%M")
    fname = Path("drafts") / f"{date}_{slug}.md"
    fname.write_text(f"# {title}\n\n{body_md}", encoding="utf-8")
    print(f"  💾 Сохранено в: {fname}")

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

    task_prompt = f"""Напиши статью для блога mama.kindar.app на тему:

"{topic}"

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

    all_sources = list(set(article.get("sources", []) + sources))
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
        score  = result.get("factcheck_score", 0)
        status = result.get("status")
        print(f"  📊 Factcheck score: {score}")

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
# ПРОСМОТР статей
# ─────────────────────────────────────────────

def list_articles(slug):
    state   = load_state()
    api_key = state.get(f"platform_api_key_{slug}")
    if not api_key:
        print(f"✗ Нет api_key для '{slug}'")
        return

    r    = requests.get(
        f"{BASE_URL}/api/v1/articles/mine",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"limit": 10},
        timeout=15
    )
    data = r.json()
    print(f"\n📋 Статьи '{AGENTS[slug]['name']}' (всего: {data.get('total', 0)}):\n")
    for a in data.get("items", []):
        status = a.get("status", "?")
        score  = a.get("factcheck_score", "?")
        icon   = "✅" if status == "published" else ("⚠️" if status == "flagged" else "📝")
        print(f"  {icon} [{score:>5}] {a.get('title', '?')[:60]}")
        if status == "published":
            print(f"           {BASE_URL}/articles/{a.get('slug', '')}")

# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Агент Маша Соколова → mama.kindar.app")
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--setup",    action="store_true")
    parser.add_argument("--run",      metavar="SLUG")
    parser.add_argument("--topic",    nargs=2, metavar=("SLUG", "TOPIC"))
    parser.add_argument("--list",     metavar="SLUG")
    args = parser.parse_args()

    if args.register:
        register_agents()
    elif args.setup:
        setup()
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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
