import React, { useCallback, useEffect, useState } from 'react';

// "Valores a cobrar a domicílio" (perfil do freelancer).
// Mesmo padrão do cadastro de serviços do proprietário (ShopDashboard), mas os
// preços são do freelancer e independentes dos preços da barbearia. Só clientes
// que escolhem A DOMICÍLIO veem estes valores. Valor vazio = não oferece.
// Mudar um preço não altera chamados já feitos (o backend versiona o serviço).

const FORM_VAZIO = { nome: '', valor: '', duracao_minutos: '30' };

const paraTexto = (valor) => (valor == null || valor === '' ? '' : String(valor).replace('.', ','));
const paraNumero = (texto) => {
  const bruto = String(texto ?? '').trim();
  // "1.234,50" / "49,90" (vírgula decimal) ou "49.90" (ponto decimal)
  const limpo = bruto.includes(',') ? bruto.replace(/\./g, '').replace(',', '.') : bruto;
  if (!limpo) return null;
  const numero = Number(limpo);
  return Number.isFinite(numero) ? numero : NaN;
};

export default function ServicosDomicilioFreelancer({ token, API_URL, notify }) {
  const [ativo, setAtivo] = useState(false);
  const [itens, setItens] = useState([]);   // serviços-modelo (mesmos do proprietário)
  const [outros, setOutros] = useState([]); // serviços criados pelo freelancer
  const [valores, setValores] = useState({}); // nome -> texto digitado
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [novo, setNovo] = useState(FORM_VAZIO);

  const avisar = useCallback((msg, tipo = 'info') => {
    if (typeof notify === 'function') notify(msg, tipo);
  }, [notify]);

  const requisitar = useCallback(async (caminho, opcoes = {}) => {
    const res = await fetch(`${API_URL}/api/v1/domicilio${caminho}`, {
      ...opcoes,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
    return data;
  }, [API_URL, token]);

  const aplicar = useCallback((data) => {
    const modelos = Array.isArray(data?.itens) ? data.itens : [];
    const extras = Array.isArray(data?.outros) ? data.outros : [];
    setAtivo(Boolean(data?.atende_domicilio));
    setItens(modelos);
    setOutros(extras);
    const mapa = {};
    [...modelos, ...extras].forEach((s) => { mapa[s.nome] = paraTexto(s.valor); });
    setValores(mapa);
  }, []);

  const carregar = useCallback(async () => {
    try {
      aplicar(await requisitar('/valores'));
    } catch (_err) {
      // silencioso: a seção só não mostra dados
    } finally {
      setCarregando(false);
    }
  }, [aplicar, requisitar]);

  useEffect(() => { carregar(); }, [carregar]);

  const temValorSalvo = [...itens, ...outros].some((s) => s.valor != null);

  const salvarValores = async () => {
    const lista = [...itens, ...outros].map((s) => ({
      nome: s.nome,
      categoria: s.categoria || 'outros',
      duracao_minutos: Number(s.duracao_minutos) || 30,
      valor: paraNumero(valores[s.nome]),
    }));
    if (lista.some((i) => Number.isNaN(i.valor) || (i.valor != null && i.valor < 0))) {
      avisar('Confira os valores: use só números (ex.: 50 ou 49,90)', 'error');
      return;
    }
    setSalvando(true);
    try {
      aplicar(await requisitar('/valores', { method: 'PUT', body: JSON.stringify({ itens: lista }) }));
      avisar('Valores a domicílio salvos', 'success');
    } catch (err) {
      avisar(err.message || 'Erro ao salvar valores', 'error');
    } finally {
      setSalvando(false);
    }
  };

  const adicionarServico = async (e) => {
    e.preventDefault();
    const valor = paraNumero(novo.valor);
    const duracao = Number(novo.duracao_minutos);
    if (novo.nome.trim().length < 2 || !(valor > 0)) {
      avisar('Preencha nome e valor', 'error');
      return;
    }
    setSalvando(true);
    try {
      await requisitar('/meus-servicos', {
        method: 'POST',
        body: JSON.stringify({ nome: novo.nome.trim(), categoria: 'outros', valor, duracao_minutos: duracao >= 5 ? duracao : 30 }),
      });
      setNovo(FORM_VAZIO);
      avisar('Serviço adicionado!', 'success');
      await carregar();
    } catch (err) {
      avisar(err.message || 'Erro ao salvar serviço', 'error');
    } finally {
      setSalvando(false);
    }
  };

  const removerOutro = async (servico) => {
    setSalvando(true);
    try {
      await requisitar(`/meus-servicos/${servico.id}`, { method: 'DELETE' });
      await carregar();
    } catch (err) {
      avisar(err.message || 'Erro ao remover serviço', 'error');
    } finally {
      setSalvando(false);
    }
  };

  const alternarAtivo = async () => {
    setSalvando(true);
    try {
      const data = await requisitar('/atendimento', { method: 'PUT', body: JSON.stringify({ atende_domicilio: !ativo }) });
      setAtivo(Boolean(data?.atende_domicilio));
      avisar(data?.atende_domicilio ? 'Você agora aparece para clientes a domicílio' : 'Atendimento a domicílio desligado', 'success');
    } catch (err) {
      avisar(err.message, 'error');
    } finally {
      setSalvando(false);
    }
  };

  const linhaValor = (s, extra = null) => (
    <div key={s.nome} className="flex items-center justify-between gap-3 bg-black/60 p-3 rounded-lg border border-purple-600/20">
      <div className="min-w-0">
        <p className="text-sm font-medium text-white truncate">{s.nome}</p>
        <p className="text-[11px] text-zinc-500">{s.duracao_minutos || 30} min</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <div className="flex items-center rounded-lg border border-zinc-800 bg-black focus-within:border-purple-500">
          <span className="pl-2 text-xs text-zinc-500">R$</span>
          <input
            inputMode="decimal"
            aria-label={`Valor a domicílio de ${s.nome}`}
            placeholder="—"
            value={valores[s.nome] ?? ''}
            onChange={(e) => setValores((v) => ({ ...v, [s.nome]: e.target.value.replace(/[^\d.,]/g, '') }))}
            className="w-20 bg-transparent p-2 text-right text-sm text-green-400 font-bold outline-none"
          />
        </div>
        {extra}
      </div>
    </div>
  );

  return (
    <div className="bg-zinc-900/60 p-5 rounded-2xl border border-purple-600/30 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-bold text-sm flex items-center gap-2 text-purple-400">🏠 Valores a cobrar a domicílio</h3>
          <p className="mt-1 text-[11px] text-zinc-500">
            Só clientes que escolhem A DOMICÍLIO veem estes valores. Os preços da barbearia não mudam. Deixe vazio o que você não oferece.
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={ativo}
          aria-label="Atendo a domicílio"
          onClick={alternarAtivo}
          disabled={carregando || salvando || (!ativo && !temValorSalvo)}
          className={`relative mt-0.5 h-7 w-12 shrink-0 rounded-full transition-colors disabled:opacity-50 ${ativo ? 'bg-orange-500' : 'bg-zinc-700'}`}
        >
          <span className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-all ${ativo ? 'left-6' : 'left-1'}`} />
        </button>
      </div>
      <p className={`text-[11px] font-semibold ${ativo ? 'text-emerald-300' : 'text-zinc-500'}`}>
        {ativo ? 'Atendendo a domicílio: clientes próximos podem chamar você.' : (temValorSalvo ? 'Ligue o botão para aparecer para clientes a domicílio.' : 'Salve ao menos um valor para poder ligar o atendimento a domicílio.')}
      </p>

      {carregando ? (
        <p className="text-xs text-zinc-500 text-center py-4">Carregando...</p>
      ) : (
        <>
          <div className="space-y-2">
            {itens.map((s) => linhaValor(s))}
            {outros.map((s) => linhaValor(s, (
              <button
                type="button"
                onClick={() => removerOutro(s)}
                disabled={salvando}
                className="text-[11px] font-bold text-red-400 hover:text-red-300 disabled:opacity-50"
              >
                Remover
              </button>
            )))}
          </div>

          <button
            type="button"
            onClick={salvarValores}
            disabled={salvando}
            className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white px-4 py-3 rounded-lg font-bold text-sm transition-all"
          >
            {salvando ? 'Salvando...' : 'Salvar valores'}
          </button>

          <form onSubmit={adicionarServico} className="space-y-3 border-t border-zinc-800 pt-4">
            <p className="text-xs font-bold text-zinc-400">Outro serviço a domicílio</p>
            <input
              className="w-full bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-purple-500 text-white"
              placeholder="Nome do serviço (ex: Pigmentação)"
              maxLength={80}
              value={novo.nome}
              onChange={(e) => setNovo({ ...novo, nome: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-3">
              <input
                className="bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-purple-500 text-white"
                inputMode="decimal"
                placeholder="Valor R$"
                value={novo.valor}
                onChange={(e) => setNovo({ ...novo, valor: e.target.value.replace(/[^\d.,]/g, '') })}
              />
              <input
                className="bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-purple-500 text-white"
                inputMode="numeric"
                placeholder="Duração (min)"
                value={novo.duracao_minutos}
                onChange={(e) => setNovo({ ...novo, duracao_minutos: e.target.value.replace(/\D/g, '') })}
              />
            </div>
            <button type="submit" disabled={salvando} className="w-full bg-orange-600 hover:bg-orange-700 disabled:opacity-60 text-white px-4 py-3 rounded-lg font-bold text-sm transition-all">
              + Adicionar Serviço
            </button>
          </form>
        </>
      )}
    </div>
  );
}
