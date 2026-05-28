import React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import './theme/painel.css';
import CadeirasDisponíveisComponent from './components/CadeirasDisponíveisComponent';
import Header from './components/Header';
import { getApiBaseUrl } from './utils/api';

const token = localStorage.getItem('token') || '';
const API_URL = getApiBaseUrl();
const notify = (msg, type='info') => { console.log(type, msg); try{ alert(msg);}catch(_){}};

async function ensureBarbearia() {
	if (!token) return;
	try {
		await fetch(`${API_URL}/api/v1/barbearia/minha`, { headers: { 'Authorization': `Bearer ${token}` } });
	} catch (_e) {}
}

ensureBarbearia().finally(() => {
		const root = createRoot(document.getElementById('root'));
		root.render(
			<div className="min-h-screen bg-black text-white flex justify-center bm-app-frame">
				<div className="w-full max-w-[430px] min-h-screen p-4 bm-shell-content app-container client-dashboard-shell">
					<Header title={<><span className="mr-2">✨</span>Cadeiras Disponíveis</>} actionButton={{ label: 'Atualizar', onClick: () => window.location.reload() }} />
					<CadeirasDisponíveisComponent token={token} API_URL={API_URL} notify={notify} />
				</div>
			</div>
		);
});
