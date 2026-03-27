import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { User, Lock, Mail, Phone, MapPin, Camera, Save, X, Eye, EyeOff, LogOut, ToggleRight, MessageCircle, Wallet } from 'lucide-react';
import { TabPortfolioBarbeiro, TabAvaliacoesBarbeiro } from './TabsPortfolioAvaliacoes';

const DEFAULT_HOST = typeof window !== "undefined" ? window.location.hostname : "localhost";
const API_URL = import.meta.env.VITE_API_URL || `http://${DEFAULT_HOST}:8000`;

export default function TelaPerfilUsuario({ userType, token, onLogout, onNotify }) {
  const AVALIACOES_PAGINA = 10;
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [imageModal, setImageModal] = useState(null);
  const [disponivel, setDisponivel] = useState(true);
  const [activeTab, setActiveTab] = useState('dados');
  const [presenteEmLocal, setPresenteEmLocal] = useState(false);
  const [barbeariaAtualId, setBarbeariaAtualId] = useState(null);
  
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    telefone: '',
    endereco: '',
    cpf: '',
    cnpj: ''
  });

  const [passwordData, setPasswordData] = useState({
    senhaAtual: '',
    novaSenha: '',
    confirmarSenha: ''
  });

  const [previewImage, setPreviewImage] = useState(null);
  const [fotoPessoal, setFotoPessoal] = useState(null);
  const [portfolioImages, setPortfolioImages] = useState([]);
  const [portfolioServerItems, setPortfolioServerItems] = useState([]);
  const [_avaliacoes, _setAvaliacoes] = useState([]);
  const [_avaliacaoMedia, _setAvaliacaoMedia] = useState(null);
  const [_avaliacoesLoading, _setAvaliacoesLoading] = useState(false);
  const [avaliacoesOffset, setAvaliacoesOffset] = useState(0);
  const [hasMoreAvaliacoes, setHasMoreAvaliacoes] = useState(false);
  const [carregandoMaisAvaliacoes, setCarregandoMaisAvaliacoes] = useState(false);
  const [barbeariaPerfilId, setBarbeariaPerfilId] = useState(null);
  const [agendamentosBarbearia, setAgendamentosBarbearia] = useState([]);
  const [barbeirosPresentesBarbearia, setBarbeirosPresentesBarbearia] = useState([]);
  const [contaPagamento, setContaPagamento] = useState({
    chave_pix: '',
    banco: '',
    agencia: '',
    conta: '',
    tipo_conta: 'corrente',
    titular_nome: '',
    titular_documento: '',
    frequencia_repasse: 'semanal',
    dia_semana_repasse: 1,
    dia_mes_repasse: 5
  });
  const [splitPagamento, setSplitPagamento] = useState(null);
  const [salvandoContaPagamento, setSalvandoContaPagamento] = useState(false);
  const [resumoPagamento, setResumoPagamento] = useState(null);
  const [assinaturaStatus, setAssinaturaStatus] = useState(null);
  const [assinaturaAtual, setAssinaturaAtual] = useState(null);
  const [cadeirasDesejadas, setCadeirasDesejadas] = useState(1);
  const [assinaturaCalculo, setAssinaturaCalculo] = useState(null);
  const [assinaturaLoading, setAssinaturaLoading] = useState(false);
  const [pagamentoAssinaturaLoading, setPagamentoAssinaturaLoading] = useState(false);
  const [pixMensalidade, setPixMensalidade] = useState(null);
  const [cartaoMensalidade, setCartaoMensalidade] = useState({
    numero_cartao: '',
    titular: '',
    validade: '',
    cvv: ''
  });

  const barbeirosVinculadosBarbearia = useMemo(() => {
    if (userType !== 'barbearia') return [];

    const mapa = new Map();

    for (const ag of agendamentosBarbearia) {
      if (!ag?.barbeiro_id) continue;
      if (!mapa.has(ag.barbeiro_id)) {
        mapa.set(ag.barbeiro_id, {
          id: ag.barbeiro_id,
          nome: ag.nome_barbeiro || `Barbeiro #${ag.barbeiro_id}`,
          totalAgendamentos: 1,
          presenteNoLocal: false,
        });
      } else {
        mapa.get(ag.barbeiro_id).totalAgendamentos += 1;
      }
    }

    for (const barbeiro of barbeirosPresentesBarbearia) {
      if (!barbeiro?.id) continue;
      if (!mapa.has(barbeiro.id)) {
        mapa.set(barbeiro.id, {
          id: barbeiro.id,
          nome: barbeiro.nome || `Barbeiro #${barbeiro.id}`,
          totalAgendamentos: 0,
          presenteNoLocal: true,
        });
      } else {
        mapa.get(barbeiro.id).presenteNoLocal = true;
      }
    }

    return Array.from(mapa.values()).sort((a, b) => b.totalAgendamentos - a.totalAgendamentos);
  }, [userType, agendamentosBarbearia, barbeirosPresentesBarbearia]);

  const fetchUserProfile = useCallback(async (options = {}) => {
    const { silent = false } = options;

    try {
      const res = await fetch(`${API_URL}/api/v1/usuarios/perfil-completo`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error('Erro ao carregar perfil');
      
      const data = await res.json();
      setUser(data);

      // Evita sobrescrever campos enquanto o usuario edita o perfil.
      if (!editing) {
        setFormData({
          nome: data.nome || '',
          email: data.email || '',
          telefone: data.telefone || '',
          endereco: data.endereco || '',
          cpf: data.cpf || '',
          cnpj: data.cnpj || ''
        });
        setPreviewImage(data.foto_perfil || null);
        setFotoPessoal(data.foto_pessoal || null);
        setPortfolioImages(data.portfolio_fotos || []);
        // Evita reuso de IDs antigos caso a leitura detalhada de portfolio falhe.
        setPortfolioServerItems([]);
      }

      setDisponivel(data.disponivel !== false);
      setPresenteEmLocal(data.presente_em_local || false);
      setBarbeariaAtualId(data.barbearia_atual_id || null);

      if (userType === 'barbeiro') {
        const portfolioRes = await fetch(`${API_URL}/api/v1/barbeiro/portfolio`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (portfolioRes.ok) {
          const portfolioData = await portfolioRes.json();
          const itens = Array.isArray(portfolioData)
            ? portfolioData.filter((item) => item?.id && item?.url)
            : [];
          const urls = itens.map((item) => item.url);

          if (!editing) {
            setPortfolioServerItems(itens);
            setPortfolioImages(urls);
          }
        }
      }
    } catch (_error) {
      if (!silent) {
        onNotify('Erro ao carregar perfil', 'error');
      }
    } finally {
      setLoading(false);
    }
  }, [token, userType, onNotify, editing]);

  const fetchPagamentoConfig = useCallback(async () => {
    try {
      const [contaRes, splitRes, resumoRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/pagamentos-config/conta`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/v1/pagamentos-config/split`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/v1/pagamentos-config/resumo`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);

      if (contaRes.ok) {
        const contaData = await contaRes.json();
        setContaPagamento({
          chave_pix: contaData.chave_pix || '',
          banco: contaData.banco || '',
          agencia: contaData.agencia || '',
          conta: contaData.conta || '',
          tipo_conta: contaData.tipo_conta || 'corrente',
          titular_nome: contaData.titular_nome || '',
          titular_documento: contaData.titular_documento || '',
          frequencia_repasse: contaData.frequencia_repasse || 'semanal',
          dia_semana_repasse: contaData.dia_semana_repasse ?? 1,
          dia_mes_repasse: contaData.dia_mes_repasse ?? 5
        });
      }

      if (splitRes.ok) {
        const splitData = await splitRes.json();
        setSplitPagamento(splitData);
      }

      if (resumoRes.ok) {
        const resumoData = await resumoRes.json();
        setResumoPagamento(resumoData);
      }
    } catch (_error) {
      // Erro silencioso para nao quebrar o perfil.
    }
  }, [token]);

  const carregarAssinaturaBarbearia = useCallback(async () => {
    if (userType !== 'barbearia') return;

    setAssinaturaLoading(true);
    try {
      const [statusRes, assinaturaRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/assinaturas/status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/v1/assinaturas/minha`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);

      if (statusRes.ok) {
        setAssinaturaStatus(await statusRes.json());
      } else {
        setAssinaturaStatus(null);
      }

      if (assinaturaRes.ok) {
        const assinaturaData = await assinaturaRes.json();
        setAssinaturaAtual(assinaturaData);
        setCadeirasDesejadas(Number(assinaturaData?.cadeiras_ativas || 1));
      } else {
        setAssinaturaAtual(null);
      }
    } catch (_error) {
      setAssinaturaStatus(null);
      setAssinaturaAtual(null);
    } finally {
      setAssinaturaLoading(false);
    }
  }, [token, userType]);

  const simularAssinatura = useCallback(async (quantidade) => {
    if (userType !== 'barbearia') return;

    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/calcular?cadeiras=${quantidade}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!res.ok) {
        setAssinaturaCalculo(null);
        return;
      }

      setAssinaturaCalculo(await res.json());
    } catch (_error) {
      setAssinaturaCalculo(null);
    }
  }, [token, userType]);

  useEffect(() => {
    fetchUserProfile();
    if (userType === 'barbeiro' || userType === 'barbearia') {
      fetchPagamentoConfig();
    }
  }, [fetchPagamentoConfig, fetchUserProfile, userType]);

  useEffect(() => {
    if (userType !== 'barbearia') return;
    carregarAssinaturaBarbearia();
  }, [userType, carregarAssinaturaBarbearia]);

  useEffect(() => {
    if (userType !== 'barbearia') return;
    const quantidade = Number(cadeirasDesejadas || 1);
    if (quantidade < 1 || quantidade > 20) return;
    simularAssinatura(quantidade);
  }, [userType, cadeirasDesejadas, simularAssinatura]);

  useEffect(() => {
    if (userType !== 'barbeiro' || !token) return;

    const interval = setInterval(() => {
      fetchUserProfile({ silent: true });
    }, 15000);

    return () => clearInterval(interval);
  }, [fetchUserProfile, token, userType]);

  useEffect(() => {
    if (userType !== 'barbearia' || !token) return;

    const carregarBarbeirosDaBarbearia = async () => {
      try {
        const barbeariaRes = await fetch(`${API_URL}/api/v1/barbearia/minha`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!barbeariaRes.ok) return;
        const barbeariaData = await barbeariaRes.json();
        if (!barbeariaData?.id) return;

        setBarbeariaPerfilId(barbeariaData.id);

        const [agRes, presentesRes] = await Promise.all([
          fetch(`${API_URL}/api/v1/barbearia/${barbeariaData.id}/agendamentos`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch(`${API_URL}/api/v1/barbearia/${barbeariaData.id}/barbeiros-presentes`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ]);

        if (agRes.ok) {
          const agData = await agRes.json();
          setAgendamentosBarbearia(Array.isArray(agData) ? agData : []);
        } else {
          setAgendamentosBarbearia([]);
        }

        if (presentesRes.ok) {
          const presentesData = await presentesRes.json();
          setBarbeirosPresentesBarbearia(Array.isArray(presentesData) ? presentesData : []);
        } else {
          setBarbeirosPresentesBarbearia([]);
        }
      } catch (_error) {
        setAgendamentosBarbearia([]);
        setBarbeirosPresentesBarbearia([]);
      }
    };

    carregarBarbeirosDaBarbearia();
    const interval = setInterval(carregarBarbeirosDaBarbearia, 30000);
    return () => clearInterval(interval);
  }, [userType, token]);

  const fetchAvaliacoesBarbeiro = useCallback(async (offset = 0, append = false) => {
    if (userType !== 'barbeiro' || !token) return;

    if (append) {
      setCarregandoMaisAvaliacoes(true);
    } else {
      _setAvaliacoesLoading(true);
    }

    try {
      let lote = [];
      let proximoHasMore = false;
      let totalFallback = null;
      let mediaFallback = null;

      const analyticsRes = await fetch(`${API_URL}/api/v1/analytics/barbeiro/minhas-avaliacoes?limite=${AVALIACOES_PAGINA}&offset=${offset}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (analyticsRes.ok) {
        const analyticsData = await analyticsRes.json();
        lote = Array.isArray(analyticsData) ? analyticsData : [];
        proximoHasMore = lote.length === AVALIACOES_PAGINA;
      } else {
        const fallbackRes = await fetch(`${API_URL}/api/v1/avaliacoes/minhas-avaliacoes-recebidas`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!fallbackRes.ok) throw new Error('Erro ao carregar avaliacoes');

        const fallbackData = await fallbackRes.json();
        const todas = Array.isArray(fallbackData?.como_freelancer) ? fallbackData.como_freelancer : [];
        totalFallback = todas.length;
        mediaFallback = Number(fallbackData?.media_freelancer ?? 0);
        lote = todas.slice(offset, offset + AVALIACOES_PAGINA);
        proximoHasMore = (offset + lote.length) < todas.length;
      }

      if (append) {
        _setAvaliacoes((prev) => {
          const mapa = new Map();
          const chaveAvaliacao = (item) => (
            item?.id ?? `${item?.criado_em || ''}-${item?.nota || ''}-${item?.comentario || ''}`
          );

          for (const item of prev) {
            mapa.set(chaveAvaliacao(item), item);
          }
          for (const item of lote) {
            mapa.set(chaveAvaliacao(item), item);
          }

          return Array.from(mapa.values()).sort((a, b) => {
            const dataA = new Date(a?.criado_em || 0).getTime();
            const dataB = new Date(b?.criado_em || 0).getTime();
            return dataB - dataA;
          });
        });
      } else {
        _setAvaliacoes(lote);
      }

      setAvaliacoesOffset(offset + lote.length);
      setHasMoreAvaliacoes(proximoHasMore);

      if (!append) {
        let mediaPayload = null;

        if (mediaFallback !== null && Number.isFinite(mediaFallback)) {
          mediaPayload = {
            media: mediaFallback.toFixed(1),
            total_avaliacoes: totalFallback ?? lote.length,
          };
        } else {
          const statsRes = await fetch(`${API_URL}/api/v1/analytics/barbeiro/estatisticas`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });

          if (statsRes.ok) {
            const stats = await statsRes.json();
            mediaPayload = {
              media: Number(stats?.media_notas || 0).toFixed(1),
              total_avaliacoes: Number(stats?.total_avaliacoes || 0),
            };
          }
        }

        if (!mediaPayload) {
          const somaNotas = lote.reduce((acc, av) => acc + Number(av?.nota || 0), 0);
          const media = lote.length > 0 ? (somaNotas / lote.length) : 0;
          mediaPayload = {
            media: media.toFixed(1),
            total_avaliacoes: lote.length,
          };
        }

        _setAvaliacaoMedia(mediaPayload);
      }
    } catch (_error) {
      if (!append) {
        _setAvaliacoes([]);
        _setAvaliacaoMedia(null);
        setAvaliacoesOffset(0);
        setHasMoreAvaliacoes(false);
      }
    } finally {
      if (append) {
        setCarregandoMaisAvaliacoes(false);
      } else {
        _setAvaliacoesLoading(false);
      }
    }
  }, [token, userType, AVALIACOES_PAGINA]);

  useEffect(() => {
    if (userType === 'barbeiro' && activeTab === 'avaliacoes') {
      fetchAvaliacoesBarbeiro(0, false);
    }
  }, [activeTab, userType, fetchAvaliacoesBarbeiro]);

  const handleCarregarMaisAvaliacoes = useCallback(() => {
    if (!hasMoreAvaliacoes || _avaliacoesLoading || carregandoMaisAvaliacoes) return;
    fetchAvaliacoesBarbeiro(avaliacoesOffset, true);
  }, [hasMoreAvaliacoes, _avaliacoesLoading, carregandoMaisAvaliacoes, fetchAvaliacoesBarbeiro, avaliacoesOffset]);

  const formatarDinheiro = (valor) => {
    const numero = Number(valor || 0);
    return numero.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    });
  };

  const formatarDataHora = (valor) => {
    if (!valor) return '-';
    const data = new Date(valor);
    if (Number.isNaN(data.getTime())) return '-';
    return data.toLocaleString('pt-BR');
  };

  const salvarContaPagamento = async () => {
    setSalvandoContaPagamento(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/pagamentos-config/conta`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(contaPagamento)
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Erro ao salvar conta de pagamento');
      }

      onNotify('Conta de pagamento salva com sucesso!', 'success');
      fetchPagamentoConfig();
    } catch (error) {
      onNotify(error.message || 'Erro ao salvar conta de pagamento', 'error');
    } finally {
      setSalvandoContaPagamento(false);
    }
  };

  const contratarOuAtualizarAssinatura = async () => {
    const quantidade = Number(cadeirasDesejadas || 1);
    if (quantidade < 1 || quantidade > 20) {
      onNotify('Quantidade de cadeiras deve ficar entre 1 e 20', 'error');
      return;
    }

    setPagamentoAssinaturaLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/criar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          cadeiras_ativas: quantidade,
          metodo_pagamento: 'pix'
        })
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || 'Erro ao salvar plano');
      }

      setAssinaturaAtual(data);
      onNotify('Plano salvo com sucesso!', 'success');
      await carregarAssinaturaBarbearia();
      await simularAssinatura(quantidade);
    } catch (error) {
      onNotify(error.message || 'Erro ao salvar plano', 'error');
    } finally {
      setPagamentoAssinaturaLoading(false);
    }
  };

  const gerarPixMensalidade = async () => {
    setPagamentoAssinaturaLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade/pix`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || 'Erro ao gerar PIX da mensalidade');
      }

      setPixMensalidade(data);
      onNotify('PIX gerado. Pague e confirme para regularizar.', 'success');
    } catch (error) {
      onNotify(error.message || 'Erro ao gerar PIX', 'error');
    } finally {
      setPagamentoAssinaturaLoading(false);
    }
  };

  const confirmarPixMensalidade = async () => {
    setPagamentoAssinaturaLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ metodo_pagamento: 'pix', confirmar_pix: true })
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || 'Erro ao confirmar PIX');
      }

      setPixMensalidade(null);
      onNotify('Mensalidade paga via PIX com sucesso!', 'success');
      await carregarAssinaturaBarbearia();
    } catch (error) {
      onNotify(error.message || 'Erro ao confirmar PIX', 'error');
    } finally {
      setPagamentoAssinaturaLoading(false);
    }
  };

  const pagarMensalidadeCartao = async () => {
    if (!cartaoMensalidade.numero_cartao || !cartaoMensalidade.titular || !cartaoMensalidade.validade || !cartaoMensalidade.cvv) {
      onNotify('Preencha todos os dados do cartao', 'error');
      return;
    }

    setPagamentoAssinaturaLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          metodo_pagamento: 'cartao',
          numero_cartao: cartaoMensalidade.numero_cartao,
          titular: cartaoMensalidade.titular,
          validade: cartaoMensalidade.validade,
          cvv: cartaoMensalidade.cvv
        })
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || 'Erro ao pagar mensalidade com cartao');
      }

      setCartaoMensalidade({ numero_cartao: '', titular: '', validade: '', cvv: '' });
      onNotify('Mensalidade paga com cartao!', 'success');
      await carregarAssinaturaBarbearia();
    } catch (error) {
      onNotify(error.message || 'Erro ao pagar mensalidade', 'error');
    } finally {
      setPagamentoAssinaturaLoading(false);
    }
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        onNotify('Imagem muito grande. Máximo 10MB', 'error');
        return;
      }
      
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewImage(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const _handlePortfolioImageChange = (e) => {
    const files = Array.from(e.target.files);

    const validFiles = files.filter(file => {
      if (file.size > 10 * 1024 * 1024) {
        onNotify(`${file.name} muito grande. Máximo 10MB`, 'error');
        return false;
      }
      return true;
    });

    if (portfolioImages.length + validFiles.length > 10) {
      const msg = `Máximo de 10 fotos no portfólio (você já tem ${portfolioImages.length})`;
      onNotify(msg, 'error');
      return;
    }

    validFiles.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPortfolioImages(prev => {
          if (prev.includes(reader.result)) {
            return prev;
          }
          return [...prev, reader.result];
        });
      };
      reader.readAsDataURL(file);
    });
  };

  const _removePortfolioImage = (index) => {
    setPortfolioImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleSaveProfile = async () => {
    if (userType === 'barbeiro') {
      if (portfolioImages.length < 3) {
        onNotify('Barbeiro precisa de NO MÍNIMO 3 fotos de portfólio! Você tem ' + portfolioImages.length, 'error');
        return;
      }
    }

    setLoading(true);
    try {
      let falhasRemocaoPortfolio = 0;
      let falhasUploadPortfolio = 0;
      let falhaUploadFotoPessoal = false;
      let itensRemovidos = [];
      let novasPortfolio = [];

      let fotoPerfil = previewImage;

      if (previewImage && previewImage.startsWith('data:')) {
        const response = await fetch(previewImage);
        const blob = await response.blob();
        
        const formDataUpload = new FormData();
        formDataUpload.append('file', blob, 'foto_perfil.jpg');
        formDataUpload.append('pasta', 'perfil');
        
        const uploadRes = await fetch(`${API_URL}/api/v1/upload/imagem`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formDataUpload
        });

        if (!uploadRes.ok) {
          const error = await uploadRes.json();
          throw new Error('Erro ao fazer upload da foto: ' + (error.detail || 'erro desconhecido'));
        }

        const uploadData = await uploadRes.json();
        fotoPerfil = uploadData.url;
      }

      if (userType === 'barbeiro') {
        itensRemovidos = portfolioServerItems.filter(
          (item) => !portfolioImages.includes(item.url)
        );
        novasPortfolio = portfolioImages.filter(img => typeof img === 'string' && img.startsWith('data:'));

      }

      let fotoURI = fotoPessoal;
      if (userType === 'barbeiro' && fotoPessoal && fotoPessoal.startsWith('data:')) {
        const response = await fetch(fotoPessoal);
        const blob = await response.blob();
        
        const formDataUpload = new FormData();
        formDataUpload.append('file', blob, 'foto_pessoal.jpg');
        formDataUpload.append('pasta', 'perfil');
        
        const uploadRes = await fetch(`${API_URL}/api/v1/upload/imagem`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formDataUpload
        });

        if (uploadRes.ok) {
          const uploadData = await uploadRes.json();
          fotoURI = uploadData.url;
        } else {
          falhaUploadFotoPessoal = true;
        }
      }

      const payload = {
        nome: formData.nome,
        email: formData.email,
        telefone: formData.telefone,
        endereco: formData.endereco
      };

      if (fotoPerfil && !fotoPerfil.startsWith('data:')) {
        payload.foto_perfil = fotoPerfil;
      }

      if (userType === 'barbeiro') {
        payload.disponivel = disponivel;
        if (fotoURI && !fotoURI.startsWith('data:')) {
          payload.foto_pessoal = fotoURI;
        }
      }

      const res = await fetch(`${API_URL}/api/v1/usuarios/me`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Erro ao atualizar perfil');
      }

      // Sincroniza portfólio somente após o PATCH do perfil ter sucesso.
      if (userType === 'barbeiro') {
        for (const item of itensRemovidos) {
          try {
            const deleteRes = await fetch(`${API_URL}/api/v1/barbeiro/portfolio/${item.id}`, {
              method: 'DELETE',
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            if (!deleteRes.ok) {
              falhasRemocaoPortfolio += 1;
            }
          } catch (_err) {
            falhasRemocaoPortfolio += 1;
          }
        }

        for (const img of novasPortfolio) {
          try {
            const response = await fetch(img);
            const blob = await response.blob();

            const formDataUpload = new FormData();
            formDataUpload.append('file', blob, 'portfolio.jpg');
            formDataUpload.append('pasta', 'portfolio');

            const uploadRes = await fetch(`${API_URL}/api/v1/upload/imagem`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`
              },
              body: formDataUpload
            });

            if (uploadRes.ok) {
              const uploadData = await uploadRes.json();
              const salvarPortfolioRes = await fetch(`${API_URL}/api/v1/barbeiro/portfolio`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                  url_imagem: uploadData.url,
                  tipo_servico: 'corte',
                  descricao: 'Portfolio'
                })
              });

              if (!salvarPortfolioRes.ok) {
                falhasUploadPortfolio += 1;
              }
            } else {
              falhasUploadPortfolio += 1;
            }
          } catch (_err) {
            falhasUploadPortfolio += 1;
          }
        }
      }

      if (falhasRemocaoPortfolio > 0 || falhasUploadPortfolio > 0 || falhaUploadFotoPessoal) {
        const partes = [];
        if (falhasRemocaoPortfolio > 0) {
          partes.push(`${falhasRemocaoPortfolio} remoção(ões) não concluída(s)`);
        }
        if (falhasUploadPortfolio > 0) {
          partes.push(`${falhasUploadPortfolio} upload(s) não concluído(s)`);
        }
        if (falhaUploadFotoPessoal) {
          partes.push('foto pessoal não atualizada');
        }
        onNotify(`Perfil atualizado, mas houve falhas em mídias: ${partes.join(' e ')}.`, 'error');
      } else {
        onNotify('Perfil atualizado com sucesso!', 'success');
      }

      setEditing(false);
      await fetchUserProfile();
    } catch (error) {
      onNotify(error.message || 'Erro ao atualizar perfil', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (passwordData.novaSenha !== passwordData.confirmarSenha) {
      onNotify('As senhas não coincidem', 'error');
      return;
    }

    if (passwordData.novaSenha.length < 6) {
      onNotify('A nova senha deve ter no mínimo 6 caracteres', 'error');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/usuarios/trocar-senha`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          senha_atual: passwordData.senhaAtual,
          nova_senha: passwordData.novaSenha
        })
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Erro ao trocar senha');
      }

      onNotify('Senha alterada com sucesso!', 'success');
      setChangingPassword(false);
      setPasswordData({ senhaAtual: '', novaSenha: '', confirmarSenha: '' });
    } catch (error) {
      onNotify(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSairDaBarbearia = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/barbeiro/sair-barbearia`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Erro ao sair da barbearia');
      }

      onNotify('Você saiu da barbearia com sucesso!', 'success');
      setBarbeariaAtualId(null);
      setPresenteEmLocal(false);
      await fetchUserProfile();
    } catch (error) {
      onNotify(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const resetarEdicaoPerfil = useCallback(() => {
    const portfolioOriginal = portfolioServerItems.length > 0
      ? portfolioServerItems.map((item) => item.url).filter(Boolean)
      : (user?.portfolio_fotos || []);

    setEditing(false);
    setFormData({
      nome: user?.nome || '',
      email: user?.email || '',
      telefone: user?.telefone || '',
      endereco: user?.endereco || '',
      cpf: user?.cpf || '',
      cnpj: user?.cnpj || ''
    });
    setPreviewImage(user?.foto_perfil || null);
    setFotoPessoal(user?.foto_pessoal || null);
    setPortfolioImages(portfolioOriginal);
  }, [user, portfolioServerItems]);

  if (loading && !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4 pb-24">
      {imageModal && (
        <div 
          className="fixed inset-0 bg-black/95 z-[100] flex items-center justify-center p-4"
          onClick={() => setImageModal(null)}
        >
          <button 
            onClick={() => setImageModal(null)}
            className="absolute top-4 right-4 bg-red-600 p-3 rounded-full hover:bg-red-700 active:scale-95"
          >
            <X size={24} className="text-white" />
          </button>
          <img 
            src={imageModal} 
            alt="Visualização" 
            className="max-w-full max-h-full object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <User className="text-orange-500" size={28} />
          Meu Perfil
        </h1>
        {!editing && !changingPassword && userType !== 'barbeiro' && (
          <button
            onClick={() => setEditing(true)}
            className="bg-orange-500 text-white px-4 py-2 rounded-lg font-bold text-sm active:scale-95"
          >
            Editar
          </button>
        )}
      </div>

      {userType === 'barbeiro' && (
        <>
          {!editing && !changingPassword && (activeTab === 'dados' || activeTab === 'portfolio') && (
            <button
              onClick={() => setEditing(true)}
              className="w-full bg-orange-500 text-white px-4 py-3 rounded-lg font-bold text-sm active:scale-95"
            >
              ✏️ Editar Perfil
            </button>
          )}

          <div className="flex gap-2 border-b border-zinc-800">
            <button
              onClick={() => setActiveTab('dados')}
              className={`flex-1 py-3 font-bold text-sm ${
                activeTab === 'dados'
                  ? 'text-orange-500 border-b-2 border-orange-500'
                  : 'text-zinc-500'
              }`}
            >
              👤 Dados
            </button>
            <button
              onClick={() => setActiveTab('portfolio')}
              className={`flex-1 py-3 font-bold text-sm ${
                activeTab === 'portfolio'
                  ? 'text-orange-500 border-b-2 border-orange-500'
                  : 'text-zinc-500'
              }`}
            >
              📸 Portfólio
            </button>
            <button
              onClick={() => setActiveTab('avaliacoes')}
              className={`flex-1 py-3 font-bold text-sm ${
                activeTab === 'avaliacoes'
                  ? 'text-orange-500 border-b-2 border-orange-500'
                  : 'text-zinc-500'
              }`}
            >
              ⭐ Avaliações
            </button>
            <button
              onClick={() => setActiveTab('pagamento')}
              className={`flex-1 py-3 font-bold text-sm ${
                activeTab === 'pagamento'
                  ? 'text-orange-500 border-b-2 border-orange-500'
                  : 'text-zinc-500'
              }`}
            >
              💸 Pagamento
            </button>
          </div>

          {userType === 'barbeiro' && (
            <div className="space-y-2 mt-4">
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-400">📄 Documento</span>
                  {user?.documento_verificado ? (
                    <span className="bg-green-600/20 border border-green-600 rounded-full px-3 py-1 text-xs text-green-400 font-bold">
                      ✓ Verificado
                    </span>
                  ) : (
                    <span className="bg-yellow-600/20 border border-yellow-600 rounded-full px-3 py-1 text-xs text-yellow-400 font-bold">
                      ⏳ Pendente
                    </span>
                  )}
                </div>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-400">👤 Perfil</span>
                  {user?.perfil_aprovado ? (
                    <span className="bg-green-600/20 border border-green-600 rounded-full px-3 py-1 text-xs text-green-400 font-bold">
                      ✓ Aprovado
                    </span>
                  ) : (
                    <span className="bg-yellow-600/20 border border-yellow-600 rounded-full px-3 py-1 text-xs text-yellow-400 font-bold">
                      ⏳ Em análise
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {userType !== 'barbeiro' && (
        <div className="flex flex-col items-center gap-3 py-4">
          <div className="relative">
            <div className="w-28 h-28 rounded-full bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center text-white font-bold text-4xl overflow-hidden border-4 border-zinc-800">
              {previewImage ? (
                <img src={previewImage} alt="Perfil" className="w-full h-full object-cover" />
              ) : (
                user?.nome?.charAt(0).toUpperCase() || 'U'
              )}
            </div>
            {editing && (
              <label className="absolute bottom-0 right-0 bg-orange-500 p-2 rounded-full cursor-pointer hover:bg-orange-600 active:scale-95">
                <Camera size={18} className="text-white" />
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleImageChange}
                />
              </label>
            )}
          </div>
        </div>
      )}

      {userType === 'barbearia' && (
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-bold text-zinc-300 uppercase">Barbeiros Vinculados</h2>
          {barbeariaPerfilId && (
            <p className="text-[11px] text-zinc-500">Barbearia ID: {barbeariaPerfilId}</p>
          )}
          {barbeirosVinculadosBarbearia.length === 0 ? (
            <p className="text-zinc-600 text-xs text-center py-2">Nenhum barbeiro vinculado ainda.</p>
          ) : (
            <div className="space-y-2">
              {barbeirosVinculadosBarbearia.map((barbeiro) => (
                <div key={barbeiro.id} className="bg-black/40 border border-zinc-800 rounded-lg p-3 flex items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-white">{barbeiro.nome}</p>
                    <p className="text-[11px] text-zinc-400">{barbeiro.totalAgendamentos} agendamento(s) com sua barbearia</p>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-1 rounded ${barbeiro.presenteNoLocal ? 'bg-green-600/20 text-green-400 border border-green-600/40' : 'bg-zinc-700/30 text-zinc-300 border border-zinc-700'}`}>
                    {barbeiro.presenteNoLocal ? 'PRESENTE' : 'SEM PRESENCA AGORA'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {userType === 'barbearia' && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
          <h3 className="text-white font-bold flex items-center gap-2">
            <Wallet size={18} className="text-orange-400" />
            Plano e Mensalidade
          </h3>

          {assinaturaLoading ? (
            <p className="text-zinc-400 text-sm">Carregando assinatura...</p>
          ) : (
            <>
              <div className="bg-black/40 border border-zinc-800 rounded-lg p-3 text-sm space-y-1">
                <p className="text-zinc-300">Status: <strong>{assinaturaStatus?.status || 'sem_assinatura'}</strong></p>
                <p className="text-zinc-400">Cadeiras ativas: <strong>{assinaturaStatus?.cadeiras_ativas ?? assinaturaAtual?.cadeiras_ativas ?? 0}</strong></p>
                <p className="text-zinc-400">Valor mensal: <strong>{formatarDinheiro(assinaturaStatus?.valor_mensalidade ?? assinaturaAtual?.valor_mensal)}</strong></p>
                <p className="text-zinc-400">Proximo vencimento: <strong>{formatarDataHora(assinaturaStatus?.proximo_vencimento || assinaturaAtual?.proximo_vencimento)}</strong></p>
                {assinaturaStatus?.mensagem && (
                  <p className="text-orange-300 text-xs">{assinaturaStatus.mensagem}</p>
                )}
              </div>

              <div className="bg-black/40 border border-zinc-800 rounded-lg p-3 space-y-2">
                <label className="text-xs text-zinc-400 block">Cadeiras no plano (1 a 20)</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={cadeirasDesejadas}
                  onChange={(e) => setCadeirasDesejadas(Number(e.target.value || 1))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-2 text-white outline-none focus:border-orange-500"
                />
                <p className="text-xs text-zinc-400">Simulacao: <strong>{formatarDinheiro(assinaturaCalculo?.valor_total)}</strong></p>
                <button
                  onClick={contratarOuAtualizarAssinatura}
                  disabled={pagamentoAssinaturaLoading}
                  className="w-full bg-orange-600 hover:bg-orange-700 disabled:opacity-60 text-white px-4 py-2 rounded-lg text-sm font-bold"
                >
                  {pagamentoAssinaturaLoading ? 'Processando...' : 'Salvar Plano'}
                </button>
              </div>

              <div className="bg-black/40 border border-zinc-800 rounded-lg p-3 space-y-2">
                <p className="text-sm text-zinc-200 font-bold">Pagamento da Mensalidade</p>

                <button
                  onClick={gerarPixMensalidade}
                  disabled={pagamentoAssinaturaLoading}
                  className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white px-4 py-2 rounded-lg text-sm font-bold"
                >
                  Gerar PIX
                </button>

                {pixMensalidade && (
                  <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-xs text-zinc-300 space-y-2">
                    <p>Valor PIX: <strong>{formatarDinheiro(pixMensalidade.valor)}</strong></p>
                    {pixMensalidade.qrcode_base64 && (
                      <img
                        src={`data:image/png;base64,${pixMensalidade.qrcode_base64}`}
                        alt="QR Code PIX"
                        className="w-40 h-40 bg-white p-2 rounded mx-auto"
                      />
                    )}
                    <p className="break-all">Copia e cola: {pixMensalidade.pix_copia_cola}</p>
                    <button
                      onClick={confirmarPixMensalidade}
                      disabled={pagamentoAssinaturaLoading}
                      className="w-full bg-green-700 hover:bg-green-800 disabled:opacity-60 text-white px-3 py-2 rounded font-bold"
                    >
                      Confirmar Pagamento PIX
                    </button>
                  </div>
                )}

                <input
                  type="text"
                  placeholder="Numero do cartao"
                  value={cartaoMensalidade.numero_cartao}
                  onChange={(e) => setCartaoMensalidade({ ...cartaoMensalidade, numero_cartao: e.target.value })}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-2 text-white outline-none focus:border-orange-500"
                />
                <input
                  type="text"
                  placeholder="Titular"
                  value={cartaoMensalidade.titular}
                  onChange={(e) => setCartaoMensalidade({ ...cartaoMensalidade, titular: e.target.value })}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-2 text-white outline-none focus:border-orange-500"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="MM/AA"
                    value={cartaoMensalidade.validade}
                    onChange={(e) => setCartaoMensalidade({ ...cartaoMensalidade, validade: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-2 text-white outline-none focus:border-orange-500"
                  />
                  <input
                    type="text"
                    placeholder="CVV"
                    value={cartaoMensalidade.cvv}
                    onChange={(e) => setCartaoMensalidade({ ...cartaoMensalidade, cvv: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-2 text-white outline-none focus:border-orange-500"
                  />
                </div>
                <button
                  onClick={pagarMensalidadeCartao}
                  disabled={pagamentoAssinaturaLoading}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white px-4 py-2 rounded-lg text-sm font-bold"
                >
                  Pagar com Cartao
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {userType === 'barbeiro' && activeTab === 'portfolio' && (
        <div className="space-y-3">
          <TabPortfolioBarbeiro
            portfolioImages={portfolioImages}
            _setPortfolioImages={setPortfolioImages}
            editing={editing}
            handlePortfolioImageChange={_handlePortfolioImageChange}
            removePortfolioImage={_removePortfolioImage}
            setImageModal={setImageModal}
          />

          {editing && (
            <div className="flex gap-2 pt-1">
              <button
                onClick={handleSaveProfile}
                disabled={loading || portfolioImages.length < 3}
                className="flex-1 bg-orange-500 text-white px-4 py-3 rounded-lg font-bold flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save size={18} />
                {loading ? 'Salvando...' : 'Salvar'}
              </button>
              <button
                onClick={resetarEdicaoPerfil}
                className="flex-1 bg-zinc-800 text-white px-4 py-3 rounded-lg font-bold flex items-center justify-center gap-2 active:scale-95"
              >
                <X size={18} />
                Cancelar
              </button>
            </div>
          )}
        </div>
      )}

      {userType === 'barbeiro' && activeTab === 'avaliacoes' && (
        <TabAvaliacoesBarbeiro
          avaliacoes={_avaliacoes}
          avaliacaoMedia={
            _avaliacaoMedia || (user?.media_avaliacoes != null
              ? {
                  media: Number(user.media_avaliacoes).toFixed(1),
                  total_avaliacoes: user?.total_avaliacoes || 0,
                }
              : null)
          }
          avaliacoesLoading={_avaliacoesLoading}
          hasMoreAvaliacoes={hasMoreAvaliacoes}
          carregandoMais={carregandoMaisAvaliacoes}
          onCarregarMais={handleCarregarMaisAvaliacoes}
        />
      )}

      {userType === 'barbeiro' && activeTab === 'pagamento' ? (
        <div className="space-y-3">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-2">
            <h3 className="text-white font-bold">Resumo de Recebimento</h3>
            <p className="text-xs text-zinc-400">Valores calculados com base nas comissoes ja concluidas.</p>

            <div className="grid grid-cols-1 gap-2 text-sm">
              <div className="bg-black/40 border border-zinc-800 rounded-lg p-3">
                <p className="text-zinc-400 text-xs">Saldo disponivel para repasse</p>
                <p className="text-green-400 text-xl font-bold">{formatarDinheiro(resumoPagamento?.saldo_disponivel)}</p>
              </div>
              <div className="bg-black/40 border border-zinc-800 rounded-lg p-3">
                <p className="text-zinc-400 text-xs">Estimativa no periodo escolhido</p>
                <p className="text-white text-lg font-bold">{formatarDinheiro(resumoPagamento?.valor_estimado_periodo)}</p>
              </div>
              <div className="bg-black/40 border border-zinc-800 rounded-lg p-3">
                <p className="text-zinc-400 text-xs">Proximo repasse previsto</p>
                <p className="text-orange-400 font-bold">{formatarDataHora(resumoPagamento?.proximo_repasse_em)}</p>
              </div>
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
            <h3 className="text-white font-bold flex items-center gap-2">
              <Wallet size={18} className="text-green-400" />
              Conta para Receber Repasse
            </h3>
            <p className="text-xs text-zinc-400">
              Cadastre sua conta. Quando o cliente pagar, o valor e dividido automaticamente entre barbeiro, barbearia e Barber Move.
            </p>

            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Titular da Conta</label>
              <input
                type="text"
                value={contaPagamento.titular_nome}
                onChange={(e) => setContaPagamento({ ...contaPagamento, titular_nome: e.target.value })}
                className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                placeholder="Nome do titular"
              />
            </div>

            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Documento do Titular</label>
              <input
                type="text"
                value={contaPagamento.titular_documento}
                onChange={(e) => setContaPagamento({ ...contaPagamento, titular_documento: e.target.value })}
                className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                placeholder="CPF/CNPJ"
              />
            </div>

            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Chave PIX</label>
              <input
                type="text"
                value={contaPagamento.chave_pix}
                onChange={(e) => setContaPagamento({ ...contaPagamento, chave_pix: e.target.value })}
                className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                placeholder="Telefone, email, CPF/CNPJ ou chave aleatoria"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-zinc-400 mb-1 block">Banco</label>
                <input
                  type="text"
                  value={contaPagamento.banco}
                  onChange={(e) => setContaPagamento({ ...contaPagamento, banco: e.target.value })}
                  className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                  placeholder="Banco"
                />
              </div>
              <div>
                <label className="text-xs text-zinc-400 mb-1 block">Agencia</label>
                <input
                  type="text"
                  value={contaPagamento.agencia}
                  onChange={(e) => setContaPagamento({ ...contaPagamento, agencia: e.target.value })}
                  className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                  placeholder="Agencia"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-zinc-400 mb-1 block">Conta</label>
                <input
                  type="text"
                  value={contaPagamento.conta}
                  onChange={(e) => setContaPagamento({ ...contaPagamento, conta: e.target.value })}
                  className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                  placeholder="Conta"
                />
              </div>
              <div>
                <label className="text-xs text-zinc-400 mb-1 block">Tipo</label>
                <select
                  value={contaPagamento.tipo_conta}
                  onChange={(e) => setContaPagamento({ ...contaPagamento, tipo_conta: e.target.value })}
                  className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                >
                  <option value="corrente">Corrente</option>
                  <option value="poupanca">Poupanca</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Frequencia de Repasse</label>
              <select
                value={contaPagamento.frequencia_repasse}
                onChange={(e) => setContaPagamento({ ...contaPagamento, frequencia_repasse: e.target.value })}
                className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
              >
                <option value="diario">Diario</option>
                <option value="semanal">Semanal</option>
                <option value="mensal">Mensal</option>
              </select>
            </div>

            {contaPagamento.frequencia_repasse === 'semanal' && (
              <div>
                <label className="text-xs text-zinc-400 mb-1 block">Dia da Semana do Repasse</label>
                <select
                  value={contaPagamento.dia_semana_repasse}
                  onChange={(e) => setContaPagamento({ ...contaPagamento, dia_semana_repasse: Number(e.target.value) })}
                  className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                >
                  <option value={0}>Segunda-feira</option>
                  <option value={1}>Terca-feira</option>
                  <option value={2}>Quarta-feira</option>
                  <option value={3}>Quinta-feira</option>
                  <option value={4}>Sexta-feira</option>
                  <option value={5}>Sabado</option>
                  <option value={6}>Domingo</option>
                </select>
              </div>
            )}

            {contaPagamento.frequencia_repasse === 'mensal' && (
              <div>
                <label className="text-xs text-zinc-400 mb-1 block">Dia do Mes do Repasse</label>
                <input
                  type="number"
                  min={1}
                  max={28}
                  value={contaPagamento.dia_mes_repasse}
                  onChange={(e) => setContaPagamento({ ...contaPagamento, dia_mes_repasse: Number(e.target.value || 1) })}
                  className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                />
              </div>
            )}

            <button
              onClick={salvarContaPagamento}
              disabled={salvandoContaPagamento}
              className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white px-4 py-3 rounded-lg font-bold"
            >
              {salvandoContaPagamento ? 'Salvando...' : 'Salvar Conta de Repasse'}
            </button>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-2">
            <h4 className="text-white font-bold">Divisao Automatica do Pagamento</h4>
            <p className="text-xs text-zinc-400">
              Essa divisao e configurada no perfil do admin.
            </p>

            <div className="text-sm text-zinc-200 grid grid-cols-1 gap-1">
              <p>Barbeiro: <strong>{splitPagamento?.percentual_barbeiro ?? 40}%</strong></p>
              <p>Barbearia: <strong>{splitPagamento?.percentual_barbearia ?? 50}%</strong></p>
              <p>Barber Move: <strong>{splitPagamento?.percentual_barbermove ?? 10}%</strong></p>
            </div>

            {userType === 'barbearia' && (
              <p className="text-xs text-green-400 font-bold mt-1">
                Sua comissao da barbearia e de 50% em cada servico concluido.
              </p>
            )}

            {(splitPagamento?.deposito_chave_pix || splitPagamento?.deposito_conta) && (
              <div className="mt-2 border-t border-zinc-800 pt-2 text-xs text-zinc-400">
                <p className="text-zinc-300 font-bold">Deposito Barber Move (Admin)</p>
                {splitPagamento?.deposito_nome && <p>Titular: {splitPagamento.deposito_nome}</p>}
                {splitPagamento?.deposito_chave_pix && <p>PIX: {splitPagamento.deposito_chave_pix}</p>}
                {splitPagamento?.deposito_banco && <p>Banco: {splitPagamento.deposito_banco}</p>}
                {splitPagamento?.deposito_agencia && <p>Agencia: {splitPagamento.deposito_agencia}</p>}
                {splitPagamento?.deposito_conta && <p>Conta: {splitPagamento.deposito_conta}</p>}
              </div>
            )}
          </div>
        </div>
      ) : null}

      {editing && (userType !== 'barbeiro' || activeTab === 'dados') ? (
        <div className="space-y-3">
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Nome Completo</label>
            <input
              type="text"
              value={formData.nome}
              onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
            />
          </div>

          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
            />
          </div>

          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Telefone</label>
            <input
              type="tel"
              value={formData.telefone}
              onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
              placeholder="(11) 98765-4321"
            />
          </div>

          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Endereço</label>
            <input
              type="text"
              value={formData.endereco}
              onChange={(e) => setFormData({ ...formData, endereco: e.target.value })}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
              placeholder="Rua, número, bairro"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <button
              onClick={handleSaveProfile}
              disabled={loading || (userType === 'barbeiro' && portfolioImages.length < 3)}
              className="flex-1 bg-orange-500 text-white px-4 py-3 rounded-lg font-bold flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save size={18} />
              {loading ? 'Salvando...' : 'Salvar'}
            </button>
            <button
              onClick={resetarEdicaoPerfil}
              className="flex-1 bg-zinc-800 text-white px-4 py-3 rounded-lg font-bold flex items-center justify-center gap-2 active:scale-95"
            >
              <X size={18} />
              Cancelar
            </button>
          </div>
        </div>
      ) : !editing && (userType !== 'barbeiro' || activeTab === 'dados') ? (
        <div className="space-y-3">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-3">
              <User size={18} className="text-zinc-500" />
              <div className="flex-1">
                <p className="text-xs text-zinc-500">Nome</p>
                <p className="text-white font-medium">{user?.nome || 'Não informado'}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Mail size={18} className="text-zinc-500" />
              <div className="flex-1">
                <p className="text-xs text-zinc-500">Email</p>
                <p className="text-white font-medium">{user?.email || 'Não informado'}</p>
              </div>
            </div>

            {user?.telefone && (
              <div className="flex items-center gap-3">
                <Phone size={18} className="text-zinc-500" />
                <div className="flex-1">
                  <p className="text-xs text-zinc-500">Telefone</p>
                  <p className="text-white font-medium">{user.telefone}</p>
                </div>
              </div>
            )}

            {userType === 'barbeiro' && (
              <>
                <div className="flex items-center gap-3">
                  <ToggleRight size={18} className="text-zinc-500" />
                  <div className="flex-1">
                    <p className="text-xs text-zinc-500">Status</p>
                    <p className="text-white font-medium">
                      {presenteEmLocal
                        ? 'PRESENTE NO LOCAL'
                        : (user?.online_regiao ? 'DISPONIVEL NA REGIAO' : 'OFFLINE')}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <MapPin size={18} className="text-zinc-500" />
                  <div className="flex-1">
                    <p className="text-xs text-zinc-500">Barbearia atual</p>
                    <p className="text-white font-medium">
                      {presenteEmLocal
                        ? (user?.barbearia_atual_nome || 'Barbearia vinculada')
                        : 'Nenhuma barbearia vinculada agora'}
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>

          {userType === 'barbeiro' && user?.telefone && (
            <a
              href={`https://wa.me/55${user.telefone.replace(/\D/g, '')}`}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full bg-green-600 text-white px-4 py-4 rounded-lg font-bold flex items-center justify-center gap-2 hover:bg-green-700 active:scale-95"
            >
              <MessageCircle size={20} />
              Meu WhatsApp Business
            </a>
          )}

          {!changingPassword ? (
            <button
              onClick={() => setChangingPassword(true)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-4 flex items-center gap-3 hover:border-orange-500 active:scale-95"
            >
              <Lock size={18} className="text-zinc-500" />
              <span className="text-white font-medium">Trocar Senha</span>
            </button>
          ) : (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
              <h3 className="font-bold text-white flex items-center gap-2">
                <Lock size={18} className="text-orange-500" />
                Trocar Senha
              </h3>

              <div className="relative">
                <input
                  type={showCurrentPassword ? "text" : "password"}
                  placeholder="Senha atual"
                  value={passwordData.senhaAtual}
                  onChange={(e) => setPasswordData({ ...passwordData, senhaAtual: e.target.value })}
                  className="w-full bg-black border border-zinc-800 rounded-lg p-3 pr-12 text-white outline-none focus:border-orange-500"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500"
                >
                  {showCurrentPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              <div className="relative">
                <input
                  type={showNewPassword ? "text" : "password"}
                  placeholder="Nova senha (min. 6 caracteres)"
                  value={passwordData.novaSenha}
                  onChange={(e) => setPasswordData({ ...passwordData, novaSenha: e.target.value })}
                  className="w-full bg-black border border-zinc-800 rounded-lg p-3 pr-12 text-white outline-none focus:border-orange-500"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500"
                >
                  {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              <input
                type="password"
                placeholder="Confirmar nova senha"
                value={passwordData.confirmarSenha}
                onChange={(e) => setPasswordData({ ...passwordData, confirmarSenha: e.target.value })}
                className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
              />

              <div className="flex gap-2">
                <button
                  onClick={handleChangePassword}
                  disabled={loading}
                  className="flex-1 bg-orange-500 text-white px-4 py-3 rounded-lg font-bold active:scale-95 disabled:opacity-50"
                >
                  {loading ? 'Alterando...' : 'Confirmar'}
                </button>
                <button
                  onClick={() => {
                    setChangingPassword(false);
                    setPasswordData({ senhaAtual: '', novaSenha: '', confirmarSenha: '' });
                  }}
                  className="flex-1 bg-zinc-800 text-white px-4 py-3 rounded-lg font-bold active:scale-95"
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}

          {userType === 'barbeiro' && (
            <button
              onClick={handleSairDaBarbearia}
              className="w-full bg-yellow-600/10 border border-yellow-600 rounded-lg p-4 flex items-center justify-center gap-2 hover:bg-yellow-600/20 active:scale-95"
            >
              <LogOut size={18} className="text-yellow-500" />
              <span className="text-yellow-500 font-bold">Sair da Barbearia</span>
            </button>
          )}

          <button
            onClick={onLogout}
            className="w-full bg-red-600/10 border border-red-600 rounded-lg p-4 flex items-center justify-center gap-2 hover:bg-red-600/20 active:scale-95"
          >
            <LogOut size={18} className="text-red-500" />
            <span className="text-red-500 font-bold">Sair da Conta</span>
          </button>
        </div>
      ) : null}
    </div>
  );
}
