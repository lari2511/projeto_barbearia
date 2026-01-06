# --- ARQUIVO: app/validators.py ---
# Validações de dados (CPF, CNPJ, telefone, etc)

import re
from typing import Optional

def validar_cpf(cpf: str) -> bool:
    """Valida CPF brasileiro"""
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    
    # Validar primeiro dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10
    
    if int(cpf[9]) != digito1:
        return False
    
    # Validar segundo dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10
    
    return int(cpf[10]) == digito2


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ brasileiro"""
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    
    # Validar primeiro dígito
    multiplicadores = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores[i] for i in range(12))
    digito1 = 11 - (soma % 11)
    digito1 = 0 if digito1 >= 10 else digito1
    
    if int(cnpj[12]) != digito1:
        return False
    
    # Validar segundo dígito
    multiplicadores = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores[i] for i in range(13))
    digito2 = 11 - (soma % 11)
    digito2 = 0 if digito2 >= 10 else digito2
    
    return int(cnpj[13]) == digito2


def validar_telefone_br(telefone: str) -> bool:
    """Valida telefone brasileiro (celular ou fixo)"""
    telefone = re.sub(r'[^0-9]', '', telefone)
    
    # Celular: (XX) 9XXXX-XXXX = 11 dígitos
    # Fixo: (XX) XXXX-XXXX = 10 dígitos
    if len(telefone) not in [10, 11]:
        return False
    
    # DDD válido (11-99)
    ddd = int(telefone[:2])
    if ddd < 11 or ddd > 99:
        return False
    
    # Celular deve começar com 9
    if len(telefone) == 11 and telefone[2] != '9':
        return False
    
    return True


def validar_email(email: str) -> bool:
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def formatar_cpf(cpf: str) -> str:
    """Formata CPF: 123.456.789-10"""
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ: 12.345.678/0001-90"""
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    if len(cnpj) != 14:
        return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def formatar_telefone_br(telefone: str) -> str:
    """Formata telefone: (11) 98765-4321"""
    telefone = re.sub(r'[^0-9]', '', telefone)
    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone


def limpar_documento(documento: str) -> str:
    """Remove formatação de documentos"""
    return re.sub(r'[^0-9]', '', documento)
