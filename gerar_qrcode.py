"""
Gerar QR Code para download do APK
"""
import qrcode
from PIL import Image

# URL do APK
url = "http://192.168.15.5:8888/BarberMove.apk"

# Criar QR Code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)

qr.add_data(url)
qr.make(fit=True)

# Criar imagem
img = qr.make_image(fill_color="black", back_color="white")

# Salvar
img.save("qrcode_download.png")

print("\n" + "="*60)
print("📱 QR CODE GERADO COM SUCESSO!")
print("="*60)
print(f"\n🌐 URL: {url}")
print(f"\n📁 Arquivo salvo: qrcode_download.png")
print(f"\n📱 COMO USAR:")
print(f"   1. Abra a imagem: qrcode_download.png")
print(f"   2. Escaneie com a câmera do celular")
print(f"   3. Toque no link que aparecer")
print(f"   4. Baixe e instale o APK")
print("\n" + "="*60)

# Mostrar QR Code ASCII no terminal
print("\n📱 QR CODE (ASCII):\n")
qr.print_ascii(invert=True)
print("\n" + "="*60 + "\n")
