// Contexto de autenticação e estado global do BarberMovie
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

const AppContext = createContext();

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
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [userType, setUserType] = useState(localStorage.getItem('userType'));
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const fetchUserData = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/${userType}/meu-perfil`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setUser(data);
      }
    } catch (_error) {
      // Erro ao buscar dados do usuário
    }
  }, [token, userType]);

  // Verificar se tem token ao carregar
  useEffect(() => {
    if (token && userType) {
      fetchUserData();
    }
  }, [fetchUserData, token, userType]);

  const login = async (email, senha, tipo) => {
    setLoading(true);
    try {
      const body = new URLSearchParams({ username: email, password: senha });
      
      const response = await fetch(`${API_URL}/api/v1/login/${tipo}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body
      });

      if (!response.ok) {
        let detail = `Erro ${response.status}: Email ou senha incorretos`;
        try {
          const error = await response.json();
          detail = toReadableString(error);
        } catch (_) {
          // Não conseguiu parsear erro JSON
        }
        throw new Error(detail);
      }

      const data = await response.json();
      
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('userType', tipo);
      localStorage.setItem('userId', data.user_id);
      
      setToken(data.access_token);
      setUserType(tipo);
      
      await fetchUserData();
      
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
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.clear();
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
      const error = await response.json();
      throw new Error(error.detail || 'Erro na requisição');
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
    logout,
    notify,
    apiRequest,
    setLoading,
    fetchUserData,
    API_URL
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};
