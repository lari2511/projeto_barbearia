# --- ARQUIVO: app/main.py ---
# Ponto de entrada: Configura o App e inclui as rotas

from fastapi import FastAPI, HTTPException
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
from .database import Base, engine, init_db
from starlette.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Evento de lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    pass

app = FastAPI(title="BarberMove API", lifespan=lifespan)

# Configuração CORS (Permite que o React acesse este backend)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://192.168.15.5:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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

# Monta arquivos estáticos para download de APKs (porta 8000)
if os.path.exists("barbermove"):
    app.mount("/download", StaticFiles(directory="barbermove"), name="download")

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

# Para rodar o servidor:
# uvicorn app.main:app