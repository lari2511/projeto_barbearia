#!/usr/bin/env python3
"""
Script para gerar ícones do app para Android e iOS
Requer: pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

BASE_LOGO = "brand-logo.png"  # coloque o arquivo enviado aqui (resources/brand-logo.png)

def load_logo(size: int) -> Image.Image:
    """Carrega a imagem enviada pelo cliente e centraliza"""
    logo_path = os.path.join("resources", BASE_LOGO)
    if not os.path.exists(logo_path):
        raise FileNotFoundError(f"Logo não encontrada em {logo_path}. Coloque o arquivo enviado neste caminho.")

    logo = Image.open(logo_path).convert("RGBA")
    logo.thumbnail((int(size * 0.7), int(size * 0.7)))
    return logo


def create_app_icon():
    """Cria um ícone baseado na logo enviada"""
    size = 1024
    image = Image.new('RGBA', (size, size), color=(8, 12, 24, 255))
    logo = load_logo(size)
    pos = ((size - logo.width) // 2, (size - logo.height) // 2)
    image.paste(logo, pos, mask=logo)
    return image.convert('RGB')

def create_splash_screen():
    """Cria splash com fundo escuro e logo centralizada"""
    size = 2732
    image = Image.new('RGBA', (size, size), color=(6, 10, 18, 255))
    logo = load_logo(size)
    pos = ((size - logo.width) // 2, (size - logo.height) // 2)
    image.paste(logo, pos, mask=logo)
    return image.convert('RGB')

def main():
    """Função principal"""
    
    # Criar diretório resources se não existir
    resources_dir = "resources"
    if not os.path.exists(resources_dir):
        os.makedirs(resources_dir)
    
    print("🎨 Gerando ícone do app (1024x1024)...")
    icon = create_app_icon()
    icon_path = os.path.join(resources_dir, "icon.png")
    icon.save(icon_path, "PNG")
    print(f"✅ Ícone salvo em: {icon_path}")
    
    print("\n🎨 Gerando splash screen (2732x2732)...")
    splash = create_splash_screen()
    splash_path = os.path.join(resources_dir, "splash.png")
    splash.save(splash_path, "PNG")
    print(f"✅ Splash screen salva em: {splash_path}")
    
    print("\n" + "="*50)
    print("✨ Assets gerados com sucesso!")
    print("="*50)
    print("\n📱 Próximos passos:")
    print("1. (Opcional) Substitua os arquivos gerados por designs profissionais")
    print("2. Execute: npx capacitor-assets generate")
    print("3. Isso criará todos os tamanhos necessários para Android e iOS")
    print("\n💡 Dica: Para melhores resultados, use:")
    print("   - Ícone: PNG transparente, 1024x1024px")
    print("   - Splash: PNG, 2732x2732px, conteúdo centralizado")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        print("\n📦 Certifique-se de instalar Pillow:")
        print("   pip install Pillow")
