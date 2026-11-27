"""Modelos de dados (entrada e saída da API)."""
from typing import List, Optional

from pydantic import BaseModel, Field

# Interesses que aparecem como blocos no formulário.
# categorias = valores aceitos na coluna "categoria" da planilha; termos = palavras usadas na busca.
INTERESSES = {
    "gastronomia": {"nome": "Gastronomia", "categorias": ["gastronomia"], "termos": "gastronomia restaurante comida almoço culinária típica regional italiana japonesa churrasco"},
    "barzinho": {"nome": "Barzinho e violão", "categorias": ["barzinho"], "termos": "bar barzinho música ao vivo violão happy hour"},
    "pesca": {"nome": "Pesca", "categorias": ["pesca"], "termos": "pesca pesque-pague pesqueiro rio peixe"},
    "cachoeiras": {"nome": "Cachoeiras", "categorias": ["cachoeiras"], "termos": "cachoeira banho trilha natureza"},
    "parques": {"nome": "Parques e lagos", "categorias": ["parques"], "termos": "parque lago caminhada ar livre piquenique pôr do sol"},
    "historia": {"nome": "História e fé", "categorias": ["historia"], "termos": "igreja patrimônio histórico tombado museu casarão"},
    "cafes": {"nome": "Cafés e doces", "categorias": ["cafes"], "termos": "café doce sorvete sorveteria confeitaria"},
    "compras": {"nome": "Compras", "categorias": ["compras"], "termos": "shopping loja feira artesanato compras"},
    "jantar": {"nome": "Jantar especial", "categorias": ["jantar"], "termos": "jantar restaurante especial noite"},
    "esporte": {"nome": "Esporte", "categorias": ["esporte"], "termos": "esporte clube quadra estádio"},
    "familia": {"nome": "Passeio em família", "categorias": [], "termos": "família crianças parquinho brinquedo"},
    "vida_noturna": {"nome": "Vida noturna", "categorias": ["vida_noturna"], "termos": "balada boate festa noite dançar"},
}

PERIODOS = {
    "manha": {"nome": "Manhã", "inicio": "08:00", "fim": "13:00", "faixa": "a partir das 08h"},
    "tarde": {"nome": "Tarde", "inicio": "13:00", "fim": "18:00", "faixa": "13h às 18h"},
    "noite": {"nome": "Noite", "inicio": "19:00", "fim": "25:00", "faixa": "a partir das 19h"},
}

DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
NOMES_DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]


class Perfil(BaseModel):
    """Escolhas feitas pelo visitante no formulário."""

    interesses: List[str] = Field(default_factory=list, description="Ids dos blocos escolhidos, ex.: pesca, cachoeiras")
    outro: str = Field("", description="Texto do bloco 'Outro'")
    dias: int = Field(1, ge=1, le=3)
    dia_semana: str = Field("sex", description="seg | ter | qua | qui | sex | sab | dom")
    periodos: List[str] = Field(default_factory=lambda: ["manha", "tarde"], description="manha | tarde | noite")
    observacoes: str = Field("", description="Pedido especial, texto livre")
    modo: str = Field("agentes", description="agentes = automático (IA local -> Gemini -> regras) | local | gemini | offline")


class Parada(BaseModel):
    ordem: int = 0
    atrativo_id: str
    nome: str = ""
    categoria: str = ""
    categoria_nome: str = ""
    descricao: str = ""
    endereco: str = ""
    bairro: str = ""
    horario_chegada: str = ""
    horario_saida: str = ""
    duracao_min: int = 0
    deslocamento_min: int = 0
    deslocamento_texto: str = ""
    refeicao: str = ""
    acesso: str = ""          # "carro" quando marcado na planilha
    acesso_texto: str = ""
    motivo: str = ""
    nota_google: Optional[float] = None
    total_avaliacoes: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    utilidade: dict = Field(default_factory=dict, description="Nota da função de utilidade e de cada critério")


class Bloco(BaseModel):
    dia: int
    dia_semana: str
    periodo: str
    periodo_nome: str
    faixa: str
    paradas: List[Parada] = Field(default_factory=list)


class Roteiro(BaseModel):
    titulo: str
    resumo: str
    blocos: List[Bloco] = Field(default_factory=list)
    total_paradas: int = 0
    paradas_com_carro: int = 0
    verificacoes: List[str] = Field(default_factory=list)
    avisos: List[str] = Field(default_factory=list)


class Etapa(BaseModel):
    agente: str
    saida: str


class RespostaRoteiro(BaseModel):
    modo: str
    roteiro: Roteiro
    etapas: List[Etapa] = Field(default_factory=list)
