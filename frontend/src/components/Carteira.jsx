import React, { useState, useEffect } from 'react'
import { barberService } from '../services/barberService'
import LayoutMobile from './LayoutMobile'
import Navbar from './Navbar'

export default function Carteira() {
  const [activeMenu, setActiveMenu] = useState('carteira')
  const [saldo, setSaldo] = useState(0.0)
  const [historico, setHistorico] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function carregarDadosCarteira() {
      try {
        const response = await barberService.getCarteira()
        const saldoNormalizado = response?.saldo ?? response?.valor ?? response?.total ?? 0
        const transacoesNormalizadas = response?.transacoes ?? response?.historico ?? response?.movimentacoes ?? []
        setSaldo(saldoNormalizado)
        setHistorico(transacoesNormalizadas)
      } catch (error) {
        console.error('Erro ao carregar dados financeiros', error)
      } finally {
        setLoading(false)
      }
    }
    carregarDadosCarteira()
  }, [])

  return (
    <LayoutMobile>
      <header className="p-4 border-b border-gray-900/50 bg-barberBg/90 backdrop-blur sticky top-0 z-40 shrink-0 flex justify-between items-center">
        <h2 className="text-sm font-black uppercase tracking-wider text-barberTextGray">Minha Carteira</h2>
        <span className="text-xs bg-barberCard border border-gray-800 px-2 py-1 rounded font-bold">Extrato</span>
      </header>

      <div className="flex-1 p-4 space-y-5 pb-24">
        <div className="bg-gradient-to-br from-barberOrange to-[#B34700] p-6 rounded-2xl shadow-xl space-y-1">
          <p className="text-[11px] text-white/80 font-bold uppercase tracking-widest">Saldo Disponível</p>
          <h3 className="text-3xl font-black text-white">R$ {Number(saldo || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
          <div className="pt-2 flex justify-between items-center text-[11px] text-white/90">
            <span>Rastreamento automático ativo</span>
            <span className="bg-black/20 px-2 py-0.5 rounded font-bold">Barber Move</span>
          </div>
        </div>

        <div className="space-y-3">
          <h4 className="text-xs font-bold text-barberTextGray uppercase tracking-wider">Últimas Movimentações</h4>

          {loading ? (
            <p className="text-xs text-barberTextGray text-center py-4">Buscando transações no banco...</p>
          ) : historico.length === 0 ? (
            <div className="bg-barberCard p-6 rounded-xl border border-gray-900 text-center">
              <p className="text-xs text-barberTextGray">Nenhuma movimentação encontrada.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {historico.map((transacao) => (
                <div key={transacao.id} className="bg-barberCard border border-gray-800/40 p-3.5 rounded-xl flex justify-between items-center">
                  <div>
                    <h5 className="text-xs font-bold text-white">{transacao.descricao}</h5>
                    <p className="text-[10px] text-barberTextGray mt-0.5">{transacao.data}</p>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs font-black ${transacao.tipo === 'entrada' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {transacao.tipo === 'entrada' ? '+' : '-'} R$ {Number(transacao.valor || 0).toFixed(2)}
                    </span>
                    <p className="text-[9px] text-barberTextGray font-medium mt-0.5">{transacao.status}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 z-40 bg-barberBg">
        <Navbar activeTab={activeMenu} setActiveTab={setActiveMenu} />
      </div>
    </LayoutMobile>
  )
}
