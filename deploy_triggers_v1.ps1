param(
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 5432,
    [string]$DbName = "barbermove",
    [string]$DbUser = "postgres",
    [Alias("DbPassword")]
    [string]$DbSecret = "",
    [switch]$AutoRollbackOnError
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Resolve-PsqlPath {
    $cmd = Get-Command psql -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $roots = @('C:\Program Files\PostgreSQL', 'C:\Program Files (x86)\PostgreSQL')
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $versions = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue
        foreach ($v in $versions) {
            $candidate = Join-Path $v.FullName 'bin\psql.exe'
            if (Test-Path $candidate) { return $candidate }
        }
    }

    return $null
}

function Invoke-PsqlFile([string]$filePath) {
    & $script:PsqlExe -v ON_ERROR_STOP=1 -f $filePath
}

function Invoke-PsqlQuery([string]$query) {
    & $script:PsqlExe -v ON_ERROR_STOP=1 -c $query
}

try {
    Write-Step "Validando pre-requisitos"
    $script:PsqlExe = Resolve-PsqlPath
    if (-not $script:PsqlExe) {
        throw "psql nao encontrado no PATH nem nas pastas padrao do PostgreSQL."
    }
    Write-Host "Usando psql em: $script:PsqlExe" -ForegroundColor DarkGray

    $root = Split-Path -Parent $MyInvocation.MyCommand.Path
    $applyFile = Join-Path $root "migration_triggers_fluxo_uber_v1_compat.sql"
    $rollbackFile = Join-Path $root "migration_triggers_fluxo_uber_v1_rollback.sql"

    if (-not (Test-Path $applyFile)) { throw "Arquivo nao encontrado: $applyFile" }
    if (-not (Test-Path $rollbackFile)) { throw "Arquivo nao encontrado: $rollbackFile" }

    $env:PGHOST = $DbHost
    $env:PGPORT = "$DbPort"
    $env:PGDATABASE = $DbName
    $env:PGUSER = $DbUser
    if ($DbSecret) { $env:PGPASSWORD = $DbSecret }

    Write-Step "Testando conexao com banco"
    Invoke-PsqlQuery "SELECT current_database() AS database, current_user AS user;"

    Write-Step "Aplicando migration v1 de triggers"
    Invoke-PsqlFile $applyFile

    Write-Step "Validando triggers criados"
    Invoke-PsqlQuery "SELECT tgname FROM pg_trigger WHERE tgrelid = 'chamados'::regclass AND NOT tgisinternal ORDER BY tgname;"

    Write-Step "Validando funcoes criadas"
    Invoke-PsqlQuery "SELECT proname FROM pg_proc WHERE proname LIKE 'fn_chamado_%_v1' ORDER BY proname;"

    Write-Host "`nDeploy concluido com sucesso." -ForegroundColor Green
}
catch {
    Write-Host "`nErro durante deploy: $($_.Exception.Message)" -ForegroundColor Red

    if ($AutoRollbackOnError) {
        try {
            Write-Step "Tentando rollback automatico"
            $root = Split-Path -Parent $MyInvocation.MyCommand.Path
            $rollbackFile = Join-Path $root "migration_triggers_fluxo_uber_v1_rollback.sql"
            if (Test-Path $rollbackFile) {
                Invoke-PsqlFile $rollbackFile
                Write-Host "Rollback automatico concluido." -ForegroundColor Yellow
            }
            else {
                Write-Host "Rollback nao executado: arquivo nao encontrado." -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "Falha no rollback automatico: $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    exit 1
}
