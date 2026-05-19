import React, { useState } from 'react';
import MapaRastreamento from './MapaRastreamento';

/**
 * PainelBarbeiroChamado: Visão do barbeiro
 * - Mostra botão "Aceitar Chamado" quando PENDENTE
 * - Mostra mapa após CONFIRMADO
 */
export default function PainelBarbeiroChamado({ 
  chamadoId, 
  status, 
  mostrarMapa, 
  coordenadas,
  onAceito 
}) {
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState(null);

  const handleAceitar = async () => {
    setLoading(true);
    setErro(null);

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Token não encontrado. Faça login novamente.');
      }

      const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const resp = await fetch(
        `${API_BASE}/api/v1/agendamento/${chamadoId}/aceitar`,
        {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.detail || 'Falha ao aceitar chamado');
      }

      console.log('✓ Chamado aceito com sucesso!');
      
      // Aguardar WebSocket notificar e atualizar status
      // Ou chamar callback para recarregar status
      if (onAceito) {
        setTimeout(() => onAceito(), 500);
      }
    } catch (err) {
      console.error('❌ Erro ao aceitar:', err);
      setErro(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Se ainda PENDENTE: mostrar botão de aceite
  if (status === 'pendente') {
    return (
      <div style={{
        padding: '30px 20px',
        backgroundColor: '#fff3cd',
        borderRadius: '8px',
        margin: '20px',
        border: '1px solid #ffc107',
      }}>
        <h3>📱 Novo Chamado Recebido</h3>
        <p style={{ marginBottom: '20px' }}>
          Um cliente está esperando por você. Aceitar para iniciar o rastreamento.
        </p>

        {erro && (
          <div style={{
            backgroundColor: '#f8d7da',
            color: '#721c24',
            padding: '10px',
            borderRadius: '4px',
            marginBottom: '20px',
          }}>
            ❌ {erro}
          </div>
        )}

        <button
          onClick={handleAceitar}
          disabled={loading}
          style={{
            backgroundColor: '#28a745',
            color: 'white',
            padding: '12px 30px',
            border: 'none',
            borderRadius: '4px',
            fontSize: '16px',
            fontWeight: 'bold',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
            transition: 'opacity 0.3s',
          }}
        >
          {loading ? '⏳ Aceeitando...' : '✓ Aceitar Chamado'}
        </button>
      </div>
    );
  }

  // Se CONFIRMADO+: mostrar mapa e coordenadas
  if (mostrarMapa) {
    return (
      <div style={{ padding: '20px' }}>
        <div style={{
          backgroundColor: '#d4edda',
          color: '#155724',
          padding: '12px',
          borderRadius: '4px',
          marginBottom: '20px',
        }}>
          ✓ Chamado aceito! Veja a localização do cliente em tempo real:
        </div>

        {coordenadas && (
          <MapaRastreamento
            clienteLat={coordenadas.cliente_lat}
            clienteLon={coordenadas.cliente_lon}
            barbeirLat={coordenadas.barbeiro_lat}
            barbeirLon={coordenadas.barbeiro_lon}
            chamadoId={chamadoId}
          />
        )}
      </div>
    );
  }

  return <div>Status desconhecido: {status}</div>;
}
