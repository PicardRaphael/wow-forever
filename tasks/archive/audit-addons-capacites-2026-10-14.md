# Audit : ce que tes addons font déjà, et ce que l'agent doit en faire (2026-10-14)

Écrit depuis la conversation claude.ai de Raphaël, après sa remarque : « tu n'as pas pris en compte mes addons ».
Constat juste : plusieurs tranches (T10a, « Est-ce une amélioration ? », une partie de RX1, la fenêtre du chat)
construisaient des choses que ses addons font déjà, souvent mieux et avec une vraie interface. Ce fichier sert de base
à une décision de méthode et à la révision de la feuille de route. À intégrer par une session Claude Code (décision
numérotée, ROADMAP, DATA_SOURCES), puis à archiver dans `tasks/archive/`.

Source : les fichiers `.toc` et quelques fichiers de données des addons installés dans
`C:\Program Files (x86)\World of Warcraft\_classic_beta_\Interface\AddOns` (lecture seule, 2026-10-14). À compléter
par une lecture plus fine de chaque addon pendant l'intégration.

## 1. Carte des capacités déjà présentes en jeu

| Besoin du joueur | Ce qui le fait déjà | Remarque |
|---|---|---|
| Liste BiS par classe, spécialisation, phase, avec lieu de butin | Forever Companion (BiS, étoiles d'or et d'argent dans les infobulles), Naowh Forever BiS (liste, « Naowh Score », quêtes à faire), FojjiCore BiS Manager (plan par emplacement, suggestions, pré-raid), AtlasLoot + module BiS ToolTip | Données de la communauté, mises à jour très souvent (Forever Companion : données v88 du 2026-10-12) |
| Poids des statistiques et « est-ce une amélioration ? » | Forever Companion (échelles par classe et spécialisation, score dans chaque infobulle, flèche verte sur les récompenses de quête et les jets de butin, échelles **importables et exportables en texte**), Naowh BiS (poids, score), GearQuest Forever (poids et calculs pour le leveling), Forever Guide (GearCalc, GearAdvisor, GearExplain) | L'agent ne doit pas refaire l'affichage : il peut **fournir de meilleurs poids** (calculés) à ces addons |
| Équipement de leveling niveau par niveau, avec la quête ou le monstre qui le donne | GearQuest Forever (« clique un emplacement, choisis une chasse, suis-la dans le journal ») | C'est le « BiS par niveau » de T10a, déjà fait en jeu |
| Talents : builds et ordre de prise, niveau par niveau | Naowh Training Planner (builds, « level by level », import/export), Talents Forever, Forever Companion (onglet « BiS Talents ») | L'agent fournit le build **calculé** (Mage) et l'exporte |
| Sorts à apprendre chez le maître et leur prix | Naowh Training Planner, Forever Companion (liste à côté du grimoire), FojjiCore SpellRanks | |
| Rotations | Forever Companion (onglet Rotation) | Utile pour les classes sans moteur |
| Donjons : boss, butin, quêtes et chaînes de prérequis | Naowh Dungeon Journal, Forever Guide, ForeverDungeonJournal, FojjiCore DungeonJournal, AtlasLoot | Déjà lus par DJ1 (sauf usage complet de Forever Guide GearCalc) |
| Quêtes et rares par zone, chaînes, sac de couchage, livres | Naowh Discovery (« Quest List », ex-Completo), Questie, Forever Guide (chaînes) | Déjà lus par T04d/RX1 |
| Métiers : recettes, seuils, chance de montée, plan de montée, liste de courses, profit | SkillUp Forever (plan, itinéraire, courses), Forever Companion (profit, ressources sur la carte), Naowh Professions, Forever Guide | MT1 doit s'appuyer dessus |
| Ressources de récolte sur la carte | Forever Companion (herbes et minerais), Naowh Glimmer | |
| Trajets et navigation | Shortest Path Forever (suit RestedXP), Naowh Journeys | Déjà lus par RX1 |
| Guide pas à pas | RestedXP (guides gratuits et payants), Factoruide (externe) | RX1 livre nos routes dans RestedXP |
| Legacy (défis par zone) | Legacy Forever | LG1 doit s'appuyer dessus |
| PvP : ce que fait la cible | Naowh PvP | PV2 doit en tenir compte |
| Groupe : score, équipement, talents des membres | Naowh Group Inspect | |
| Interface, barres, cadres | EllesmereUI (« mon UI, c'est mon UI » : l'agent n'y touche jamais sans demande) | |

## 2. Ce que l'agent apporte que les addons n'ont pas

1. **Une seule conversation** qui réunit tous ces addons : il sait lequel répond à quoi, les recoupe, signale leurs
   désaccords (comme pour les donjons et le sac de couchage) et répond en une phrase claire.
2. **Des calculs exacts tirés du client et de mes mesures** : XP réelle des quêtes et des monstres, bonus d'XP, builds
   et poids **calculés** (Mage aujourd'hui, les autres classes ensuite), au lieu de listes de la communauté.
3. **La personnalisation** : mon personnage réel (niveau, talents, équipement, métiers, Legacy), pas un profil type.
4. **Agir dans les addons** plutôt que les refaire : pousser mes builds dans Naowh et Talents Forever, mes poids
   calculés dans les échelles de Forever Companion et de Naowh, ma liste BiS dans Naowh, mes routes dans RestedXP.
5. **Rester à jour seul** : données du jeu, correctifs du serveur, versions des addons.

## 3. Règle de méthode proposée

- **Avant de construire une fonction, regarder si un addon installé la fait déjà** (prolonge la décision 264 sur
  l'étude de l'existant, qui ne regardait que le web et les dépôts). Si oui : l'agent s'en sert (lecture locale,
  agrégats seulement, décision 133) et l'alimente (exports), il ne refait ni son interface ni ses données.
- **Construire seulement** ce qu'aucun addon ne fait, ou ce que l'agent fait nettement mieux (calcul exact, route
  personnalisée, réponse unifiée), et le dire dans le plan.
- **Accepter une fonction en jeu par Raphaël** avant de la déclarer finie.

## 4. Conséquences sur la feuille de route (à trancher à l'intégration)

- **T10a** : au lieu d'un affichage BiS et d'une comparaison d'objets à nous, (a) calculer les poids (Mage d'abord)
  et les **exporter** vers Forever Companion (format texte de ses échelles) et Naowh (`NFSW1:`), (b) produire la liste
  BiS personnelle en partant des listes des addons, recoupées et classées avec nos poids, et l'**exporter** vers Naowh
  (`!NBIS1!`), (c) dans le chat, répondre « est-ce une amélioration ? » en lisant le score de ces addons et nos poids.
- **« BiS par niveau »** : s'appuyer sur GearQuest Forever plutôt que le recalculer.
- **MT1 (métiers)** : s'appuyer sur SkillUp Forever (plan et itinéraire de montée) et Forever Companion.
- **Talents** : plan complet dès le niveau 1, exporté vers Naowh Training Planner et Talents Forever (déjà noté dans
  `tasks/idees-du-chat-2026-10-14-ux-routes.md`).
- **Fenêtre du chat** : rester une conversation claire ; laisser à chaque addon son propre affichage (BiS, talents,
  métiers) et y renvoyer d'un clic.
- **Inventaire** : mettre à jour `tasks/inventaire-addons.md` et `DATA_SOURCES.md` avec ces capacités (Forever
  Companion en particulier n'y figure pas comme source de BiS, d'échelles et de rotations ; GearQuest Forever non plus
  comme source de BiS de leveling).
