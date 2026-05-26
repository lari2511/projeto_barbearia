#!/usr/bin/env python3
"""Script temporário para baixar a logo do BarberMove"""
import urllib.request
import os

# URL da imagem enviada (BarberMove logo)
logo_url = "https://raw.githubusercontent.com/github/copilot-workspace-user-manual/main/assets/barbermove-logo.png"

# Destinos
destinations = [
    os.path.join("resources", "brand-logo.png"),
    os.path.join("public", "brand-logo.png")
]

# Criar diretórios se não existirem
os.makedirs("resources", exist_ok=True)
os.makedirs("public", exist_ok=True)

# Como não temos a URL real, vou copiar da imagem anexada manualmente
# Por enquanto, crio um placeholder que o usuário pode substituir
print("⚠️  Por favor, salve manualmente a imagem enviada como:")
print("   - barbermove/resources/brand-logo.png")
print("   - barbermove/public/brand-logo.png")
print("\nOu me envie a logo novamente que eu salvo nos locais corretos.")
