# --- ARQUIVO: app/main.py ---
# Ponto de entrada: Configura o App e inclui as rotas

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

# Carrega variáveis do .env
load_dotenv()

from .routes import router  # Importa as rotas do arquivo routes.py
from .routes_extras import router as router_extras  # Importa rotas extras
from .routes_documentos import router as router_documentos  # Importa rotas de documentos
from .routes_disponibilidade import router as router_disponibilidade  # Rotas de disponibilidade on-demand
from .routes_relatorio import router as router_relatorio  # Rotas de relatório de ganhos
from .routes_servicos import router as router_servicos  # Rotas de gerenciamento de serviços
from .routes_pagamentos import router as router_pagamentos  # Rotas de pagamentos
from .routes_saques import router as router_saques  # 💰 Rotas de saques e transferências
from .routes_mensalidade import router as router_mensalidade  # 💵 Rotas de mensalidade progressiva
from .routes_freelancer import router as router_freelancer  # Rotas de freelancers (BarberMovie)
from .routes_cadeiras import router as router_cadeiras  # Rotas de cadeiras (BarberMovie)
from .routes_assinaturas import router as router_assinaturas  # Rotas de assinaturas por cadeira
from .routes_avaliacoes import router as router_avaliacoes  # Rotas de avaliações (BarberMovie)
from .routes_admin_avaliacoes import router as router_admin_avaliacoes  # 🛡️ Gerenciamento admin de avaliações
from .routes_barbearias import router as router_barbearias  # Rotas de barbearias com filtro de proximidade
from .routes_notificacoes import router as router_notificacoes  # 🔴 Rotas de notificações
from .routes_precos import router as router_precos  # 🔴 Rotas de preços customizados
from .routes_analytics import router as router_analytics  # 🔴 Rotas de analytics e avaliações
from .admin_routes import router as router_admin  # Dashboard web do admin
from .routes_legais import router as router_legais  # Rotas de termos e privacidade
from .routes_fixes import router as router_fixes  # Rotas de correções (email verification, cadeiras, avaliacoes)
from .routes_aprovacoes import router as router_aprovacoes  # Rotas de aprovação bidirecional
from .routes_freelancer_status import router as router_freelancer_status  # Sistema de status freelancer (OFFLINE/ONLINE/PRESENTE)
from .routes_geo_checkin import router as router_geo_checkin  # Sistema de check-in automático por geolocalização
from .routes_assinatura import router as router_assinatura  # 💰 Cálculo de mensalidades e gerenciamento de assinaturas
from .routes_transacoes import router as router_transacoes  # 💰 Rastreamento financeiro (Cortes, Transações, Assinaturas)
from .routes_firebase import router as router_firebase  # 🔔 Gerenciamento de Firebase Cloud Messaging (FCM tokens)
from .routes_on_demand import router as router_on_demand  # 📍 Sistema On-Demand com geolocalização (estilo Uber)
from .routes_pagamento_perfis import router as router_pagamento_perfis  # 💳 Conta do barbeiro e split admin
from .realtime import realtime_manager
from .database import Base, engine, init_db
from sqlalchemy import text
from starlette.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

# Evento de lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    pass

app = FastAPI(title="BarberMove API", lifespan=lifespan)

# Configuração CORS - Lê do .env
cors_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5175").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui todas as rotas definidas em routes.py
app.include_router(router, prefix="/api/v1")
app.include_router(router_extras, prefix="/api/v1")
app.include_router(router_documentos, prefix="/api/v1/documentos")
app.include_router(router_disponibilidade, prefix="/api/v1")
app.include_router(router_relatorio, prefix="/api/v1")
app.include_router(router_servicos, prefix="/api/v1")
app.include_router(router_pagamentos, prefix="/api/v1")
app.include_router(router_saques, prefix="/api/v1")  # 💰 Saques e transferências
app.include_router(router_mensalidade)  # 💵 Mensalidade progressiva
# Novas rotas BarberMovie
app.include_router(router_freelancer)
app.include_router(router_cadeiras)
app.include_router(router_assinaturas, prefix="/api/v1")  # Assinaturas por cadeira
app.include_router(router_avaliacoes)
app.include_router(router_barbearias)
app.include_router(router_notificacoes)  # 🔴 Notificações
app.include_router(router_precos)  # 🔴 Preços customizados
app.include_router(router_analytics)  # 🔴 Analytics
app.include_router(router_admin)  # Dashboard admin web
app.include_router(router_fixes, prefix="/api/v1")  # Rotas de correções
app.include_router(router_aprovacoes, prefix="/api/v1")  # Aprovações bidirecional
app.include_router(router_freelancer_status)  # Sistema de status freelancer
app.include_router(router_geo_checkin)  # 📍 Check-in automático por geolocalização
app.include_router(router_assinatura)  # 💰 Assinatura e cálculo de mensalidades
app.include_router(router_transacoes)  # 💰 Rastreamento financeiro
app.include_router(router_firebase)  # 🔔 Firebase Cloud Messaging
app.include_router(router_on_demand)  # 📍 On-Demand com geolocalização
app.include_router(router_admin_avaliacoes)  # 🛡️ Gerenciamento admin de avaliações e bloqueios
app.include_router(router_pagamento_perfis)  # 💳 Configurações de pagamento
# Rotas legais (Termos e Privacidade)
app.include_router(router_legais, prefix="/api/v1")

# Monta arquivos estáticos para download de APKs (porta 8000)
if os.path.exists("barbermove"):
    app.mount("/download", StaticFiles(directory="barbermove"), name="download")

# Monta uploads de imagens (perfil, portfólio, etc.)
uploads_dir = pathlib.Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# WebSocket simples para notificacoes (evita 403 quando o front conecta)
@app.websocket("/ws/notificacoes")
async def websocket_notificacoes(websocket: WebSocket):
    await realtime_manager.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        realtime_manager.disconnect(websocket)
    except Exception:
        realtime_manager.disconnect(websocket)
        try:
            await websocket.close()
        except Exception:
            pass

# Endpoint dedicado para baixar APK com cabeçalho correto
@app.get("/apk/latest")
def download_latest_apk():
    base_dir = "barbermove"
    if not os.path.isdir(base_dir):
        raise HTTPException(status_code=404, detail="Diretório de downloads não encontrado")
    apks = [f for f in os.listdir(base_dir) if f.lower().endswith(".apk")]
    if not apks:
        raise HTTPException(status_code=404, detail="Nenhum APK disponível")
    latest = max(apks, key=lambda f: os.path.getmtime(os.path.join(base_dir, f)))
    path = os.path.join(base_dir, latest)
    return FileResponse(
        path,
        media_type="application/vnd.android.package-archive",
        filename=latest
    )

@app.get("/apk/{filename}")
def download_apk(filename: str):
    path = os.path.join("barbermove", filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(
        path,
        media_type="application/vnd.android.package-archive",
        filename=filename
    )

@app.get("/")
def read_root():
    return {"status": "BarberMove API Online", "docs": "/docs"}


@app.get("/health")
def healthcheck_root():
    db_status = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        db_status = "degraded"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "barbermove-api",
        "database": db_status,
    }


@app.get("/api/health")
def healthcheck_api():
    return healthcheck_root()

# Para rodar o servidor:
# uvicorn app.main:app# Reload trigger: 2026-02-26 22:11:06
