// LGPD: o próprio usuário exclui a conta (backend anonimiza os dados pessoais).
import React, { useState } from 'react';
import { Trash2, Loader } from 'lucide-react';

export default function ExcluirConta({ token, apiBase, onExcluida, onNotify }) {
  const [aberto, setAberto] = useState(false);
  const [senha, setSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState('');

  const podeEnviar = senha.length > 0 && confirmacao.trim().toUpperCase() === 'EXCLUIR' && !enviando;

  const excluir = async () => {
    if (!podeEnviar) return;
    setEnviando(true);
    setErro('');
    try {
      const resp = await fetch(`${apiBase}/api/v1/conta/excluir`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ senha, confirmacao }),
      });
      const dados = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        setErro(typeof dados?.detail === 'string' ? dados.detail : 'Não foi possível excluir a conta.');
        return;
      }
      onNotify?.(dados?.mensagem || 'Conta excluída.', 'success');
      onExcluida?.();
    } catch (_e) {
      setErro('Sem conexão. Tente de novo.');
    } finally {
      setEnviando(false);
    }
  };

  if (!aberto) {
    return (
      <button
        type="button"
        data-testid="abrir-excluir-conta"
        onClick={() => setAberto(true)}
        className="mx-auto mt-2 mb-4 flex items-center gap-2 text-xs font-bold text-zinc-500 hover:text-red-400"
      >
        <Trash2 size={14} />
        Excluir minha conta
      </button>
    );
  }

  return (
    <div className="mb-4 space-y-3 rounded-2xl border border-red-500/40 bg-red-500/5 p-4" data-testid="excluir-conta">
      <p className="text-sm font-black text-red-300">Excluir minha conta</p>
      <p className="text-xs leading-relaxed text-zinc-400">
        Apagamos seu nome, e-mail, telefone, documentos, fotos, localização e dados bancários.
        Você não conseguirá mais entrar com esta conta. Atendimentos e pagamentos já feitos ficam
        guardados sem identificar você, porque a lei obriga a manter esses registros.
      </p>
      <input
        type="password"
        autoComplete="current-password"
        placeholder="Sua senha"
        value={senha}
        onChange={(e) => setSenha(e.target.value)}
        className="w-full rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:border-red-400 focus:outline-none"
      />
      <input
        type="text"
        autoCapitalize="characters"
        placeholder='Digite EXCLUIR para confirmar'
        value={confirmacao}
        onChange={(e) => setConfirmacao(e.target.value)}
        className="w-full rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:border-red-400 focus:outline-none"
      />
      {erro && <p className="text-xs font-bold text-red-400">{erro}</p>}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => { setAberto(false); setSenha(''); setConfirmacao(''); setErro(''); }}
          className="flex-1 rounded-xl border border-zinc-700 px-3 py-2 text-sm font-bold text-zinc-300"
        >
          Cancelar
        </button>
        <button
          type="button"
          data-testid="confirmar-excluir-conta"
          onClick={excluir}
          disabled={!podeEnviar}
          className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-red-600 px-3 py-2 text-sm font-black text-white disabled:opacity-40"
        >
          {enviando ? <Loader size={14} className="animate-spin" /> : <Trash2 size={14} />}
          Excluir
        </button>
      </div>
    </div>
  );
}
