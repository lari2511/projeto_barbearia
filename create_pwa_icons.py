from PIL import Image, ImageDraw, ImageFont

def create_pwa_icon(size, filename):
    """Criar ícone PWA com gradiente e símbolo de barbeiro"""
    img = Image.new('RGB', (size, size), '#1f2937')
    draw = ImageDraw.Draw(img)
    
    # Desenhar fundo com gradiente simulado
    for i in range(size):
        shade = int(31 + (135 - 31) * (i / size))
        color = f'#{shade:02x}29{shade+10:02x}'
        draw.rectangle([(0, i), (size, i+1)], fill=color)
    
    # Desenhar ícone de tesoura estilizado
    center_x, center_y = size // 2, size // 2
    icon_size = size // 3
    
    # Círculo principal (azul)
    draw.ellipse(
        [(center_x - icon_size, center_y - icon_size),
         (center_x + icon_size, center_y + icon_size)],
        fill='#3b82f6'
    )
    
    # Detalhes brancos (tesoura simplificada)
    detail_size = icon_size // 4
    draw.ellipse(
        [(center_x - detail_size - 20, center_y - detail_size - 20),
         (center_x - detail_size + 20, center_y - detail_size + 20)],
        fill='white'
    )
    draw.ellipse(
        [(center_x + detail_size - 20, center_y + detail_size - 20),
         (center_x + detail_size + 20, center_y + detail_size + 20)],
        fill='white'
    )
    
    # Linha central
    draw.line(
        [(center_x - icon_size//2, center_y - icon_size//2),
         (center_x + icon_size//2, center_y + icon_size//2)],
        fill='white', width=size//40
    )
    
    img.save(filename, 'PNG')
    print(f'✓ Criado: {filename} ({size}x{size})')

if __name__ == '__main__':
    import os
    os.chdir('barbermove/public')
    
    create_pwa_icon(192, 'pwa-192x192.png')
    create_pwa_icon(512, 'pwa-512x512.png')
    create_pwa_icon(180, 'apple-touch-icon.png')
    
    print('\n✓ Todos os ícones PWA criados com sucesso!')
