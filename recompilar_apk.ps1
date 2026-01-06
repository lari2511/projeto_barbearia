# Script para recompilar APK com API configurada
Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "🔨 RECOMPILANDO APK - BarberMove" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

try {
    # 1. Build React
    Write-Host "`n📦 1/4 - Building React App..." -ForegroundColor Green
    cd C:\projeto_barbearia\barbermove
    npm run build
    
    # 2. Sync Capacitor
    Write-Host "`n🔄 2/4 - Syncing Capacitor..." -ForegroundColor Green
    npx cap sync android
    
    # 3. Compilar APK
    Write-Host "`n🔨 3/4 - Compilando APK (pode demorar)..." -ForegroundColor Green
    cd android
    .\gradlew assembleDebug
    
    # 4. Copiar APK
    Write-Host "`n📋 4/4 - Copiando APK..." -ForegroundColor Green
    $apkOriginal = "app\build\outputs\apk\debug\app-debug.apk"
    $apkNovo = "..\BarberMove.apk"
    
    if (Test-Path $apkOriginal) {
        Copy-Item $apkOriginal $apkNovo -Force
        $tamanho = [math]::Round((Get-Item $apkNovo).Length / 1MB, 2)
        
        Write-Host "`n=========================================" -ForegroundColor Cyan
        Write-Host "✅ APK RECOMPILADO COM SUCESSO!" -ForegroundColor Green
        Write-Host "=========================================" -ForegroundColor Cyan
        Write-Host "`n📦 Arquivo: BarberMove.apk"
        Write-Host "📊 Tamanho: $tamanho MB"
        Write-Host "`n🌐 Baixe no celular:"
        Write-Host "   http://192.168.15.5:8888/BarberMove.apk" -ForegroundColor White -BackgroundColor DarkGreen
        Write-Host "`n✅ API configurada para: http://192.168.15.5:8000" -ForegroundColor Green
        Write-Host ""
    } else {
        throw "APK não encontrado em $apkOriginal"
    }
    
} catch {
    Write-Host "`n❌ ERRO: $_" -ForegroundColor Red
    Write-Host "`nTente executar manualmente:" -ForegroundColor Yellow
    Write-Host "1. cd C:\projeto_barbearia\barbermove"
    Write-Host "2. npm run build"
    Write-Host "3. npx cap sync android"
    Write-Host "4. cd android && .\gradlew assembleDebug"
    exit 1
}
