#!/usr/bin/env python3
"""
Script para criar usuário ADMIN no sistema BarberMovie

Este tipo de usuário é exclusivo para desenvolvedores e donos do negócio.
NÃO é acessível por clientes, barbeiros ou barbearias.
"""

from app.database import SessionLocal, engine, Base
from app.models import Usuario
from passlib.context import CryptContext
import sys

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def criar_usuario_admin():
    """
    Cria um usuário do tipo 'admin' no banco de dados.
    """
    db = SessionLocal()
    
    try:
        # Verifica se já existe admin
        admin_existente = db.query(Usuario).filter(Usuario.tipo == "admin").first()
        
        if admin_existente:
            print(f"⚠️  Já existe um usuário admin: {admin_existente.email}")
            resposta = input("Deseja criar outro? (s/n): ")
            if resposta.lower() != 's':
                print("❌ Operação cancelada")
                return
        
        print("\n🔧 Criar Novo Usuário ADMIN")
        print("=" * 50)
        
        email = input("Email do admin: ").strip()
        
        # Verifica se email já existe
        if db.query(Usuario).filter(Usuario.email == email).first():
            print(f"❌ Email {email} já está cadastrado!")
            return
        
        nome = input("Nome completo: ").strip()
        senha = input("Senha (mín. 6 caracteres): ").strip()
        
        if len(senha) < 6:
            print("❌ Senha precisa ter pelo menos 6 caracteres!")
            return
        
        # Criar usuário admin
        novo_admin = Usuario(
            email=email,
            nome=nome,
            senha_hash=pwd_context.hash(senha),
            tipo="admin",  # TIPO ESPECIAL
            email_verificado=True,  # Admin já vem verificado
            documento_verificado=True,  # Admin não precisa validar documento
            telefone="",
            endereco="Sistema"
        )
        
        db.add(novo_admin)
        db.commit()
        db.refresh(novo_admin)
        
        print("\n" + "=" * 50)
        print("✅ USUÁRIO ADMIN CRIADO COM SUCESSO!")
        print("=" * 50)
        print(f"📧 Email: {novo_admin.email}")
        print(f"👤 Nome: {novo_admin.nome}")
        print(f"🔑 ID: {novo_admin.id}")
        print(f"🛡️  Tipo: {novo_admin.tipo.upper()}")
        print("=" * 50)
        print("\n🎯 Acesso:")
        print("1. Faça login com essas credenciais")
        print("2. Você terá acesso ao Painel Administrativo")
        print("3. Poderá validar documentos, gerenciar usuários, etc.")
        print("\n⚠️  IMPORTANTE:")
        print("- Este tipo de usuário é EXCLUSIVO para desenvolvedores")
        print("- NÃO compartilhe essas credenciais")
        print("- Clientes, barbeiros e barbearias NÃO têm acesso a este painel")
        
    except Exception as e:
        print(f"\n❌ Erro ao criar admin: {e}")
        db.rollback()
    finally:
        db.close()


def listar_admins():
    """
    Lista todos os usuários admin do sistema.
    """
    db = SessionLocal()
    
    try:
        admins = db.query(Usuario).filter(Usuario.tipo == "admin").all()
        
        if not admins:
            print("\n⚠️  Nenhum usuário admin cadastrado no sistema")
            return
        
        print("\n" + "=" * 50)
        print(f"👥 USUÁRIOS ADMIN CADASTRADOS ({len(admins)})")
        print("=" * 50)
        
        for admin in admins:
            print(f"\n🆔 ID: {admin.id}")
            print(f"📧 Email: {admin.email}")
            print(f"👤 Nome: {admin.nome}")
            print(f"✅ Email Verificado: {'Sim' if admin.email_verificado else 'Não'}")
            print(f"📅 Criado em: {admin.criado_em}")
            print("-" * 50)
        
    except Exception as e:
        print(f"\n❌ Erro ao listar admins: {e}")
    finally:
        db.close()


def deletar_admin():
    """
    Remove um usuário admin do sistema.
    """
    db = SessionLocal()
    
    try:
        admins = db.query(Usuario).filter(Usuario.tipo == "admin").all()
        
        if not admins:
            print("\n⚠️  Nenhum admin para deletar")
            return
        
        print("\n" + "=" * 50)
        print("👥 ADMINS DISPONÍVEIS")
        print("=" * 50)
        
        for idx, admin in enumerate(admins, 1):
            print(f"{idx}. {admin.email} (ID: {admin.id})")
        
        escolha = input("\nDigite o número do admin para deletar (0 para cancelar): ")
        
        try:
            idx = int(escolha)
            if idx == 0:
                print("❌ Operação cancelada")
                return
            
            if idx < 1 or idx > len(admins):
                print("❌ Opção inválida")
                return
            
            admin_selecionado = admins[idx - 1]
            
            confirmacao = input(f"\n⚠️  Confirma deletar {admin_selecionado.email}? (s/n): ")
            
            if confirmacao.lower() == 's':
                db.delete(admin_selecionado)
                db.commit()
                print(f"✅ Admin {admin_selecionado.email} deletado com sucesso!")
            else:
                print("❌ Operação cancelada")
                
        except ValueError:
            print("❌ Digite um número válido")
            
    except Exception as e:
        print(f"\n❌ Erro ao deletar admin: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🔧 GERENCIADOR DE USUÁRIOS ADMIN")
    print("=" * 50)
    print("\n1. Criar novo admin")
    print("2. Listar admins existentes")
    print("3. Deletar admin")
    print("0. Sair")
    
    opcao = input("\nEscolha uma opção: ").strip()
    
    if opcao == "1":
        criar_usuario_admin()
    elif opcao == "2":
        listar_admins()
    elif opcao == "3":
        deletar_admin()
    elif opcao == "0":
        print("👋 Saindo...")
    else:
        print("❌ Opção inválida")
