# Parar todos Python
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Aguardar liberar portas
Write-Host "Aguardando liberar portas..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Iniciar Backend (porta 8000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\projeto_barbearia; C:/Users/Usuário/AppData/Local/Programs/Python/Python313/python.exe run.py"

# Aguardar backend subir
Start-Sleep -Seconds 3

# Iniciar Admin (porta 9000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\projeto_barbearia; C:/Users/Usuário/AppData/Local/Programs/Python/Python313/python.exe admin_web.py"

# Aguardar admin subir
Start-Sleep -Seconds 3

Write-Host "`n=== SERVICOS INICIADOS ===" -ForegroundColor Green
Write-Host "Backend: http://10.241.205.196:8000" -ForegroundColor Cyan
Write-Host "Admin:   http://10.241.205.196:9000/admin" -ForegroundColor Cyan
Write-Host "`nLogin Admin:" -ForegroundColor Yellow
Write-Host "Email: barbermove2024@gmail.com" -ForegroundColor White
Write-Host "Senha: admin123" -ForegroundColor White
