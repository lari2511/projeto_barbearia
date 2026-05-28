(async function(){
  const API = (window.__API_URL__ || location.origin.replace(/:\d+$/, ':8000')) + '/api/v1';
  const out = document.getElementById('out');
  const log = document.getElementById('log');
  const append = (k,v)=>{log.textContent += k+': '+JSON.stringify(v,null,2)+'\n\n';};

  const getToken = ()=> localStorage.getItem('token');

  async function request(method, path, body){
    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = 'Bearer '+token;
    if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
    const res = await fetch(API+path, {method, headers, body: body && !(body instanceof FormData) ? JSON.stringify(body) : body});
    const data = await res.json().catch(()=>({}));
    return {status: res.status, ok: res.ok, data};
  }

  async function runFlow(){
    log.textContent = '';
    out.innerHTML = '';
    append('API', API);

    // 1) garantir barbearia login/token já presente
    const token = getToken();
    if (!token){
      append('error','Token nao encontrado em localStorage. Use set_token.js para colar um token dev.');
      out.innerHTML = '<b>Token nao encontrado</b>';
      return;
    }

    // 2) minha barbearia
    append('step','GET /barbearia/minha');
    let r = await request('GET','/barbearia/minha'); append('minha_barbearia', r);
    if (!r.ok){ out.innerHTML = 'Erro ao carregar barbearia: '+r.status; return; }
    const barbeariaId = r.data?.id;

    // 3) tentar gerar PIX
    append('step','POST /assinaturas/pagar-mensalidade/pix');
    r = await request('POST','/assinaturas/pagar-mensalidade/pix'); append('pagar_pix', r);

    if (r.status === 404 && /assinatura/i.test(r.data?.detail || '')){
      append('info','Criar assinatura via /assinaturas/criar');
      const criar = await request('POST','/assinaturas/criar',{cadeiras_ativas:1,metodo_pagamento:'pix'});
      append('criar_assinatura', criar);
      r = await request('POST','/assinaturas/pagar-mensalidade/pix'); append('pagar_pix_after_create', r);
    }

    if (r.ok && (r.data?.qrcode_base64 || r.data?.pix_copia_cola)){
      append('info','PIX gerado, confirmando pagamento via /assinaturas/pagar-mensalidade');
      const conf = await request('POST','/assinaturas/pagar-mensalidade',{metodo_pagamento:'pix',confirmar_pix:true}); append('confirmar', conf);
    }

    // 4) listar cadeiras
    if (barbeariaId){
      append('step','GET /cadeiras?barbearia_id='+barbeariaId);
      const cadeiras = await request('GET','/cadeiras?barbearia_id='+barbeariaId); append('cadeiras', cadeiras);
      const cadeiraId = Array.isArray(cadeiras.data) && cadeiras.data[0] && cadeiras.data[0].id;
      if (cadeiraId){
        append('step','PUT /cadeiras/{id}/liberar-para-barbeiros');
        const lib = await request('PUT','/cadeiras/'+cadeiraId+'/liberar-para-barbeiros'); append('liberar_para_barbeiros', lib);
      }
    }

    out.innerHTML = '<b>Execução concluída (ver log)</b>';
  }

  document.getElementById('run').addEventListener('click', ()=>{runFlow().catch(e=>append('fatal',String(e)))});
  document.getElementById('clear').addEventListener('click', ()=>{localStorage.clear(); location.reload();});

})();
