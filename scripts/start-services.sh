#!/usr/bin/env bash
set -euo pipefail

repo_root="/home/bober/projects/AI_Assistant"
backend_pid_file="/tmp/ai-assistant-backend.pid"
frontend_pid_file="/tmp/ai-assistant-frontend.pid"

cd "$repo_root"
docker compose up -d postgres

for _ in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U ai_assistant -d ai_assistant >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker compose exec -T postgres pg_isready -U ai_assistant -d ai_assistant >/dev/null

cd backend
.venv/bin/alembic upgrade head

cd "$repo_root"

if [[ -f "$backend_pid_file" ]] && kill -0 "$(<"$backend_pid_file")" 2>/dev/null; then
  echo "AI Assistant backend already running."
else
  rm -f "$backend_pid_file"
  setsid -f sh -c 'cd /home/bober/projects/AI_Assistant/backend && echo $$ > /tmp/ai-assistant-backend.pid; exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/ai-assistant-backend.log 2>&1 < /dev/null' >/dev/null 2>&1 < /dev/null
fi

if [[ -f "$frontend_pid_file" ]] && kill -0 "$(<"$frontend_pid_file")" 2>/dev/null; then
  echo "AI Assistant frontend already running."
else
  rm -f "$frontend_pid_file"
  setsid -f sh -c 'echo $$ > /tmp/ai-assistant-frontend.pid; exec npm --prefix frontend run dev -- --host 0.0.0.0 --port 5173 --strictPort > /tmp/ai-assistant-frontend.log 2>&1 < /dev/null' >/dev/null 2>&1 < /dev/null
fi

for _ in $(seq 1 20); do
  curl -fsS http://127.0.0.1:8000/api/health >/dev/null && break
  sleep 1
done
curl -fsS http://127.0.0.1:8000/api/health >/dev/null

for _ in $(seq 1 20); do
  curl -fsSI http://127.0.0.1:5173 >/dev/null && break
  sleep 1
done
curl -fsSI http://127.0.0.1:5173 >/dev/null

echo "AI Assistant started: http://localhost:5173"