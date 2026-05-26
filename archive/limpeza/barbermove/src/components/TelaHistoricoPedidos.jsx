import React from 'react';
import ScreenWrapper from './ScreenWrapper';

export function TelaHistoricoPedidos({ historico, aoSelecionarPedido }) {
  const listaPedidos = historico || [
    { id: 43, data: "20/05/2026", servico: "Cabelo e Barba", profissional: "Lari", valor: "R$ 80,00", status: "CONCLUIDO" },
    { id: 42, data: "12/05/2026", servico: "Corte Degradê", profissional: "Allan", valor: "R$ 50,00", status: "CONCLUIDO" },
    { id: 41, data: "05/05/2026", servico: "Barba Completa", profissional: "Lari", valor: "R$ 30,00", status: "CANCELADO" }
  ];

  return (
    <ScreenWrapper>
      <div className="flex justify-between items-center mb-5 border-b border-zinc-900 pb-3">
        <h1 className="text-lg font-black tracking-tight text-white">Meus Pedidos</h1>
        <span className="text-[10px] text-zinc-500 uppercase font-black tracking-wider bg-zinc-900 px-2.5 py-1 rounded-md">Histórico</span>
      </div>

      <button className="flex items-center gap-2 text-zinc-400 text-xs mb-5 hover:text-white transition-all bg-transparent border-none cursor-pointer">
        <span>←</span> Voltar para o início
      </button>

      <div className="space-y-3.5">
        {listaPedidos.map((pedido) => (
          <div key={pedido.id} className="bg-[#1e1e24] rounded-2xl p-4 border border-zinc-800/40 shadow-lg flex flex-col justify-between">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] text-zinc-500 block font-medium uppercase tracking-wider">{pedido.data}</span>
                <h3 className="text-base font-bold text-white mt-0.5">{pedido.servico}</h3>
                <p className="text-xs text-zinc-400 mt-0.5">Profissional: <span className="text-zinc-200 font-semibold">{pedido.profissional}</span></p>
              </div>

              <span className={`text-[9px] font-black tracking-widest uppercase px-2.5 py-1 rounded-full ${
                pedido.status === 'CONCLUIDO'
                  ? 'bg-emerald-500/10 text-[#22c55e] border border-emerald-500/20'
                  : 'bg-red-500/10 text-red-400 border border-red-500/20'
              }`}>
                {pedido.status}
              </span>
            </div>

            <div className="flex justify-between items-center mt-4 pt-3 border-t border-zinc-800/60">
              <div>
                <span className="text-[10px] text-zinc-500 block uppercase tracking-wider font-semibold">Valor Pago</span>
                <span className="text-sm font-black text-white">{pedido.valor}</span>
              </div>
              <button onClick={() => aoSelecionarPedido && aoSelecionarPedido(pedido.id)} className="bg-[#f97316] hover:bg-orange-600 active:scale-[0.97] text-white text-xs font-bold px-4 py-2 rounded-xl transition-all border-none cursor-pointer">Ver Detalhes</button>
            </div>
          </div>
        ))}
      </div>
    </ScreenWrapper>
  );
}

export default TelaHistoricoPedidos;
