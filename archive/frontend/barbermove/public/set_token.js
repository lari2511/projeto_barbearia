// Ambiente de desenvolvimento: solicita que o dev cole um token manualmente.
// Para segurança, não injetamos tokens automaticamente em ambientes compartilhados.
(function(){
	try {
		if (localStorage.getItem('token')) return;
		const token = window.prompt('Cole o token de desenvolvimento (ou cancele):');
		if (!token) return;
		const userType = window.prompt('Tipo de usuário (barbearia/barbeiro/cliente/admin):', 'barbearia') || 'barbearia';
		const userId = window.prompt('User ID (opcional):', '');
		localStorage.setItem('token', token);
		localStorage.setItem('userType', userType);
		if (userId) localStorage.setItem('userId', String(userId));
		alert('Token salvo no localStorage para esta sessão.');
	} catch (e) {
		// não bloquear o app
		console.error('set_token error', e);
	}
})();
