param(
  [string]$url = 'http://127.0.0.1:8000/static/index.html',
  [int]$width = 375,
  [int]$height = 812,
  [string]$out = 'screenshots'
)

$chrome = "$env:LOCALAPPDATA\\ms-playwright\\chromium-1223\\chrome-win64\\chrome.exe"
if (-not (Test-Path $chrome)) { Write-Error "Chrome não encontrado: $chrome"; exit 1 }
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }

$outfile = Join-Path $out ("screenshot_{0}x{1}.png" -f $width, $height)

$cmd = "$chrome --headless --disable-gpu --hide-scrollbars --window-size=$width,$height --screenshot=$outfile $url"
Write-Output "Executando: $cmd"
Invoke-Expression $cmd
Write-Output "Salvo: $outfile"