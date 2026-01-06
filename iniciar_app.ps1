# Script para iniciar BarberMove completo (Backend + Frontend)
# Executa backend e frontend simultaneamente

Write-Host "🚀 INICIANDO BARBERMOVE - Sistema Completo" -ForegroundColor Cyan
Write-Host ""

# Verificar se está no diretório correto
if (-not (Test-Path ".\app") -or -not (Test-Path ".\barbermove")) {
    Write-Host "❌ Erro: Execute este script na raiz do projeto (c:\projeto_barbearia)" -ForegroundColor Red
    exit 1
}

# Verificar ambiente virtual Python
if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Host "❌ Ambiente virtual Python não encontrado!" -ForegroundColor Red
    Write-Host "💡 Criando ambiente virtual..." -ForegroundColor Yellow
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
}

Write-Host "✅ Ambiente Python configurado" -ForegroundColor Green

# Verificar node_modules
if (-not (Test-Path ".\barbermove\node_modules")) {
    Write-Host "💡 Instalando dependências do frontend..." -ForegroundColor Yellow
    Set-Location barbermove
    npm install
    Set-Location ..
}

Write-Host "✅ Dependências do frontend instaladas" -ForegroundColor Green
Write-Host ""

# Criar script para backend
$backendScript = @'
Write-Host "🔧 Backend FastAPI iniciando..." -ForegroundColor Blue
C:\projeto_barbearia\venv\Scripts\python.exe C:\projeto_barbearia\run.py
'@

$backendScript | Out-File -FilePath "temp_backend.ps1" -Encoding UTF8

# Criar script para frontend
$frontendScript = @'
Write-Host "🎨 Frontend React iniciando..." -ForegroundColor Magenta
Set-Location C:\projeto_barbearia\barbermove
npm run dev
'@

$frontendScript | Out-File -FilePath "temp_frontend.ps1" -Encoding UTF8

Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🚀 BARBERMOVE INICIADO!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 Backend API:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "📍 API Docs:     http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "📍 Frontend:     http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  Abrindo em 2 terminais separados..." -ForegroundColor Cyan
Write-Host "⚠️  Para parar: CTRL+C em cada terminal" -ForegroundColor Cyan
Write-Host ""

Start-Sleep -Seconds 2

# Iniciar backend em novo terminal
Start-Process powershell -ArgumentList "-NoExit", "-File", "temp_backend.ps1"

Start-Sleep -Seconds 3

# Iniciar frontend em novo terminal
Start-Process powershell -ArgumentList "-NoExit", "-File", "temp_frontend.ps1"

Start-Sleep -Seconds 2

Write-Host "✅ Servidores iniciados!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Dica: Aguarde alguns segundos e acesse http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎯 Contas de teste:" -ForegroundColor Yellow
Write-Host "   Cliente: cliente@test.com / senha123" -ForegroundColor White
Write-Host "   Barbeiro: barbeiro@test.com / senha123" -ForegroundColor White
Write-Host "   Barbearia: barbearia@test.com / senha123" -ForegroundColor White
Write-Host ""

# Aguardar 10 segundos e limpar arquivos temporários
Start-Sleep -Seconds 10
Remove-Item "temp_backend.ps1" -ErrorAction SilentlyContinue
Remove-Item "temp_frontend.ps1" -ErrorAction SilentlyContinue

Write-Host "Pressione qualquer tecla para fechar esta janela..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
