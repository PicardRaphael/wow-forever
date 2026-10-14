<#
.SYNOPSIS
Installe le plugin Claude Code « forever » au niveau utilisateur. Même script sur chaque PC, relançable sans risque.

.DESCRIPTION
1. Contrôle git (Git for Windows fournit aussi le bash des hooks), uv et claude.
2. Fixe la variable d'environnement utilisateur FOREVER_HOME (ce dépôt).
3. Synchronise l'environnement Python du dépôt (uv sync), puis fixe FOREVER_WOW_DIR sur l'installation que choisit
   forever wow list (bêta, ou version finale adoptée par forever wow adopt ; ou -WowDir) ; demande l'accord avant
   de remplacer une valeur différente.
4. Déclare la marketplace locale du dépôt (wow-forever), installe le plugin forever@wow-forever en portée
   utilisateur, ou le met à jour s'il est déjà installé.
5. Contrôles : validation du plugin, état des données sans réseau, plugin présent et activé.

Lancement, depuis la racine du dépôt (contourne la politique d'exécution des scripts pour ce seul lancement) :
    powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1
Mise à jour : git pull, puis la même commande.

.PARAMETER WowDir
Dossier du client (celui qui contient Interface et Logs), s'il n'est pas trouvé par forever wow list.

.PARAMETER Print
Affiche seulement l'installation choisie et sa raison, sans rien changer (diagnostic, LN1).
#>
[CmdletBinding()]
param(
    [string]$WowDir = "",
    [switch]$Print
)

$ErrorActionPreference = "Stop"
$Marketplace = "wow-forever"
$Plugin = "forever@wow-forever"

function Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }

function Fail([string]$Message) {
    Write-Host "Erreur : $Message" -ForegroundColor Red
    exit 1
}

function Invoke-Checked([string]$What, [scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { Fail "$What a échoué (code de sortie $LASTEXITCODE)." }
}

function Read-WowChoice([string]$Project) {
    # Choix de forever (LN1) : bêta, version finale adoptée, ou dossier forcé ; --no-sync : jamais de réseau ici.
    $text = (& uv run --no-sync --quiet --project $Project forever wow list --json | Out-String)
    if ($LASTEXITCODE -ne 0) { Fail "forever wow list --json en échec (code de sortie $LASTEXITCODE)." }
    return ($text | ConvertFrom-Json)
}

function Read-Json([scriptblock]$Command) {
    $text = (& $Command | Out-String)
    if ($LASTEXITCODE -ne 0) { Fail "commande claude en échec (code de sortie $LASTEXITCODE)." }
    # Windows PowerShell 5.1 rend un tableau JSON comme un seul objet : ForEach-Object en émet les éléments.
    return ($text | ConvertFrom-Json | ForEach-Object { $_ })
}

if ($Print) {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $here = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $listing = Read-WowChoice $here
    Write-Output "Installation choisie : $($listing.choice.folder) ($($listing.reason))"
    Write-Output "FOREVER_WOW_DIR actuel : $([Environment]::GetEnvironmentVariable('FOREVER_WOW_DIR', 'User'))"
    exit 0
}

# 1. Outils requis
Step "Contrôle des outils"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail "git introuvable : installer Git for Windows (https://git-scm.com/download/win), qui fournit aussi le bash des hooks."
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Fail "uv introuvable : installer uv (https://docs.astral.sh/uv/getting-started/installation/)."
}
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Fail "claude introuvable : installer Claude Code (https://code.claude.com/docs/fr/setup)."
}

# 2. Dépôt
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path -LiteralPath (Join-Path $Root "pyproject.toml"))) { Fail "dépôt introuvable autour de $PSScriptRoot." }
if (-not (Test-Path -LiteralPath (Join-Path $Root ".claude-plugin\marketplace.json"))) {
    Fail "marketplace absente ($Root\.claude-plugin\marketplace.json) : mettre le dépôt à jour (git pull)."
}
[Environment]::SetEnvironmentVariable("FOREVER_HOME", $Root, "User")
$env:FOREVER_HOME = $Root
Step "FOREVER_HOME = $Root"

# 4. Environnement Python
Step "Synchronisation de l'environnement Python"
Invoke-Checked "uv sync" { uv sync --project $Root }

# 4 bis. Dossier du client : choix de `forever wow list --json` (LN1), accord avant de remplacer une autre valeur
$previous = [Environment]::GetEnvironmentVariable("FOREVER_WOW_DIR", "User")
if ($WowDir) {
    $wow = $WowDir
    $reason = "dossier donné par -WowDir"
} else {
    $listing = Read-WowChoice $Root
    $wow = $listing.choice.folder
    $reason = $listing.reason
}
if ($wow) {
    $apply = $true
    if ($previous -and $previous -ne $wow) {
        $answer = Read-Host "FOREVER_WOW_DIR vaut $previous ; forever choisit $wow ($reason). Remplacer ? [o/N]"
        $apply = $answer -match '^(o|oui)$'
    }
    if ($apply) {
        [Environment]::SetEnvironmentVariable("FOREVER_WOW_DIR", $wow, "User")
        $env:FOREVER_WOW_DIR = $wow
        Step "FOREVER_WOW_DIR = $wow ($reason)"
    } else {
        Step "FOREVER_WOW_DIR gardé : $previous (forever wow list pour revoir le choix)"
    }
} else {
    Write-Warning ("Client WoW Forever introuvable ($reason) : FOREVER_WOW_DIR n'est pas fixée. Relancer avec " +
        "-WowDir <dossier du client>, ou déclarer sa racine dans FOREVER_WOW_ROOTS. Le plugin fonctionne sans, sauf " +
        "les zones (Questie) et les journaux de combat.")
}

# 5. Marketplace et plugin
Step "Marketplace locale $Marketplace"
$markets = @(Read-Json { claude plugin marketplace list --json })
if ($markets | Where-Object { $_.name -eq $Marketplace }) {
    Invoke-Checked "mise à jour de la marketplace" { claude plugin marketplace update wow-forever }
} else {
    Invoke-Checked "ajout de la marketplace" { claude plugin marketplace add $Root --scope user }
}

Step "Plugin $Plugin (portée utilisateur)"
$plugins = @(Read-Json { claude plugin list --json })
if ($plugins | Where-Object { $_.id -eq $Plugin -and $_.scope -eq "user" }) {
    Invoke-Checked "mise à jour du plugin" { claude plugin update forever@wow-forever --scope user }
} else {
    Invoke-Checked "installation du plugin" { claude plugin install forever@wow-forever --scope user }
}

# 6. Contrôles
Step "Contrôles"
Invoke-Checked "validation du plugin" { claude plugin validate --strict $Root }
Invoke-Checked "état des données" { uv run --no-sync --quiet --project $Root forever status --offline }
$installed = @(Read-Json { claude plugin list --json }) | Where-Object { $_.id -eq $Plugin -and $_.scope -eq "user" }
if (-not $installed) { Fail "plugin $Plugin absent de claude plugin list." }
if (-not $installed.enabled) { Fail "plugin $Plugin désactivé : claude plugin enable $Plugin" }

Write-Host ""
Write-Host "Plugin $Plugin installé." -ForegroundColor Green
Write-Host "Ouvrir un NOUVEAU terminal (pour les variables d'environnement), puis lancer claude depuis n'importe quel dossier."
Write-Host "Mode d'emploi : docs\USAGE.md"
