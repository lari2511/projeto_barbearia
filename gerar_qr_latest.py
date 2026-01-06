#!/usr/bin/env python3
import qrcode

qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=2,
    border=1
)

qr.add_data('http://192.168.15.5:8000/apk/latest')
qr.make(fit=True)

print('\n═══════════════════════════════════════')
print(' QR CODE - BARBERMOVE (SEMPRE ATUALIZADO)')
print('═══════════════════════════════════════\n')

qr.print_ascii(invert=True)

print('\n URL: http://192.168.15.5:8000/apk/latest')
print('\n ✓ Sempre baixa a versão mais recente')
print(' ✓ Tipo MIME correto (APK, não ZIP)')
print(' ✓ Porta 8000 (já liberada no firewall)\n')
print(' INSTRUÇÕES:')
print(' 1. Desinstale versões antigas do app')
print(' 2. Escaneie o QR ou acesse o link no Chrome')
print(' 3. Baixe e instale o APK (5.3 MB)')
print(' 4. Permita "Fontes desconhecidas" se solicitado\n')
print(' TESTE DE LOGIN:')
print(' - Barbearia: barbearia1@test.com / senha123\n')
print('═══════════════════════════════════════\n')
