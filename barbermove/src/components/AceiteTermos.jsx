import React, { useState } from 'react'
import { Calendar, LogOut } from 'lucide-react'
import { Button, Input } from './Common'
import CaixasTermos, { todosConfirmados } from './CaixasTermos'
import DocumentoLegal from './DocumentoLegal'
import { aceitarDocumentos, recusarDocumentos } from '../utils/termos'
import { erroDataNascimentoFreelancer } from '../utils/cadastroFreelancer'

// Tela de aceite obrigatório (usuário já logado sem aceite vigente das versões publicadas).
// Recusar não exclui a conta: a pessoa continua podendo ler os documentos, sair e pedir suporte.

export default function AceiteTermos({ API_URL, token, situacao, onLiberado, onAtualizar, onSair }) {
  const [confirmados, setConfirmados] = useState({})
  const [nascimento, setNascimento] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')
  const [recusou, setRecusou] = useState(Boolean(situacao?.recusou))
  const [lendo, setLendo] = useState(null)

  const pendentes = situacao?.pendentes || []
  const exigeNascimento = Boolean(situacao?.exige_data_nascimento)
  const atualizacao = pendentes.some((doc) => doc.atualizacao)
  const podeAceitar = (pendentes.length === 0 || todosConfirmados(pendentes, confirmados)) && (!exigeNascimento || nascimento)

  const aceitar = async () => {
    if (exigeNascimento) {
      const erroData = erroDataNascimentoFreelancer(nascimento)
      if (erroData) {
        setErro(erroData)
        return
      }
    }
    setEnviando(true)
    setErro('')
    try {
      const nova = await aceitarDocumentos(API_URL, token, pendentes, exigeNascimento ? nascimento : undefined)
      if (nova?.liberado) onLiberado(nova)
      else onAtualizar(nova)
    } catch (err) {
      setErro(err?.message || 'Não foi possível registrar o aceite')
      // Versão mudou enquanto a tela estava aberta: recarrega os documentos.
      if (/atualizado/i.test(err?.message || '')) {
        setConfirmados({})
        onAtualizar()
      }
    } finally {
      setEnviando(false)
    }
  }

  const recusar = async () => {
    setEnviando(true)
    setErro('')
    try {
      await recusarDocumentos(API_URL, token)
      setConfirmados({})
      setRecusou(true)
    } catch (err) {
      setErro(err?.message || 'Não foi possível registrar a recusa')
    } finally {
      setEnviando(false)
    }
  }

  const botaoSair = (
    <button type="button" onClick={onSair} className="flex items-center gap-1 text-xs text-zinc-400 hover:text-white">
      <LogOut size={14} />
      Sair
    </button>
  )

  if (situacao?.bloqueio_idade) {
    return (
      <Moldura titulo="Cadastro de freelancer não permitido" acao={botaoSair}>
        <p className="text-sm text-zinc-300">
          É preciso ter 18 anos completos para atuar como freelancer no BarberMove. As funcionalidades de freelancer
          ficam indisponíveis nesta conta. Para corrigir a data informada ou encerrar a conta, fale com o suporte
          pelo canal informado nos Termos de Uso.
        </p>
      </Moldura>
    )
  }

  if (recusou) {
    return (
      <Moldura titulo="Documentos não aceitos" acao={botaoSair}>
        <p className="text-sm text-zinc-300">
          Sem o aceite dos Termos de Uso e a ciência da Política de Privacidade, as funcionalidades do aplicativo
          ficam bloqueadas. Sua conta e seus dados não foram excluídos.
        </p>
        <p className="text-sm text-zinc-300">
          Você ainda pode ler os documentos, sair da conta ou falar com o suporte (inclusive para pedir o
          encerramento da conta) pelo canal informado nos documentos.
        </p>
        <div className="space-y-1">
          {pendentes.map((doc) => (
            <button
              key={doc.codigo}
              type="button"
              onClick={() => setLendo(doc)}
              className="block text-left text-xs font-semibold text-orange-300 underline underline-offset-2 hover:text-orange-200"
            >
              Ler: {doc.titulo}
            </button>
          ))}
        </div>
        <Button type="button" fullWidth onClick={() => setRecusou(false)}>
          Revisar e aceitar
        </Button>
        {lendo && <DocumentoLegal API_URL={API_URL} codigo={lendo.codigo} versao={lendo.versao} onFechar={() => setLendo(null)} />}
      </Moldura>
    )
  }

  return (
    <Moldura
      titulo={atualizacao ? 'Documentos atualizados' : 'Termos de Uso e Privacidade'}
      acao={botaoSair}
    >
      <p className="text-xs text-zinc-400">
        {atualizacao
          ? 'Atualizamos documentos do BarberMove. Leia e confirme para continuar usando o aplicativo.'
          : 'Para usar o BarberMove, leia os documentos abaixo e confirme cada um.'}
      </p>

      {exigeNascimento && (
        <div>
          <Input
            label="Data de nascimento"
            type="date"
            icon={Calendar}
            value={nascimento}
            onChange={(event) => setNascimento(event.target.value)}
            required
          />
          <p className="-mt-2 mb-2 text-[11px] text-zinc-500">Freelancers precisam ter 18 anos completos.</p>
        </div>
      )}

      <CaixasTermos
        API_URL={API_URL}
        documentos={pendentes}
        confirmados={confirmados}
        onChange={(codigo, valor) => setConfirmados((atual) => ({ ...atual, [codigo]: valor }))}
        desabilitado={enviando}
      />

      {erro && <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{erro}</div>}

      <Button type="button" fullWidth disabled={!podeAceitar || enviando} onClick={aceitar}>
        {enviando ? 'Enviando...' : 'Aceitar e continuar'}
      </Button>
      {pendentes.length > 0 && (
        <button
          type="button"
          onClick={recusar}
          disabled={enviando}
          className="w-full py-2 text-xs text-zinc-400 hover:text-white disabled:opacity-50"
        >
          Não aceito
        </button>
      )}
    </Moldura>
  )
}

function Moldura({ titulo, acao, children }) {
  return (
    <div className="bg-black text-white flex flex-col justify-start px-1 pt-2 pb-6">
      <div className="w-full min-w-0 rounded-2xl border border-zinc-800/50 bg-[#1e1e24] shadow-xl p-3 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <h1 className="text-xl font-black">{titulo}</h1>
          {acao}
        </div>
        {children}
      </div>
    </div>
  )
}
