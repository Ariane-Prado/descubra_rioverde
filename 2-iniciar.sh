#!/usr/bin/env bash
# Descubra Rio Verde - iniciar no dia (não precisa de internet). Uso: bash 2-iniciar.sh
cd "$(dirname "$0")"
[ -d backend/.venv ] || { echo "Rode primeiro: bash 1-instalar.sh"; exit 1; }

echo "Ligando a IA local (Ollama)..."
(ollama serve >/dev/null 2>&1 &) ; sleep 3

URL=http://localhost:8000
( sleep 6; (command -v xdg-open >/dev/null && xdg-open $URL) || open $URL ) >/dev/null 2>&1 &
echo "Descubra Rio Verde rodando em $URL  (para desligar: Ctrl+C)"
cd backend && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
