# Descubra Rio Verde

Plataforma web que monta roteiros turísticos personalizados para Rio Verde (GO) utilizando agentes de IA.
O modelo principal é o **Gemini** (online), com **contingência local via Ollama (Llama)** e fallback baseado em regras para garantir o funcionamento mesmo com conexão instável ou offline.

---

## Pré-requisitos e instalação

1. Instale o **Python 3.11 ou superior**: https://www.python.org/downloads/
   - No Windows, marque a opção **"Add python.exe to PATH"** durante a instalação.
2. Instale o **Ollama**: https://ollama.com/download
3. Crie uma chave gratuita do Gemini em https://aistudio.google.com/apikey
4. Execute **`1-instalar.bat`** (no Linux ou macOS: `bash 1-instalar.sh`).
   - O script cria o ambiente virtual, instala as dependências, configura o arquivo `.env` com a chave do Gemini, baixa o modelo local de contingência (`llama3.2:3b`, ~2 GB) e valida o sistema.
5. Ajuste ou complemente a base de atrativos em `backend/dados/atrativos.csv`, se desejar.

## Como executar

1. Execute **`2-iniciar.bat`** (no Linux ou macOS: `bash 2-iniciar.sh`). O navegador abrirá automaticamente em **http://localhost:8000**.
2. Mantenha o terminal aberto enquanto a aplicação estiver em uso (ele executa o servidor).

> **Dica de desempenho:** ao rodar o modelo local (Llama) em notebook, manter o equipamento conectado à energia evita redução de desempenho da GPU/CPU.

### Modos de operação e contingência offline

O sistema alterna automaticamente conforme a disponibilidade da conexão:

| Situação | Comportamento do sistema |
|---|---|
| Internet disponível | Agentes executados com o **Gemini** |
| Internet lenta ou indisponível (verificação em 2 s) | Se uma combinação equivalente já foi gerada antes, responde imediatamente pelo **cache** |
| Sem internet e sem cache | Agentes executados localmente com **Llama (Ollama)** |
| Ollama indisponível | **Plano B por regras**, sem LLM, utilizando a mesma base de atrativos |

Na interface, a seção **"Opções da apresentação"** (abaixo do formulário) permite forçar um modo específico manualmente. No resultado, **"Ver como o roteiro foi montado"** exibe qual motor foi utilizado, o raciocínio de cada agente e as pontuações atribuídas.

---

## Base de atrativos (`backend/dados/atrativos.csv`)

A planilha pode ser editada no Google Sheets ou no Excel e exportada como **CSV UTF-8 (separado por vírgula)**, mantendo exatamente os nomes das colunas. Após qualquer alteração, reinicie o servidor.

- Registros sem latitude, longitude ou horário de funcionamento são **ignorados** (o log do servidor lista eventuais registros descartados).
- Linhas marcadas com `[EXEMPLO]` são dados fictícios para teste e podem ser removidas conforme os locais reais forem cadastrados.
- Para montar roteiros de 3 dias sem repetição de locais, recomenda-se manter entre **40 e 50 atrativos** cadastrados.

| Coluna | Obrigatória | Descrição e formato |
|---|---|---|
| `id` | sim | Identificador único: `001`, `002`… |
| `nome` | sim | Nome do local (ex.: `Domah`) |
| `categoria` | sim | Uma das opções: `gastronomia`, `barzinho`, `pesca`, `cachoeiras`, `parques`, `historia`, `cafes`, `compras`, `jantar`, `esporte`, `vida_noturna` |
| `descricao` | sim | Breve descrição (1 frase). É utilizada tanto na busca semântica quanto pelos agentes de IA |
| `latitude`, `longitude` | sim | Coordenadas obtidas no Google Maps (ex.: `-17.7923` e `-50.9192`) |
| `dias_funcionamento` | sim | Ex.: `todos os dias`, `ter a dom`, `qui a sab`, `sex,sab` |
| `horario_abertura`, `horario_fechamento` | sim | Formato 24h (ex.: `07:00` e `17:00`; quando fecha após a meia-noite: `21:00` e `02:00`) |
| `duracao_visita_min` | sim | Duração média estimada da visita, em minutos |
| `endereco`, `bairro` | não | Ex.: `Rua X, 123 · Centro` |
| `tags` | não | Palavras-chave separadas por vírgula (`pôr do sol`, `crianças`, `música ao vivo`…). Locais com a tag **`pôr do sol`** são priorizados no fim da tarde |
| `precisa_carro` | não | `sim` para locais afastados ou em zona rural que exigem carro |
| `serve_refeicao` | não | `almoco` ou `jantar` (evita sugerir outro restaurante em seguida quando o local já oferece refeição) |
| `nota_google`, `total_avaliacoes` | não | Avaliação no Google Maps (ex.: `4.7` e `820`) |
| `fonte`, `verificado_em` | não | Origem da informação e data da última conferência |

**Avaliações do Google:** o roteiro exibe a nota e um link que direciona para a página do local no Google Maps (onde é possível consultar os comentários com acesso à internet). Os textos das avaliações não são armazenados na base local, em conformidade com os termos do Google.

---

## Arquitetura e funcionamento

### Estrutura dos agentes

| Componente | Implementação no sistema |
|---|---|
| **Entrada do usuário (User Prompt)** | Formulário com interesses, quantidade de dias, dia da semana, períodos e observações adicionais |
| **Instruções base (System Prompt)** | Persona, regras e formato de saída definidos para cada agente em `backend/app/agentes.py` |
| **Orquestração multiagente** | **CrewAI** com 3 agentes em sequência: **Pesquisador → Planejador → Verificador** (Chain-of-Verification) |
| **Memória** | Passagem de contexto entre os agentes na execução e cache persistente de roteiros já gerados |
| **Ferramentas (Tools)** | Funções determinísticas para consulta na base, cálculo de distâncias/trajetos e encaixe nos horários de funcionamento |
| **Base de Conhecimento (RAG)** | Planilha de atrativos vetorizada com **TF-IDF** e consultada por similaridade |
| **Modelos de linguagem** | **Gemini** como modelo principal e **Llama** (open source, via Ollama) como contingência offline |

### Abordagens de agentes aplicadas

| Tipo de agente | Papel no sistema |
|---|---|
| **Baseado em Utilidade** | O Pesquisador e a função de utilidade (`backend/app/planejador.py`) atribuem uma nota de 0 a 100 a cada local: **afinidade com o perfil (50%) + avaliação no Google (25%) + proximidade (25%)**, priorizando os candidatos mais bem pontuados |
| **Baseado em Objetivos** | O Planejador organiza as paradas para preencher os dias e períodos selecionados respeitando horários de funcionamento e deslocamentos |
| **Reativo com Estado** | O cache identifica combinações já solicitadas e retorna o roteiro correspondente de imediato |
| **Reativo Simples** | O plano B por regras seleciona atrativos com lógica determinística (horário aberto + encaixe no tempo disponível) |

As pontuações da função de utilidade podem ser inspecionadas diretamente no resultado em **"Ver como o roteiro foi montado"**.

### Engenharia de prompt e controle de alucinações

Os prompts combinam definição de persona, delimitadores estruturais (`###`), decomposição de tarefas, exemplos (*few-shot*) e verificação em cadeia (*Chain-of-Verification*). Além disso, uma camada de validação determinística garante que o roteiro final só aceite locais efetivamente cadastrados na planilha e abertos no dia e horário previstos.

---

## Execução manual pelo terminal

Os comandos abaixo utilizam **PowerShell** no Windows. No Linux ou macOS, substitua `.venv\Scripts\` por `.venv/bin/`.

**Instalação (primeira execução, na pasta raiz do projeto):**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env          # abra o .env e preencha GEMINI_API_KEY=
ollama pull llama3.2:3b         # modelo local de contingência (~2 GB)
```

**Iniciar o servidor:**

```powershell
cd backend
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Acesse **http://localhost:8000** no navegador. Para encerrar o servidor, pressione **Ctrl + C**.

O Ollama costuma iniciar automaticamente após a instalação. Caso não esteja ativo, execute `ollama serve` em outro terminal antes de iniciar o backend.

**Comandos úteis (dentro de `backend/`):**

| Finalidade | Comando |
|---|---|
| Executar com reload automático | `.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000` |
| Executar os testes | `.venv\Scripts\python -m pytest -q` |
| Verificar status do backend e da IA local | Acessar `http://localhost:8000/api/saude` |
| Listar modelos instalados no Ollama | `ollama list` |

Para ativar o ambiente virtual diretamente no PowerShell:

```powershell
.venv\Scripts\Activate.ps1      # se houver bloqueio de política: Set-ExecutionPolicy -Scope Process Bypass
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Desenvolvimento do frontend (requer Node.js):**

```powershell
cd frontend
npm install
npm run dev       # servidor de desenvolvimento em http://localhost:5173 (requer o backend na porta 8000)
npm run build     # gera o build de produção em frontend/dist, servido diretamente pelo backend
```

---

## Estrutura do projeto

- `backend/app/agentes.py` — definição dos agentes (CrewAI) e prompts.
- `backend/app/planejador.py` — função de utilidade, encaixe de horários/dias e plano B por regras.
- `backend/app/base_conhecimento.py` — leitura do CSV e busca por similaridade (TF-IDF / RAG).
- `backend/app/main.py` — API FastAPI, cache e lógica de contingência.
- `backend/tests/test_api.py` — testes automatizados da API (`pytest`).
- `frontend/src/App.jsx` — interface React (build compilado em `frontend/dist`).
