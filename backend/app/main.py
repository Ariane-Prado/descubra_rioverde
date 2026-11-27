"""API do Descubra Rio Verde (FastAPI).

Rodar:  uvicorn app.main:app   (dentro da pasta backend)  ->  abrir http://localhost:8000
Docs:   http://localhost:8000/docs

Contingência para internet baixa (modo automático):
  1. Gemini (online)  -> testa a conexão em 2 s antes de tentar
  2. Cache            -> roteiro já gerado antes com as mesmas escolhas
  3. IA local         -> Llama pelo Ollama, sem internet
  4. Plano B          -> regras, sem IA
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import socket
import threading
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
# Funcionamento 100% offline: desliga telemetria e downloads automáticos das bibliotecas de IA.
for _var, _valor in {"CREWAI_DISABLE_TELEMETRY": "true", "OTEL_SDK_DISABLED": "true",
                     "CREWAI_TRACING_ENABLED": "false", "LITELLM_LOCAL_MODEL_COST_MAP": "True"}.items():
    os.environ.setdefault(_var, _valor)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from .base_conhecimento import CAMINHO_PADRAO, BaseAtrativos  # noqa: E402
from .modelos import INTERESSES, Etapa, Perfil, RespostaRoteiro  # noqa: E402
from .planejador import planejar_offline  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("descubra")

app = FastAPI(title="Descubra Rio Verde", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"], allow_headers=["*"],
)

base = BaseAtrativos(os.getenv("ARQUIVO_ATRATIVOS") or CAMINHO_PADRAO)
NOMES = {"ollama": "IA local (Llama)", "gemini": "Gemini (online)"}
CACHE = Path(os.getenv("ARQUIVO_CACHE") or Path(__file__).resolve().parent.parent / "dados" / "cache_roteiros.json")


def _internet_ok() -> bool:
    """Testa em até 2 segundos se o servidor do Gemini responde."""
    try:
        with socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=2):
            return True
    except OSError:
        return False


def _chave(perfil: Perfil) -> str:
    dados = perfil.model_dump(exclude={"modo"})
    dados["interesses"] = sorted(dados["interesses"])
    dados["periodos"] = sorted(dados["periodos"])
    for campo in ("outro", "observacoes"):
        dados[campo] = dados[campo].strip().lower()
    return hashlib.sha1(json.dumps(dados, sort_keys=True).encode()).hexdigest()


def _cache_ler(perfil: Perfil):
    try:
        return json.loads(CACHE.read_text(encoding="utf-8")).get(_chave(perfil))
    except Exception:
        return None


def _cache_salvar(perfil: Perfil, resposta: RespostaRoteiro):
    try:
        dados = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
        dados[_chave(perfil)] = resposta.model_dump()
        CACHE.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    except Exception as erro:
        log.warning("Não consegui salvar o cache: %s", erro)


# ---------------------------------------------------------------- Ollama (IA local)
def _url_ollama(caminho: str) -> str:
    return os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/") + caminho


def _modelo_local() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.2:3b")


def _ollama_pronto() -> bool:
    """O Ollama está rodando e o modelo já foi baixado?"""
    try:
        with urllib.request.urlopen(_url_ollama("/api/tags"), timeout=1) as r:
            modelos = [m["name"] for m in json.load(r).get("models", [])]
    except Exception:
        return False
    alvo = _modelo_local()
    return any(m == alvo or m == alvo + ":latest" for m in modelos)


def _manter_modelo_carregado():
    """Carrega o modelo na memória ao iniciar e o mantém carregado.
    Sem isso, o primeiro visitante esperaria o modelo 'acordar'."""
    while True:
        if _ollama_pronto():
            try:
                dados = json.dumps({"model": _modelo_local(), "keep_alive": "60m"}).encode()
                req = urllib.request.Request(_url_ollama("/api/generate"), data=dados,
                                             headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=180).read()
            except Exception as erro:
                log.warning("Não consegui aquecer o modelo local: %s", erro)
        time.sleep(600)


@app.on_event("startup")
def _iniciar():
    threading.Thread(target=_manter_modelo_carregado, daemon=True).start()


# ---------------------------------------------------------------- rotas
@app.get("/api/saude")
def saude():
    return {"ok": True, "atrativos": len(base.todos()), "incompletos": base.incompletos,
            "modelo_local": _modelo_local(), "ia_local_pronta": _ollama_pronto(),
            "gemini_configurado": bool(os.getenv("GEMINI_API_KEY"))}


@app.get("/api/interesses")
def interesses():
    return [{"id": k, "nome": v["nome"]} for k, v in INTERESSES.items()]


@app.get("/api/atrativos")
def atrativos():
    return base.todos()


def _tentar(provedor: str, perfil: Perfil, avisos: list, erros: list):
    try:
        from .agentes import gerar_roteiro_com_agentes  # import aqui para o plano B funcionar sem CrewAI
        inicio = time.time()
        roteiro, etapas = gerar_roteiro_com_agentes(base, perfil, provedor)
        if roteiro.total_paradas == 0:
            raise ValueError("os agentes não montaram nenhuma parada válida")
        log.info("Roteiro gerado por %s em %.0f s", provedor, time.time() - inicio)
        roteiro.avisos[:0] = avisos
        resposta = RespostaRoteiro(modo="local" if provedor == "ollama" else "gemini",
                                   roteiro=roteiro, etapas=erros + etapas)
        _cache_salvar(perfil, resposta)
        return resposta
    except Exception as erro:  # internet caiu, cota da API, modelo travou, resposta inválida...
        log.exception("Falha com %s", provedor)
        avisos.append(f"{NOMES[provedor]} não respondeu; usamos a próxima opção.")
        erros.append(Etapa(agente=f"Erro: {NOMES[provedor]}", saida=str(erro)[:2000]))
        return None


@app.post("/api/roteiro", response_model=RespostaRoteiro)
def gerar_roteiro(perfil: Perfil):
    forcado = os.getenv("MODO_PADRAO", "").lower()
    modo = forcado or perfil.modo
    avisos: list[str] = []
    erros: list[Etapa] = []

    if modo != "offline":
        if modo in ("agentes", "gemini") and os.getenv("GEMINI_API_KEY"):
            if _internet_ok():
                resposta = _tentar("gemini", perfil, avisos, erros)
                if resposta:
                    return resposta
            else:
                avisos.append("Internet indisponível: usamos a contingência.")
        if modo == "agentes":
            guardado = _cache_ler(perfil)
            if guardado:
                resposta = RespostaRoteiro.model_validate(guardado)
                resposta.roteiro.avisos[:0] = avisos
                resposta.modo = "cache"
                return resposta
        if modo in ("agentes", "local") and _ollama_pronto():
            resposta = _tentar("ollama", perfil, avisos, erros)
            if resposta:
                return resposta

    roteiro = planejar_offline(base, perfil)
    if modo != "offline" and not avisos:
        avisos.append("Nenhuma IA disponível no momento: roteiro montado pelo plano B.")
    roteiro.avisos[:0] = avisos
    return RespostaRoteiro(modo="offline", roteiro=roteiro, etapas=erros)


# ---------------------------------------------------------------- site (React já compilado)
SITE = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if SITE.exists():
    app.mount("/", StaticFiles(directory=SITE, html=True), name="site")
