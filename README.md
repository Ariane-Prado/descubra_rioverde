# Descubra Rio Verde

Plataforma web que monta roteiros turísticos personalizados para Rio Verde (GO) com agentes de IA.
A IA principal é o **Gemini**, que usa internet. Para internet baixa, há uma **contingência que roda no próprio notebook**.

---

## Preparação (uma vez, em casa, COM internet)

1. Instale o **Python 3.11 ou mais novo**: https://www.python.org/downloads/
   No Windows, marque **"Add python.exe to PATH"** durante a instalação.
2. Instale o **Ollama**: https://ollama.com/download
3. Crie uma chave gratuita do Gemini em https://aistudio.google.com/apikey
4. Dê dois cliques em **`1-instalar.bat`** (no Linux ou Mac: `bash 1-instalar.sh`).
   Ele instala tudo, pede a chave do Gemini, baixa a IA de contingência (Llama, cerca de 2 GB) e testa o sistema.
5. Preencha a planilha `backend/dados/atrativos.csv` (veja abaixo).
6. **Ensaio:** abra o `2-iniciar.bat` e gere roteiros com internet. Depois desligue o Wi-Fi e gere de novo.

## No dia da apresentação

1. Dê dois cliques em **`2-iniciar.bat`**. O navegador abre em **http://localhost:8000**.
2. **Não feche a janela preta**: ela é o servidor.
3. Deixe o notebook **ligado na tomada**, porque na bateria a placa de vídeo fica mais lenta.

### Contingência para internet baixa (automática)

| Situação | O que o sistema faz |
|---|---|
| Internet boa | Agentes com o **Gemini** |
| Internet lenta ou caída (o sistema testa a conexão em 2 s) | Se as mesmas escolhas já foram feitas antes, responde na hora pelo **cache** |
| Sem cache | Agentes com a **Llama**, rodando no notebook, sem internet |
| Llama indisponível | **Plano B por regras**, sem IA, usando a mesma planilha |

Em "Opções da apresentação", embaixo do formulário, dá para forçar um modo específico.
No resultado, "Ver como o roteiro foi montado" mostra qual IA foi usada e o raciocínio de cada agente.

**Dica:** no ensaio, com internet boa, gere as combinações mais prováveis de serem pedidas. Elas ficam no cache e saem na hora no Workshop.

---

## A planilha (`backend/dados/atrativos.csv`)

Editem no Google Sheets ou no Excel e salvem como **CSV UTF-8, separado por vírgula**, mantendo os nomes das colunas.
Depois de editar, feche e abra o `2-iniciar` de novo.

- Lugares sem latitude, longitude ou horário são **ignorados**, e a janela preta mostra a lista deles.
- As linhas `[EXEMPLO]` são fictícias e servem só para testar. Apaguem quando os lugares reais estiverem completos.
- Para roteiros de 3 dias sem repetir lugares, o ideal é ter **40 a 50 lugares**.

| Coluna | Obrigatória | Como preencher |
|---|---|---|
| id | sim | número único: 001, 002… |
| nome | sim | Domah |
| categoria | sim | uma destas: `gastronomia`, `barzinho`, `pesca`, `cachoeiras`, `parques`, `historia`, `cafes`, `compras`, `jantar`, `esporte`, `vida_noturna` |
| descricao | sim | 1 frase. **É o que a busca e a IA leem**: capriche. |
| latitude, longitude | sim | No Google Maps: botão direito no lugar e clique nos números (ex.: -17.7923 e -50.9192) |
| dias_funcionamento | sim | `todos os dias`, `ter a dom`, `qui a sab`, `sex,sab` |
| horario_abertura, horario_fechamento | sim | `07:00` e `17:00`. Se fecha depois da meia-noite: `21:00` e `02:00` |
| duracao_visita_min | sim | tempo médio no lugar, em minutos |
| endereco, bairro | não | Rua X, 123 · Centro |
| tags | não | palavras-chave: `pôr do sol`, `crianças`, `música ao vivo`… Use **"pôr do sol"** nos lugares bons para o pôr do sol: eles vão para o fim da tarde |
| precisa_carro | não | `sim` para forçar. Vazio: o sistema decide pela distância do centro (mais de 8 km = precisa de carro) |
| serve_refeicao | não | `almoco` ou `jantar`. Ex.: pesque-pague que serve almoço, para o sistema não sugerir outro restaurante na sequência |
| nota_google, total_avaliacoes | não | copiados do Google Maps, ex.: `4.7` e `820` |
| link_google_maps | não | No Google Maps: Compartilhar → Copiar link. Sem link, o botão "Ver no Google" faz uma busca pelo nome |
| fonte, verificado_em | não | onde conferiram e quando |

**Avaliações do Google:** o roteiro mostra a nota e um botão que abre a página do lugar no Google Maps, com os comentários (o clique precisa de internet). Os textos dos comentários **não** são copiados para a planilha, porque os termos do Google não permitem armazenar esse conteúdo.

---

## Como funciona (ligação com os slides)

Seguindo o slide "Arquitetura de um Agente" (Aula 5):

| Slide | No sistema |
|---|---|
| User Prompt | O formulário (interesses, dias, dia da semana, períodos, pedido especial) |
| Prompt base (System Prompt) | A persona e as instruções de cada agente (`backend/app/agentes.py`) |
| Agentes | **CrewAI** com 3 agentes: Pesquisador → Planejador → Verificador (Chain-of-Verification) |
| Memória | Cada agente recebe o resultado do anterior, e o cache guarda os roteiros já gerados |
| Tools | Funções do sistema: busca na base, cálculo de trajetos e encaixe nos horários de funcionamento |
| Base de Conhecimento / Dados | A planilha de atrativos, vetorizada (TF-IDF) e consultada por similaridade: o **RAG** |
| Modelos (slide "A Base") | **Gemini** como principal; **Llama** (open source) como contingência offline |

Seguindo o slide "Tipos de Agentes de IA" (Aula 5):

| Tipo de agente | No sistema |
|---|---|
| **Baseado em Utilidade** | O Pesquisador e a **função de utilidade** (`planejador.py`): cada lugar recebe uma nota de 0 a 100 = afinidade com o perfil (50%) + avaliação no Google (25%) + proximidade (25%). Escolhe o lugar com a maior nota, como num sistema de recomendação |
| **Baseado em Objetivos** | O Planejador: o objetivo é preencher os dias e períodos escolhidos, e ele planeja a sequência de paradas com um modelo do "mundo" (horários de funcionamento, distâncias), como um GPS |
| **Reativo com Estado** | O cache: lembra os roteiros já gerados e responde direto quando as mesmas escolhas se repetem |
| **Reativo Simples** | O plano B: regras "SE está aberto E cabe no tempo ENTÃO inclui" |

As notas da função de utilidade aparecem no resultado, em "Ver como o roteiro foi montado".

Técnicas de prompt (Aulas 2 e 2b): persona, delimitadores `###`, divisão de tarefas, few-shot e Chain-of-Verification.
**Segurança contra alucinação:** o código só aceita lugares que existem na planilha e que estão abertos no dia e no horário.

---

## Rodar pelo terminal (sem os arquivos .bat)

Os comandos abaixo são para o **PowerShell** do Windows. No Linux ou Mac, troque `.venv\Scripts\` por `.venv/bin/`.

**Instalação (uma vez, com internet), dentro da pasta do projeto:**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env          # depois abra o .env e cole a chave em GEMINI_API_KEY=
ollama pull llama3.2:3b         # IA de contingência (cerca de 2 GB)
```

**Ligar o servidor (toda vez):**

```powershell
cd backend
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Abra **http://localhost:8000** no navegador. Para desligar, aperte **Ctrl + C** no terminal.

O Ollama normalmente já fica ligado sozinho depois de instalado (ícone perto do relógio). Se não estiver, abra **outro terminal** e rode `ollama serve` antes de ligar o servidor. Se aparecer um erro dizendo que a porta já está em uso, é porque ele já estava ligado.

**Comandos úteis:**

| Para quê | Comando (dentro de `backend`) |
|---|---|
| Ligar e recarregar sozinho ao salvar o código | `.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000` |
| Rodar os testes | `.venv\Scripts\python -m pytest -q` |
| Ver se a IA local está pronta | abrir http://localhost:8000/api/saude |
| Ver os modelos baixados no Ollama | `ollama list` |

Se preferir **ativar o ambiente** para digitar só `python`, `uvicorn` e `pytest`:

```powershell
.venv\Scripts\Activate.ps1      # se o Windows bloquear: Set-ExecutionPolicy -Scope Process Bypass
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Mexer na tela (precisa do Node.js):**

```powershell
cd frontend
npm install
npm run dev       # abre em http://localhost:5173 e atualiza ao salvar (o servidor da porta 8000 precisa estar ligado)
npm run build     # gera a versão final em frontend/dist, que o servidor da porta 8000 mostra
```

---

## Para quem for mexer no código

- `backend/app/agentes.py`: agentes e prompts. `planejador.py`: encaixe nos dias e horários e plano B. `base_conhecimento.py`: planilha e busca (RAG). `main.py`: rotas e contingência.
- Tela: `frontend/src/App.jsx`. A versão compilada vem em `frontend/dist`. Para alterar: `cd frontend && npm install && npm run build` (precisa do Node.js).
- Testes: `cd backend && .venv\Scripts\python -m pytest`
