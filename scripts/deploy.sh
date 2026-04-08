#!/bin/bash
# AI Mama deployment script
# Usage: ./deploy.sh [branch]
set -e

BRANCH="${1:-main}"
APP_DIR="/opt/ai-mama"
LOG_FILE="/var/log/aimama-deploy.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

log "=== Начало деплоя ветки: $BRANCH ==="

cd "$APP_DIR"

# Бэкап перед деплоем
log "Создание бэкапа перед деплоем..."
/opt/ai-mama/scripts/backup.sh

# Git pull (если есть .git)
if [ -d ".git" ]; then
    log "Pulling from git..."
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
fi

# Backend: установка зависимостей
log "Обновление Python зависимостей..."
"$APP_DIR/backend/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt" -q

# DB migrations
log "Применение DB миграций..."
cd "$APP_DIR/backend"
"$APP_DIR/backend/venv/bin/python" -m alembic upgrade head 2>/dev/null || log "WARN: alembic не настроен, пропускаем"
cd "$APP_DIR"

# Frontend: сборка
log "Сборка frontend..."
cd "$APP_DIR/frontend"
npm ci --silent
npm run build
cd "$APP_DIR"

# Перезапуск сервисов
log "Перезапуск сервисов..."
systemctl restart aimama-backend
sleep 3
systemctl reload nginx

# Проверка здоровья
log "Проверка здоровья API..."
if curl -sf http://localhost:8000/api/v1/health > /dev/null; then
    log "✅ API здоров"
else
    log "❌ API не отвечает — откат..."
    # TODO: rollback logic
    exit 1
fi

log "=== Деплой завершён успешно ==="
