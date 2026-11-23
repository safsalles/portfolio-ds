# Executa o verificador uma vez. Usado pelo Agendador de Tarefas e para testes manuais.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONPATH = Join-Path $root "src"
# O Agendador roda como o proprio usuario; a chave fica na variavel de ambiente do usuario.
if (-not $env:SERPAPI_KEY) {
    $env:SERPAPI_KEY = [Environment]::GetEnvironmentVariable("SERPAPI_KEY", "User")
}
& (Join-Path $root ".venv\Scripts\python.exe") -m verificador.run_daily
exit $LASTEXITCODE
