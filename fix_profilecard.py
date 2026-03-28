#!/usr/bin/env python3
import os

filepath = r'c:\projeto_barbearia\barbermove\src\components\ProfileCard.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Remover caracteres de markdown no final
while content.endswith('`') or content.endswith('}') or content.endswith('\n'):
    if content.endswith('\n') and not content[:-1].endswith('}'):
        content = content[:-1]
    elif content.endswith('`') or (content.endswith('}') and content.count('}') > content.count('{')):
        content = content[:-1]
    else:
        break

# Garantir que termina com }
if not content.strip().endswith('}'):
    content = content.rstrip() + '\n}\n'

# Escrever de volta
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Arquivo ProfileCard.jsx corrigido!")
