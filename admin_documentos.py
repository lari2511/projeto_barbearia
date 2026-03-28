"""
Script para listar e validar documentos de barbeiros como Barbearia/Admin
Deve ser usado em um ambiente de administração
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Usuario

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost/barbermovie_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def listar_documentos_pendentes():
    """Lista documentos pendentes de verificação"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("📄 DOCUMENTOS PENDENTES DE VERIFICAÇÃO")
        print("="*80 + "\n")
        
        # Buscar usuários com documentos pendentes
        pendentes = db.query(Usuario).filter(
            (Usuario.documento_frente_url != None) &
            (Usuario.documento_verificado == False)
        ).all()
        
        if not pendentes:
            print("✅ Nenhum documento pendente de verificação!\n")
            return
        
        print(f"📋 ENCONTRADOS {len(pendentes)} DOCUMENTO(S) PENDENTE(S):\n")
        
        for i, usuario in enumerate(pendentes, 1):
            print(f"{i}. {usuario.nome} ({usuario.email})")
            print(f"   ID: {usuario.id}")
            print(f"   Tipo: {usuario.tipo}")
            print(f"   RG/CNH: {usuario.rg or 'Não informado'}")
            print(f"   Frente: {usuario.documento_frente_url[:60]}...")
            print(f"   Verso: {usuario.documento_verso_url[:60]}..." if usuario.documento_verso_url else "   Verso: Não enviado")
            print(f"   Selfie: {usuario.selfie_documento_url[:60]}..." if usuario.selfie_documento_url else "   Selfie: Não enviado")
            print(f"   Enviado em: {usuario.criado_em.strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"   Status: ⏳ AGUARDANDO VERIFICAÇÃO")
            print()
    
    finally:
        db.close()

def listar_documentos_verificados():
    """Lista documentos já verificados"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("✅ DOCUMENTOS VERIFICADOS")
        print("="*80 + "\n")
        
        verificados = db.query(Usuario).filter(
            Usuario.documento_verificado == True
        ).all()
        
        if not verificados:
            print("Nenhum documento verificado ainda.\n")
            return
        
        print(f"✅ {len(verificados)} USUÁRIO(S) COM DOCUMENTOS VERIFICADOS:\n")
        
        for usuario in verificados:
            print(f"✓ {usuario.nome} ({usuario.email})")
            print(f"  Verificado em: {usuario.documento_verificado_em.strftime('%d/%m/%Y %H:%M:%S') if usuario.documento_verificado_em else 'N/A'}")
            print()
    
    finally:
        db.close()

def listar_documentos_rejeitados():
    """Lista documentos rejeitados"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("❌ DOCUMENTOS REJEITADOS")
        print("="*80 + "\n")
        
        rejeitados = db.query(Usuario).filter(
            (Usuario.documento_verificado == False) &
            (Usuario.documento_rejeitado_motivo != None)
        ).all()
        
        if not rejeitados:
            print("Nenhum documento rejeitado.\n")
            return
        
        print(f"❌ {len(rejeitados)} USUÁRIO(S) COM DOCUMENTOS REJEITADOS:\n")
        
        for usuario in rejeitados:
            print(f"✗ {usuario.nome} ({usuario.email})")
            print(f"  Motivo: {usuario.documento_rejeitado_motivo}")
            print()
    
    finally:
        db.close()

def aprovar_documento(usuario_id: int):
    """Aprova documento de um usuário"""
    db = SessionLocal()
    
    try:
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        
        if not usuario:
            print(f"❌ Usuário ID {usuario_id} não encontrado!")
            return
        
        print(f"\n✅ APROVANDO DOCUMENTO DE: {usuario.nome}")
        print(f"   Email: {usuario.email}")
        
        usuario.documento_verificado = True
        from datetime import datetime
        usuario.documento_verificado_em = datetime.utcnow()
        usuario.documento_rejeitado_motivo = None
        
        db.commit()
        print(f"   ✅ Documento APROVADO com sucesso!\n")
        
    finally:
        db.close()

def rejeitar_documento(usuario_id: int, motivo: str):
    """Rejeita documento de um usuário"""
    db = SessionLocal()
    
    try:
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        
        if not usuario:
            print(f"❌ Usuário ID {usuario_id} não encontrado!")
            return
        
        print(f"\n❌ REJEITANDO DOCUMENTO DE: {usuario.nome}")
        print(f"   Email: {usuario.email}")
        print(f"   Motivo: {motivo}")
        
        usuario.documento_verificado = False
        usuario.documento_rejeitado_motivo = motivo
        
        db.commit()
        print(f"   ❌ Documento REJEITADO com sucesso!\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    print("\n🔐 GERENCIADOR DE DOCUMENTOS - ADMIN BARBEARIA")
    print("="*80)
    
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        
        if comando == "pendentes":
            listar_documentos_pendentes()
        elif comando == "verificados":
            listar_documentos_verificados()
        elif comando == "rejeitados":
            listar_documentos_rejeitados()
        elif comando == "aprovar" and len(sys.argv) > 2:
            usuario_id = int(sys.argv[2])
            aprovar_documento(usuario_id)
        elif comando == "rejeitar" and len(sys.argv) > 3:
            usuario_id = int(sys.argv[2])
            motivo = sys.argv[3]
            rejeitar_documento(usuario_id, motivo)
        else:
            print("\n❌ Comando desconhecido!")
            print("\nUso:")
            print("  python admin_documentos.py pendentes          # Listar pendentes")
            print("  python admin_documentos.py verificados        # Listar verificados")
            print("  python admin_documentos.py rejeitados         # Listar rejeitados")
            print("  python admin_documentos.py aprovar <id>       # Aprovar documento")
            print("  python admin_documentos.py rejeitar <id> <motivo>  # Rejeitar")
    else:
        # Mostrar resumo geral
        listar_documentos_pendentes()
        listar_documentos_verificados()
        listar_documentos_rejeitados()
