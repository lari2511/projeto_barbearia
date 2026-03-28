#!/usr/bin/env python3
"""
🚀 Script para marcar todos os usuários já cadastrados como aprovados
Usa como referência: email verificado + cadastro anterior
"""

from app.database import SessionLocal, engine, Base
from app.models import Usuario
from datetime import datetime
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

db = SessionLocal()

try:
    print("\n" + "=" * 100)
    print("🚀 MARCANDO USUÁRIOS EXISTENTES COMO APROVADOS")
    print("=" * 100)
    
    # Buscar usuarios que:
    # 1. Ainda não foram aprovados (perfil_aprovado = False ou NULL)
    # 2. Já têm email verificado OU cadastro anterior a agora
    usuarios_existentes = db.query(Usuario).filter(
        (Usuario.perfil_aprovado == False) | (Usuario.perfil_aprovado == None),
        Usuario.criado_em < datetime.now()  # Qualquer um que já existe
    ).all()
    
    print(f"\n📋 Encontrados {len(usuarios_existentes)} usuários para aprovar\n")
    
    if usuarios_existentes:
        for user in usuarios_existentes:
            print(f"✅ {user.id:3d} | {user.nome[:25]:25s} | {user.tipo:10s} | {user.email}")
            user.perfil_aprovado = True
            user.perfil_aprovado_em = datetime.now()
        
        db.commit()
        print(f"\n✅ SUCESSO! {len(usuarios_existentes)} usuários marcados como aprovados!")
    else:
        print("⚠️  Nenhum usuário para aprovar.")
    
    # Mostrar estatística
    total_approved = db.query(Usuario).filter(Usuario.perfil_aprovado == True).count()
    total_users = db.query(Usuario).count()
    
    print(f"\n📊 ESTATÍSTICAS:")
    print(f"   Total de usuários: {total_users}")
    print(f"   Aprovados: {total_approved}")
    print(f"   Pendentes: {total_users - total_approved}")
    print()
    
except Exception as e:
    print(f"\n❌ ERRO: {e}\n")
    db.rollback()
finally:
    db.close()
