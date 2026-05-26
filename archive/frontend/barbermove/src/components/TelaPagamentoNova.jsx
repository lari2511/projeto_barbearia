import React from 'react';
import TelaPagamento from './TelaPagamento';

// Componente legado mantido para compatibilidade.
// O checkout oficial e unico agora vive em TelaPagamento.
export default function TelaPagamentoNova({ chamadoId, valor, onPago }) {
  return <TelaPagamento chamadoId={chamadoId} valor={valor} onPago={onPago} />;
}
