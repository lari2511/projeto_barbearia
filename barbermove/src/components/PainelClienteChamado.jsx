import React from 'react';
import MapaRastreamento from './MapaRastreamento';

/**
 * PainelClienteChamado: Visão do cliente
 * - Mostra "Aguardando aceite..." enquanto PENDENTE
 * - Mostra mapa e coordenadas quando CONFIRMADO+
 */
export default function PainelClienteChamado({ 
  chamadoId, 
  status, 
  mostrarMapa, 
  coordenadas 
}) {
  if (!mostrarMapa) {
    return (
      <div style={{
        padding: '30px 20px',
        textAlign: 'center',
        backgroundColor: '#f5f5f5',
        borderRadius: '8px',
        margin: '20px',
      }}>
        <div style={{ marginBottom: '20px' }}>
          <h3>⏳ Aguardando aceite do barbeiro</h3>
          <p style={{ color: '#666', fontSize: '14px' }}>
            Seu pedido foi recebido. Um barbeiro aceitará em breve.
          </p>
        </div>
        
        <div style={{ marginTop: '20px' }}>
          <div style={{
            display: 'inline-block',
            width: '40px',
            height: '40px',
            border: '3px solid #007bff',
            borderRadius: '50%',
            borderTop: '3px solid transparent',
            animation: 'spin 1s linear infinite',
          }} />
        </div>
        
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Mapa habilitado: barbeiro aceita o chamado
  return (
    <div style={{ padding: '20px' }}>
      <div style={{
        backgroundColor: '#d4edda',
        color: '#155724',
        padding: '12px',
        borderRadius: '4px',
        marginBottom: '20px',
      }}>
        ✓ Barbeiro aceitou seu chamado! Veja a localização em tempo real:
      </div>

      {mostrarMapa && coordenadas && (
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
