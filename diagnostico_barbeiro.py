"""
Script para diagnosticar e corrigir problemas de portfólio de barbeiros
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Usuario, Freelancer

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost/barbermovie_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def diagnosticar_problema():
    """Verifica qual é o problema com portfólio"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*70)
        print("🔍 DIAGNÓSTICO: PORTFÓLIO DE BARBEIROS")
        print("="*70 + "\n")
        
        # 1. Buscar barbeiros
        barbeiros = db.query(Usuario).filter(Usuario.tipo == "barbeiro").all()
        
        if not barbeiros:
            print("❌ Nenhum barbeiro encontrado no banco!")
            return
        
        print(f"📊 ENCONTRADOS {len(barbeiros)} BARBEIROS:\n")
        
        for barbeiro in barbeiros:
            print(f"👨‍💼 {barbeiro.nome} ({barbeiro.email})")
            print(f"   ID Usuario: {barbeiro.id}")
            print(f"   Email verificado: {'✅' if barbeiro.email_verificado else '❌'}")
            print(f"   Documento verificado: {'✅' if barbeiro.documento_verificado else '❌'}")
            
            # Verificar se existe freelancer associado
            freelancer = db.query(Freelancer).filter(
                Freelancer.usuario_id == barbeiro.id
            ).first()
            
            if freelancer:
                print(f"   ✅ Freelancer registrado: ID {freelancer.id}")
                print(f"      - Experiência: {freelancer.tempo_experiencia_anos} anos")
                print(f"      - Nível: {freelancer.nivel_tecnico}")
                print(f"      - Portfólio: {len(freelancer.portfolio)} fotos")
            else:
                print(f"   ❌ NÃO HÁ FREELANCER REGISTRADO! <-- PROBLEMA!")
                print(f"      👉 Barbeiro não pode fazer upload de portfólio!")
            
            print()
        
        # 2. Resumo
        print("\n" + "="*70)
        print("📋 RESUMO")
        print("="*70)
        
        total_barbeiros = len(barbeiros)
        barbeiros_com_freelancer = len([b for b in barbeiros if db.query(Freelancer).filter(
            Freelancer.usuario_id == b.id
        ).first()])
        
        print(f"\nBarbeiros cadastrados: {total_barbeiros}")
        print(f"Barbeiros com Freelancer: {barbeiros_com_freelancer}")
        print(f"Barbeiros SEM Freelancer: {total_barbeiros - barbeiros_com_freelancer} ❌")
        
        if total_barbeiros > barbeiros_com_freelancer:
            print(f"\n⚠️  PROBLEMA ENCONTRADO!")
            print(f"   {total_barbeiros - barbeiros_com_freelancer} barbeiro(s) não têm registro de freelancer")
            print(f"   Por isso não conseguem fazer upload de portfólio!")
        
    finally:
        db.close()

if __name__ == "__main__":
    diagnosticar_problema()
