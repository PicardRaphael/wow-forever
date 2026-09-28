# Feuille de route — tranches verticales

Chaque tranche traverse toutes les couches (données → moteur → outil → test) et se termine par un résultat utilisable.
Une tranche = 1 à 3 sessions Claude Code. Ne commence la suivante que lorsque `uv run tasks.py verify` est vert.

L'ordre de la table est l'ordre d'exécution. Il suit les priorités du joueur (PvP en champs de bataille, donjons et leveling d'abord, raid ensuite) et les dépendances (mémoire joueur T07 pour tout suivi de progression, API Blizzard après le lancement) ; le plugin (T06) et l'aide au leveling en jeu (FA1) passent juste après T05. Une tranche gardée par un événement extérieur (condition écrite dans sa colonne « Dépend de ») est sautée tant que la condition n'est pas remplie, puis reprise à la première fin de tranche qui suit : elle ne bloque pas les suivantes (décision 62).

Tranches lettrées par domaine (sans renuméroter les tranches T existantes) : PV (PvP), DJ (donjons), LG (Legacy), MT (métiers), RP (réputations), EC (économie). Les sources de chaque domaine sont résumées dans `docs/SPEC.md` (section « Domaines et sources ») et détaillées dans chaque section ci-dessous. Outils et skills prévus (provisoires, forme fixée au plan de chaque tranche) : `docs/ARCHITECTURE.md`, section « Outils et skills prévus ».

| Tranche | But | Dépend de |
| --- | --- | --- |
| T01 | Squelette de bout en bout : `forever status` + consultation d'un sort, CLI + MCP + provenance + CI | — |
| T02 | Port du cœur de mécaniques du skill Mage + registre + tests de référence | T01 |
| T03 | Pipeline de données : builds, fetch, decode, diff, verify, report (tests hors ligne) | T01 |
| T04a | Sources locales du client : journaux de combat, Questie, table des monstres, points de base par niveau, preuves du registre, addon ForeverLogger | T02, T03 |
| T04b | Simulateurs de leveling (MC + analytique) exposés en MCP + graphique | T04a |
| T04c | Simulateur fiable pour comparer les builds : Ignite, Arcane Blast, recharges, régénération et armure, `forever measures refresh`, zone ou donjon à mon niveau | T04b |
| T04e | Calculs de dégâts fidèles au client : coefficients du client, DoT, multiplicateurs, cumul des bonus | T04c |
| T05 | Optimiseur de talents et conseiller de respec | T04b, T04c, T04e |
| T06 | Plugin Claude Code : skills, hooks, statusline, commandes, sous-agents | T04b |
| T04d | Quêtes propres à Forever et modèle d'XP de Forever (placée après T06 : ses sources viennent de l'inventaire des addons, `tasks/inventaire-addons.md`, et elle ne change pas le classement des builds) | T04c |
| FA1 | ForeverAssist V1 : talent suivant à chaque gain de niveau, comparaison de l'équipement dans l'infobulle, données précalculées par forever | T04b, T05 |
| PV1 | PvP, savoir des 9 classes sans moteur de classe : sorts, recharges, contrôles et durées, défensifs, raciaux, bijoux, rendements décroissants (règles Classic), fiches par affrontement | T03, T05 |
| PV2 | PvP, champs de bataille (objectifs, récompenses, équipement PvP) et monde ouvert ; rendements décroissants mesurés dans les journaux de champs de bataille | PV1, T04a |
| DJ1 | Donjons : niveaux, boss, butin | T03, T04a |
| LG1 | Legacy : défis, points, arbres de bonus, conseil des bonus par personnage (Mage, Paladin, Démoniste) | T03, T04b |
| FA1p | Extension PvP de ForeverAssist V1 : fiche fixe de la classe adverse | FA1, PV1 |
| P06 | Évaluation d'un pont de conversation existant (wow-claude / wow-ai) pointé sur ce dépôt | T06 |
| T07 | Mémoire joueur : fiches du vault, import de l'addon (+ ForeverAssist V2 proposée) | T06 |
| LG2 | Suivi de ma progression Legacy (et, par le même import, honneur et rang PvP) | LG1, T07 |
| MT1 | Métiers : recettes, montée de compétence, points Legacy des métiers | T03, LG1, T07 |
| RP1 | Réputations : factions, paliers, gains, récompenses, suivi | T03, T07 |
| T08 | Veille : workflow planifié, PR de données, note d'impact par personnage | T03, T07 |
| EC1 | Économie : prix de l'hôtel des ventes par l'API Blizzard | T03, MT1 ; condition : lancement du 4 novembre passé et couverture de Forever par l'API vérifiée |
| FA3 | ForeverAssist V3 : compagnon de bureau, analyse des journaux après le combat | T08 |
| T09 | Raid : moteur analytique porté, Monte Carlo, parité avec wowsims Forever | T02 |
| T10 | Équipement : base d'objets par formules du client, optimiseur | T09 |
| T11 | Consommables et préparation de raid | T10 |
| T12 | Paladin, puis Démoniste, puis les autres classes | T09 |
| T13 | (Option) Serveur MCP distant pour Claude.ai et ChatGPT | T06 |

## T01 — Squelette de bout en bout
- **Fait** : paquet `forever` installable avec `uv` ; `forever/data/1.60.1.70009/` initialisé depuis `seed/forever-mage/data/` ; `manifest.json` avec empreintes ; `forever status` (réseau simulé en test) ; `forever lookup spell frostbolt --rank 2` ; serveur MCP avec `forever_status` et `forever_lookup` ; bloc provenance ; `forever manifest --update` (recalcul des empreintes) ; la CI fournie (`.github/workflows/ci.yml`) passe.
- **Hors périmètre** : mécaniques, simulateurs.
- **Critères de fin** :
    - `uv run forever lookup spell frostbolt --rank 2` renvoie 34-38 dégâts, 1,8 s, 35 mana, version 1.60.1.70009, certitude `certain`.
    - `forever status` renvoie `fresh`, `stale`, `unknown` et `silent` selon les réponses simulées (4 tests).
    - Une empreinte modifiée dans `data/` est détectée (1 test).
    - Le serveur MCP liste ses deux outils et répond (test d'intégration).
    - Test de contrat : chaque sortie CLI et MCP contient un bloc `provenance` complet (schéma validé).

## T02 — Cœur de mécaniques et registre
- **Fait** : porter `seed/forever-mage/scripts/fm.py` dans `forever/engine/` (modules : talents, character, spells, hit, crit, damage, casting, mana, cast), en fonctions pures qui reçoivent `GameData` ; constantes absentes des tables dans `forever/data/<version>/mechanics.json` ; créer `forever/registry.py` qui lit et valide `docs/MECHANICS_REGISTRY.yaml` ; `uv run tasks.py verify` échoue si une entrée `modelise` ou mieux n'a pas de test ; porter les 5 tests du seed qui visent `fm.py` (`donnees_completes`, `valeurs_client_70009`, `prerequis`, `legalite`, `couverture_mecaniques` et ses 30 contrôles) plus un test de parité avec `fm.py` ; passer `STRICT_REGISTRY = True` dans `tasks.py` ; `forever explain-mechanic` et l'outil MCP `forever_explain_mechanic`.
- **Reporté** : les 5 autres tests du seed dépendent des simulateurs (T04 : `analytique_proche_du_monte_carlo`, `calibrage_cible_blizzard`, `monte_carlo_reproductible`) ou de l'optimiseur, du PvP et de la respec (T05 : `optimiseur_legal`, `pvp_et_respec`).
- **Critères de fin** :
    - Les 30 contrôles de mécaniques de `seed/forever-mage/tests/run_all.py` passent à l'identique.
    - Chaque entrée du registre marquée `teste` pointe vers au moins un test qui existe.
    - `forever explain-mechanic A5` affiche la formule, la certitude et les sources.

## T03 — Pipeline de données
- **Fait** : `forever builds` (API wago.tools, produit `wow_classic_beta`, tri par date) ; `forever fetch --version X --tables …` (cache, empreintes) ; `forever decode` (talents depuis les tables Trait*, sorts depuis Spell*, noms français et anglais) ; `forever diff A B` ; `forever verify` ; `forever report` (Markdown).
- **Critères de fin** :
    - Tests hors ligne sur des extraits CSV dans `tests/fixtures/wago/1.60.1.70009/`.
    - `decode` reproduit les 54 talents Mage de `talents.json` (clé, nom, arbre, palier, colonne, max, prérequis, ordre, rangs) à partir des fixtures, aux changements confirmés près (`confirmed_changes.json`, vérifié dans les deux sens) ; idem pour les 99 rangs des 15 sorts de `spells.json`.
    - `diff` signale un rang de talent modifié et un sort ajouté (tests).
    - `decode`, `verify` et `report` sur les fixtures : code 0, provenance sur chaque sortie, `forever/data/` inchangé.

## T04a — Sources locales du client et mesures sur journaux
- **Fait** : lecture des journaux de combat (`WoWCombatLog-*.txt`, format 22 avancé) et mesures (PV des monstres, coûts, intervalles, incantations, critiques, touchés et ratés par écart de niveau) ; lecteur local de la base Questie (sans réseau, jamais copiée) ; table des monstres `monsters.json` (journal `certain`, Questie `suppose`) ; points de base des sorts par niveau (`spell_scaling.json`, `rank_values_at_level`) ; champ `preuves` du registre et contrôle de `valide-journal` ; addon ForeverLogger réparé (SavedVariable `ForeverLoggerDB`), script d'installation, test statique des règles de l'addon ; `docs/ADDON.md`. Plan : `tasks/T04-plan.md`.
- **Hors périmètre** : simulateurs (T04b) ; `DBCache.bin` et hotfixes (T08) ; caches WDB ; client de l'API Blizzard ; ForeverAssist (planifié seulement).
- **Critères de fin** :
    - `forever logs measure` sur la fixture anonymisée renvoie PV, coûts, intervalles et critiques, avec provenance, code 0, sans réseau.
    - `forever monsters build` sur les fixtures produit une table où les PNJ mesurés sont `certain` et égaux à Questie ; `monsters.json` et `spell_scaling.json` installés dans 1.60.1.70009 avec manifeste à jour.
    - `rank_values_at_level` reproduit `spells.json` au niveau min(MaxLevel, 60).
    - Le registre refuse un `valide-journal` sans preuve ; B1 porte la preuve du journal.
    - `uv run scripts/install_addon.py --dry-run` affiche la copie prévue ; `test_addon_rules.py` vert.

## T04b — Leveling
- **Fait** : seconde fixture de journal (journal entier filtré aux événements utiles, anonymisé, compressé ; lecteur `.gz`) ; niveau du lanceur par ForeverLogger, puis carnet de Questie, puis `--caster-level` ; B1 validée par deux journaux (50 intervalles, 10e percentile et médiane à 0,05 s de la recharge globale) ; A3 : règle Classic des cibles plus basses (`suppose`) ; correction PV Questie → Forever (H11, `monsters.json` schéma 2) ; `sim_leveling.py` porté (Monte Carlo à impacts différés et analytique, parité à 1e-12 avec le seed en mode `mob_source="seed"`, `spell_level="rank"`) ; chiffres du seed dans `mechanics.json` (clés `leveling.*`), `leveling.json` et `spells.json` restant des copies du seed ; `forever sim leveling`, `forever chart leveling`, outil MCP `forever_sim_leveling` ; tests du seed `analytique_proche_du_monte_carlo`, `calibrage_cible_blizzard` et `monte_carlo_reproductible` portés dans les deux modes ; registre : B6, B7, B13, C1, C5, I1, I6, J2 testées, C2 (Arctic Reach), A17 et A18 (tics du Monte Carlo) complétées, H2 reste absente (le seed n'arme pas la cible). Plan : `tasks/T04b-plan.md`.
- **Critères de fin** (atteints) :
    - Au niveau 12 avec 3 Improved Frostbolt, le Monte Carlo (graine fixe, `mob_source="seed"`, `spell_level="rank"`) reproduit le seed à 1e-12 (donc à ±1 %).
    - L'analytique reste à moins de 15 % du Monte Carlo aux niveaux 12, 16 et 24, dans les deux modes.
    - Le graphique est un fichier PNG déterministe à graine fixe (deux générations identiques octet pour octet).

## T04c — Simulateur fiable, mesures, zones (fait)
- **Fait** : fins de ligne normalisées par Git ; option `rules` des simulateurs (`seed` : parité à 1e-12) ; Ignite roulant (A18) ; escalade d'Arcane Blast et rotation arcane (B11, B15, I1) ; recharge de Fire Blast dans l'analytique (B13) ; armure portée selon le niveau lu dans le client et régénération cumulée (B7, I6) ; `forever measures refresh` ; `forever lookup zones` (I7). Plan : `tasks/T04c-plan.md`.
- **Paramètres de build prêts pour T05** : `armor` (`auto`, `frost`, `mage`) et `ab_stacks` (0 au maximum du talent), avec `ab_dump`.

## T04e — Calculs de dégâts fidèles au client
- **Fait** : coefficients de puissance des sorts lus dans le client (`SpellEffect.EffectBonusCoefficient`, par rang et par effet) en mode `forever`, formule du seed gardée en mode `seed` ; puissance des sorts et période des tics de DoT lues dans le client ; Improved Cone of Cold, Arcane Power et Fire Vulnerability dans le multiplicateur de dégâts ; bonus en pourcentage multipliés entre sources (`probable`) ; pénalité des sorts de bas niveau paramétrable ; exemples chiffrés de la vidéo BVSgeHp3sWU en tests ; protocole de collecte des tests en jeu. Plan : `tasks/T04e-plan.md`.
- **Hors périmètre, avec échéance** : Arcane Power dans les rotations des simulateurs en T05 (sans lui, l'Arcane est sous-évalué en leveling) ; Fire Vulnerability (Scorch et ses cumuls) dans les rotations en T09.
- **Critères de fin** : mode `seed` identique au seed à 1e-12 ; coefficients égaux aux tables du client ; exemples de la vidéo à ±0,5 (trois exclus pour l'arrondi des bornes, question ouverte) ; `uv run tasks.py verify` vert.

## T05 — Talents et respec
- **Fait** : porter les tests du seed `optimiseur_legal` et `pvp_et_respec` ; remonter I5 dans le registre ; comparer les builds avec les simulateurs de T04c, `armor` et `ab_stacks` compris parmi les paramètres de build à optimiser ; Arcane Power dans les rotations des simulateurs (aura et recharge du client, fonctions de T04e), sans quoi l'Arcane est sous-évalué en leveling.
- **Critères de fin** : `forever optimize talents --from 10 --to 30` produit un ordre légal à chaque niveau ; le barème de respec est paramétrable ; tests de légalité et de non-régression.

## T06 — Plugin Claude Code
- **Fait** : skills des domaines disponibles à ce stade (leveling, Mage) ; chaque tranche de domaine suivante ajoute son skill (PvP, donjons, Legacy, métiers, réputations, économie).
- **Critères de fin** : installation locale du plugin ; SessionStart injecte une seule ligne de fraîcheur ; la statusline affiche version et statut ; jeu d'évaluation d'aiguillage de 30 requêtes (60 % doivent déclencher un skill, 40 % non) avec au moins 90 % de bonnes décisions.

## T04d — Quêtes Forever et XP
- **À faire** (reporté de T04c) : ingestion des quêtes propres à Forever (`QuestieForeverDB`) et modèle d'XP (XP des monstres et des quêtes de Forever, remplaçant la règle Classic `leveling.mob_xp`) ; durée d'infobulle dans `tooltip_values`. Routes de leveling : pas de tranche dédiée (le joueur suit RestedXP en jeu ; RestedXP reste exclu comme source de données, `docs/DATA_SOURCES.md`). La réponse « quelle zone ou quel donjon à mon niveau » est faite en T04c (`forever lookup zones`, Questie lu localement, `suppose`) ; DJ1 affinera la partie donjons. Les quêtes de donjon restent ici ; DJ1 s'y réfère.
- **Place** : après T06 (décision 78). Ses sources dépendent de l'inventaire des addons (`tasks/inventaire-addons.md` : ForeverDungeonJournal pour l'XP des quêtes, GearQuestForever pour la liste des quêtes absentes de Questie, tables de quêtes du client) ; l'XP ne change pas le classement des builds de T05, qui compare des taux de dégâts et de temps par monstre.
- **Critères de fin** : à fixer au plan de T04d.

## FA1 — ForeverAssist V1 (affichage de données précalculées)
Addon d'affichage seul (règles et canaux : `docs/ADDON.md`). Aucun calcul de combat dans l'addon : `forever` précalcule, l'addon affiche.
- **Fait** : `forever export-addon` génère `addon/ForeverAssist/Data/Generated.lua` (schéma versionné, build, date de génération, écriture atomique) à partir des calculs de forever pour un personnage : **talent suivant proposé à chaque gain de niveau** (ordre de talents de l'optimiseur T05) et **comparaison de l'équipement dans l'infobulle des objets** (valeur des statistiques au niveau du personnage, calculée par le moteur ; l'addon affiche l'écart avec l'objet porté) ; table des monstres de la zone (PV mesurés, source). Affichage hors combat (`PLAYER_LEVEL_UP`, `TooltipDataProcessor`, `pcall`, `issecretvalue`), panneau `/fa`, avertissement si la build du client diffère de celle des données.
- **Hors périmètre** : fiches PvP (extension FA1p, après PV1) ; conseil en combat, conversation, écriture de SavedVariables (V2), analyse des journaux (V3).
- **Critères de fin** :
    - Le fichier généré est déterministe et validé par un schéma (pytest) ; `Generated.sample.lua` versionné, `Generated.lua` ignoré par git.
    - Au gain de niveau, l'addon affiche le talent prévu pour ce niveau par les données ; l'infobulle d'un objet affiche l'écart avec l'objet porté (tests hors jeu sur bouchons de l'API).
    - `test_addon_rules.py` étendu à ForeverAssist ; procédure de test en jeu dans `docs/ADDON.md`.

## PV1 — PvP : savoir des 9 classes (priorité haute)
Les champs de bataille arrivent bientôt (date à confirmer par annonce officielle, `docs/OPEN_QUESTIONS.md`). T05 garde le profil PvP comparatif du Mage porté du seed (`pvp_et_respec`) ; PV1 élargit le savoir aux 9 classes et comble les limites de ce profil listées dans `seed/forever-mage/references/pvp-model.md` (ni rendements décroissants, ni bijou PvP). PV1 n'attend pas les moteurs par classe de T12 : il ne calcule aucun dégât hors Mage, il consulte et croise des données fixes.
- **Fait** :
    - Décodage étendu (dépendance T03, pas T12) : `decode_rules.json` couvre les lignes de compétence et les arbres de talents des 9 classes, en plus du Mage ; sorts de classe et de talent avec rangs, recharge, recharge globale, durée, portée, école, type d'aura et mécanique de contrôle ; raciaux des races jouables ; bijoux PvP (sort d'utilisation et recharge lus dans les tables d'objets, lecture ciblée, la base d'objets complète reste en T10).
    - Espace de données par classe sans moteur : `GameData` expose les sorts, talents et raciaux des 9 classes ; T12 y branchera les moteurs de classe sans changer ce schéma.
    - Classement de chaque sort : contrôle (catégorie de rendement décroissant, durée pleine, ruptures connues), défensif ou immunité, rupture de contrôle, interruption, dissipation, mobilité. Le classement vient des champs du client ; un sort que les données ne permettent pas de classer est listé comme non résolu, jamais deviné.
    - Rendements décroissants : règles Classic (catégories, fenêtre, paliers) dans un fichier de `forever/data/<version>/`, certitude `suppose`, entrées du registre (nouvelle catégorie à fixer au plan) ; fonction pure dans `forever/engine/` qui donne la durée effective d'une suite de contrôles. Aucun chiffre de ces règles hors des données.
    - Fiches par affrontement, générées depuis les données (jamais recopiées d'un guide) : contrôles subis et leur catégorie, défensifs et immunités adverses avec leur recharge, ruptures et interruptions adverses, mes réponses (sorts de rupture, bijou, raciaux, dissipations), fenêtres à surveiller. Conseils communautaires éventuels : faits sourcés, `suppose`, avec le lien.
    - Profil PvP du Mage (T05) : ajout des rendements décroissants et du bijou PvP, résultat toujours comparatif, jamais un duel simulé.
    - `forever pvp class <classe>`, `forever pvp matchup <ma classe> <classe adverse>`, consultation MCP par `forever_lookup`, domaine `pvp` (paginé, compact ; forme provisoire, `docs/ARCHITECTURE.md`) ; provenance et certitude par champ.
- **Sources** : client (tables des sorts, talents, raciaux, objets ; `certain` ou `probable`) ; annonces officielles (changements PvP de Forever, règles des contrôles) ; communauté (Wowhead Forever, guides PvP : faits sourcés, `suppose`) ; journaux (rien en PV1, mesures en PV2) ; addon (affichage de fiches fixes par l'extension FA1p).
- **Addon** : le suivi en direct des temps de recharge adverses est impossible sur Forever (abonnement au journal de combat refusé aux addons, valeurs de combat secrètes : `docs/research/addon-forever.md`). En jeu, seules des informations fixes s'affichent : la fiche de la classe adverse, jamais un état (recharge en cours, bijou utilisé). Affichage par l'extension FA1p.
- **Hors périmètre** : dégâts et soins des autres classes (T12) ; simulation de duel ; résistances des joueurs ; mesures sur journaux (PV2) ; toute détection d'événement de combat dans un addon.
- **Critères de fin** :
    - `forever decode` sur des fixtures wago étendues produit, pour chacune des 9 classes, ses sorts et talents avec recharge, durée et école ; `verify` vert ; les sorts non classés sont listés dans le rapport.
    - `forever pvp matchup` rend une fiche déterministe pour deux paires de classes fixées en test, avec provenance complète et certitude par champ.
    - La fonction de rendement décroissant reproduit, sur des suites de contrôles de test, les durées attendues par les règles des données (valeurs lues dans les données, pas dans le test).
    - Le profil PvP du Mage change quand on active les rendements décroissants ou le bijou (test de non-régression du mode sans).

## PV2 — PvP : champs de bataille et monde ouvert
- **Fait** :
    - Champs de bataille : liste, niveaux d'accès, objectifs et conditions de victoire, récompenses (monnaie ou honneur, rang, marques : système de Forever à confirmer), temps de partie observés.
    - Équipement PvP : objets, exigences (rang, réputation, niveau), coûts ; statistiques lues dans le client quand elles y sont ; la comparaison chiffrée et l'optimisation restent en T10.
    - PvP en monde ouvert : type de royaume et règles, zones contestées, objectifs mondiaux et leurs récompenses, selon les annonces.
    - Rendements décroissants mesurés dans mes journaux de champs de bataille : `forever logs pvp` relève les contrôles appliqués aux joueurs (aura posée puis retirée), leur rang dans la suite d'une même catégorie et leur durée observée ; les ruptures (dégâts, dissipation, bijou, mort) sont écartées quand le journal les montre. Les entrées du registre passent en `valide-journal` quand `n` atteint `tolerance.n_min`.
    - Fixtures : journal de champ de bataille anonymisé (noms des autres joueurs remplacés, décision 49), compressé.
    - `forever bg info <champ>`, `forever pvp gear`, `forever pvp world` ; consultation MCP par `forever_lookup`, domaine `pvp` étendue.
- **Sources** : client (cartes et listes de champs de bataille, objets PvP, tables de monnaie : noms de tables à identifier à l'inventaire) ; annonces officielles (dates, liste, système de récompenses, règles du monde ouvert) ; communauté (vendeurs et coûts, faits de stratégie sourcés, `suppose`) ; journaux (mes parties : contrôles, recharges adverses observées après coup, durées) ; addon (résultat de partie et honneur relevés hors combat, API à sonder sous `pcall`).
- **Hors périmètre** : suivi de ma progression PvP (repris par LG2, même import après T07) ; suivi des recharges adverses en direct (impossible) ; classement ou matchmaking.
- **Critères de fin** :
    - `forever logs pvp` sur la fixture renvoie les contrôles par catégorie et rang, avec durée observée, écart à la règle des données et provenance, code 0, sans réseau.
    - Au moins une entrée de rendement décroissant porte une preuve de journal contrôlée par le registre, ou la tranche documente le manque de données.
    - `forever bg info` et `forever pvp gear` rendent des données avec source et certitude par champ ; toute information non annoncée est absente, pas devinée.

## DJ1 — Donjons
- **Fait** : liste des donjons de Forever avec plages de niveau (accès, recommandé) ; boss et leur niveau ; butin par boss (objets, emplacement, exigence de classe) avec taux quand une source existe ; donjons nouveaux ou modifiés dans Forever ; lien vers les quêtes de donjon de T04c ; `forever dungeon list --level N`, `forever dungeon info <donjon>`, consultation MCP par `forever_lookup`, domaine `dungeons` ; fichier de données par version avec certitude par champ.
- **Sources** : client (instances, niveaux, objets ; tables de journal de rencontre et de butin à identifier à l'inventaire, sans présumer de leur présence ; les taux de butin sont absents du client, `docs/DATA_SOURCES.md`) ; annonces officielles (donjons nouveaux ou modifiés, niveaux) ; communauté (Wowhead Forever pour le butin et les taux, `suppose` ; ForeverDungeonJournal en recoupement, non ingéré tant que sa licence n'est pas vérifiée) ; journaux (niveau et PV des boss et des monstres par le bloc avancé, registre H1, durée des passages) ; addon (butin observé relevé hors combat par ForeverLogger, API à sonder sous `pcall`).
- **Hors périmètre** : stratégies de boss détaillées recopiées d'un guide ; valeur chiffrée d'un objet pour un personnage (T10) ; raids (T09 à T11).
- **Critères de fin** :
    - `forever dungeon list --level N` et `forever dungeon info` sur les données de test rendent niveaux, boss et butin avec provenance ; un taux absent est affiché comme inconnu.
    - Le niveau d'un boss mesuré dans une fixture de journal l'emporte sur la valeur communautaire et passe `certain`.

## LG1 — Legacy : catalogue et conseil par personnage
Placé avant T07 parce que les bonus Legacy pèsent sur le leveling : le catalogue et le conseil n'ont pas besoin de la mémoire joueur (état Legacy saisi en paramètre). Le suivi vient en LG2.
- **Fait** : catalogue des défis (conditions, points rapportés), des points et des arbres de bonus (nœuds, coûts, prérequis, effets, réinitialisation) ; effets chiffrés dans les données quand le client ou une annonce les donne, sinon marqués inconnus ; conseil des bonus par personnage : Mage chiffré par le moteur (effet sur le temps par monstre et l'XP par heure du simulateur de leveling), Paladin et Démoniste sans moteur de classe (T12) par un classement fondé sur les effets et l'objectif du joueur, marqué `suppose` et recalculé après T12 ; registre G5 mis à jour ; `forever legacy catalog`, `forever legacy advise --class <classe> [--state F] [--goal leveling|pvp|raid]`, consultation MCP par `forever_lookup`, domaine `legacy` pour le catalogue, outil de calcul séparé pour le conseil (il appelle le simulateur de leveling).
- **Sources** : client (tables des arbres et des défis à identifier à l'inventaire) ; annonces officielles (système Legacy, état en bêta et au lancement) ; communauté (Icy Veins et Wowhead Forever, noms d'arbres divergents à recouper, `suppose`) ; journaux (validation d'un bonus mesurable, par exemple un gain d'XP) ; addon (lecture de la progression : LG2).
- **Hors périmètre** : suivi de ma progression (LG2) ; points Legacy des métiers (MT1, qui s'appuie sur ce catalogue).
- **Critères de fin** :
    - Le catalogue passe `verify` (prérequis cohérents, coûts présents ou marqués inconnus, source par entrée).
    - `forever legacy advise` rend un ordre déterministe pour les trois classes, avec justification et certitude ; pour le Mage, le gain vient d'un appel au simulateur de leveling (aucun calcul dans l'outil).

## FA1p — Extension PvP de ForeverAssist V1
- **Fait** : `forever export-addon` ajoute à `Generated.lua` la **fiche PvP fixe de chaque classe adverse** (données de PV1 : contrôles et leur catégorie de rendement décroissant, défensifs et immunités, ruptures et interruptions, avec leurs recharges nominales) ; l'addon l'affiche hors combat (panneau `/fa`, classe de la cible lue sous `pcall` et `issecretvalue`). Le suivi en direct des recharges adverses est impossible dans un addon sur Forever (abonnement au journal de combat refusé, valeurs de combat secrètes) : aucun état n'est affiché (recharge en cours, bijou utilisé).
- **Hors périmètre** : toute détection d'événement de combat ; conseil en combat.
- **Critères de fin** :
    - Le schéma versionné de `Generated.lua` inclut les fiches ; génération déterministe (pytest) ; `Generated.sample.lua` mis à jour.
    - La fiche d'une classe adverse s'affiche hors combat, sans aucun abonnement à un événement de combat (tests hors jeu sur bouchons de l'API) ; `test_addon_rules.py` vert.

## P06 — Évaluation d'un pont de conversation (après T06)
- **Fait** : évaluer un pont existant (wow-claude / wow-ai, voir `docs/research/addon-forever.md`, section 3.5) dont la session Claude Code est pointée sur ce dépôt, pour disposer en jeu des outils et des données de forever-core par le serveur MCP du plugin (T06). Grille : conformité (zone grise : lecture d'écran, aucune action de jeu), sécurité (liste d'autorisations stricte, jamais de mode sans permission, commandes réseau exclues), fragilité face aux builds, installation sous Windows.
- **Hors périmètre** : écrire ou vendoriser un pont dans ce dépôt ; toute entrée simulée.
- **Critères de fin** : décision écrite dans `docs/DECISIONS.md` (adopter, reporter ou écarter) avec la grille remplie ; si adopté, procédure d'installation et liste d'autorisations dans `docs/ADDON.md`.

## T07 — Mémoire joueur
- **Critères de fin** : import d'un export d'addon d'exemple ; fiche écrite dans le vault avec la version du jeu ; une fiche plus ancienne que la version courante est signalée.

## LG2 — Suivi de ma progression Legacy
- **Fait** : lecture de la progression Legacy du compte (défis faits, points gagnés et dépensés, nœuds pris) par l'addon hors combat (ForeverLogger ou ForeverAssist V2, API à sonder sous `pcall`), import par la voie de T07 dans `legacy.json` du vault (avec la version du jeu) ; `forever legacy status` : points disponibles, prochains défis accessibles par personnage, conseil de LG1 recalculé sur l'état réel ; par le même import, honneur et rang PvP (PV2) dans la fiche du personnage.
- **Sources** : addon (source principale) ; client et catalogue de LG1 ; annonces officielles (changements du système) ; communauté (recoupement) ; journaux (rien).
- **Hors périmètre** : écriture en jeu ; note d'impact Legacy par version (T08).
- **Critères de fin** : import d'une SavedVariable d'exemple (fixture) ; `legacy.json` régénéré de façon déterministe ; une progression plus ancienne que la version courante est signalée ; `forever legacy status` avec provenance.

## MT1 — Métiers
- **Fait** : recettes par métier (composants, objet créé, niveau requis, seuils de couleur de difficulté) ; sources des recettes (entraîneur, vendeur, butin, quête) ; changements de Forever (recettes retirées ou ajoutées, bonus de métier) ; plan de montée de compétence `forever profession plan <métier> --from A --to B` qui minimise le nombre de fabrications (puis le coût quand EC1 fournit les prix) ; points Legacy des métiers par palier, depuis le catalogue de LG1 ; niveaux actuels lus dans la fiche du vault (T07) sinon saisis ; registre G6 mis à jour ; consultation MCP par `forever_lookup`, domaine `professions` pour les recettes, outil de calcul séparé pour le plan de montée.
- **Sources** : client (lignes de compétence et recettes, composants, objets créés, seuils de couleur ; certain) ; annonces officielles (changements de métiers, points Legacy) ; communauté (listes d'entraîneurs et sources de recettes, absentes du client ; chance de gain de point par couleur, règle Classic `suppose` ; `alcaras/forever-ref` en recoupement) ; journaux (rien : l'artisanat n'est pas un événement de combat utile) ; addon (niveaux de compétence et recettes connues, lus hors combat sous `pcall`).
- **Hors périmètre** : prix et rentabilité (EC1) ; consommables de raid (T11).
- **Critères de fin** : recettes décodées depuis des fixtures wago pour deux métiers ; `forever profession plan` déterministe à graine fixe, avec provenance et hypothèses (chance de gain `suppose`) ; points Legacy rattachés au catalogue de LG1 ou marqués inconnus.

## RP1 — Réputations
- **Fait** : factions de Forever (nouvelles ou modifiées), paliers, sources de réputation (quêtes, monstres, objets remis) et leurs gains, récompenses par palier (objets, recettes, accès) ; état actuel importé depuis l'addon (T07) ; `forever rep info <faction>`, `forever rep plan --faction X --to <palier>` (temps estimé à partir des gains et, pour les monstres, du temps par monstre du simulateur de leveling) ; consultation MCP par `forever_lookup`, domaine `reputations` pour les factions, outil de calcul séparé pour le plan.
- **Sources** : client (factions et paliers ; tables à identifier à l'inventaire) ; annonces officielles (réputations de Forever) ; communauté (gains par source, récompenses par palier, `suppose`) ; journaux (rien) ; addon (paliers et valeurs actuels, gains relevés hors combat, sous `pcall`).
- **Hors périmètre** : valeur chiffrée des récompenses (T10).
- **Critères de fin** : `forever rep info` avec source et certitude par champ ; `forever rep plan` déterministe sur un état d'exemple importé d'une fixture de SavedVariable.

## T08 — Veille
- **Fait (repris de T03)** : installation d'une version candidate (copie dans `forever/data/`, `forever manifest --update`, PR « data: A → B » avec `forever report`) ; application de `overrides.json` et de `confirmed_changes.json` ; substitution des coûts en mana relevés dans le client à l'estimation de `mechanics.json` (`mana.talent_rank_cost`) ; outil MCP `forever_diff_versions` ; baisse ciblée de la certitude des entités touchées par un diff quand le statut est `stale` (décision 19).
- **Durcissement du pipeline (relecture T03)** : `$d` entre dans les expressions `${…}` dans son unité d'affichage (minutes dès 60 s), aucune infobulle de talent ne l'exerce aujourd'hui ; un sort cité deux fois par une infobulle d'aura 226 compterait deux fois ses dégâts ; `SpellLevel` n'est pas lu (écart de niveau calculé depuis `BaseLevel`) ; `--locale` ignoré sans `--tables` ; un CSV réduit à son en-tête est accepté ; `verify` suppose `level` en tête de `rank_format`.
- **Critères de fin** : `build-watch.yml` simulé en test (nouvelle version fictive → PR et note) ; alerte `silent` après 14 jours sans version.

## EC1 — Économie (après le lancement du 4 novembre)
Tranche gardée : sautée tant que le lancement n'a pas eu lieu et que la couverture de Forever par l'API Blizzard (produit, espace de noms, hôtel des ventes) n'est pas vérifiée.
- **Fait** : client `forever/pipeline/bnet.py` (via `Deps.http_get`, clés dans `.env`, jamais lues par les tests) ; `forever prices fetch` (prix de l'hôtel des ventes de mon royaume, instantané daté) ; prix en cache hors de `forever/data/` (ce ne sont pas des données de version du jeu), âge de l'instantané dans les hypothèses ; `forever prices item <objet>` ; coût des plans de MT1 et budget des consommables (T11) ; outil MCP séparé `forever_prices` (calcul et réseau, pas une consultation).
- **Arrêt obligatoire** : le plan de EC1 s'arrête pour demander l'accord de l'utilisateur avant d'ajouter un accès réseau ; une fois accordé, la commande entre dans la liste réseau de `CLAUDE.md`, de `docs/ARCHITECTURE.md` et de `tests/unit/test_network_boundary.py`.
- **Sources** : API Blizzard (source principale, après le lancement) ; addon (base de prix d'Auctionator, installé, lue localement dans ses SavedVariables : format et fonctionnement sur Forever à vérifier ; possible repli avant le lancement) ; client (prix de vente aux marchands, tables à identifier) ; annonces officielles (ouverture et couverture de l'API) ; communauté (rien) ; journaux (rien).
- **Hors périmètre** : achat ou vente automatisés ; historique long des prix.
- **Critères de fin** : `forever prices fetch` testé hors ligne sur des réponses d'API en fixtures (client HTTP simulé) ; échec réseau → code 5 ; `test_network_boundary.py` à jour ; plan de MT1 chiffré en or sur les prix d'une fixture.

## ForeverAssist V2 et V3
- **V2 (proposée avec T07, qui lit déjà les SavedVariables)** : l'addon écrit hors combat le contexte du personnage (niveau, talents `C_Traits`, équipement, zone, quêtes) dans `ForeverAssistCharDB` ; `forever ingest-sv` le lit après un `/reload`, recalcule et régénère `Generated.lua`. Hors périmètre : tout canal temps réel. Critères de fin : lecture d'une SavedVariable d'exemple, régénération déterministe, fiche du vault mise à jour.
- **V3 (proposée après T08)** : compagnon de bureau qui analyse `WoWCombatLog-*.txt` après le combat (`forever logs measure`), résume le dernier combat, l'expose au MCP et prépare le fichier de V1. Hors périmètre : toute consigne en direct. Critères de fin : découpe des combats testée sur fixtures, résumé avec provenance.

## T09 à T13
- **T09, reporté de T04e** : Fire Vulnerability dans les rotations (Scorch jusqu'aux cumuls maximum, fonctions de T04e).

Détaillées au moment de les planifier, avec la même structure (fait, hors périmètre, critères de fin testables).
