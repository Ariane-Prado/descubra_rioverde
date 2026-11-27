"""Testes que rodam sem IA e sem internet."""
import os

os.environ["GEMINI_API_KEY"] = ""          # testes rodam sem IA
os.environ["OLLAMA_URL"] = "http://127.0.0.1:9"
os.environ["ARQUIVO_CACHE"] = "/tmp/descubra_cache_testes.json"

from fastapi.testclient import TestClient  # noqa: E402

from app.base_conhecimento import BaseAtrativos, ler_dias, para_minutos  # noqa: E402
from app.main import app  # noqa: E402
from app.modelos import Perfil  # noqa: E402
from app.planejador import agendar, planejar_offline  # noqa: E402

cliente = TestClient(app)
base = BaseAtrativos()
SEXTA = {"interesses": ["pesca", "cachoeiras", "cafes", "historia", "parques", "barzinho"],
         "outro": "balada depois do happy hour", "dia_semana": "sex",
         "periodos": ["manha", "tarde", "noite"], "modo": "offline"}


def todas(roteiro):
    return [p for b in roteiro["blocos"] for p in b["paradas"]]


def test_saude_e_lugares_incompletos():
    r = cliente.get("/api/saude").json()
    assert r["ok"] and r["atrativos"] > 0
    assert "Domah" in r["incompletos"]  # lugar real ainda sem coordenadas e horários


def test_dias_da_semana():
    assert ler_dias("todos os dias") == set(range(7))
    assert ler_dias("ter a dom") == {1, 2, 3, 4, 5, 6}
    assert ler_dias("sex a sab") == {4, 5}
    assert ler_dias("qui, sex") == {3, 4}


def test_roteiro_respeita_periodos_e_nao_tem_preco():
    r = cliente.post("/api/roteiro", json=SEXTA).json()["roteiro"]
    assert [b["periodo"] for b in r["blocos"]] == ["manha", "tarde", "noite"]
    assert "custo_total_estimado" not in r and all("custo_estimado" not in p for p in todas(r))
    assert len(todas(r)) == r["total_paradas"] > 0


def test_cada_parada_esta_aberta_no_dia_e_horario():
    perfil = Perfil(**SEXTA)
    for bloco in planejar_offline(base, perfil).blocos:
        dia = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
               "Sexta-feira", "Sábado", "Domingo"].index(bloco.dia_semana)
        for p in bloco.paradas:
            chegada, saida = para_minutos(p.horario_chegada), para_minutos(p.horario_saida)
            if saida < chegada:
                saida += 24 * 60
            if chegada < 6 * 60:
                chegada, saida = chegada + 24 * 60, saida + 24 * 60
            assert base.aberto(base.obter(p.atrativo_id), dia, chegada, saida), p.nome


def test_lugar_que_fecha_no_domingo_nao_entra():
    perfil = Perfil(interesses=["historia"], dia_semana="dom", periodos=["manha"])
    ids = [p.atrativo_id for b in planejar_offline(base, perfil).blocos for p in b.paradas]
    assert "108" not in ids  # museu de exemplo funciona de terça a sábado


def test_atrativo_inventado_e_ignorado():
    perfil = Perfil(interesses=["historia"], dia_semana="sex", periodos=["manha"])
    blocos, _ = agendar(base, perfil, ["999", "106"])
    assert [p.atrativo_id for p in blocos[0].paradas] == ["106"]


def test_como_chegar():
    assert base.obter("101")["acesso"] == "carro"        # cachoeira marcada "precisa de carro"
    assert base.obter("104")["acesso"] == "a_pe"         # sorveteria no centro
    assert base.obter("102")["acesso"] == "aplicativo"   # pesque-pague perto da cidade


def test_pesque_pague_serve_almoco_sem_outro_restaurante_na_manha():
    perfil = Perfil(interesses=["pesca", "gastronomia"], dia_semana="sex", periodos=["manha"])
    blocos, _ = agendar(base, perfil, ["102", "112"])
    refeicoes = [p for p in blocos[0].paradas if p.refeicao]
    assert len(refeicoes) == 1


def test_varios_dias_sem_repetir_lugar():
    r = cliente.post("/api/roteiro", json={**SEXTA, "dias": 3}).json()["roteiro"]
    ids = [p["atrativo_id"] for p in todas(r)]
    assert len(ids) == len(set(ids))
    assert {b["dia"] for b in r["blocos"]} == {1, 2, 3}


def test_sem_ia_disponivel_cai_no_plano_b():
    r = cliente.post("/api/roteiro", json={**SEXTA, "modo": "agentes"}).json()
    assert r["modo"] == "offline"
    assert any("plano B" in a for a in r["roteiro"]["avisos"])


def test_avisa_interesse_que_nao_coube():
    # o barzinho de exemplo só abre à noite: pedido só à tarde deve avisar
    r = cliente.post("/api/roteiro", json={"interesses": ["barzinho"], "dia_semana": "qui", "periodos": ["tarde"],
                                           "modo": "offline"}).json()["roteiro"]
    assert any("Barzinho e violão" in a for a in r["avisos"])


def test_titulo_com_dia_errado_e_trocado():
    from app.agentes import _cita_outro_dia
    perfil = Perfil(dia_semana="qui")
    assert _cita_outro_dia("Roteiro de Quarta-Feira", perfil)
    assert not _cita_outro_dia("Quinta de natureza", perfil)
