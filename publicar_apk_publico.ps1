param(
	[string]$ApiBaseUrl = ""
)

Write-Host "PUBLICACAO DE APK PARA DOWNLOAD PUBLICO" -ForegroundColor Cyan
Write-Host ""

$root = Get-Location
$apkDir = Join-Path $root "APK_PRONTO"

if (-not (Test-Path $apkDir)) {
	Write-Host "Erro: pasta APK_PRONTO nao encontrada em $root" -ForegroundColor Red
	exit 1
}

$apkFiles = Get-ChildItem -Path $apkDir -Filter *.apk -File | Sort-Object LastWriteTime -Descending
if (-not $apkFiles -or $apkFiles.Count -eq 0) {
	Write-Host "Erro: nenhum arquivo .apk encontrado em APK_PRONTO" -ForegroundColor Red
	exit 1
}

$latest = $apkFiles[0]
$stableName = "BarberMove.apk"
$stablePath = Join-Path $apkDir $stableName

if ($latest.Name -ne $stableName) {
	Copy-Item -Path $latest.FullName -Destination $stablePath -Force
	Write-Host "APK publicado: $($latest.Name) -> $stableName" -ForegroundColor Green
} else {
	Write-Host "APK ja esta com nome estavel: $stableName" -ForegroundColor Green
}

Write-Host ""
Write-Host "Diretorio de publicacao: $apkDir" -ForegroundColor White
Write-Host "Arquivo estavel: $stablePath" -ForegroundColor White

if ($ApiBaseUrl) {
	$clean = $ApiBaseUrl.TrimEnd('/')
	Write-Host "" 
	Write-Host "Links publicos para compartilhar:" -ForegroundColor Cyan
	Write-Host "$clean/apk/latest" -ForegroundColor White
	Write-Host "$clean/apk/BarberMove.apk" -ForegroundColor White
	Write-Host "$clean/apk/info" -ForegroundColor White
	Write-Host "$clean/downloads/BarberMove.apk" -ForegroundColor White
}

Write-Host ""
Write-Host "Concluido." -ForegroundColor Green
