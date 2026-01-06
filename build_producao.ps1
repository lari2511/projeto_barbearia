# Script para build de produção - BarberMove
# Executa todos os passos necessários para gerar APK e PWA

Write-Host "🚀 INICIANDO BUILD DE PRODUÇÃO - BarberMove" -ForegroundColor Cyan
Write-Host ""

# Verificar se está no diretório correto
if (-not (Test-Path ".\barbermove")) {
    Write-Host "❌ Erro: Execute este script na raiz do projeto (c:\projeto_barbearia)" -ForegroundColor Red
    exit 1
}

Write-Host "📦 1. Instalando dependências do frontend..." -ForegroundColor Yellow
Set-Location barbermove
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro ao instalar dependências" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🔨 2. Gerando build de produção (PWA)..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro ao gerar build" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Build PWA criado em: barbermove/dist/" -ForegroundColor Green

Write-Host ""
Write-Host "📱 3. Deseja gerar APK Android? (s/n): " -ForegroundColor Yellow -NoNewline
$resposta = Read-Host

if ($resposta -eq "s" -or $resposta -eq "S") {
    Write-Host ""
    Write-Host "🔄 Sincronizando Capacitor..." -ForegroundColor Yellow
    npm run cap:sync
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erro ao sincronizar Capacitor" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "📱 Gerando APK..." -ForegroundColor Yellow
    Write-Host "⚠️  ATENÇÃO: Este processo pode demorar alguns minutos..." -ForegroundColor Cyan
    
    npm run android:build:debug
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ APK gerado com sucesso!" -ForegroundColor Green
        Write-Host "📍 Localização: barbermove\android\app\build\outputs\apk\debug\app-debug.apk" -ForegroundColor Cyan
        
        # Copiar APK para raiz para facilitar
        Copy-Item "android\app\build\outputs\apk\debug\app-debug.apk" "..\barbermove-debug.apk" -Force
        Write-Host "📄 Cópia criada em: barbermove-debug.apk (raiz do projeto)" -ForegroundColor Cyan
    } else {
        Write-Host "❌ Erro ao gerar APK" -ForegroundColor Red
        Write-Host "💡 Verifique se o Android SDK está instalado corretamente" -ForegroundColor Yellow
    }
}

Set-Location ..

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ BUILD DE PRODUÇÃO CONCLUÍDO!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📁 Arquivos gerados:" -ForegroundColor Yellow
Write-Host "   • PWA: barbermove/dist/" -ForegroundColor White

if (Test-Path "barbermove-debug.apk") {
    Write-Host "   • APK: barbermove-debug.apk" -ForegroundColor White
}

Write-Host ""
Write-Host "📚 Próximos passos:" -ForegroundColor Yellow
Write-Host "   1. Deploy do PWA: Vercel, Netlify ou GitHub Pages" -ForegroundColor White
Write-Host "   2. Teste o APK no celular Android" -ForegroundColor White
Write-Host "   3. Para produção, gere APK assinado (veja FINALIZACAO.md)" -ForegroundColor White
Write-Host ""
Write-Host "📖 Leia FINALIZACAO.md para instruções completas de deploy!" -ForegroundColor Cyan
Write-Host ""
