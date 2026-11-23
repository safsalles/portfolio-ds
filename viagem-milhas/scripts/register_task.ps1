# Registra a tarefa diaria "VerificadorPassagens" (08:00, usuario atual, so com o usuario logado).
# Se o PC estiver desligado as 08:00, roda assim que ligar. Remover:  Unregister-ScheduledTask -TaskName VerificadorPassagens -Confirm:$false
$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root "scripts\run_daily.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" `
    -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "VerificadorPassagens" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Verificador de passagens e milhas (GIG-BUD / BER-GIG)" -Force | Out-Null
Get-ScheduledTask -TaskName "VerificadorPassagens" | Select-Object TaskName, State
