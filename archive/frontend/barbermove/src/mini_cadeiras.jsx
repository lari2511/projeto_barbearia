import React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import './theme/painel.css';
import LiberarCadeirasComponent from './components/LiberarCadeirasComponent';
import { getApiBaseUrl } from './utils/api';

const token = localStorage.getItem('token') || '';
const API_URL = getApiBaseUrl();
const notify = (msg, type='info') => { console.log(type, msg); };

async function ensureBarbearia() {
	if (!token) return;
	try {
		await fetch(`${API_URL}/api/v1/barbearia/minha`, { headers: { 'Authorization': `Bearer ${token}` } });
	} catch (_e) {}
}

ensureBarbearia().finally(() => {
	const root = createRoot(document.getElementById('root'));
	root.render(<LiberarCadeirasComponent token={token} API_URL={API_URL} notify={notify} barbeariaId={2} />);
});
