/**
 * EXEMPLOS DE USO DOS HOOKS DE AGENDAMENTOS
 * Copia e cola esses exemplos no seu React
 */

// ============================================================================
// EXEMPLO 1: Usar com Fetch API - Hook simples
// ============================================================================
import React from 'react';
import { useAgendamentosBarbeiro } from './hooks/useAgendamentos';

function ListaAgendamentosBarbeiro({ barbeiro_id, api_url }) {
  const { agendamentos, loading, error } = useAgendamentosBarbeiro(
    barbeiro_id,
    api_url
  );

  if (loading) return <p>Carregando agendamentos...</p>;
  if (error) return <p style={{ color: 'red' }}>Erro: {error}</p>;

  return (
    <div>
      <h2>Agendamentos do Barbeiro #{barbeiro_id}</h2>
      {agendamentos.length === 0 ? (
        <p>Nenhum agendamento encontrado</p>
      ) : (
        <ul>
          {agendamentos.map((ag) => (
            <li key={ag.id}>
              <strong>{ag.cliente_nome}</strong> - {ag.servico}
              <br />
              Status: {ag.status} | R$ {ag.valor}
              <br />
              Barbearia: {ag.barbearia_nome}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ============================================================================
// EXEMPLO 2: Usar com token do usuário autenticado
// ============================================================================
import { useMeusAgendamentos } from './hooks/useAgendamentos';

function MeusAgendamentos({ token, api_url }) {
  const { agendamentos, loading, error, refetch } = useMeusAgendamentos(
    token,
    api_url
  );

  return (
    <div>
      <h2>Meus Agendamentos</h2>
      <button onClick={refetch} disabled={loading}>
        {loading ? 'Atualizando...' : 'Atualizar'}
      </button>

      {error && <p style={{ color: 'red' }}>Erro: {error}</p>}

      <div>
        {agendamentos.length === 0 ? (
          <p>Você não tem agendamentos</p>
        ) : (
          agendamentos.map((ag) => (
            <div
              key={ag.id}
              style={{
                border: '1px solid #ccc',
                padding: '10px',
                margin: '10px 0',
              }}
            >
              <h3>{ag.cliente_nome}</h3>
              <p>Serviço: {ag.servico}</p>
              <p>Valor: R$ {ag.valor}</p>
              <p>Status: {ag.status}</p>
              <p>Data: {new Date(ag.data_agendamento).toLocaleString('pt-BR')}</p>
              <p>Barbearia: {ag.barbearia_nome}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ============================================================================
// EXEMPLO 3: Filtrar agendamentos (ACEITO, CONCLUÍDO, etc)
// ============================================================================
import { useFiltrarAgendamentos } from './hooks/useAgendamentos';

function FiltrarAgendamentosPorStatus({ barbeiro_id, api_url }) {
  const { agendamentos, loading, error, filtrar } = useFiltrarAgendamentos(
    barbeiro_id,
    api_url
  );

  const handleFiltrarAceitos = async () => {
    await filtrar({ status: 'ACEITO' });
  };

  const handleFiltrarConcluidos = async () => {
    await filtrar({ status: 'CONCLUÍDO' });
  };

  const handleFiltrarPorData = async () => {
    await filtrar({
      status: 'ACEITO',
      data_inicio: '2025-01-01',
      data_fim: '2025-01-31',
    });
  };

  return (
    <div>
      <h2>Filtrar Agendamentos</h2>
      <button onClick={handleFiltrarAceitos} disabled={loading}>
        Mostrar ACEITOS
      </button>
      <button onClick={handleFiltrarConcluidos} disabled={loading}>
        Mostrar CONCLUÍDOS
      </button>
      <button onClick={handleFiltrarPorData} disabled={loading}>
        Mostrar Jan/2025
      </button>

      {loading && <p>Filtrando...</p>}
      {error && <p style={{ color: 'red' }}>Erro: {error}</p>}

      <ul>
        {agendamentos.map((ag) => (
          <li key={ag.id}>
            {ag.cliente_nome} - {ag.status} (R$ {ag.valor})
          </li>
        ))}
      </ul>
    </div>
  );
}

// ============================================================================
// EXEMPLO 4: Usando Fetch API diretamente (sem hooks)
// ============================================================================
async function buscarAgendamentosBarbeiro(barbeiro_id, api_url) {
  try {
    const response = await fetch(
      `${api_url}/api/v1/barbeiro/${barbeiro_id}/agendamentos`
    );

    if (!response.ok) {
      throw new Error(`Erro: ${response.status}`);
    }

    const agendamentos = await response.json();
    console.log('Agendamentos:', agendamentos);
    return agendamentos;
  } catch (error) {
    console.error('Erro ao buscar agendamentos:', error);
    return [];
  }
}

// Usar em um useEffect:
// useEffect(() => {
//   buscarAgendamentosBarbeiro(123, 'http://localhost:8000');
// }, []);

// ============================================================================
// EXEMPLO 5: Com autenticação (token)
// ============================================================================
async function buscarMeusAgendamentos(token, api_url) {
  try {
    const response = await fetch(`${api_url}/api/v1/barbeiro/agendamentos/meus`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Erro: ${response.status}`);
    }

    const agendamentos = await response.json();
    return agendamentos;
  } catch (error) {
    console.error('Erro ao buscar meus agendamentos:', error);
    return [];
  }
}

// ============================================================================
// EXEMPLO 6: Filtrar com POST
// ============================================================================
async function filtrarAgendamentos(barbeiro_id, filtros, api_url) {
  try {
    const response = await fetch(
      `${api_url}/api/v1/barbeiro/${barbeiro_id}/agendamentos/filtrar`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          status: 'ACEITO',
          data_inicio: '2025-01-01',
          data_fim: '2025-01-31',
        }),
      }
    );

    if (!response.ok) {
      throw new Error(`Erro: ${response.status}`);
    }

    const agendamentos = await response.json();
    return agendamentos;
  } catch (error) {
    console.error('Erro ao filtrar agendamentos:', error);
    return [];
  }
}

// ============================================================================
// EXEMPLO 7: Componente Completo com Estado
// ============================================================================
import React, { useState, useEffect } from 'react';

function DashboardBarbeiro({ barbeiro_id, token, api_url }) {
  const [agendamentos, setAgendamentos] = useState([]);
  const [filtroStatus, setFiltroStatus] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function carregarAgendamentos() {
      setLoading(true);

      const filtros = {};
      if (filtroStatus) {
        filtros.status = filtroStatus;
      }

      try {
        const response = await fetch(
          `${api_url}/api/v1/barbeiro/${barbeiro_id}/agendamentos${
            Object.keys(filtros).length > 0 ? '/filtrar' : ''
          }`,
          {
            method: Object.keys(filtros).length > 0 ? 'POST' : 'GET',
            headers: {
              'Content-Type': 'application/json',
              ...(token && { Authorization: `Bearer ${token}` }),
            },
            ...(Object.keys(filtros).length > 0 && {
              body: JSON.stringify(filtros),
            }),
          }
        );

        if (!response.ok) throw new Error('Erro ao carregar');

        const data = await response.json();
        setAgendamentos(Array.isArray(data) ? data : []);
      } catch (error) {
        console.error('Erro:', error);
        setAgendamentos([]);
      } finally {
        setLoading(false);
      }
    }

    carregarAgendamentos();
  }, [barbeiro_id, filtroStatus, api_url, token]);

  return (
    <div style={{ padding: '20px' }}>
      <h1>Dashboard do Barbeiro</h1>

      <div style={{ marginBottom: '20px' }}>
        <label>
          Filtrar por status:
          <select
            value={filtroStatus}
            onChange={(e) => setFiltroStatus(e.target.value)}
          >
            <option value="">Todos</option>
            <option value="ABERTO">Aberto</option>
            <option value="ACEITO">Aceito</option>
            <option value="CONCLUÍDO">Concluído</option>
          </select>
        </label>
      </div>

      {loading ? (
        <p>Carregando...</p>
      ) : (
        <div>
          <h2>Total de agendamentos: {agendamentos.length}</h2>
          {agendamentos.map((ag) => (
            <div
              key={ag.id}
              style={{
                border: '1px solid #ddd',
                padding: '15px',
                margin: '10px 0',
                borderRadius: '8px',
              }}
            >
              <h3>{ag.cliente_nome}</h3>
              <p>
                <strong>Serviço:</strong> {ag.servico}
              </p>
              <p>
                <strong>Valor:</strong> R$ {ag.valor.toFixed(2)}
              </p>
              <p>
                <strong>Status:</strong> {ag.status}
              </p>
              <p>
                <strong>Telefone:</strong> {ag.cliente_telefone}
              </p>
              <p>
                <strong>Barbearia:</strong> {ag.barbearia_nome}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default DashboardBarbeiro;
