$ErrorActionPreference = 'Stop'

wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant && docker compose up -d postgres && cd backend && source .venv/bin/activate && alembic upgrade head'

Start-Sleep -Seconds 5

wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant/backend && setsid -f .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/ai-assistant-backend.log 2>&1 < /dev/null'

Start-Sleep -Seconds 5

wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant/frontend && setsid -f npm run dev -- --host 0.0.0.0 > /tmp/ai-assistant-frontend.log 2>&1 < /dev/null'
