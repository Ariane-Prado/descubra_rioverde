// Ícones em traço (SVG próprio, funciona sem internet).
const caminhos = {
  gastronomia: <><path d="M7 3v8a2 2 0 0 0 2 2v8M5 3v5m4-5v5" /><path d="M17 21V3c-2 1-3 4-3 8h3" /></>,
  barzinho: <><path d="M9 18V5l11-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="17" cy="16" r="3" /></>,
  pesca: <><path d="M3 12c4-5 10-5 14 0-4 5-10 5-14 0z" /><path d="M17 12l4-3v6z" /><circle cx="8" cy="11.5" r=".6" /></>,
  cachoeiras: <><path d="M4 21l6-12 4 7 2-3 4 8z" /><path d="M14 4v6" /><path d="M12 8c1 1 3 1 4 0" /></>,
  parques: <><path d="M12 22v-7" /><path d="M7 15h10l-5-12z" /><path d="M3 22h18" /></>,
  historia: <><path d="M12 2v6m-3-3h6" /><path d="M6 22V12l6-4 6 4v10z" /><path d="M10 22v-5h4v5" /></>,
  cafes: <><path d="M4 9h13v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5z" /><path d="M17 11h1.5a2.5 2.5 0 0 1 0 5H17M8 3v3M12 3v3" /></>,
  compras: <><path d="M5 8h14l-1 13H6z" /><path d="M9 8a3 3 0 0 1 6 0" /></>,
  jantar: <><path d="M3 11h18M5 11c0 5 3 9 7 9s7-4 7-9" /><path d="M8 7c0-2 1-3 2-3M12 7c0-2 1-3 2-3" /></>,
  esporte: <><circle cx="12" cy="12" r="9" /><path d="M12 7l4 3-1.5 5h-5L8 10z" /></>,
  familia: <><circle cx="8" cy="6" r="2.5" /><circle cx="17" cy="8" r="2" /><path d="M4 21v-6a4 4 0 0 1 8 0v6M14 21v-4a3 3 0 0 1 6 0v4" /></>,
  vida_noturna: <><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" /></>,
  outro: <path d="M12 5v14M5 12h14" />,
  manha: <path d="M3 18h18M7 18a5 5 0 0 1 10 0M12 4v4M4.9 9.9l2.1 2.1M19.1 9.9L17 12" />,
  tarde: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  noite: <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />,
  local: <><path d="M12 22s7-6.5 7-12a7 7 0 0 0-14 0c0 5.5 7 12 7 12z" /><circle cx="12" cy="10" r="2.5" /></>,
  carro: <><path d="M3 16V11l2-5h14l2 5v5z" /><circle cx="7.5" cy="16.5" r="1.5" /><circle cx="16.5" cy="16.5" r="1.5" /></>,
  aplicativo: <rect x="7" y="2" width="10" height="20" rx="2" />,
  a_pe: <><circle cx="13" cy="4" r="2" /><path d="M10 22l2-7-3-3 1-4 4 2 3 1M14 15l2 7" /></>,
  voltar: <path d="M15 18l-6-6 6-6" />,
  abrir: <path d="M6 9l6 6 6-6" />,
  alerta: <><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16h.01" /></>,
  estrela: <path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z" />,
  externo: <><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>,
}

export default function Icone({ nome, tamanho = 22, preenchido = false }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 24 24" aria-hidden="true"
      fill={preenchido ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round">
      {caminhos[nome] ?? caminhos.local}
    </svg>
  )
}

export function Logo({ tamanho = 34 }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 40 40" aria-hidden="true">
      <path d="M20 9c2-4 5-5 7-5" stroke="#CFE6D8" strokeWidth="2.4" fill="none" strokeLinecap="round" />
      <ellipse cx="20" cy="24" rx="16" ry="12" fill="#F28C28" />
      <path d="M20 12.5c-4 3-4 20 0 23M20 12.5c4 3 4 20 0 23M11 14.5c-3.5 4-3.5 15 0 19M29 14.5c3.5 4 3.5 15 0 19"
        stroke="#C9661A" strokeWidth="1.4" fill="none" />
    </svg>
  )
}

// Linha da cidade: Igreja de São Sebastião, casarão, Cristo Redentor, lavoura e abóbora gigante.
export function Cidade() {
  return (
    <svg className="cidade-desenho" viewBox="0 0 472 150" fill="none" stroke="#7FB898" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M0 149h472" />
      <path d="M40 149V88l26-18 26 18v61M58 149v-24a8 8 0 0 1 16 0v24M52 79V44h28v35M66 44V26M60 32h12" />
      <circle cx="66" cy="96" r="6" />
      <path d="M120 149v-42h64v42M114 107l38-20 38 20M134 149v-18h12v18M160 120h12v12h-12z" />
      <circle cx="236" cy="40" r="7" />
      <path d="M200 58h72M228 58l-4 62h24l-4-62M222 120h28v12h-28zM214 132h44v17h-44z" />
      <path d="M290 149c6-10 6-20 0-30M306 149c6-10 6-20 0-30M322 149c6-10 6-20 0-30M338 149c6-10 6-20 0-30M284 128l6-4M300 128l6-4M316 128l6-4M332 128l6-4" />
      <ellipse cx="412" cy="126" rx="38" ry="23" stroke="#F28C28" fill="#F28C28" fillOpacity=".18" />
      <path d="M412 103c-9 6-9 40 0 46M412 103c9 6 9 40 0 46M392 107c-7 9-7 30 0 38M432 107c7 9 7 30 0 38M412 103c1-8 5-11 10-12" stroke="#F28C28" />
    </svg>
  )
}
