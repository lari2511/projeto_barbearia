/**
 * Componente: CadastroServicosOnboarding
 * Localização: barbermove/src/components/CadastroServicosOnboarding.jsx
 * 
 * Fluxo:
 * 1. Dono abre o app
 * 2. Vê a tela: "Vamos configurar sua loja! Quais serviços você oferece?"
 * 3. Clica em "Adicionar Serviço"
 * 4. Vê sugestões (Corte, Barba, Combo, etc)
 * 5. Clica em uma sugestão
 * 6. App preenche os campos (nome, duração, preço padrão)
 * 7. Dono edita o preço se quiser (ex: quer cobrar R$ 40 em vez de R$ 30)
 * 8. Clica em "Salvar Serviço"
 * 9. Serviço fica salvo com os valores personalizados dele
 */

import { useState, useEffect, useCallback } from 'react';
import SeletorCategoria from './SeletorCategoria';

export const CadastroServicosOnboarding = ({ barbearia_id, token, apiUrl }) => {
  const [servicos, setServicos] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [mostraFormulario, setMostraFormulario] = useState(false);
  const [servicoSelecionado, setServicoSelecionado] = useState(null);
  const [formulario, setFormulario] = useState({
    nome: '',
    categoria: '',
    descricao: '',
    valor: '',
    duracao_minutos: 30
  });
  const [loading, setLoading] = useState(false);

  // Carregar templates
  useEffect(() => {
    fetch(`${apiUrl}/templates/servicos`)
      .then(r => r.json())
      .then(data => setTemplates(data.templates))
      .catch(_err => {
        // Erro ao carregar serviços
      });
  }, [apiUrl]);

  // Carregar serviços existentes
  const carregarServicos = useCallback(async () => {
    try {
      const response = await fetch(
        `${apiUrl}/barbearias/${barbearia_id}/servicos`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      const data = await response.json();
      setServicos(data.servicos);
    } catch (_error) {
      // Erro ao carregar serviços
    }
  }, [apiUrl, barbearia_id, token]);

  useEffect(() => {
    carregarServicos();
  }, [carregarServicos]);

  // ✅ Usuário clica em um template
  const handleSelecionarTemplate = (template) => {
    // Pre-preencher formulário com valores do template
    setServicoSelecionado(template);
    setFormulario({
      nome: template.nome,
      categoria: template.categoria,  // ✅ HÍBRIDO: categoria vem do template
      descricao: template.descricao,
      valor: template.valor_padrao.toString(),
      duracao_minutos: template.duracao_minutos_padrao
    });
    setMostraFormulario(true);
  };

  // ✅ Usuário edita o valor antes de salvar
  const handleMudarValor = (novoValor) => {
    setFormulario({
      ...formulario,
      valor: novoValor
    });
  };

  // ✅ Salvar novo serviço
  const handleSalvarServico = async () => {
    if (!formulario.nome || !formulario.valor || !formulario.categoria) {
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${apiUrl}/barbearias/${barbearia_id}/servicos`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            nome: formulario.nome,
            categoria: formulario.categoria,  // ✅ Envia categoria
            descricao: formulario.descricao,
            valor: parseFloat(formulario.valor),
            duracao_minutos: parseInt(formulario.duracao_minutos)
          })
        }
      );

      if (response.ok) {
        const data = await response.json();
        
        // Limpar formulário e recarregar serviços
        setMostraFormulario(false);
        setServicoSelecionado(null);
        carregarServicos();
      } else {
        const erro = await response.json();
      }
    } catch (error) {
      // Erro ao salvar serviço
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      {/* Cabeçalho */}
      <div className="mb-6">
        <h1 className="h1-lg mb-2">🏪 Vamos Configurar Sua Loja!</h1>
        <p className="muted">
          Quais serviços você oferece? Você pode editar tudo depois.
        </p>
      </div>

      {/* Lista de serviços já criados */}
      {servicos.length > 0 && (
        <div className="bm-card mb-6">
          <h3 className="font-bold text-white mb-3">✅ Seus Serviços</h3>
          <div className="space-y-2">
            {servicos.map(s => (
              <div key={s.id} className="flex justify-between items-center bg-zinc-900 p-3 rounded border border-zinc-800">
                <div>
                  <p className="font-semibold text-white">{s.nome}</p>
                  <p className="text-sm text-zinc-400">{s.duracao_minutos} min</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-green-400">R$ {s.valor.toFixed(2)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Botão para adicionar mais */}
      {!mostraFormulario && (
        <button
          onClick={() => setMostraFormulario(true)}
          className="w-full bm-cta-orange mb-4 text-center"
        >
          ➕ Adicionar Serviço
        </button>
      )}

      {/* Formulário aberto */}
      {mostraFormulario && !servicoSelecionado && (
        <div className="border-2 border-blue-300 rounded-lg p-6 mb-4 bg-blue-50">
          <h2 className="text-2xl font-bold mb-4">Escolha um Template</h2>
          <p className="text-gray-600 mb-4">
            Clique em um dos serviços abaixo. O app vai preencher os campos com valores sugeridos.
            Você pode editar tudo antes de salvar! 💡
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {templates.map((template, idx) => (
              <button
                key={idx}
                onClick={() => handleSelecionarTemplate(template)}
                className="text-left p-4 border-2 border-blue-200 rounded-lg hover:border-blue-600 hover:bg-blue-100 transition"
              >
                <h4 className="font-bold text-blue-900">{template.nome}</h4>
                <p className="text-sm text-gray-600 mt-1">{template.descricao}</p>
                <div className="flex justify-between items-center mt-3">
                  <span className="text-sm text-gray-500">⏱ {template.duracao_minutos_padrao} min</span>
                  <span className="text-lg font-bold text-blue-600">
                    R$ {template.valor_padrao.toFixed(2)}
                  </span>
                </div>
              </button>
            ))}
          </div>

          <button
            onClick={() => setMostraFormulario(false)}
            className="w-full mt-4 bg-gray-300 text-gray-800 py-2 rounded hover:bg-gray-400"
          >
            Cancelar
          </button>
        </div>
      )}

      {/* Formulário com template pré-preenchido */}
      {mostraFormulario && servicoSelecionado && (
        <div className="border-2 border-green-300 rounded-lg p-6 bg-green-50">
          <h2 className="text-2xl font-bold mb-4">
            ✏️ Personalize seu serviço: {servicoSelecionado.nome}
          </h2>

          {/* Nome */}
          <div className="mb-4">
            <label className="block text-sm font-bold mb-2">Nome do Serviço</label>
            <input
              type="text"
              value={formulario.nome}
              onChange={(e) => setFormulario({ ...formulario, nome: e.target.value })}
              className="w-full border-2 border-gray-300 rounded px-3 py-2 font-semibold"
            />
          </div>

          {/* Descrição */}
          <div className="mb-4">
            <label className="block text-sm font-bold mb-2">Descrição (Opcional)</label>
            <textarea
              value={formulario.descricao}
              onChange={(e) => setFormulario({ ...formulario, descricao: e.target.value })}
              className="w-full border-2 border-gray-300 rounded px-3 py-2"
              rows="2"
              placeholder="Ex: Inclui corte na máquina e tesoura"
            />
          </div>

          {/* Preço (O IMPORTANTE!) */}
          <div className="mb-4 p-4 bg-yellow-100 border-2 border-yellow-400 rounded">
            <label className="block text-sm font-bold mb-2">💰 Preço</label>
            <div className="flex items-center">
              <span className="text-2xl mr-2">R$</span>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formulario.valor}
                onChange={(e) => handleMudarValor(e.target.value)}
                className="flex-1 border-2 border-yellow-400 rounded px-3 py-2 text-2xl font-bold"
              />
            </div>
            <p className="text-xs text-gray-600 mt-2">
              📌 Sugestão: R$ {servicoSelecionado.valor_padrao.toFixed(2)} (mas você pode mudar!)
            </p>
          </div>

          {/* Duração */}
          <div className="mb-6">
            <label className="block text-sm font-bold mb-2">⏱ Duração (minutos)</label>
            <div className="flex gap-2 flex-wrap">
              {[15, 20, 30, 40, 50, 60].map(min => (
                <button
                  key={min}
                  onClick={() => setFormulario({ ...formulario, duracao_minutos: min })}
                  className={`px-4 py-2 rounded font-semibold transition ${
                    formulario.duracao_minutos === min
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-200 hover:bg-gray-300'
                  }`}
                >
                  {min} min
                </button>
              ))}
            </div>
          </div>

          {/* Botões */}
          <div className="flex gap-3">
            <button
              onClick={handleSalvarServico}
              disabled={loading}
              className={`flex-1 py-3 rounded-lg font-bold text-white text-lg transition ${
                loading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-700'
              }`}
            >
              {loading ? '⏳ Salvando...' : '✅ Salvar Serviço'}
            </button>
            <button
              onClick={() => {
                setMostraFormulario(false);
                setServicoSelecionado(null);
              }}
              disabled={loading}
              className="flex-1 py-3 rounded-lg font-bold bg-gray-300 hover:bg-gray-400"
            >
              Voltar
            </button>
          </div>
        </div>
      )}

      {/* Info e próximos passos */}
      {!mostraFormulario && servicos.length > 0 && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-bold text-blue-900 mb-2">✨ Você está pronto!</h3>
          <p className="text-sm text-gray-700">
            Seus serviços foram salvos. Quando clientes buscarem por você, verão esses serviços com esses preços.
          </p>
          <p className="text-sm text-gray-700 mt-2">
            💡 Dica: Você pode editar ou adicionar mais serviços a qualquer momento!
          </p>
        </div>
      )}
    </div>
  );
};

export default CadastroServicosOnboarding;
