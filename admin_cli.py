#!/usr/bin/env python3
"""
🔧 ADMIN CLI - Gerenciador de Perfis de Barbeiros
Ferrramenta separada do app para admin aprovar/rejeitar barbeiros
Usar: python admin_cli.py
"""

from app.database import SessionLocal, engine, Base
from app.models import Usuario
from datetime import datetime
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

class AdminCLI:
    def __init__(self):
        self.db = SessionLocal()
    
    def listar_pendentes(self):
        """Lista todos os barbeiros/clientes/barbearias pendentes de aprovação"""
        pendentes = self.db.query(Usuario).filter(
            Usuario.perfil_aprovado == False,
            Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
        ).order_by(Usuario.criado_em).all()
        
        if not pendentes:
            print("\n✅ Nenhum perfil pendente de aprovação!\n")
            return pendentes
        
        print(f"\n📋 PERFIS PENDENTES DE APROVAÇÃO ({len(pendentes)})\n")
        print("=" * 100)
        
        for idx, user in enumerate(pendentes, 1):
            print(f"\n{idx}. 👤 {user.nome}")
            print(f"   📧 Email: {user.email}")
            print(f"   🏷️  Tipo: {user.tipo.upper()}")
            print(f"   📞 Telefone: {user.telefone or 'Não informado'}")
            print(f"   🆔 RG: {user.rg or 'Não informado'}")
            print(f"   📅 Cadastrado em: {user.criado_em.strftime('%d/%m/%Y %H:%M:%S')}")
            
            # Mostrar documentos
            print(f"\n   📄 DOCUMENTOS:")
            print(f"      • Frente: {'✅' if user.documento_frente_url else '❌'}")
            print(f"      • Verso: {'✅' if user.documento_verso_url else '❌'}")
            print(f"      • Selfie: {'✅' if user.selfie_documento_url else '❌'}")
            print(f"      • Email Verificado: {'✅' if user.email_verificado else '❌'}")
            
            if user.documento_frente_url:
                print(f"      🔗 Frente: {user.documento_frente_url[:60]}...")
            if user.documento_verso_url:
                print(f"      🔗 Verso: {user.documento_verso_url[:60]}...")
            if user.selfie_documento_url:
                print(f"      🔗 Selfie: {user.selfie_documento_url[:60]}...")
            
            print("-" * 100)
        
        return pendentes
    
    def listar_aprovados(self):
        """Lista todos os barbeiros/clientes/barbearias já aprovados"""
        aprovados = self.db.query(Usuario).filter(
            Usuario.perfil_aprovado == True,
            Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
        ).order_by(Usuario.perfil_aprovado_em.desc()).all()
        
        if not aprovados:
            print("\n⚠️  Nenhum perfil aprovado ainda!\n")
            return aprovados
        
        print(f"\n✅ PERFIS APROVADOS ({len(aprovados)})\n")
        print("=" * 100)
        
        for idx, user in enumerate(aprovados, 1):
            print(f"{idx}. ✅ {user.nome} ({user.email}) - Tipo: {user.tipo.upper()}")
            print(f"   Aprovado em: {user.perfil_aprovado_em.strftime('%d/%m/%Y %H:%M:%S')}")
            print("-" * 100)
        
        return aprovados
    
    def aprovar_perfil(self, usuario_id: int):
        """Aprova um perfil de barbeiro/cliente"""
        try:
            usuario = self.db.query(Usuario).filter(Usuario.id == usuario_id).first()
            
            if not usuario:
                print(f"\n❌ Usuário ID {usuario_id} não encontrado!\n")
                return False
            
            if usuario.perfil_aprovado:
                print(f"\n⚠️  Perfil de {usuario.nome} já estava aprovado!\n")
                return False
            
            # Validar documentos
            if not (usuario.documento_frente_url and usuario.documento_verso_url and usuario.selfie_documento_url):
                print(f"\n❌ {usuario.nome} não tem todos os documentos!")
                print(f"   Frente: {'✅' if usuario.documento_frente_url else '❌'}")
                print(f"   Verso: {'✅' if usuario.documento_verso_url else '❌'}")
                print(f"   Selfie: {'✅' if usuario.selfie_documento_url else '❌'}\n")
                return False
            
            if not usuario.email_verificado:
                print(f"\n❌ {usuario.nome} ainda não verificou o email!\n")
                return False
            
            # Aprovar
            usuario.perfil_aprovado = True
            usuario.perfil_aprovado_em = datetime.now()
            self.db.commit()
            
            print(f"\n✅ PERFIL APROVADO!")
            print(f"   👤 {usuario.nome}")
            print(f"   📧 {usuario.email}")
            print(f"   🏷️  Tipo: {usuario.tipo.upper()}")
            print(f"   ✨ Agora pode usar o app!\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Erro ao aprovar: {e}\n")
            self.db.rollback()
            return False
    
    def rejeitar_perfil(self, usuario_id: int, motivo: str = ""):
        """Rejeita um perfil (delete ou marca como rejeitado)"""
        try:
            usuario = self.db.query(Usuario).filter(Usuario.id == usuario_id).first()
            
            if not usuario:
                print(f"\n❌ Usuário ID {usuario_id} não encontrado!\n")
                return False
            
            print(f"\n⚠️  REJEITANDO PERFIL")
            print(f"   👤 {usuario.nome}")
            print(f"   📧 {usuario.email}")
            print(f"   Motivo: {motivo or 'Documentos incompletos ou inválidos'}\n")
            
            # Deletar perfil
            self.db.delete(usuario)
            self.db.commit()
            
            print(f"✅ Perfil deletado com sucesso!\n")
            return True
            
        except Exception as e:
            print(f"\n❌ Erro ao rejeitar: {e}\n")
            self.db.rollback()
            return False
    
    def menu_principal(self):
        """Menu interativo do admin"""
        while True:
            print("\n" + "=" * 100)
            print("🔧 ADMIN CLI - BarberMovie")
            print("=" * 100)
            print("\n1. 📋 Listar perfis pendentes")
            print("2. ✅ Listar perfis aprovados")
            print("3. ✨ Aprovar um perfil")
            print("4. ❌ Rejeitar um perfil")
            print("5. 🚪 Sair")
            
            opcao = input("\nEscolha uma opção (1-5): ").strip()
            
            if opcao == "1":
                pendentes = self.listar_pendentes()
                if pendentes:
                    input("\nPressione ENTER para voltar ao menu...")
            
            elif opcao == "2":
                aprovados = self.listar_aprovados()
                if aprovados:
                    input("\nPressione ENTER para voltar ao menu...")
            
            elif opcao == "3":
                pendentes = self.listar_pendentes()
                if pendentes:
                    try:
                        num = int(input("\nDigite o número do perfil para aprovar (0 para cancelar): "))
                        if num == 0:
                            continue
                        if 1 <= num <= len(pendentes):
                            usuario_id = pendentes[num - 1].id
                            self.aprovar_perfil(usuario_id)
                        else:
                            print("\n❌ Número inválido!")
                    except ValueError:
                        print("\n❌ Digite um número válido!")
            
            elif opcao == "4":
                pendentes = self.listar_pendentes()
                if pendentes:
                    try:
                        num = int(input("\nDigite o número do perfil para rejeitar (0 para cancelar): "))
                        if num == 0:
                            continue
                        if 1 <= num <= len(pendentes):
                            usuario_id = pendentes[num - 1].id
                            motivo = input("Digite o motivo da rejeição (ou deixe em branco): ").strip()
                            self.rejeitar_perfil(usuario_id, motivo)
                        else:
                            print("\n❌ Número inválido!")
                    except ValueError:
                        print("\n❌ Digite um número válido!")
            
            elif opcao == "5":
                print("\n👋 Até logo!\n")
                break
            
            else:
                print("\n❌ Opção inválida!")
    
    def fechar(self):
        """Fecha conexão com banco"""
        self.db.close()

if __name__ == "__main__":
    print("\n" + "=" * 100)
    print("🔧 INICIANDO ADMIN CLI - BarberMovie")
    print("=" * 100)
    
    admin = AdminCLI()
    try:
        admin.menu_principal()
    finally:
        admin.fechar()
