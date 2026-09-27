# forever-core : plan d'un système expert WoW Forever sur Claude Code, portable vers ChatGPT, qui sait toujours si ses données sont à jour

> Rapport de recherche du 27/09/2026 (claude.ai), recopié pour Claude Code. Sources principales en fin de fichier.
> Légende : **[Certain]** source primaire ; **[Probable]** sources concordantes ou inférence forte ; **[Supposé]** jugement non vérifié.

**Réponse courte :** construisez un cœur déterministe unique, `forever-core`, en Python. Il expose des outils MCP et produit un manifeste de fraîcheur par build du jeu. Au-dessus, un plugin Claude Code mince (skills routeurs, hooks SessionStart, sous-agents isolés). **Aucune donnée de jeu ni aucun calcul dans les skills.** Le vrai garde-fou de l'exhaustivité est un **registre de mécaniques versionné, lié aux tests**, alimenté par la comparaison continue avec le fork wowsims Forever et avec des journaux de combat bruts.

## TL;DR

- **Architecture recommandée : « cœur MCP + plugin mince ».** Le calcul, les données versionnées et la fraîcheur vivent dans `forever-core` (CLI + serveur MCP + tests). Claude Code orchestre. Le même serveur MCP est réutilisable par ChatGPT (Apps SDK, bâti sur MCP) et par un site. **À éviter :** le « skill-monolithe » où le modèle calcule ou lit des tableaux dans le Markdown.
- **Fraîcheur : manifeste + sonde légère.** La sonde lit le dernier build de `wow_classic_beta` sur wago.tools au démarrage (hook SessionStart) et dans une tâche planifiée. Chaque réponse d'outil porte un bloc `provenance` (build, date, certitude).
- **Exhaustivité : un registre de mécaniques (≈ 100 entrées).** Chaque entrée porte un statut, une source et des tests, vérifiés en CI comme SimulationCraft et wowsims le font avec leurs fichiers « golden ». Validation contre des journaux de combat bruts (format 22).

## Décisions tranchées

| Sujet | Option recommandée | Option à éviter | Raison principale |
|---|---|---|---|
| Où vit la logique | `forever-core` exposé via CLI + MCP | Logique dans SKILL.md | Les tests ne visent que du code |
| Moteur de simulation | Garder le Monte Carlo du leveling ; comparer le raid au fork wowsims Forever | Porter wowsims ou partir de SimulationCraft | SimC ne modélise pas Classic |
| Fraîcheur | Manifeste par build + sonde + provenance dans chaque réponse | Dates en dur dans les skills | Doc Anthropic : pas d'info datée dans les skills |
| Déclenchement des skills | 1 routeur + skills de domaine courts, descriptions à la 3e personne | Un skill géant | Descriptions vagues = pas de déclenchement |
| Effets de bord | Commandes avec `disable-model-invocation: true` | Laisser le modèle décider d'un fetch | Recommandation officielle |
| ChatGPT | Plus tard, via le même serveur MCP | Custom GPT + Actions | Les Apps OpenAI sont bâties sur MCP |
| Validation | Journaux bruts + tests en jeu + parité wowsims | Guides web | Guides Forever souvent SEO |

## 1. Pratiques des praticiens

### 1.1 Claude Code

- **Chargement progressif** : seuls `name` (≤ 64 caractères) et `description` (≤ 1 024) sont préchargés. Description à la **troisième personne**. Corps sous 500 lignes, références à un niveau, table des matières au-delà de 100 lignes. [Certain]
- **Évaluer avant d'écrire** la documentation ; tester sur chaque modèle visé. [Certain]
- **Pas de contenu daté dans les skills.** [Certain]
- **Commandes et sous-agents** : `disable-model-invocation: true` pour les workflows à effets de bord ; sous-agents pour les tâches qui lisent beaucoup. [Certain]
- **Hooks** : SessionStart est rejoué au `resume` ; le texte injecté par UserPromptSubmit/PostToolUse est rejoué tel quel à la reprise (donc périmé) ; un hook qui expire ne bloque pas ; « exit codes or JSON, never both ». [Certain]
- **Statusline** : script qui reçoit l'état en JSON et affiche une ligne. **Piège constaté sous Windows : une statusline Python lancée au démarrage ouvre l'agent view — ne pas en utiliser.**
- **Routines** : sessions sauvegardées dans le cloud, en aperçu de recherche ; intervalle minimal d'une heure ; seuls les skills commités sont disponibles. [Certain]
- **Outils** : peu d'outils à fort levier, espaces de noms, retours lisibles, pagination, erreurs actionnables, amélioration par évaluations. [Certain]
- **Communauté** [Probable] : la description est un déclencheur (phrases littérales) ; une section « Gotchas » par skill ; trois exemples valent mieux que vingt règles ; un skill = un travail.
- **Tester un skill** : 20 à 40 requêtes (≈ 60 % doivent déclencher, ≈ 40 % quasi-homonymes qui ne doivent pas) ; rejouer en CI.

### 1.2 OpenAI / ChatGPT

- Apps SDK bâti sur MCP (standard MCP Apps, UI en iframe) ; tests en Developer Mode. [Certain]
- Champ `instructions` du serveur MCP lu par ChatGPT et Codex : l'essentiel dans les 512 premiers caractères ; un outil par action distincte. [Certain]
- Plugins OpenAI : skills + connecteurs MCP ; skills Codex au standard Agent Skills (`.agents/skills`). [Certain]
- Agents SDK : handoffs, garde-fous (attention : entrée sur le premier agent, sortie sur le dernier), tracing par défaut. [Certain]

### 1.3 Portabilité

| Surface | Consommation de `forever-core` | Limites |
|---|---|---|
| Claude Code | MCP local + CLI + skills + hooks | — |
| Claude.ai / Desktop | MCP distant + skills | Pas de hooks : fraîcheur via la provenance |
| ChatGPT / Codex | Même MCP distant | Publication soumise à revue |
| Site web | API HTTP + JSON pré-rendus | Pas de LLM par défaut |

**Conséquence** : la fraîcheur et la provenance doivent être dans les réponses d'outils.

### 1.4 Fraîcheur

- Sonde de build existante dans l'écosystème (`/api/builds/<product>/latest`) ; suggestion d'alerte si aucun build depuis N semaines (« silent »). Nom du produit de lancement supposé.
- Le fork ElliotWood ouvre des PR de données automatiques ; son amont `wowsims/forever` a été injoignable : **épingler les commits**.
- Patron : manifeste → sonde avec cache → statut `fresh`/`stale`/`unknown`/`silent` → une ligne affichée → mise à jour sur commande.

## 2. Méthode des theorycrafters

### 2.1 Outils de référence

- **SimulationCraft** : rotations en APL ; rencontres par `fight_style` et `raid_events` ; variation de durée ±20 % ; `target_error` ; reproductibilité à tester (issue #9818 : `deterministic=1` et `seed` divergent) ; événements à horaire fixe et durée variable mal combinés (issue #4447). Aucun support Classic.
- **wowsims** : moteur Go, APL, table d'attaque, auras, procs ; tests « golden » (`.results`, `make test` / `make update-tests`) ; le fork exige des résultats identiques et ne re-bénit qu'avec explication ; un `Ruleset` par défaut Classic ; liste générée des effets non modélisés ; une ligne par règle Forever avec sa source ; 58 talents sur 469 extrapolés.
- **Validation par journaux** : exemple de la rage par coup blanc mesurée sur des journaux publics (63 paires, 3,46 retenu contre 3,5). Modèle : mesure brute → issue documentée → règle → golden re-béni avec explication.
- **Warcraft Logs** : API v2 GraphQL ; aucun support Forever documenté. Le parseur Chronicle lit déjà le format 22 de Forever.
- **Guides de classe** : priorités de stats et seuils ; pour Forever, sites souvent SEO : pistes, pas vérité.

### 2.2 Spécificités Classic et Forever

- **Table d'attaque (coups blancs)** : raté, esquive, parade, blocage, érafle, critique, normal ; boss +3 avec 300 de compétence : 40 % d'érafles à −35 %.
- **Sorts** : raté lié au niveau (plancher 1 %) puis résistance (paliers 0/25/50/75/100 %, moyenne ≈ 0,75 × R / (5 × niveau), plafond 75 %) ; sorts binaires entièrement résistés ou non.
- **Résistance liée au niveau** : environ 8 par niveau d'écart (« believed ») — à vérifier.
- **Règle des 5 secondes** : régénération par l'Esprit coupée 5 s après une dépense ; ticks de 2 s ; MP5 non affecté.
- **Regroupement des actions** : 400 ms historiquement, 10 ms depuis 1.13.7 ; **valeur Forever inconnue**, à mesurer.
- **Forever [Certain]** : sortie le 4 novembre ; bêta jusqu'au 21 octobre ; raids le 9 décembre ; toucher et critique unifiés ; bonus de soins → un tiers en dégâts ; compétence d'arme réduite par objet ; stat « réduit esquive/parade » ; pas de résilience ; 4e talent doré à 16 points ; Kings, Divine Spirit et Improved Mark of the Wild passifs ; potions de soins à First Aid ; Camping (buff d'une heure) ; Well Fed +5 % d'XP.
- **Forever [Probable]** : 4 871 nouveaux objets ; **flacons conditionnés par zone** ; bonus alchimistes ; Gourmand (nourriture 33 % plus longue). → Consommables conditionnés par zone ET par profession.
- **Mage Forever [Probable]** : Arcane Blast (+10 %/charge, +175 % de coût, 4 charges) ; Hot Streak (critiques non périodiques) ; Frostfire Bolt ; Ice Lance ; Fingers of Frost ; Missile Barrage ; Scorch et Winter's Chill deviennent personnels ; bug bêta des baguettes à ne pas modéliser.

### 2.3 Registre de mécaniques (liste de contrôle)

Format : `id`, `catégorie`, `description`, `applicable_forever`, `statut` (absent / modélisé / testé / validé-journal / validé-jeu), `source`, `certitude`, `tolérance`, `tests`. La CI échoue si une entrée modélisée n'a pas de test.

- **A. Résolution des attaques** : table d'attaque, deux jets pour les sorts, raté selon l'écart de niveau, toucher et critique unifiés, érafles, compétence d'arme, stat esquive/parade, position, double arme, écrasements, résistances partielles, sorts binaires, résistance liée au niveau, pénétration, écoles et immunités, DoT qui critiquent, Ignite, procs et critiques périodiques.
- **B. Temps et ressources** : GCD, hâte, file d'attente, latence, regroupement serveur, recul d'incantation, règle des 5 s, MP5, mana et Intellect, Évocation et potions, coûts en % du mana de base, Clearcasting, recharges, procs (PPM, ICD), durée et cumul des buffs.
- **C. Physique** : temps de vol des projectiles, portées, marge de mêlée, vitesse du joueur, vitesse des monstres et gel, temps en mouvement, rayons et plafonds de cibles, ligne de vue.
- **D. Buffs et environnement** : buffs de raid, non-cumuls, buffs mondiaux, débuffs de cible, campement et Legacy, effets de biome, bonus d'XP.
- **E. Consommables** : flacons (zone), élixirs, nourriture, potions, huiles, pierres, parchemins, ingénierie, runes, bonus alchimistes, protections, coût en or.
- **F. Équipement** : stats par build, enchantements, sets, effets déclenchés, bijoux, armes de lanceur, bonus de soins → dégâts, effets non modélisés.
- **G. Personnage** : raciaux, stats de base, talents, sorts par rang et coefficients, Legacy, bonus de métiers.
- **H. Rencontres** : niveau de la cible, armure et résistances, nombre de cibles, exécution, durée, mouvement, interruptions, taille de raid, menace, mort.
- **I. Rotation et optimisation** : APL, optimisation des APL, poids de stats avec erreur standard, simulation de l'ensemble réel, optimiseur de talents, leveling.
- **J. Méta** : build et hotfixes, graine, erreur statistique, parité wowsims, validation par journaux, hypothèses datées.

### 2.4 Protocole de validation

1. Tests unitaires par mécanique avec valeurs sourcées.
2. Fichiers golden par scénario, graine fixe ; re-bénir seulement avec explication.
3. Parité avec le fork wowsims Forever (en ordre de classement tant que la bêta bouge).
4. Journaux bruts format 22 : parseur local, distributions (critiques, résistances, intervalles) ; chaque mesure devient une entrée du registre avec sa taille d'échantillon.
5. Tests en jeu ciblés pour les entrées « supposé ».

## 3. Plan de l'« app parfaite »

### 3.1 Options

| | A. Plugin-monolithe | **B. Cœur MCP + plugin mince (recommandé)** | C. Service web d'abord |
|---|---|---|---|
| Portabilité | Claude Code seulement | Claude Code, Claude.ai, ChatGPT, site | Maximale mais hébergement obligatoire |
| Testabilité | Faible | Forte | Forte |
| Verdict | À éviter | **Recommandée** | Plus tard |

### 3.2 Architecture B

- `forever-core/forever/` : `data/<build>/`, `data/manifest.json`, `mechanics/registry.yaml`, `engine/`, `sim/`, `optim/`, `charts/`, `pipeline/`, `provenance.py`, `mcp_server.py` ; `tests/` (unit, golden, parité, journaux) ; CI.
- Plugin : skills (routeur, mage, raid, gear, data), sous-agents (data-updater, sim-runner, web-researcher, evaluator), hook SessionStart, commandes `/forever`, `/forever update`, `/forever sim`, `/forever raid-prep`.
- Outils MCP : `forever_status`, `forever_lookup`, `forever_explain_mechanic`, `forever_sim_run`, `forever_optimize_talents`, `forever_optimize_gear`, `forever_consumables_plan`, `forever_diff_builds`, `forever_player_profile_get/set`. Chaque réponse : `result`, `assumptions`, `provenance`, `certainty`.

### 3.3 Fraîcheur

1. Manifeste : produit, build, hotfixes, empreintes, date, version du registre.
2. Sonde `forever status` (< 1 s, cache de 6 h, expiration réseau de 2 s) : `fresh`, `stale`, `unknown`, `silent` (aucun build depuis plus de 14 jours) ; vérification des empreintes.
3. Moments : SessionStart, champ `freshness` de chaque outil, tâche planifiée (GitHub Actions préférable aux Routines en aperçu).
4. Si `stale` : répondre quand même en étiquetant, baisser la certitude des entités touchées par le diff, proposer la mise à jour ; jamais de mise à jour silencieuse.
5. Cache des résultats de simulation par (build, empreinte, registre, profil, scénario, graine).

### 3.4 Mode d'emploi

- Commandes : `/forever`, `/forever update`, `/forever sim`, `/forever raid-prep`, `/forever respec`, et le langage naturel.
- Automatique : fraîcheur au démarrage, profil joueur depuis le vault, provenance, veille des builds.
- Sessions types : question de talent (verdict + Δ avec IC + hypothèses + certitude) ; optimisation d'équipement (ensemble réel) ; nouvelle version du jeu (diff, goldens expliqués) ; préparation de raid (consommables à condition de zone, non-cumuls, recharges partagées).

### 3.5 Plan par étapes

1. Fondations : cœur extrait, manifeste, status, provenance, registre initialisé.
2. Garde-fous : tests, goldens, CI, veille des builds.
3. Outils MCP et plugin, jeux d'évaluation.
4. Avant le 4 novembre : parseur de journaux format 22, premières validations, parité Mage.
5. Avant le 9 décembre : consommables et raid.
6. Ensuite : MCP distant pour Claude.ai et ChatGPT, site statique.

### 3.6 Tokens

Skills courts ; aucune donnée dans les skills ; résumés par défaut ; sous-agents pour les lots ; graphiques en fichiers ; modèles économiques pour les tâches mécaniques ; cache des résultats.

### 3.7 Pièges

Laisser le modèle calculer ; chiffres dans les skills ; hooks traités comme des barrières ; contexte injecté hors SessionStart ; dépendre d'un amont qui disparaît ; modéliser des bugs de bêta ; guides SEO comme sources ; poids de stats sans erreur standard ; événements à horaire fixe avec durée variable ; batching supposé à 400 ms ; non-cumuls oubliés.

## Caveats

- Tout ce qui concerne Forever reste de la bêta ; valeurs précises lues par des tiers dans le client.
- Les preuves de validation du fork wowsims viennent de descriptions de PR ; échantillons de journaux petits.
- Surfaces en évolution rapide (Routines, Warcraft Logs, emplacements des skills Codex).
- Valeurs inconnues pour Forever : regroupement des actions, résistance liée au niveau, résistances partielles des DoT.

## Sources principales

- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- https://code.claude.com/docs/en/best-practices
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/statusline
- https://www.anthropic.com/engineering/writing-tools-for-agents
- https://anthropic.com/news/claude-code-plugins
- https://help.openai.com/en/articles/12515353-build-with-the-apps-sdk
- https://developers.openai.com/apps-sdk/mcp-apps-in-chatgpt
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/codex/skills
- https://openai.github.io/openai-agents-python/
- https://github.com/andersonjohnf/forever_sim/issues/11
- https://github.com/ElliotWood/Forever
- https://github.com/ElliotWood/Forever/pull/463
- https://github.com/ElliotWood/Forever/issues/252
- https://github.com/simulationcraft/simc/wiki/StatisticalBehaviour
- https://github.com/simulationcraft/simc/issues/4447
- https://github.com/simulationcraft/simc/issues/9818
- https://pkg.go.dev/github.com/wowsims/classic/sim/core
- https://github.com/Emyrk/chronicle/pull/694
- https://articles.warcraftlogs.com/help/api-documentation
- https://vanilla-wow-archive.fandom.com/wiki/Resist
- https://wowpedia.fandom.com/wiki/Five_second_rule
- https://outputlag.com/news/world-of-warcraft-forever-unifies-hit-and-crit-stats-and-gives-healing-gear-bonus-damage/
- https://wow-guides.com/forever/items
- https://classicwowforever.com/talents/mage/
- https://mythicsim.com/wow-forever/mage
