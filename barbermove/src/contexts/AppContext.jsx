// Contexto de autenticação e estado global do BarberMove
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getApiBaseUrl } from '../utils/api';

const API_URL = getApiBaseUrl();
const FRONTEND_CRASH_ENDPOINT = `${API_URL}/api/v1/notificacoes/frontend-crash`;

const storage = {
  get(key, fallback = null) {
    try {
      const value = localStorage.getItem(key);
      return value ?? fallback;
    } catch (_error) {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch (_error) {
      return false;
    }
  },
  clear() {
    try {
      localStorage.clear();
      return true;
    } catch (_error) {
      return false;
    }
  },
};

function normalizeUserType(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function isAdminType(value) {
  const normalized = normalizeUserType(value);
  return normalized === 'admin' || normalized === 'adm' || normalized === 'administrador' || normalized.includes('admin');
}

// Função auxiliar para converter QUALQUER coisa para string legível
function toReadableString(value) {
  if (value === null || value === undefined) return 'Erro desconhecido';
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return String(value);
  if (typeof value === 'boolean') return String(value);
  
  if (Array.isArray(value)) {
    return value
      .map(v => toReadableString(v))
      .filter(s => s && s !== 'Erro desconhecido')
      .join('; ') || 'Erro desconhecido';
  }
  
  if (typeof value === 'object') {
    // Prioridade: detail > message > msg > desc > error > description
    if (value.detail !== undefined) return toReadableString(value.detail);
    if (value.message !== undefined) return toReadableString(value.message);
    if (value.msg !== undefined) return toReadableString(value.msg);
    if (value.desc !== undefined) return toReadableString(value.desc);
    if (value.error !== undefined) return toReadableString(value.error);
    if (value.description !== undefined) return toReadableString(value.description);
    
    // Se nenhum desses, tenta toString
    const str = String(value);
    if (str !== '[object Object]') return str;
  }
  
  return 'Erro desconhecido';
}

async function safeReadJson(response) {
  if (!response) return null;
  const contentType = response.headers?.get?.('content-type') || '';
  if (!contentType.includes('application/json')) return null;

  try {
    return await response.json();
  } catch (_error) {
    return null;
  }
}

export const AppContext = createContext();

// eslint-disable-next-line react-refresh/only-export-components
export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp deve ser usado dentro de AppProvider');
  }
  return context;
};

export const AppProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(storage.get('token'));
  const [userType, setUserType] = useState(storage.get('userType'));
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const crashReportRef = React.useRef({ lastKey: '', lastSentAt: 0 });
  const authTokenRef = React.useRef(token);
  const pushSetupRef = React.useRef({ initialized: false, listeners: [] });

  const isNativeApp = typeof window !== 'undefined' && (
    window.location.protocol === 'capacitor:' ||
    window.location.protocol === 'ionic:' ||
    window.Capacitor?.isNativePlatform?.() === true
  );

  useEffect(() => {
    const tipoAtual = storage.get('userType') || userType || '';
    if (!isAdminType(tipoAtual)) return;

    storage.clear();
    setToken(null);
    setUserType(null);
    setUser(null);
    notify('Perfil admin foi removido deste app. Use o painel web administrativo.', 'info');
  }, [userType]);

  const reportFrontendCrash = useCallback(async (payload) => {
    const message = toReadableString(payload?.mensagem || payload?.message || 'Erro desconhecido');
    if (!message || message === 'Erro desconhecido') return;

    const now = Date.now();
    const key = `${payload?.contexto || 'global'}|${message}`;
    if (crashReportRef.current.lastKey === key && (now - crashReportRef.current.lastSentAt) < 5000) {
      return;
    }

    crashReportRef.current = { lastKey: key, lastSentAt: now };

    try {
      await fetch(FRONTEND_CRASH_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          origem: 'frontend',
          contexto: payload?.contexto || 'global',
          mensagem: message,
          stack: payload?.stack || null,
          url: typeof window !== 'undefined' ? window.location.href : null,
          user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
          user_type: userType || null,
          extra: payload?.extra || null,
        }),
      });
    } catch (_error) {
      // Silencioso: não deve gerar cascata de erro ao reportar o próprio crash.
    }
  }, [token, userType]);

  const fetchUserData = useCallback(async (overrideToken = token, overrideType = userType) => {
    if (!overrideToken || !overrideType) {
      return;
    }

    if (overrideType !== 'barbearia') {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/v1/barbearia/minha`, {
        headers: { 'Authorization': `Bearer ${overrideToken}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setUser(data);
      }
    } catch (_error) {
      // Erro ao buscar dados do usuário
    }
  }, [token, userType]);

  const sincronizarDeviceToken = useCallback(async (jwtToken, deviceToken) => {
    if (!jwtToken || !deviceToken) {
      return false;
    }

    const tokenAnterior = storage.get('deviceToken');
    const endpoint = tokenAnterior && tokenAnterior !== deviceToken
      ? '/api/v1/firebase/renovar-token'
      : '/api/v1/firebase/registrar-token';

    const payload = tokenAnterior && tokenAnterior !== deviceToken
      ? { token_antigo: tokenAnterior, token_novo: deviceToken }
      : { device_token: deviceToken, tipo_dispositivo: 'android' };

    try {
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${jwtToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorPayload = await safeReadJson(response);
        throw new Error(toReadableString(errorPayload) || `Falha ${response.status} ao registrar push`);
      }

      storage.set('deviceToken', deviceToken);
      return true;
    } catch (error) {
      reportFrontendCrash({
        contexto: 'push-sync',
        mensagem: error,
        extra: { endpoint },
      });
      return false;
    }
  }, [reportFrontendCrash]);

  const configurarPushNativo = useCallback(async (jwtToken) => {
    if (!isNativeApp || !jwtToken) {
      return;
    }

    authTokenRef.current = jwtToken;

    try {
      const { PushNotifications } = await import('@capacitor/push-notifications');

      if (!pushSetupRef.current.initialized) {
        const registrationListener = await PushNotifications.addListener('registration', async (tokenInfo) => {
          await sincronizarDeviceToken(authTokenRef.current, tokenInfo?.value);
        });

        const errorListener = await PushNotifications.addListener('registrationError', (error) => {
          reportFrontendCrash({
            contexto: 'push-registration',
            mensagem: error,
          });
        });

        pushSetupRef.current = {
          initialized: true,
          listeners: [registrationListener, errorListener],
        };
      }

      let permissao = await PushNotifications.checkPermissions();
      if (permissao.receive !== 'granted') {
        permissao = await PushNotifications.requestPermissions();
      }

      if (permissao.receive === 'granted') {
        await PushNotifications.register();
      }
    } catch (error) {
      reportFrontendCrash({
        contexto: 'push-bootstrap',
        mensagem: error,
      });
    }
  }, [isNativeApp, reportFrontendCrash, sincronizarDeviceToken]);

  // Verificar se tem token ao carregar
  useEffect(() => {
    if (token && userType) {
      fetchUserData(token, userType);
    }
  }, [fetchUserData, token, userType]);

  useEffect(() => {
    authTokenRef.current = token;

    if (!token) {
      return undefined;
    }

    configurarPushNativo(token);

    return undefined;
  }, [configurarPushNativo, token]);

  const login = async (email, senha, tipo) => {
    setLoading(true);
    try {
      const normalizedEmail = String(email || '').trim().toLowerCase();
      const body = new URLSearchParams({ username: normalizedEmail, password: senha });
      
      const response = await fetch(`${API_URL}/api/v1/login/${tipo}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body
      });

      if (!response.ok) {
        let detail = `Erro ${response.status}: Email ou senha incorretos`;
        try {
          const error = await safeReadJson(response);
          detail = toReadableString(error);
        } catch (_) {
          // Não conseguiu parsear erro JSON
        }
        throw new Error(detail);
      }

      const data = (await safeReadJson(response)) || {};

      const dataJson = data || {};

      // Priorizar o tipo/role retornado pelo backend quando disponível
      const serverType = (
        dataJson.user?.tipo_usuario ||
        dataJson.usuario?.tipo_usuario ||
        dataJson.user_type ||
        dataJson.tipo_usuario ||
        dataJson.role ||
        tipo
      );

      if (isAdminType(serverType)) {
        storage.clear();
        setToken(null);
        setUserType(null);
        setUser(null);
        throw new Error('Perfil admin foi removido do app. Use o painel web administrativo.');
      }

      storage.set('token', dataJson.access_token);
      storage.set('userType', serverType);
      storage.set('userId', dataJson.user_id);

      setToken(dataJson.access_token);
      setUserType(serverType);

      setUser({
        id: dataJson.user_id,
        tipo: serverType,
        email: normalizedEmail,
      });

      await fetchUserData(dataJson.access_token, serverType);

      // Garantir que a barbearia existe/vinculada ao usuário (cria se necessário)
      if (tipo === 'barbearia') {
        try {
          await fetch(`${API_URL}/api/v1/barbearia/minha`, {
            headers: { 'Authorization': `Bearer ${data.access_token}` }
          });
        } catch (_err) {
          // Não bloquear o fluxo de login por falha nessa chamada
        }
      }
      
      notify('✅ Login realizado com sucesso!', 'success');
      return true;
    } catch (error) {
      let msg = 'Erro desconhecido ao fazer login';
      
      // Tenta extrair mensagem de diferentes tipos de erro
      if (error instanceof Error) {
        msg = error.message || msg;
      } else if (typeof error === 'string') {
        msg = error;
      } else if (error && typeof error === 'object') {
        msg = toReadableString(error);
      }
      
      // Garante que nunca fica [object Object]
      if (msg.includes('[object Object]')) {
        msg = 'Email ou senha incorretos. Tente novamente.';
      }
      
      notify(`❌ ${msg}`, 'error');
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  };

  const register = async (tipo, payload) => {
    setLoading(true);
    try {
      const endpoints = {
        cliente: '/api/v1/clientes/',
        barbeiro: '/api/v1/barbeiros/',
        barbearia: '/api/v1/barbearias/',
      };

      const endpoint = endpoints[tipo];
      if (!endpoint) {
        throw new Error('Tipo de cadastro inválido');
      }

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let detail = `Erro ${response.status}: não foi possível concluir o cadastro`;
        try {
          const error = await safeReadJson(response);
          detail = toReadableString(error);
        } catch (_) {
          // Não conseguiu ler o detalhe do erro
        }
        throw new Error(detail);
      }

      const dataJson = (await safeReadJson(response)) || {};
      const userData = dataJson.usuario || dataJson.user || null;

      // Priorizar o tipo/role retornado pelo backend quando disponível
      const serverType = (
        dataJson.usuario?.tipo_usuario ||
        dataJson.user?.tipo_usuario ||
        dataJson.user_type ||
        dataJson.tipo_usuario ||
        dataJson.role ||
        tipo
      );

      if (isAdminType(serverType)) {
        storage.clear();
        setToken(null);
        setUserType(null);
        setUser(null);
        throw new Error('Perfil admin foi removido do app. Use o painel web administrativo.');
      }

      storage.set('token', dataJson.access_token);
      storage.set('userType', serverType);
      if (userData?.id) {
        storage.set('userId', String(userData.id));
      }

      setToken(dataJson.access_token);
      setUserType(serverType);
      setUser(userData ? { ...userData, tipo: serverType } : { ...payload, tipo: serverType });

      if (tipo === 'barbearia') {
        await fetchUserData(dataJson.access_token, tipo);
      }

      notify('✅ Cadastro realizado com sucesso!', 'success');
      return dataJson;
    } catch (error) {
      let msg = 'Erro desconhecido ao cadastrar';

      if (error instanceof Error) {
        msg = error.message || msg;
      } else if (typeof error === 'string') {
        msg = error;
      } else if (error && typeof error === 'object') {
        msg = toReadableString(error);
      }

      notify(`❌ ${msg}`, 'error');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    storage.clear();
    setToken(null);
    setUserType(null);
    setUser(null);
    notify('Logout realizado', 'info');
  };

  const notify = (message, type = 'info') => {
    // Garante ABSOLUTO que message é string legível
    const msg = toReadableString(message);
    setToast({ message: msg, type, id: Date.now() });
    setTimeout(() => setToast(null), 5000);
  };

  useEffect(() => {
    const emitirErroGlobal = (mensagem, tipo = 'error') => {
      const texto = toReadableString(mensagem);
      if (!texto || texto === 'Erro desconhecido') return;
      notify(texto, tipo);
    };

    const onUnhandledRejection = (event) => {
      const detalhe = event?.reason?.message || event?.reason || 'Falha assíncrona inesperada';
      reportFrontendCrash({
        contexto: 'unhandledrejection',
        mensagem: detalhe,
        stack: event?.reason?.stack || null,
        extra: {
          reason_type: typeof event?.reason,
        },
      });
      emitirErroGlobal(detalhe, 'error');
    };

    const onWindowError = (event) => {
      const detalhe = event?.error?.message || event?.message || 'Erro inesperado na interface';
      reportFrontendCrash({
        contexto: 'window.error',
        mensagem: detalhe,
        stack: event?.error?.stack || null,
        extra: {
          filename: event?.filename || null,
          lineno: event?.lineno || null,
          colno: event?.colno || null,
        },
      });
      emitirErroGlobal(detalhe, 'error');
    };

    window.addEventListener('unhandledrejection', onUnhandledRejection);
    window.addEventListener('error', onWindowError);

    return () => {
      window.removeEventListener('unhandledrejection', onUnhandledRejection);
      window.removeEventListener('error', onWindowError);
    };
  }, [reportFrontendCrash]);

  const apiRequest = async (endpoint, options = {}) => {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await safeReadJson(response);
      throw new Error(error?.detail || 'Erro na requisição');
    }

    return response.json();
  };

  const value = {
    user,
    token,
    userType,
    loading,
    toast,
    login,
    register,
    logout,
    notify,
    apiRequest,
    setLoading,
    fetchUserData,
    API_URL
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};
