# Journaux de combat (fixtures)

## `WoWCombatLog-092726_145346.anon.txt`
- Origine : `C:\Program Files (x86)\World of Warcraft\_classic_beta_\Logs\WoWCombatLog-092726_145346.txt`, journal réel du client 1.60.1 (build 70009 installé), 2026-09-27 14:53:46 → 14:55:24, Durotar, 194 lignes (en-tête compris), format `COMBAT_LOG_VERSION 22`, `ADVANCED_LOG_ENABLED 1`, `PROJECT_ID 18`.
- Anonymisation : `uv run python scripts/extract_combatlog_fixture.py <journal>` (décision 8 du plan T04). Le joueur « à moi » (Mage, drapeau `0x511`) devient `Moi-Royaume` / `Player-0000-00000000` ; les 26 autres joueurs `Joueur<N>-Royaume` / `Player-0000-0000000N` dans l'ordre de première apparition ; les familiers (nom choisi par le joueur) `Familier<N>`. Créatures, sorts et chiffres intacts ; nombre de lignes et d'événements conservés. Ne pas éditer à la main.

## `synthetic/`
Cas limites écrits pour les tests (pas des journaux réels) :
- `version21.txt` : en-tête `COMBAT_LOG_VERSION 21` → `unsupported_log`.
- `not_advanced.txt` : `ADVANCED_LOG_ENABLED 0` → `unsupported_log`.
- `empty.txt` : fichier vide (comme le second journal du 2026-09-27) → `unsupported_log`.
- `truncated.txt` : ligne 3 tronquée dans le bloc avancé → `data_schema` avec le numéro de ligne.
- `unknown_event.txt` : événement inconnu `FOREVER_NEW_EVENT` (gardé brut, compté).
- `ignite_pairs.txt` (T04c) : Ignite roulant écrit d'après les formes réelles du format 22 (lignes `SPELL_DAMAGE` et `SPELL_PERIODIC_DAMAGE` des fixtures) ; montants choisis, pas des chiffres de jeu. Critique isolé de Fireball (133) de 200 sur le PNJ 3099 à 10:00:01, tics d'Ignite (412538) de 40 à +2 s et +4 s ; deux critiques de 200 et 150 à 1 s d'écart sur le PNJ 3100 à 10:01:00, tics de 70 à +3 s et +5 s (règle roulante de la décision 2, part 40 %).
- `hp_conflict.txt` : deux sangliers 3099 de niveau 6 avec des PV max différents (120 et 125) → conflit ; nom de joueur non ASCII (`Élève-Royaume`).
- `multi_power.txt` : bloc avancé à plusieurs ressources (`3|4,46|2,100|5,35|2` : énergie et points de combo), ligne relevée dans `WoWCombatLog-092726_150346.txt` (joueur anonymisé) → ressource principale retenue.
- `summoned.txt` : totem de feu (2523) invoqué par un joueur (propriétaire non nul dans le bloc avancé) → exclu des PV de monstres.
- `absorbed.txt` : `SPELL_ABSORBED` sans puis avec le sort de l'attaquant (disposition variable, relevée dans le second journal) → deux unités lues, reste brut.
- `missed_first.txt` : un Frostbolt résisté puis un immunisé **avant** le premier bloc avancé de la cible, puis un touché → le raté compte à l'écart de niveau de la cible ; IMMUNE hors de la table de toucher.

## `WoWCombatLog-092726_150346.anon.txt.gz`
- Origine : `…\_classic_beta_\Logs\WoWCombatLog-092726_150346.txt`, journal réel du client 1.60.1 (build 70009), 2026-09-27 15:03:46 → 16:48:23, les Tarides (`uiMapID` 1413), 25 902 lignes (6,4 Mo), même en-tête que la première fixture.
- Extraction (décision 1 du plan T04b) : `uv run python scripts/extract_combatlog_fixture.py <journal> --useful --gzip`. Filtre des événements utiles **avant** l'anonymisation : tout événement dont la source ou la destination est le Mage « à moi » (incantations, ratés, baguette, effets), tout événement de dégâts dont le bloc avancé décrit une créature (PV des monstres, quelle que soit la cible), les morts de créatures (`UNIT_DIED`, `PARTY_KILL`) et les changements de carte ; 3 330 lignes (3 329 événements). Anonymisation identique à la première fixture ; gzip déterministe (`mtime` 0, sans nom de fichier). Ne pas éditer à la main.
- Contrôle au moment de l'extraction : mêmes mesures que le journal complet (47 intervalles entre sorts sous recharge globale, 98 sans filtre, 29 relevés de PV sur 19 PNJ, 0 conflit, coûts identiques, 334 touchés dont 53 de baguette).
- Le lecteur (`forever/pipeline/combatlog.py`) lit les `.txt.gz` comme les `.txt` ; `forever logs scan` et `forever logs measure <dossier>` les listent.
