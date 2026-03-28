#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para resetar o banco de dados quando está bloqueado por processos órfãos
"""
import os
import shutil
import time
from datetime import datetime

print("=" * 60)
print("🔄 SCRIPT DE RESET DO BANCO DE DADOS")
print("=" * 60)

# 1. Fazer backup do banco atual
banco_atual = "barbearia.db"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
banco_backup = f"barbearia_backup_{timestamp}.db"

if os.path.exists(banco_atual):
    print(f"\n📦 Fazendo backup: {banco_atual} → {banco_backup}")
    try:
        shutil.copy2(banco_atual, banco_backup)
        print(f"✅ Backup criado com sucesso!")
        print(f"   Tamanho: {os.path.getsize(banco_backup) / 1024:.2f} KB")
    except Exception as e:
        print(f"⚠️ Erro ao fazer backup: {e}")
        print("   Continuando mesmo assim...")
else:
    print(f"\n⚠️ Banco {banco_atual} não encontrado")

# 2. Tentar deletar banco atual
print(f"\n🗑️ Deletando banco bloqueado: {banco_atual}")
try:
    if os.path.exists(banco_atual):
        os.remove(banco_atual)
        print("✅ Banco deletado com sucesso!")
    else:
        print("⚠️ Banco já não existe")
except PermissionError as e:
    print(f"❌ ERRO: Banco está bloqueado por outro processo!")
    print(f"   {e}")
    print("\n💡 SOLUÇÃO:")
    print("   1. Feche o VS Code completamente")
    print("   2. Use o Task Manager para matar processos Python/Node")
    print("   3. Reinicie a máquina se necessário")
    exit(1)
except Exception as e:
    print(f"❌ Erro inesperado: {e}")
    exit(1)

# 3. Aguardar um pouco
print("\n⏳ Aguardando 2 segundos...")
time.sleep(2)

# 4. Recriar banco usando criar_banco.py
print("\n🏗️ Recriando banco de dados...")
try:
    # Importar e executar criar_banco
    import criar_banco
    print("✅ Banco recriado com sucesso!")
except Exception as e:
    print(f"❌ Erro ao recriar banco: {e}")
    print("\n💡 Execute manualmente: python criar_banco.py")
    exit(1)

# 5. Resumo
print("\n" + "=" * 60)
print("✅ RESET CONCLUÍDO COM SUCESSO!")
print("=" * 60)
print(f"\n📊 Arquivos:")
if os.path.exists(banco_backup):
    print(f"   Backup: {banco_backup} ({os.path.getsize(banco_backup) / 1024:.2f} KB)")
if os.path.exists(banco_atual):
    print(f"   Novo:   {banco_atual} ({os.path.getsize(banco_atual) / 1024:.2f} KB)")

print("\n🚀 Próximos passos:")
print("   1. Iniciar backend: python -m uvicorn app.main:app --reload --port 8000")
print("   2. Iniciar frontend: cd barbermove && npm run dev")
print("   3. Criar contas teste: python criar_contas_teste.py")
print()
