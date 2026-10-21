# Plan « Sources d'abord » (décision 288) — changement de cap du 2026-10-21

Demande de l'utilisateur du 2026-10-21, prioritaire sur la suite du bloc 6b de CJ1. Plan écrit pour validation :
**rien n'est construit avant son accord**.

> Statut : **proposé, en attente de validation** (avis de l'advisor en fin de document).

## 0. Constat et règle
- Notre moteur maison casse à chaque refonte de classe : 229 tests rouges pour 1.60.1.70450 (8 vrais défauts, le
  reste figé sur l'ancien Mage), 119 pour 70291 ; une constante de version figée de plus à chaque refonte ;
  88 fichiers de tests lisent la version installée et restent exposés au prochain patch
  (`docs/research/audit-cap-288-2026-10-21.md`). Ce qui est lu dans le client et dans les addons s'adapte seul.
- **Décision 288** (consignée, et dans `CLAUDE.md`) : avant tout chantier, « qui maintient déjà ça mieux que nous ? » et
  « que se passe-t-il au prochain patch ? » ; si tout casse, on ne le construit pas : on lit et on alimente ce qui
  existe ; notre calcul ne sert qu'en recoupement et pour combler les trous ; une nouvelle version donne un rapport des
  valeurs qui changent, à valider, pas des tests rouges.

## 1. Études de l'existant (décision 264 ; lecture seule, sources citées et datées)
| Étude | Fichier | Constat principal |
| --- | --- | --- |
| Carte de notre code, ce qui casse | `docs/research/audit-cap-288-2026-10-21.md` | tout le calcul de combat est propre au Mage ; 11 branches du moteur suivent des marqueurs tirés du texte anglais du client, qui gardent l'ancien sens **sans rien dire** quand le texte change ; la veille se met en attente à chaque version qui touche le Mage et ne sait pas rejouer quand un talent ou un sort est ajouté |
| Addons installés | `docs/research/sources-addons-2026-10-21.md` | poids, BiS, builds, rotations (Forever Companion, 28 spécialisations, niveau 30 et « Leveling 1-60 », en prose), builds populaires (Talents Forever, encore au build 70425), BiS (Naowh, Companion, plus récent), métiers (SkillUp, généré sur 70450), quêtes de classe (Forever Guide) ; **défaut trouvé** : nous lisons `ForeverGuide/GearData.lua` sans `ItemBuild70425.lua` que l'addon applique (291 objets modifiés, 20 retirés) ; trous pour toutes les classes : temps par monstre, DPS chiffré sous 60, poids par niveau, ordre de prise des talents, parcours au-delà du niveau 22 |
| Simulateur de la communauté | `docs/research/simulateur-communaute-2026-10-21.md` | `ElliotWood/Forever` n'existe plus (404) ; référence : **`wowsims/forever`** (MIT, plusieurs mainteneurs, commit du 2026-10-21), suivi par MythicSim ; données **plus à jour que les nôtres** (70450 avec correctif du serveur pour le Mage) ; 12 spécialisations simulées (« Alpha »), 4 soigneurs en planificateur, 2 tanks non publiés ; **joueur fixé au niveau 60** (ni leveling, ni temps par monstre, ni PvP) ; **aucun binaire à jour** : compilation locale (Go 1.25, `protoc`) |
| Méthodes de routes | `docs/research/routes-methodes-2026-10-21.md` | Polestar (paquets de zone, recuit, robustesse), Factoruide (évaluation incrémentale, ruine et recréation), outils écrits à la main (RestedXP, Zygor, Leveldon, Guidelime…) ; méthodes : orienteering avec fenêtres et précédences, recherche locale, acceptation tardive, ILS, LNS, GRASP ; écartés : génétique, fourmis, apprentissage par renforcement, MIP exact |
| Base locale, cache, sorties compactes | `docs/research/base-locale-2026-10-21.md` | caches actuels de 194 Mo (quêtes) et 14 Mo (donjons) sans arrêt anticipé ; base dans `<cache>/kb/` à deux étages d'empreintes (sortie par source puis fusion SQLite) ; tables `STRICT` par type, provenance par champ, FTS5 ; reconstruction plutôt que migrations ; sorties sous 10 000 jetons |

## 2. Les deux questions, domaine par domaine
| Domaine | Qui le maintient mieux que nous ? | Au prochain patch | Rôle de notre code |
| --- | --- | --- | --- |
| DPS et poids au niveau 60, spécialisations de dégâts | `wowsims/forever` (mis à jour en heures ou en jours après un patch) | ils le réparent ; nous détectons s'ils sont en retard | lancer le simulateur, lire, recouper (moteur du Mage) |
| Soigneurs, Druide ours, Guerrier Protection au 60 | personne aujourd'hui | — | builds et poids des addons, marqués « non calculé » |
| Builds de talents (contexte, niveau) | Talents Forever (builds populaires), Forever Companion, Naowh | leurs auteurs les mettent à jour ; nous détectons un talent changé dans le client | lire, puis **vérifier** par le simulateur au 60, par notre moteur pour le Mage ; ordre de prise : nous (trou) |
| Rotations | Forever Companion (prose, niveau 30), simulateur au 60 | idem | lire ; jamais de rotation écrite à la main pour une autre classe |
| Poids sous le niveau 60, temps par monstre, XP par heure | **personne** | notre moteur du Mage casse | Mage : notre moteur, en recoupement des journaux ; autres classes : mesures de tes journaux (`kill_time.py`) ou réponse « non calculé » ; jamais de nouveau moteur de classe avant la sortie (décision 252 maintenue) |
| Listes BiS | Forever Companion (20/10), Naowh (11/10), GearQuest, Forever Guide | leurs auteurs | lire, fusionner, classer par les poids de la meilleure source à jour |
| Parcours de leveling | RestedXP (gratuit jusqu'au niveau 22 environ), Polestar (1-60) | leurs auteurs | personnaliser, insérer, livrer ; l'optimiseur comble les trous |
| Réputations | Forever Guide (factions), Naowh (paliers et récompenses) ; aucun gain chiffré | — | lire ; route de réputation 4e réduite à ce qui est lisible, le reste `suppose` |
| Métiers | SkillUp Forever (généré sur 70450) | son auteur | lire (lecteur à écrire), livrer |
| Données du jeu (sorts, talents, quêtes, objets, PNJ) | le client (tables décodées), Questie | s'adapte seul | décoder, ranger dans la base locale |

## 3. Architecture retenue
### 3.1 Registre des sources et fraîcheur (cœur du changement)
- Un **registre des sources** par domaine (`forever/sources/`) : chaque source déclare ce qu'elle fournit, pour quelles
  classes et spécialisations, son **build du jeu** (lu dans ses fichiers : version de l'addon et date, champ de build
  des données de Talents Forever, `spell_store_inputs.json` du simulateur, build de SkillUp…) et un ordre de préférence
  par domaine.
- **Détection d'une source périmée, par sort et par talent** : nos tables décodées du client (qui suivent chaque
  version) sont comparées aux données de la source (identifiants de sorts et de talents, rangs, points de base,
  coefficients quand la source les porte). Un écart sur une entrée que la réponse utilise → la source est « en retard
  pour cette classe » ; la réponse dit **« calcul en cours de mise à jour »**, nomme la source écartée et prend la
  meilleure source encore à jour ; s'il n'en reste aucune, la réponse est celle de la meilleure source avec la mention
  « source antérieure au patch », **jamais une panne**.
- La même détection remplace, pour notre moteur du Mage, les marqueurs muets : un talent dont le texte du client a
  changé sans marqueur connu met le moteur « en retard » au lieu de garder l'ancien sens sans le dire.

### 3.2 Simulateur de la communauté (SIM1 avancée, réduite au niveau 60)
- `wowsims/forever` compilé en local à un commit épinglé (`<cache>/third_party/wowsims-forever`), lancé en sous-
  processus (`wowsimcli`), provenance : commit, builds par groupe de classes, certitude `suppose` (source externe).
- Usages : DPS de raid et de donjon au 60 pour les 12 spécialisations simulées, poids des statistiques au 60,
  « Est-ce une amélioration ? » au 60, lots de builds de talents (écrits chez nous en appelant `wowsimcli`).
- **Demande d'accord** : nouvelle dépendance (Go 1.25, `protoc`, hors de `uv`), accès réseau (clone et mise à jour du
  dépôt), compilation. Sans accord : SIM1 reste hors du plan et le registre des sources ne contient que les addons et
  notre moteur.

### 3.3 Vérification des builds et rapport des écarts
- Pour chaque build proposé par un addon (Talents Forever, Companion, Naowh) et chaque contexte (leveling, donjon,
  raid, PvP) : recalcul par le simulateur (niveau 60, spécialisations simulées) et par notre moteur (Mage, tous
  niveaux), classement, verdict « le build de l'addon est le meilleur » ou « mieux existe » avec l'écart chiffré et
  la raison (talent, statistique) ; là où rien ne calcule (soigneurs, tanks, PvP, leveling des autres classes), le
  rapport le dit au lieu d'inventer.
- **Rapport des écarts entre sources** par classe et spécialisation : addons, simulateur, notre moteur, tes journaux
  de combat quand ils existent (`forever measures`) ; source retenue et pourquoi (fraîcheur, couverture, accord avec
  les journaux). Fichier régénéré à chaque version : `docs/research/sources-ecarts-<version>.md`.

### 3.4 Une nouvelle version : un rapport, plus des tests rouges
- La veille produit **un rapport des valeurs qui changent** (sorts, talents, builds recommandés, poids, sources
  devenues en retard) à valider, au lieu d'une attente bloquée ou de tests rouges ; l'accord de l'utilisateur installe.
- **Politique de tests** : un test qui vérifie une **valeur de jeu** lit une version figée explicite de sa famille
  (jamais la version installée) ; un test sur la version installée ne vérifie que des **invariants** (structure,
  provenance, pas de panne, source en retard signalée). Migration des 88 fichiers qui lisent la version installée,
  famille par famille, sans changer une valeur attendue.

### 3.5 Routes
- **Squelette** : parcours gratuits de RestedXP sur les niveaux qu'ils couvrent, puis **guides de Polestar** au-delà,
  lus en local depuis un clone en cache à un commit épinglé, attribution dans la route livrée et sa provenance,
  utilisation et modification privées (GPL-3.0), **rien redistribué** : la décision 278 est revue en ce sens
  (nouvelle décision ; « jamais installé » reste : on lit les fichiers de guides, on n'installe pas l'addon).
- **Optimiseur en trois modes** (recommandation de l'étude) : insertion dans le squelette (donjons avec leurs quêtes,
  quêtes de classe, métiers, vols et foyer, chaque insertion avec sa raison), personnalisation (position réelle,
  quêtes faites, fenêtre glissante exacte sur 10 à 12 arrêts), trous (contenu 30-60 propre à Forever, quêtes lancées
  par un objet ; paquets de zone, recherche locale, ruine et recréation, acceptation tardive, passe de robustesse).
  Ordre : P1 évaluation incrémentale, P2 insertion, P3 vols, foyer et monstres en chemin, P4 objectif avec pénalités,
  P5 fenêtre glissante, P6 trous. Idées réécrites et citées, aucun code repris.

### 3.6 Réputations, métiers, équipement
- Lire et alimenter : **correction du défaut de Forever Guide** (appliquer `ItemBuild70425.lua` comme l'addon), lecteurs
  des rotations et builds de Forever Companion, des poids par défaut de Naowh, de SkillUp Forever, des quêtes de classe
  de Forever Guide ; la route de réputation (4e) réduite à ce qui est lisible (factions, paliers, récompenses, quêtes
  avec faction), gains `suppose` ; vérification par le calcul quand c'est possible (poids recoupés par le simulateur
  au 60).

### 3.7 Base de connaissances locale
- `<cache>/kb/`, reconstruite depuis les sources, jamais dans le dépôt (décision 133) : étage 1, une sortie par source
  (JSON) avec sa clé d'empreintes (taille, date, sha256 des fichiers, version de l'addon, build du jeu, version du
  lecteur) ; étage 2, fusion SQLite dont la clé est faite des empreintes des sorties (une source relue à l'identique ne
  relance pas la fusion), tables `STRICT` par type d'entité (quête, objet, PNJ, sort, zone) avec identifiant du jeu,
  provenance (source, certitude) par champ, FTS5 sur les noms ; schéma versionné, **reconstruction au lieu de
  migrations** ; construction à la fin de la veille, au démarrage du pont (tâche de fond) et au premier appel.
- Outils : résumé et identifiants d'abord, détail à la demande, provenance résumée une fois, moins de 10 000 jetons.
- Pilote : `quests` et `dungeons` (fusion et provenance par champ déjà là), mesure, puis objets, PNJ, sorts, zones.

## 4. Ce que le changement retire, ce qu'il garde
- **Retire** (ou rétrograde en recoupement) :
  - le moteur du Mage comme **réponse principale** au niveau 60 en raid et en donjon (le simulateur la donne) et pour
    les poids au 60 ;
  - toute rotation, tout build ou tout poids écrits par nous pour une classe qu'un addon ou le simulateur couvre ;
  - l'attente bloquée de la veille à chaque version qui touche le Mage (remplacée par le rapport à valider) ;
  - les tests de valeurs lus sur la version installée (rattachés à leur version) ;
  - les marqueurs muets du moteur (un texte changé sans modèle connu → « en retard », jamais l'ancien sens en silence) ;
  - la tranche d'optimiseur de routes « construire toute la route » (devient insertion et trous).
- **Garde** : le décodage du client et l'installation des versions (ils s'adaptent seuls), les lecteurs d'addons
  existants, le pont et la fenêtre en jeu, les exports vers les addons, la livraison RestedXP, la recette des routes,
  ForeverLogger et la mesure des journaux ; le moteur du Mage pour le **leveling, le temps par monstre et les niveaux
  sous 60** (personne d'autre ne les calcule), en recoupement des journaux ; le registre des mécaniques (une mécanique
  « lue d'une source » a son statut).
- **Ne construit pas** : un moteur générique des classes (décision 252), un simulateur de leveling pour les autres
  classes, une rotation écrite à la main.

## 5. Ordre de migration des outils existants
1. `forever_build` : builds lus (Talents Forever, Companion, Naowh), vérifiés (simulateur au 60, moteur pour le Mage),
   verdict « meilleur » ou « mieux existe » ; source en retard signalée.
2. `forever_gear` : poids de la meilleure source à jour (simulateur au 60, Companion, Naowh ; nos poids du Mage sous 60
   en recoupement), BiS fusionné, défaut de Forever Guide corrigé.
3. `forever_lookup` et `forever_explain_mechanic` : lisent la base locale (pilote quêtes et donjons d'abord).
4. `forever_route` : squelette RestedXP puis Polestar, mode insertion, attribution.
5. `forever_sim_leveling` : temps par monstre du moteur (Mage) et des journaux, source dite ; « non calculé » sinon.
6. `forever_status` et la veille : rapport des valeurs qui changent et des sources en retard.

## 6. Calendrier jusqu'au 4 novembre (sans jeu jusqu'à la sortie)
| Dates | Travail | Condition |
| --- | --- | --- |
| 21-22 oct. | Validation du plan ; décisions (288 faite ; 278, 224, 250, 252 amendées) ; registre des sources et détection de fraîcheur (cœur, §3.1) ; défaut de Forever Guide | accord |
| 22-24 oct. | Rapport des valeurs qui changent dans la veille ; politique de tests et migration des familles exposées (§3.4) | — |
| 24-27 oct. | Simulateur `wowsims/forever` en local, DPS et poids au 60, vérification des builds, premier rapport des écarts par classe et spécialisation (§3.2, §3.3) | accord sur Go, `protoc` et le réseau ; sinon builds et poids des addons seulement, et ces jours vont aux routes |
| 27-30 oct. | Routes : décision sur Polestar, lecture du squelette, P1 et P2 (évaluation incrémentale, insertion) | accord sur le clone de Polestar |
| 30 oct.-1er nov. | Lecteurs : rotations et builds de Companion, SkillUp, quêtes de classe de Forever Guide, poids de Naowh ; route de réputation lue (4e réduite) | — |
| 1er-2 nov. | Base locale, pilote quêtes et donjons, sorties compactes de `forever_lookup` | — |
| 3 nov. | Marge ; `docs/LANCEMENT.md` (essais des nouveautés) | — |
| 4 nov. | Sortie : version finale installée par la veille (rapport des valeurs qui changent), essais en jeu | — |

**Glisse après le 4 novembre** : réponses en cartes du bloc 6b (décision 287), P3 à P6 des routes (vols et foyer de 1d
compris dans P3), extension de la base locale aux objets, PNJ, sorts et zones, vérification des soigneurs et des
tanks dès qu'une source les calcule.

## 7. À trancher par l'utilisateur
1. **Simulateur** : accord pour Go 1.25 et `protoc` (hors de `uv`), le clone et la mise à jour de `wowsims/forever`
   (réseau), et sa compilation locale ?
2. **Polestar** : lire ses guides comme squelette au-delà de RestedXP (clone en cache, commit épinglé, usage privé,
   attribution, rien redistribué) : nouvelle décision qui amende la 278 ?
3. **Correctifs du serveur** : la liste publique des `DBCache.bin` vérifiés de raidbots (utilisée par le simulateur)
   comme source de nos correctifs quand tu ne peux pas te connecter : nouvel accès réseau, à accepter ou non.
4. **Base locale** : une seule base (recommandé) ou une par domaine ; nombre de bases gardées ; recherche plein texte
   sur les noms seulement (recommandé) ou aussi les objectifs de quête.
5. **AlexAtlasLoot** : pendant l'inventaire, un agent a ouvert ses fichiers et compté leur structure, contre la
   décision 229 (« exclu et jamais lu ») ; aucune valeur recopiée, le rapport ne garde que des comptes. La décision 229
   reste en vigueur sauf avis contraire ; dis-moi si tu veux que ces comptes soient retirés du rapport.

## 8. Risques
- Le simulateur est en « Alpha », mono-mainteneur par classe, son format change sans migration et ses flux visent le
  produit de la bêta, qui change à la sortie : épinglage du commit, recoupement par notre moteur (Mage) et par les
  journaux, mention « source externe, `suppose` ».
- Sans le simulateur, la vérification des builds se réduit au Mage : les autres classes restent « build d'addon, non
  vérifié ».
- Les addons de l'utilisateur ne sont à jour que s'il les met à jour (SavedVariables du 15/10 aujourd'hui) : la
  fraîcheur est dite dans chaque réponse.
- Migration des tests : risque de perdre de la couverture réelle ; règle : chaque test déplacé garde un pendant
  « invariant » sur la version installée.
- Calendrier serré (14 jours, sans jeu) : le cœur (§3.1, §3.4) passe en premier ; tout le reste peut glisser sans
  casser l'existant.

## 9. Avis de l'advisor
(à compléter)
