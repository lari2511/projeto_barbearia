import React, { useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import BannerVencimentoAssinatura from './components/BannerVencimentoAssinatura';
import ModalBloqueio from './components/ModalBloqueio';
import TelaAssinaturaBarbearia from './components/TelaAssinaturaBarbearia';
import useVerificarBloqueio from './hooks/useVerificarBloqueio';

/**
 * EXEMPLO DE INTEGRAÇÃO COMPLETA
 * 
 * Este componente mostra como integrar todos os componentes
 * do sistema de bloqueio automático no dashboard da barbearia
 */
export default function DashboardBarbearia({ token, userType }) {
  const navigate = useNavigate();
  const [mostrarModalBloqueio, setMostrarModalBloqueio] = useState(false);
  
  // Hook que verifica bloqueio automaticamente
  const { 
    statusBloqueio, 
    estaBloqueada, 
    estaProximoVencimento,
    interceptarBloqueio,
    verificarStatus
  } = useVerificarBloqueio(token);

  // Função helper para ações protegidas
  const executarAcaoProtegida = async (acao, onSucesso) => {
    try {
      await acao();
      onSucesso?.();
    } catch (err) {
      if (err.message === 'BARBEARIA_BLOQUEADA') {
        setMostrarModalBloqueio(true);
      } else {
        console.error('Erro:', err);
        alert(`Erro: ${err.message}`);
      }
    }
  };

  // Exemplo: Criar serviço (ação protegida)
  const criarServico = async (dadosServico) => {
    await executarAcaoProtegida(
      async () => {
        const res = await interceptarBloqueio(
          fetch(`${API_URL}/api/v1/servicos/barbearias/${barbeariaId}/servicos`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`
            },
            body: JSON.stringify(dadosServico)
          })
        );

        if (!res.ok) throw new Error('Erro ao criar serviço');
        return res.json();
      },
      () => {
        alert('Serviço criado com sucesso!');
      }
    );
  };

  // Exemplo: Aprovar agendamento (ação protegida)
  const aprovarAgendamento = async (chamadoId) => {
    await executarAcaoProtegida(
      async () => {
        const res = await interceptarBloqueio(
          fetch(`${API_URL}/api/v1/aprovacoes/chamados/${chamadoId}/aprovacao-barbearia`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` }
          })
        );

        if (!res.ok) throw new Error('Erro ao aprovar');
        return res.json();
      },
      () => {
        alert('Agendamento aprovado!');
      }
    );
  };

  return (
    <div className="min-h-screen bg-black">
      {/* Banner de alerta de vencimento/bloqueio */}
      <BannerVencimentoAssinatura
        token={token}
        onNavigateToPagamento={() => navigate('/assinatura')}
      />

      {/* Modal de bloqueio */}
      <ModalBloqueio
        isOpen={mostrarModalBloqueio}
        onClose={() => setMostrarModalBloqueio(false)}
        statusBloqueio={statusBloqueio}
        token={token}
        onPagamentoSucesso={() => {
          verificarStatus(); // Atualiza status
          window.location.reload(); // Recarrega para aplicar mudanças
        }}
      />

      {/* Conteúdo principal */}
      <div className="container mx-auto p-4">
        <Routes>
          {/* Rota de gerenciamento de assinatura */}
          <Route 
            path="/assinatura" 
            element={
              <TelaAssinaturaBarbearia
                token={token}
                onNotify={(msg, tipo) => alert(msg)}
              />
            } 
          />

          {/* Outras rotas do dashboard */}
          <Route 
            path="/" 
            element={
              <div>
                <h1 className="text-2xl font-bold text-white mb-4">
                  Dashboard da Barbearia
                </h1>

                {/* Indicador de status */}
                {estaBloqueada && (
                  <div className="bg-red-900/20 border border-red-600 rounded-lg p-4 mb-6">
                    <p className="text-red-300 font-bold">
                      ⛔ Barbearia bloqueada! Algumas funcionalidades estão desabilitadas.
                    </p>
                    <button
                      onClick={() => navigate('/assinatura')}
                      className="mt-2 bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
                    >
                      Regularizar Assinatura
                    </button>
                  </div>
                )}

                {estaProximoVencimento && !estaBloqueada && (
                  <div className="bg-yellow-900/20 border border-yellow-600 rounded-lg p-4 mb-6">
                    <p className="text-yellow-300 font-bold">
                      ⚠️ Sua assinatura vence em {statusBloqueio?.dias_vencimento} dias!
                    </p>
                    <button
                      onClick={() => navigate('/assinatura')}
                      className="mt-2 bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded"
                    >
                      Pagar Agora
                    </button>
                  </div>
                )}

                {/* Exemplo de botões que podem ser bloqueados */}
                <div className="grid grid-cols-2 gap-4">
                  <button
                    onClick={() => criarServico({ nome: 'Teste', valor: 50 })}
                    className="bg-orange-600 hover:bg-orange-700 text-white font-bold py-3 rounded-lg"
                  >
                    ➕ Criar Serviço
                  </button>

                  <button
                    onClick={() => aprovarAgendamento(123)}
                    className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-lg"
                  >
                    ✅ Aprovar Agendamento
                  </button>
                </div>

                {/* Resto do conteúdo do dashboard */}
              </div>
            }
          />
        </Routes>
      </div>
    </div>
  );
}
