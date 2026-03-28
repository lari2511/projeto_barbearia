# Inicializa BarberMove completo com portas fixas:
# - Backend FastAPI: 8000
# - Frontend principal: 5173
# - Painel admin: 5175

Write-Host "INICIANDO BARBERMOVE (backend + frontend + admin)" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".\app") -or -not (Test-Path ".\barbermove") -or -not (Test-Path ".\admin-panel")) {
    Write-Host "Erro: execute este script na raiz do projeto (c:\projeto_barbearia)." -ForegroundColor Red
    exit 1
}

$pythonExe = $null
if (Test-Path ".\.venv\Scripts\python.exe") {
    $pythonExe = (Resolve-Path ".\.venv\Scripts\python.exe").Path
} elseif (Test-Path ".\venv\Scripts\python.exe") {
    $pythonExe = (Resolve-Path ".\venv\Scripts\python.exe").Path
} else {
    Write-Host "Erro: ambiente virtual nao encontrado (.venv ou venv)." -ForegroundColor Red
    Write-Host "Crie/ative o venv antes de iniciar os servicos." -ForegroundColor Yellow
    exit 1
}

function Stop-PortListeners {
    param([int[]]$Ports)

    foreach ($port in $Ports) {
        $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($listeners) {
            foreach ($listener in $listeners) {
                $processId = $listener.OwningProcess
                if ($processId) {
                    try {
                        Stop-Process -Id $processId -Force -ErrorAction Stop
                        Write-Host "Porta $port liberada (PID $processId encerrado)." -ForegroundColor Yellow
                    } catch {
                        Write-Host "Nao foi possivel encerrar PID $processId na porta $port (pode ja ter encerrado)." -ForegroundColor DarkYellow
                    }
                }
            }
        }
    }
}

Write-Host "Limpando conflitos de porta (8000, 5173, 5174, 5175)..." -ForegroundColor Cyan
Stop-PortListeners -Ports @(8000, 5173, 5174, 5175)

$root = (Get-Location).Path

$backendCommand = "& '$pythonExe' -m uvicorn app.main:app --app-dir '$root' --reload --host 0.0.0.0 --port 8000"
$frontCommand = "cd '$root'; npm --prefix barbermove run dev -- --port 5173 --strictPort"
$adminCommand = "cd '$root'; npm --prefix admin-panel run dev -- --port 5175 --strictPort"

Write-Host ""
Write-Host "Subindo backend na porta 8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand | Out-Null

Start-Sleep -Seconds 2

Write-Host "Subindo frontend principal na porta 5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontCommand | Out-Null

Start-Sleep -Seconds 2

Write-Host "Subindo painel admin na porta 5175..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $adminCommand | Out-Null

function Invoke-BackendSmokeCheck {
    param(
        [int]$MaxAttempts = 6,
        [int]$DelaySeconds = 2
    )

    if (-not (Test-Path ".\smoke_backend.ps1")) {
        Write-Host "Smoke script nao encontrado (smoke_backend.ps1)." -ForegroundColor DarkYellow
        return
    }

    Write-Host "" 
    Write-Host "Executando smoke test do backend..." -ForegroundColor Cyan
    $artifactRelativePath = "artifacts/smoke-backend.json"
    $artifactFullPath = Join-Path (Get-Location).Path $artifactRelativePath

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $jsonOutput = & .\smoke_backend.ps1 -BaseUrl "http://127.0.0.1:8000" -Json -OutputJsonPath $artifactRelativePath
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0) {
            $summary = $jsonOutput | ConvertFrom-Json
            Write-Host "Smoke test backend: PASS" -ForegroundColor Green
            foreach ($check in $summary.checks) {
                Write-Host (" - {0} {1} => {2}" -f $check.Endpoint, $check.Status, $check.Result) -ForegroundColor DarkGreen
            }
            Write-Host ("Artifact JSON: " + $artifactFullPath) -ForegroundColor DarkGreen
            return
        }

        if ($attempt -lt $MaxAttempts) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    Write-Host "Smoke test backend: FAIL (servicos iniciaram, mas verificacao automatica falhou)." -ForegroundColor Yellow
    if (Test-Path $artifactFullPath) {
        Write-Host ("Artifact JSON: " + $artifactFullPath) -ForegroundColor DarkYellow
    }
    Write-Host "Rode manualmente: .\smoke_backend.ps1" -ForegroundColor DarkYellow
}

Invoke-BackendSmokeCheck

Write-Host ""
Write-Host "Servicos iniciados." -ForegroundColor Green
Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor White
Write-Host "Docs:     http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "Front:    http://127.0.0.1:5173" -ForegroundColor White
Write-Host "Admin:    http://127.0.0.1:5175" -ForegroundColor White
Write-Host ""
Write-Host "Para reiniciar tudo, rode novamente: .\iniciar_app.ps1" -ForegroundColor Cyan
