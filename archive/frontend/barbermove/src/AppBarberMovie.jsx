// App Principal - BarberMovie
import React from 'react';
import { AppProvider, useApp } from './contexts/AppContext';
import Login from './components/Login';
import FreelancerDashboard from './components/FreelancerDashboard';
import { Toast } from './components/Common';
import './index.css';

function AppContent() {
  const { token, userType } = useApp();

  if (!token || !userType) {
    return <Login onLoginSuccess={() => {}} />;
  }

  // Renderizar dashboard baseado no tipo de usuário
  if (userType === 'barbeiro') {
    return <FreelancerDashboard />;
  }

  // TODO: Implementar dashboards de cliente e barbearia
  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4">
      <div className="text-center">
        <h1 className="text-2xl font-black mb-4">Dashboard {userType}</h1>
        <p className="text-zinc-500">Em desenvolvimento...</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
      <ToastContainer />
    </AppProvider>
  );
}

function ToastContainer() {
  const { toast } = useApp();
  
  return toast ? <Toast message={toast.message} type={toast.type} /> : null;
}
