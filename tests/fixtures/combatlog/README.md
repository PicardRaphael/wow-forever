# Journaux de combat (fixtures)

## `WoWCombatLog-092726_145346.anon.txt`
- Origine : `C:\Program Files (x86)\World of Warcraft\_classic_beta_\Logs\WoWCombatLog-092726_145346.txt`, journal réel du client 1.60.1 (build 70009 installé), 2026-09-27 14:53:46 → 14:55:24, Durotar, 194 lignes (en-tête compris), format `COMBAT_LOG_VERSION 22`, `ADVANCED_LOG_ENABLED 1`, `PROJECT_ID 18`.
- Anonymisation : `uv run python scripts/extract_combatlog_fixture.py <journal>` (décision 8 du plan T04). Le joueur « à moi » (Mage, drapeau `0x511`) devient `Moi-Royaume` / `Player-0000-00000000` ; les 26 autres joueurs `Joueur<N>-Royaume` / `Player-0000-0000000N` dans l'ordre de première apparition. Créatures, sorts et chiffres intacts ; nombre de lignes et d'événements conservés. Ne pas éditer à la main.

## `synthetic/`
Cas limites écrits pour les tests (pas des journaux réels) :
- `version21.txt` : en-tête `COMBAT_LOG_VERSION 21` → `unsupported_log`.
- `not_advanced.txt` : `ADVANCED_LOG_ENABLED 0` → `unsupported_log`.
- `empty.txt` : fichier vide (comme le second journal du 2026-09-27) → `unsupported_log`.
- `truncated.txt` : ligne 3 tronquée dans le bloc avancé → `data_schema` avec le numéro de ligne.
- `unknown_event.txt` : événement inconnu `FOREVER_NEW_EVENT` (gardé brut, compté).
- `hp_conflict.txt` : deux sangliers 3099 de niveau 6 avec des PV max différents (120 et 125) → conflit ; nom de joueur non ASCII (`Jén-Royaume`).
- `multi_power.txt` : bloc avancé à plusieurs ressources (`3|4,46|2,100|5,35|2` : énergie et points de combo), ligne relevée dans `WoWCombatLog-092726_150346.txt` (joueur anonymisé) → ressource principale retenue.
