# Tâche planifiée Windows de la veille locale (T08b, bloc G) : `forever watch --report` une fois par jour, hors ligne.
# Lancée par l'utilisateur, jamais par l'agent. Le résumé va dans <cache>/watch/report.json ; la ligne de démarrage
# de session suivante l'affiche. Aucun accès réseau : la veille ne lance rien, elle propose des commandes.
#
#   powershell -File scripts\install_watch_task.ps1            # créer ou remplacer la tâche (08:00 chaque jour)
#   powershell -File scripts\install_watch_task.ps1 -WhatIf    # montrer ce qui serait fait, sans rien créer
#   powershell -File scripts\install_watch_task.ps1 -Remove    # retirer la tâche
#   powershell -File scripts\install_watch_task.ps1 -At 21:30  # autre heure
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Remove,
    [string]$At = "08:00",
    [string]$TaskName = "WoW Forever - veille locale"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot

if ($Remove) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        if ($PSCmdlet.ShouldProcess($TaskName, "Retirer la tâche planifiée")) {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
            Write-Output "Tâche « $TaskName » retirée."
        }
    } else {
        Write-Output "Aucune tâche « $TaskName »."
    }
    return
}

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) {
    throw "uv introuvable dans le PATH : installer uv (https://docs.astral.sh/uv/) avant de créer la tâche."
}
$action = New-ScheduledTaskAction -Execute $uv -Argument "run --project `"$repo`" forever watch --report" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$description = "Veille locale de forever-core (T08b) : build du client, addons, correctifs, journaux ; hors ligne, rien n'est lancé."

if ($PSCmdlet.ShouldProcess($TaskName, "Créer ou remplacer la tâche planifiée (chaque jour à $At)")) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Description $description -Force | Out-Null
    Write-Output "Tâche « $TaskName » créée : chaque jour à $At, `uv run forever watch --report` dans $repo."
}
