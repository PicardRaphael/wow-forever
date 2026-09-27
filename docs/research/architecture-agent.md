# Agent expert « WoW Forever » dans claude-forge : architecture recommandée

> Rapport de recherche du 27/09/2026 (claude.ai), recopié pour Claude Code. Sources principales en fin de fichier.
> Légende : **[Certain]** source primaire lue ; **[Probable]** recoupement ou inférence forte ; **[Supposé]** jugement d'architecture non vérifié empiriquement.

**Recommandation : ne construisez pas neuf sous-agents de classe. Construisez un plugin Claude Code organisé autour d'un cœur de calcul unique et versionné par build (`forever-core`). Ce cœur est exposé à la fois en CLI et en serveur MCP. Des skills de domaine et de classe se chargent à la demande, et quelques sous-agents « opérationnels » seulement exécutent les tâches lourdes : mise à jour des données, simulations, recherche web, évaluation.** La raison principale : les connaissances d'un expert WoW sont très interdépendantes (mécaniques, talents, objets et buffs se combinent). C'est exactement le cas où Anthropic dit que le multi-agent fonctionne mal. Les sous-agents isolés dupliqueraient la connaissance et produiraient des sources de vérité incohérentes. Les skills à divulgation progressive, adossés à des outils déterministes, donnent la spécialisation sans ce coût.

## TL;DR

- **Option recommandée : plugin hybride.** Un skill routeur `wow-forever`, des skills de domaine et un skill par classe, chargés à la demande. Un cœur `forever-core` unique (Python) fournit les données par build, les mécaniques, les simulateurs et l'optimiseur d'équipement, via CLI et MCP. Quatre sous-agents opérationnels (data-updater, sim-runner, web-researcher, eval-judge) et des hooks de fraîcheur complètent l'ensemble.
- **Option à éviter : un multi-agent hiérarchique** (un superviseur plus neuf sous-agents de classe, chacun avec sa propre connaissance). Selon Anthropic, les systèmes multi-agents utilisent environ 15× plus de tokens qu'un chat et conviennent mal aux domaines où tous les agents doivent partager le même contexte ou dépendent beaucoup les uns des autres. La taxonomie MAST attribue la majorité des échecs multi-agents à la spécification et au désalignement inter-agents.
- **La fiabilité numérique vient du code, pas du modèle.** Chaque chiffre doit sortir d'un outil qui renvoie la valeur, le build et le niveau de certitude. Les données brutes viennent des tables client DB2 via wago.tools (build 1.60.1.70009). La couverture est vérifiée par des évaluations de « régression » (tests de référence, 100 %) et de « capacité » (20 à 50 tâches issues d'échecs réels, dont des pièges Classic ≠ Forever).

## Key Findings

1. **Anthropic recommande de commencer simple et d'ajouter des agents seulement si la tâche se décompose en fils indépendants.** [Certain] Leur système de recherche multi-agents (Opus 4 en chef, sous-agents Sonnet 4) bat un agent unique Opus 4 de 90,2 % sur leur évaluation interne, surtout parce qu'il dépense assez de tokens (l'usage de tokens explique 80 % de la variance sur BrowseComp). En contrepartie : agents ≈ 4× les tokens d'un chat, multi-agents ≈ 15×. Anthropic écarte explicitement les domaines où les agents doivent partager le même contexte ou dépendent beaucoup les uns des autres. Le theorycraft WoW est de ce type.
2. **Le débat Cognition/Anthropic converge vers un patron commun.** [Certain/Probable] Cognition (« Don't Build Multi-Agents ») : partager le contexte complet et les traces ; les actions portent des décisions implicites, des décisions parallèles contradictoires donnent de mauvais résultats. En avril 2026, Cognition déploie des multi-agents « qui marchent » quand les écritures restent sur un seul fil et que les agents additionnels apportent de l'intelligence plutôt que des actions. Consensus : une boucle principale porte l'état ; des sous-agents sans état ont un périmètre étroit. [Probable]
3. **Les échecs multi-agents sont surtout des échecs de conception.** [Certain] MAST (NeurIPS 2025) : 14 modes d'échec en 3 catégories (spécification, désalignement inter-agents, vérification), plus de 1 600 traces, κ = 0,88. Répartition ≈ 44 % / 32 % / 24 %.
4. **Dans Claude Code, chaque primitive a un rôle précis.** [Certain] Skills : connaissance ou workflow à la demande (description chargée en permanence, corps quand pertinent). Sous-agents : contexte isolé qui renvoie un résumé. MCP : services et outils externes. Hooks : automatisation déterministe. Plugins : emballage avec espace de noms. Un sous-agent peut précharger des skills ; un skill peut s'exécuter dans un contexte isolé.
5. **Les skills sont conçus pour des connaissances de domaine volumineuses.** [Certain] Divulgation progressive en trois niveaux (métadonnées, SKILL.md, fichiers liés) ; scripts embarqués pour la fiabilité déterministe. Règles : SKILL.md sous 500 lignes, références à un seul niveau, description précise sur le « quoi » et le « quand ».
6. **Pour les agents experts, les outils de calcul battent le RAG et le fine-tuning sur les chiffres.** [Certain/Probable] Le code apporte le déterminisme. En médecine, déléguer aux calculateurs vérifiables élimine les erreurs de calcul (0 % contre 16,8 % pour un LLM seul). Le fine-tuning est à exclure : les données Forever changent à chaque build de bêta.
7. **L'écosystème Forever fournit déjà presque tout le pipeline de données.** [Certain] wago.tools publie chaque table DB2 de chaque build en CSV ; forever-ref calcule les stats d'objets avec les formules du client ; plusieurs simulateurs open source (dérivés de wowsims/classic) couvrent 23 spécialisations ; l'addon MythicSim exporte la fiche du joueur en JSON. Il manque une couche de provenance et un optimiseur d'équipement fiable.

## Details

### 1. État de l'art des architectures hiérarchiques

| Architecture | Principe | Avantages | Coûts | Modes d'échec | Quand l'utiliser |
|---|---|---|---|---|---|
| Agent unique + outils spécialisés | Une boucle, des outils déterministes | Contexte cohérent, faible latence, source de vérité unique | Le contexte grossit | Pollution de contexte, outils trop nombreux | Tâches interdépendantes, calculs |
| Agent unique + skills | Connaissance chargée à la demande | Spécialisation à coût quasi nul au repos | Déclenchement par descriptions | Mauvais skill si descriptions floues | Domaine large avec sous-domaines : **notre cas** |
| Routeur (workflow) | Classifier puis envoyer vers un chemin | Simple, prévisible | Rigide | Erreurs de routage silencieuses | Catégories nettes et stables |
| Orchestrateur-travailleurs | Un chef décompose, des travailleurs exécutent | Parallélisme | ≈15× tokens, coordination | Travail dupliqué, synthèse incohérente | Recherche large parallélisable |
| Superviseur hiérarchique | Superviseurs de sous-domaines | Modularité | Latence et tokens multipliés | Désalignement, sources divergentes | Rarement justifié pour un utilisateur seul |

- **Pollution de contexte** : argument pour les sous-agents, mais pour les tâches bavardes (logs de simulation, diffs de tables, pages web), pas pour la connaissance.
- **Connaissances dupliquées** : risque majeur d'un « sous-agent Mage » et d'un « sous-agent Itemisation » qui auraient chacun leurs règles. Parade : aucune règle numérique dans les prompts ; toutes vivent dans `forever-core`.
- **Erreurs de routage** : le routage se fait par correspondance avec la description ; descriptions vagues ou qui se chevauchent → mauvais skill.

### 2. Ce que recommande Anthropic, primitive par primitive

- **« Building effective agents »** : distinguer workflows (chaînage, routage, parallélisation, orchestrateur-travailleurs, évaluateur-optimiseur) et agents (boucle autonome), réservés aux problèmes ouverts. [Certain]
- **Subagents** : contexte, prompt système, outils et permissions propres ; utiles quand une tâche annexe inonderait la conversation. Les sous-agents livrés par plugin ignorent `hooks`, `mcpServers` et `permissionMode` : le serveur MCP se déclare au niveau du plugin (`.mcp.json`). [Certain]
- **Agent Skills** : trois niveaux de divulgation, scripts exécutables sans charger le script dans le contexte, démarche qui commence par l'évaluation ; skills en standard ouvert. [Certain]
- **MCP** : noms d'outils chargés au démarrage, schémas différés. « Code execution with MCP » : un flux passe de 150 000 à 2 000 tokens quand l'agent écrit du code contre des API d'outils. Les résultats volumineux restent côté serveur et remontent résumés. [Certain]
- **Écriture d'outils** : consolider plutôt qu'envelopper chaque endpoint ; espaces de noms ; retours lisibles ; `response_format` concis ou détaillé ; pagination et filtrage (plafond de 25 000 tokens par réponse d'outil) ; erreurs actionnables ; amélioration pilotée par évaluations. [Certain]
- **Hooks** : déterministes ; `SessionStart` peut injecter du contexte mais ne bloque pas ; ce sont les seuls vrais garde-fous. [Certain]
- **Plugins** : `.claude-plugin/plugin.json` (seul `name` requis), `skills/`, `agents/`, `hooks/hooks.json`, `.mcp.json` à la racine ; skills préfixés par le nom du plugin. [Certain]
- **Évaluation** : commencer avec 20 à 50 tâches issues d'échecs réels ; correcteurs de code d'abord ; séparer capacité et régression ; pass@k et pass^k ; juge LLM isolé par dimension avec une porte de sortie « Unknown ». [Certain]

**Patron déduit** [Probable] : un agent principal qui porte l'état ; sous-domaines en skills (procédures) ; faits et calculs dans des outils déterministes partagés ; sous-agents pour les tâches isolables et bavardes ; hooks pour les invariants ; plugin pour la distribution.

### 3. Gestion de la connaissance

| Besoin | Meilleur support | Pourquoi |
|---|---|---|
| Valeurs numériques | Données structurées versionnées + fonctions | Exactes, diffables, testables |
| Calculs | Code (analytique + Monte Carlo) | Déterminisme |
| Culture générale | Données structurées quand elles existent + RAG léger sur guides datés | Texte peu numérique |
| Style de réponse | Skills | Pas besoin d'entraînement |
| Fine-tuning | **À éviter** | Données mouvantes, aucune provenance |

- **Source de vérité unique** : `forever-core` contient données par build, mécaniques, classes (données + petits modules), objets, simulateurs, optimiseurs, provenance. Aucun chiffre dans un SKILL.md.
- **Provenance** : chaque valeur porte `{value, build, source, tier, retrieved_at}` avec `client_verified`, `derived`, `community`, `assumed`. Les nombres du client ne prouvent pas les règles serveur.
- **Pipeline de fraîcheur** : API des builds wago (produit `wow_classic_beta`, liste à trier par `created_at`) ; tables via `https://wago.tools/db2/<Table>/csv?build=<build>` (talents dans les tables `Trait*`) ; diff ; régénération ; tests ; changelog.
- **Empêcher les réponses « de mémoire »** : SessionStart injecte le build courant ; le routeur impose de citer build et certitude ; un hook `Stop` signale les nombres sans appel d'outil ; évaluations pièges sur les changements Classic → Forever (Mangle renommé Primal Bite, Improved Holy Strike et Crusade retirés, baguettes sans bonus de sorts, 27 recettes supprimées).
- **Theorycraft existant** : SimulationCraft ne supporte pas Classic ; l'écosystème Forever repose sur wowsims/classic (MIT). Raidbots déconseille les poids de stats et recommande de simuler l'équipement réel (Top Gear). BGannon2 contrôle la parité entre deux implémentations (0,000 % d'écart sur 23 spés). gunba publie un benchmark reproductible (5 000 itérations par résultat).

### 4. Application à WoW Forever

**Calendrier** : bêta du 17 septembre au 21 octobre, lancement le 4 novembre 2026, raids le 9 décembre (Barrow Deeps 10, Hyjal Summit 20, Onyxia 40). Build 1.60.1.70009 (24 septembre).

| Source | Contenu | Usage recommandé |
|---|---|---|
| wago.tools (DB2 CSV) | Toutes les tables du client par build | **Source primaire** |
| alcaras/forever-ref | Objets, sorts, recettes, stats calculées par formules client | Référence du calcul des objets |
| foreverchanges.pro | Objets nouveaux et modifiés, taux de concordance avec Classic | Validation du calcul d'objets |
| Wowhead Forever | Base, guides, gear planner | `community` ; culture générale |
| ElliotWood/Forever (fork wowsims) | Simulateur, règles Forever | Moteur de référence niveau 60 |
| wowsims/forever | Implémentation officielle par spé | À surveiller |
| gunba/wow-forever-sim | Benchmark DPS reproductible | Jeux de référence pour les tests |
| BGannon2/foreversims | 23 spés, Python + Rust/WASM | Modèle de provenance |
| laurencestokes/foreversim | Raciaux Forever depuis le client | Recoupement |
| MythicSim + addon Forever Sim Exporter | Export JSON du personnage | **Import de la fiche réelle** |
| Listes BiS | Objets de valeur par emplacement | Candidats seulement |
| Calculateurs de talents (wowforevertalents.com) | Arbres générés depuis le client | Contrôle croisé |

**Sous-domaines** :
```
wow-forever (skill routeur : provenance, carte des sous-domaines, outils)
├── mechanics
├── classes/ (mage, warlock, priest, warrior, rogue, hunter, druid, paladin, shaman)
├── gear
├── leveling
├── instances
├── pvp
├── professions
├── legacy
└── data-ops
```

**Équipement** : base d'objets générée depuis la DB2 avec les formules du client ; « sans équipement » = stats de base + talents + buffs ; « avec équipement » = liste d'IDs ou import JSON MythicSim/WoWSims ; poids de stats calculés par simulation pour le seul pré-filtrage ; optimisation sous contraintes (unique-équipé, 2M ou 1M+MG, plafond de toucher, sets, armure) : pré-filtre analytique puis Monte Carlo sur les K meilleurs ; sortie avec delta ± IC, stat limitante, source et certitude.

**9 sous-agents de classe ou modules à la demande ? Des modules.** Une question transverse (classe + équipement + instance + mécaniques) répartie entre sous-agents impose de retransmettre le contexte et de payer le multiplicateur de tokens. Un `sim-runner` générique paramétré par classe suffit pour les lots massifs.

### 5. Options comparées

| Critère | A. Méga-skill | **B. Plugin hybride (recommandé)** | C. Multi-agent hiérarchique |
|---|---|---|---|
| Source de vérité | Unique, couplée au skill | **Unique, découplée** | Copies divergentes |
| Coût en tokens | Lourd une fois chargé | **Faible au repos** | ≈15× |
| Questions transverses | Bonnes | **Bonnes** | Mauvaises |
| Passage à l'échelle | Mauvais | **Bon** | Fragile |
| Réutilisation hors Claude Code | Faible | **Bonne via MCP** | Moyenne |
| Évaluabilité | Moyenne | **Haute** | Faible |

**Arborescence type (option B)** :
```
plugins/wow-forever/
├── .claude-plugin/plugin.json
├── .mcp.json
├── skills/ (wow-forever, forever-mechanics, forever-gear, forever-leveling, forever-instances,
│            forever-pvp, forever-professions, forever-legacy, forever-class-*, forever-data-ops)
├── agents/ (forever-data-updater, forever-sim-runner, forever-web-researcher, forever-eval-judge)
├── hooks/hooks.json
└── core/ (forever_core/{data,mechanics,classes,items,sim,optimize,provenance}, cli.py, mcp_server.py, tests/)
```

**Outils MCP** : `forever_lookup`, `forever_character_import`, `forever_calc`, `forever_simulate`, `forever_gear_optimize`, `forever_talent_optimize`, `forever_leveling_plan`, `forever_build_status`.

## Recommendations (plan par étapes)

1. Extraire `forever-core` du skill Mage ; schéma de provenance ; les 30 tests passent à l'identique.
2. Pipeline de données (détection des builds, téléchargement, diff, régénération, tests, changelog) ; hook SessionStart de fraîcheur.
3. Équipement : générateur par formules client validé contre foreverchanges.pro ; import MythicSim ; optimiseur.
4. Culture générale : leveling, instances, métiers, Legacy.
5. Les 8 autres classes, avec parité contre les simulateurs existants.
6. Après le lancement : version de production, données de raid.

**Évaluation** : régression (tests de référence, parité, calcul d'objets, graines fixes) et capacité (20 à 50 tâches réelles, pièges Classic ≠ Forever), tests d'aiguillage des skills.

**Pièges** : chiffres dans les skills ; listes BiS ou poids de stats comme vérité ; nombres du client pris pour des règles serveur ; outils MCP un-pour-un ; descriptions de skills qui se chevauchent ; `additionalContext` non testé sur la surface utilisée.

## Caveats

- Plusieurs faits Forever viennent de sites communautaires récents ; divergences signalées (plafond de niveau en bêta, noms des arbres Legacy).
- Les chiffres d'Anthropic viennent d'évaluations internes sur d'autres tâches : leur transposition est une inférence.
- Aucun benchmark ne compare directement skills et sous-agents pour un agent expert : la recommandation repose sur la convergence des guides.

## Sources principales

- https://www.anthropic.com/engineering/multi-agent-research-system
- https://www.anthropic.com/research/building-effective-agents
- https://cognition.com/blog/dont-build-multi-agents
- https://arxiv.org/pdf/2606.08162
- https://code.claude.com/docs/en/features-overview
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/plugins-reference
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://www.anthropic.com/engineering/writing-tools-for-agents
- https://www.anthropic.com/engineering/code-execution-with-mcp
- https://anthropic.com/engineering/demystifying-evals-for-ai-agents
- https://arxiv.org/pdf/2503.17550
- https://medium.com/raidbots/beware-of-stat-weights-240769a5323e
- https://github.com/alcaras/forever-ref
- https://foreverchanges.pro/items
- https://github.com/BGannon2/foreversims
- https://github.com/gunba/wow-forever-sim
- https://github.com/ProfetGit/forever-sim
- https://github.com/laurencestokes/foreversim
- https://mythicsim.com/wow-forever/sim
- https://www.curseforge.com/wow/addons/mythicsim-forever-sim-exporter
- https://wowforevertalents.com/about/
- https://www.icy-veins.com/wow-forever/legacy-system
