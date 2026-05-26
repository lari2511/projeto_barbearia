import React from 'react';
import { User, Mail, Phone, MapPin, Lock, Eye, EyeOff, LogOut, Send, Camera, Save, X, MessageCircle } from 'lucide-react';

// Tab: Dados Pessoais do Barbeiro
export function TabDadosBarbeiro({ 
  user, 
  editing, 
  formData, 
  setFormData, 
  previewImage,
  handleImageChange,
  handleSaveProfile,
  setEditing,
  setPreviewImage,
  setPortfolioImages,
  portfolioImages,
  loading,
  changingPassword,
  setChangingPassword,
  passwordData,
  setPasswordData,
  handleChangePassword,
  showCurrentPassword,
  setShowCurrentPassword,
  showNewPassword,
  setShowNewPassword,
  handleReenviarEmail,
  onLogout
}) {
  return (
    <div className="space-y-3">
      {/* Foto de Perfil */}
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
        
        {user?.documento_verificado && (
          <div className="bg-green-600/20 border border-green-600 rounded-full px-3 py-1 flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-green-400 text-xs font-bold">✓ Verificado</span>
          </div>
        )}
        
        {/* Botão WhatsApp */}
        {user?.telefone && !editing && (
          <a
            href={`https://wa.me/55${user.telefone.replace(/\D/g, '')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-green-600 text-white px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 hover:bg-green-700 active:scale-95"
          >
            <MessageCircle size={16} />
            Contato WhatsApp
          </a>
        )}
      </div>

      {/* Formulário de Edição */}
      {editing ? (
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
              disabled={loading || portfolioImages.length < 3}
              title={portfolioImages.length < 3 ? 'Adicione no mínimo 3 fotos de portfólio' : ''}
              className="flex-1 bg-orange-500 text-white px-4 py-3 rounded-lg font-bold flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save size={18} />
              {loading ? 'Salvando...' : 'Salvar'}
            </button>
            <button
              onClick={() => {
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
                setPortfolioImages(user?.portfolio_fotos || []);
              }}
              className="flex-1 bg-zinc-800 text-white px-4 py-3 rounded-lg font-bold flex items-center justify-center gap-2 active:scale-95"
            >
              <X size={18} />
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Informações do Perfil */}
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
                {user && !user.email_verificado && (
                  <button
                    onClick={handleReenviarEmail}
                    disabled={loading}
                    className="mt-1 text-xs text-red-500 hover:text-red-400 font-bold flex items-center gap-1"
                  >
                    <Send size={12} />
                    Reenviar verificação
                  </button>
                )}
              </div>
              {user?.email_verificado && (
                <span className="text-green-500 text-xs font-bold">✓ Verificado</span>
              )}
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

            {user?.endereco && (
              <div className="flex items-center gap-3">
                <MapPin size={18} className="text-zinc-500" />
                <div className="flex-1">
                  <p className="text-xs text-zinc-500">Endereço</p>
                  <p className="text-white font-medium">{user.endereco}</p>
                </div>
              </div>
            )}

            {user?.cpf && (
              <div className="flex items-center gap-3">
                <User size={18} className="text-zinc-500" />
                <div className="flex-1">
                  <p className="text-xs text-zinc-500">CPF</p>
                  <p className="text-white font-medium">{user.cpf}</p>
                </div>
              </div>
            )}
          </div>

          {/* Trocar Senha */}
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

          {/* Sair */}
          <button
            onClick={onLogout}
            className="w-full bg-red-600/10 border border-red-600 rounded-lg p-4 flex items-center justify-center gap-2 hover:bg-red-600/20 active:scale-95"
          >
            <LogOut size={18} className="text-red-500" />
            <span className="text-red-500 font-bold">Sair da Conta</span>
          </button>
        </div>
      )}
    </div>
  );
}
