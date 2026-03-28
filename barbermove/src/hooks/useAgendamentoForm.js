/**
 * Hook customizado para criar agendamento com tratamento de erro amigável
 * Localização: barbermove/src/hooks/useAgendamentoForm.js
 * 
 * Exemplo:
 * const { criar, loading, erro } = useAgendamentoForm(token, apiUrl);
 * 
 * if (erro) {
 *   // Mostrar mensagem amigável ao usuário
 *   if (erro.horarioIndisponivel) {
 *     // Sugerir novos horários
 *   }
 * }
 */

import { useState } from 'react';

export const useAgendamentoForm = (token, apiUrl) => {
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);

  const criar = async (dadosAgendamento) => {
    setLoading(true);
    setErro(null);
    setSucesso(null);

    try {
      const response = await fetch(`${apiUrl}/chamados`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(dadosAgendamento),
      });

      const data = await response.json();

      if (!response.ok) {
        // ✅ TRATAMENTO DE ERRO AMIGÁVEL
        const novoErro = {
          status: response.status,
          mensagem: data.detail || 'Erro ao criar agendamento',
          horarioIndisponivel: false,
          tipo: null,
        };

        // Detectar erros específicos
        if (response.status === 400) {
          const mensagem = data.detail.toLowerCase();
          
          // Erro de horário indisponível
          if (mensagem.includes('horário') || mensagem.includes('reservado')) {
            novoErro.horarioIndisponivel = true;
            novoErro.tipo = 'horario_ocupado';
            novoErro.mensagem = data.detail; // Usar mensagem do servidor
          }
          
          // Erro de data obrigatória
          if (mensagem.includes('data') || mensagem.includes('hora')) {
            novoErro.tipo = 'data_obrigatoria';
            novoErro.mensagem = 'Por favor, selecione uma data e hora válidas';
          }
          
          // Erro de serviço não pertence à barbearia
          if (mensagem.includes('serviço') || mensagem.includes('barbearia')) {
            novoErro.tipo = 'servico_invalido';
            novoErro.mensagem = 'Serviço não disponível para essa barbearia';
          }
        }

        setErro(novoErro);
        return null;
      }

      // ✅ SUCESSO
      setSucesso({
        id: data.id,
        mensagem: 'Agendamento criado com sucesso!',
      });

      return data;
    } catch (error) {
      setErro({
        status: 500,
        mensagem: error.message || 'Erro de conexão com o servidor',
        tipo: 'conexao',
        horarioIndisponivel: false,
      });
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { criar, loading, erro, sucesso };
};

/**
 * ============================================================
 * EXEMPLO DE USO NO REACT
 * ============================================================
 */

export const ExemploAgendamentoForm = ({ token, apiUrl }) => {
  const { criar, loading, erro, sucesso } = useAgendamentoForm(token, apiUrl);
  const [formulario, setFormulario] = useState({
    servico_id: '',
    barbearia_id: '',
    data_hora_inicio: '',
    barbeiro_id: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validação básica no cliente
    if (!formulario.servico_id || !formulario.barbearia_id || !formulario.data_hora_inicio) {
      alert('Preencha todos os campos obrigatórios');
      return;
    }

    const resultado = await criar(formulario);
    if (resultado) {
      // Limpar formulário após sucesso
      setFormulario({
        servico_id: '',
        barbearia_id: '',
        data_hora_inicio: '',
        barbeiro_id: '',
      });
    }
  };

  return (
    <div className="max-w-md mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Agendar Serviço</h2>

      {/* ✅ TRATAMENTO DE ERRO AMIGÁVEL */}
      {erro && (
        <div className={`mb-4 p-4 rounded-lg ${
          erro.horarioIndisponivel 
            ? 'bg-yellow-100 border border-yellow-400 text-yellow-800' 
            : 'bg-red-100 border border-red-400 text-red-800'
        }`}>
          <h3 className="font-bold mb-2">
            {erro.horarioIndisponivel ? '⏳ Horário Indisponível' : '❌ Erro'}
          </h3>
          <p className="mb-3">{erro.mensagem}</p>
          
          {erro.horarioIndisponivel && (
            <div className="text-sm bg-white bg-opacity-50 p-2 rounded mt-2">
              <p className="font-semibold mb-1">💡 Dica:</p>
              <ul className="list-disc list-inside">
                <li>Experimente horários próximos (ex: 14:00, 15:30)</li>
                <li>Escolha outro dia da semana</li>
                <li>Veja a agenda disponível do barbeiro</li>
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ✅ MENSAGEM DE SUCESSO */}
      {sucesso && (
        <div className="mb-4 p-4 rounded-lg bg-green-100 border border-green-400 text-green-800">
          <h3 className="font-bold mb-2">✨ {sucesso.mensagem}</h3>
          <p className="text-sm">
            Seu agendamento #{sucesso.id} foi criado! 
            O barbeiro será notificado em breve.
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Barbearia */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Barbearia *
          </label>
          <select
            required
            value={formulario.barbearia_id}
            onChange={(e) => setFormulario({ ...formulario, barbearia_id: e.target.value })}
            className="w-full border rounded px-3 py-2"
          >
            <option value="">Selecione uma barbearia</option>
            <option value="1">Barbearia A</option>
            <option value="2">Barbearia B</option>
          </select>
        </div>

        {/* Serviço */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Serviço *
          </label>
          <select
            required
            value={formulario.servico_id}
            onChange={(e) => setFormulario({ ...formulario, servico_id: e.target.value })}
            className="w-full border rounded px-3 py-2"
          >
            <option value="">Selecione um serviço</option>
            <option value="1">Corte de Cabelo (R$ 50)</option>
            <option value="2">Barba (R$ 30)</option>
            <option value="3">Combo (R$ 70)</option>
          </select>
        </div>

        {/* Data e Hora */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Data e Hora *
          </label>
          <input
            type="datetime-local"
            required
            value={formulario.data_hora_inicio}
            onChange={(e) => setFormulario({ ...formulario, data_hora_inicio: e.target.value })}
            className="w-full border rounded px-3 py-2"
            min={new Date().toISOString().slice(0, 16)} // Não permitir datas passadas
          />
          <p className="text-xs text-gray-500 mt-1">
            Selecione um horário disponível
          </p>
        </div>

        {/* Barbeiro (opcional) */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Preferência de Barbeiro (opcional)
          </label>
          <select
            value={formulario.barbeiro_id}
            onChange={(e) => setFormulario({ ...formulario, barbeiro_id: e.target.value })}
            className="w-full border rounded px-3 py-2"
          >
            <option value="">Qualquer barbeiro disponível</option>
            <option value="1">João</option>
            <option value="2">Carlos</option>
            <option value="3">Pedro</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Deixe em branco se não tem preferência
          </p>
        </div>

        {/* Botão Submit */}
        <button
          type="submit"
          disabled={loading}
          className={`w-full py-2 rounded font-medium transition ${
            loading
              ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {loading ? '⏳ Agendando...' : '📅 Agendar'}
        </button>
      </form>

      {/* Loading indicator */}
      {loading && (
        <div className="mt-4 flex justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}
    </div>
  );
};

/**
 * ============================================================
 * COMPONENTE ALTERNATIVO: Mostrar horários disponíveis
 * ============================================================
 */

export const HorariosDisponiveis = ({ barbeiro_id, data, token, apiUrl }) => {
  const [horarios, setHorarios] = useState([]);
  const [loading, setLoading] = useState(false);

  // Buscar horários disponíveis para o barbeiro em um dia específico
  const buscarHorarios = async () => {
    if (!barbeiro_id || !data) return;

    setLoading(true);
    try {
      const response = await fetch(
        `${apiUrl}/barbeiro/${barbeiro_id}/horarios-disponiveis?data=${data}`,
        {
          headers: { 'Authorization': `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const dados = await response.json();
        setHorarios(dados.horarios || []);
      }
    } catch (_error) {
      // Erro ao buscar horários
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-4">
      <button
        onClick={buscarHorarios}
        disabled={loading || !barbeiro_id || !data}
        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
      >
        {loading ? '⏳ Buscando...' : '🔍 Ver Horários Disponíveis'}
      </button>

      {horarios.length > 0 && (
        <div className="mt-3 grid grid-cols-3 gap-2">
          {horarios.map((horario) => (
            <button
              key={horario}
              className="p-2 bg-green-100 text-green-800 rounded hover:bg-green-200 text-sm"
            >
              {horario}
            </button>
          ))}
        </div>
      )}

      {horarios.length === 0 && !loading && (
        <p className="text-gray-500 text-sm mt-2">
          Nenhum horário disponível para este dia
        </p>
      )}
    </div>
  );
};
