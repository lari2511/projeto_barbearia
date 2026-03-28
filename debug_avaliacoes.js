/**
 * Teste de Avaliação - Debug
 * Cole este código no console do navegador (F12) para testar
 */

(async () => {
  console.log('🧪 Testando envio de avaliação...');
  
  // Pegue um token válido do localStorage
  const token = localStorage.getItem('token');
  if (!token) {
    console.error('❌ Nenhum token encontrado');
    return;
  }
  
  // Dados de teste - AJUSTE ESTES VALORES
  const payload = {
    chamado_id: 1,  // ID do primeiro chamado
    avaliado_id: 1, // ID do cliente ou barbeiro
    nota: 5,
    comentario: 'Teste de avaliação'
  };
  
  try {
    const res = await fetch('http://localhost:8000/api/v1/avaliacoes/criar', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });
    
    const data = await res.json();
    
    console.log('📊 Resposta da API:');
    console.log('Status:', res.status);
    console.log('OK:', res.ok);
    console.log('Response:', data);
    
    if (!res.ok) {
      console.error('❌ Erro:', data.detail || JSON.stringify(data));
    } else {
      console.log('✅ Sucesso!');
    }
  } catch (err) {
    console.error('❌ Erro na requisição:', err);
  }
})();
