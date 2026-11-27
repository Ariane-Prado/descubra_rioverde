"""Agendamento do roteiro: transforma uma lista de lugares em dias, períodos e horários.

É código determinístico (sem IA), usado em dois momentos:
1. Depois que os agentes escolhem e priorizam os lugares, o código encaixa cada um
   num dia e período em que ele esteja ABERTO, respeitando tempo, deslocamento e refeições.
   Isso garante que o roteiro final nunca tenha lugar inventado ou fechado.
2. No plano B (sem IA), a lista de prioridades vem direto da busca na base.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from .base_conhecimento import BaseAtrativos, distancia_km, normalizar, para_hhmm, para_minutos, trajeto
from .modelos import DIAS_SEMANA, INTERESSES, NOMES_DIAS, PERIODOS, Bloco, Parada, Perfil, Roteiro

CATEGORIAS_REFEICAO = {"gastronomia", "jantar"}
TOLERANCIA_MIN = 30
POR_DO_SOL_MIN = 17 * 60  # chegada nos lugares de pôr do sol a partir das 17h  # a última parada de um período pode passar até 30 min do horário de fim
NOMES_CATEGORIAS = {k: v["nome"] for k, v in INTERESSES.items()}


# ---------------------------------------------------------------- função de utilidade
# Slide "Tipos de Agentes" (Aula 5): o agente baseado em UTILIDADE escolhe a ação com o melhor
# resultado, medido por uma função de utilidade. Aqui, cada lugar candidato recebe uma nota de 0 a 1:
PESOS = {"afinidade": 0.50, "avaliacao": 0.25, "proximidade": 0.25}


def utilidade(posicao: int, total: int, r: dict, desloc_min: int, espera_min: int) -> dict:
    """Quão 'bom' é visitar este lugar agora. Devolve a nota final e cada critério."""
    criterios = {
        # quanto combina com o visitante (ordem de preferência definida pelos agentes / busca RAG)
        "afinidade": 1 - posicao / max(total, 1),
        # nota do Google: 3,0 vale 0 e 5,0 vale 1 (sem nota: neutro)
        "avaliacao": 0.5 if r["nota_google"] is None else min(max((r["nota_google"] - 3) / 2, 0), 1),
        # mais perto da parada anterior = melhor
        "proximidade": 1 - min(desloc_min, 60) / 60,
    }
    nota = sum(PESOS[k] * v for k, v in criterios.items()) - min(espera_min, 120) / 240
    return {"nota": round(nota, 3), **{k: round(v, 2) for k, v in criterios.items()}}


def janelas(perfil: Perfil) -> List[dict]:
    """Cada combinação de dia e período escolhido vira uma janela de tempo."""
    inicio_semana = DIAS_SEMANA.index(perfil.dia_semana) if perfil.dia_semana in DIAS_SEMANA else 4
    lista = []
    for d in range(perfil.dias):
        dia = (inicio_semana + d) % 7
        for p in ["manha", "tarde", "noite"]:
            if p in perfil.periodos:
                info = PERIODOS[p]
                lista.append({"dia": d + 1, "dia_semana": dia, "periodo": p,
                              "inicio": para_minutos(info["inicio"]), "fim": para_minutos(info["fim"])})
    return lista


def consulta_do_perfil(perfil: Perfil) -> str:
    termos = [INTERESSES[i]["termos"] for i in perfil.interesses if i in INTERESSES]
    return " ".join(termos + [perfil.outro, perfil.observacoes])


def categorias_do_perfil(perfil: Perfil) -> List[str]:
    return [c for i in perfil.interesses if i in INTERESSES for c in INTERESSES[i]["categorias"]]


def candidatos_diversos(base: BaseAtrativos, perfil: Perfil, k: int = 30) -> List[dict]:
    """Recupera lugares da base (RAG) garantindo que CADA interesse marcado apareça,
    intercalando os melhores de cada um (1º de pesca, 1º de cachoeira, ..., 2º de pesca...)."""
    listas = []
    for i in perfil.interesses:
        if i in INTERESSES:
            cats = INTERESSES[i]["categorias"]
            achados = base.buscar(INTERESSES[i]["termos"] + " " + perfil.observacoes, cats, k=8)
            if cats:
                achados = [a for a in achados if a["categoria"] in cats] or achados[:2]
            listas.append(achados)
    texto_livre = f"{perfil.outro} {perfil.observacoes}".strip()
    if texto_livre:
        listas.append(base.buscar(texto_livre, None, k=6))
    resultado, vistos = [], set()
    for rodada in range(max((len(l) for l in listas), default=0)):
        for lista in listas:
            if rodada < len(lista) and lista[rodada]["id"] not in vistos:
                resultado.append(lista[rodada])
                vistos.add(lista[rodada]["id"])
    for extra in base.buscar(consulta_do_perfil(perfil), categorias_do_perfil(perfil), k=k):
        if extra["id"] not in vistos:
            resultado.append(extra)
            vistos.add(extra["id"])
    return resultado[:k]


def agendar(base: BaseAtrativos, perfil: Perfil, prioridades: List[str],
            periodo_preferido: Optional[Dict[str, str]] = None, motivos: Optional[Dict[str, str]] = None,
            reserva: Optional[List[str]] = None) -> tuple[List[Bloco], List[str]]:
    """Encaixa os lugares nas janelas. 'prioridades' vem na ordem de preferência.
    'reserva' só é usada para não deixar um período vazio."""
    periodo_preferido = periodo_preferido or {}
    motivos = motivos or {}
    usados, avisos = set(), []
    blocos: List[Bloco] = []

    fim_do_dia: Dict[int, int] = {}
    ultimo_lugar: Dict[int, dict] = {}
    for j in janelas(perfil):
        # o período pode começar mais tarde se o anterior do mesmo dia se estendeu
        relogio, refeicao_feita = max(j["inicio"], fim_do_dia.get(j["dia"], 0)), False
        atual = ultimo_lugar.get(j["dia"])  # trajeto desde o último lugar do período anterior
        limite_janela = j["fim"] + TOLERANCIA_MIN
        paradas: List[Parada] = []
        lista = list(prioridades) + [i for i in (reserva or []) if i not in prioridades]
        for _ in [0]:
            while True:
                melhor, melhor_nota = None, -math.inf
                for posicao, id_ in enumerate(lista):
                    r = base.obter(id_)
                    if r is None or id_ in usados:
                        continue
                    if posicao >= len(prioridades) and len(paradas) >= 3:
                        continue  # a reserva só completa períodos com poucas paradas
                    pref = periodo_preferido.get(id_)
                    if pref and pref != j["periodo"] and pref in perfil.periodos:
                        continue  # os agentes preferem este lugar em outro período
                    refeicao = r["categoria"] in CATEGORIAS_REFEICAO or bool(r["serve_refeicao"])
                    if refeicao and refeicao_feita:
                        continue  # uma refeição por período basta
                    km = 0 if atual is None else distancia_km(atual["latitude"], atual["longitude"],
                                                             r["latitude"], r["longitude"])
                    desloc, _ = (0, "") if atual is None else trajeto(km)
                    abre = para_minutos(r["horario_abertura"])
                    if j["periodo"] == "tarde" and "por do sol" in normalizar(r["tags"]):
                        abre = max(abre, POR_DO_SOL_MIN)  # lugar de pôr do sol fica para o fim da tarde
                    chegada = max(relogio + desloc, abre if abre >= j["inicio"] else relogio + desloc)
                    espera_max = 150 if abre == POR_DO_SOL_MIN else 60
                    if paradas and chegada - (relogio + desloc) > espera_max:
                        continue  # entre paradas, não deixa o visitante esperando mais de 1 hora
                    # (a primeira parada do período pode começar mais tarde, ex.: bar que abre às 21h)
                    saida = chegada + r["duracao_visita_min"]
                    if saida > limite_janela or not base.aberto(r, j["dia_semana"], chegada, saida):
                        continue
                    espera = 0 if abre == POR_DO_SOL_MIN else chegada - relogio - desloc  # esperar o pôr do sol é proposital
                    util = utilidade(posicao, len(lista), r, desloc, espera)
                    if abre == POR_DO_SOL_MIN and relogio + desloc < POR_DO_SOL_MIN - 60:
                        util["nota"] -= 0.5  # pôr do sol fecha a tarde: antes, preenche o resto do período
                    if util["nota"] > melhor_nota:
                        melhor, melhor_nota = (r, chegada, saida, desloc, km, refeicao, util), util["nota"]
                if melhor is None:
                    break
                r, chegada, saida, desloc, km, refeicao, util = melhor
                _, desloc_txt = (0, "") if atual is None else trajeto(km)
                paradas.append(_parada(r, len(paradas) + 1, chegada, saida, desloc, desloc_txt, motivos.get(r["id"], ""), util))
                usados.add(r["id"])
                refeicao_feita = refeicao_feita or refeicao
                relogio, atual = saida, r

        if paradas:
            fim_do_dia[j["dia"]] = relogio
            ultimo_lugar[j["dia"]] = atual
        info = PERIODOS[j["periodo"]]
        blocos.append(Bloco(dia=j["dia"], dia_semana=NOMES_DIAS[j["dia_semana"]], periodo=j["periodo"],
                            periodo_nome=info["nome"], faixa=info["faixa"], paradas=paradas))
        if not paradas:
            avisos.append(f"Não encontramos lugares abertos para {info['nome'].lower()} de "
                          f"{NOMES_DIAS[j['dia_semana']].lower()} com essas escolhas.")
    return blocos, avisos


def _parada(r: dict, ordem: int, chegada: int, saida: int, desloc: int, desloc_txt: str, motivo: str,
            util: Optional[dict] = None) -> Parada:
    refeicao = r["serve_refeicao"] or ("almoco" if r["categoria"] == "gastronomia" else "jantar" if r["categoria"] == "jantar" else "")
    return Parada(
        ordem=ordem, atrativo_id=r["id"], nome=r["nome"], categoria=r["categoria"],
        categoria_nome=NOMES_CATEGORIAS.get(r["categoria"], r["categoria"].replace("_", " ").capitalize()),
        descricao=r["descricao"], endereco=r["endereco"], bairro=r["bairro"],
        horario_chegada=para_hhmm(chegada), horario_saida=para_hhmm(saida), duracao_min=saida - chegada,
        deslocamento_min=desloc, deslocamento_texto=desloc_txt,
        refeicao=refeicao, acesso=r["acesso"], acesso_texto=r["acesso_texto"],
        distancia_centro_km=r["distancia_centro_km"], motivo=motivo,
        nota_google=r["nota_google"], total_avaliacoes=r["total_avaliacoes"],
        latitude=r["latitude"], longitude=r["longitude"], utilidade=util or {},
    )


def montar_roteiro(blocos: List[Bloco], titulo: str, resumo: str, verificacoes: List[str],
                   avisos: List[str], perfil: Optional[Perfil] = None) -> Roteiro:
    paradas = [p for b in blocos for p in b.paradas]
    com_carro = [p for p in paradas if p.acesso == "carro"]
    avisos = list(avisos)
    if perfil is not None:  # avisa quando um interesse marcado não coube no roteiro
        categorias = {p.categoria for p in paradas}
        faltando = [INTERESSES[i]["nome"] for i in perfil.interesses
                    if i in INTERESSES and INTERESSES[i]["categorias"]
                    and not categorias & set(INTERESSES[i]["categorias"])]
        if faltando:
            nomes = faltando[0] if len(faltando) == 1 else ", ".join(faltando[:-1]) + " e " + faltando[-1]
            avisos.insert(0, f"Não encontramos {nomes} aberto nesse dia e período. "
                             "Tente outro dia da semana ou outro período.")
    if com_carro:
        nomes = ", ".join(p.nome for p in com_carro)
        avisos.insert(0, f"Precisa de carro para: {nomes}. Os demais lugares dá para ir de aplicativo.")
    return Roteiro(titulo=titulo, resumo=resumo, blocos=blocos, total_paradas=len(paradas),
                   paradas_com_carro=len(com_carro), verificacoes=verificacoes,
                   avisos=list(dict.fromkeys(avisos)))


def titulo_padrao(perfil: Perfil, blocos: Optional[List[Bloco]] = None) -> str:
    """Título a partir do que REALMENTE entrou no roteiro (ou dos interesses, se ainda não há paradas)."""
    no_roteiro = [p.categoria for b in (blocos or []) for p in b.paradas]
    nomes = []
    for c in no_roteiro:
        nome = NOMES_CATEGORIAS.get(c, c.replace("_", " ")).lower()
        if nome not in nomes:
            nomes.append(nome)
    nomes = nomes[:3] or [INTERESSES[i]["nome"].lower() for i in perfil.interesses if i in INTERESSES][:3]
    if not nomes:
        return "Seu roteiro por Rio Verde"
    texto = nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]
    return texto[0].upper() + texto[1:]


def planejar_offline(base: BaseAtrativos, perfil: Perfil) -> Roteiro:
    """Plano B sem IA: prioridades vêm direto da busca na base."""
    candidatos = candidatos_diversos(base, perfil, k=40)
    reserva = [r["id"] for r in base.buscar("passeio turismo cidade parque praça", None, k=40)]
    blocos, avisos = agendar(base, perfil, [c["id"] for c in candidatos], reserva=reserva)
    dias = "um dia" if perfil.dias == 1 else f"{perfil.dias} dias"
    return montar_roteiro(blocos, titulo_padrao(perfil, blocos),
                          f"Um roteiro de {dias} montado a partir das suas escolhas.", [], avisos, perfil)
