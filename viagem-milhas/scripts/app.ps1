# Abre a interface no navegador (Streamlit). Precisa de:  pip install -r requirements-app.txt
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
# A chave da SerpApi fica na variavel de ambiente do usuario.
if (-not $env:SERPAPI_KEY) {
    $env:SERPAPI_KEY = [Environment]::GetEnvironmentVariable("SERPAPI_KEY", "User")
}
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
& $python -m streamlit run (Join-Path $root "src\verificador\app.py")
exit $LASTEXITCODE
