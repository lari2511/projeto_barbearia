import json
import urllib.request
import urllib.error
import urllib.parse

API = 'http://127.0.0.1:8000'

def post(path, data=None, token=None):
    url = API + path
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {'detail': str(e)}
    except Exception as e:
        return None, {'detail': str(e)}

def login_form(path, email, senha):
    url = API + path
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    body = urllib.parse.urlencode({'username': email, 'password': senha}).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {'detail': str(e)}
    except Exception as e:
        return None, {'detail': str(e)}

def request_any(method, path, data=None, token=None):
    url = API + path
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = None
    if data is not None:
        headers['Content-Type'] = 'application/json'
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {'detail': str(e)}
    except Exception as e:
        return None, {'detail': str(e)}

def get(path, token=None):
    url = API + path
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {'detail': str(e)}
    except Exception as e:
        return None, {'detail': str(e)}

if __name__ == '__main__':
    out = {}

    # Login barbearia (form)
    code, data = login_form('/api/v1/login/barbearia/', 'barbearia@test.com', 'senha123')
    out['login_barbearia'] = {'status': code, 'data': data}
    token_b = data.get('access_token') if isinstance(data, dict) else None

    # Get minha barbearia
    code, data = get('/api/v1/barbearia/minha', token=token_b)
    out['minha_barbearia'] = {'status': code, 'data': data}
    barbearia_id = data.get('id') if isinstance(data, dict) else None

    # Assinatura: try gerar PIX
    code, data = post('/api/v1/assinaturas/pagar-mensalidade/pix', None, token_b)
    out['pagar_pix_first'] = {'status': code, 'data': data}

    if code == 404 and isinstance(data, dict) and ('nenhuma assinatura' in (data.get('detail') or '').lower() or 'sem_assinatura' in (data.get('detail') or '').lower()):
        # criar assinatura
        code_c, data_c = post('/api/v1/assinaturas/criar', {'cadeiras_ativas': 1, 'metodo_pagamento': 'pix'}, token_b)
        out['criar_assinatura'] = {'status': code_c, 'data': data_c}
        # tentar gerar pix novamente
        code, data = post('/api/v1/assinaturas/pagar-mensalidade/pix', None, token_b)
        out['pagar_pix_second'] = {'status': code, 'data': data}

    # If we have a pix, confirm it (simulate pago)
    if isinstance(data, dict) and (data.get('qrcode_base64') or data.get('pix_copia_cola')):
        code_conf, data_conf = post('/api/v1/assinaturas/pagar-mensalidade', {'metodo_pagamento': 'pix', 'confirmar_pix': True}, token_b)
        out['confirmar_pix'] = {'status': code_conf, 'data': data_conf}

    # List chairs
    if barbearia_id:
        code, data = get(f'/api/v1/cadeiras?barbearia_id={barbearia_id}', token_b)
        out['cadeiras_list'] = {'status': code, 'data': data}
        cadeira_id = None
        if isinstance(data, list) and len(data) > 0:
            cadeira_id = data[0].get('id')
        elif isinstance(data, dict) and data.get('cadeiras'):
            cadeira_id = data['cadeiras'][0].get('id') if data['cadeiras'] else None

        if cadeira_id:
            # Liberar para barbeiros (prefer PUT) - se falhar, tenta /liberar (POST)
            code_lib, data_lib = request_any('PUT', f'/api/v1/cadeiras/{cadeira_id}/liberar-para-barbeiros', None, token_b)
            out['liberar_para_barbeiros'] = {'status': code_lib, 'data': data_lib}
            if code_lib != 200:
                code_lib2, data_lib2 = post(f'/api/v1/cadeiras/{cadeira_id}/liberar', {'motivo': 'Liberado via teste E2E'}, token_b)
                out['liberar_fallback'] = {'status': code_lib2, 'data': data_lib2}

            # Login barbeiro (form)
            code2, data2 = login_form('/api/v1/login/barbeiro/', 'barbeiro@test.com', 'senha123')
            out['login_barbeiro'] = {'status': code2, 'data': data2}
            token_bb = data2.get('access_token') if isinstance(data2, dict) else None

            # Barbeiro aceitar cadeira
            code_acc, data_acc = post(f'/api/v1/cadeiras/{cadeira_id}/aceitar', None, token_bb)
            out['barbeiro_aceitar'] = {'status': code_acc, 'data': data_acc}

    print(json.dumps(out, ensure_ascii=False, indent=2))
