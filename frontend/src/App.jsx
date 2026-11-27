import { useEffect, useState } from 'react'
import Icone, { Cidade, Logo } from './Icones.jsx'

const API = import.meta.env.VITE_API_URL ?? ''

const BLOCOS = [
  { id: 'gastronomia', nome: 'Gastronomia', sub: 'restaurantes de vários estilos' },
  { id: 'barzinho', nome: 'Barzinho e violão', sub: 'música ao vivo' },
  { id: 'pesca', nome: 'Pesca', sub: 'rios e pesqueiros' },
  { id: 'cachoeiras', nome: 'Cachoeiras', sub: 'banho e trilhas' },
  { id: 'parques', nome: 'Parques e lagos', sub: 'caminhadas ao ar livre' },
  { id: 'historia', nome: 'História e fé', sub: 'igrejas e patrimônio' },
  { id: 'cafes', nome: 'Cafés e doces', sub: 'pra uma pausa' },
  { id: 'compras', nome: 'Compras', sub: 'shopping e feiras' },
  { id: 'jantar', nome: 'Jantar especial', sub: 'pra fechar o dia' },
  { id: 'esporte', nome: 'Esporte', sub: 'clubes e quadras' },
  { id: 'familia', nome: 'Em família', sub: 'passeio com crianças' },
  { id: 'outro', nome: 'Outro', sub: 'escreva o que procura' },
]
const DIAS = [['seg', 'Seg'], ['ter', 'Ter'], ['qua', 'Qua'], ['qui', 'Qui'], ['sex', 'Sex'], ['sab', 'Sáb'], ['dom', 'Dom']]
const PERIODOS = [
  { id: 'manha', nome: 'Manhã', faixa: 'a partir das 08h' },
  { id: 'tarde', nome: 'Tarde', faixa: '13h às 18h' },
  { id: 'noite', nome: 'Noite', faixa: 'a partir das 19h' },
]
const MODOS = [
  ['agentes', 'Automático: Gemini, com contingência offline'],
  ['gemini', 'Somente Gemini (online)'],
  ['local', 'Somente IA local: Llama (sem internet)'],
  ['offline', 'Somente plano B, sem IA'],
]
const ORIGEM = {
  gemini: 'Montado com IA (Gemini).',
  local: 'Montado com IA local (Llama), sem internet.',
  cache: 'Roteiro recuperado do cache, sem internet.',
  offline: 'Montado pelo plano B, sem IA.',
}
const CARREGANDO = ['Buscando os lugares…', 'Organizando os horários…', 'Conferindo as informações…']
const hoje = DIAS[(new Date().getDay() + 6) % 7][0]

const lista = (itens) => (itens.length <= 1 ? itens.join('') : `${itens.slice(0, -1).join(', ')} e ${itens.at(-1)}`)

function Segmentado({ opcoes, valor, aoMudar, rotulo }) {
  return (
    <div className="seg" role="radiogroup" aria-label={rotulo}>
      {opcoes.map(([v, nome]) => (
        <button type="button" key={String(v)} role="radio" aria-checked={valor === v}
          className={valor === v ? 'on' : ''} onClick={() => aoMudar(v)}>{nome}</button>
      ))}
    </div>
  )
}

export default function App() {
  const [perfil, setPerfil] = useState({
    interesses: [], outro: '', dias: 1, dia_semana: hoje, periodos: ['manha', 'tarde'],
    observacoes: '', modo: 'agentes',
  })
  const [resposta, setResposta] = useState(null)
  const [carregando, setCarregando] = useState(false)
  const [passo, setPasso] = useState(0)
  const [erro, setErro] = useState('')
  const [opcoes, setOpcoes] = useState(false)
  const [diaAberto, setDiaAberto] = useState(1)

  useEffect(() => {
    if (!carregando) return undefined
    const id = setInterval(() => setPasso((p) => Math.min(p + 1, CARREGANDO.length - 1)), 6000)
    return () => clearInterval(id)
  }, [carregando])

  const mudar = (campo, valor) => setPerfil((p) => ({ ...p, [campo]: valor }))
  const alternar = (campo, id) => setPerfil((p) => ({
    ...p, [campo]: p[campo].includes(id) ? p[campo].filter((x) => x !== id) : [...p[campo], id],
  }))
  const outroMarcado = perfil.interesses.includes('outro')

  async function montar(e) {
    e.preventDefault()
    if (perfil.periodos.length === 0) { setErro('Escolha pelo menos um período.'); return }
    setErro(''); setCarregando(true); setPasso(0)
    try {
      const corpo = { ...perfil, interesses: perfil.interesses.filter((i) => i !== 'outro'), outro: outroMarcado ? perfil.outro : '' }
      const r = await fetch(`${API}/api/roteiro`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) })
      if (!r.ok) throw new Error('O sistema não conseguiu montar o roteiro. Tente de novo.')
      setResposta(await r.json()); setDiaAberto(1); window.scrollTo(0, 0)
    } catch (err) {
      setErro(err.message.includes('fetch') ? 'O sistema não está respondendo. Confira se a janela do servidor está aberta.' : err.message)
    } finally {
      setCarregando(false)
    }
  }

  if (resposta) return <Resultado resposta={resposta} perfil={perfil} dia={diaAberto} setDia={setDiaAberto} voltar={() => setResposta(null)} />

  return (
    <div className="tela">
      <aside className="painel">
        <div className="logo"><Logo />Descubra Rio Verde</div>
        <h1 className="chamada">Descubra<br />Rio Verde<span>do seu jeito.</span></h1>
        <p className="apoio">Conte o que você gosta e quanto tempo tem na cidade. Montamos um roteiro sob medida, com horários e como chegar em cada lugar.</p>
        <div className="cidade">
          <Cidade />
          <p>Igreja de São Sebastião, casarões históricos, Cristo Redentor, lavouras e as abóboras gigantes.</p>
        </div>
      </aside>

      <main className="conteudo formulario">
        <form onSubmit={montar}>
          <h2>Monte o seu roteiro</h2>
          <p className="ajuda">Escolha o que não pode faltar. Pode marcar vários.</p>
          <div className="grade" role="group" aria-label="Interesses">
            {BLOCOS.map((b) => {
              const on = perfil.interesses.includes(b.id)
              return (
                <button type="button" key={b.id} className={on ? 'bloco on' : 'bloco'} aria-pressed={on} onClick={() => alternar('interesses', b.id)}>
                  <Icone nome={b.id} />
                  <span><strong>{b.nome}</strong><small>{b.sub}</small></span>
                </button>
              )
            })}
          </div>
          {outroMarcado && (
            <label className="outro">
              <span>Outro:</span>
              <input autoFocus value={perfil.outro} onChange={(e) => mudar('outro', e.target.value)} placeholder="ex.: lugar bonito pra ver o pôr do sol" />
            </label>
          )}

          <hr />
          <div className="duas">
            <div>
              <p className="rotulo"><b>Quantos dias?</b></p>
              <Segmentado rotulo="Quantos dias" opcoes={[[1, '1 dia'], [2, '2 dias'], [3, '3 dias']]} valor={perfil.dias} aoMudar={(v) => mudar('dias', v)} />
            </div>
            <div>
              <p className="rotulo"><b>Que dia você vai?</b><span>confere o que estará aberto</span></p>
              <Segmentado rotulo="Dia da semana" opcoes={DIAS} valor={perfil.dia_semana} aoMudar={(v) => mudar('dia_semana', v)} />
            </div>
          </div>

          <p className="rotulo rotulo-espaco"><b>Em quais períodos?</b><span>pode marcar mais de um</span></p>
          <div className="periodos" role="group" aria-label="Períodos">
            {PERIODOS.map((p) => {
              const on = perfil.periodos.includes(p.id)
              return (
                <button type="button" key={p.id} className={on ? 'per on' : 'per'} aria-pressed={on} onClick={() => alternar('periodos', p.id)}>
                  <Icone nome={p.id} /><span><strong>{p.nome}</strong><small>{p.faixa}</small></span>
                </button>
              )
            })}
          </div>

          <hr />
          <label className="rotulo" htmlFor="pedido"><b>Algum pedido especial?</b><span>opcional</span></label>
          <textarea id="pedido" rows="2" value={perfil.observacoes} onChange={(e) => mudar('observacoes', e.target.value)}
            placeholder="Ex.: vou com crianças, sou vegetariano, prefiro lugares com sombra…" />

          {erro && <p className="erro" role="alert">{erro}</p>}
          <div className="acao">
            <button type="button" className="link-discreto" onClick={() => setOpcoes(!opcoes)}>Opções da apresentação</button>
            <button className="botao" disabled={carregando}>
              {carregando ? <><span className="girando" aria-hidden="true" />{CARREGANDO[passo]}</> : 'Montar meu roteiro'}
            </button>
          </div>
          {opcoes && (
            <label className="opcoes">Qual IA usar
              <select value={perfil.modo} onChange={(e) => mudar('modo', e.target.value)}>
                {MODOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
              </select>
            </label>
          )}
        </form>
      </main>
    </div>
  )
}

function linkGoogle(p) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${p.nome} Rio Verde GO`)}`
}

function Resultado({ resposta, perfil, dia, setDia, voltar }) {
  const { roteiro } = resposta
  const dias = [...new Set(roteiro.blocos.map((b) => b.dia))]
  const blocos = roteiro.blocos.filter((b) => b.dia === dia)
  const primeiro = roteiro.blocos[0]
  const periodos = [...new Set(roteiro.blocos.map((b) => b.periodo_nome.toLowerCase()))]
  const quando = perfil.periodos.length === 3 ? 'dia inteiro' : lista(periodos)

  return (
    <div className="tela">
      <aside className="painel">
        <div className="logo"><Logo />Descubra Rio Verde</div>
        <button className="voltar" onClick={voltar}><Icone nome="voltar" tamanho={18} />Voltar às escolhas</button>
        <h1 className="pronto">Seu roteiro está pronto.</h1>
        <dl className="resumo">
          <div><dt>Quando</dt><dd>{roteiro.blocos.length ? `${primeiro.dia_semana}${dias.length > 1 ? ` + ${dias.length - 1} dia${dias.length > 2 ? 's' : ''}` : ''}, ${quando}` : '—'}</dd></div>
          <div><dt>Paradas</dt><dd>{roteiro.total_paradas} {roteiro.total_paradas === 1 ? 'lugar' : 'lugares'}</dd></div>
          <div><dt>Como chegar</dt><dd>{roteiro.paradas_com_carro === 0 ? 'Tudo de aplicativo ou a pé'
            : `${roteiro.paradas_com_carro} ${roteiro.paradas_com_carro === 1 ? 'parada precisa' : 'paradas precisam'} de carro`}</dd></div>
        </dl>
        <div className="botoes">
          <button className="b2" onClick={voltar}>Montar outro roteiro</button>
        </div>
        <div className="cidade"><Cidade /></div>
      </aside>

      <main className="conteudo roteiro">
        <h2 className="titulo">{roteiro.titulo}</h2>
        <p className="sub">{roteiro.resumo}</p>

        {dias.length > 1 && (
          <div className="seg abas" role="tablist">
            {dias.map((d) => {
              const nome = roteiro.blocos.find((b) => b.dia === d).dia_semana
              return <button key={d} role="tab" aria-selected={dia === d} className={dia === d ? 'on' : ''} onClick={() => setDia(d)}>Dia {d}, {nome.split('-')[0].toLowerCase()}</button>
            })}
          </div>
        )}

        {blocos.map((b) => (
          <section key={`${b.dia}-${b.periodo}`}>
            <div className="periodo"><Icone nome={b.periodo} /><b>{b.periodo_nome}</b><span>{b.faixa}</span></div>
            {b.paradas.length === 0 && <p className="vazio">Nenhum lugar aberto nesse período com as suas escolhas.</p>}
            {b.paradas.map((p, i) => (
              <div key={p.atrativo_id}>
                {i > 0 && p.deslocamento_texto && <div className="trajeto">{p.deslocamento_texto}</div>}
                <article className="parada">
                  <div className="hora"><b>{p.horario_chegada}</b><span>até {p.horario_saida}</span></div>
                  <div className="info">
                    <h3>{p.nome}</h3>
                    <div className="cat">{p.categoria_nome}{p.refeicao === 'almoco' ? ', com almoço' : p.refeicao === 'jantar' ? ', com jantar' : ''}</div>
                    <p>{p.motivo && p.motivo.length > 25 ? p.motivo : p.descricao}</p>
                    <div className="meta">
                      <span><Icone nome="local" tamanho={16} />{p.bairro || `${p.distancia_centro_km} km do centro`}</span>
                      <span className={p.acesso === 'carro' ? 'carro' : ''}><Icone nome={p.acesso} tamanho={16} />{p.acesso_texto}</span>
                      <a href={linkGoogle(p)} target="_blank" rel="noreferrer">
                        {p.nota_google != null
                          ? <><Icone nome="estrela" tamanho={15} preenchido />{p.nota_google.toLocaleString('pt-BR')}{p.total_avaliacoes ? ` (${p.total_avaliacoes.toLocaleString('pt-BR')})` : ''} no Google</>
                          : <><Icone nome="externo" tamanho={15} />Ver no Google</>}
                      </a>
                    </div>
                  </div>
                </article>
              </div>
            ))}
          </section>
        ))}

        {roteiro.avisos.length > 0 && (
          <div className="dica"><Icone nome="alerta" tamanho={20} />
            <ul>{roteiro.avisos.map((a, i) => <li key={i}>{a}</li>)}</ul>
          </div>
        )}

        <details className="como">
          <summary>Ver como o roteiro foi montado</summary>
          <p className="origem">{ORIGEM[resposta.modo] ?? ''}</p>
          <h4>Função de utilidade: por que cada lugar foi escolhido</h4>
          <p className="origem">Nota de 0 a 100: afinidade com o seu perfil (50%), avaliação no Google (25%) e proximidade (25%).</p>
          <table className="utilidade">
            <thead><tr><th>Lugar</th><th>Nota</th><th>Afinidade</th><th>Avaliação</th><th>Proximidade</th></tr></thead>
            <tbody>
              {roteiro.blocos.flatMap((b) => b.paradas).filter((p) => p.utilidade?.nota != null).map((p) => (
                <tr key={p.atrativo_id}><td>{p.nome}</td>
                  {['nota', 'afinidade', 'avaliacao', 'proximidade'].map((k) => <td key={k}>{Math.round(Math.max(p.utilidade[k], 0) * 100)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
          {roteiro.verificacoes.length > 0 && (<><h4>Verificações (Chain-of-Verification)</h4><ul>{roteiro.verificacoes.map((v, i) => <li key={i}>{v}</li>)}</ul></>)}
          {resposta.etapas.map((e, i) => <div key={i} className="etapa"><h4>{e.agente}</h4><pre>{e.saida}</pre></div>)}
        </details>
      </main>
    </div>
  )
}
