# Tâche planifiée Windows de la mise à jour automatique (T08d, bloc G, décisions 179 à 181) : `forever update --auto
# --json` une fois par jour, limitée à 2 h. Lancée par l'utilisateur, jamais par l'agent. Le passage travaille dans le
# clone dédié du cache (<cache>/update/repo), jamais dans l'arbre de travail de la session ; réseau accordé par la
# décision 179 (wago.tools, WoWDBDefs, git et gh du clone). Remplace l'ancienne tâche « veille locale » : l'archivage
# et la veille font partie du passage.
#
#   powershell -File scripts\install_update_task.ps1            # créer ou remplacer la tâche (08:00 chaque jour)
#   powershell -File scripts\install_update_task.ps1 -WhatIf    # montrer ce qui serait fait, sans rien créer
#   powershell -File scripts\install_update_task.ps1 -Remove    # retirer la tâche
#   powershell -File scripts\install_update_task.ps1 -At 21:30  # autre heure
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Remove,
    [string]$At = "08:00",
    [string]$TaskName = "WoW Forever - mise à jour",
    [string]$OldTaskName = "WoW Forever - veille locale"
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

if (Get-ScheduledTask -TaskName $OldTaskName -ErrorAction SilentlyContinue) {
    if ($PSCmdlet.ShouldProcess($OldTaskName, "Retirer l'ancienne tâche de veille (remplacée par la mise à jour)")) {
        Unregister-ScheduledTask -TaskName $OldTaskName -Confirm:$false
        Write-Output "Ancienne tâche « $OldTaskName » retirée."
    }
}

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) {
    throw "uv introuvable dans le PATH : installer uv (https://docs.astral.sh/uv/) avant de créer la tâche."
}
$action = New-ScheduledTaskAction -Execute $uv -Argument "run --project `"$repo`" forever update --auto --json" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$description = "Mise à jour automatique de forever-core (T08d) : jeu, correctifs du serveur, journaux, addons ; " +
    "écriture par le clone dédié seulement si la règle d'automatisme tient, sinon attente d'accord."

if ($PSCmdlet.ShouldProcess($TaskName, "Créer ou remplacer la tâche planifiée (chaque jour à $At, 2 h au plus)")) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Description $description -Force | Out-Null
    Write-Output "Tâche « $TaskName » créée : chaque jour à $At, `uv run forever update --auto --json` dans $repo."
}
