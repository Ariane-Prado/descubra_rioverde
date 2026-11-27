@echo off
chcp 65001 >nul
title Descubra Rio Verde - Instalacao
cd /d "%~dp0"
echo ============================================================
echo   DESCUBRA RIO VERDE - INSTALACAO (fazer UMA vez, COM internet)
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python nao encontrado.
  echo Instale o Python 3.11 ou mais novo em https://www.python.org/downloads/
  echo IMPORTANTE: marque a opcao "Add python.exe to PATH" na instalacao.
  start https://www.python.org/downloads/
  pause & exit /b 1
)

where ollama >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Ollama nao encontrado.
  echo Baixe e instale em https://ollama.com/download e depois rode este arquivo de novo.
  start https://ollama.com/download
  pause & exit /b 1
)

echo [1/3] Instalando as bibliotecas do Python (pode levar alguns minutos)...
cd backend
if not exist .venv python -m venv .venv
call .venv\Scripts\python -m pip install --upgrade pip >nul
call .venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 ( echo [ERRO] Falha ao instalar as bibliotecas. & pause & exit /b 1 )
if not exist .env copy .env.example .env >nul

echo.
echo IA PRINCIPAL - Gemini (online). Sem a chave, o sistema usa so a contingencia.
echo Crie uma chave gratis em https://aistudio.google.com/apikey
echo Cole a chave e aperte Enter (para pular, apenas aperte Enter).
set "CHAVE="
set /p CHAVE=Chave do Gemini: 
if not "%CHAVE%"=="" powershell -NoProfile -Command "(Get-Content .env) -replace '^GEMINI_API_KEY=.*','GEMINI_API_KEY=%CHAVE%' | Set-Content -Encoding UTF8 .env"
if not "%CHAVE%"=="" echo Chave do Gemini salva.

echo.
echo [2/3] Baixando a IA de contingencia, Llama, que roda sem internet (cerca de 2 GB)...
for /f "tokens=2 delims==" %%M in ('findstr /b "OLLAMA_MODEL=" .env') do set MODELO=%%M
if "%MODELO%"=="" set MODELO=llama3.2:3b
start "" /min ollama serve
timeout /t 3 >nul
ollama pull %MODELO%
if errorlevel 1 ( echo [ERRO] Falha ao baixar o modelo. Confira a internet. & pause & exit /b 1 )

echo.
echo [3/3] Testando o sistema...
call .venv\Scripts\python -m pytest -q
cd ..

echo.
echo ============================================================
echo   PRONTO! No dia da apresentacao, use o arquivo 2-iniciar.bat
echo   (nao precisa de internet).
echo ============================================================
pause
