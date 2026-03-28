"""
Rotas para Admin Dashboard Web
Endpoints para gerenciar aprovações via interface web
Protegido por autenticação de admin
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import Usuario
from app.routes import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])

# Verificar se é admin ou barbearia (permitir ambos)
def verificar_admin(usuario = Depends(get_current_user)):
    print(f"🔍 verificar_admin - Usuário: {usuario.email}, Tipo: {usuario.tipo}")
    if usuario.tipo not in ["admin", "barbearia"]:
        print(f"❌ Acesso negado para tipo: {usuario.tipo}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado - apenas admins e barbearias"
        )
    print(f"✅ Acesso permitido para {usuario.email}")
    return usuario

# ============================================================================
# TESTE DE AUTENTICAÇÃO
# ============================================================================

@router.get("/api/test-auth")
def testar_autenticacao(admin = Depends(verificar_admin)):
    """Endpoint de teste para verificar autenticação"""
    return {
        "status": "autenticado",
        "usuario_id": admin.id,
        "email": admin.email,
        "tipo": admin.tipo
    }

# ============================================================================
# ENDPOINTS DA API
# ============================================================================

@router.get("/api/pendentes")
def listar_pendentes(
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Lista usuários pendentes de aprovação"""
    pendentes = db.query(Usuario).filter(
        Usuario.perfil_aprovado == False,
        Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
    ).order_by(Usuario.criado_em).all()
    
    return [{
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "tipo": u.tipo,
        "telefone": u.telefone,
        "rg": u.rg,
        "criado_em": u.criado_em,
        "documento_frente": bool(u.documento_frente_url),
        "documento_verso": bool(u.documento_verso_url),
        "selfie": bool(u.selfie_documento_url),
        "email_verificado": u.email_verificado,
        "documento_frente_url": u.documento_frente_url,
        "documento_verso_url": u.documento_verso_url,
        "selfie_documento_url": u.selfie_documento_url,
    } for u in pendentes]

@router.get("/api/aprovados")
def listar_aprovados(
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Lista usuários já aprovados"""
    aprovados = db.query(Usuario).filter(
        Usuario.perfil_aprovado == True,
        Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
    ).order_by(Usuario.perfil_aprovado_em.desc()).all()
    
    return [{
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "tipo": u.tipo,
        "telefone": u.telefone,
        "aprovado_em": u.perfil_aprovado_em,
    } for u in aprovados]

@router.get("/api/estatisticas")
def obter_estatisticas(
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Estatísticas gerais"""
    total_usuarios = db.query(Usuario).filter(
        Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
    ).count()
    
    aprovados = db.query(Usuario).filter(
        Usuario.perfil_aprovado == True,
        Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
    ).count()
    
    pendentes = total_usuarios - aprovados
    
    barbeiros = db.query(Usuario).filter(
        Usuario.tipo == 'barbeiro'
    ).count()
    
    clientes = db.query(Usuario).filter(
        Usuario.tipo == 'cliente'
    ).count()
    
    barbearias = db.query(Usuario).filter(
        Usuario.tipo == 'barbearia'
    ).count()
    
    return {
        "total": total_usuarios,
        "aprovados": aprovados,
        "pendentes": pendentes,
        "barbeiros": barbeiros,
        "clientes": clientes,
        "barbearias": barbearias,
    }

@router.get("/api/usuario/{usuario_id}")
def obter_usuario_detalhes(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Retorna detalhes completos do usuário (documentos, portfólio, etc)"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Buscar portfólio se barbeiro
    portfolio = []
    if usuario.tipo == 'barbeiro' and hasattr(usuario, 'portfolio'):
        portfolio = [
            {
                "id": p.id,
                "foto_url": p.foto_url,
                "descricao": p.descricao
            } for p in usuario.portfolio
        ]
    
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "tipo": usuario.tipo,
        "telefone": usuario.telefone,
        "rg": usuario.rg,
        "criado_em": usuario.criado_em,
        "documento_frente": usuario.documento_frente_url,
        "documento_verso": usuario.documento_verso_url,
        "selfie": usuario.selfie_documento_url,
        "portfolio": portfolio,
        "aprovado": usuario.perfil_aprovado,
        "aprovado_em": usuario.perfil_aprovado_em,
    }

@router.post("/api/aprovar/{usuario_id}")
def aprovar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin),
    background_tasks = None
):
    """Aprova um usuário e envia email de confirmação"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if usuario.perfil_aprovado:
        raise HTTPException(status_code=400, detail="Usuário já aprovado")
    
    usuario.perfil_aprovado = True
    usuario.perfil_aprovado_em = datetime.now()
    db.commit()
    
    # Enviar email de aprovação em background
    if background_tasks:
        from app.email_send import send_perfil_approved_email
        background_tasks.add_task(
            send_perfil_approved_email,
            usuario.email,
            usuario.nome,
            usuario.tipo
        )
    
    return {"status": "aprovado", "usuario_id": usuario.id}

@router.post("/api/rejeitar/{usuario_id}")
def rejeitar_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Rejeita um usuário"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Deletar usuário
    db.delete(usuario)
    db.commit()
    
    return {"status": "rejeitado", "usuario_id": usuario_id}

@router.get("/api/buscar")
def buscar_usuario(
    q: str = "",
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Buscar usuário por email ou nome"""
    if not q or len(q) < 2:
        return []
    
    usuarios = db.query(Usuario).filter(
        (Usuario.email.ilike(f"%{q}%")) | (Usuario.nome.ilike(f"%{q}%")),
        Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
    ).limit(10).all()
    
    return [{
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "tipo": u.tipo,
        "aprovado": u.perfil_aprovado,
    } for u in usuarios]

# ============================================================================
# PÁGINA HTML DO DASHBOARD
# ============================================================================

@router.get("/", response_class=HTMLResponse)
def dashboard_page():
    """Página do dashboard admin - com login integrado"""
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Panel - BarberMovie</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);
                color: #fff;
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            
            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 1px solid #333;
            }
            h1 { font-size: 28px; font-weight: bold; }
            .logout-btn {
                background: #ef4444;
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: bold;
            }
            .logout-btn:hover { background: #dc2626; }
            
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
            }
            .stat-number { font-size: 32px; font-weight: bold; color: #f97316; }
            .stat-label { font-size: 12px; color: #9ca3af; margin-top: 5px; }
            
            .tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                border-bottom: 1px solid #333;
            }
            .tab-btn {
                background: transparent;
                border: none;
                color: #9ca3af;
                padding: 12px 20px;
                cursor: pointer;
                font-weight: bold;
                border-bottom: 3px solid transparent;
                transition: all 0.3s;
            }
            .tab-btn.active {
                color: #f97316;
                border-bottom-color: #f97316;
            }
            .tab-btn:hover { color: #d4d4d8; }
            
            .search-box {
                margin-bottom: 20px;
            }
            .search-box input {
                width: 100%;
                padding: 12px 15px;
                background: #1f2937;
                border: 1px solid #374151;
                border-radius: 8px;
                color: #fff;
                font-size: 14px;
            }
            .search-box input:focus {
                outline: none;
                border-color: #f97316;
                box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.1);
            }
            
            .users-list {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .user-card {
                background: #1f2937;
                border: 1px solid #374151;
                border-radius: 8px;
                padding: 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                transition: all 0.3s;
            }
            .user-card:hover { border-color: #f97316; }
            
            .user-info h3 { font-size: 16px; margin-bottom: 5px; }
            .user-info p { font-size: 12px; color: #9ca3af; }
            .user-badge {
                display: inline-block;
                background: #3b82f6;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 10px;
                margin-right: 8px;
                font-weight: bold;
            }
            .user-badge.barbeiro { background: #8b5cf6; }
            .user-badge.cliente { background: #06b6d4; }
            .user-badge.barbearia { background: #10b981; }
            
            .user-actions {
                display: flex;
                gap: 8px;
            }
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
            }
            .btn-approve {
                background: #10b981;
                color: white;
            }
            .btn-approve:hover { background: #059669; }
            
            .btn-reject {
                background: #ef4444;
                color: white;
            }
            .btn-reject:hover { background: #dc2626; }
            
            .loading {
                text-align: center;
                padding: 40px;
                color: #9ca3af;
            }
            .empty-state {
                text-align: center;
                padding: 40px;
                color: #6b7280;
            }
            .empty-state p { font-size: 14px; margin-bottom: 10px; }
            .empty-state .emoji { font-size: 48px; margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🔧 Admin Dashboard</h1>
                <button class="logout-btn" onclick="logout()">Sair</button>
            </header>
            
            <!-- ESTATÍSTICAS -->
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="total">-</div>
                    <div class="stat-label">Total de Usuários</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="pendentes">-</div>
                    <div class="stat-label">Pendentes de Aprovação</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="aprovados">-</div>
                    <div class="stat-label">Aprovados</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="barbeiros">-</div>
                    <div class="stat-label">Barbeiros</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="clientes">-</div>
                    <div class="stat-label">Clientes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="barbearias">-</div>
                    <div class="stat-label">Barbearias</div>
                </div>
            </div>
            
            <!-- ABAS -->
            <div class="tabs">
                <button class="tab-btn active" onclick="mudarAba('pendentes')">⏳ Pendentes</button>
                <button class="tab-btn" onclick="mudarAba('aprovados')">✅ Aprovados</button>
            </div>
            
            <!-- BUSCA -->
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 Buscar por email ou nome..." onkeyup="buscar()">
            </div>
            
            <!-- LISTA DE USUÁRIOS -->
            <div class="users-list" id="usersList">
                <div class="loading">Carregando...</div>
            </div>
        </div>
        
        <script>
            const API_URL = "/admin/api";
            let token = localStorage.getItem('token');
            let abaAtual = 'pendentes';
            
            // Mostrar login se não tiver token
            if (!token) {
                mostrarLogin();
            } else {
                carregarDados();
            }
            
            function mostrarLogin() {
                document.querySelector('.container').innerHTML = `
                    <div style="max-width: 400px; margin: 100px auto; background: #1f2937; padding: 40px; border-radius: 12px; border: 1px solid #374151;">
                        <h2 style="text-align: center; margin-bottom: 30px;">🔐 Login Admin</h2>
                        <form onsubmit="fazerLogin(event)">
                            <div style="margin-bottom: 20px;">
                                <label style="display: block; margin-bottom: 8px; color: #9ca3af; font-size: 14px;">Email</label>
                                <input type="email" id="email" required 
                                    style="width: 100%; padding: 12px; background: #111827; border: 1px solid #374151; border-radius: 8px; color: #fff; font-size: 14px;"
                                    placeholder="admin@barbermovie.local">
                            </div>
                            <div style="margin-bottom: 30px;">
                                <label style="display: block; margin-bottom: 8px; color: #9ca3af; font-size: 14px;">Senha</label>
                                <input type="password" id="senha" required 
                                    style="width: 100%; padding: 12px; background: #111827; border: 1px solid #374151; border-radius: 8px; color: #fff; font-size: 14px;"
                                    placeholder="••••••••">
                            </div>
                            <button type="submit" 
                                style="width: 100%; padding: 14px; background: #f97316; border: none; border-radius: 8px; color: #fff; font-weight: bold; font-size: 16px; cursor: pointer;">
                                Entrar
                            </button>
                            <p id="erro" style="color: #ef4444; text-align: center; margin-top: 15px; font-size: 14px;"></p>
                        </form>
                    </div>
                `;
            }
            
            async function fazerLogin(e) {
                e.preventDefault();
                const email = document.getElementById('email').value;
                const senha = document.getElementById('senha').value;
                const erro = document.getElementById('erro');
                
                try {
                    const formData = new URLSearchParams();
                    formData.append('username', email);
                    formData.append('password', senha);
                    
                    // Tentar login em múltiplos endpoints (admin ou barbearia)
                    const endpoints = ['/api/v1/login/admin/', '/api/v1/login/barbearia/'];
                    let sucesso = false;
                    
                    for (const endpoint of endpoints) {
                        const res = await fetch('http://' + window.location.hostname + ':8000' + endpoint, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                            body: formData
                        });
                        
                        if (res.ok) {
                            const data = await res.json();
                            localStorage.setItem('token', data.access_token);
                            token = data.access_token;
                            location.reload();
                            sucesso = true;
                            break;
                        }
                    }
                    
                    if (!sucesso) {
                        erro.textContent = 'Email ou senha incorretos, ou sem permissão de admin';
                    }
                } catch (err) {
                    erro.textContent = 'Erro ao conectar - verifique se o backend está rodando';
                    console.error(err);
                }
            }
            
            async function carregarDados() {
                try {
                    // Estatísticas
                    const statsRes = await fetch(API_URL + '/estatisticas', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    const stats = await statsRes.json();
                    
                    document.getElementById('total').textContent = stats.total;
                    document.getElementById('pendentes').textContent = stats.pendentes;
                    document.getElementById('aprovados').textContent = stats.aprovados;
                    document.getElementById('barbeiros').textContent = stats.barbeiros;
                    document.getElementById('clientes').textContent = stats.clientes;
                    document.getElementById('barbearias').textContent = stats.barbearias;
                    
                    // Usuários
                    carregarUsuarios();
                } catch (err) {
                    console.error('Erro:', err);
                }
            }
            
            async function carregarUsuarios() {
                const endpoint = abaAtual === 'pendentes' ? '/pendentes' : '/aprovados';
                const usersList = document.getElementById('usersList');
                
                try {
                    const res = await fetch(API_URL + endpoint, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    const usuarios = await res.json();
                    
                    if (usuarios.length === 0) {
                        usersList.innerHTML = `
                            <div class="empty-state">
                                <div class="emoji">${abaAtual === 'pendentes' ? '✨' : '🎉'}</div>
                                <p>${abaAtual === 'pendentes' ? 'Nenhum usuário pendente!' : 'Nenhum usuário aprovado!'}</p>
                            </div>
                        `;
                        return;
                    }
                    
                    usersList.innerHTML = usuarios.map(u => `
                        <div class="user-card">
                            <div class="user-info">
                                <div>
                                    <span class="user-badge ${u.tipo}">${u.tipo.toUpperCase()}</span>
                                    <h3>${u.nome}</h3>
                                </div>
                                <p>📧 ${u.email}</p>
                                <p>📞 ${u.telefone || 'Sem telefone'}</p>
                                ${abaAtual === 'pendentes' ? `
                                    <p style="margin-top: 8px; color: #fbbf24;">
                                        📄 Documentos: 
                                        ${u.documento_frente ? '✅' : '❌'} 
                                        ${u.documento_verso ? '✅' : '❌'} 
                                        ${u.selfie ? '✅' : '❌'}
                                    </p>
                                ` : ''}
                            </div>
                            <div class="user-actions">
                                ${abaAtual === 'pendentes' ? `
                                    <button class="btn btn-approve" onclick="aprovar(${u.id})">✅ Aprovar</button>
                                    <button class="btn btn-reject" onclick="rejeitar(${u.id})">❌ Rejeitar</button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('');
                } catch (err) {
                    usersList.innerHTML = '<div class="loading">Erro ao carregar</div>';
                }
            }
            
            function mudarAba(aba) {
                abaAtual = aba;
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                event.target.classList.add('active');
                carregarUsuarios();
            }
            
            async function aprovar(usuarioId) {
                if (!confirm('Confirmar aprovação?')) return;
                
                try {
                    const res = await fetch(API_URL + `/aprovar/${usuarioId}`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    if (res.ok) {
                        alert('✅ Usuário aprovado!');
                        carregarDados();
                    }
                } catch (err) {
                    alert('❌ Erro ao aprovar');
                }
            }
            
            async function rejeitar(usuarioId) {
                if (!confirm('Confirmar rejeição?')) return;
                
                try {
                    const res = await fetch(API_URL + `/rejeitar/${usuarioId}`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    if (res.ok) {
                        alert('❌ Usuário rejeitado!');
                        carregarDados();
                    }
                } catch (err) {
                    alert('❌ Erro ao rejeitar');
                }
            }
            
            async function buscar() {
                const q = document.getElementById('searchInput').value;
                if (!q) {
                    carregarUsuarios();
                    return;
                }
                
                try {
                    const res = await fetch(API_URL + `/buscar?q=${encodeURIComponent(q)}`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    const usuarios = await res.json();
                    
                    const usersList = document.getElementById('usersList');
                    if (usuarios.length === 0) {
                        usersList.innerHTML = '<div class="empty-state"><p>Nenhum resultado</p></div>';
                        return;
                    }
                    
                    usersList.innerHTML = usuarios.map(u => `
                        <div class="user-card">
                            <div class="user-info">
                                <div>
                                    <span class="user-badge ${u.tipo}">${u.tipo.toUpperCase()}</span>
                                    <h3>${u.nome}</h3>
                                </div>
                                <p>📧 ${u.email}</p>
                                <span style="color: ${u.aprovado ? '#10b981' : '#f97316'}">
                                    ${u.aprovado ? '✅ Aprovado' : '⏳ Pendente'}
                                </span>
                            </div>
                        </div>
                    `).join('');
                } catch (err) {
                    console.error('Erro na busca:', err);
                }
            }
            
            function logout() {
                localStorage.clear();
                window.location.href = '/';
            }
            
            // Carregar ao iniciar
            carregarDados();
            setInterval(carregarDados, 30000); // Atualizar a cada 30s
        </script>
    </body>
    </html>
    """
