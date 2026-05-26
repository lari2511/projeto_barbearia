import React from 'react';

export default function BottomNav({ activeTab, setActiveTab }) {
  return (
    <nav className="bottom-nav">
      <button className={`nav-item ${activeTab === 'inicio' ? 'active' : ''}`} onClick={() => setActiveTab && setActiveTab('inicio')}>
        <span className="nav-icon">🏠</span>
        <span>Início</span>
      </button>
      <button className={`nav-item ${activeTab === 'chamados' ? 'active' : ''}`} onClick={() => setActiveTab && setActiveTab('chamados')}>
        <span className="nav-icon">📋</span>
        <span>Chamados</span>
      </button>
      <button className={`nav-item ${activeTab === 'atendimentos' ? 'active' : ''}`} onClick={() => setActiveTab && setActiveTab('atendimentos')}>
        <span className="nav-icon">💈</span>
        <span>Atendimentos</span>
      </button>
      <button className={`nav-item ${activeTab === 'carteira' ? 'active' : ''}`} onClick={() => setActiveTab && setActiveTab('carteira')}>
        <span className="nav-icon">💳</span>
        <span>Carteira</span>
      </button>
      <button className={`nav-item ${activeTab === 'perfil' ? 'active' : ''}`} onClick={() => setActiveTab && setActiveTab('perfil')}>
        <span className="nav-icon">👤</span>
        <span>Perfil</span>
      </button>
    </nav>
  );
}
