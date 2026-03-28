/**
 * Componente: SeletorServicoBarbearia
 * Localização: barbermove/src/components/SeletorServicoBarbearia.jsx
 * 
 * Fluxo:
 * 1. Cliente clica em "Barbearia João"
 * 2. App mostra os SERVIÇOS ÚNICOS do João
 * 3. Cliente vê: "Corte R$ 40", "Barba R$ 25"
 * 4. Cliente seleciona um serviço
 * 5. A duração automática já aparece (salva no banco)
 * 6. Cliente segue para selecionar a data/hora
 */

import { useState, useEffect } from 'react';

export const SeletorServicoBarbearia = ({ 
  barbearia_id, 
  barbearia_nome,
  token, 
  apiUrl,
  onServicoSelecionado  // Callback quando usuário seleciona um serviço
}) => {
  const [servicos, setServicos] = useState([]);
  const [servicoSelecionado, setServicoSelecionado] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  // Carregar serviços da barbearia
  useEffect(() => {
    const carregarServicos = async () => {
      setLoading(true);
      setErro(null);

      try {
        const response = await fetch(
          `${apiUrl}/barbearias/${barbearia_id}/servicos`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        );

        if (!response.ok) {
          throw new Error('Erro ao carregar serviços');
        }

        const data = await response.json();
        setServicos(data.servicos);

        if (data.servicos.length === 0) {
          setErro('Esta barbearia ainda não tem serviços cadastrados');
        }
      } catch (error) {
        setErro(error.message);
      } finally {
        setLoading(false);
      }
    };

    if (barbearia_id) {
      carregarServicos();
    }
  }, [barbearia_id, token, apiUrl]);

  // Usuário seleciona um serviço
  const handleSelecionarServico = (servico) => {
    setServicoSelecionado(servico);
    
    // Chamar callback para o componente pai
    if (onServicoSelecionado) {
      onServicoSelecionado({
        servico_id: servico.id,
        servico_nome: servico.nome,
        servico_valor: servico.valor,
        duracao_minutos: servico.duracao_minutos
      });
    }
  };

  if (loading) {
    return (
      <div className="p-4 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Carregando serviços...</p>
      </div>
    );
  }

  if (erro) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded text-red-700">
        <p className="font-bold">❌ Erro</p>
        <p className="text-sm">{erro}</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      {/* Cabeçalho */}
      <div className="mb-4">
        <h2 className="text-2xl font-bold">💈 {barbearia_nome}</h2>
        <p className="text-gray-600 text-sm">
          Selecione um serviço para agendar
        </p>
      </div>

      {/* Grid de serviços */}
      <div className="grid gap-3">
        {servicos.map(servico => (
          <div
            key={servico.id}
            onClick={() => handleSelecionarServico(servico)}
            className={`p-4 rounded-lg border-2 cursor-pointer transition ${
              servicoSelecionado?.id === servico.id
                ? 'border-blue-600 bg-blue-50'
                : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50'
            }`}
          >
            <div className="flex justify-between items-start">
              {/* Informações do serviço */}
              <div className="flex-1">
                <h3 className="font-bold text-lg">{servico.nome}</h3>
                
                {servico.descricao && (
                  <p className="text-sm text-gray-600 mt-1">{servico.descricao}</p>
                )}
                
                {/* Duração */}
                <div className="flex items-center gap-2 mt-2 text-sm text-gray-500">
                  <span>⏱</span>
                  <span>
                    {servico.duracao_minutos < 60
                      ? `${servico.duracao_minutos} min`
                      : `${Math.floor(servico.duracao_minutos / 60)}h ${servico.duracao_minutos % 60}min`}
                  </span>
                </div>
              </div>

              {/* Preço (Grande e destaque) */}
              <div className="text-right ml-4">
                <p className="text-3xl font-bold text-green-600">
                  R$ {servico.valor.toFixed(2)}
                </p>
              </div>
            </div>

            {/* Indicador de seleção */}
            {servicoSelecionado?.id === servico.id && (
              <div className="mt-3 flex items-center text-blue-600 font-bold">
                <span className="mr-2">✓</span>
                <span>Selecionado</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Info útil */}
      {servicoSelecionado && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
          <p className="font-bold">✅ Serviço selecionado!</p>
          <p className="mt-1">
            Duração: {servicoSelecionado.duracao_minutos} minutos
          </p>
        </div>
      )}
    </div>
  );
};

export default SeletorServicoBarbearia;

/**
 * ============================================================
 * EXEMPLO DE USO:
 * ============================================================
 * 
 * import { SeletorServicoBarbearia } from '@/components/SeletorServicoBarbearia';
 * 
 * export function TelaAgendamento() {
 *   const [servicoInfo, setServicoInfo] = useState(null);
 * 
 *   return (
 *     <div>
 *       <SeletorServicoBarbearia
 *         barbearia_id={1}
 *         barbearia_nome="Barbearia João"
 *         token={token}
 *         apiUrl={apiUrl}
 *         onServicoSelecionado={(info) => {
 *           console.log('Serviço selecionado:', info);
 *           // {
 *           //   servico_id: 5,
 *           //   servico_nome: "Corte Masculino",
 *           //   servico_valor: 40.00,
 *           //   duracao_minutos: 30
 *           // }
 *           setServicoInfo(info);
 *         }}
 *       />
 * 
 *       {servicoInfo && (
 *         <div className="mt-4">
 *           <p>Próximo: Selecione data e hora</p>
 *           <button onClick={avancarParaProximoEtapa}>
 *             Continuar →
 *           </button>
 *         </div>
 *       )}
 *     </div>
 *   );
 * }
 */
