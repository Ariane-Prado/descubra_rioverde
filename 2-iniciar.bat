@echo off
chcp 65001 >nul
title Descubra Rio Verde - NAO FECHE ESTA JANELA
cd /d "%~dp0"

if not exist backend\.venv (
  echo O sistema ainda nao foi instalado. Rode primeiro o arquivo 1-instalar.bat
  pause & exit /b 1
)

echo Ligando a IA local (Ollama)...
start "" /min ollama serve
timeout /t 3 >nul

echo Abrindo o site em http://localhost:8000 ...
start "" cmd /c "timeout /t 6 >nul & start http://localhost:8000"

echo.
echo ============================================================
echo   Descubra Rio Verde rodando em http://localhost:8000
echo   Celulares na mesma rede: http://IP-DESTE-NOTEBOOK:8000
echo   (para ver o IP, abra outro terminal e digite: ipconfig)
echo   Para desligar: feche esta janela.
echo ============================================================
echo.
cd backend
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
