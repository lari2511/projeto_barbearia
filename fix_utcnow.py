#!/usr/bin/env python3
"""
Script para corrigir todas as ocorrências de datetime.utcnow() para datetime.now()
em arquivos Python do app
"""

import os
import re

# Arquivos a corrigir
files_to_fix = [
    "app/routes_freelancer.py",
    "app/routes_fixes.py",
    "app/routes_relatorio.py",
    "app/routes_extras.py",
    "app/routes_pagamentos.py",
    "app/routes_documentos.py",
    "app/routes_cadeiras.py",
    "app/routes_disponibilidade.py",
]

def fix_utcnow_in_file(filepath):
    """Substitui todas as ocorrências de utcnow() por now()"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Contar ocorrências
        count = len(re.findall(r'datetime\.utcnow\(\)', content))
        
        if count == 0:
            print(f"✅ {filepath}: Nenhuma ocorrência de utcnow()")
            return 0
        
        # Substituir
        new_content = content.replace('datetime.utcnow()', 'datetime.now()')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ {filepath}: {count} ocorrência(s) corrigida(s)")
        return count
        
    except FileNotFoundError:
        print(f"❌ {filepath}: Arquivo não encontrado")
        return 0
    except Exception as e:
        print(f"❌ {filepath}: Erro - {e}")
        return 0

if __name__ == "__main__":
    print("\n🔧 CORRIGINDO datetime.utcnow() para datetime.now()")
    print("=" * 70)
    
    total_fixed = 0
    
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            total_fixed += fix_utcnow_in_file(filepath)
        else:
            print(f"⚠️  {filepath}: Arquivo não encontrado")
    
    print("=" * 70)
    print(f"\n✨ Total de ocorrências corrigidas: {total_fixed}")
    print("✅ Todas as ocorrências foram atualizadas!")
