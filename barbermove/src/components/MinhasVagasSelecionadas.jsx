import React, { useCallback, useEffect, useState } from 'react';
import { MessageCircle } from 'lucide-react';
import ChatVaga from './ChatVaga';
import { aoReceberMensagemVaga, buscarMinhasSelecoes } from '../utils/vagas';

const INTERVALO_ATUALIZACAO_MS = 15000;

// Vagas para as quais o freelancer foi escolhido, com acesso ao chat privado de cada uma.
export default function MinhasVagasSelecionadas({ API_URL, token }) {
  const [vagas, setVagas] = useState([]);
  const [chatVaga, setChatVaga] = useState(null);

  const carregar = useCallback(async () => {
    try {
      const lista = await buscarMinhasSelecoes(API_URL, token);
      setVagas(Array.isArray(lista) ? lista : []);
    } catch (_error) {
      // Mantem a ultima lista carregada; tenta de novo no proximo ciclo.
    }
  }, [API_URL, token]);

  useEffect(() => {
    if (!token) return undefined;
    carregar();
    const intervalo = window.setInterval(carregar, INTERVALO_ATUALIZACAO_MS);
    const pararDeOuvir = aoReceberMensagemVaga(carregar);
    return () => {
      window.clearInterval(intervalo);
      pararDeOuvir();
    };
  }, [carregar, token]);

  if (vagas.length === 0 && !chatVaga) return null;

  return (
    <div className="rounded-2xl border border-emerald-600/40 bg-emerald-950/10 p-4 space-y-2" data-testid="minhas-vagas">
      <p className="text-xs font-bold text-emerald-300 uppercase tracking-wide">Você foi escolhido</p>
      {vagas.map((vaga) => (
        <div key={vaga.id} className="flex items-center justify-between gap-3 rounded-xl border border-zinc-800 bg-zinc-900/80 p-3">
          <div className="min-w-0">
            <p className="text-sm font-bold text-white truncate">{vaga.barbearia_nome}</p>
            <p className="text-xs text-zinc-400">
              {vaga.cadeira_bloqueada
                ? 'A barbearia libera a cadeira quando você chegar. Até lá, você não recebe chamados dela.'
                : 'Cadeira liberada.'}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setChatVaga({ id: vaga.id, titulo: vaga.barbearia_nome })}
            className="relative shrink-0 inline-flex items-center gap-1 rounded-lg bg-zinc-800 px-3 py-2 text-xs font-bold text-white hover:bg-zinc-700"
          >
            <MessageCircle size={14} /> Chat
            {vaga.nao_lidas > 0 && (
              <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-orange-500 text-[9px] font-black flex items-center justify-center">
                {vaga.nao_lidas}
              </span>
            )}
          </button>
        </div>
      ))}
      {chatVaga && (
        <ChatVaga
          token={token}
          apiBase={API_URL}
          vagaId={chatVaga.id}
          titulo={chatVaga.titulo}
          onFechar={() => { setChatVaga(null); carregar(); }}
        />
      )}
    </div>
  );
}
