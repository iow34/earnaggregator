#!/bin/sh
set -eu
case "${SERVICE_NAME:-yield-api}" in
  yield-api) exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" ;;
  telegram-bot) exec python -m bot.main ;;
  broadcast-admin) exec python -m uvicorn bot.admin_app:app --host 0.0.0.0 --port "${PORT:-8081}" ;;
  broadcast-worker) exec python -m bot.broadcasts.worker_app ;;
  preview) exec python -m uvicorn demo.server:app --host 0.0.0.0 --port "${PORT:-8000}" ;;
  *) echo "Unknown SERVICE_NAME" >&2; exit 1 ;;
esac
