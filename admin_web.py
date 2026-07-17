#!/usr/bin/env python3
"""
🔧 Admin Dashboard Web
Rodar em porta separada para gerenciar aprovações com interface visual

Uso:
    python admin_web.py
    
Acesso:
    http://localhost:8001/admin
    
Login:
    Email: admin@barbermovie.local
    Senha: Senha@123
"""

import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", "9000"))

    print("\n" + "=" * 80)
    print("🔧 INICIANDO ADMIN DASHBOARD WEB")
    print("=" * 80)
    print(f"\n📍 Acesse em: http://localhost:{port}/admin")
    print("🔐 Login: admin@barbermovie.local / Senha@123")
    print("\n" + "=" * 80 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
