#!/bin/bash
cd /opt/ai-mama/backend
export PYTHONPATH=/opt/ai-mama/backend
exec venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
