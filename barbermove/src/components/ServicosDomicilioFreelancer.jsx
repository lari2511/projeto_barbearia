import React, { useCallback, useEffect, useState } from 'react';
import { House } from 'lucide-react';

// Atendimento A DOMICÍLIO do freelancer: liga/desliga ("Atendo a domicílio") e
// serviços/preços próprios para atender na casa do cliente.
// Só quem liga isto + tem serviço ativo aparece em "Freelancers perto de você".
const CATEGORIAS = [
  { id: 'corte', nome: 'Corte' },
  { id: 'barba', nome: 'Barba' },
  { id: 'combo', nome: 'Combo' },
  { id: 'sobrancelha', nome: 'Sobrancelha' },
  { id: 'infantil', nome: 'Infantil' },
  { id: 'quimica', nome: 'Química' },
  { id: 'tratamento', nome: 'Tratamento' },
  { id: 'outros', nome: 'Outros' },
];

const FORM_VAZIO = { nome: '', categoria: 'corte', valor: '', duracao_minutos: '30' };

const formatarPreco = (valor) => {
  const numero = Number(valor) || 0;
  const casas = Number.isInteger(numero) ? 0 : 2;
  return `R$ ${numero.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: 2 })}`;
};

export default function ServicosDomicilioFreelancer({ token, API_URL, notify }) {
  const [ativo, setAtivo] = useState(false);
  const [servicos, setServicos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);
  const [mostrarForm, setMostrarForm] = useState(false);

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

  const carregar = useCallback(async () => {
    try {
      const data = await requisitar('/meus-servicos');
      setAtivo(Boolean(data?.atende_domicilio));
      setServicos(Array.isArray(data?.servicos) ? data.servicos.filter((s) => s.ativo) : []);
    } catch (_err) {
      // silencioso: o card só não mostra dados
    } finally {
      setCarregando(false);
    }
  }, [requisitar]);

  useEffect(() => { carregar(); }, [carregar]);

  const alternarAtivo = async () => {
    if (salvando) return;
    setSalvando(true);
    try {
      const data = await requisitar('/atendimento', {
        method: 'PUT',
        body: JSON.stringify({ atende_domicilio: !ativo }),
      });
      setAtivo(Boolean(data?.atende_domicilio));
      avisar(data?.atende_domicilio ? 'Você agora aparece para clientes a domicílio' : 'Atendimento a domicílio desligado', 'success');
    } catch (err) {
      avisar(err.message, 'error');
    } finally {
      setSalvando(false);
    }
  };

  const adicionarServico = async (e) => {
    e.preventDefault();
    const valor = Number(String(form.valor).replace(',', '.'));
    const duracao = Number(form.duracao_minutos);
    if (form.nome.trim().length < 2) { avisar('Informe o nome do serviço', 'error'); return; }
    if (!(valor > 0)) { avisar('Informe um preço válido', 'error'); return; }
    if (!(duracao >= 5)) { avisar('Informe a duração em minutos', 'error'); return; }
    setSalvando(true);
    try {
      await requisitar('/meus-servicos', {
        method: 'POST',
        body: JSON.stringify({ nome: form.nome.trim(), categoria: form.categoria, valor, duracao_minutos: duracao }),
      });
      setForm(FORM_VAZIO);
      setMostrarForm(false);
      avisar('Serviço a domicílio cadastrado', 'success');
      await carregar();
    } catch (err) {
      avisar(err.message, 'error');
    } finally {
      setSalvando(false);
    }
  };

  const removerServico = async (servico) => {
    if (salvando) return;
    setSalvando(true);
    try {
      const data = await requisitar(`/meus-servicos/${servico.id}`, { method: 'DELETE' });
      if (data?.atende_domicilio === false && ativo) avisar('Sem serviços ativos: atendimento a domicílio desligado', 'info');
      await carregar();
    } catch (err) {
      avisar(err.message, 'error');
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="h-9 w-9 shrink-0 rounded-xl bg-zinc-800 text-orange-400 flex items-center justify-center"><House size={18} /></span>
          <div className="min-w-0">
            <p className="text-sm font-bold text-white">Atendimento a domicílio</p>
            <p className="text-[11px] text-zinc-500">Clientes perto de você chamam você direto em casa.</p>
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={ativo}
          onClick={alternarAtivo}
          disabled={carregando || salvando || (!ativo && servicos.length === 0)}
          className={`relative h-7 w-12 shrink-0 rounded-full transition-colors disabled:opacity-50 ${ativo ? 'bg-orange-500' : 'bg-zinc-700'}`}
          aria-label="Atendo a domicílio"
        >
          <span className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-all ${ativo ? 'left-6' : 'left-1'}`} />
        </button>
      </div>

      {!carregando && servicos.length === 0 && (
        <p className="text-[11px] text-amber-300/90">Cadastre ao menos um serviço com preço para poder ativar.</p>
      )}

      {servicos.length > 0 && (
        <div className="space-y-1.5">
          {servicos.map((s) => (
            <div key={s.id} className="flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-black/30 px-3 py-2">
              <div className="min-w-0">
                <p className="text-xs font-semibold text-white truncate">{s.nome}</p>
                <p className="text-[11px] text-zinc-500">{s.duracao_minutos} min · {formatarPreco(s.valor)}</p>
              </div>
              <button
                type="button"
                onClick={() => removerServico(s)}
                disabled={salvando}
                className="shrink-0 text-[11px] font-bold text-red-400 hover:text-red-300 disabled:opacity-50"
              >
                Remover
              </button>
            </div>
          ))}
        </div>
      )}

      {mostrarForm ? (
        <form onSubmit={adicionarServico} className="space-y-2 rounded-xl border border-zinc-800 bg-black/30 p-3">
          <input
            value={form.nome}
            onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
            maxLength={80}
            placeholder="Nome do serviço (ex.: Corte em casa)"
            className="bm-input w-full px-3 py-2 rounded-lg border border-zinc-800 outline-none focus:border-orange-500 text-sm text-white"
          />
          <select
            value={form.categoria}
            onChange={(e) => setForm((f) => ({ ...f, categoria: e.target.value }))}
            className="bm-input w-full px-3 py-2 rounded-lg border border-zinc-800 outline-none focus:border-orange-500 text-sm text-white bg-zinc-950"
          >
            {CATEGORIAS.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
          <div className="grid grid-cols-2 gap-2">
            <input
              value={form.valor}
              onChange={(e) => setForm((f) => ({ ...f, valor: e.target.value }))}
              inputMode="decimal"
              placeholder="Preço (R$)"
              className="bm-input w-full px-3 py-2 rounded-lg border border-zinc-800 outline-none focus:border-orange-500 text-sm text-white"
            />
            <input
              value={form.duracao_minutos}
              onChange={(e) => setForm((f) => ({ ...f, duracao_minutos: e.target.value.replace(/\D/g, '') }))}
              inputMode="numeric"
              placeholder="Duração (min)"
              className="bm-input w-full px-3 py-2 rounded-lg border border-zinc-800 outline-none focus:border-orange-500 text-sm text-white"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button type="button" onClick={() => { setMostrarForm(false); setForm(FORM_VAZIO); }} className="rounded-lg border border-zinc-700 py-2 text-xs font-bold text-zinc-300">
              Cancelar
            </button>
            <button type="submit" disabled={salvando} className="rounded-lg bg-orange-600 py-2 text-xs font-bold text-white hover:bg-orange-500 disabled:opacity-60">
              {salvando ? 'Salvando...' : 'Salvar serviço'}
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setMostrarForm(true)}
          className="w-full rounded-lg border border-dashed border-zinc-700 py-2 text-xs font-bold text-zinc-300 hover:border-orange-500 hover:text-orange-300"
        >
          + Adicionar serviço a domicílio
        </button>
      )}
    </div>
  );
}
