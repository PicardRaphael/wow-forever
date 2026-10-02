# Feuille de route — tranches verticales

Chaque tranche traverse toutes les couches (données → moteur → outil → test) et se termine par un résultat utilisable.
Une tranche = 1 à 3 sessions Claude Code. Ne commence la suivante que lorsque `uv run tasks.py verify` est vert.

L'ordre de la table est l'ordre d'exécution. Il suit les priorités du joueur et les dépendances ; ordre revu le 2026-09-29 (décisions 102 à 121) : le PvP d'abord (PV1, puis le savoir des familiers du Chasseur CH0, avancé avant FA1 parce que le joueur joue de plus en plus le Chasseur et que la bêta se termine le 21 octobre (décisions 154 et 156), l'aide en jeu FA1, PV2), puis l'analyse de mes combats PvP (AN1), puis une tranche par classe pour les huit autres classes (leveling, donjon, PvP), puis la mana des combats longs et l'analyse de mes combats PvE (T05b, AN2), les domaines de progression (quêtes, donjons, Legacy, métiers, réputations, économie), et le raid en dernier (T09, puis la partie raid des classes que son moteur ne couvre pas). La mémoire joueur T07 reste préalable à tout suivi de progression ; l'API Blizzard attend le lancement. Une tranche gardée par un événement extérieur (condition écrite dans sa colonne « Dépend de ») est sautée tant que la condition n'est pas remplie, puis reprise à la première fin de tranche qui suit : elle ne bloque pas les suivantes (décision 62).

Tranches lettrées par domaine (sans renuméroter les tranches T existantes) : PV (PvP), AN (analyse de mes combats), DJ (donjons), LG (Legacy), MT (métiers), RP (réputations), EC (économie), FA (addon ForeverAssist). Tranches de classe (remplacent T12, décision 102) : PA1 Paladin, DE1 Démoniste, PR1 Prêtre, CH1 Chasseur, CM1 Chaman, GU1 Guerrier, VO1 Voleur, DR1 Druide ; l'indice `0` (CH0) désigne le savoir d'une classe pris avant sa tranche, sans son moteur (décision 154) ; le suffixe `r` (PA1r…) désigne la partie raid d'une classe, faite après T09 quand le moteur porté de T09 ne la couvre pas. Les sources de chaque domaine sont résumées dans `docs/SPEC.md` (section « Domaines et sources ») et détaillées dans chaque section ci-dessous. Outils et skills prévus (provisoires, forme fixée au plan de chaque tranche) : `docs/ARCHITECTURE.md`, section « Outils et skills prévus ».

Chaque tranche utilise le profil du personnage actif (plusieurs personnages, de toutes les classes, y compris des personnages prévus pas encore créés : décision 119 ; rempli automatiquement dès le début de PV1) et ajoute le skill de son domaine et de son usage (décision 115).

Sources communautaires (décisions 123 à 131, `docs/DATA_SOURCES.md`) : les addons de données installés (AtlasLoot Classic Forever, ForeverDungeonJournal, Questie Forever, GearQuestForever en recoupement seulement, Auctionator pour mes relevés de prix, Forever Bestiary pour les familiers du Chasseur) sont la première source communautaire de chaque tranche qui en a besoin, lus en local avec leur version comme provenance, et suivis par version (`forever addons status` en T08b, avancé de DJ1 ; relecture à chaque veille en T08) ; hiérarchie des sources : client, puis mes observations (journaux, relevés de ForeverLogger), puis Wowhead (contrôle, jamais vérité) et les addons de données, puis les guides ; chaque tranche met à jour la liste des données manquantes et de leurs addons candidats (`docs/DATA_SOURCES.md`) et, quand un addon pourrait combler un manque, l'agent propose de l'installer sans jamais l'installer lui-même.

| Tranche | But | Dépend de |
| --- | --- | --- |
| T01 | Squelette de bout en bout : `forever status` + consultation d'un sort, CLI + MCP + provenance + CI | — |
| T02 | Port du cœur de mécaniques du skill Mage + registre + tests de référence | T01 |
| T03 | Pipeline de données : builds, fetch, decode, diff, verify, report (tests hors ligne) | T01 |
| T04a | Sources locales du client : journaux de combat, Questie, table des monstres, points de base par niveau, preuves du registre, addon ForeverLogger | T02, T03 |
| T04b | Simulateurs de leveling (MC + analytique) exposés en MCP + graphique | T04a |
| T04c | Simulateur fiable pour comparer les builds : Ignite, Arcane Blast, recharges, régénération et armure, `forever measures refresh`, zone ou donjon à mon niveau | T04b |
| T04e | Calculs de dégâts fidèles au client : coefficients du client, DoT, multiplicateurs, cumul des bonus | T04c |
| T05 | Builds du Mage par contexte : optimiseur (leveling, donjon, raid, PvP), Arcane Power et Hot Streak dans les rotations, sensibilité, respec | T04b, T04c, T04e |
| T06 | Plugin Claude Code : skills, hooks, sous-agents, installation au niveau utilisateur, évaluation (sans statusline) | T04b |
| T06b | Données décodées du client installées pour 1.60.1.70009 (talents redécodés, Hot Streak à 20 s, coûts en mana relevés, changements confirmés appliqués) et totaux dans les sorties des outils (points d'un build par arbre…) pour que le modèle n'ait plus à calculer | T03, T05, T06 |
| T08a | Installer une **nouvelle** version du jeu (`forever install --new-version` : nouveau dossier, copies figées du seed et changements confirmés reportés, provenance et fraîcheur) ; version du client attachée à chaque session de journal pour qu'une mesure ne soit jamais attribuée à une autre version ; veille quotidienne en CI (fetch, decode, verify, diff, report, PR, rien installé) ; routeur du plugin qui propose l'analyse quand la fraîcheur est en retard | T06b |
| PV1 | Import automatique minimal du profil (ForeverLogger, journaux), puis PvP : savoir des 9 classes sans moteur de classe (sorts, recharges, contrôles et durées, défensifs, raciaux de toutes les races décodés du client, bijoux, rendements décroissants selon les règles Classic, fiches par affrontement) ; builds de la communauté vérifiés sur le client pour les classes pas encore calculées | T03, T04a, T05, T06b |
| T08b | Tout ce qui doit suivre les mises à jour (d'après `docs/research/audit-mises-a-jour.md`) : ratios du personnage décodés du client en mode forever (le mode seed garde ses estimations), plafond de niveau et valeurs dépendantes de la version tirés des données ou de l'installation, `forever diff` des valeurs de `spell_scaling.json`, `forever addons status` (avancé de DJ1), correctifs du serveur listés depuis `Hotfix.log`, veille des notes officielles du forum de Blizzard, veille locale au démarrage d'une session, origine déclarée de chaque valeur des données et contrôle dans `verify`, rejeu des builds de T05 | T08a, PV1 |
| CH0 | Savoir des familiers du Chasseur, sans moteur : système de familiers de Forever (apprivoisement, capacités et rangs, Beast Training, points d'entraînement, loyauté, régime, Beast Lore) établi dans le client puis recoupé avec Forever Bestiary ; familles, capacités, rangs et bêtes qui les enseignent (niveau, zones) ; héritage des statistiques du Chasseur et vitesse d'attaque (relevés de joueurs, protocole de mesure dans mes journaux) ; guide d'apprivoisement par zone et niveau ; lecture de `ForeverBestiaryDB` | T03, T04a, PV1, T08b |
| FA1 | ForeverAssist V1 : talent suivant à chaque gain de niveau, comparaison de l'équipement dans l'infobulle, données précalculées par forever | T04b, T05 |
| PV2 | PvP, champs de bataille (objectifs, récompenses, équipement PvP) et monde ouvert ; rendements décroissants mesurés dans les journaux de champs de bataille (`docs/research/pvp-dr-protocole.md`) ; profil PvP du Mage avec rendements décroissants et bijou (reporté de PV1) | PV1, T04a |
| AN1 | Analyse PvP de mes combats (champs de bataille, monde ouvert) : contrôles donnés et subis, recharges, burst, interruptions, morts, cibles, comparés aux fiches de PV1 ; taux réels comparés au modèle ; `forever analyze`, outil MCP, rapport | PV1, PV2, T04a |
| PA1 | Paladin (Sacré, Protection, Vindicte) : moteur (table d'attaque de mêlée, soins, mitigation, menace, sceaux et jugements), leveling, donjon, PvP, builds par contexte et par rôle ; analyse AN1 étendue | PV1, AN1 |
| DE1 | Démoniste (Affliction, Démonologie, Destruction) : moteur (familiers, DoT, fragments d'âme), leveling, donjon, PvP, builds par contexte ; analyse AN1 étendue | PA1 |
| PR1 | Prêtre (Discipline, Sacré, Ombre) : moteur (soins, boucliers d'absorption, DoT, Forme d'ombre), leveling, donjon, PvP, builds par contexte et par rôle ; analyse AN1 étendue | PA1, DE1 |
| CH1 | Chasseur (Maîtrise des bêtes, Précision, Survie) : moteur (attaque à distance, familier), leveling, donjon, PvP, builds par contexte, choix du familier par contexte (savoir de CH0) ; analyse AN1 étendue | PA1, DE1, CH0 |
| CM1 | Chaman (Élémentaire, Amélioration, Restauration) : moteur (totems, mêlée, soins, sorts), leveling, donjon, PvP, builds par contexte et par rôle ; analyse AN1 étendue | PA1, PR1 |
| GU1 | Guerrier (Armes, Fureur, Protection) : moteur (rage, postures, double arme, mitigation et menace du tank), leveling, donjon, PvP, builds par contexte et par rôle ; analyse AN1 étendue | PA1 |
| VO1 | Voleur (Assassinat, Combat, Finesse) : moteur (énergie, points de combo, furtivité, poisons), leveling, donjon, PvP, builds par contexte ; analyse AN1 étendue | GU1 |
| DR1 | Druide (Équilibre, Farouche félin et ours, Restauration) : moteur (formes et leurs ressources, soins, mitigation et menace en forme d'ours), leveling, donjon, PvP, builds par contexte et par rôle ; analyse AN1 étendue | PR1, GU1, VO1 |
| T05b | Mana des combats longs : Évocation, potions et gemmes de mana, régénération en combat, dans les scénarios de donjon et de raid et le conseil de build, pour toutes les classes à mana | T05, DR1 |
| AN2 | Analyse PvE de mes combats (leveling, donjon, raid, chaque boss) : rotation réelle, écarts avec la rotation optimale, perte chiffrée par rejeu du même combat | AN1, T05b, DR1 |
| T04d | Quêtes propres à Forever et modèle d'XP de Forever (ses sources viennent de l'inventaire des addons, `tasks/inventaire-addons.md`, et elle ne change pas le classement des builds) | T04c |
| DJ1 | Donjons : niveaux, boss, butin (AtlasLoot, ForeverDungeonJournal), « où trouver tel objet » ; lecteurs d'AtlasLoot et de ForeverDungeonJournal branchés sur `forever addons status` (T08b) ; relevé hors combat de ForeverLogger (marchands, butin, réputation) | T03, T04a |
| LG1 | Legacy : défis, points, arbres de bonus, conseil des bonus pour chacun de mes personnages, chiffré par le moteur de sa classe | T03, T04b, DR1 |
| FA1p | Extension PvP de ForeverAssist V1 : fiche fixe de la classe adverse | FA1, PV1 |
| P06 | Évaluation d'un pont de conversation existant (wow-claude / wow-ai) pointé sur ce dépôt | T06 |
| T07 | Mémoire joueur : import complet (équipement, métiers, réputations, historique ; API Blizzard branchée par EC1) et fiches du vault (+ ForeverAssist V2 proposée) ; l'import minimal du profil, les quêtes faites dans Questie et mes prix d'Auctionator sont faits en PV1 | T06, PV1 |
| LG2 | Suivi de ma progression Legacy (et, par le même import, honneur et rang PvP) | LG1, T07 |
| MT1 | Métiers : recettes, montée de compétence, points Legacy des métiers, répartition des métiers entre mes personnages | T03, LG1, T07 |
| RP1 | Réputations : factions, paliers, gains, récompenses, suivi, « combien coûte telle réputation » (gains relevés par ForeverLogger depuis DJ1) | T03, T07, DJ1 |
| T08 | Veille (suite de T08a) : note d'impact par personnage ; versions des addons de données (relecture, changements signalés) ; `forever_diff_versions` ; correctifs serveur (`DBCache.bin`, `Hotfix.log`) | T08a, T07, DJ1 |
| EC1 | API Blizzard : hôtel des ventes, personnages, PvP (prix, fiches de personnages avec équipement, niveau et talents si disponibles, honneur, rang et classements), branchée sur le profil multi-sources | T03, MT1, T07 ; condition : lancement du 4 novembre passé et couverture de Forever par l'API vérifiée |
| FA3 | ForeverAssist V3 : compagnon de bureau, analyse des journaux après le combat (reprend `forever analyze` de AN1 et AN2) | T08, AN1, AN2 |
| T09 | Raid : moteur analytique porté (`seed/grimoire-engine/`), Monte Carlo, parité avec wowsims Forever ; partie raid des classes que couvre ce moteur (Mage, Démoniste, Prêtre, Paladin Sacré et Protection) ; rejeu de raid de AN2 | T02, AN2, PA1, DE1, PR1 |
| PA1r | Partie raid du Paladin Vindicte | T09, PA1 |
| CH1r | Partie raid du Chasseur | T09, CH1 |
| CM1r | Partie raid du Chaman | T09, CM1 |
| GU1r | Partie raid du Guerrier | T09, GU1 |
| VO1r | Partie raid du Voleur | T09, VO1 |
| DR1r | Partie raid du Druide | T09, DR1 |
| T10 | Équipement : base d'objets par formules du client, optimiseur, plan d'équipement par personnage et par contexte (où l'obtenir, coût, temps estimé) | T09, DJ1, RP1 |
| T11 | Consommables et préparation de raid | T10 |
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

## T05 — Builds du Mage par contexte
- **Fait** : `forever build <contexte> --level N` et l'outil MCP `forever_build` (contextes `leveling`, `dungeon`, `raid`, `pvp-bg`, `pvp-world`) : talents et ordre d'apprentissage, raison de chaque choix, alternative la plus proche avec écart apparié et intervalle de confiance, stabilité sur plusieurs graines, sensibilité aux hypothèses incertaines, conseil de respec, angles morts, certitude et provenance ; armure, `ab_stacks` et cumuls de Hot Streak traités comme des choix du build ; Arcane Power (aura et recharge du client) et Hot Streak (Pyroblast dans la rotation de feu) dans les rotations ; Missile Barrage, Flame Throwing et Arcane Geometry modélisés ; option `--talented-bonus N` (bonus Legacy « Talented ») ; scénarios de donjon et de raid provisoires ; portage des tests du seed `optimiseur_legal` et `pvp_et_respec` ; comparaison avec les builds de la communauté. Plan : `tasks/T05-plan.md` (décisions 79 à 89).
- **Hors périmètre, avec échéance** : Presence of Mind, Combustion et Cold Snap (angles morts chiffrés) ; Fire Vulnerability dans les rotations et moteur de raid (T09) ; équipement réel (T07, T10) ; scénarios de donjon réels (DJ1).
- **Critères de fin** : `forever build <contexte> --level N` pour les cinq contextes, légal, avec provenance ; parité du seed (`optimiseur_legal`, `pvp_et_respec`, glouton PvP) ; Arcane Power et Hot Streak dans les rotations ; décision au Monte Carlo avec intervalle ; stabilité et sensibilité affichées ; tout build au-delà du plafond de la bêta signalé comme non vérifiable en jeu avant la sortie ; comparaison communautaire documentée ; `uv run tasks.py verify` vert.

## T06 — Plugin Claude Code
- **Fait** : skills des domaines disponibles à ce stade (leveling, Mage) ; chaque tranche de domaine suivante ajoute son skill (PvP, donjons, Legacy, métiers, réputations, économie).
- **Critères de fin** (plan `tasks/T06-plan.md`, décisions 91 à 97) : plugin installé au niveau utilisateur par `scripts/install_plugin.ps1` sur un PC et utilisable depuis un autre dossier ; SessionStart injecte une ligne de fraîcheur hors ligne, seulement dans le dépôt ; le hook Stop signale un chiffre inventé sur la fixture, seulement dans une session qui a utilisé forever ; skills sans chiffre de jeu ; `forever lookup talent` ; évaluation de 30 questions réelles et 20 voisines aux seuils de la décision 96 (passage local documenté dans `docs/research/plugin-eval-T06.md`, taux de fausses alertes du contrôle des chiffres mesuré) ; `uv run tasks.py verify` vert. Pas de statusline (décision 15).

## T06b — Données du client installées et totaux dans les sorties
Demande de l'utilisateur du 2026-09-29, après l'évaluation du plugin (`docs/research/plugin-eval-T06.md`).
- **Données** : installer dans `forever/data/1.60.1.70009/` les valeurs décodées du client à la place des valeurs de
  référence, en reprenant de T08 ce qu'il faut (installation d'une version candidate, `forever manifest --update`,
  rapport `forever report`, accord de l'utilisateur avant l'écriture) : talents redécodés au build 70009 (49 talents
  encore `FC-69893`, certitude `probable`), Hot Streak à 20 s dans ses rangs (aujourd'hui 15 s dans les rangs et
  20 s dans `duration_s`), coûts en mana relevés dans le client substitués à l'estimation `mana.talent_rank_cost`,
  changements de `confirmed_changes.json` appliqués. Chaque valeur remplacée garde sa source et sa certitude ; les
  golden et la parité avec le seed (`rules=seed`) ne bougent pas.
- **Totaux** : ajouter aux sorties des outils les grandeurs que le modèle calculait lui-même au premier passage
  d'évaluation (points du build par arbre et au total dans `forever_build`, effet au maximum des cumuls quand un
  talent ou une mécanique le définit…), calculées dans `forever/engine/` ; consigne « aucun calcul » du plugin
  inchangée.
- **Critères de fin** (plan `tasks/T06b-plan.md`, validé le 2026-09-29) : `forever lookup talent` à `certain` pour
  les 54 talents ; Hot Streak à 20 s partout ; coûts en mana du client en mode forever, estimation B11 réservée au
  seed ; révision 2 visible dans la provenance, `revisions.json` et le rapport de diff ; parité du seed verte sans
  valeur attendue changée ; totaux dans `forever_build`, `forever_explain_mechanic`, `forever_lookup`,
  `forever_sim_leveling` ; `forever profile` et `forever_player_profile` ; départage et `next_step` ; builds de T05
  rejoués et documentés ; évaluation du plugin (53 cas, profil de test rempli, deux cas à profil vide) sans alerte du contrôle des chiffres ; `plugin.json`
  versionné, `validate --strict` vert.
- **Fait** : `forever install` (révision 2, décision 98), copies figées du seed pour le mode seed, provenance
  `data_revision` ; totaux (`points`, `derived`, `monte_carlo_stats`, `advantage`) ; profil joueur hors du dépôt
  (décision 99) ; recommandations départagées et `next_step` (décision 100) ; plugin 0.2.1 et empreinte (décision
  101) ; rejeu des builds (`docs/research/builds-T05.md`, section « Rejeu T06b ») ; évaluation (`docs/research/plugin-eval-T06.md`).
- **Reste pour T08** : chaîne automatique de veille, installation d'une **nouvelle** version de données (copie des
  `_seed_*.json` comprise) et PR de données ; `forever_diff_versions`.

## T08a — Nouvelle version du jeu installée, et veille automatique
Demande de l'utilisateur du 2026-09-30, à la publication de 1.60.1.70124 (décisions 134 et 135). Plan
`tasks/T08a-plan.md`, analyse `docs/research/data-1.60.1.70124.md`, rapport d'installation
`docs/research/data-1.60.1.70124-install.md`.

**Fait le 2026-09-30** (blocs A, B, C et E ; le workflow du bloc D est livré en patch, à appliquer par
l'utilisateur) : `forever install --new-version` ; 1.60.1.70124 installée en révision 1, aucune valeur de jeu
changée, `forever diff` entre les deux versions installées rend « aucun changement » et la fraîcheur repasse à
`fresh` ; `forever/pipeline/client_builds.py` et l'attribution des mesures par version du client ; routeur du
plugin en 0.4.3. Rejeu des builds de T05 identique à celui de T06b (`docs/research/builds-T05.md`, section
« Rejeu T08a »). Reprend de T08 l'installation d'une
**nouvelle** version et la veille planifiée ; le reste de T08 ne bouge pas.
- **Installer une nouvelle version** : `forever install --new-version` (T06b n'installe qu'une **révision** de la
  version courante). Nouveau dossier `forever/data/<version>/` ; copies figées du seed (`_seed_*.json`,
  `_source_gunba_mage_tree.json`), `confirmed_changes.json`, `overrides.json` et `sources.json` reportés ;
  fichiers non décodés (`leveling.json`, `mechanics.json`, `monsters.json`, `racials.json`, `respec.json`) reportés
  avec la mention « hérité de <version> » et leur date ; `revisions.json` neuf en révision 1 ;
  `forever manifest --update` ; fraîcheur de retour à `fresh` ; accord avant écriture ; rapport hors des données.
  Critère : `forever diff` entre les deux versions installées ne montre **aucun fichier retiré**.
- **Installation de 1.60.1.70124** : les 22 tables du client sont identiques à celles de 1.60.1.70009 (0 talent,
  0 sort changés) ; l'installation aligne la version des données sur le client joué et remet la fraîcheur à
  `fresh`, sans changer une seule valeur. Parité du seed et builds de T05 attendus identiques.
- **Mesure attribuée à la bonne version** (décision 135) : journal `client_builds.json` dans le cache (build lu
  dans `.build.info`, date de la mise à jour, en ajout seulement, écrit à chaque lecture des journaux) ; version du
  client attachée à chaque **session** et non à chaque fichier (un journal peut chevaucher une mise à jour) ;
  `forever measures refresh` n'écrit que les sessions de la version installée et liste les autres « en attente » ;
  une mesure reportée d'une version à l'autre garde « mesuré sous <version d'origine> ». L'entête du journal
  (`BUILD_VERSION 1.60.1`, tronquée) n'est jamais utilisée pour attribuer. PV1 consomme la même règle pour les
  instantanés de ForeverLogger.
- **Veille** : `.github/workflows/build-watch.yml` quotidien — `forever builds` contre le manifeste, puis `fetch`,
  `decode`, `verify` (échec non bloquant), `diff`, `report` ; rapport et résumé committés (la candidate vit dans le
  cache : sans cela la PR serait vide), PR sur la branche `data/<version>`, **rien installé** (contrôle
  `git diff --exit-code -- forever/data`) ; alerte `silent` après 14 jours. Livré en **patch**
  (`tasks/T08a-build-watch.patch`) : le mode auto n'écrit pas dans `.github/workflows`. Les addons restent hors
  veille de CI (ils sont sur le poste de l'utilisateur, décision 124).
- **Plugin** : le routeur propose l'analyse de la nouvelle version quand la fraîcheur est `stale` au démarrage,
  sans rien lancer sans accord, et répond quand même avec les données installées. Plugin 0.4.3.
- **Sources** : tables du client (wago.tools), `.build.info` et les journaux du client (lus sur disque).
- **Hors périmètre** (reste en T08) : `forever addons status` et le suivi des versions d'addons,
  `forever_diff_versions`, baisse ciblée de certitude sur un diff `stale`, durcissement du pipeline relevé à la
  relecture de T03, `DBCache.bin` et les correctifs serveur, décodage de 1.60.1.70058 (sautée).
- **Critères de fin** : `install --new-version` testé sur fixtures et `diff` sans fichier retiré ; 70124 installée
  et `forever status` en `fresh` ; une mesure d'une autre version n'est jamais écrite ; `build-watch.yml` simulé en
  test (version fictive → rapport, résumé, PR, `forever/data/` inchangé) ; routeur et plugin 0.4.3 ;
  `uv run tasks.py verify` vert.

## PV1 — Profil automatique, puis PvP : savoir des 9 classes (priorité haute)
**Fait le 2026-09-30** (plan `tasks/PV1-plan.md`, rapport de données `docs/research/data-1.60.1.70124-r2.md`,
corrections de tests `tasks/PV1-corrections.md`) : `forever profile import` (ForeverLogger, journaux, Questie,
Auctionator ; profil de schéma 2) ; 1.60.1.70124 en révision 2, puis 3 après relecture (sens des dissipations) (`classes.json`, `races.json`, `pvp_items.json`,
`pvp_rules.json`, `racials.json` retiré, copie figée `_seed_racials.json`) ; rendements décroissants (registre K1 à
K4) ; `forever pvp class`, `forever pvp matchup`, `forever_lookup(kind="pvp")` ; légalité des builds des 9 classes
(`forever talents check`, `kind="build_check"`) ; plugin 0.5.0 (`forever-pvp`, `forever-builds`). Rejeu des builds
de T05 identique à T08a. Écarts au texte ci-dessous : Questie et Auctionator importés dès PV1 (D1) ; profil PvP du
Mage avec rendements décroissants et bijou reporté à PV2 (D4) ; catégorie de rendement décroissant lue dans le client
(`SpellCategories.DiminishType`, certain), seules les règles du serveur restent supposées ; positions des deux
talents hors grille du Paladin relevées en jeu par l'utilisateur, paliers des deux du Démoniste communautaires.
Les champs de bataille arrivent bientôt (date à confirmer par annonce officielle, `docs/OPEN_QUESTIONS.md`). T05 garde le profil PvP comparatif du Mage porté du seed (`pvp_et_respec`) ; PV1 élargit le savoir aux 9 classes et comble les limites de ce profil listées dans `seed/forever-mage/references/pvp-model.md` (ni rendements décroissants, ni bijou PvP). PV1 n'attend pas les moteurs des tranches de classe : il ne calcule aucun dégât hors Mage, il consulte et croise des données fixes.
- **Fait, au début de la tranche : import automatique minimal du profil** (décision 105) :
    - `forever profile import` (forme au plan) lit sur disque, jamais par le réseau, les SavedVariables de ForeverLogger (`ForeverLoggerDB` : classe, race, niveau, talents de chaque personnage connecté, instantanés datés) et les journaux de combat (personnages que le journal marque comme joueur « à moi » : GUID, nom, classe) ; il crée ou met à jour les personnages du profil (décisions 99 et 119 : hors du dépôt, plusieurs personnages de toutes les classes, un actif), marque « créé » un personnage prévu qu'il retrouve, garde la source et la date de chaque champ, ne remplace jamais une valeur plus récente par une plus ancienne et liste ce qu'il change avant d'écrire (accord ou `--yes`). La faction reste donnée par le joueur (décision 99).
    - Profil multi-sources (décision 125) : le schéma du profil et la règle de fusion sont fixés ici pour toutes les sources à venir, sans changement de schéma quand T07 et EC1 en ajoutent : chaque champ porte sa source (ForeverLogger, journal, sauvegarde d'un autre addon, API Blizzard, saisie du joueur) et sa date ; en cas de désaccord, la valeur la plus récente l'emporte, à date égale la plus directe (ordre des sources fixé au plan) ; l'écart est signalé dans la sortie de l'import, jamais effacé en silence. Ce que le joueur dit dans sa question l'emporte toujours pour la réponse en cours (décision 122), sans écrire le profil.
    - Talents validés pour toutes les classes dès que leurs arbres sont décodés (plus bas) ; `validated: false` jusque-là.
    - Plugin : l'agent propose la mise à jour quand le joueur dit en conversation « j'ai … » (consigne de `format-reponse.md` depuis le plugin 0.3.0) et, après PV1, propose l'import automatique quand le profil est vide ou daté.
    - T07 garde l'import complet (équipement, métiers, réputations, historique, quêtes faites dans Questie, mes prix d'Auctionator) et le vault ; EC1 branche l'API Blizzard sur la même règle.
    - Plugin : consigne « donnée manquante » (décision 131) dans le routeur : quand une réponse bute sur une donnée absente, l'agent propose un addon qui la comblerait (recherche par `forever-web-researcher` sur CurseForge, Wago et la liste des addons Forever de foreverchanges.pro ; lien, version, date, licence, compatibilité Forever, stabilité), sans jamais rien télécharger ni installer ; consigne « pas encore construit » pour les questions d'objets, de réputation et de PvP (décision 130) : source citée quand elle existe, sinon la tranche qui le fera.
- **Fait** :
    - Décodage étendu (dépendance T03, pas les tranches de classe) : `decode_rules.json` couvre les lignes de compétence et les arbres de talents des 9 classes, en plus du Mage ; sorts de classe et de talent avec rangs, recharge, recharge globale, durée, portée, école, type d'aura et mécanique de contrôle ; bijoux PvP (sort d'utilisation et recharge lus dans les tables d'objets, lecture ciblée, la base d'objets complète reste en T10).
    - Raciaux de toutes les races jouables, y compris les nouvelles combinaisons race et classe de Forever, décodés du client (décision 106) : races et classes permises, sorts raciaux avec effet, recharge et durée (tables à identifier à l'inventaire). Ils remplacent `racials.json`, aujourd'hui relevé sur foreverchanges.pro avec des recharges communautaires ; utilisés par les fiches PvP dès PV1, puis par les calculs de chaque tranche de classe.
    - Espace de données par classe sans moteur : `GameData` expose les sorts, talents et raciaux des 9 classes ; les tranches de classe y brancheront leurs moteurs sans changer ce schéma (décision 31).
    - Classement de chaque sort : contrôle (catégorie de rendement décroissant, durée pleine, ruptures connues), défensif ou immunité, rupture de contrôle, interruption, dissipation, mobilité. Le classement vient des champs du client ; un sort que les données ne permettent pas de classer est listé comme non résolu, jamais deviné.
    - Rendements décroissants : règles Classic (catégories, fenêtre, paliers) dans un fichier de `forever/data/<version>/`, certitude `suppose`, entrées du registre (nouvelle catégorie à fixer au plan) ; fonction pure dans `forever/engine/` qui donne la durée effective d'une suite de contrôles. Aucun chiffre de ces règles hors des données.
    - Fiches par affrontement, générées depuis les données (jamais recopiées d'un guide) : contrôles subis et leur catégorie, défensifs et immunités adverses avec leur recharge, ruptures et interruptions adverses, mes réponses (sorts de rupture, bijou, raciaux, dissipations), fenêtres à surveiller. Conseils communautaires éventuels : faits sourcés, `suppose`, avec le lien.
    - Profil PvP du Mage (T05) : ajout des rendements décroissants et du bijou PvP, résultat toujours comparatif, jamais un duel simulé (**reporté à PV2**, D4 de PV1).
    - Classes pas encore calculées (décision 114) : talents des 9 classes consultables (`forever_lookup(kind="talent", class=…)`, forme au plan) et contrôle de légalité d'un build de n'importe quelle classe (points par palier, prérequis, niveau), pour vérifier les builds de la communauté trouvés par le sous-agent de recherche et les expliquer par les descriptions de talents du client (le contrôle des chiffres reconnaît déjà les lignes sourcées du rapport de ce sous-agent, décision 120).
    - `forever pvp class <classe>`, `forever pvp matchup <ma classe> <classe adverse>`, consultation MCP par `forever_lookup`, domaine `pvp` (paginé, compact ; forme provisoire, `docs/ARCHITECTURE.md`) ; provenance et certitude par champ.
    - Skills : `forever-pvp` (savoir PvP, fiches) et `forever-builds` (builds de toutes les classes : calculés pour les classes à moteur, communautaires vérifiés pour les autres), décision 115.
- **Sources** : client (tables des sorts, talents, races, classes, raciaux, objets ; `certain` ou `probable`) ; annonces officielles (changements PvP de Forever, règles des contrôles, combinaisons race et classe) ; communauté (Wowhead Forever, guides PvP : faits sourcés, `suppose`) ; journaux (personnages « à moi » pour le profil ; mesures PvP en PV2) ; addon (ForeverLogger pour le profil ; affichage de fiches fixes par l'extension FA1p).
- **Addon** : le suivi en direct des temps de recharge adverses est impossible sur Forever (abonnement au journal de combat refusé aux addons, valeurs de combat secrètes : `docs/research/addon-forever.md`). En jeu, seules des informations fixes s'affichent : la fiche de la classe adverse, jamais un état (recharge en cours, bijou utilisé). Affichage par l'extension FA1p.
- **Hors périmètre** : dégâts et soins des autres classes (tranches de classe) ; simulation de duel ; résistances des joueurs ; mesures sur journaux (PV2) ; analyse de mes combats (AN1) ; toute détection d'événement de combat dans un addon.
- **Critères de fin** :
    - `forever profile import` sur une fixture de `ForeverLoggerDB` et une fixture de journal crée deux personnages de classes différentes (classe, race, niveau, talents, source et date par champ), sans réseau ; un second import sans changement n'écrit rien ; une valeur plus ancienne ne remplace pas une plus récente.
    - `forever decode` sur des fixtures wago étendues produit, pour chacune des 9 classes, ses sorts et talents avec recharge, durée et école, et les raciaux de chaque race jouable ; `verify` vert ; les sorts non classés sont listés dans le rapport.
    - `forever pvp matchup` rend une fiche déterministe pour deux paires de classes fixées en test, avec provenance complète et certitude par champ.
    - La fonction de rendement décroissant reproduit, sur des suites de contrôles de test, les durées attendues par les règles des données (valeurs lues dans les données, pas dans le test).
    - Le profil PvP du Mage change quand on active les rendements décroissants ou le bijou (test de non-régression du mode sans).
    - Le contrôle de légalité refuse un build d'une autre classe qui dépasse un palier ou saute un prérequis (fixtures) ; cas d'évaluation « classe pas encore calculée » mis à jour.

## T08b — Tout ce qui doit suivre les mises à jour
Demande de l'utilisateur du 2026-10-01, d'après l'audit `docs/research/audit-mises-a-jour.md` (décision 147). Placée
après PV1 et avant FA1 : elle avance de T08 et de DJ1 ce qui fait qu'une mise à jour du jeu, d'un correctif du
serveur ou d'un addon de données n'est plus manquée. Plan : `tasks/T08b-plan.md`.
- **Fait** :
    - **Ratios du personnage décodés du client** en mode forever : `PlayerExpectedStat` (Intelligence par point de critique, mana de base, PV par Endurance…), `LevelExperience`, constante d'armure (`ExpectedStat`), XP de repos (`Exhaustion`), régénération de PV par l'Esprit (`GlobalCurve`) et tables voisines utiles ; le mode seed garde ses estimations et sa parité. GameTables lues par l'API de fichiers de wago.tools, accord de l'utilisateur à chaque accès.
    - **Plus de valeur dépendante de la version écrite à la main** : le plafond de niveau vient des données ou de l'installation ; chaque valeur marquée `certain` mais écrite à la main (règle d'Ignite, multiplicateur de critique…) est décodée du client quand c'est possible, sinon ramenée à la certitude de la règle du projet.
    - `forever diff` compare les **valeurs** de `spell_scaling.json`, et plus seulement l'empreinte du fichier.
    - **`forever addons status`** (avancé de DJ1) : nouvelle version d'un addon de données détectée par empreinte, données relues, changements listés.
    - **Correctifs du serveur** : `Logs/Hotfix.log` lu pour lister les tables et les lignes corrigées depuis la dernière installation, et les signaler ; `DBCache.bin` reste en T08.
    - **Veille des notes officielles** : catégories Forever du forum de Blizzard lues une fois par jour, dans la limite de son `robots.txt` et de ses conditions ; une note nouvelle ou modifiée ouvre une issue GitHub qui liste les sorts, talents et mécaniques nommés, sans rien changer aux données. Workflow livré en patch.
    - **Veille locale** sur le poste de l'utilisateur : au démarrage d'une session dans le dépôt (et par une tâche planifiée Windows si c'est simple), changement de version du client (`.build.info`), nouvelle version d'un addon de données, nouveaux correctifs du serveur, nouveaux journaux et sauvegardes ; résumé et actions proposées, rien lancé sans accord. La lecture directe des fichiers du client sans wago.tools reste un secours documenté pour plus tard.
    - **Origine de chaque valeur des données** (client, journal, addon, ou écrite à la main avec sa raison) ; inventaire complet des valeurs écrites à la main avec leur certitude (au mieux `probable` si elles ne sont ni décodées ni observées) ; contrôle de `uv run tasks.py verify` qui échoue sur une nouvelle valeur écrite à la main sans origine ni raison.
    - **Rejeu des builds de T05** après le décodage des ratios : chaque recommandation qui change est montrée à l'utilisateur, avec sa raison, avant le commit.
- **Hors périmètre** : `DBCache.bin` (T08) ; modèle d'XP de Forever (T04d) ; lecteurs d'AtlasLoot et de ForeverDungeonJournal pour leurs propres consultations (DJ1) ; lecture directe des fichiers du client sans wago.tools (documentée seulement).
- **Critères de fin** : fixés au plan.
- **Réalisé (2026-10-01)** : blocs H, A, B, C, D, E, F, G, I et J (sonde de l'API Blizzard, ajoutée par l'utilisateur) ; veille des notes **lancée à la main seulement** (D1, décision 148) ; révision 4 de 1.60.1.70124 installée après le rejeu (`docs/research/builds-T05.md`, section « Rejeu T08b ») ; workflows `notes-watch` et `api-probe` livrés en patch.

## CH0 — Savoir des familiers du Chasseur
Demande de l'utilisateur du 2026-10-01 (décision 154). Placée juste avant FA1 (décision 156 ; place précédente : juste après FA1) et **séparée du calcul de CH1** : CH0 établit ce que le jeu permet (règles du système de familiers, familles, capacités, rangs, où les apprendre), sans moteur ni classement ; CH1 reprend ce savoir pour calculer le familier et choisir le meilleur par contexte. Plan : `tasks/CH0-plan.md`.
- **Réalisé (2026-10-01)** : blocs A à G. `pets.json` décodé du client (19 familles, capacités, rangs, niveau requis, coût en points d'entraînement probable, bonus, régime, cartes) et `pet_rules.json` (règles relevées par des joueurs, `suppose`) installés en révision 5 de 1.60.1.70124 après accord ; lecteur de Forever Bestiary et de sa sauvegarde (anonymisation par liste blanche), suivi par `forever addons status` ; recoupement client ↔ addon ↔ Questie (`docs/research/familiers-recoupement.md`) ; guide d'apprivoisement, `forever pets …` et `forever_lookup(kind="pets")` ; skill `forever-familiers` et quatre cas d'évaluation (plugin 0.6.0) ; ForeverLogger 0.3.0 (instantané du familier hors combat, fenêtre Beast Training) et `forever pets measure` ; protocole `docs/research/familiers-protocole.md` ; registre L1 à L12. La marge d'apprivoisement n'est pas dans le client (`SpellTargetRestrictions`) et reste supposée.
- **Fait** :
    1. **Système de familiers de Forever**, établi d'abord dans les données du client (tables à identifier à l'inventaire du plan : familles de créatures, lignes de compétence des familles, sorts et rangs des capacités, coûts d'entraînement), puis recoupé avec Forever Bestiary : apprivoisement (bêtes apprivoisables, apprivoisement **jusqu'à deux niveaux au-dessus** du Chasseur, règle à établir dans le client ou par un texte officiel, sinon `suppose` avec sa question dans `docs/OPEN_QUESTIONS.md`) ; apprentissage des capacités et de leurs rangs (apprises d'une bête apprivoisée qui les connaît, Beast Training) ; points d'entraînement (gain et coût de chaque rang) ; loyauté ; régime (aliments acceptés par famille) ; Beast Lore. Chaque règle a son entrée au registre (statut, source, tests) ; un comportement que Blizzard a reconnu comme bug n'est pas modélisé.
    2. **Toutes les familles** (bonus de dégâts, d'armure et de PV, régime, capacités), **leurs capacités et leurs rangs** (niveau requis, coût en points d'entraînement, effet lu dans le client), et pour **chaque rang, les bêtes qui l'enseignent**, avec leur niveau et leurs zones : Forever Bestiary et Questie lus en local (bêtes, niveaux, zones et positions, que le client ne porte pas), recoupés avec le client (familles, capacités, rangs) ; un écart est signalé, jamais tranché ; source et certitude par champ.
    3. **Ce que le familier hérite du Chasseur** (PV, armure, puissance d'attaque, critique) et **sa vitesse d'attaque selon le passif de la bête** (Faster Attack, Slower Attack…) : relevés de joueurs, donc `suppose` (décision 127, sans exception ; décision 154), avec la source et la date de chaque relevé ; ces valeurs ne montent qu'une fois mesurées par le protocole dans mes journaux ; **protocole de mesure dans mes journaux** (`docs/research/`, sur le modèle de `pvp-dr-protocole.md` : coups blancs du familier et intervalle entre deux coups, PV et armure du familier lus dans le bloc avancé, statistiques du Chasseur au même instant par ForeverLogger) ; une mesure suffisante devient une preuve proposée au registre, jamais écrite sans accord.
    4. **Guide d'apprivoisement** : selon la zone et le niveau du personnage actif (profil de PV1), où trouver telle bête ou tel rang d'une capacité (bêtes apprivoisables à ce niveau dans la zone et les zones voisines de son niveau, rang le plus haut atteignable) ; consultation par la CLI et le MCP (forme au plan, par exemple `forever pets` et `forever_lookup` domaine `pets`) ; skill ou carte du routeur à jour.
    5. **Lecture de la sauvegarde `ForeverBestiaryDB`** (`WTF/Account/<COMPTE>/SavedVariables/ForeverBestiary.lua`, lue sans exécuter de Lua par `forever/pipeline/lua_table.py`) : mes observations (bêtes vues, niveau, position, date), mes familiers et leur historique, et la carte communautaire (observations partagées par les joueurs, celles livrées avec l'addon et celles reçues en jeu), comme **source communautaire datée** (date de la carte et de chaque observation dans la provenance). Données personnelles : profil hors du dépôt (décision 99) ; noms des autres joueurs (`peers`) jamais lus dans une sortie ni écrits, empreintes de joueurs jamais reprises (décision 49) ; fixture minimale et anonymisée dans `tests/fixtures/`.
    - Forever Bestiary inscrit au suivi des versions des addons (`DATA_ADDONS` de `forever/addons.py`, `forever addons status`) : version de l'addon et empreinte de ses fichiers dans la provenance (décision 124). Ses données sont figées sur le client 1.60.1.69913 : le client installé fait foi, l'addon sert au recoupement et à ce que le client ne porte pas (bêtes, niveaux, zones).
- **Sources** : client (vérité pour les familles, les capacités, les rangs et leurs coûts) ; Forever Bestiary (`tasks/inventaire-addons.md`, sans licence : lecture locale, seuls des agrégats dans le dépôt) ; Questie (niveaux et zones des PNJ, base Classic sans correction Forever) ; mes journaux et ForeverLogger (mesures du protocole) ; relevés de joueurs et guides (héritage, vitesse d'attaque : source et date citées) ; notes officielles (signal, décision 148).
- **Hors périmètre** : choix du meilleur familier par contexte (leveling, donjon, raid, PvP), dégâts du familier et sa part dans les dégâts du Chasseur, moteur du Chasseur (CH1) ; partie raid (CH1r) ; aucune écriture dans `ForeverBestiaryDB`.
- **Critères de fin** : fixés au plan ; au moins : chaque famille, capacité et rang consultable avec source et certitude par champ ; recoupement client ↔ Forever Bestiary documenté (écarts listés) ; guide d'apprivoisement rendu pour une zone et un niveau sur fixture, sans réseau, avec provenance (version et empreinte de l'addon, date de la carte communautaire) ; aucun nom de joueur tiers dans une sortie (test) ; protocole de mesure écrit ; entrées du registre à jour ; `uv run tasks.py verify` vert.

## FA1 — ForeverAssist V1 (affichage de données précalculées)
Addon d'affichage seul (règles et canaux : `docs/ADDON.md`). Aucun calcul de combat dans l'addon : `forever` précalcule, l'addon affiche.
- **Fait** : `forever export-addon` génère `addon/ForeverAssist/Data/Generated.lua` (schéma versionné, build, date de génération, écriture atomique) à partir des calculs de forever pour un personnage : **talent suivant proposé à chaque gain de niveau** (ordre de talents de l'optimiseur T05) et **comparaison de l'équipement dans l'infobulle des objets** (valeur des statistiques au niveau du personnage, calculée par le moteur ; l'addon affiche l'écart avec l'objet porté) ; table des monstres de la zone (PV mesurés, source). Affichage hors combat (`PLAYER_LEVEL_UP`, `TooltipDataProcessor`, `pcall`, `issecretvalue`), panneau `/fa`, avertissement si la build du client diffère de celle des données.
- **Hors périmètre** : fiches PvP (extension FA1p, après PV1) ; conseil en combat, conversation, écriture de SavedVariables (V2), analyse des journaux (V3).
- **Critères de fin** :
    - Le fichier généré est déterministe et validé par un schéma (pytest) ; `Generated.sample.lua` versionné, `Generated.lua` ignoré par git.
    - Au gain de niveau, l'addon affiche le talent prévu pour ce niveau par les données ; l'infobulle d'un objet affiche l'écart avec l'objet porté (tests hors jeu sur bouchons de l'API).
    - `test_addon_rules.py` étendu à ForeverAssist ; procédure de test en jeu dans `docs/ADDON.md`.

## PV2 — PvP : champs de bataille et monde ouvert
- **Fait** :
    - Champs de bataille : liste, niveaux d'accès, objectifs et conditions de victoire, récompenses (monnaie ou honneur, rang, marques : système de Forever à confirmer), temps de partie observés.
    - Équipement PvP : objets, exigences (rang, réputation, niveau), coûts ; statistiques lues dans le client quand elles y sont ; la comparaison chiffrée et l'optimisation restent en T10.
    - PvP en monde ouvert : type de royaume et règles, zones contestées, objectifs mondiaux et leurs récompenses, selon les annonces.
    - Rendements décroissants mesurés dans mes journaux de champs de bataille : `forever logs pvp` relève les contrôles appliqués aux joueurs (aura posée puis retirée), leur rang dans la suite d'une même catégorie et leur durée observée ; les ruptures (dégâts, dissipation, bijou, mort) sont écartées quand le journal les montre. Les entrées du registre passent en `valide-journal` quand `n` atteint `tolerance.n_min`.
    - Fixtures : journal de champ de bataille anonymisé (noms des autres joueurs remplacés, décision 49), compressé.
    - `forever bg info <champ>`, `forever pvp gear`, `forever pvp world` ; consultation MCP par `forever_lookup`, domaine `pvp` étendue.
- **Sources** : client (cartes et listes de champs de bataille, objets PvP, tables de monnaie : noms de tables à identifier à l'inventaire) ; annonces officielles (dates, liste, système de récompenses, règles du monde ouvert) ; communauté (vendeurs et coûts, faits de stratégie sourcés, `suppose`) ; journaux (mes parties : contrôles, recharges adverses observées après coup, durées) ; addon (résultat de partie et honneur relevés hors combat, API à sonder sous `pcall`).
- **Hors périmètre** : analyse de mes affrontements (AN1) ; suivi de ma progression PvP (repris par LG2, même import après T07) ; suivi des recharges adverses en direct (impossible) ; classement ou matchmaking.
- **Critères de fin** :
    - `forever logs pvp` sur la fixture renvoie les contrôles par catégorie et rang, avec durée observée, écart à la règle des données et provenance, code 0, sans réseau.
    - Au moins une entrée de rendement décroissant porte une preuve de journal contrôlée par le registre, ou la tranche documente le manque de données.
    - `forever bg info` et `forever pvp gear` rendent des données avec source et certitude par champ ; toute information non annoncée est absente, pas devinée.
- **À vérifier au plan (pistes du 2026-10-01, notes officielles lues le 2026-10-02)** : les sujets officiels du forum lus par `forever notes` (notes de développement <https://us.forums.blizzard.com/en/wow/t/2360696>, problèmes connus <https://us.forums.blizzard.com/en/wow/t/2352687>, Guerrier du 2026-10-02, annonce de la BlizzCon) ne disent rien des types de royaume (Normal, PvP, RP, puis Hardcore selon les pistes), des champs de bataille mixtes, ni de Darkspear Islands (15 contre 15, points et drapeaux selon les pistes). Ces points restent des affirmations à retrouver dans une source officielle (site d'actualités de Blizzard, non lu) avant d'entrer dans les données. Deux points JcJ figurent dans les notes de développement (texte lu) : Sap marque désormais le Voleur JcJ sur une cible marquée JcJ, et Touch of the Grave ne rompt plus les contrôles sensibles aux dégâts. Note officielle du 01/10 (<https://us.forums.blizzard.com/en/wow/t/2360696/4>, révision 4, `docs/research/notes-blizzard-2026-10-01.md`) : coûts en honneur de l'équipement PvP et des jetons relevés d'environ 50 %, plafond d'honneur porté à 25 000 (règles du serveur, `probable`, registre K6) ; à reprendre dans les récompenses et l'équipement PvP de cette tranche, et dans le suivi de l'honneur (LG2).

## AN1 — Analyse PvP de mes combats
Analyse après coup, hors du jeu, de mes affrontements en champ de bataille et en PvP de monde ouvert, à partir de mes journaux (`WoWCombatLog-*.txt`, ForeverLogger) et du profil du personnage actif (décision 104). Tout est lu et traité en local ; les autres joueurs des journaux restent anonymisés.
- **Fait** :
    - Découpe des journaux en affrontements (combat contre des joueurs, carte et zone, morts) ; personnage analysé : le joueur « à moi » du journal, rattaché au profil par l'import de PV1 ; autres joueurs anonymisés dès la lecture (classe et niveau gardés, nom remplacé, décision 49), jamais écrits en clair dans une sortie ou un rapport.
    - Pour chaque affrontement :
        - mes contrôles donnés et subis : sort, catégorie, rang dans la suite de rendements décroissants (fonction de PV1, règles mesurées en PV2), durée pleine et durée effective, rupture, contrôle perdu sur une cible immunisée ;
        - mes temps de recharge offensifs et défensifs : utilisés, gâchés (prêts mais inutilisés pendant une fenêtre où ils servaient) ou trop tardifs (après le seuil de danger, pendant un contrôle, après la mort de la cible) ; seuils dans les données, jamais dans le code ;
        - mes fenêtres de burst : recharges offensives réunies, cible contrôlée, défensifs adverses indisponibles tels que le journal les montre ;
        - mes interruptions données et subies (sort coupé, école verrouillée), tentatives perdues ;
        - mes morts et leur cause : dégâts reçus avant la mort par source et par sort, contrôles subis à ce moment, défensifs prêts et inutilisés ;
        - le choix de mes cibles : cibles frappées, leur classe, leur état (PV, défensifs, contrôle), changements de cible ;
        - la comparaison avec ce que recommande la fiche d'affrontement de PV1 selon la classe adverse : chaque écart cite la ligne de la fiche et sa certitude.
    - Mes taux réels (critique, raté, résistance) comparés au modèle du moteur de la classe, avec l'effectif et l'intervalle ; un écart significatif ou une mesure suffisante devient une preuve proposée au registre (champ `preuves`, `valide-journal` quand `n` atteint `tolerance.n_min`), jamais écrite sans accord (précédent : décision 68).
    - `forever analyze <journal> [--combat N]` (texte, `--json`, provenance) : sans `--combat`, liste des combats du journal (contexte, durée, adversaires anonymisés) ; avec, analyse d'un combat. Outil MCP de calcul séparé (décision 63, nom au plan, par exemple `forever_analyze`). Rapport Markdown avec graphique (chronologie des contrôles, des recharges et des PV ; PNG déterministe, décision 60), écrit hors du dépôt.
    - Skill `forever-analyse-pvp` (« analyse mon dernier champ de bataille », « pourquoi je suis mort »).
- **Classes** : l'analyse vaut pour la classe du personnage analysé dès que cette classe a son moteur : le Mage en AN1, puis chaque tranche de classe étend l'analyse à sa classe. Personnage d'une classe sans moteur : l'analyse le dit et cite la tranche, sans rien estimer.
- **Sources** : journaux (source principale, lus sur disque, dossier `FOREVER_WOW_DIR`) ; addon (ForeverLogger : niveau et talents à l'instant du combat) ; profil ; données de PV1 et de PV2 ; moteur de la classe.
- **Hors périmètre** : conseil en direct ou dans le jeu (V3 et addon exclus) ; simulation de duel ; analyse des autres joueurs pour eux-mêmes ; analyse PvE (AN2).
- **Critères de fin** :
    - `forever analyze` sur une fixture de journal de champ de bataille anonymisée (PV2) liste les combats et analyse un combat : contrôles avec rang de rendement décroissant, recharges classées, interruptions, une mort attribuée à ses sources, cibles ; déterministe, provenance, code 0, sans réseau.
    - Aucun nom de joueur tiers dans une sortie ni dans le rapport (test sur la fixture et sur un journal synthétique à noms connus).
    - Un taux réel est comparé au modèle avec son intervalle ; la preuve proposée au registre n'est écrite qu'après accord.
    - Personnage d'une classe sans moteur : refus explicite avec la tranche.
    - Rapport Markdown et PNG identiques octet pour octet entre deux générations ; outil MCP listé, provenance au contrat ; skill `forever-analyse-pvp` et carte du routeur à jour ; `uv run tasks.py verify` vert.

## Tranches de classe (PA1, DE1, PR1, CH1, CM1, GU1, VO1, DR1)
Remplacent T12 (décision 102) : une tranche par classe pour les 8 classes autres que le Mage, chacune avec le leveling, le donjon et le PvP, sans attendre T09. Ordre proposé selon les briques de moteur à partager (décision 103), en commençant par le Paladin et le Démoniste (mes personnages, briques égales) :

**Toutes les spécialisations et tous les rôles** (décision 146) : chaque tranche de classe couvre **toutes** les spécialisations de sa classe et **tous** les rôles qu'elles tiennent, pas seulement la spécialisation de dégâts. Chaque build est jugé sur la mesure de son rôle :

| Rôle | Mesure |
| --- | --- |
| Dégâts | dégâts par seconde |
| Soins | soins par seconde et efficacité de la mana (soins par point de mana dépensé) |
| Tank | dégâts encaissés (après mitigation) et menace générée |

En leveling, la mesure reste le temps par monstre et l'XP par heure pour toutes les spécialisations (un soigneur ou un tank monte de niveau seul), avec les dégâts encaissés ; en donjon et en raid, la mesure du rôle. Le PvP reste un profil comparatif (décision 102).

| Classe | Spécialisations (rôle) | Tranche |
| --- | --- | --- |
| Paladin | Sacré (soins), Protection (tank), Vindicte (dégâts) | PA1 (raid : T09 pour Sacré et Protection, PA1r pour Vindicte) |
| Chasseur | Maîtrise des bêtes, Précision, Survie (dégâts) | CH1 |
| Démoniste | Affliction, Démonologie, Destruction (dégâts) | DE1 |
| Prêtre | Discipline (soins), Sacré (soins), Ombre (dégâts) | PR1 |
| Druide | Équilibre (dégâts), Farouche félin (dégâts) et ours (tank), Restauration (soins) | DR1 |
| Chaman | Élémentaire (dégâts), Amélioration (dégâts), Restauration (soins) | CM1 |
| Guerrier | Armes (dégâts), Fureur (dégâts), Protection (tank) | GU1 |
| Voleur | Assassinat, Combat, Finesse (dégâts) | VO1 |
| Mage | Arcanes, Feu, Givre (dégâts) | T02 à T05 (fait) ; raid en T09 |

**Briques des soigneurs et des tanks** : elles naissent dans la **première tranche qui en a besoin**, PA1 (Paladin Sacré et Protection), puis sont reprises : soins (puissance et critique des soins, coefficients du client, soins perdus en excès, efficacité de la mana) ; mitigation (armure, esquive, parade et blocage subis, réduction des dégâts, PV et Endurance) ; menace (menace par point de dégâts et de soins, multiplicateurs de posture, de forme ou d'aura, sorts de provocation). Chaque brique a ses entrées au registre et ses valeurs dans `forever/data/<version>/`.

| Tranche | Classe | Briques nouvelles | Briques reprises | Partie raid |
| --- | --- | --- | --- | --- |
| PA1 | Paladin | table d'attaque de mêlée (armes, coups blancs, esquive, parade, blocage), **soins** (puissance et critique des soins, efficacité de la mana), **mitigation**, **menace**, sceaux et jugements, auras ; mesures des trois rôles dans l'optimiseur ; espace de classe du moteur (décision 31) | cœur de sorts du Mage (toucher, critique, coefficients du client) | Sacré et Protection en T09 ; Vindicte en PA1r |
| DE1 | Démoniste | familiers (entité à part : statistiques, part des dégâts, sorts), DoT multiples, fragments d'âme, conversion de vie en mana | sorts, toucher, critique ; espace de classe (PA1) | T09 (trois spécialisations) |
| PR1 | Prêtre | Forme d'ombre, boucliers d'absorption | soins et mesure des soigneurs (PA1), DoT (DE1) | T09 (trois spécialisations) |
| CH1 | Chasseur | attaque à distance, munitions, aspects, familier du Chasseur (statistiques héritées, capacités de sa famille et de leurs rangs) et choix du familier par contexte | table d'attaque (PA1), familiers (DE1), savoir des familiers (CH0) | CH1r |
| CM1 | Chaman | totems, horions | mêlée (PA1), soins (PA1, PR1), sorts | CM1r |
| GU1 | Guerrier | rage, postures, double arme | table de mêlée, mitigation et menace (PA1) | GU1r |
| VO1 | Voleur | énergie, points de combo, furtivité, poisons | table de mêlée et double arme (PA1, GU1) | VO1r |
| DR1 | Druide | formes (changement de ressource, de table d'attaque et de sorts) | rage (GU1), énergie et points de combo (VO1), soins (PA1, PR1), mitigation et menace (PA1, GU1), sorts | DR1r |

- **Fait (chaque tranche)** :
    - **Savoir propre à la classe** (décision 155) : ce que la classe a et que les autres n'ont pas, lu dans le client puis recoupé avec les addons de données, avec source et certitude par champ : démons et grimoires du Démoniste (DE1), totems du Chaman (CM1), formes du Druide (DR1), postures du Guerrier (GU1), poisons du Voleur (VO1), sceaux et auras du Paladin (PA1), familiers du Chasseur (pris en avance par CH0, CH1 n'en garde que le calcul)… ; consultable par la CLI et le MCP ; liste fixée au plan de chaque tranche.
    - Moteur de la classe dans `forever/engine/` (fonctions pures, `GameData` de la classe décodé en PV1) : ressources, règles propres, rotations de **chaque** spécialisation, soins, mitigation et menace pour les spécialisations qui soignent ou qui tankent ; valeurs dans `forever/data/<version>/`, entrées du registre par mécanique (statut, source, tests) ; règle incertaine `suppose` avec sa question dans `docs/OPEN_QUESTIONS.md`.
    - Simulateurs de leveling (Monte Carlo et analytique) et scénarios de donjon (ceux de T05 en attendant DJ1) pour la classe ; profil PvP comparatif de la classe (rendements décroissants et bijou de PV1).
    - Builds par contexte (`leveling`, `dungeon`, `pvp-bg`, `pvp-world`), pour chaque spécialisation et chaque rôle, jugés sur la mesure du rôle (table plus haut), avec l'optimiseur de T05 : talents et ordre, raison de chaque choix, alternative et écart apparié, stabilité, sensibilité, respec, angles morts ; `forever build <contexte> --class <classe>` et `forever_build` (forme au plan) ; raciaux décodés en PV1 dans les calculs ; comparaison avec les builds de la communauté (bloc J de T05).
    - Mesures sur mes journaux de la classe quand j'en ai (coûts, intervalles, critiques) et preuves du registre.
    - Analyse de mes combats PvP (AN1) étendue à la classe ; profil du personnage de la classe validé.
    - Skill `forever-<classe>` (sorts, talents, mécaniques, rotations de la classe), carte du routeur et skill `forever-builds` à jour (la classe passe de « communautaire » à « calculé »).
- **Hors périmètre** : raid (T09 pour les spécialisations de son moteur porté, sinon la partie raid `…r` de la classe après T09) ; équipement réel (T10) ; mana des combats longs (T05b, qui couvre ensuite toutes les classes à mana ; en attendant, la mention de T05 s'applique à chaque sortie de donjon).
- **Critères de fin (chaque tranche, précisés au plan)** : `forever build <contexte> --class <classe> --level N` pour les quatre contextes et pour chaque spécialisation et chaque rôle de la classe (mesure du rôle dans la sortie), légal, avec provenance et certitude ; analytique à la tolérance du plan du Monte Carlo sur une grille de niveaux ; toute mécanique de la classe utilisée par le moteur au registre avec un test ; comparaison communautaire documentée ; analyse AN1 d'un combat de la classe sur fixture ; skill sans chiffre de jeu, évaluation du plugin étendue à la classe (questions générales et personnelles) ; `uv run tasks.py verify` vert.

## T05b — Mana des combats longs
- **Pourquoi** : en T05, la mana borne les scénarios de donjon et de raid (fiche de base, sans Évocation ni potion) ; l'angle mort B10 a une borne haute de 86 à 144 % de la métrique (`docs/research/builds-T05.md`) : les classements de donjon et de raid sont fragiles. Placée après les tranches de classe et avant AN2 (décision 110 ; place précédente : après FA1 et avant DJ1, décision 90) : AN2 en a besoin pour rejouer un donjon ou un raid, et elle couvre alors toutes les classes à mana.
- **Fait** : Évocation (recharge, durée, régénération lues dans le client), potions et gemmes de mana (rendement, recharges partagées, rangs par niveau), régénération en combat (règle des 5 s si Forever la garde, B7) dans `forever/sim/encounter.py` et l'analytique ; politique d'usage (au plus tôt utile, sous un seuil de mana) ; rotation qui s'adapte à la mana restante (I8) ; B10 passe de l'angle mort au modèle ; `forever build dungeon|raid` refait aux niveaux 20, 40, 60. Autres classes à mana : règles communes (potions, régénération en combat) appliquées à leurs scénarios ; recharges de mana propres à une classe modélisées avec leur mécanique (entrée du registre), dans les scénarios de la classe.
- **En attendant** : chaque sortie de donjon et de raid de `forever build` et de `forever_build`, pour toute classe, affiche que la mana des combats longs n'est pas modélisée (hypothèse du rapport).
- **Critères de fin** : Évocation et potions dans les deux simulateurs des scénarios, analytique à ±3 % du Monte Carlo sur un boss avec fin de mana ; B10 `teste` ; sensibilité des builds de donjon et de raid recalculée ; `uv run tasks.py verify` vert.

## AN2 — Analyse PvE de mes combats
Même principe que AN1, pour le leveling, le donjon et le raid, chaque boss en particulier (décision 104). Placée après les tranches de classe (toutes les classes ont alors leur moteur) et après T05b (sans la mana des combats longs, le rejeu d'un donjon ou d'un raid et la panne de ressource seraient faux).
- **Fait** :
    - Découpe en combats PvE : suite de monstres en leveling, donjon, raid, chaque boss à part (événements de rencontre quand le journal les donne, sinon cible principale) ; contexte détecté par la carte et le type d'instance du journal, forçable par `--context`. Le boss est reconnu par son identifiant de PNJ, son niveau et ses PV lus dans le bloc avancé ; DJ1 et T09 y ajouteront nom et données de rencontre.
    - Ma rotation réelle : suite des sorts horodatée, temps morts (ni incantation ni lancer), temps de recharge global gâché (retard entre la fin d'une recharge globale et le lancer suivant, au-delà de la latence mesurée par B1), incantations coupées ou annulées.
    - Mes écarts avec la rotation optimale du simulateur de la classe : mauvais sort (priorité non suivie), gestion des ressources et des cumuls (cumuls perdus ou expirés lus dans le journal), temps de recharge mal placés (tenus trop longtemps, hors fenêtre), panne de ressource évitable (ressource épuisée là où la rotation optimale finit le combat).
    - Perte chiffrée : le même combat rejoué avec la rotation optimale (même durée, même cible : niveau, PV et armure lus dans le journal, mêmes auras observées), Monte Carlo à tirages communs, écart en dégâts et en DPS avec intervalle (décision 85), décomposé par type d'écart ; « non départagé » quand l'intervalle contient zéro.
    - Mes taux réels comparés au modèle et preuves proposées au registre (comme AN1).
    - `forever analyze` étendu au PvE (même commande, même outil MCP), rapport Markdown avec graphique (sorts réels et optimaux sur une même chronologie, ressource).
    - Skill `forever-analyse-pve` (« analyse mon dernier boss », « combien je perds sur ma rotation »).
- **Classes** : toutes les classes à moteur ; en raid, le rejeu passe par le scénario provisoire de T05 jusqu'à T09 et aux parties raid, qui y branchent leur moteur.
- **Sources** : journaux (source principale, en local) ; addon (niveau et talents à l'instant du combat) ; profil ; simulateurs des classes.
- **Hors périmètre** : conseil en direct ; stratégie de boss recopiée d'un guide ; analyse des autres joueurs.
- **Critères de fin** :
    - Sur une fixture de journal de donjon anonymisée avec un boss : rotation réelle, temps morts et recharge globale gâchée extraits ; écarts classés ; perte chiffrée avec intervalle, déterministe à graine fixe ; provenance, code 0, sans réseau.
    - Un journal synthétique qui suit la rotation optimale donne une perte non significative ; un journal synthétique avec une panne de mana évitable la signale.
    - Aucun nom de joueur tiers dans les sorties ; rapport et PNG déterministes ; skill et routeur à jour ; `uv run tasks.py verify` vert.

## T04d — Quêtes Forever et XP
- **À faire** (reporté de T04c) : ingestion des quêtes propres à Forever (`QuestieForeverDB`) et modèle d'XP (XP des monstres et des quêtes de Forever, remplaçant la règle Classic `leveling.mob_xp`) ; durée d'infobulle dans `tooltip_values`. Routes de leveling : pas de tranche dédiée (le joueur suit RestedXP en jeu ; RestedXP reste exclu comme source de données, `docs/DATA_SOURCES.md`). La réponse « quelle zone ou quel donjon à mon niveau » est faite en T04c (`forever lookup zones`, Questie lu localement, `suppose`) ; DJ1 affinera la partie donjons. Les quêtes de donjon restent ici ; DJ1 s'y réfère.
- **Place** : après AN2 (décision 111 ; place précédente : après T06, décision 78). Ses sources dépendent de l'inventaire des addons (`tasks/inventaire-addons.md` : ForeverDungeonJournal pour l'XP des quêtes, GearQuestForever pour la liste des quêtes absentes de Questie, tables de quêtes du client) ; l'XP ne change pas le classement des builds de T05, qui compare des taux de dégâts et de temps par monstre.
- **Critères de fin** : à fixer au plan de T04d.

## DJ1 — Donjons
- **Fait** :
    - Liste des donjons de Forever avec plages de niveau (accès, recommandé) ; boss et leur niveau ; butin par boss (objets, emplacement, exigence de classe) avec taux quand une source existe ; donjons nouveaux ou modifiés dans Forever ; lien vers les quêtes de donjon de T04c ; `forever dungeon list --level N`, `forever dungeon info <donjon>`, `forever dungeon item <objet>` (« où trouver tel objet » : boss, donjon, source et version ; forme au plan), consultation MCP par `forever_lookup`, domaine `dungeons` ; fichier de données par version avec certitude par champ.
    - Addons de données (décisions 123 et 124) : lecteurs locaux d'AtlasLoot Classic Forever (butin par boss, valeur Classic de `GetForVersion`, taux Classic `suppose`) et de ForeverDungeonJournal (donjons, boss, quêtes de donjon, `Data/` en plusieurs fichiers depuis la 1.3.1) ; seuls des agrégats et des valeurs recoupées entrent dans le dépôt, la version de l'addon et l'empreinte de ses fichiers dans la provenance.
    - **`forever addons status`** (**avancé en T08b**, décision 147 : DJ1 y branche ses lecteurs d'AtlasLoot et de ForeverDungeonJournal ; description d'origine) : pour chaque addon de données installé (AtlasLoot, ForeverDungeonJournal, Questie, GearQuestForever, Auctionator), version lue dans le `.toc`, empreinte des fichiers de données, date du dernier relevé, statut « inchangé » ou « changé » et agrégats du dépôt touchés ; la chaîne de version ne suffit pas (AtlasLoot 1.1.3 est le nom de sa version sur CurseForge, absent de ses fichiers, `docs/DATA_SOURCES.md`) : la comparaison se fait par empreinte. Lecture sur disque, sans réseau ; l'automatisation vient en T08.
    - **Relevé hors combat de ForeverLogger** (décision 127) : objets et prix des marchands à l'ouverture d'un marchand, butin ramassé, gains de réputation ; chaque API sondée sous `pcall`, aucun abonnement au journal de combat ni fonction d'action (`docs/ADDON.md`, `scripts/check_addon.py`). Une observation réelle l'emporte sur la donnée d'un addon et passe `certain` ; l'écart est signalé avec la valeur de l'addon et sa version en regard. Les gains de réputation relevés servent RP1.
- **À reprendre au plan (note officielle du 01/10, <https://us.forums.blizzard.com/en/wow/t/2360696/4>, révision 4, `docs/research/notes-blizzard-2026-10-01.md`)** : nouveau donjon Excavation Site: Wetlands (26-31) ; Razorfen Downs (25+) et Uldaman (30+) ouverts, en plus de Ragefire Chasm, Hall of Thanes, Ruins of Lordaeron, Wailing Caverns, The Deadmines, Shadowfang Keep, The Stockade, Blackfathom Deeps, Gnomeregan, Razorfen Kraul et Scarlet Monastery ; niveaux d'accès annoncés, `probable` jusqu'à leur lecture dans le client ou en jeu. Quêtes de donjon : bonus d'XP au-delà de la valeur normale réduit de moitié (registre I9, modèle d'XP en T04d).
- **Sources** : client (instances, niveaux, objets ; tables de journal de rencontre et de butin à identifier à l'inventaire, sans présumer de leur présence ; les taux de butin sont absents du client, `docs/DATA_SOURCES.md`) ; annonces officielles (donjons nouveaux ou modifiés, niveaux) ; communauté (AtlasLoot et ForeverDungeonJournal, première source communautaire, `suppose`, lecture locale libre, addons à jour pour Forever seulement (décision 133), Forever Guide s'il est installé ; Wowhead Forever en contrôle ponctuel par le sous-agent de recherche ; les niveaux des boss hérités de ForeverDungeonJournal sont une copie de Classic, pas un recoupement de H1) ; journaux (niveau et PV des boss et des monstres par le bloc avancé, registre H1, durée des passages) ; addon (relevé hors combat de ForeverLogger, plus haut).
- **Hors périmètre** : stratégies de boss détaillées recopiées d'un guide ; valeur chiffrée d'un objet pour un personnage (T10) ; raids (T09 à T11) ; relecture automatique à chaque changement de version d'un addon (T08).
- **Critères de fin** :
    - `forever dungeon list --level N` et `forever dungeon info` sur les données de test rendent niveaux, boss et butin avec provenance (version de l'addon comprise) ; un taux absent est affiché comme inconnu.
    - Le niveau d'un boss mesuré dans une fixture de journal l'emporte sur la valeur communautaire et passe `certain`.
    - `forever addons status` sur des fixtures d'addons signale « changé » quand la version ou l'empreinte des fichiers de données change (y compris à chaîne de version identique), « inchangé » sinon, sans réseau.
    - Un butin ou un prix de marchand relevé dans une fixture de SavedVariable de ForeverLogger l'emporte sur la valeur d'addon, passe `certain`, et l'écart est signalé ; `test_addon_rules.py` vert.

## LG1 — Legacy : catalogue et conseil par personnage
Placé avant T07 parce que les bonus Legacy pèsent sur le leveling : le catalogue et le conseil n'ont pas besoin de la mémoire joueur (état Legacy saisi en paramètre, personnages lus dans le profil). Placé après les tranches de classe : le conseil est chiffré pour chacun de mes personnages par le moteur de sa classe (décision 112). Le suivi vient en LG2.
- **Fait** : catalogue des défis (conditions, points rapportés), des points et des arbres de bonus (nœuds, coûts, prérequis, effets, réinitialisation) ; effets chiffrés dans les données quand le client ou une annonce les donne, sinon marqués inconnus ; conseil des bonus pour chacun de mes personnages (profil), chiffré par le moteur de sa classe (effet sur le temps par monstre et l'XP par heure du simulateur de leveling de la classe) ; registre G5 mis à jour ; `forever legacy catalog`, `forever legacy advise --class <classe> [--state F] [--goal leveling|pvp|raid]`, consultation MCP par `forever_lookup`, domaine `legacy` pour le catalogue, outil de calcul séparé pour le conseil (il appelle le simulateur de leveling).
- **Sources** : client (tables des arbres et des défis à identifier à l'inventaire) ; annonces officielles (système Legacy, état en bêta et au lancement) ; communauté (Icy Veins et Wowhead Forever, noms d'arbres divergents à recouper, `suppose`) ; journaux (validation d'un bonus mesurable, par exemple un gain d'XP) ; addon (lecture de la progression : LG2).
- **Hors périmètre** : suivi de ma progression (LG2) ; points Legacy des métiers (MT1, qui s'appuie sur ce catalogue).
- **Critères de fin** :
    - Le catalogue passe `verify` (prérequis cohérents, coûts présents ou marqués inconnus, source par entrée).
    - `forever legacy advise` rend un ordre déterministe pour un personnage de chaque classe, avec justification et certitude ; le gain vient d'un appel au simulateur de leveling de la classe (aucun calcul dans l'outil).
- **À vérifier au plan (pistes du 2026-10-01, notes officielles lues le 2026-10-02)** : seul signal officiel lu, les problèmes connus (<https://us.forums.blizzard.com/en/wow/t/2352687>) : la fenêtre Legacy s'ouvre par erreur (touche Y) avant le niveau 25, d'où un déblocage au niveau 25 (signal, pas une valeur). Les 65 défis, les rangs PvP 3, 7, 10, 13 et 14, les réputations de champs de bataille, Field of Honor et les perks n'apparaissent dans aucun sujet officiel lu : à chercher dans une source officielle avant le catalogue. Plafond de niveau à 30 : **observé en jeu par l'utilisateur** le 2026-10-01 et installé avec 1.60.1.70170 le 2026-10-02 (`meta.json` `game_state`, origine journal, `certain`), puis annoncé par la note officielle du 01/10 (<https://us.forums.blizzard.com/en/wow/t/2360696/4>, révision 4, `docs/research/notes-blizzard-2026-10-01.md`). Date de lancement : absente des sujets lus.

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
- **Fait** : import complet et multi-sources (décision 125) et fiches du vault ; l'import automatique minimal du profil (classe, race, niveau, talents) et la règle de fusion sont faits au début de PV1 (décision 105), T07 les prolonge sans changer le schéma : ForeverLogger (équipement, métiers, réputations, historique, observations de DJ1), quêtes faites de mes personnages dans Questie, mes relevés de prix d'Auctionator (lecture de mes SavedVariables, décision 123), journaux ; chaque champ garde sa source et sa date, la plus récente l'emporte (à date égale la plus directe), l'écart est signalé. L'API Blizzard s'y branche en EC1.
- **Critères de fin** : import d'un export d'addon d'exemple ; fiche écrite dans le vault avec la version du jeu ; une fiche plus ancienne que la version courante est signalée ; sur des fixtures de deux sources en désaccord (ForeverLogger et Questie, par exemple), la plus récente l'emporte et l'écart figure dans la sortie.

## LG2 — Suivi de ma progression Legacy
- **Fait** : lecture de la progression Legacy du compte (défis faits, points gagnés et dépensés, nœuds pris) par l'addon hors combat (ForeverLogger ou ForeverAssist V2, API à sonder sous `pcall`), import par la voie de T07 dans `legacy.json` du vault (avec la version du jeu) ; `forever legacy status` : points disponibles, prochains défis accessibles par personnage, conseil de LG1 recalculé sur l'état réel ; par le même import, honneur et rang PvP (PV2) dans la fiche du personnage, pour répondre à « où j'en suis en PvP » (décision 130 ; classements par l'API en EC1).
- **Sources** : addon (source principale) ; client et catalogue de LG1 ; annonces officielles (changements du système) ; communauté (recoupement) ; journaux (rien).
- **Hors périmètre** : écriture en jeu ; note d'impact Legacy par version (T08).
- **Critères de fin** : import d'une SavedVariable d'exemple (fixture) ; `legacy.json` régénéré de façon déterministe ; une progression plus ancienne que la version courante est signalée ; `forever legacy status` avec provenance.

## MT1 — Métiers
- **Fait** : recettes par métier (composants, objet créé, niveau requis, seuils de couleur de difficulté) ; sources des recettes (entraîneur, vendeur, butin, quête) ; changements de Forever (recettes retirées ou ajoutées, bonus de métier) ; plan de montée de compétence `forever profession plan <métier> --from A --to B` qui minimise le nombre de fabrications (puis le coût quand EC1 fournit les prix) ; points Legacy des métiers par palier, depuis le catalogue de LG1 ; **répartition des métiers sur l'ensemble de mes personnages, existants et prévus** (décisions 107 et 119) : qui prend quel métier selon les besoins de chaque personnage (classe, niveau, contextes joués : consommables, équipement fabriqué, points Legacy) et les couples récolte-fabrication, `forever profession split` (forme au plan), objectif en paramètre, hypothèses affichées ; niveaux actuels lus dans la fiche du vault (T07) sinon saisis ; registre G6 mis à jour ; consultation MCP par `forever_lookup`, domaine `professions` pour les recettes, outil de calcul séparé pour le plan de montée.
- **Sources** : client (lignes de compétence et recettes, composants, objets créés, seuils de couleur ; certain) ; annonces officielles (changements de métiers, points Legacy) ; communauté (listes d'entraîneurs et sources de recettes, absentes du client ; chance de gain de point par couleur, règle Classic `suppose` ; `alcaras/forever-ref` en recoupement) ; journaux (rien : l'artisanat n'est pas un événement de combat utile) ; addon (niveaux de compétence et recettes connues, lus hors combat sous `pcall`).
- **Hors périmètre** : prix et rentabilité (EC1) ; consommables de raid (T11).
- **Critères de fin** : recettes décodées depuis des fixtures wago pour deux métiers ; `forever profession plan` déterministe à graine fixe, avec provenance et hypothèses (chance de gain `suppose`) ; points Legacy rattachés au catalogue de LG1 ou marqués inconnus ; `forever profession split` déterministe sur un profil d'exemple à plusieurs personnages de classes différentes, avec provenance.

## RP1 — Réputations
- **Fait** : factions de Forever (nouvelles ou modifiées), paliers, sources de réputation (quêtes, monstres, objets remis) et leurs gains, récompenses par palier (objets, recettes, accès) ; état actuel importé depuis l'addon (T07) ; gains relevés hors combat par ForeverLogger (relevé ajouté en DJ1, `certain`, écart signalé face à une source communautaire) ; « combien coûte telle réputation » (décision 130) : temps, objets remis et leur prix (mes relevés d'Auctionator, puis l'API en EC1), source et version citées ; `forever rep info <faction>`, `forever rep plan --faction X --to <palier>` (temps estimé à partir des gains et, pour les monstres, du temps par monstre du simulateur de leveling) ; consultation MCP par `forever_lookup`, domaine `reputations` pour les factions, outil de calcul séparé pour le plan.
- **Sources** : client (factions et paliers ; tables à identifier à l'inventaire) ; annonces officielles (réputations de Forever) ; communauté (gains par source, récompenses par palier, `suppose`) ; journaux (rien) ; addon (paliers et valeurs actuels, gains relevés hors combat par le relevé de DJ1, sous `pcall`) ; addons de données (candidat à chercher, `docs/DATA_SOURCES.md`, « Données manquantes »).
- **Hors périmètre** : valeur chiffrée des récompenses (T10).
- **Critères de fin** : `forever rep info` avec source et certitude par champ ; `forever rep plan` déterministe sur un état d'exemple importé d'une fixture de SavedVariable.

## T08 — Veille
- **Fait (repris de T03)** (l'installation pour 1.60.1.70009 passe en T06b ; **l'installation d'une nouvelle version et la veille planifiée passent en T08a**, décision 134) : application de `overrides.json` ; outil MCP `forever_diff_versions` ; baisse ciblée de la certitude des entités touchées par un diff quand le statut est `stale` (décision 19) ; lecture de `DBCache.bin` (valeurs des correctifs serveur ; la liste des tables et des lignes corrigées, tirée de `Logs/Hotfix.log`, est faite en T08b).
- **Durcissement du pipeline (relecture T03)** : `$d` entre dans les expressions `${…}` dans son unité d'affichage (minutes dès 60 s), aucune infobulle de talent ne l'exerce aujourd'hui ; un sort cité deux fois par une infobulle d'aura 226 compterait deux fois ses dégâts ; `SpellLevel` n'est pas lu (écart de niveau calculé depuis `BaseLevel`) ; `--locale` ignoré sans `--tables` ; un CSV réduit à son en-tête est accepté ; `verify` suppose `level` en tête de `rank_format`.
- **Versions des addons de données** (décision 124) : à chaque veille, `forever addons status` (T08b) compare version et empreinte des fichiers de données de chaque addon au dernier relevé (commande faite en T08b, veille locale au démarrage d'une session comprise) ; un changement relit ses données, régénère les agrégats du dépôt qui en viennent et produit une note de changement (valeurs changées, certitude, personnages touchés), comme pour une version du jeu. Lecture locale sur le poste de l'utilisateur (les addons ne sont pas sur le serveur de CI) : la veille planifiée de CI ne couvre que les versions du jeu.
- **Critères de fin** : changement de version fictif d'un addon (fixtures) → relecture et note de changement déterministes ; `forever_diff_versions` testé ; certitude abaissée sur un diff `stale`. (`build-watch.yml` simulé et alerte `silent` : passés en T08a.)

## EC1 — API Blizzard : hôtel des ventes, personnages, PvP (après le lancement du 4 novembre)
Tranche gardée : sautée tant que le lancement n'a pas eu lieu et que la couverture de Forever par l'API Blizzard (produit, espace de noms, hôtel des ventes, profils de personnages, PvP) n'est pas vérifiée. Élargie le 2026-09-30 à tout ce que l'API couvre pour Forever ; identifiant EC1 gardé (décision 126).
- **Fait** :
    - Client `forever/pipeline/bnet.py` (via `Deps.http_get`, clés dans `.env`, jamais lues par les tests).
    - Hôtel des ventes : `forever prices fetch` (prix de mon royaume, instantané daté), prix en cache hors de `forever/data/` (ce ne sont pas des données de version du jeu), âge de l'instantané dans les hypothèses ; `forever prices item <objet>` ; coût des plans de MT1, budget des consommables (T11), coût du plan d'équipement (T10) ; outil MCP séparé `forever_prices` (calcul et réseau, pas une consultation).
    - Fiches de personnages : niveau, équipement, talents si l'API les donne, branchés sur le profil multi-sources (décision 125 : source « API Blizzard » et date par champ, la plus récente l'emporte, écart signalé avec ForeverLogger).
    - PvP : honneur, rang, classements (« où j'en suis en PvP », décision 130), dans la fiche du personnage à côté de l'import de LG2.
    - Chaque partie seulement si l'API la couvre pour Forever ; une partie non couverte est listée comme telle, jamais remplacée par une autre source sans le dire.
- **Arrêt obligatoire** : le plan de EC1 s'arrête pour demander l'accord de l'utilisateur avant d'ajouter chaque accès réseau (hôtel des ventes, profils, PvP) ; une fois accordé, la commande entre dans la liste réseau de `CLAUDE.md`, de `docs/ARCHITECTURE.md` et de `tests/unit/test_network_boundary.py`.
- **Sources** : API Blizzard (source principale, après le lancement) ; addon (mes relevés de prix d'Auctionator, lus localement dans mes SavedVariables par un décodeur maison, décision 123 : repli avant le lancement et quand l'API ne couvre pas un objet) ; client (prix de vente aux marchands, tables à identifier) ; relevé des marchands par ForeverLogger (DJ1) ; annonces officielles (ouverture et couverture de l'API) ; communauté (rien) ; journaux (rien).
- **Hors périmètre** : achat ou vente automatisés ; historique long des prix ; toute écriture par l'API.
- **Critères de fin** : `forever prices fetch` et la lecture d'une fiche de personnage testés hors ligne sur des réponses d'API en fixtures (client HTTP simulé) ; échec réseau → code 5 ; `test_network_boundary.py` à jour ; plan de MT1 chiffré en or sur les prix d'une fixture ; une fiche de l'API en désaccord avec ForeverLogger (fixtures) : la plus récente l'emporte, écart signalé.

## ForeverAssist V2 et V3
- **V2 (proposée avec T07, qui lit déjà les SavedVariables)** : l'addon écrit hors combat le contexte du personnage (niveau, talents `C_Traits`, équipement, zone, quêtes) dans `ForeverAssistCharDB` ; `forever ingest-sv` le lit après un `/reload`, recalcule et régénère `Generated.lua`. Hors périmètre : tout canal temps réel. Critères de fin : lecture d'une SavedVariable d'exemple, régénération déterministe, fiche du vault mise à jour.
- **V3 (tranche FA3, après T08, AN1 et AN2)** : compagnon de bureau qui analyse `WoWCombatLog-*.txt` après le combat (`forever analyze` de AN1 et AN2, `forever logs measure`), résume le dernier combat, l'expose au MCP et prépare le fichier de V1. Hors périmètre : toute consigne en direct. Critères de fin : découpe des combats testée sur fixtures, résumé avec provenance.

## T09 — Raid
- **Fait** : moteur analytique porté de `seed/grimoire-engine/` (Mage, Démoniste, Prêtre, Paladin Sacré et Protection), Monte Carlo, parité avec wowsims Forever ; partie raid de ces classes (contexte `raid` de leurs builds) ; rejeu de raid de AN2 branché sur ce moteur.
- **Reporté de T04e** : Fire Vulnerability dans les rotations (Scorch jusqu'aux cumuls maximum, fonctions de T04e).
- **Critères de fin** : à fixer au plan de T09.

## Parties raid des classes (PA1r, CH1r, CM1r, GU1r, VO1r, DR1r)
Après T09 (décision 102). Le moteur porté de `seed/grimoire-engine/` couvre le Mage, le Démoniste, le Prêtre (Ombre, Sacré, Discipline) et le Paladin (Sacré, Protection) : leur partie raid se fait dans T09. Chaque partie `…r` branche une autre classe (ou spécialisation, comme le Paladin Vindicte) sur le moteur de raid de T09 : contexte `raid` de `forever build --class`, rejeu de raid de AN2, parité avec wowsims Forever quand il couvre la spécialisation. Critères de fin fixés au plan, sur le modèle de T09.

## T10 — Équipement et plan d'équipement
Détaillée au moment de la planifier ; ce qui est déjà fixé :
- **Plan d'équipement** par personnage et par contexte (décision 129) : pour chaque emplacement, le meilleur objet accessible au niveau du personnage (gain calculé par le moteur de sa classe, jamais par l'outil) ; où l'obtenir (boss et donjon, quête, marchand, intendant de réputation, métier, hôtel des ventes, récompense PvP) ; son coût (or, composants, réputation ou rang requis) ; le temps estimé (probabilité de butin, montée de réputation ou d'honneur). Répond à « quel objet viser à mon niveau » et « où trouver tel objet » (décision 130).
- **Sources** : données du client (objets, formules) ; addons de données (AtlasLoot et ForeverDungeonJournal pour le butin, Questie pour les récompenses de quête, GearQuestForever en recoupement seulement, Auctionator pour mes prix) ; RP1 (intendants, paliers, temps de montée) ; PV2 (récompenses PvP) ; MT1 (objets fabriqués) ; mes observations (butin et marchands relevés par ForeverLogger depuis DJ1) ; l'API Blizzard quand EC1 est faite (prix, équipement actuel), sinon mes relevés d'Auctionator, sinon prix inconnu. Aucun taux de butin de Forever n'existe à ce jour : seuls les taux Classic d'AtlasLoot (`suppose`) ; un temps estimé sur un taux absent est affiché comme inconnu.

## T11 à T13
Détaillées au moment de les planifier, avec la même structure (fait, hors périmètre, critères de fin testables).
