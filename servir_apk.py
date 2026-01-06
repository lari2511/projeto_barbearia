"""
Servidor HTTP simples para compartilhar o APK via rede local
Execute este script e acesse o link gerado no seu celular
"""
import http.server
import socketserver
import socket
import qrcode
import os

def get_local_ip():
    """Pega o IP local da máquina"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def main():
    PORT = 8080
    
    # Mudar para o diretório do APK
    os.chdir('barbermove')
    
    # Pegar IP local
    ip = get_local_ip()
    url = f"http://{ip}:{PORT}/BarberMove.apk"
    
    print("\n" + "="*60)
    print("📱 SERVIDOR APK - BarberMove")
    print("="*60)
    print(f"\n🌐 Seu IP Local: {ip}")
    print(f"📦 Link do APK: {url}")
    print(f"\n📋 INSTRUÇÕES:")
    print(f"1. Conecte seu celular na MESMA rede WiFi")
    print(f"2. Abra o navegador no celular")
    print(f"3. Digite: {url}")
    print(f"4. Baixe e instale o APK")
    print(f"\n⚠️  Você precisa habilitar 'Instalar apps de fontes desconhecidas'")
    print(f"    (Configurações > Segurança > Fontes desconhecidas)")
    
    # Gerar QR Code
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        
        print(f"\n📱 QR CODE:")
        print("="*60)
        qr.print_ascii(invert=True)
        print("="*60)
        print(f"\nEscaneie o QR Code acima com seu celular!")
    except:
        print(f"\n⚠️  Instale 'qrcode' para gerar QR Code: pip install qrcode")
    
    print(f"\n🔴 Servidor rodando na porta {PORT}...")
    print(f"Pressione Ctrl+C para parar\n")
    
    # Iniciar servidor HTTP
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✅ Servidor encerrado!")

if __name__ == "__main__":
    main()
