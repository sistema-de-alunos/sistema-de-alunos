$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$nome = "Sistema de Alunos"
$url = "https://github.com/sistema-de-alunos/sistema-de-alunos/releases/latest/download/SistemaDeAlunos.zip"
$destino = Join-Path $env:LOCALAPPDATA "Programs\SistemaDeAlunos"
$exe = Join-Path $destino "SistemaDeAlunos.exe"
$zip = Join-Path $env:TEMP "SistemaDeAlunos.zip"

try {
    Write-Host "Instalando $nome..." -ForegroundColor Cyan

    Get-Process SistemaDeAlunos -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Milliseconds 500

    Write-Host "Baixando a versao mais recente..."
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing

    Write-Host "Copiando arquivos..."
    if (Test-Path $destino) { Remove-Item $destino -Recurse -Force }
    New-Item -ItemType Directory -Path $destino -Force | Out-Null
    Expand-Archive -Path $zip -DestinationPath $destino -Force
    Remove-Item $zip -Force

    Write-Host "Criando atalhos..."
    $shell = New-Object -ComObject WScript.Shell
    $menuIniciar = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    foreach ($pasta in @([Environment]::GetFolderPath("Desktop"), $menuIniciar)) {
        New-Item -ItemType Directory -Path $pasta -Force | Out-Null
        $atalho = $shell.CreateShortcut((Join-Path $pasta "$nome.lnk"))
        $atalho.TargetPath = $exe
        $atalho.WorkingDirectory = $destino
        $atalho.IconLocation = $exe
        $atalho.Save()
    }

    Write-Host ""
    Write-Host "$nome instalado com sucesso! Abrindo..." -ForegroundColor Green
    Start-Process $exe -WorkingDirectory $destino
}
catch {
    Write-Host ""
    Write-Host "Nao foi possivel instalar: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Verifique a conexao com a internet e tente novamente."
}
