# Tâche planifiée Windows de la mise à jour automatique (T08d, bloc G, décisions 179 à 181 et 226) :
# `forever update --auto`, comme le hook de démarrage (même verrou `<cache>\update\lock`, même journal
# `<cache>\update\run-<horodatage>.log`), chaque jour à 08:00, lancée dès que possible si l'heure est passée, seulement
# si le réseau est disponible, 2 h au plus. Lancée par l'utilisateur, jamais par l'agent ; sans droits administrateur.
# Le passage travaille dans le clone dédié du cache (<cache>\update\repo), jamais dans l'arbre de travail de la
# session ; réseau accordé par la décision 179 (wago.tools, WoWDBDefs, git et gh du clone). Remplace l'ancienne tâche
# « WoW Forever - veille locale » (`forever watch --report`, qui ne faisait que regarder) : la retire si elle existe.
#
# L'action est le `pythonw.exe` de l'interpréteur de base (aucune fenêtre : l'environnement n'en a pas, et une tâche
# qui lance une console l'ouvre sur le bureau) ; il lance `python -m forever.update_task`, qui démarre le passage avec
# le vrai interpréteur dans l'environnement du dépôt et l'attend (la limite de 2 h l'atteint).
#
#   powershell -File scripts\install_update_task.ps1            # créer ou remplacer la tâche (08:00 chaque jour)
#   powershell -File scripts\install_update_task.ps1 -Print     # contenu de la tâche en JSON, sans rien créer
#   powershell -File scripts\install_update_task.ps1 -WhatIf    # montrer ce qui serait fait, sans rien créer
#   powershell -File scripts\install_update_task.ps1 -Remove    # retirer la tâche
#   powershell -File scripts\install_update_task.ps1 -At 21:30  # autre heure
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Remove,
    [switch]$Print,
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

# Interpréteur de base de l'environnement : clé `home` de .venv\pyvenv.cfg.
$cfg = Join-Path $repo ".venv\pyvenv.cfg"
if (-not (Test-Path $cfg)) {
    throw "Environnement absent ($cfg) : lancer « uv sync » dans $repo avant de créer la tâche."
}
$pyHome = (Get-Content $cfg | Where-Object { $_ -match '^\s*home\s*=' } | Select-Object -First 1) -replace '^\s*home\s*=\s*', ''
$pythonw = Join-Path $pyHome.Trim() "pythonw.exe"
if (-not (Test-Path $pythonw)) {
    throw "Interpréteur sans fenêtre introuvable : $pythonw (réinstaller Python avec pythonw.exe)."
}

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "-m forever.update_task" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $At
# Heure locale, sans « Z » : sinon la tâche suit l'UTC et glisse d'une heure au changement d'heure.
$trigger.StartBoundary = (Get-Date $At).ToString("yyyy-MM-dd'T'HH:mm:ss")
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$description = "Mise à jour automatique de forever-core (T08d, décision 226) : forever update --auto, comme le hook " +
    "de démarrage (même verrou, même journal <cache>\update\run-*.log) ; jeu, correctifs du serveur, journaux, " +
    "addons ; écriture par le clone dédié seulement si la règle d'automatisme tient, sinon attente d'accord."

if ($Print) {
    # Contenu de la tâche, sans rien créer ni retirer (vérifié par tests/unit/test_scheduled_update_task.py).
    $content = [ordered]@{
        TaskName                  = $TaskName
        OldTaskName               = $OldTaskName
        Execute                   = $action.Execute
        Arguments                 = $action.Arguments
        WorkingDirectory          = $action.WorkingDirectory
        Trigger                   = [ordered]@{
            Kind          = "Daily"
            DaysInterval  = [int]$trigger.DaysInterval
            StartBoundary = [string]$trigger.StartBoundary
        }
        StartWhenAvailable        = [bool]$settings.StartWhenAvailable
        RunOnlyIfNetworkAvailable = [bool]$settings.RunOnlyIfNetworkAvailable
        ExecutionTimeLimit        = [string]$settings.ExecutionTimeLimit
        MultipleInstances         = [string]$settings.MultipleInstances
        LogonType                 = [string]$principal.LogonType
        RunLevel                  = [string]$principal.RunLevel
        Description               = $description
    }
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    $content | ConvertTo-Json -Depth 4
    return
}

if (Get-ScheduledTask -TaskName $OldTaskName -ErrorAction SilentlyContinue) {
    if ($PSCmdlet.ShouldProcess($OldTaskName, "Retirer l'ancienne tâche de veille (remplacée par la mise à jour)")) {
        Unregister-ScheduledTask -TaskName $OldTaskName -Confirm:$false
        Write-Output "Ancienne tâche « $OldTaskName » retirée."
    }
}

if ($PSCmdlet.ShouldProcess($TaskName, "Créer ou remplacer la tâche planifiée (chaque jour à $At, 2 h au plus)")) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Principal $principal -Description $description -Force | Out-Null
    Write-Output "Tâche « $TaskName » créée : chaque jour à $At (ou dès que possible), réseau requis, 2 h au plus."
    Write-Output "  action : $pythonw -m forever.update_task (forever update --auto --json --log) dans $repo"
    Write-Output "  journal de chaque passage : <cache>\update\run-<horodatage>.log ; suivi : uv run forever update status"
}
