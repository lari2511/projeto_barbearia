#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para iniciar o backend com melhor tratamento de erros
"""
import sys
import traceback

print("=" * 60, flush=True)
print("🚀 INICIANDO BACKEND BARBERMOVE", flush=True)
print("=" * 60, flush=True)

try:
    print("\n1. Testando imports básicos...", flush=True)
    import uvicorn
    print("   ✅ uvicorn", flush=True)
    
    from fastapi import FastAPI
    print("   ✅ fastapi", flush=True)
    
    print("\n2. Importando app.main...", flush=True)
    from app.main import app
    print("   ✅ app.main importado", flush=True)
    
    print("\n3. Iniciando servidor Uvicorn...", flush=True)
    print("   📍 Host: 0.0.0.0", flush=True)
    print("   📍 Port: 8000", flush=True)
    print("   🔄 Reload: Enabled", flush=True)
    print("\n" + "=" * 60, flush=True)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
    
except ImportError as e:
    print(f"\n❌ ERRO DE IMPORT: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ ERRO: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
