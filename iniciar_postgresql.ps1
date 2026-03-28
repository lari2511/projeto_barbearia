# 🚀 SCRIPT PARA INICIAR POSTGRESQL
# Execute este script como Administrador

Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "🐘 INICIANDO POSTGRESQL" -ForegroundColor Green
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 59) -ForegroundColor Cyan

# Tenta iniciar o serviço
try {
    Write-Host "`n1️⃣ Verificando serviço PostgreSQL..." -ForegroundColor Yellow
    $service = Get-Service -Name "postgresql-x64-18" -ErrorAction Stop
    
    Write-Host "   Status atual: $($service.Status)" -ForegroundColor Gray
    
    if ($service.Status -eq "Running") {
        Write-Host "`n✅ PostgreSQL JÁ ESTÁ RODANDO!" -ForegroundColor Green
    } else {
        Write-Host "`n2️⃣ Iniciando PostgreSQL..." -ForegroundColor Yellow
        Start-Service -Name "postgresql-x64-18" -ErrorAction Stop
        Start-Sleep -Seconds 2
        
        $service.Refresh()
        if ($service.Status -eq "Running") {
            Write-Host "✅ PostgreSQL INICIADO COM SUCESSO!" -ForegroundColor Green
        }
    }
    
    Write-Host "`n" -NoNewline
    Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 59) -ForegroundColor Cyan
    Write-Host "✅ POSTGRESQL RODANDO!" -ForegroundColor Green
    Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 59) -ForegroundColor Cyan
    
    Write-Host "`n📊 Agora execute:" -ForegroundColor Yellow
    Write-Host "   python setup_postgres.py" -ForegroundColor White
    
} catch {
    Write-Host "`n❌ ERRO: $_" -ForegroundColor Red
    Write-Host "`n💡 SOLUÇÃO:" -ForegroundColor Yellow
    Write-Host "   1. Clique com botão direito neste script" -ForegroundColor White
    Write-Host "   2. Selecione 'Executar como Administrador'" -ForegroundColor White
    Write-Host "`n   OU" -ForegroundColor Yellow
    Write-Host "`n   1. Aperte Windows + R" -ForegroundColor White
    Write-Host "   2. Digite: services.msc" -ForegroundColor White
    Write-Host "   3. Procure 'postgresql-x64-18'" -ForegroundColor White
    Write-Host "   4. Clique com botão direito → Iniciar" -ForegroundColor White
}

Write-Host '`nPressione Enter para sair...' -ForegroundColor Gray
Read-Host | Out-Null
