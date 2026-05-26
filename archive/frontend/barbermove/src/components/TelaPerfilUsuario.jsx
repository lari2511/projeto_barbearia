import React, { useState } from 'react';
import { LogOut } from 'lucide-react';
import ScreenWrapper from './ScreenWrapper';
import AppCard from './AppCard';
import Header from './Header';
import styles from './TelaPerfilUsuario.module.css';

export function TelaPerfilUsuario({ usuario, aoSalvar, onLogout }) {
  const [nome, setNome] = useState(usuario?.nome || 'Lari Nascimento');
  const [email] = useState(usuario?.email || 'lari.nascimento20148@gmail.com');
  const [telefone, setTelefone] = useState(usuario?.telefone || '(11) 99999-9999');

  return (
    <ScreenWrapper>
      <Header title="Meu Perfil" actionButton={{ icon: <LogOut size={14} />, label: 'Sair', onClick: onLogout }} />

      <AppCard className={styles.alertCard}>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-red-300">Encerrar sessão</p>
          <p className="mt-1 text-sm text-zinc-200">Se quiser voltar para a tela inicial, toque no botão abaixo.</p>
        </div>
        <button type="button" onClick={onLogout} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl font-extrabold text-sm bg-transparent border border-red-700 text-red-300">
          <LogOut size={16} />
          Sair da conta
        </button>
      </AppCard>

      <AppCard className="large">
        <div className={styles.profileHeader}>
          <div className={styles.profileAvatar}>
            <div className={styles.avatarInner}>
              {nome.charAt(0).toUpperCase()}
            </div>
          </div>
          <div className={styles.profileInfo}>
            <h2 className="card-title text-ui-lg tracking-wide">{nome}</h2>
            <div>
              <span className={styles.badge}>Cliente Premium</span>
            </div>
          </div>
        </div>
      </AppCard>

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

          <div className={styles.actions}>
            <button onClick={() => aoSalvar && aoSalvar({ nome, telefone })} className={styles.saveBtn}>🚀 Salvar Alterações</button>
          </div>
        </div>
      </AppCard>
    </ScreenWrapper>
  );
}

export default TelaPerfilUsuario;
