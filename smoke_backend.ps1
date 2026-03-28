param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$Json,
    [string]$OutputJsonPath = "",
    [int]$RetryCount = 3,
    [int]$RetryDelayMs = 700
)

$ErrorActionPreference = "Stop"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

function Get-AppVersion {
    $packageCandidates = @(
        "barbermove/package.json",
        "package.json"
    )

    foreach ($candidate in $packageCandidates) {
        if (Test-Path $candidate) {
            try {
                $content = Get-Content $candidate -Raw | ConvertFrom-Json
                if ($content.version) {
                    return [string]$content.version
                }
            } catch {
                # Ignora arquivos inválidos e tenta próximo candidato.
            }
        }
    }

    return "unknown"
}

function Get-GitCommitSha {
    try {
        $sha = (git rev-parse --short HEAD 2>$null)
        if ($LASTEXITCODE -eq 0 -and $sha) {
            return ([string]$sha).Trim()
        }
    } catch {
        # Sem git disponível ou não é um repositório git.
    }

    return "unknown"
}

$checks = @(
    @{ Name = "Root"; Path = "/"; ExpectedStatus = 200 },
    @{ Name = "Health"; Path = "/health"; ExpectedStatus = 200 },
    @{ Name = "API Health"; Path = "/api/health"; ExpectedStatus = 200 },
    @{ Name = "OpenAPI"; Path = "/openapi.json"; ExpectedStatus = 200 },
    @{ Name = "Docs"; Path = "/docs"; ExpectedStatus = 200 }
)

$results = @()
$hasFailure = $false

foreach ($check in $checks) {
    $url = "$BaseUrl$($check.Path)"
    $attempt = 0
    $response = $null
    $status = "ERR"
    $details = ""
    $ok = $false

    while ($attempt -lt $RetryCount -and -not $ok) {
        $attempt += 1
        try {
            $response = Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing -TimeoutSec 15
            $status = [int]$response.StatusCode
            $ok = $status -eq $check.ExpectedStatus
            $details = ""

            if ($check.Path -eq "/health" -or $check.Path -eq "/api/health") {
                try {
                    $body = $response.Content | ConvertFrom-Json
                    if ($null -eq $body.status) {
                        $ok = $false
                        $details = "missing field: status"
                    }
                    if ($null -eq $body.database) {
                        $ok = $false
                        if ($details) { $details += "; " }
                        $details += "missing field: database"
                    }
                    if ($body.status -ne "ok" -and $body.status -ne "degraded") {
                        $ok = $false
                        if ($details) { $details += "; " }
                        $details += "unexpected status=$($body.status)"
                    }
                } catch {
                    $ok = $false
                    $details = "invalid JSON"
                }
            }
        } catch {
            $status = "ERR"
            $details = $_.Exception.Message
            $ok = $false
        }

        if (-not $ok -and $attempt -lt $RetryCount) {
            Start-Sleep -Milliseconds $RetryDelayMs
        }
    }

    if (-not $ok) { $hasFailure = $true }

    $results += [PSCustomObject]@{
        Check = $check.Name
        Endpoint = $check.Path
        Status = $status
        Expected = $check.ExpectedStatus
        Result = if ($ok) { "PASS" } else { "FAIL" }
        Details = if ($ok) { "" } else { $details }
    }
}

$summary = [PSCustomObject]@{
    baseUrl = $BaseUrl
    success = (-not $hasFailure)
    timestamp = (Get-Date).ToString("o")
    metadata = [PSCustomObject]@{
        environment = if ($env:APP_ENV) { $env:APP_ENV } else { "local" }
        appVersion = Get-AppVersion
        gitCommitSha = Get-GitCommitSha
        durationMs = 0
        workspace = (Get-Location).Path
        generator = "smoke_backend.ps1"
    }
    checks = $results
}

$stopwatch.Stop()
$summary.metadata.durationMs = [int]$stopwatch.ElapsedMilliseconds

if ($Json) {
    $jsonText = $summary | ConvertTo-Json -Depth 5
    if ($OutputJsonPath) {
        $resolvedOutput = $OutputJsonPath
        if (-not [System.IO.Path]::IsPathRooted($resolvedOutput)) {
            $resolvedOutput = Join-Path (Get-Location).Path $resolvedOutput
        }

        $outputDir = Split-Path -Parent $resolvedOutput
        if ($outputDir -and -not (Test-Path $outputDir)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }

        [System.IO.File]::WriteAllText($resolvedOutput, $jsonText, [System.Text.Encoding]::UTF8)
    }

    $jsonText
    if ($hasFailure) { exit 1 }
    exit 0
}

$results | Format-Table -AutoSize

if ($hasFailure) {
    Write-Host "`nSmoke test: FAIL" -ForegroundColor Red
    exit 1
}

Write-Host "`nSmoke test: PASS" -ForegroundColor Green
exit 0
