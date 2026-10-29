import React, { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { lerDocumento } from '../utils/termos'

// Leitor em tela cheia do texto completo de um documento legal (Termos / Privacidade).
// O texto vem do servidor (mesma versão que o usuário aceita). Markdown simples:
// #, ##, ###, listas com "- " e **negrito**. Sem HTML cru.

const negrito = (texto) =>
  String(texto)
    .split(/(\*\*[^*]+\*\*)/g)
    .map((parte, i) =>
      parte.startsWith('**') && parte.endsWith('**') ? <strong key={i} className="text-white">{parte.slice(2, -2)}</strong> : parte,
    )

const blocos = (conteudo) => {
  const saida = []
  let paragrafo = []
  let lista = []
  const fecharParagrafo = () => {
    if (paragrafo.length) saida.push({ tipo: 'p', texto: paragrafo.join(' ') })
    paragrafo = []
  }
  const fecharLista = () => {
    if (lista.length) saida.push({ tipo: 'ul', itens: lista })
    lista = []
  }
  String(conteudo || '').split(/\r?\n/).forEach((linhaBruta) => {
    const linha = linhaBruta.trim()
    const titulo = linha.match(/^(#{1,3})\s+(.*)$/)
    if (!linha) {
      fecharParagrafo()
      fecharLista()
    } else if (titulo) {
      fecharParagrafo()
      fecharLista()
      saida.push({ tipo: `h${titulo[1].length}`, texto: titulo[2] })
    } else if (linha.startsWith('- ')) {
      fecharParagrafo()
      lista.push(linha.slice(2))
    } else {
      fecharLista()
      paragrafo.push(linha)
    }
  })
  fecharParagrafo()
  fecharLista()
  return saida
}

export function TextoDocumento({ conteudo }) {
  return (
    <div className="space-y-3 text-sm leading-relaxed text-zinc-300">
      {blocos(conteudo).map((bloco, i) => {
        if (bloco.tipo === 'h1') return <h1 key={i} className="text-lg font-black text-white">{bloco.texto}</h1>
        if (bloco.tipo === 'h2') return <h2 key={i} className="pt-2 text-base font-bold text-orange-300">{bloco.texto}</h2>
        if (bloco.tipo === 'h3') return <h3 key={i} className="text-sm font-bold text-white">{bloco.texto}</h3>
        if (bloco.tipo === 'ul') {
          return (
            <ul key={i} className="list-disc space-y-1 pl-5">
              {bloco.itens.map((item, j) => <li key={j}>{negrito(item)}</li>)}
            </ul>
          )
        }
        return <p key={i}>{negrito(bloco.texto)}</p>
      })}
    </div>
  )
}

export default function DocumentoLegal({ API_URL, codigo, versao, onFechar }) {
  const [documento, setDocumento] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    setDocumento(null)
    setErro('')
    lerDocumento(API_URL, codigo, versao)
      .then((data) => ativo && setDocumento(data))
      .catch((err) => ativo && setErro(err?.message || 'Não foi possível abrir o documento'))
    return () => {
      ativo = false
    }
  }, [API_URL, codigo, versao])

  return (
    <div className="fixed inset-0 z-[60] flex flex-col bg-black text-white" role="dialog" aria-modal="true">
      <div
        className="flex items-center justify-between gap-3 border-b border-zinc-800 px-4 pb-3"
        style={{ paddingTop: 'calc(env(safe-area-inset-top, 0px) + 12px)' }}
      >
        <div className="min-w-0">
          <p className="truncate text-sm font-black">{documento?.titulo || 'Documento'}</p>
          {documento && (
            <p className="text-[11px] text-zinc-500">
              Versão {documento.versao}
              {documento.estado !== 'publicado' ? ' · rascunho em revisão' : ''}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onFechar}
          className="flex shrink-0 items-center gap-1 rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-bold text-zinc-200 hover:bg-zinc-800"
        >
          <X size={14} />
          Fechar
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4" style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 24px)' }}>
        {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{erro}</p>}
        {!erro && !documento && <p className="text-sm text-zinc-400">Carregando...</p>}
        {documento && <TextoDocumento conteudo={documento.conteudo} />}
      </div>
    </div>
  )
}
