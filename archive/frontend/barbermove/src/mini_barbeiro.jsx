import React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import './theme/painel.css';
import CadeirasDisponíveisComponent from './components/CadeirasDisponíveisComponent';
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
	root.render(<CadeirasDisponíveisComponent token={token} API_URL={API_URL} notify={notify} />);
});
