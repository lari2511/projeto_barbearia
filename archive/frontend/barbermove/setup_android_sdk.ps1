# Script para baixar e configurar Android SDK sem Android Studio

Write-Host "Baixando Android Command Line Tools..." -ForegroundColor Yellow

# Criar diretorio para SDK
$sdkPath = "$env:USERPROFILE\android-sdk"
$cmdlineToolsPath = "$sdkPath\cmdline-tools\latest"

if (!(Test-Path $sdkPath)) {
    New-Item -ItemType Directory -Path $sdkPath -Force | Out-Null
}

# URL das Command Line Tools
$toolsUrl = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
$toolsZip = "$env:TEMP\android-cmdline-tools.zip"

# Baixar
Write-Host "Baixando ferramentas..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $toolsUrl -OutFile $toolsZip

# Extrair
Write-Host "Extraindo..." -ForegroundColor Cyan
Expand-Archive -Path $toolsZip -DestinationPath "$sdkPath\cmdline-tools-temp" -Force

# Organizar estrutura correta
if (!(Test-Path "$sdkPath\cmdline-tools")) {
    New-Item -ItemType Directory -Path "$sdkPath\cmdline-tools" -Force | Out-Null
}

Move-Item -Path "$sdkPath\cmdline-tools-temp\cmdline-tools" -Destination "$sdkPath\cmdline-tools\latest" -Force

# Limpar
Remove-Item -Path $toolsZip -Force
Remove-Item -Path "$sdkPath\cmdline-tools-temp" -Recurse -Force

Write-Host "Command Line Tools instaladas!" -ForegroundColor Green

# Configurar variaveis de ambiente
Write-Host "Configurando variaveis de ambiente..." -ForegroundColor Yellow

$env:ANDROID_HOME = $sdkPath
$platformTools = "$sdkPath\platform-tools"
$cmdTools = "$sdkPath\cmdline-tools\latest\bin"
$env:PATH = "$cmdTools;$platformTools;$env:PATH"

[System.Environment]::SetEnvironmentVariable('ANDROID_HOME', $sdkPath, [System.EnvironmentVariableTarget]::User)

Write-Host "Variaveis configuradas!" -ForegroundColor Green

# Aceitar licencas e instalar componentes necessarios
Write-Host "Instalando componentes do SDK (pode demorar alguns minutos)..." -ForegroundColor Yellow

$sdkmanager = "$cmdlineToolsPath\bin\sdkmanager.bat"

# Instalar componentes necessarios
Write-Host "Instalando Android SDK Platform 34..." -ForegroundColor Cyan
$yesString = "y`n" * 10
$yesString | & $sdkmanager --licenses
& $sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"

Write-Host "Android SDK configurado com sucesso!" -ForegroundColor Green
Write-Host "Agora voce pode gerar o APK!" -ForegroundColor Yellow

# Criar local.properties
$localProps = "sdk.dir=$($sdkPath -replace '\\', '\\')"
$localPropsPath = "C:\projeto_barbearia\barbermove\android\local.properties"
Set-Content -Path $localPropsPath -Value $localProps
Write-Host "Arquivo local.properties criado!" -ForegroundColor Green
