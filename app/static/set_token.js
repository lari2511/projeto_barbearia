// Ambiente de desenvolvimento: solicita que o dev cole um token manualmente.
// Para segurança, não injetamos tokens automaticamente em ambientes compartilhados.
(function(){
	try {
		if (localStorage.getItem('token')) return;

		// 1) permitir setar via query params: ?dev_token=...&dev_user=barbeiro
		try {
			const params = new URLSearchParams(window.location.search || '');
			const urlToken = params.get('dev_token') || params.get('token');
			const urlUser = params.get('dev_user') || params.get('userType');
			const urlUserId = params.get('dev_user_id') || params.get('userId');
			if (urlToken) {
				localStorage.setItem('token', urlToken);
				if (urlUser) localStorage.setItem('userType', urlUser);
				if (urlUserId) localStorage.setItem('userId', String(urlUserId));
				console.info('Dev token set from URL params');
				return;
			}
		} catch (e) {}

		// 2) tentar usar prompt quando disponível, mas não bloquear se não for suportado
		try {
			if (typeof window.prompt === 'function') {
				const token = window.prompt('Cole o token de desenvolvimento (ou cancele):');
				if (token) {
					const userType = typeof window.prompt === 'function' ? window.prompt('Tipo de usuário (barbearia/barbeiro/cliente/admin):', 'barbearia') || 'barbearia' : 'barbearia';
					const userId = typeof window.prompt === 'function' ? window.prompt('User ID (opcional):', '') : '';
					localStorage.setItem('token', token);
					localStorage.setItem('userType', userType);
					if (userId) localStorage.setItem('userId', String(userId));
					console.info('Token salvo no localStorage para esta sessão.');
				}
				return;
			}
		} catch (e) {
			console.warn('prompt() não disponível, usando banner de inserção de token');
		}

		// 3) fallback: criar um banner não-bloqueante para colar o token manualmente
		const banner = document.createElement('div');
		banner.style.position = 'fixed';
		banner.style.left = '8px';
		banner.style.right = '8px';
		banner.style.top = '8px';
		banner.style.zIndex = '99999';
		banner.style.background = 'linear-gradient(90deg, rgba(86,28,187,0.95), rgba(255,111,0,0.95))';
		banner.style.color = '#fff';
		banner.style.padding = '10px';
		banner.style.borderRadius = '12px';
		banner.style.boxShadow = '0 6px 20px rgba(0,0,0,0.6)';
		banner.style.fontFamily = 'sans-serif';
		banner.innerHTML = '<div style="display:flex;gap:8px;align-items:center"><input id="bm-dev-token" placeholder="Cole o token de desenvolvimento" style="flex:1;padding:8px;border-radius:8px;border:none;outline:none"/><input id="bm-dev-usertype" placeholder="Tipo (barbearia)" style="width:160px;padding:8px;border-radius:8px;border:none;outline:none" value="barbearia"/><button id="bm-dev-save" style="background:#fff;color:#000;padding:8px 10px;border-radius:8px;border:none;font-weight:700">Salvar</button><button id="bm-dev-close" style="margin-left:6px;background:transparent;border:1px solid rgba(255,255,255,0.3);color:#fff;padding:8px 10px;border-radius:8px">Fechar</button></div>';
		document.addEventListener('DOMContentLoaded', function(){
			document.body.appendChild(banner);
			document.getElementById('bm-dev-save').addEventListener('click', function(){
				const t = document.getElementById('bm-dev-token').value.trim();
				const u = document.getElementById('bm-dev-usertype').value.trim() || 'barbearia';
				if (!t) { console.warn('Nenhum token fornecido'); return; }
				localStorage.setItem('token', t);
				localStorage.setItem('userType', u);
				console.info('Token salvo no localStorage para esta sessão.');
				banner.parentNode && banner.parentNode.removeChild(banner);
			});
			document.getElementById('bm-dev-close').addEventListener('click', function(){ banner.parentNode && banner.parentNode.removeChild(banner); });
		});

	} catch (e) {
		console.error('set_token error', e);
	}
})();
