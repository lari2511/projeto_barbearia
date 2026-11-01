import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Send } from 'lucide-react';
import BotaoVoltar from './BotaoVoltar';
import { useBackHandler } from '../utils/useBackHandler';
import { formatarDataSP, formatarHoraSP } from '../utils/dataHora';
import {
  aoReceberMensagemSuporte,
  buscarConversaSuporte,
  definirChatSuporteAberto,
  enviarMensagemSuporte,
  marcarSuporteLido,
} from '../utils/suporte';

const INTERVALO_ATUALIZACAO_MS = 8000;
const TAMANHO_MAXIMO = 2000;

// Conversa do usuario autenticado com o ADM. Tela cheia sobre o dashboard, igual
// para os tres perfis: o backend resolve a conversa e o perfil pelo token.
export default function ChatSuporte({ token, apiBase, onFechar }) {
  const [mensagens, setMensagens] = useState(null);
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
      const dados = await buscarConversaSuporte(apiBase, token);
      setMensagens(dados.mensagens);
      setFalhaAoCarregar(false);
      if (document.visibilityState === 'visible' && dados.mensagens.some((m) => m.do_adm && !m.lida)) {
        await marcarSuporteLido(apiBase, token);
      }
    } catch (_error) {
      setFalhaAoCarregar(true);
    }
  }, [apiBase, token]);

  useEffect(() => {
    definirChatSuporteAberto(true);
    carregar();
    const intervalo = window.setInterval(carregar, INTERVALO_ATUALIZACAO_MS);
    const pararDeOuvir = aoReceberMensagemSuporte(carregar);
    return () => {
      definirChatSuporteAberto(false);
      window.clearInterval(intervalo);
      pararDeOuvir();
    };
  }, [carregar]);

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
      const nova = await enviarMensagemSuporte(apiBase, token, conteudo);
      setMensagens((atuais) => (atuais?.some((m) => m.id === nova.id) ? atuais : [...(atuais || []), nova]));
      setTexto('');
    } catch (_error) {
      setErroEnvio('Não foi possível enviar. Verifique sua conexão e tente de novo.');
    } finally {
      setEnviando(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[60] flex justify-center bg-[#050507]" data-testid="chat-suporte">
      <div
        className="flex h-[100dvh] w-full max-w-[430px] flex-col bg-[#0a0a0c]"
        style={{ paddingTop: 'env(safe-area-inset-top)', paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <header className="flex items-center gap-2 border-b border-zinc-800 px-3 py-2">
          <BotaoVoltar onClick={onFechar} />
          <div className="min-w-0">
            <h1 className="text-sm font-black text-white">Falar com o ADM</h1>
            <p className="text-xs text-zinc-400">Sua conversa fica salva aqui</p>
          </div>
        </header>

        <div className="flex-1 space-y-2 overflow-y-auto px-3 py-3">
          {mensagens === null && !falhaAoCarregar && (
            <p className="py-8 text-center text-sm text-zinc-400">Carregando conversa...</p>
          )}
          {mensagens === null && falhaAoCarregar && (
            <p className="py-8 text-center text-sm text-red-300">
              Não foi possível carregar a conversa. Tentando de novo...
            </p>
          )}
          {mensagens?.length === 0 && (
            <p className="py-8 text-center text-sm text-zinc-400">
              Escreva sua mensagem abaixo. O ADM responde por aqui mesmo.
            </p>
          )}
          {mensagens?.map((m) => (
            <div key={m.id} className={`flex ${m.do_adm ? 'justify-start' : 'justify-end'}`}>
              <div
                className={`max-w-[82%] rounded-2xl px-3 py-2 ${
                  m.do_adm ? 'rounded-bl-sm bg-zinc-800 text-zinc-100' : 'rounded-br-sm bg-orange-500 text-white'
                }`}
              >
                {m.do_adm && <p className="mb-0.5 text-[11px] font-black text-orange-300">ADM</p>}
                <p className="whitespace-pre-wrap break-words text-sm">{m.mensagem}</p>
                <p className={`mt-1 text-right text-[10px] ${m.do_adm ? 'text-zinc-400' : 'text-orange-100'}`}>
                  {formatarDataSP(m.criado_em)} {formatarHoraSP(m.criado_em)}
                  {!m.do_adm && m.lida ? ' · Lida' : ''}
                </p>
              </div>
            </div>
          ))}
          <div ref={fimRef} />
        </div>

        <form onSubmit={enviar} className="border-t border-zinc-800 p-2">
          {erroEnvio && <p className="px-1 pb-2 text-xs text-red-300">{erroEnvio}</p>}
          <div className="flex items-end gap-2">
            <textarea
              value={texto}
              onChange={(event) => setTexto(event.target.value)}
              maxLength={TAMANHO_MAXIMO}
              rows={2}
              placeholder="Digite sua mensagem"
              aria-label="Mensagem para o ADM"
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
      </div>
    </div>,
    document.body
  );
}
