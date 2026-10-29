import React, { useState } from 'react'
import { FileText, ShieldCheck } from 'lucide-react'
import DocumentoLegal from './DocumentoLegal'

// Um bloco por documento: link para o texto completo + caixa de seleção própria
// (começa desmarcada; abrir o documento não marca nada).
// confirmados: { [codigo]: true }

export const todosConfirmados = (documentos, confirmados) =>
  documentos.length > 0 && documentos.every((doc) => confirmados[doc.codigo] === true)

export default function CaixasTermos({ API_URL, documentos, confirmados, onChange, desabilitado = false }) {
  const [aberto, setAberto] = useState(null)

  return (
    <div className="space-y-2">
      {documentos.map((doc) => {
        const Icone = doc.tipo === 'politica_privacidade' ? ShieldCheck : FileText
        const marcado = confirmados[doc.codigo] === true
        return (
          <div key={doc.codigo} className="rounded-xl border border-zinc-800 bg-black/30 p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex min-w-0 items-center gap-2">
                <Icone size={16} className="shrink-0 text-orange-400" />
                <p className="text-sm font-bold leading-tight">{doc.titulo}</p>
              </div>
              <span className="shrink-0 text-[10px] text-zinc-500">v{doc.versao}</span>
            </div>
            <button
              type="button"
              onClick={() => setAberto(doc)}
              className="mt-1 text-xs font-semibold text-orange-300 underline underline-offset-2 hover:text-orange-200"
            >
              Ler documento completo
            </button>
            <label className="mt-2 flex cursor-pointer items-start gap-2 text-xs text-zinc-200">
              <input
                type="checkbox"
                checked={marcado}
                disabled={desabilitado}
                onChange={(event) => onChange(doc.codigo, event.target.checked)}
                className="mt-0.5 h-4 w-4 shrink-0 accent-orange-500"
              />
              <span>{doc.confirmacao}</span>
            </label>
          </div>
        )
      })}

      {aberto && (
        <DocumentoLegal API_URL={API_URL} codigo={aberto.codigo} versao={aberto.versao} onFechar={() => setAberto(null)} />
      )}
    </div>
  )
}
