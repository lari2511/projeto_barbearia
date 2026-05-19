param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [bool]$BuildApk = $true
)

$ErrorActionPreference = 'Stop'

function Write-Info([string]$Message) {
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host $Message -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Err([string]$Message) {
    Write-Host $Message -ForegroundColor Red
}

Write-Info 'INICIANDO DEMO PUBLICA BARBERMOVE'
Write-Host ''

if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    Write-Err 'Ambiente virtual nao encontrado em .\.venv\Scripts\python.exe'
    exit 1
}

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-Err 'npx nao encontrado no PATH (Node.js necessario para localtunnel).'
    exit 1
}

$root = (Get-Location).Path
$pythonExe = (Resolve-Path '.\.venv\Scripts\python.exe').Path
$backendCommand = "& '$pythonExe' -m uvicorn app.main:app --app-dir '$root' --host 127.0.0.1 --port $BackendPort"

Write-Info "Subindo backend local na porta $BackendPort..."
Start-Process powershell -ArgumentList '-NoExit', '-Command', $backendCommand | Out-Null

Start-Sleep -Seconds 3

Write-Info 'Abrindo tunnel LocalTunnel para o backend...'
$tunnelLog = Join-Path $root 'localtunnel.log'
$tunnelErrLog = Join-Path $root 'localtunnel.err.log'
$publicUrl = $null
$tunnelProcess = $null

for ($attempt = 1; $attempt -le 3; $attempt++) {
    if (Test-Path $tunnelLog) {
        Remove-Item $tunnelLog -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $tunnelErrLog) {
        Remove-Item $tunnelErrLog -Force -ErrorAction SilentlyContinue
    }

    $tunnelProcess = Start-Process cmd.exe -ArgumentList "/c npx --yes localtunnel --port $BackendPort" -PassThru -WindowStyle Hidden -RedirectStandardOutput $tunnelLog -RedirectStandardError $tunnelErrLog

    for ($i = 1; $i -le 30; $i++) {
        if ($tunnelProcess.HasExited) {
            break
        }

        $combinedLog = ''
        if (Test-Path $tunnelLog) {
            $combinedLog += (Get-Content -Path $tunnelLog -Raw -ErrorAction SilentlyContinue)
        }
        if (Test-Path $tunnelErrLog) {
            $combinedLog += "`n"
            $combinedLog += (Get-Content -Path $tunnelErrLog -Raw -ErrorAction SilentlyContinue)
        }

        if ($combinedLog) {
            $match = [regex]::Match($combinedLog, 'https://[a-z0-9-]+\.loca\.lt')
            if ($match.Success) {
                $publicUrl = $match.Value
                break
            }
        }

        Start-Sleep -Seconds 2
    }

    if ($publicUrl) {
        break
    }

    if ($tunnelProcess -and -not $tunnelProcess.HasExited) {
        Stop-Process -Id $tunnelProcess.Id -Force -ErrorAction SilentlyContinue
    }

    Write-Warn "Tentativa $attempt/3 de tunnel falhou. Repetindo..."
}

if (-not $publicUrl) {
    Write-Err 'Nao foi possivel obter a URL publica do LocalTunnel.'
    if ($tunnelProcess -and -not $tunnelProcess.HasExited) {
        Stop-Process -Id $tunnelProcess.Id -Force -ErrorAction SilentlyContinue
    }
    exit 1
}

$wsUrl = $publicUrl -replace '^https://', 'wss://'

Write-Ok "URL publica da API: $publicUrl"
Write-Ok "URL publica do WebSocket: $wsUrl/ws/notificacoes"

# Garante que o processo de build herde a URL publica correta.
$env:VITE_API_URL = $publicUrl
$env:VITE_WS_URL = "$wsUrl/ws/notificacoes"
$env:VITE_DEV_MODE = 'false'

$envFile = Join-Path $root 'barbermove\.env.local'
@"
VITE_API_URL=$publicUrl
VITE_WS_URL=$wsUrl/ws/notificacoes
VITE_DEV_MODE=false
"@ | Set-Content -Path $envFile -Encoding UTF8

Write-Ok "Arquivo atualizado: $envFile"

if ($BuildApk) {
    Write-Info 'Gerando APK com a API publica...'
    Push-Location 'barbermove'
    try {
        npm run android:build:debug
        if ($LASTEXITCODE -ne 0) {
            throw 'Falha ao gerar APK debug.'
        }

        $apkSource = 'android\app\build\outputs\apk\debug\app-debug.apk'
        $apkTargetDir = Join-Path $root 'APK_PRONTO'
        New-Item -ItemType Directory -Force -Path $apkTargetDir | Out-Null
        Copy-Item -Path $apkSource -Destination (Join-Path $apkTargetDir 'BarberMove.apk') -Force
        Write-Ok "APK atualizado em $apkTargetDir\BarberMove.apk"
    } finally {
        Pop-Location
    }
}

Write-Host ''
Write-Ok 'DEMO PUBLICA PRONTA'
Write-Host ''
Write-Host 'Compartilhe estes links:' -ForegroundColor White
Write-Host "$publicUrl/health" -ForegroundColor White
Write-Host "$publicUrl/docs" -ForegroundColor White
Write-Host "$publicUrl/apk/latest" -ForegroundColor White
Write-Host "$publicUrl/apk/BarberMove.apk" -ForegroundColor White
Write-Host "$publicUrl/downloads/BarberMove.apk" -ForegroundColor White
Write-Host ''
Write-Warn 'Deixe esta janela aberta para manter o tunnel ativo.'