#!/usr/bin/env bash
set -euo pipefail

backend_status="stopped"
frontend_status="stopped"
postgres_status="stopped"

if curl --max-time 3 -fsS http://127.0.0.1:8000/api/health >/dev/null; then backend_status="running"; fi
if curl --max-time 3 -fsSI http://127.0.0.1:5173 >/dev/null; then frontend_status="running"; fi
if docker compose -f /home/bober/projects/AI_Assistant/docker-compose.yml ps --status running --services | grep -qx postgres; then postgres_status="running"; fi

printf "PostgreSQL: %s\nBackend: %s\nFrontend: %s\n" "$postgres_status" "$backend_status" "$frontend_status"