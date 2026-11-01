import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Send } from 'lucide-react';
import BotaoVoltar from './BotaoVoltar';
import { useBackHandler } from '../utils/useBackHandler';
import { formatarDataSP, formatarHoraSP } from '../utils/dataHora';
import {
  aoReceberMensagemVaga,
  buscarConversaVaga,
  definirChatVagaAberto,
  enviarMensagemVaga,
  marcarVagaLida,
} from '../utils/vagas';

const INTERVALO_ATUALIZACAO_MS = 8000;
const TAMANHO_MAXIMO = 2000;

// Conversa privada da vaga entre o dono da barbearia e o freelancer escolhido.
// Separada do chat dos chamados (ChatRoom): o backend libera o acesso pelo token.
export default function ChatVaga({ token, apiBase, vagaId, titulo, onFechar }) {
  const [conversa, setConversa] = useState(null);
  const [falhaAoCarregar, setFalhaAoCarregar] = useState(false);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState('');
  const fimRef = useRef(null);

  useBackHandler(() => {
    onFechar();
    return true;
  }, [onFechar]);

  const carregar = useCallback(async () => {
    try {
      const dados = await buscarConversaVaga(apiBase, token, vagaId);
      setConversa(dados);
      setFalhaAoCarregar(false);
      if (document.visibilityState === 'visible' && dados.mensagens.some((m) => !m.minha && !m.lida)) {
        await marcarVagaLida(apiBase, token, vagaId);
      }
    } catch (_error) {
      setFalhaAoCarregar(true);
    }
  }, [apiBase, token, vagaId]);

  useEffect(() => {
    definirChatVagaAberto(vagaId);
    carregar();
    const intervalo = window.setInterval(carregar, INTERVALO_ATUALIZACAO_MS);
    const pararDeOuvir = aoReceberMensagemVaga(carregar);
    return () => {
      definirChatVagaAberto(null);
      window.clearInterval(intervalo);
      pararDeOuvir();
    };
  }, [carregar, vagaId]);

  const mensagens = conversa?.mensagens;
  const totalMensagens = mensagens?.length || 0;
  useEffect(() => {
    fimRef.current?.scrollIntoView({ block: 'end' });
  }, [totalMensagens]);

  const enviar = async (event) => {
    event.preventDefault();
    const conteudo = texto.trim();
    if (!conteudo || enviando) return;
    setEnviando(true);
    setErroEnvio('');
    try {
      const nova = await enviarMensagemVaga(apiBase, token, vagaId, conteudo);
      setConversa((atual) => (
        atual?.mensagens.some((m) => m.id === nova.id)
          ? atual
          : { ...atual, mensagens: [...(atual?.mensagens || []), nova] }
      ));
      setTexto('');
    } catch (error) {
      setErroEnvio(error?.message || 'Não foi possível enviar. Verifique sua conexão e tente de novo.');
    } finally {
      setEnviando(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[60] flex justify-center bg-[#050507]" data-testid="chat-vaga">
      <div
        className="flex h-[100dvh] w-full max-w-[430px] flex-col bg-[#0a0a0c]"
        style={{ paddingTop: 'env(safe-area-inset-top)', paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <header className="flex items-center gap-2 border-b border-zinc-800 px-3 py-2">
          <BotaoVoltar onClick={onFechar} />
          <div className="min-w-0">
            <h1 className="truncate text-sm font-black text-white">{titulo || 'Chat da vaga'}</h1>
            <p className="text-xs text-zinc-400">Conversa privada sobre esta vaga</p>
          </div>
        </header>

        <div className="flex-1 space-y-2 overflow-y-auto px-3 py-3">
          {!conversa && !falhaAoCarregar && (
            <p className="py-8 text-center text-sm text-zinc-400">Carregando conversa...</p>
          )}
          {!conversa && falhaAoCarregar && (
            <p className="py-8 text-center text-sm text-red-300">
              Não foi possível carregar a conversa. Tentando de novo...
            </p>
          )}
          {mensagens?.length === 0 && (
            <p className="py-8 text-center text-sm text-zinc-400">
              Nenhuma mensagem ainda. Use este chat para combinar a chegada na barbearia.
            </p>
          )}
          {mensagens?.map((m) => (
            <div key={m.id} className={`flex ${m.minha ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[82%] rounded-2xl px-3 py-2 ${
                  m.minha ? 'rounded-br-sm bg-orange-500 text-white' : 'rounded-bl-sm bg-zinc-800 text-zinc-100'
                }`}
              >
                <p className="whitespace-pre-wrap break-words text-sm">{m.mensagem}</p>
                <p className={`mt-1 text-right text-[10px] ${m.minha ? 'text-orange-100' : 'text-zinc-400'}`}>
                  {formatarDataSP(m.criado_em)} {formatarHoraSP(m.criado_em)}
                  {m.minha && m.lida ? ' · Lida' : ''}
                </p>
              </div>
            </div>
          ))}
          <div ref={fimRef} />
        </div>

        {conversa?.aberta === false ? (
          <p className="border-t border-zinc-800 p-3 text-center text-xs text-zinc-400">
            Esta vaga foi encerrada. A conversa fica disponível só para leitura.
          </p>
        ) : (
          <form onSubmit={enviar} className="border-t border-zinc-800 p-2">
            {erroEnvio && <p className="px-1 pb-2 text-xs text-red-300">{erroEnvio}</p>}
            <div className="flex items-end gap-2">
              <textarea
                value={texto}
                onChange={(event) => setTexto(event.target.value)}
                maxLength={TAMANHO_MAXIMO}
                rows={2}
                placeholder="Digite sua mensagem"
                aria-label="Mensagem no chat da vaga"
                className="min-w-0 flex-1 resize-none rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:border-orange-500 focus:outline-none"
              />
              <button
                type="submit"
                disabled={enviando || !texto.trim()}
                aria-label="Enviar mensagem"
                className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-orange-500 text-white disabled:opacity-40"
              >
                <Send size={18} />
              </button>
            </div>
          </form>
        )}
      </div>
    </div>,
    document.body
  );
}
