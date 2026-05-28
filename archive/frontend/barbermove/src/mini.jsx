import React from 'react';
import { createRoot } from 'react-dom/client';
import AssinaturaPage from './components/AssinaturaPage';
import { getApiBaseUrl } from './utils/api';

const token = localStorage.getItem('token') || '';
const API_URL = getApiBaseUrl();
const notify = (msg, type) => { console.log(type||'info', msg); try{ if(type!=='info') alert(msg); }catch(_){} };

async function ensureBarbearia() {
	if (!token) return;
	try {
		await fetch(`${API_URL}/api/v1/barbearia/minha`, { headers: { 'Authorization': `Bearer ${token}` } });
	} catch (_e) {}
}

ensureBarbearia().finally(() => {
	const root = createRoot(document.getElementById('root'));
	root.render(<AssinaturaPage token={token} notify={notify} />);
});
