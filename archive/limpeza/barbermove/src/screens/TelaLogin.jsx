import React, { useState, useEffect } from 'react';
import styles from './TelaLogin.module.css';

export default function TelaLogin() {
  const [tipoConta, setTipoConta] = useState('cliente');

  useEffect(() => {
    document.body.classList.add('no-bottom-nav');
    return () => document.body.classList.remove('no-bottom-nav');
  }, []);

  return (
    <div className={styles.shell}>
      <div className={styles.frame}>
        <div className={styles.brandArea}>
          <div className={styles.brandIcon}>
            <img src="/brand-logo.png" alt="logo" onError={(e)=>{ e.currentTarget.style.display='none'; }} />
          </div>
          <div className={styles.brandName}><span className={styles.brandWord}>Barber</span><span className={styles.brandMove}>Move</span></div>
          <div className={styles.brandSubtitle}>AGENDA E GESTÃO PROFISSIONAL</div>
        </div>

        <div className={styles.tabs} role="tablist">
          {['Cliente','Barbeiro','Barbearia'].map((t)=> (
            <button key={t} type="button" onClick={() => setTipoConta(t.toLowerCase())} className={`${styles.tab} ${tipoConta===t.toLowerCase()?styles.tabActive:''}`}>{t}</button>
          ))}
        </div>

        <form className={styles.form} onSubmit={(e)=>e.preventDefault()}>
          <input className={styles.field} placeholder="lari.nascimento20148@gmail.com" />
          <input className={styles.field} placeholder="••••••••" type="password" />

          <button className={styles.submit} type="button">Entrar na Conta</button>
        </form>
      </div>
    </div>
  );
}