param(
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 5432,
    [string]$DbName = "barbermove",
    [string]$DbUser = "postgres",
    [Alias("DbPassword")]
    [string]$DbSecret = ""
)

$ErrorActionPreference = "Stop"

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

$script:PsqlExe = Resolve-PsqlPath
if (-not $script:PsqlExe) {
    throw "psql nao encontrado no PATH nem nas pastas padrao do PostgreSQL."
}
Write-Host "Usando psql em: $script:PsqlExe" -ForegroundColor DarkGray

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$rollbackFile = Join-Path $root "migration_triggers_fluxo_uber_v1_rollback.sql"
if (-not (Test-Path $rollbackFile)) {
    throw "Arquivo nao encontrado: $rollbackFile"
}

$env:PGHOST = $DbHost
$env:PGPORT = "$DbPort"
$env:PGDATABASE = $DbName
$env:PGUSER = $DbUser
if ($DbSecret) { $env:PGPASSWORD = $DbSecret }

& $script:PsqlExe -v ON_ERROR_STOP=1 -f $rollbackFile
& $script:PsqlExe -v ON_ERROR_STOP=1 -c "SELECT tgname FROM pg_trigger WHERE tgrelid = 'chamados'::regclass AND NOT tgisinternal ORDER BY tgname;"

Write-Host "Rollback v1 concluido." -ForegroundColor Yellow
