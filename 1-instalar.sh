#!/usr/bin/env bash
# Descubra Rio Verde - instalação (fazer UMA vez, COM internet). Uso: bash 1-instalar.sh
set -e
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "[ERRO] Instale o Python 3.11+ (https://www.python.org/downloads/)"; exit 1; }
command -v ollama  >/dev/null || { echo "[ERRO] Instale o Ollama (https://ollama.com/download) e rode de novo"; exit 1; }

echo "[1/3] Instalando as bibliotecas do Python..."
cd backend
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env

echo "IA PRINCIPAL - Gemini (online). Chave grátis em https://aistudio.google.com/apikey"
read -r -p "Cole a chave e aperte Enter (ou só Enter para pular): " CHAVE
if [ -n "$CHAVE" ]; then sed -i.bak "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$CHAVE|" .env && rm -f .env.bak && echo "Chave salva."; fi

echo "[2/3] Baixando a IA de contingência, Llama, que roda sem internet (cerca de 2 GB)..."
MODELO=$(grep -E '^OLLAMA_MODEL=' .env | cut -d= -f2); MODELO=${MODELO:-llama3.2:3b}
(ollama serve >/dev/null 2>&1 &) ; sleep 3
ollama pull "$MODELO"

echo "[3/3] Testando o sistema..."
.venv/bin/python -m pytest -q
echo
echo "PRONTO! No dia da apresentação, rode: bash 2-iniciar.sh (não precisa de internet)."
