# Gera dist\SistemaDeAlunos.zip (o .exe e tudo que ele precisa) -- é este
# zip que vai para a Release do GitHub e que o `instalar.ps1` baixa.
#
# Uso (na raiz do projeto):  powershell -ExecutionPolicy Bypass -File tools\gerar_executavel.ps1
#
# Usa um ambiente virtual próprio (.venv-build) para não mexer no Python do
# computador de desenvolvimento.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".venv-build")) {
    python -m venv .venv-build
}
$py = ".venv-build\Scripts\python.exe"
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE) { throw "Falha ao instalar dependencias." }

# --onedir (pasta) abre bem mais rápido que --onefile, que se descompacta a
# cada execução. Só as imagens que o app usa: as de depuração do gerador de
# máscaras (watershed_debug*) ficam de fora.
& $py -m PyInstaller main.py `
    --name SistemaDeAlunos `
    --windowed `
    --noconfirm `
    --clean `
    --add-data "assets\corpos\corpohomem.png;assets\corpos" `
    --add-data "assets\corpos\corpomulher.png;assets\corpos" `
    --add-data "assets\corpos\mascaras_masculino;assets\corpos\mascaras_masculino" `
    --add-data "assets\corpos\mascaras_feminino;assets\corpos\mascaras_feminino" `
    --add-data "musculogordura.png;."
if ($LASTEXITCODE) { throw "Falha no PyInstaller." }

$zip = "dist\SistemaDeAlunos.zip"
# O antivírus costuma segurar os arquivos recém-gerados por alguns segundos.
for ($tentativa = 1; ; $tentativa++) {
    try {
        if (Test-Path $zip) { Remove-Item $zip }
        Compress-Archive -Path "dist\SistemaDeAlunos\*" -DestinationPath $zip
        break
    } catch {
        if ($tentativa -ge 10) { throw }
        Start-Sleep -Seconds 3
    }
}
Write-Host ""
Write-Host "Pronto: $zip  -- envie este arquivo para uma nova Release no GitHub."
