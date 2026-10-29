import React, { useState } from 'react'

// "Estrutura oferecida ao freelancer": checklist SIM/NÃO + textos livres preenchidos pelo dono
// (GET /barbearia/{id}/condicoes-estrutura, PUT /barbearia/condicoes-estrutura).
// null/undefined = o dono ainda não respondeu (nunca vira SIM sozinho).

export const ITENS_CONDICOES_ESTRUTURA = [
  { chave: 'secador_disponivel', label: 'Secador de cabelo disponível' },
  { chave: 'cadeira_disponivel', label: 'Cadeira de barbeiro disponível' },
  { chave: 'bancada_disponivel', label: 'Bancada ou estação de trabalho' },
  { chave: 'espelho_disponivel', label: 'Espelho' },
  { chave: 'capa_fornecida', label: 'Capa de corte fornecida pela barbearia' },
  { chave: 'tomadas_equipamentos', label: 'Tomadas para equipamentos' },
  { chave: 'espaco_adequado_trabalho', label: 'Espaço adequado para trabalhar' },
  { chave: 'local_guardar_materiais', label: 'Local para guardar materiais' },
  { chave: 'local_carregar_celular', label: 'Local para carregar celular' },
  { chave: 'banheiro', label: 'Banheiro' },
  { chave: 'bebedouro_agua', label: 'Bebedouro/água' },
  { chave: 'microondas', label: 'Micro-ondas' },
  { chave: 'local_esquentar_marmita', label: 'Local para esquentar marmita' },
  { chave: 'ar_condicionado', label: 'Ar-condicionado' },
  { chave: 'ventilador', label: 'Ventilador' },
  { chave: 'wifi_freelancers', label: 'Wi-Fi para freelancers' },
]

export const TEXTOS_CONDICOES_ESTRUTURA = [
  { chave: 'outros_recursos', label: 'Outros equipamentos ou recursos oferecidos', max: 500 },
  { chave: 'observacoes', label: 'Observações sobre a estrutura', max: 1000 },
]

export const AVISO_KIT_FREELANCER =
  'Pelos Termos de Uso, o freelancer traz a própria máquina e o kit de trabalho; a barbearia fornece gilete e capa de corte. O secador é opcional e combinado com o proprietário antes de começar.'

function Selo({ valor }) {
  const classe = valor === true
    ? 'bg-green-500/15 text-green-400 border-green-500/30'
    : valor === false
      ? 'bg-red-500/15 text-red-400 border-red-500/30'
      : 'bg-zinc-700/30 text-zinc-400 border-zinc-700'
  return (
    <span className={`px-2 py-1 rounded text-[10px] font-bold border shrink-0 ${classe}`}>
      {valor === true ? 'SIM' : valor === false ? 'NÃO' : 'NÃO INFORMADO'}
    </span>
  )
}

// Visão do freelancer (perfil da barbearia e vaga relâmpago).
export function ListaEstrutura({ condicoes, compacta = false }) {
  if (!condicoes) return null
  const textos = TEXTOS_CONDICOES_ESTRUTURA.filter(({ chave }) => String(condicoes[chave] || '').trim())
  return (
    <div className="space-y-2">
      <div className={compacta ? 'grid grid-cols-1 gap-1' : 'space-y-2'}>
        {ITENS_CONDICOES_ESTRUTURA.map(({ chave, label }) => (
          <div
            key={chave}
            className={`flex items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-black/30 ${compacta ? 'px-2 py-1' : 'px-3 py-2'}`}
          >
            <span className={`${compacta ? 'text-xs' : 'text-sm'} text-white`}>{label}</span>
            <Selo valor={condicoes[chave]} />
          </div>
        ))}
      </div>
      {textos.map(({ chave, label }) => (
        <div key={chave} className="rounded-lg border border-zinc-800 bg-black/30 px-3 py-2">
          <p className="text-[11px] uppercase text-zinc-400">{label}</p>
          <p className="mt-1 whitespace-pre-wrap break-words text-sm text-white">{condicoes[chave]}</p>
        </div>
      ))}
      <p className="text-[11px] text-zinc-500">{AVISO_KIT_FREELANCER}</p>
      {condicoes.atualizado_em && (
        <p className="text-[10px] text-zinc-600">
          Informado pela barbearia · atualizado em {new Date(condicoes.atualizado_em).toLocaleDateString('pt-BR')}
        </p>
      )}
    </div>
  )
}

// Botão "Ver estrutura" do card de vaga: carrega só quando o freelancer abre.
export function EstruturaDaVaga({ API_URL, token, barbeariaId }) {
  const [aberta, setAberta] = useState(false)
  const [condicoes, setCondicoes] = useState(null)
  const [erro, setErro] = useState('')

  const alternar = async () => {
    const abrir = !aberta
    setAberta(abrir)
    if (!abrir || condicoes || !barbeariaId) return
    setErro('')
    try {
      const res = await fetch(`${API_URL}/api/v1/barbearia/${barbeariaId}/condicoes-estrutura`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('falha')
      setCondicoes(await res.json())
    } catch (_e) {
      setErro('Não foi possível carregar a estrutura desta barbearia')
    }
  }

  if (!barbeariaId) return null
  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={alternar}
        className="text-xs font-semibold text-orange-300 underline underline-offset-2 hover:text-orange-200"
      >
        {aberta ? 'Ocultar estrutura' : 'Ver estrutura oferecida (secador, equipamentos...)'}
      </button>
      {aberta && (
        <div className="mt-2">
          {erro && <p className="text-xs text-red-300">{erro}</p>}
          {!erro && !condicoes && <p className="text-xs text-zinc-400">Carregando...</p>}
          {condicoes && <ListaEstrutura condicoes={condicoes} compacta />}
        </div>
      )}
    </div>
  )
}
