# --- ARQUIVO: app/main.py ---
# Ponto de entrada: Configura o App e inclui as rotas

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import hashlib

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
from .routes_senha import router as router_senha  # 🔑 Reset de senha
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

app = FastAPI(
    title="BarberMove API", 
    lifespan=lifespan,
    timeout=300.0  # Aumenta timeout para 5 minutos
)

# Configuração CORS - Lê do .env
origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:5175")
cors_origins = [o.strip() for o in origins_env.split(",") if o and o.strip()]

# Origens do app mobile (Capacitor) para evitar bloqueio CORS no APK.
mobile_origins = [
    "http://localhost",
    "https://localhost",
    "capacitor://localhost",
    "ionic://localhost",
]

for origin in mobile_origins:
    if origin not in cors_origins:
        cors_origins.append(origin)

# Permite modo de desenvolvimento com CORS aberto definindo DEBUG_ALLOW_ALL_CORS=1
if os.getenv("DEBUG_ALLOW_ALL_CORS", "0") == "1":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|[a-z0-9-]+\.loca\.lt)(:\d+)?$",
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
app.include_router(router_senha)  # 🔑 Reset de senha
# Rotas legais (Termos e Privacidade)
app.include_router(router_legais, prefix="/api/v1")

# Diretorio de distribuicao de APKs (configuravel por variavel de ambiente).
apk_download_dir = pathlib.Path(os.getenv("APK_DOWNLOAD_DIR", "barbermove"))
if not apk_download_dir.is_absolute():
    apk_download_dir = pathlib.Path.cwd() / apk_download_dir
apk_download_dir = apk_download_dir.resolve()
apk_download_dir.mkdir(parents=True, exist_ok=True)

# Rota principal para download e alias legado para manter compatibilidade.
app.mount("/downloads", StaticFiles(directory=str(apk_download_dir)), name="downloads")
app.mount("/download", StaticFiles(directory=str(apk_download_dir)), name="download")

# Monta uploads de imagens (perfil, portfólio, etc.)
uploads_dir = pathlib.Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# WebSocket simples para notificacoes (evita 403 quando o front conecta)
# Aceita também o caminho proxied usado pelo Vite/ngrok (`/proxy/ws/notificacoes`).
@app.websocket("/proxy/ws/notificacoes")
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

def _list_apk_files() -> list[pathlib.Path]:
    if not apk_download_dir.exists() or not apk_download_dir.is_dir():
        return []
    return [
        file_path
        for file_path in apk_download_dir.iterdir()
        if file_path.is_file() and file_path.suffix.lower() == ".apk"
    ]


def _resolve_apk_file(filename: str) -> pathlib.Path:
    file_path = (apk_download_dir / filename).resolve()

    # Bloqueia path traversal para fora do diretorio de distribuicao.
    if file_path != apk_download_dir and apk_download_dir not in file_path.parents:
        raise HTTPException(status_code=400, detail="Nome de arquivo invalido")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    if file_path.suffix.lower() != ".apk":
        raise HTTPException(status_code=400, detail="Somente arquivos .apk sao permitidos")

    return file_path


# Endpoint dedicado para baixar APK com cabecalho correto.
@app.get("/apk/latest")
def download_latest_apk():
    apks = _list_apk_files()
    if not apks:
        raise HTTPException(status_code=404, detail="Nenhum APK disponivel")

    latest = max(apks, key=lambda file_path: file_path.stat().st_mtime)
    return FileResponse(
        str(latest),
        media_type="application/vnd.android.package-archive",
        filename=latest.name,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/apk/info")
def apk_info():
    apks = _list_apk_files()
    api_url = os.getenv("API_URL", "").rstrip("/")

    if not apks:
        return {
            "status": "empty",
            "apk_dir": str(apk_download_dir),
            "downloads_path": "/downloads",
            "latest_endpoint": "/apk/latest",
            "message": "Nenhum APK publicado",
        }

    latest = max(apks, key=lambda file_path: file_path.stat().st_mtime)
    latest_stat = latest.stat()
    latest_endpoint = f"/apk/{latest.name}"
    latest_url = f"{api_url}{latest_endpoint}" if api_url else latest_endpoint
    static_download_url = f"{api_url}/downloads/{latest.name}" if api_url else f"/downloads/{latest.name}"
    download_url = latest_url

    # Assinatura simples para detectar nova versao no app mesmo com nome fixo (app-release.apk).
    signature_base = f"{latest.name}:{int(latest_stat.st_mtime)}:{latest_stat.st_size}"
    latest_signature = hashlib.sha256(signature_base.encode("utf-8")).hexdigest()

    return {
        "status": "ok",
        "apk_dir": str(apk_download_dir),
        "downloads_path": "/downloads",
        "latest_filename": latest.name,
        "latest_size_bytes": latest_stat.st_size,
        "latest_mtime_epoch": int(latest_stat.st_mtime),
        "latest_signature": latest_signature,
        "latest_endpoint": latest_endpoint,
        "latest_url": latest_url,
        "download_url": download_url,
        "static_download_url": static_download_url,
    }


@app.get("/apk/{filename}")
def download_apk(filename: str):
    file_path = _resolve_apk_file(filename)
    return FileResponse(
        str(file_path),
        media_type="application/vnd.android.package-archive",
        filename=file_path.name,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@app.get("/")
def read_root():
    # Se a SPA foi construída e copiada para `app/static`, sirva o index.html
    try:
        index_path = spa_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")
        # Fallback: verifica caminho relativo ao cwd (caso uvicorn tenha mudado o cwd)
        alt = pathlib.Path.cwd() / "app" / "static" / "index.html"
        if alt.exists():
            return FileResponse(str(alt), media_type="text/html")
    except Exception:
        pass

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

# Serve arquivos estáticos do frontend (build Vite em barbermove/dist copiadas para app/static)
spa_dir = pathlib.Path("app") / "static"
if spa_dir.exists():
    # Monta o diretório estático na raiz. Como as rotas da API já foram registradas
    # acima, elas têm precedência; este mount atua como fallback para a SPA.
    app.mount("/", StaticFiles(directory=str(spa_dir), html=True), name="spa")
    # Alias compatível: expõe também em /static para requests legadas que usem
    # /static/index.html ou caminhos com /static/asset.js
    app.mount("/static", StaticFiles(directory=str(spa_dir), html=True), name="spa_static")

