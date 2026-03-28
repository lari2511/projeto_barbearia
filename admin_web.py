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
    Senha: admin123456
"""

import uvicorn
import sys

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔧 INICIANDO ADMIN DASHBOARD WEB")
    print("=" * 80)
    print("\n📍 Acesse em: http://localhost:9000/admin")
    print("🔐 Login: admin@barbermovie.local / admin123456")
    print("\n" + "=" * 80 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9000,
        reload=False,
        log_level="info"
    )
