#!/bin/bash
# PostgreSQL backup script for ai-mama
BACKUP_DIR="/opt/ai-mama/backups"
DATE=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

# PostgreSQL dump
PGPASSWORD=aimama_secret pg_dump -U aimama -h localhost aimama | gzip > "$BACKUP_DIR/postgres_$DATE.sql.gz"

# Удалить старые бэкапы
find "$BACKUP_DIR" -name "postgres_*.sql.gz" -mtime +$KEEP_DAYS -delete

echo "$(date): Backup created: postgres_$DATE.sql.gz" >> /var/log/aimama-backup.log
ls -lh "$BACKUP_DIR" | tail -5 >> /var/log/aimama-backup.log
