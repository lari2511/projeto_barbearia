import React, { useState } from 'react';

export default function TelaLogin({
  API_URL,
  BRAND_LOGO,
  notify,
  saveLogin,
  setShowTerms,
  setShowPrivacy,
}) {
  const [isLogin, setIsLogin] = useState(true);
  const [activeTab, setActiveTab] = useState('cliente');
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    senha: '',
    nome: '',
    endereco: '',
    cep: '',
    telefone: '',
    cpf: '',
    cnpj: '',
  });
  const [docFiles, setDocFiles] = useState({ frente: null, verso: null, selfie: null });
  const [portfolioFiles, setPortfolioFiles] = useState([]);
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState('');

  const inputClass = 'login-input';

  const validateForm = () => {
    if (!formData.email.includes('@')) throw new Error('Email inválido');
    if ((formData.senha || '').length < 6) throw new Error('Senha precisa ter 6 caracteres ou mais');
    if (!isLogin && (formData.nome || '').trim().length < 3) throw new Error('Informe o nome completo');
    if (!isLogin && activeTab !== 'cliente' && (formData.endereco || '').trim().length < 5) throw new Error('Endereço obrigatório para barbearia');
    if (!isLogin && activeTab !== 'cliente' && (formData.cep || '').trim().length < 5) throw new Error('CEP obrigatório para barbearia');
    if (!isLogin && formData.telefone && formData.telefone.replace(/\D/g, '').length < 10) throw new Error('Telefone com DDD obrigatório');
  };

  const formatApiError = (data) => {
    if (!data) return 'Erro na requisição';
    const detail = data.detail ?? data.message ?? data.error;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map(d => d?.msg || d?.detail || d?.message || JSON.stringify(d)).join(' | ');
    if (typeof detail === 'object') return detail.msg || detail.detail || detail.message || JSON.stringify(detail);
    if (typeof data === 'string') return data;
    return JSON.stringify(data);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setFormError('');

    try {
      validateForm();

      if (!isLogin && (activeTab === 'barbeiro' || activeTab === 'barbearia')) {
        if (!docFiles.frente || !docFiles.verso || !docFiles.selfie) {
          throw new Error('Envie os 3 documentos: frente, verso e selfie');
        }
      }

      if (!isLogin && activeTab === 'barbeiro') {
        if (portfolioFiles.length < 3) {
          throw new Error('Envie no mínimo 3 fotos com você ao lado do corte para aprovação');
        }
      }

      const endpoint = isLogin
        ? `login/${activeTab}/`
        : `${activeTab === 'cliente' ? 'clientes' : activeTab === 'barbeiro' ? 'barbeiros' : 'barbearias'}/`;
      const payload = isLogin
        ? { email: formData.email, senha: formData.senha }
        : {
            nome: formData.nome,
            email: formData.email,
            senha: formData.senha,
            endereco: formData.endereco,
            cep: formData.cep || undefined,
            telefone: formData.telefone,
            cpf: formData.cpf || undefined,
            cnpj: formData.cnpj || undefined,
          };

      const res = await fetch(`${API_URL}/api/v1/${endpoint}`, {
        method: 'POST',
        headers: isLogin
          ? { 'Content-Type': 'application/x-www-form-urlencoded' }
          : { 'Content-Type': 'application/json' },
        body: isLogin
          ? new URLSearchParams({ username: formData.email, password: formData.senha })
          : JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) throw new Error(formatApiError(data));

      if (isLogin) {
        saveLogin(activeTab, data.access_token, data.user_id);
        notify('Bem-vindo!', 'success');
      } else {
        if ((activeTab === 'barbeiro' || activeTab === 'barbearia') && docFiles.frente && docFiles.verso && docFiles.selfie) {
          try {
            const formDataDocs = new FormData();
            formDataDocs.append('documento_frente', docFiles.frente);
            formDataDocs.append('documento_verso', docFiles.verso);
            formDataDocs.append('selfie_documento', docFiles.selfie);

            const docRes = await fetch(`${API_URL}/api/v1/documentos/upload-files`, {
              method: 'POST',
              headers: { 'Authorization': `Bearer ${data.access_token}` },
              body: formDataDocs,
            });

            if (!docRes.ok) {
              const errData = await docRes.json();
              notify('Aviso: ' + (errData.detail || 'Documentos não foram salvos'), 'error');
            } else {
              await docRes.json();
              notify('Documentos enviados para análise!', 'success');
            }
          } catch (_docErr) {
            notify('Erro ao enviar documentos', 'error');
          }
        }

        if (activeTab === 'barbeiro' && portfolioFiles.length > 0) {
          try {
            for (let i = 0; i < portfolioFiles.length; i++) {
              const file = portfolioFiles[i];
              const formDataPortfolio = new FormData();
              formDataPortfolio.append('file', file);
              formDataPortfolio.append('pasta', 'portfolio');

              const portRes = await fetch(`${API_URL}/api/v1/upload/imagem`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${data.access_token}` },
                body: formDataPortfolio,
              });

              if (portRes.ok) {
                const portData = await portRes.json();
                await fetch(`${API_URL}/api/v1/barbeiro/portfolio`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${data.access_token}`,
                  },
                  body: JSON.stringify({
                    url_imagem: portData.url,
                    tipo_servico: 'corte',
                    descricao: 'Portfólio de cadastro',
                  }),
                });
              }
            }
          } catch (_portErr) {
            // Erro ao fazer upload de portfólio
          }
        }

        notify('Conta criada! Faça login.', 'success');
        setIsLogin(true);
        setDocFiles({ frente: null, verso: null, selfie: null });
        setPortfolioFiles([]);
      }
    } catch (err) {
      const message = err.message === 'Failed to fetch'
        ? `Erro de conexão com API - Verifique se o celular está na mesma rede Wi-Fi (${API_URL})`
        : (err.message || 'Erro inesperado');
      setFormError(message);
      notify(message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-shell flex flex-col items-center justify-center min-h-screen p-3 sm:p-6 text-white animate-in fade-in overflow-y-auto">
      <style>{`
        .login-shell { background: #121212; }
        .login-shell .phone-frame {
          width: min(380px, calc(100vw - 24px));
          min-height: min(720px, calc(100vh - 24px));
          background: #000;
          border: 12px solid #000;
          border-radius: 36px;
          padding: 20px;
          display: flex;
          flex-direction: column;
          align-items: center;
          position: relative;
          overflow: hidden;
          box-shadow: 0 18px 42px rgba(0,0,0,0.45);
        }
        .login-shell .logo-container { text-align: center; margin-bottom: 30px; }
        .login-shell .brand-icon {
          width: 65px;
          height: 65px;
          background: #fff;
          margin: 0 auto 15px auto;
          display: flex;
          justify-content: center;
          align-items: center;
          overflow: hidden;
        }
        .login-shell .brand-icon img { width: 100%; object-fit: cover; display: block; }
        .login-shell .brand-name {
          color: #fff;
          font-size: 28px;
          font-weight: 700;
          letter-spacing: 0.5px;
          line-height: 1;
          text-shadow: 1px 1px 0px #000000;
        }
        .login-shell .brand-name span { color: #f57c00; font-weight: 800; letter-spacing: -0.5px; }
        .login-shell .brand-subtitle {
          color: #757575;
          font-size: 11px;
          letter-spacing: 1.5px;
          margin-top: 5px;
          text-transform: uppercase;
        }
        .login-shell .login-tabs {
          background: #121212;
          border: 1px solid #222;
          width: 100%;
          padding: 6px;
          border-radius: 14px;
          display: flex;
          justify-content: space-between;
          gap: 0;
          margin-bottom: 35px;
          box-sizing: border-box;
        }
        .login-shell .login-tab {
          flex: 1;
          background: none !important;
          border: none !important;
          color: #616161 !important;
          padding: 12px 0;
          font-size: 14px;
          font-weight: 700;
          cursor: pointer;
          border-radius: 10px;
          transition: background 0.2s ease, color 0.2s ease;
          min-height: 44px;
        }
        .login-shell .login-tab-active { background: #2a2a2a !important; color: #fff !important; }
        .login-shell .login-form { width: 100%; display: flex; flex-direction: column; gap: 16px; }
        .login-shell .login-input {
          width: 100%;
          height: 55px;
          background: #e8f0fe !important;
          border: none;
          border-radius: 14px;
          padding: 0 20px;
          font-size: 15px;
          color: #000 !important;
          outline: none;
          box-sizing: border-box;
        }
        .login-shell .login-input::placeholder { color: #111; opacity: 0.85; }
        .login-shell .login-submit {
          width: 100%;
          height: 55px;
          background: #fff !important;
          color: #000 !important;
          border: none !important;
          border-radius: 14px;
          font-size: 16px;
          font-weight: 700;
          cursor: pointer;
          margin-top: 10px;
          transition: background-color 0.2s ease;
        }
        .login-shell .login-submit:hover { background: #e0e0e0 !important; }
        .login-shell .login-toggle {
          display: inline-block;
          background: none !important;
          color: #71717a !important;
          transition: color 0.2s ease;
        }
        .login-shell .login-toggle:hover,
        .login-shell .login-link:hover { color: #d4d4d8 !important; }
        .login-shell .login-body { width: 100%; max-width: 100%; }
      `}</style>
      <div className="phone-frame">
      <div className="login-body">
      <div className="logo-container">
        <div className="brand-icon">
            <img
              src={BRAND_LOGO}
              alt="BarberMove"
              style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
              onError={(e) => e.currentTarget.style.display = 'none'}
            />
          </div>
        <h1 className="brand-name">
          Barber<span>Move</span>
        </h1>
        <p className="brand-subtitle">AGENDA E GESTÃO PROFISSIONAL</p>
      </div>

      <div className="login-tabs">
        {['cliente', 'barbeiro', 'barbearia'].map(t => (
          <button
            key={t}
            type="button"
            onClick={() => setActiveTab(t)}
            className={`login-tab capitalize ${activeTab === t ? 'login-tab-active' : ''}`}
          >
            {t}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="login-form w-full">
        {!isLogin && <input name="nome" placeholder="Nome Completo" className={`${inputClass} login-input`} value={formData.nome} onChange={e => setFormData({ ...formData, nome: e.target.value })} required />}
        {!isLogin && <input name="telefone" placeholder="Telefone com DDD" className={`${inputClass} login-input`} value={formData.telefone} onChange={e => setFormData({ ...formData, telefone: e.target.value })} />}
        {!isLogin && (activeTab === 'cliente' || activeTab === 'barbeiro') && (
          <input
            name="cpf"
            placeholder="CPF (opcional)"
            className={`${inputClass} login-input`}
            value={formData.cpf}
            maxLength="14"
            onChange={e => {
              let value = e.target.value.replace(/\D/g, '');
              if (value.length <= 11) {
                value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
              }
              setFormData({ ...formData, cpf: value });
              e.target.value = value;
            }}
          />
        )}
        {!isLogin && activeTab === 'barbearia' && (
          <>
            <input
              name="cpf"
              placeholder="CPF do Dono (opcional)"
              className={`${inputClass} login-input`}
              value={formData.cpf}
              maxLength="14"
              onChange={e => {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length <= 11) {
                  value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
                }
                setFormData({ ...formData, cpf: value });
                e.target.value = value;
              }}
            />
            <input
              name="cnpj"
              placeholder="CNPJ da Empresa (opcional)"
              className={`${inputClass} login-input`}
              value={formData.cnpj}
              maxLength="18"
              onChange={e => {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length <= 14) {
                  value = value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
                }
                setFormData({ ...formData, cnpj: value });
                e.target.value = value;
              }}
            />
          </>
        )}
        {!isLogin && activeTab !== 'cliente' && (
          <>
            <input
              name="cep"
              placeholder="CEP (ex: 12345-678)"
              className={`${inputClass} login-input`}
              value={formData.cep}
              onChange={async (e) => {
                let value = e.target.value.replace(/\D/g, '');
                setFormData({ ...formData, cep: value });

                if (value.length === 8) {
                  const cepFormatted = value.replace(/(\d{5})(\d{3})/, '$1-$2');
                  try {
                    const res = await fetch(`https://viacep.com.br/ws/${value}/json/`);
                    const data = await res.json();
                    if (!data.erro) {
                      const endereco = `${data.logradouro}, ${data.bairro} - ${data.localidade}, ${data.uf}`;
                      setFormData(prev => ({ ...prev, cep: cepFormatted, endereco }));
                    }
                  } catch (_err) {
                    // Erro ao buscar CEP
                  }
                }
              }}
              required
            />
            <input
              name="endereco"
              placeholder="Endereço da Loja/Base"
              className={`${inputClass} login-input`}
              value={formData.endereco}
              onChange={e => setFormData({ ...formData, endereco: e.target.value })}
              required
            />
          </>
        )}
        <input
          name="email"
          type="email"
          placeholder="Email"
          className={inputClass}
          value={formData.email}
          onChange={e => {
            const v = e.target.value;
            setFormData({ ...formData, email: v });
            setFieldErrors(prev => ({ ...prev, email: v.includes('@') ? '' : 'Email inválido' }));
            setFormError('');
            if (topAlert === 'Field required') setTopAlert('');
          }}
          required
          autoFocus
        />

        <div className="relative">
          <input
            name="senha"
            type={showPassword ? 'text' : 'password'}
            placeholder="Senha"
            className={`${inputClass} pr-12`}
            value={formData.senha}
            onChange={e => {
              const v = e.target.value;
              setFormData({ ...formData, senha: v });
              setFieldErrors(prev => ({ ...prev, senha: v.length >= 6 ? '' : 'Senha precisa ter 6 caracteres ou mais' }));
              setFormError('');
              if (topAlert === 'Field required') setTopAlert('');
            }}
            required
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-400 hover:text-zinc-200"
            aria-label={showPassword ? 'Esconder senha' : 'Mostrar senha'}
          >
            {showPassword ? 'Ocultar' : 'Mostrar'}
          </button>
        </div>
        {fieldErrors.email && <p className="text-xs text-red-400 mt-1">{fieldErrors.email}</p>}
        {fieldErrors.senha && <p className="text-xs text-red-400 mt-1">{fieldErrors.senha}</p>}

        {!isLogin && (activeTab === 'barbeiro' || activeTab === 'barbearia') && (
          <div className="bg-zinc-900/50 p-3 rounded-2xl border border-zinc-800 mt-4">
            <p className="text-yellow-400 text-xs font-bold mb-3">📄 Envie seus documentos (obrigatório)</p>
            <div className="space-y-2">
              <label className="text-xs text-zinc-400 block">Frente do RG/CNH:</label>
              <input
                type="file"
                accept="image/*"
                className="login-input w-full bg-black border border-zinc-800 rounded-xl py-3 px-4 text-white text-xs file:mr-3 file:bg-zinc-800 file:text-white file:border-0 file:rounded file:px-3 file:py-1"
                onChange={e => setDocFiles({ ...docFiles, frente: e.target.files?.[0] || null })}
              />

              <label className="text-xs text-zinc-400 block mt-2">Verso do RG/CNH:</label>
              <input
                type="file"
                accept="image/*"
                className="login-input w-full bg-black border border-zinc-800 rounded-xl py-3 px-4 text-white text-xs file:mr-3 file:bg-zinc-800 file:text-white file:border-0 file:rounded file:px-3 file:py-1"
                onChange={e => setDocFiles({ ...docFiles, verso: e.target.files?.[0] || null })}
              />

              <label className="text-xs text-zinc-400 block mt-2">Selfie com o documento:</label>
              <input
                type="file"
                accept="image/*"
                className="login-input w-full bg-black border border-zinc-800 rounded-xl py-3 px-4 text-white text-xs file:mr-3 file:bg-zinc-800 file:text-white file:border-0 file:rounded file:px-3 file:py-1"
                onChange={e => setDocFiles({ ...docFiles, selfie: e.target.files?.[0] || null })}
              />
            </div>
          </div>
        )}

        {!isLogin && activeTab === 'barbeiro' && (
          <div className="bg-zinc-900/50 p-3 rounded-2xl border border-zinc-800 mt-4">
            <p className="text-orange-400 text-xs font-bold mb-3">⭐ Portfólio (obrigatório)</p>
            <p className="text-zinc-400 text-xs mb-3">Envie no mínimo 3 fotos com você ao lado do corte para aprovação</p>
            <div className="space-y-2">
              <label className="text-xs text-zinc-400 block">Fotos do corte/trabalho (mínimo 3, máximo 10):</label>
              <div className="flex gap-2 mb-2 flex-wrap">
                {portfolioFiles.map((file, idx) => (
                  <div key={idx} className="text-xs bg-zinc-800 px-2 py-1 rounded flex items-center gap-2">
                    <span>{file.name}</span>
                    <button
                      type="button"
                      onClick={() => setPortfolioFiles(portfolioFiles.filter((_, i) => i !== idx))}
                      className="text-red-400 hover:text-red-500"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              {portfolioFiles.length < 10 && (
                <input
                  type="file"
                  accept="image/*"
                  className="login-input w-full bg-black border border-zinc-800 rounded-xl py-3 px-4 text-white text-xs file:mr-3 file:bg-zinc-800 file:text-white file:border-0 file:rounded file:px-3 file:py-1"
                  onChange={e => {
                    const file = e.target.files?.[0];
                    if (file && portfolioFiles.length < 10) {
                      setPortfolioFiles([...portfolioFiles, file]);
                    } else if (portfolioFiles.length >= 10) {
                      notify('Máximo de 10 fotos no portfólio', 'error');
                    }
                  }}
                />
              )}
              <p className="text-zinc-500 text-[10px]">Você adicionou {portfolioFiles.length} foto(s)</p>
            </div>
          </div>
        )}

        <button disabled={loading} className="login-submit w-full py-4 rounded-xl font-bold mt-4 active:scale-95 transition-all disabled:opacity-50">
          {loading ? 'Processando...' : (isLogin ? 'Entrar na Conta' : 'Criar Nova Conta')}
        </button>
      </form>

      <div className="mt-6 text-center">
        <button type="button" onClick={() => setIsLogin(!isLogin)} className="login-toggle text-xs text-zinc-500 hover:text-zinc-300 transition-all">
          {isLogin ? 'Não tem uma conta? Cadastre-se' : 'Já possui conta? Faça login'}
        </button>
        <p className="mt-4 text-[10px] text-zinc-500">Sua conta será validada com email e senha fortes.</p>
        {formError && <p className="mt-2 text-xs text-red-400">{formError}</p>}
        <div className="login-link-list mt-4 flex flex-col items-center gap-1 text-[11px]">
          <span onClick={() => setShowTerms(true)} className="login-link text-xs text-zinc-500 hover:text-zinc-300 transition-all">Termos de Uso</span>
          <span onClick={() => setShowPrivacy(true)} className="login-link text-xs text-zinc-500 hover:text-zinc-300 transition-all">Política de Privacidade</span>
        </div>
      </div>
      </div>
      </div>
    </div>
  );
}