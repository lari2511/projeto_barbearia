#!/usr/bin/env python3
"""Script para rodar o servidor FastAPI"""

import uvicorn
import sys

if __name__ == "__main__":
    # Inicializar banco de dados
    from app.database import init_db
    init_db()
    
    # Rodar o servidor
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Permite acesso externo
        port=8000,
        reload=False,
        log_level="info"
    )
