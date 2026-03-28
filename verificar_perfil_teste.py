"""
Script para verificar e corrigir perfil de teste do barbeiro

Verifica:
- perfil_aprovado = True
- disponivel = True  
- latitude e longitude configuradas

Se não estiverem corretos, corrige automaticamente.
"""

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models

def verificar_e_corrigir_perfil_teste():
    db = SessionLocal()
    try:
        # Buscar todos os barbeiros
        barbeiros = db.query(models.Usuario).filter(
            models.Usuario.tipo == "barbeiro"
        ).all()
        
        print(f"📋 Total de barbeiros: {len(barbeiros)}")
        print("\n" + "="*60)
        
        for barbeiro in barbeiros:
            print(f"\n👤 Barbeiro: {barbeiro.nome} (ID: {barbeiro.id})")
            print(f"   Email: {barbeiro.email}")
            print(f"   Perfil Aprovado: {barbeiro.perfil_aprovado}")
            print(f"   Disponível: {barbeiro.disponivel}")
            print(f"   Latitude: {barbeiro.latitude}")
            print(f"   Longitude: {barbeiro.longitude}")
            
            # Verificar se precisa corrigir
            corrigir = False
            
            if not barbeiro.perfil_aprovado:
                print("   ❌ Perfil NÃO aprovado - corrigindo...")
                barbeiro.perfil_aprovado = True
                corrigir = True
            
            if not barbeiro.disponivel:
                print("   ❌ Não disponível - corrigindo...")
                barbeiro.disponivel = True
                corrigir = True
            
            if barbeiro.latitude is None or barbeiro.longitude is None:
                print("   ❌ Sem coordenadas - configurando São Paulo Centro...")
                # Coordenadas do centro de São Paulo
                barbeiro.latitude = -23.5505
                barbeiro.longitude = -46.6333
                corrigir = True
            
            if corrigir:
                db.commit()
                print("   ✅ Perfil corrigido!")
            else:
                print("   ✅ Perfil OK!")
        
        print("\n" + "="*60)
        print("✅ Verificação concluída!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔍 Verificando perfis de teste...")
    verificar_e_corrigir_perfil_teste()
