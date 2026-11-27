"""Base de conhecimento dos atrativos + recuperação (a parte "R" do RAG).

Os atrativos ficam em dados/atrativos.csv (planilha). Para cada pedido, a base devolve
os atrativos mais parecidos usando TF-IDF + similaridade de cosseno. Esses registros
são entregues aos agentes, que só podem sugerir o que existe na base.
"""
from __future__ import annotations

import logging
import math
import os
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger("descubra")

CAMINHO_PADRAO = Path(__file__).resolve().parent.parent / "dados" / "atrativos.csv"

OBRIGATORIAS = ["id", "nome", "categoria", "descricao", "latitude", "longitude", "horario_abertura",
                "horario_fechamento", "dias_funcionamento", "duracao_visita_min"]
OPCIONAIS = ["endereco", "bairro", "tags", "precisa_carro", "serve_refeicao", "nota_google",
             "total_avaliacoes", "fonte", "verificado_em"]

DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]

# Centro de Rio Verde (Praça da Matriz, aproximado). Pode ser ajustado no .env.
CENTRO = (float(os.getenv("CENTRO_LAT", "-17.7923")), float(os.getenv("CENTRO_LON", "-50.9192")))
LIMITE_CARRO_KM = float(os.getenv("LIMITE_CARRO_KM", "8"))   # mais longe que isso do centro: precisa de carro
RAIO_CENTRO_KM = float(os.getenv("RAIO_CENTRO_KM", "1.2"))   # até aqui: "no centro, dá para ir a pé"


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para a busca não depender de 'música' x 'musica'."""
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def para_minutos(hhmm: str) -> int:
    h, m = str(hhmm).strip().split(":")
    return int(h) * 60 + int(m)


def para_hhmm(minutos: int) -> str:
    minutos = int(round(minutos)) % (24 * 60)
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta (Haversine) x 1,3 para aproximar o trajeto pelas ruas."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a)) * 1.3


def trajeto(km: float) -> tuple[int, str]:
    """Tempo e texto do deslocamento entre duas paradas."""
    if km <= 0.8:
        minutos = max(3, round(km / 4.5 * 60))
        return minutos, f"{minutos} min a pé"
    minutos = max(5, round(km / 30 * 60) + 3)  # carro/aplicativo na cidade, com tempo para estacionar
    return minutos, f"{minutos} min de trajeto"


def ler_dias(texto: str) -> Set[int]:
    """Converte 'todos os dias', 'seg a sex', 'qui,sex,sab' ou 'sex a dom' em dias da semana (0 = segunda)."""
    t = normalizar(texto).replace("-feira", "").replace("sabado", "sab").replace("domingo", "dom")
    if not t.strip() or "todos" in t or "diariamente" in t:
        return set(range(7))
    dias: Set[int] = set()
    for inicio, fim in re.findall(r"(seg|ter|qua|qui|sex|sab|dom)\w*\s*(?:a|ate|-)\s*(seg|ter|qua|qui|sex|sab|dom)", t):
        i, f = DIAS.index(inicio), DIAS.index(fim)
        dias.update(range(i, f + 1) if i <= f else list(range(i, 7)) + list(range(0, f + 1)))
    dias.update(DIAS.index(d) for d in re.findall(r"\b(seg|ter|qua|qui|sex|sab|dom)", t))
    return dias or set(range(7))


def _numero(valor) -> Optional[float]:
    try:
        texto = str(valor).strip().replace(",", ".")
        return float(texto) if texto else None
    except ValueError:
        return None


class BaseAtrativos:
    def __init__(self, caminho: Path | str = CAMINHO_PADRAO):
        self.caminho = Path(caminho)
        df = pd.read_csv(self.caminho, dtype=str).fillna("")
        df.columns = [c.strip() for c in df.columns]
        faltando = [c for c in OBRIGATORIAS if c not in df.columns]
        if faltando:
            raise ValueError(f"Colunas faltando em {self.caminho.name}: {faltando}")
        for c in OPCIONAIS:
            if c not in df.columns:
                df[c] = ""

        self.incompletos: List[str] = []
        registros = []
        for r in df.to_dict("records"):
            r = {k: str(v).strip() for k, v in r.items()}
            lat, lon = _numero(r["latitude"]), _numero(r["longitude"])
            horarios_ok = all(re.fullmatch(r"\d{1,2}:\d{2}", r[c]) for c in ("horario_abertura", "horario_fechamento"))
            if not r["id"] or not r["nome"] or lat is None or lon is None or not horarios_ok:
                if r["nome"]:
                    self.incompletos.append(r["nome"])
                continue
            r["latitude"], r["longitude"] = lat, lon
            r["categoria"] = normalizar(r["categoria"]).strip().replace(" ", "_")
            r["duracao_visita_min"] = int(_numero(r["duracao_visita_min"]) or 60)
            r["nota_google"] = _numero(r["nota_google"])
            total = _numero(r["total_avaliacoes"])
            r["total_avaliacoes"] = int(total) if total is not None else None
            r["dias"] = ler_dias(r["dias_funcionamento"])
            r["serve_refeicao"] = normalizar(r["serve_refeicao"])
            r["distancia_centro_km"] = round(distancia_km(*CENTRO, lat, lon) / 1.3, 1)
            r["acesso"], r["acesso_texto"] = self._acesso(r)
            registros.append(r)
        if self.incompletos:
            log.warning("%d lugares ignorados por falta de dados: %s", len(self.incompletos), ", ".join(self.incompletos))
        if not registros:
            raise ValueError("A planilha não tem nenhum lugar completo (com latitude, longitude e horários).")

        self._registros = registros
        self._indice = {r["id"]: r for r in registros}
        textos = [normalizar(f"{r['nome']} {r['categoria'].replace('_', ' ')} {r['descricao']} {r['tags']} {r['bairro']}")
                  for r in registros]
        self.vetorizador = TfidfVectorizer(ngram_range=(1, 2))
        self.matriz = self.vetorizador.fit_transform(textos)

    @staticmethod
    def _acesso(r: dict) -> tuple[str, str]:
        marcado = normalizar(r.get("precisa_carro", ""))
        if marcado.startswith("s") or (not marcado and r["distancia_centro_km"] > LIMITE_CARRO_KM):
            return "carro", "Precisa de carro"
        if r["distancia_centro_km"] <= RAIO_CENTRO_KM:
            return "a_pe", "No centro, dá para ir a pé"
        return "aplicativo", "Dá para ir de aplicativo"

    # ---------- consultas ----------
    def todos(self) -> List[Dict]:
        return [{k: v for k, v in r.items() if k != "dias"} for r in self._registros]

    def obter(self, atrativo_id: str) -> Optional[Dict]:
        return self._indice.get(str(atrativo_id).strip())

    def buscar(self, consulta: str, categorias: Optional[List[str]] = None, k: int = 10) -> List[Dict]:
        """Atrativos mais relevantes para a consulta. Categorias escolhidas ganham prioridade."""
        notas = cosine_similarity(self.vetorizador.transform([normalizar(consulta)]), self.matriz).ravel()
        cats = set(categorias or [])
        resultados = []
        for pos, r in enumerate(self._registros):
            nota = float(notas[pos]) + (0.6 if r["categoria"] in cats else 0)
            if nota > 0:
                resultados.append({**r, "relevancia": round(nota, 3)})
        resultados.sort(key=lambda r: r["relevancia"], reverse=True)
        return resultados[:k]

    @staticmethod
    def aberto(r: Dict, dia: int, chegada: int, saida: int) -> bool:
        """Está aberto nesse dia da semana entre a chegada e a saída (minutos desde 00:00)?"""
        abre, fecha = para_minutos(r["horario_abertura"]), para_minutos(r["horario_fechamento"])
        if fecha <= abre:  # funciona até depois da meia-noite (ex.: 21:00 às 02:00)
            fecha += 24 * 60
        return dia in r["dias"] and abre <= chegada and saida <= fecha
