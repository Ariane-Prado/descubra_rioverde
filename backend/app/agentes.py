"""Equipe de agentes (CrewAI) que roda com um modelo LOCAL (Ollama) ou com o Gemini.

Pensado para modelos pequenos (SLM) rodando no notebook, sem internet:
o código faz a parte pesada e exata (busca RAG na base, distâncias, horários) e
entrega esses dados como CONTEXTO no prompt de cada agente. Assim o modelo não
precisa chamar ferramentas, o que deixa tudo mais rápido e confiável.

Fluxo:
  1. Pesquisador  recebe os atrativos recuperados da base (RAG) e escolhe os que combinam.
  2. Planejador   recebe as distâncias entre eles e define a ordem das visitas.
  3. Verificador  aplica Chain-of-Verification (CoVe) sobre os fatos da base e fecha o roteiro.
Técnicas de prompt: persona, delimitadores, divisão de tarefas, few-shot e CoVe.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Tuple

from crewai import LLM, Agent, Crew, Process, Task

from .base_conhecimento import BaseAtrativos, normalizar
from .modelos import DIAS_SEMANA, INTERESSES, NOMES_DIAS, PERIODOS, Etapa, Perfil, Roteiro
from .planejador import agendar, candidatos_diversos, janelas, montar_roteiro, titulo_padrao


# ---------------------------------------------------------------- modelos de linguagem
def nome_modelo_local() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.2:3b")


def _llm(provedor: str) -> LLM:
    if provedor == "ollama":
        # Modelo pequeno rodando no próprio notebook pelo Ollama: não usa internet.
        return LLM(
            model="ollama/" + nome_modelo_local(),
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            temperature=0.2,
            max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "500")),
            timeout=float(os.getenv("OLLAMA_TIMEOUT", "240")),
        )
    from google.genai import types  # só é necessário quando usar o Gemini
    extras = {}
    # Os Gemini mais novos "pensam" antes de responder, o que deixa cada chamada bem mais lenta.
    # Para escolher lugares de uma lista curta, um raciocínio curto basta (GEMINI_RACIOCINIO no .env).
    nivel = os.getenv("GEMINI_RACIOCINIO", "low").strip().upper()
    if nivel:
        extras["thinking_config"] = types.ThinkingConfig(thinking_level=nivel, include_thoughts=False)
    return LLM(
        model=os.getenv("GEMINI_MODEL", "gemini/gemini-3.6-flash"),
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.3,
        max_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "1200")),
        client_params={"http_options": types.HttpOptions(timeout=int(float(os.getenv("LLM_TIMEOUT", "30")) * 1000))},
        **extras,
    )


# ---------------------------------------------------------------- utilidades de texto
def _limpar(texto: str) -> str:
    """Remove o 'pensamento' que alguns modelos (ex.: Qwen3) escrevem entre <think></think>."""
    return re.sub(r"<think>.*?</think>", "", texto or "", flags=re.S).strip()


def _ids_no_texto(texto: str, validos: List[str]) -> List[str]:
    """Encontra, na ordem em que aparecem, os ids de atrativos citados pelo modelo."""
    achados: List[str] = []
    for token in re.findall(r"\b\d{1,4}\b", texto):
        for candidato in (token, token.zfill(3)):
            if candidato in validos and candidato not in achados:
                achados.append(candidato)
                break
    return achados


def _motivos(texto: str, validos: List[str]) -> Dict[str, str]:
    motivos = {}
    for linha in texto.splitlines():
        ids = _ids_no_texto(linha, validos)
        if ids and "|" in linha:
            motivos[ids[0]] = linha.split("|", 1)[1].strip(" -.*")
    return motivos


def _json_no_texto(texto: str) -> dict:
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim <= inicio:
        return {}
    try:
        return json.loads(texto[inicio:fim + 1])
    except json.JSONDecodeError:
        return {}


def _tabela(registros: List[dict], curta: bool = False) -> str:
    if curta:  # modelo local pequeno: tabela enxuta = prompt menor = resposta mais rápida
        linhas = ["id | nome | categoria | dias | horário | descrição"]
        for r in registros:
            linhas.append(f"{r['id']} | {r['nome']} | {r['categoria']} | {r['dias_funcionamento']} | "
                          f"{r['horario_abertura']}-{r['horario_fechamento']} | {str(r['descricao'])[:50]}")
        return "\n".join(linhas)
    linhas = ["id | nome | categoria | dias | horário | visita (min) | como chegar | descrição"]
    for r in registros:
        linhas.append(f"{r['id']} | {r['nome']} | {r['categoria']} | {r['dias_funcionamento']} | "
                      f"{r['horario_abertura']}-{r['horario_fechamento']} | "
                      f"{r['duracao_visita_min']} | {r['acesso_texto']} | {str(r['descricao'])[:100]}")
    return "\n".join(linhas)


def _descricao_perfil(p: Perfil) -> str:
    interesses = [INTERESSES[i]["nome"] for i in p.interesses if i in INTERESSES]
    if p.outro:
        interesses.append(f"outro: {p.outro}")
    dia = NOMES_DIAS[DIAS_SEMANA.index(p.dia_semana)] if p.dia_semana in DIAS_SEMANA else "sexta-feira"
    periodos = ", ".join(PERIODOS[x]["nome"].lower() for x in ["manha", "tarde", "noite"] if x in p.periodos)
    return (
        f"- Interesses: {', '.join(interesses) or 'não informado (sugira um passeio variado)'}\n"
        f"- Duração: {p.dias} dia(s), começando na {dia.lower()}\n"
        f"- Períodos: {periodos}\n"
        f"- Pedido especial: {p.observacoes or 'nenhum'}"
    )


def _rodar(agente: Agent, descricao: str, esperado: str, sufixo: str) -> str:
    tarefa = Task(description=descricao + sufixo, expected_output=esperado, agent=agente)
    resultado = Crew(agents=[agente], tasks=[tarefa], process=Process.sequential, verbose=True).kickoff()
    return _limpar(resultado.raw)


EXEMPLO_PLANO = """<exemplo>
031 | manhã | cachoeira é melhor cedo, antes do calor
018 | manhã | pesque-pague serve almoço, fecha bem a manhã
044 | tarde | sorvete no centro depois do almoço
007 | noite | barzinho abre às 21h
</exemplo>"""


def _cita_outro_dia(texto: str, perfil: Perfil) -> bool:
    """O título fala de um dia da semana diferente do escolhido? (ex.: 'quarta' quando é quinta)"""
    t = normalizar(texto)
    nomes = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
    escolhido = nomes[DIAS_SEMANA.index(perfil.dia_semana)] if perfil.dia_semana in DIAS_SEMANA else ""
    return any(n in t and n != escolhido for n in nomes)


def _periodo_na_linha(linha: str) -> str:
    t = normalizar(linha)
    for chave, palavra in (("manha", "manha"), ("tarde", "tarde"), ("noite", "noite")):
        if palavra in t:
            return chave
    return ""


# ---------------------------------------------------------------- fluxo principal
def gerar_roteiro_com_agentes(base: BaseAtrativos, perfil: Perfil,
                              provedor: str = "gemini") -> Tuple[Roteiro, List[Etapa]]:
    llm = _llm(provedor)
    # Se usarem Qwen3 localmente: ele "pensa" antes de responder; /no_think deixa a resposta mais rápida.
    sufixo = "\n/no_think" if provedor == "ollama" and nome_modelo_local().startswith("qwen3") else ""
    perfil_txt = _descricao_perfil(perfil)
    n_janelas = max(1, len(janelas(perfil)))

    # ---- RAG: o código recupera da planilha os lugares mais relevantes para o pedido
    local = provedor == "ollama"
    # Modelo local: menos candidatos e menos escolhas, para caber num prompt curto e responder rápido
    candidatos = candidatos_diversos(base, perfil, k=min(14, 6 + 3 * n_janelas) if local else min(30, 8 + 5 * n_janelas))
    if len(candidatos) < 4:
        candidatos += [r for r in base.buscar("passeio turismo cidade parque praça", None, k=20)
                       if r["id"] not in {c["id"] for c in candidatos}]
    ids_validos = [c["id"] for c in candidatos]
    quantos = min(len(candidatos), (2 if local else 3) * n_janelas + 2)
    # Modelo local: 1 iteração por agente evita que o CrewAI peça novas tentativas quando o formato sai diferente
    iteracoes = 1 if local else 2

    pesquisador = Agent(
        role="Pesquisador de atrativos turísticos de Rio Verde (GO)",
        goal="Escolher, entre os lugares da base, os que mais combinam com o visitante.",
        backstory="Você é um guia de turismo local, atencioso e objetivo. Só recomenda lugares da lista recebida.",
        llm=llm, verbose=True, allow_delegation=False, max_iter=iteracoes,
    )
    planejador = Agent(
        role="Planejador de roteiros",
        goal="Distribuir os lugares entre manhã, tarde e noite de forma realista.",
        backstory=("Você conhece a rotina da cidade: cachoeira e pesca rendem mais cedo, o almoço pode ser no "
                   "próprio pesque-pague, o centro histórico combina com a tarde e barzinhos abrem à noite."),
        llm=llm, verbose=True, allow_delegation=False, max_iter=iteracoes,
    )
    verificador = Agent(
        role="Verificador de informações turísticas",
        goal="Conferir cada parada contra os fatos da base antes de o roteiro chegar ao visitante.",
        backstory="Você é um revisor rigoroso que segue o método Chain-of-Verification e nunca inventa informações.",
        llm=llm, verbose=True, allow_delegation=False, max_iter=iteracoes,
    )

    # ---- 1. Pesquisador
    saida_pesquisa = _rodar(
        pesquisador,
        "Perfil do visitante:\n###\n" + perfil_txt + "\n###\n"
        "Lugares recuperados da base (use SOMENTE estes):\n###\n" + _tabela(candidatos, local) + "\n###\n"
        f"Escolha até {quantos} lugares que combinam com o perfil, funcionam nos dias e períodos do passeio. "
        "Coloque primeiro os mais importantes.",
        "Somente linhas no formato: id | motivo curto. Exemplo:\n031 | cachoeira para começar o dia na natureza",
        sufixo,
    )
    escolhidos = _ids_no_texto(saida_pesquisa, ids_validos) or ids_validos[:quantos]
    motivos = _motivos(saida_pesquisa, ids_validos)

    # ---- 2. Planejador: em que período cada lugar faz mais sentido
    periodos_txt = ", ".join(PERIODOS[x]["nome"].lower() + f" ({PERIODOS[x]['faixa']})"
                             for x in ["manha", "tarde", "noite"] if x in perfil.periodos)
    saida_plano = _rodar(
        planejador,
        "Perfil do visitante:\n###\n" + perfil_txt + "\n###\n"
        "Lugares escolhidos:\n###\n" + _tabela([base.obter(i) for i in escolhidos], local) + "\n###\n"
        f"Diga em qual período cada lugar deve entrar. Períodos disponíveis: {periodos_txt}. "
        "Respeite o horário de funcionamento. Siga o formato do exemplo:\n" + EXEMPLO_PLANO,
        "Linhas no formato: id | período | justificativa curta",
        sufixo,
    )
    periodo_preferido = {}
    for linha in saida_plano.splitlines():
        ids = _ids_no_texto(linha, escolhidos)
        if ids and _periodo_na_linha(linha):
            periodo_preferido[ids[0]] = _periodo_na_linha(linha)
    ordem = _ids_no_texto(saida_plano, escolhidos)
    prioridades = ordem + [i for i in escolhidos if i not in ordem]
    reserva = [i for i in ids_validos if i not in prioridades]
    # Reserva extra (passeios gerais) para não deixar um período vazio quando o pedido é muito restrito
    reserva += [r["id"] for r in base.buscar("passeio turismo cidade parque praça", None, k=20)
                if r["id"] not in prioridades and r["id"] not in reserva]

    # ---- o código encaixa os lugares nos horários (fatos para a verificação)
    blocos, avisos = agendar(base, perfil, prioridades, periodo_preferido, motivos, reserva)
    fatos = []
    for b in blocos:
        for p in b.paradas:
            r = base.obter(p.atrativo_id)
            fatos.append(f"Dia {b.dia} ({b.dia_semana}), {b.periodo_nome}: {p.atrativo_id} {p.nome} "
                         f"{p.horario_chegada}-{p.horario_saida} | funciona {r['dias_funcionamento']} "
                         f"{r['horario_abertura']}-{r['horario_fechamento']} | {p.acesso_texto}")

    # ---- 3. Verificador (Chain-of-Verification)
    saida_verif = _rodar(
        verificador,
        "Perfil do visitante:\n###\n" + perfil_txt + "\n###\n"
        "Roteiro montado, com os FATOS da base:\n###\n" + ("\n".join(fatos) or "(vazio)") + "\n###\n"
        "Aplique Chain-of-Verification:\n"
        "1. Para cada parada, faça perguntas de verificação (abre nesse dia e horário? "
        "combina com o pedido do visitante?).\n"
        "2. Responda cada pergunta usando SOMENTE os fatos acima.\n"
        "3. Liste em 'remover' os ids das paradas que falharem.\n"
        "4. Escreva um título curto (até 6 palavras) e um resumo de uma frase, convidativos, em português.\n"
        "5. Em 'verificacoes', no máximo 4 itens curtos. Em 'avisos', no máximo 2 dicas práticas.",
        'Somente um JSON neste formato: {"titulo": "...", "resumo": "...", "remover": ["id"], '
        '"verificacoes": ["pergunta? resposta"], "avisos": ["dica"]}',
        sufixo,
    )
    final = _json_no_texto(saida_verif)
    no_roteiro = {p.atrativo_id for b in blocos for p in b.paradas}
    remover = {str(i).strip() for i in final.get("remover", []) or []}
    remover = ({i.zfill(3) if i.isdigit() else i for i in remover}) & no_roteiro
    # Proteção contra um verificador confuso: o código já garante horário e dia.
    # Modelo local: a remoção é ignorada. Gemini: aceita, mas nunca mais que metade das paradas.
    if local or len(remover) > len(no_roteiro) // 2:
        remover = set()
    if remover:
        prioridades = [i for i in prioridades if i not in remover]
        reserva = [i for i in reserva if i not in remover]
        blocos, avisos = agendar(base, perfil, prioridades, periodo_preferido, motivos, reserva)

    titulo = str(final.get("titulo") or "").strip()
    if local or not titulo or _cita_outro_dia(titulo, perfil):
        titulo = titulo_padrao(perfil, blocos)  # modelo pequeno costuma errar detalhes no título
    roteiro = montar_roteiro(
        blocos, titulo,
        str(final.get("resumo") or "Um roteiro montado a partir das suas escolhas."),
        [str(v) for v in final.get("verificacoes", []) or []][:6],
        avisos + [str(a) for a in final.get("avisos", []) or []][:2],
        perfil,
    )
    etapas = [Etapa(agente="Pesquisador", saida=saida_pesquisa),
              Etapa(agente="Planejador", saida=saida_plano),
              Etapa(agente="Verificador (Chain-of-Verification)", saida=saida_verif)]
    return roteiro, etapas
