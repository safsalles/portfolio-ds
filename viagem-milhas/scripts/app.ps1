# Abre a interface no navegador (Streamlit). Precisa de:  pip install -r requirements-app.txt
# -NoBrowser: nao abre o navegador (usado em testes).
param([switch]$NoBrowser)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$port = 8501
$url = "http://localhost:$port"

# Se a interface ja esta aberta, so abre a pagina de novo.
if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "A interface ja esta rodando. Abrindo $url ..."
    if (-not $NoBrowser) { Start-Process $url }
    exit 0
}

# A chave da SerpApi fica na variavel de ambiente do usuario.
if (-not $env:SERPAPI_KEY) {
    $env:SERPAPI_KEY = [Environment]::GetEnvironmentVariable("SERPAPI_KEY", "User")
}
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

# Abre o navegador alguns segundos depois de o servidor subir.
if (-not $NoBrowser) {
    Start-Job -ScriptBlock { param($u) Start-Sleep -Seconds 4; Start-Process $u } -ArgumentList $url | Out-Null
}

Write-Host "Verificador de voos rodando em $url"
Write-Host "Para encerrar, feche esta janela (ou aperte Ctrl+C)."
& $python -m streamlit run (Join-Path $root "src\verificador\app.py") --server.headless true --server.port $port --browser.gatherUsageStats false
exit $LASTEXITCODE
