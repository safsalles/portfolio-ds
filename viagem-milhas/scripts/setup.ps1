# Abre o assistente de configuracao (gera o config.toml na raiz do projeto).
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONPATH = Join-Path $root "src"
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
& $python -m verificador.setup
exit $LASTEXITCODE
