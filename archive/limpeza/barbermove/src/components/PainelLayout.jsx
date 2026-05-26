import React from 'react';
import '../theme/painel.css';
import BottomNav from './BottomNav';

export default function PainelLayout({ children, activeTab, setActiveTab }) {
  return (
    <div className="app-shell">
      <main className="flex-1 py-2">
        {children}
      </main>

      <BottomNav activeTab={activeTab} setActiveTab={setActiveTab} />
    </div>
  );
}
