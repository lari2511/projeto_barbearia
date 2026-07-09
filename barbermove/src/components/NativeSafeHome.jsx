import React from 'react';

export default function NativeSafeHome({ userType, API_URL, onLogout }) {
  const [status, setStatus] = React.useState('ok');
  const [mensagem, setMensagem] = React.useState('Modo seguro ativo');
  const [loading, setLoading] = React.useState(false);

  const testarConexao = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/openapi.json`, { cache: 'no-store' });
      if (!res.ok) {
        setStatus('erro');
        setMensagem(`Servidor respondeu ${res.status}`);
        return;
      }
      setStatus('ok');
      setMensagem('Conexao com servidor OK');
    } catch (_err) {
      setStatus('erro');
      setMensagem('Falha de rede com o servidor');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b0b0d] text-white p-4 flex items-center justify-center">
      <div className="w-full max-w-[420px] rounded-2xl border border-zinc-800 bg-zinc-950 p-4 space-y-4">
        <h1 className="text-lg font-black">BarberMove - Modo Seguro</h1>
        <p className="text-sm text-zinc-300">Login concluido para perfil: <span className="font-bold">{userType || 'desconhecido'}</span></p>
        <p className="text-xs text-zinc-400 break-all">API: {API_URL}</p>

        <div className={`rounded-xl px-3 py-2 text-sm ${status === 'ok' ? 'bg-emerald-900/30 border border-emerald-600/40 text-emerald-300' : 'bg-red-900/30 border border-red-600/40 text-red-300'}`}>
          {mensagem}
        </div>

        <button
          type="button"
          onClick={testarConexao}
          className="w-full rounded-xl bg-orange-500 px-3 py-3 text-sm font-black text-white"
          disabled={loading}
        >
          {loading ? 'Testando...' : 'Testar conexao servidor'}
        </button>

        <button
          type="button"
          onClick={onLogout}
          className="w-full rounded-xl border border-zinc-700 px-3 py-3 text-sm font-bold text-zinc-200"
        >
          Sair
        </button>
      </div>
    </div>
  );
}
