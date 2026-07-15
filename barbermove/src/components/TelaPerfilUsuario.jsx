import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Camera, LogOut, Upload, Trash2, Loader } from 'lucide-react';
import ScreenWrapper from './ScreenWrapper';
import AppCard from './AppCard';
import Header from './Header';
import styles from './TelaPerfilUsuario.module.css';
import { getApiBaseUrl, resolveMediaUrl } from '../utils/api';
import { gerarQrDataUrl, salvarMetodoPreferidoCliente, validarCartaoBasico } from './checkout/core';

const PERFIL_META = {
  cliente: { badge: 'Cliente Premium', titulo: 'Meu Perfil' },
  barbeiro: { badge: 'Barbeiro Profissional', titulo: 'Meu Perfil' },
  freelancer: { badge: 'Barbeiro Profissional', titulo: 'Meu Perfil' },
  barbearia: { badge: 'Barbearia Parceira', titulo: 'Meu Perfil' },
};

const PRECO_PRIMEIRA_CADEIRA = 47.9;
const PRECO_SEGUNDA_CADEIRA = 37.9;
const PRECO_TERCEIRA_CADEIRA = 27.9;
const PRECO_QUARTA_CADEIRA = 20.9;
const PRECO_MINIMO = 17.9;

function calcularPrecoCadeira(posicao) {
  if (posicao <= 1) return PRECO_PRIMEIRA_CADEIRA;
  if (posicao === 2) return PRECO_SEGUNDA_CADEIRA;
  if (posicao === 3) return PRECO_TERCEIRA_CADEIRA;
  if (posicao === 4) return PRECO_QUARTA_CADEIRA;
  return PRECO_MINIMO;
}

function calcularMensalidadeTotal(qtd) {
  let total = 0;
  for (let i = 1; i <= qtd; i += 1) {
    total += calcularPrecoCadeira(i);
  }
  return Number(total.toFixed(2));
}

function moneyBRL(value) {
  return Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function pareceQrEmImagem(valor) {
  if (!valor || typeof valor !== 'string') return false;
  const conteudo = valor.trim();
  if (!conteudo) return false;
  if (conteudo.startsWith('data:image')) return true;
  if (conteudo.startsWith('http://') || conteudo.startsWith('https://')) return true;
  if (conteudo.startsWith('iVBORw0KGgo')) return true;
  if (conteudo.startsWith('/9j/')) return true;
  if (conteudo.startsWith('R0lGOD')) return true;
  if (conteudo.startsWith('PHN2Zy')) return true;
  if (conteudo.startsWith('000201')) return false;
  if (conteudo.includes('BR.GOV.BCB.PIX')) return false;
  return conteudo.length > 80 && /^[A-Za-z0-9+/=\s]+$/.test(conteudo);
}

function pareceCodigoPix(valor) {
  if (!valor || typeof valor !== 'string') return false;
  const conteudo = valor.trim();
  if (!conteudo) return false;
  if (conteudo.startsWith('000201')) return true;
  return conteudo.includes('BR.GOV.BCB.PIX');
}

function normalizarPixPerfil(data) {
  const payload = data?.pix || data?.dados_pix || data?.data || data || {};
  const transactionData = payload?.point_of_interaction?.transaction_data || {};
  const nested = payload?.data || {};
  const cobr = payload?.cob || data?.cob || {};
  const loc = payload?.loc || data?.loc || {};

  const candidatosImagem = [
    payload.qrcode_base64,
    payload.qr_code_base64,
    payload.qrCodeBase64,
    payload.qrcode,
    payload.qr_code,
    payload.imagem_qr,
    transactionData.qr_code_base64,
    transactionData.qr_code,
    nested.qrcode_base64,
    nested.qr_code_base64,
    nested.qrcode,
    nested.qr_code,
    cobr.qrcode_base64,
    cobr.qr_code_base64,
    cobr.qrcode,
    cobr.qr_code,
    loc.qrcode_base64,
    loc.qr_code_base64,
    loc.qrcode,
    loc.qr_code,
  ];

  const candidatosTexto = [
    payload.pix_copia_cola,
    payload.codigo_pix,
    payload.copia_cola,
    payload.emv,
    payload.payload,
    payload.payload_pix,
    transactionData.qr_code,
    transactionData.payload,
    nested.pix_copia_cola,
    nested.codigo_pix,
    nested.copia_cola,
    nested.emv,
    nested.payload,
    nested.payload_pix,
    cobr.pix_copia_cola,
    cobr.codigo_pix,
    cobr.emv,
    loc.qrcode,
    loc.qr_code,
    data?.pix_copia_cola,
    data?.codigo_pix,
    data?.copia_cola,
    data?.emv,
    data?.payload,
    data?.payload_pix,
  ];

  let qrcodeBase64 = null;
  for (const item of candidatosImagem) {
    if (pareceQrEmImagem(item)) {
      qrcodeBase64 = item;
      break;
    }
  }

  let pixCopiaCola = '';
  for (const item of candidatosTexto) {
    if (pareceCodigoPix(item)) {
      pixCopiaCola = item;
      break;
    }
  }

  if (!pixCopiaCola) {
    pixCopiaCola = candidatosTexto.find((item) => typeof item === 'string' && item.trim()) || '';
  }

  return {
    ...payload,
    qrcode_base64: qrcodeBase64,
    pix_copia_cola: pixCopiaCola,
    valor: payload.valor ?? payload.amount ?? nested.valor ?? nested.amount ?? data?.valor_mensalidade ?? 0,
  };
}

function montarPixFinalPerfil(pixRaw) {
  const pixNormalizado = normalizarPixPerfil(pixRaw);
  const payloadBruto = pixRaw?.pix || pixRaw?.dados_pix || pixRaw?.data || pixRaw || {};
  const payloadData = payloadBruto?.data || {};
  const payloadCobr = payloadBruto?.cob || {};

  return {
    ...payloadBruto,
    ...pixNormalizado,
    qrcode_base64:
      pixNormalizado.qrcode_base64 ||
      payloadBruto.qrcode_base64 ||
      payloadBruto.qr_code_base64 ||
      payloadBruto.qrCodeBase64 ||
      payloadData.qrcode_base64 ||
      payloadData.qr_code_base64 ||
      payloadCobr.qrcode_base64 ||
      payloadCobr.qr_code_base64 ||
      null,
    pix_copia_cola:
      pixNormalizado.pix_copia_cola ||
      payloadBruto.pix_copia_cola ||
      payloadBruto.codigo_pix ||
      payloadBruto.copia_cola ||
      payloadBruto.emv ||
      payloadBruto.qrcode ||
      payloadBruto.qr_code ||
      payloadBruto.payload ||
      payloadData.pix_copia_cola ||
      payloadData.codigo_pix ||
      payloadData.copia_cola ||
      payloadData.emv ||
      payloadData.payload ||
      payloadCobr.pix_copia_cola ||
      payloadCobr.codigo_pix ||
      payloadCobr.emv ||
      '',
    valor:
      pixNormalizado.valor ??
      payloadBruto.valor ??
      payloadBruto.amount ??
      payloadData.valor ??
      payloadData.amount ??
      payloadCobr.valor_original ??
      payloadBruto.valor_mensalidade ??
      0,
  };
}

function getPixQrSrcPerfil(qrcodeBase64) {
  if (!qrcodeBase64) return '';
  const conteudo = String(qrcodeBase64).trim();
  if (!conteudo) return '';
  if (conteudo.startsWith('data:image')) return conteudo;
  if (conteudo.startsWith('http://') || conteudo.startsWith('https://')) return conteudo;

  const conteudoLimpo = conteudo.replace(/\s/g, '');
  if (!conteudoLimpo) return '';

  let mime = 'image/png';
  if (conteudoLimpo.startsWith('/9j/')) mime = 'image/jpeg';
  if (conteudoLimpo.startsWith('R0lGOD')) mime = 'image/gif';
  if (conteudoLimpo.startsWith('PHN2Zy')) mime = 'image/svg+xml';
  return `data:${mime};base64,${conteudoLimpo}`;
}

async function safeReadJson(response, fallback = null) {
  if (!response) return fallback;
  const contentType = response.headers?.get?.('content-type') || '';
  if (!contentType.includes('application/json')) return fallback;

  try {
    return await response.json();
  } catch (_err) {
    return fallback;
  }
}

async function cropSquareImage(file, options = {}) {
  const { outSize = 720, quality = 0.88, zoom = 1, panX = 0, panY = 0 } = options;

  const dataUrl = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

  const img = await new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = dataUrl;
  });

  const baseSide = Math.min(img.width, img.height);
  const clampedZoom = Math.max(1, Math.min(2.5, Number(zoom || 1)));
  const cropSide = Math.max(1, Math.round(baseSide / clampedZoom));

  const maxShiftX = Math.max(0, Math.floor((img.width - cropSide) / 2));
  const maxShiftY = Math.max(0, Math.floor((img.height - cropSide) / 2));
  const clampedPanX = Math.max(-1, Math.min(1, Number(panX || 0)));
  const clampedPanY = Math.max(-1, Math.min(1, Number(panY || 0)));
  const sx = Math.max(0, Math.min(img.width - cropSide, Math.floor((img.width - cropSide) / 2 + (clampedPanX * maxShiftX))));
  const sy = Math.max(0, Math.min(img.height - cropSide, Math.floor((img.height - cropSide) / 2 + (clampedPanY * maxShiftY))));
  const finalSize = Math.max(1, Math.min(outSize, cropSide));

  const canvas = document.createElement('canvas');
  canvas.width = finalSize;
  canvas.height = finalSize;
  const ctx = canvas.getContext('2d');
  if (!ctx) return file;

  ctx.drawImage(img, sx, sy, cropSide, cropSide, 0, 0, finalSize, finalSize);

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));
  if (!blob) return file;

  return new File([blob], `${Date.now()}-avatar.jpg`, { type: 'image/jpeg' });
}

async function compressImage(file, maxSize = 1080, quality = 0.82) {
  const dataUrl = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

  const img = await new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = dataUrl;
  });

  const ratio = Math.min(1, maxSize / Math.max(img.width, img.height));
  const width = Math.max(1, Math.round(img.width * ratio));
  const height = Math.max(1, Math.round(img.height * ratio));

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext('2d');
  if (!ctx) return file;

  ctx.drawImage(img, 0, 0, width, height);

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));
  if (!blob) return file;

  return new File([blob], `${Date.now()}-${file.name.replace(/\.[^.]+$/, '')}.jpg`, { type: 'image/jpeg' });
}

export function TelaPerfilUsuario({
  userType = 'cliente',
  usuario,
  token,
  API_URL,
  aoSalvar,
  onLogout,
  onNotify: onNotifyProp,
  mostrarCabecalho = true,
  permitirEdicaoFoto = true,
}) {
  const onNotify = useCallback((mensagem, tipo = 'info') => {
    if (typeof onNotifyProp !== 'function') return;
    try {
      onNotifyProp(mensagem, tipo);
    } catch (err) {
      console.error('[perfil-cliente] falha ao notificar UI:', err);
    }
  }, [onNotifyProp]);

  const apiBase = useMemo(() => (API_URL || getApiBaseUrl() || '').replace(/\/$/, ''), [API_URL]);
  const perfilTipo = useMemo(() => {
    const tipoBruto = String(userType || usuario?.tipo || 'cliente').toLowerCase();
    return tipoBruto === 'freelancer' ? 'barbeiro' : tipoBruto;
  }, [userType, usuario?.tipo]);
  const meta = PERFIL_META[perfilTipo] || PERFIL_META.cliente;

  const [userId, setUserId] = useState(usuario?.id || null);
  const [nome, setNome] = useState(usuario?.nome || 'Usuario');
  const [email, setEmail] = useState(usuario?.email || '');
  const [telefone, setTelefone] = useState(usuario?.telefone || '');
  const [fotoPerfil, setFotoPerfil] = useState(usuario?.foto_perfil || '');
  const [portfolioFotos, setPortfolioFotos] = useState([]);
  const fotoPerfilResolvida = useMemo(() => resolveMediaUrl(fotoPerfil, apiBase), [fotoPerfil, apiBase]);

  const [barbeariaId, setBarbeariaId] = useState(null);
  const [cadeirasPlano, setCadeirasPlano] = useState(1);
  const [cadeirasPlanoSalvas, setCadeirasPlanoSalvas] = useState(1);
  const [metodoPagamentoPlano, setMetodoPagamentoPlano] = useState('pix');
  const [tipoCartaoPlano, setTipoCartaoPlano] = useState('cartao_credito');
  const [cartaoPlano, setCartaoPlano] = useState({ numero_cartao: '', titular: '', validade: '', cvv: '' });
  const [pixPlano, setPixPlano] = useState(null);
  const [pixPlanoQrFallback, setPixPlanoQrFallback] = useState('');
  const [pixPlanoImagemInvalida, setPixPlanoImagemInvalida] = useState(false);
  const [copiouPixPlano, setCopiouPixPlano] = useState(false);

  const [barberStatus, setBarberStatus] = useState('offline');
  const [barbeariaPresencaId, setBarbeariaPresencaId] = useState('');
  const [barbeariasDisponiveis, setBarbeariasDisponiveis] = useState([]);
  const [barbeariaAtualNome, setBarbeariaAtualNome] = useState('');
  const [barbeariaAtualEndereco, setBarbeariaAtualEndereco] = useState('');

  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [portfolioFalhas, setPortfolioFalhas] = useState({});

  const [avatarSourceFile, setAvatarSourceFile] = useState(null);
  const [avatarDraftPreview, setAvatarDraftPreview] = useState('');
  const [avatarZoom, setAvatarZoom] = useState(1);
  const [avatarPanX, setAvatarPanX] = useState(0);
  const [avatarPanY, setAvatarPanY] = useState(0);
  const [avatarEditorOpen, setAvatarEditorOpen] = useState(false);
  const [avatarDragging, setAvatarDragging] = useState(false);
  const avatarDragRef = useRef({
    active: false,
    startX: 0,
    startY: 0,
    startPanX: 0,
    startPanY: 0,
  });
  const avatarPointersRef = useRef(new Map());
  const avatarPinchRef = useRef({ active: false, startDistance: 0, startZoom: 1 });
  const saveSuccessTimeoutRef = useRef(null);

  const initial = (nome || '?').charAt(0).toUpperCase();

  const mensalidadeTotal = useMemo(() => calcularMensalidadeTotal(cadeirasPlano), [cadeirasPlano]);
  const mensalidadeAnterior = useMemo(() => calcularMensalidadeTotal(cadeirasPlanoSalvas), [cadeirasPlanoSalvas]);
  const precoCadeiraAtual = useMemo(() => calcularPrecoCadeira(cadeirasPlano), [cadeirasPlano]);
  const aumentoCadeirasPendente = useMemo(() => perfilTipo === 'barbearia' && cadeirasPlano > cadeirasPlanoSalvas, [perfilTipo, cadeirasPlano, cadeirasPlanoSalvas]);
  const acrescimoMensalPlano = useMemo(() => Number(Math.max(0, mensalidadeTotal - mensalidadeAnterior).toFixed(2)), [mensalidadeTotal, mensalidadeAnterior]);

  const carregarPerfil = useCallback(async () => {
    if (!token || !apiBase) return;

    try {
      const res = await fetch(`${apiBase}/api/v1/usuarios/perfil-completo`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await safeReadJson(res, {});
        setUserId(data?.id || null);
        setNome(data?.nome || 'Usuario');
        setEmail(data?.email || '');
        setTelefone(data?.telefone || '');
        setFotoPerfil(data?.foto_perfil || '');

        if (perfilTipo === 'barbeiro') {
          setBarbeariaAtualNome(data?.barbearia_atual_nome || '');
          setBarbeariaAtualEndereco(data?.barbearia_atual_endereco || '');
          if (data?.presente_em_local && data?.barbearia_atual_id) {
            setBarberStatus('presente');
            setBarbeariaPresencaId(String(data.barbearia_atual_id));
          } else if (data?.online_regiao || data?.disponivel) {
            setBarberStatus('online');
          } else {
            setBarberStatus('offline');
          }
        } else {
          setBarbeariaAtualNome('');
          setBarbeariaAtualEndereco('');
        }
      }
    } catch (_e) {
      // manter estado atual
    }

    if (perfilTipo === 'barbeiro') {
      try {
        const resPortfolio = await fetch(`${apiBase}/api/v1/barbeiro/portfolio`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (resPortfolio.ok) {
          const lista = await safeReadJson(resPortfolio, []);
          setPortfolioFotos(Array.isArray(lista) ? lista : []);
        }
      } catch (_e) {
        setPortfolioFotos([]);
      }

      try {
        const resBarbearias = await fetch(`${apiBase}/api/v1/barbearias/todas-aprovadas`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (resBarbearias.ok) {
          const data = await safeReadJson(resBarbearias, {});
          const lista = Array.isArray(data?.barbearias) ? data.barbearias : [];
          setBarbeariasDisponiveis(lista);
        }
      } catch (_e) {
        setBarbeariasDisponiveis([]);
      }
    }

    if (perfilTipo === 'barbearia') {
      try {
        const barbeariaRes = await fetch(`${apiBase}/api/v1/barbearia/minha`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (barbeariaRes.ok) {
          const barbearia = await safeReadJson(barbeariaRes, {});
          const id = Number(barbearia?.id || 0);
          if (id) {
            setBarbeariaId(id);
            const assinaturaRes = await fetch(`${apiBase}/api/v1/assinatura/barbearia/${id}`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (assinaturaRes.ok) {
              const assinatura = await safeReadJson(assinaturaRes, {});
              const qtd = Number(assinatura?.quantidade_cadeiras || 1);
              setCadeirasPlano(Math.max(1, Math.min(50, qtd)));
              setCadeirasPlanoSalvas(Math.max(1, Math.min(50, qtd)));
            }
          }
        }
      } catch (_e) {
        // ignora erro de assinatura
      }
    }
  }, [apiBase, token, perfilTipo]);

  useEffect(() => {
    let ativo = true;

    const carregarComSeguranca = async () => {
      try {
        await carregarPerfil();
      } catch (err) {
        console.error('[perfil-cliente] erro na inicializacao do perfil:', err);
        if (ativo) {
          onNotify('Nao foi possivel carregar seu perfil agora', 'error');
        }
      }
    };

    carregarComSeguranca();

    return () => {
      ativo = false;
    };
  }, [carregarPerfil, onNotify]);

  useEffect(() => {
    let ativo = true;

    const gerarPreviewPix = async () => {
      if (!pixPlano?.pix_copia_cola) {
        setPixPlanoQrFallback('');
        setPixPlanoImagemInvalida(false);
        return;
      }

      setPixPlanoImagemInvalida(false);

      try {
        const dataUrl = await gerarQrDataUrl(pixPlano.pix_copia_cola);
        if (ativo) setPixPlanoQrFallback(dataUrl);
      } catch (_err) {
        if (ativo) setPixPlanoQrFallback('');
      }
    };

    gerarPreviewPix();

    return () => {
      ativo = false;
    };
  }, [pixPlano]);

  useEffect(() => {
    let revoked = false;

    const gerarPreview = async () => {
      if (!avatarSourceFile) {
        if (avatarDraftPreview) {
          URL.revokeObjectURL(avatarDraftPreview);
        }
        setAvatarDraftPreview('');
        return;
      }

      try {
        const arquivoCrop = await cropSquareImage(avatarSourceFile, {
          zoom: avatarZoom,
          panX: avatarPanX,
          panY: avatarPanY,
          outSize: 720,
        });
        const previewUrl = URL.createObjectURL(arquivoCrop);

        if (revoked) {
          URL.revokeObjectURL(previewUrl);
          return;
        }

        if (avatarDraftPreview) {
          URL.revokeObjectURL(avatarDraftPreview);
        }
        setAvatarDraftPreview(previewUrl);
      } catch (_e) {
        onNotify?.('Nao foi possivel gerar preview da foto', 'error');
      }
    };

    gerarPreview();

    return () => {
      revoked = true;
    };
  }, [avatarSourceFile, avatarZoom, avatarPanX, avatarPanY]);

  const uploadImagem = async (file, pasta) => {
    const comprimido = await compressImage(file);
    const formData = new FormData();
    formData.append('file', comprimido);

    const res = await fetch(`${apiBase}/api/v1/upload/imagem?pasta=${encodeURIComponent(pasta)}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });

    if (!res.ok) throw new Error('Falha no upload');
    const data = await res.json();
    if (!data?.url) throw new Error('Upload sem URL');
    return data.url;
  };

  const handleFotoPerfil = async (event) => {
    const file = event.target.files?.[0];
    if (!file || !token || !apiBase) return;

    setAvatarSourceFile(file);
    setAvatarZoom(1);
    setAvatarPanX(0);
    setAvatarPanY(0);
    setAvatarEditorOpen(true);
    onNotify?.('Ajuste a foto no editor e clique em Aplicar foto.', 'info');
    event.target.value = '';
  };

  const cancelarDraftAvatar = () => {
    if (avatarDraftPreview) {
      URL.revokeObjectURL(avatarDraftPreview);
    }
    setAvatarSourceFile(null);
    setAvatarDraftPreview('');
    setAvatarZoom(1);
    setAvatarPanX(0);
    setAvatarPanY(0);
    setAvatarEditorOpen(false);
    setAvatarDragging(false);
    avatarDragRef.current.active = false;
    avatarPointersRef.current.clear();
    avatarPinchRef.current = { active: false, startDistance: 0, startZoom: 1 };
  };

  const clampPan = (value) => Math.max(-1, Math.min(1, Number(value || 0)));
  const clampZoom = (value) => Math.max(1, Math.min(2.5, Number(value || 1)));
  const distanciaEntrePontos = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

  const iniciarArrasteAvatar = (event) => {
    if (!avatarSourceFile) return;

    avatarPointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });

    if (avatarPointersRef.current.size >= 2) {
      const [p1, p2] = Array.from(avatarPointersRef.current.values());
      avatarPinchRef.current = {
        active: true,
        startDistance: distanciaEntrePontos(p1, p2),
        startZoom: avatarZoom,
      };
      avatarDragRef.current.active = false;
      setAvatarDragging(false);
      event.currentTarget.setPointerCapture?.(event.pointerId);
      return;
    }

    avatarDragRef.current = {
      active: true,
      startX: event.clientX,
      startY: event.clientY,
      startPanX: avatarPanX,
      startPanY: avatarPanY,
    };
    setAvatarDragging(true);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  };

  const moverArrasteAvatar = (event) => {
    if (avatarPointersRef.current.has(event.pointerId)) {
      avatarPointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    }

    if (avatarPointersRef.current.size >= 2) {
      const [p1, p2] = Array.from(avatarPointersRef.current.values());
      const currentDistance = distanciaEntrePontos(p1, p2);
      const baseDistance = avatarPinchRef.current.startDistance || currentDistance;
      const factor = baseDistance > 0 ? currentDistance / baseDistance : 1;
      setAvatarZoom(clampZoom(avatarPinchRef.current.startZoom * factor));
      return;
    }

    if (!avatarDragRef.current.active) return;

    const bounds = event.currentTarget.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;

    const deltaX = (event.clientX - avatarDragRef.current.startX) / bounds.width;
    const deltaY = (event.clientY - avatarDragRef.current.startY) / bounds.height;

    setAvatarPanX(clampPan(avatarDragRef.current.startPanX + (deltaX * 2)));
    setAvatarPanY(clampPan(avatarDragRef.current.startPanY + (deltaY * 2)));
  };

  const finalizarArrasteAvatar = (event) => {
    event.currentTarget.releasePointerCapture?.(event.pointerId);

    avatarPointersRef.current.delete(event.pointerId);

    if (avatarPointersRef.current.size < 2) {
      avatarPinchRef.current.active = false;
    }

    if (!avatarDragRef.current.active) return;

    avatarDragRef.current.active = false;
    setAvatarDragging(false);
  };

  const aplicarDraftAvatar = async () => {
    if (!avatarSourceFile || !token || !apiBase) return;

    try {
      setUploading(true);
      const avatarCortado = await cropSquareImage(avatarSourceFile, {
        zoom: avatarZoom,
        panX: avatarPanX,
        panY: avatarPanY,
        outSize: 720,
      });
      const url = await uploadImagem(avatarCortado, 'perfil');

      const res = await fetch(`${apiBase}/api/v1/usuarios/foto-perfil`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!res.ok) throw new Error('Falha ao atualizar foto');

      setFotoPerfil(url);
      cancelarDraftAvatar();
      onNotify?.('Foto de perfil atualizada', 'success');
    } catch (_e) {
      onNotify?.('Nao foi possivel atualizar a foto', 'error');
    } finally {
      setUploading(false);
    }
  };

  const handlePortfolio = async (event) => {
    const files = Array.from(event.target.files || []).slice(0, 8);
    if (files.length === 0 || !token || !apiBase || perfilTipo !== 'barbeiro') return;

    try {
      setUploading(true);
      for (const file of files) {
        const url = await uploadImagem(file, 'portfolio');
        const res = await fetch(`${apiBase}/api/v1/barbeiro/portfolio`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            url_imagem: url,
            tipo_servico: 'corte',
            descricao: 'Trabalho do barbeiro',
          }),
        });

        if (res.ok) {
          const novaFoto = await res.json();
          setPortfolioFotos((prev) => [novaFoto, ...prev]);
        }
      }

      onNotify?.('Fotos do portfolio adicionadas', 'success');
    } catch (_e) {
      onNotify?.('Erro ao enviar fotos do portfolio', 'error');
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const removerPortfolio = async (fotoId) => {
    if (!fotoId || !token || !apiBase) return;

    try {
      const res = await fetch(`${apiBase}/api/v1/barbeiro/portfolio/${fotoId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Falha ao remover foto');

      setPortfolioFotos((prev) => prev.filter((item) => item.id !== fotoId));
      onNotify?.('Foto removida do portfolio', 'success');
    } catch (_e) {
      onNotify?.('Nao foi possivel remover a foto', 'error');
    }
  };

  const marcarFalhaPortfolio = useCallback((fotoId) => {
    if (!fotoId) return;
    setPortfolioFalhas((prev) => (prev[fotoId] ? prev : { ...prev, [fotoId]: true }));
  }, []);

  const atualizarStatusBarbeiro = async (statusDesejado) => {
    if (perfilTipo !== 'barbeiro' || !token || !apiBase || !userId) return;

    try {
      setSaving(true);
      const payload = { status: statusDesejado };

      if (statusDesejado === 'presente') {
        const selecionada = Number(barbeariaPresencaId || 0);
        if (!selecionada) {
          onNotify?.('Selecione uma barbearia para marcar como presente', 'info');
          return;
        }
        payload.barbearia_id = selecionada;
      }

      const res = await fetch(`${apiBase}/api/v1/freelancer/${userId}/alterar-status`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || 'Nao foi possivel atualizar status');
      }

      setBarberStatus(statusDesejado);
      if (statusDesejado !== 'presente') {
        setBarbeariaPresencaId('');
      }
      onNotify?.(`Status atualizado para ${statusDesejado.toUpperCase()}`, 'success');
      await carregarPerfil();
    } catch (e) {
      onNotify?.(e?.message || 'Erro ao atualizar status', 'error');
    } finally {
      setSaving(false);
    }
  };

  const salvar = async () => {
    if (!token || !apiBase) return;

    try {
      setSaving(true);

      const perfilRes = await fetch(`${apiBase}/api/v1/usuarios/me`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nome: String(nome || '').trim(),
          email: String(email || '').trim(),
          telefone: String(telefone || '').trim(),
        }),
      });

      if (!perfilRes.ok) {
        const errData = await perfilRes.json().catch(() => ({}));
        throw new Error(errData?.detail || 'Falha ao salvar perfil');
      }

      if (perfilTipo === 'barbearia' && barbeariaId) {
        if (aumentoCadeirasPendente) {
          const metodoPlano = metodoPagamentoPlano === 'cartao' ? tipoCartaoPlano : 'pix';

          const criarRes = await fetch(`${apiBase}/api/v1/assinaturas/criar`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              cadeiras_ativas: cadeirasPlano,
              metodo_pagamento: metodoPlano,
            }),
          });

          const criarData = await criarRes.json().catch(() => ({}));
          if (!criarRes.ok) {
            throw new Error(criarData?.detail || 'Falha ao preparar cobranca das cadeiras');
          }

          if (metodoPagamentoPlano === 'cartao') {
            const errosCartao = validarCartaoBasico({
              numero: cartaoPlano.numero_cartao,
              titular: cartaoPlano.titular,
              validade: cartaoPlano.validade,
              cvv: cartaoPlano.cvv,
            });
            if (Object.keys(errosCartao).length > 0) {
              throw new Error('Preencha todos os dados do cartao corretamente');
            }

            const pagamentoCartaoRes = await fetch(`${apiBase}/api/v1/assinaturas/pagar-mensalidade`, {
              method: 'POST',
              headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                metodo_pagamento: tipoCartaoPlano,
                numero_cartao: cartaoPlano.numero_cartao,
                titular: cartaoPlano.titular,
                validade: cartaoPlano.validade,
                cvv: cartaoPlano.cvv,
              }),
            });

            const pagamentoCartaoData = await pagamentoCartaoRes.json().catch(() => ({}));
            if (!pagamentoCartaoRes.ok) {
              throw new Error(pagamentoCartaoData?.detail || 'Falha ao processar pagamento com cartao');
            }

            setPixPlano(null);
            setCartaoPlano({ numero_cartao: '', titular: '', validade: '', cvv: '' });
            setCadeirasPlanoSalvas(cadeirasPlano);
          } else {
            const pixRes = await fetch(`${apiBase}/api/v1/assinaturas/pagar-mensalidade/pix`, {
              method: 'POST',
              headers: { Authorization: `Bearer ${token}` },
            });

            const pixRaw = await pixRes.json().catch(() => ({}));
            if (!pixRes.ok) {
              throw new Error(pixRaw?.detail || 'Falha ao gerar PIX para novas cadeiras');
            }

            const pixFinal = montarPixFinalPerfil(pixRaw);
            if (!pixFinal.qrcode_base64 && !pixFinal.pix_copia_cola) {
              throw new Error('PIX gerado sem QR Code e sem codigo copia e cola');
            }
            setPixPlano(pixFinal);
          }
        } else {
          const assinaturaRes = await fetch(
            `${apiBase}/api/v1/assinatura/ativar?barbearia_id=${barbeariaId}&quantidade_cadeiras=${cadeirasPlano}`,
            {
              method: 'POST',
              headers: { Authorization: `Bearer ${token}` },
            }
          );

          if (!assinaturaRes.ok) {
            const errData = await assinaturaRes.json().catch(() => ({}));
            throw new Error(errData?.detail || 'Falha ao atualizar mensalidade por cadeiras');
          }
          setCadeirasPlanoSalvas(cadeirasPlano);
        }
      }

      await carregarPerfil();

      const payload = { nome, email, telefone, fotoPerfil, cadeirasPlano, mensalidadeTotal, userType: perfilTipo };
      if (typeof aoSalvar === 'function') aoSalvar(payload);
      if (!(aumentoCadeirasPendente && metodoPagamentoPlano === 'pix')) {
        setSaveSuccess(true);
        if (saveSuccessTimeoutRef.current) {
          clearTimeout(saveSuccessTimeoutRef.current);
        }
        saveSuccessTimeoutRef.current = setTimeout(() => {
          setSaveSuccess(false);
        }, 1800);
      }
      onNotify?.(aumentoCadeirasPendente && metodoPagamentoPlano === 'pix' ? 'Perfil salvo e PIX gerado para liberar as novas cadeiras' : 'Perfil salvo com sucesso', 'success');
    } catch (e) {
      onNotify?.(e?.message || 'Nao foi possivel salvar o perfil', 'error');
    } finally {
      setSaving(false);
    }
  };

  const confirmarPagamentoPixPlano = async () => {
    if (!token || !apiBase) return;

    try {
      setSaving(true);
      const res = await fetch(`${apiBase}/api/v1/assinaturas/pagar-mensalidade`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          metodo_pagamento: 'pix',
          confirmar_pix: true,
        }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || 'Falha ao confirmar pagamento PIX');
      }

      setPixPlano(null);
      setCadeirasPlanoSalvas(cadeirasPlano);
      setSaveSuccess(true);
      if (saveSuccessTimeoutRef.current) {
        clearTimeout(saveSuccessTimeoutRef.current);
      }
      saveSuccessTimeoutRef.current = setTimeout(() => {
        setSaveSuccess(false);
      }, 1800);
      onNotify?.(data?.message || 'Pagamento PIX confirmado com sucesso', 'success');
    } catch (e) {
      onNotify?.(e?.message || 'Nao foi possivel confirmar o PIX', 'error');
    } finally {
      setSaving(false);
    }
  };

  const copiarPixPlano = async () => {
    if (!pixPlano?.pix_copia_cola) return;
    await navigator.clipboard.writeText(pixPlano.pix_copia_cola);
    setCopiouPixPlano(true);
    window.setTimeout(() => setCopiouPixPlano(false), 1500);
    onNotify?.('Codigo PIX copiado', 'success');
  };

  const pixPlanoQrSrc = getPixQrSrcPerfil(pixPlano?.qrcode_base64);

  return (
    <ScreenWrapper>
      {mostrarCabecalho && (
        <Header title={meta.titulo} actionButton={{ icon: <LogOut size={14} />, label: 'Sair', onClick: onLogout }} />
      )}

      <AppCard className="large">
        <div className={styles.profileHeader}>
          <div className={styles.profileAvatar}>
            {avatarDraftPreview ? (
              <img src={avatarDraftPreview} alt="Preview da foto" className={styles.avatarPhoto} />
            ) : fotoPerfilResolvida ? (
              <img src={fotoPerfilResolvida} alt="Foto de perfil" className={styles.avatarPhoto} />
            ) : (
              <div className={styles.avatarInner}>{initial}</div>
            )}
          </div>
          <div className={styles.profileInfo}>
            <h2 className="card-title text-ui-lg tracking-wide">{nome || 'Usuario'}</h2>
            <div>
              <span className={styles.badge}>{meta.badge}</span>
            </div>
            {permitirEdicaoFoto && (
              <label className={styles.fileBtn}>
                <Camera size={14} />
                {uploading ? 'Enviando...' : 'Trocar foto'}
                <input type="file" accept="image/*" onChange={handleFotoPerfil} className={styles.hiddenInput} disabled={uploading} />
              </label>
            )}
            {permitirEdicaoFoto && avatarSourceFile && (
              <button
                type="button"
                className={styles.fileBtn}
                onClick={() => setAvatarEditorOpen(true)}
                disabled={uploading}
              >
                Abrir editor de recorte
              </button>
            )}
          </div>
        </div>
      </AppCard>

      {perfilTipo === 'barbeiro' && (
        <AppCard>
          <div className="space-y-3">
            <p className={styles.labelStrong}>Disponibilidade para clientes</p>
            <div className={styles.statusGrid}>
              <button type="button" onClick={() => atualizarStatusBarbeiro('offline')} className={`${styles.statusBtn} ${barberStatus === 'offline' ? styles.statusBtnActive : ''}`} disabled={saving}>Offline</button>
              <button type="button" onClick={() => atualizarStatusBarbeiro('online')} className={`${styles.statusBtn} ${barberStatus === 'online' ? styles.statusBtnActive : ''}`} disabled={saving}>Ficar online</button>
              <button type="button" onClick={() => atualizarStatusBarbeiro('presente')} className={`${styles.statusBtn} ${barberStatus === 'presente' ? styles.statusBtnActive : ''}`} disabled={saving}>Presente</button>
            </div>

            <div>
              <label className={styles.label}>Barbearia para marcar presença</label>
              <select value={barbeariaPresencaId} onChange={(e) => setBarbeariaPresencaId(e.target.value)} className={styles.input + ' mt-2'}>
                <option value="">Selecione a barbearia</option>
                {barbeariasDisponiveis.map((item) => (
                  <option key={item.id} value={item.id}>{item.nome}</option>
                ))}
              </select>
            </div>

            {barbeariaAtualNome && (
              <div className="rounded-xl border border-orange-500/30 bg-orange-500/10 p-3 text-xs text-zinc-300">
                <p className="font-bold text-orange-300 mb-1">Barbearia atual</p>
                <p className="text-sm font-bold text-white">{barbeariaAtualNome}</p>
                <p className="text-zinc-400 mt-1">{barbeariaAtualEndereco || 'Endereco nao informado'}</p>
              </div>
            )}
          </div>
        </AppCard>
      )}

      {perfilTipo === 'barbeiro' && (
        <AppCard>
          <div className="space-y-3">
            <div className={styles.sectionHeader}>
              <p className={styles.labelStrong}>Portfolio de trabalhos</p>
              <label className={styles.fileBtn}>
                <Upload size={14} />
                {uploading ? 'Enviando...' : 'Adicionar fotos'}
                <input type="file" accept="image/*" multiple onChange={handlePortfolio} className={styles.hiddenInput} disabled={uploading} />
              </label>
            </div>

            {portfolioFotos.length === 0 ? (
              <p className={styles.emptyText}>Nenhuma foto no portfolio ainda.</p>
            ) : (
              <div className={styles.portfolioGrid}>
                {portfolioFotos.map((foto) => (
                  <div key={foto.id} className={styles.portfolioItem}>
                    {portfolioFalhas[foto.id] ? (
                      <div className={`${styles.portfolioImg} flex items-center justify-center bg-black/20 px-2 text-center text-xs text-zinc-400`}>
                        Imagem indisponivel
                      </div>
                    ) : (
                      <img
                        src={resolveMediaUrl(foto.url, apiBase)}
                        alt="Portfolio"
                        className={styles.portfolioImg}
                        onError={() => marcarFalhaPortfolio(foto.id)}
                      />
                    )}
                    <button type="button" className={styles.removeBtn} onClick={() => removerPortfolio(foto.id)} aria-label="Remover foto">
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </AppCard>
      )}

      {perfilTipo !== 'barbearia' && (
        <AppCard>
          <div className="grid gap-3">
            <div>
              <label className={styles.label}>Nome Completo</label>
              <input type="text" value={nome} onChange={(e) => setNome(e.target.value)} className={styles.input + ' mt-2'} />
            </div>

            <div>
              <label className={styles.label}>E-mail cadastrado</label>
              <input type="email" value={email} disabled className={styles.input + ' mt-2'} />
            </div>

            <div>
              <label className={styles.label}>Telefone / WhatsApp</label>
              <input type="text" value={telefone} onChange={(e) => setTelefone(e.target.value)} className={styles.input + ' mt-2'} />
            </div>
          </div>
        </AppCard>
      )}

      {perfilTipo === 'barbearia' && (
        <AppCard>
          <div className="space-y-3">
            <p className={styles.labelStrong}>Plano da barbearia por cadeira</p>

            <div className={styles.counterRow}>
              <div>
                <p className={styles.counterLabel}>Quantidade de cadeiras</p>
                <p className={styles.counterValue}>{cadeirasPlano}</p>
              </div>
              <div className={styles.counterButtons}>
                <button type="button" onClick={() => setCadeirasPlano((v) => Math.max(1, v - 1))} className={styles.counterBtn}>-</button>
                <button type="button" onClick={() => setCadeirasPlano((v) => Math.min(50, v + 1))} className={styles.counterBtn}>+</button>
              </div>
              <div>
                <p className={styles.counterLabel}>Mensalidade</p>
                <p className={styles.counterMoney}>{moneyBRL(mensalidadeTotal)}</p>
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 text-xs text-zinc-300 leading-relaxed">
              <p className="font-bold text-orange-300 mb-1">Como funciona</p>
              <p className="text-zinc-400">
                A cadeira 1 é a primeira cadeira paga do plano. Quando você aumenta a quantidade, o sistema adiciona a cadeira 2, 3 e assim por diante com preço progressivo.
                Se a barbearia contratou apenas 1 cadeira, só a <strong>Cadeira 1</strong> deve ficar ativa e disponível no painel.
              </p>
            </div>

            <div className={styles.planInfoCard}>
              <p className={styles.planDesc}>Valor da cadeira atual: <strong>{moneyBRL(precoCadeiraAtual)}</strong></p>
              <p className={styles.planDesc}>Quanto mais cadeiras você ativa, maior o total mensal e com desconto progressivo por cadeira.</p>
            </div>

            {aumentoCadeirasPendente && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3">
                <p className="text-[11px] font-bold uppercase tracking-wide text-emerald-300">Novo valor ao alterar agora</p>
                <p className="mt-1 text-lg font-black text-white">+{moneyBRL(acrescimoMensalPlano)}/mês</p>
                <p className="mt-1 text-xs text-zinc-300">Seu plano vai de {moneyBRL(mensalidadeAnterior)} para {moneyBRL(mensalidadeTotal)}.</p>
              </div>
            )}

            {aumentoCadeirasPendente && (
              <div className="rounded-xl border border-emerald-600/30 bg-emerald-500/10 p-3 space-y-3">
                <div>
                  <p className="text-sm font-bold text-emerald-300">Forma de pagamento para liberar as novas cadeiras</p>
                  <p className="text-xs text-zinc-300 mt-1">Voce esta saindo de {cadeirasPlanoSalvas} para {cadeirasPlano} cadeiras. Escolha como pagar essa atualizacao.</p>
                </div>

                <div className="rounded-lg border border-orange-500/30 bg-orange-500/10 p-3">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-orange-300">Acréscimo desta mudança</p>
                  <p className="mt-1 text-lg font-black text-white">{moneyBRL(acrescimoMensalPlano)}/mês</p>
                  <p className="mt-1 text-xs text-zinc-300">Plano atual: {moneyBRL(mensalidadeAnterior)}. Novo plano: {moneyBRL(mensalidadeTotal)}.</p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      salvarMetodoPreferidoCliente?.('pix');
                      setMetodoPagamentoPlano('pix');
                    }}
                    className={`rounded px-3 py-2 text-xs font-bold border transition ${metodoPagamentoPlano === 'pix' ? 'bg-orange-600/20 border-orange-500 text-orange-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                  >
                    PIX
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      salvarMetodoPreferidoCliente?.('cartao_credito');
                      setMetodoPagamentoPlano('cartao');
                    }}
                    className={`rounded px-3 py-2 text-xs font-bold border transition ${metodoPagamentoPlano === 'cartao' ? 'bg-blue-600/20 border-blue-500 text-blue-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                  >
                    Cartao
                  </button>
                </div>

                {metodoPagamentoPlano === 'cartao' && (
                  <div className="space-y-2 rounded-lg border border-zinc-700 bg-zinc-900/60 p-3">
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setTipoCartaoPlano('cartao_credito')}
                        className={`rounded py-2 text-xs font-bold border transition ${tipoCartaoPlano === 'cartao_credito' ? 'bg-blue-600/20 border-blue-500 text-blue-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                      >
                        Credito
                      </button>
                      <button
                        type="button"
                        onClick={() => setTipoCartaoPlano('cartao_debito')}
                        className={`rounded py-2 text-xs font-bold border transition ${tipoCartaoPlano === 'cartao_debito' ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                      >
                        Debito
                      </button>
                    </div>

                    <input
                      type="text"
                      placeholder="Numero do cartao"
                      value={cartaoPlano.numero_cartao}
                      onChange={(e) => setCartaoPlano({ ...cartaoPlano, numero_cartao: e.target.value.replace(/\D/g, '').slice(0, 19) })}
                      className={styles.input}
                    />
                    <input
                      type="text"
                      placeholder="Nome no cartao"
                      value={cartaoPlano.titular}
                      onChange={(e) => setCartaoPlano({ ...cartaoPlano, titular: e.target.value.toUpperCase() })}
                      className={styles.input}
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        placeholder="MM/AA"
                        value={cartaoPlano.validade}
                        onChange={(e) => setCartaoPlano({ ...cartaoPlano, validade: e.target.value.slice(0, 5) })}
                        className={styles.input}
                      />
                      <input
                        type="text"
                        placeholder="CVV"
                        value={cartaoPlano.cvv}
                        onChange={(e) => setCartaoPlano({ ...cartaoPlano, cvv: e.target.value.replace(/\D/g, '').slice(0, 4) })}
                        className={styles.input}
                      />
                    </div>
                  </div>
                )}

                <p className="text-xs text-zinc-400">Valor total novo do plano: <strong className="text-white">{moneyBRL(mensalidadeTotal)}</strong></p>

                <button
                  type="button"
                  onClick={salvar}
                  disabled={saving}
                  className="w-full rounded-lg bg-gradient-to-r from-orange-600 to-orange-700 px-4 py-3 text-sm font-bold text-white transition hover:from-orange-700 hover:to-orange-800 disabled:from-zinc-700 disabled:to-zinc-700"
                >
                  {saving
                    ? (metodoPagamentoPlano === 'pix' ? 'Gerando PIX...' : 'Processando cartao...')
                    : (metodoPagamentoPlano === 'pix'
                      ? 'Gerar PIX agora'
                      : `Pagar agora com ${tipoCartaoPlano === 'cartao_debito' ? 'debito' : 'credito'}`)}
                </button>
              </div>
            )}

            {pixPlano && (
              <div className="rounded-xl border border-orange-500/40 bg-zinc-950/80 p-3 space-y-3">
                <p className="text-sm font-bold text-white">PIX gerado para as novas cadeiras</p>
                {pixPlanoQrSrc && !pixPlanoImagemInvalida && (
                  <div className="flex justify-center">
                    <img src={pixPlanoQrSrc} alt="QR Code PIX" className="h-40 w-40 object-contain rounded bg-zinc-900 p-2" onError={() => setPixPlanoImagemInvalida(true)} />
                  </div>
                )}
                {(pixPlanoImagemInvalida || !pixPlanoQrSrc) && pixPlanoQrFallback && (
                  <div className="flex justify-center">
                    <img src={pixPlanoQrFallback} alt="QR Code PIX" className="h-40 w-40 object-contain rounded bg-zinc-900 p-2" />
                  </div>
                )}
                <input type="text" readOnly value={pixPlano.pix_copia_cola || ''} className={styles.input} />
                <button type="button" onClick={copiarPixPlano} className="w-full rounded-lg bg-zinc-100 py-2 text-xs font-bold text-zinc-900">
                  {copiouPixPlano ? 'Copiado!' : 'Copiar codigo PIX'}
                </button>
                <button type="button" onClick={confirmarPagamentoPixPlano} disabled={saving} className="w-full rounded-lg bg-green-600 py-2 text-xs font-bold text-white disabled:opacity-60">
                  {saving ? 'Confirmando...' : 'Confirmar pagamento'}
                </button>
              </div>
            )}
          </div>
        </AppCard>
      )}

      {perfilTipo === 'barbearia' && (
        <AppCard>
          <div className="grid gap-3">
            <div>
              <label className={styles.label}>Nome Completo</label>
              <input type="text" value={nome} onChange={(e) => setNome(e.target.value)} className={styles.input + ' mt-2'} />
            </div>

            <div>
              <label className={styles.label}>E-mail cadastrado</label>
              <input type="email" value={email} disabled className={styles.input + ' mt-2'} />
            </div>

            <div>
              <label className={styles.label}>Telefone / WhatsApp</label>
              <input type="text" value={telefone} onChange={(e) => setTelefone(e.target.value)} className={styles.input + ' mt-2'} />
            </div>
          </div>
        </AppCard>
      )}

      <AppCard>
        <div className={styles.actions}>
          <button type="button" onClick={salvar} className={styles.saveBtn} disabled={saving}>
            {saving ? (
              <span className="inline-flex items-center gap-2">
                <Loader size={14} className="animate-spin" />
                {aumentoCadeirasPendente ? (metodoPagamentoPlano === 'pix' ? 'Gerando PIX...' : 'Processando cartao...') : 'Salvando...'}
              </span>
            ) : saveSuccess ? 'Salvo' : pixPlano ? 'Aguardando confirmacao do PIX' : aumentoCadeirasPendente ? (metodoPagamentoPlano === 'pix' ? 'Salvar e gerar PIX' : `Salvar e pagar com ${tipoCartaoPlano === 'cartao_debito' ? 'debito' : 'credito'}`) : 'Salvar alteracoes'}
          </button>
        </div>
      </AppCard>

      {avatarEditorOpen && avatarSourceFile && (
        <div className={styles.editorOverlay} role="dialog" aria-modal="true">
          <div className={styles.editorCard}>
            <p className={styles.labelStrong}>Recortar foto de perfil</p>
            <p className={styles.editorHint}>Use os controles para enquadrar melhor sua foto antes de aplicar.</p>

            <div className={styles.editorPreviewWrap}>
              {avatarDraftPreview ? (
                <img
                  src={avatarDraftPreview}
                  alt="Preview de recorte"
                  className={`${styles.editorPreview} ${avatarDragging ? styles.editorPreviewDragging : ''}`}
                  onPointerDown={iniciarArrasteAvatar}
                  onPointerMove={moverArrasteAvatar}
                  onPointerUp={finalizarArrasteAvatar}
                  onPointerCancel={finalizarArrasteAvatar}
                  onPointerLeave={finalizarArrasteAvatar}
                />
              ) : (
                <div className={styles.editorPlaceholder}>Gerando preview...</div>
              )}
            </div>

            <div className={styles.adjustWrap}>
              <label className={styles.label}>Zoom</label>
              <input
                type="range"
                min="1"
                max="2.5"
                step="0.1"
                value={avatarZoom}
                onChange={(e) => setAvatarZoom(Number(e.target.value))}
                className={styles.zoomRange}
              />
              <label className={styles.label}>Mover horizontal</label>
              <input
                type="range"
                min="-1"
                max="1"
                step="0.05"
                value={avatarPanX}
                onChange={(e) => setAvatarPanX(Number(e.target.value))}
                className={styles.zoomRange}
              />
              <label className={styles.label}>Mover vertical</label>
              <input
                type="range"
                min="-1"
                max="1"
                step="0.05"
                value={avatarPanY}
                onChange={(e) => setAvatarPanY(Number(e.target.value))}
                className={styles.zoomRange}
              />
              <p className={styles.editorHint}>Dica: arraste com um dedo para mover e use pinça com dois dedos para zoom.</p>
            </div>

            <div className={styles.previewActions}>
              <button type="button" onClick={aplicarDraftAvatar} className={styles.applyBtn} disabled={uploading}>
                {uploading ? 'Aplicando...' : 'Aplicar foto'}
              </button>
              <button type="button" onClick={() => setAvatarEditorOpen(false)} className={styles.cancelBtn} disabled={uploading}>
                Continuar editando depois
              </button>
              <button type="button" onClick={cancelarDraftAvatar} className={styles.cancelBtn} disabled={uploading}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </ScreenWrapper>
  );
}

export default TelaPerfilUsuario;
