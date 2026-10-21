# Plan « Sources d'abord » (décision 288) — changement de cap du 2026-10-21

Demande de l'utilisateur du 2026-10-21, prioritaire sur la suite du bloc 6b de CJ1. Plan écrit pour validation :
**rien n'est construit avant son accord**.

> Statut : **validé le 2026-10-21** (décisions 289 à 291). Fait : Piercing Ice et correctifs du serveur (révision 6 de
> 70450, lus chez Raidbots, veille branchée sur Raidbots) ; lecture de Forever Guide avec ses deltas `ItemBuild` ;
> (a) registre des sources (`forever/sources.py`, `forever status`, provenance de `forever_build`) ; (b) Forever
> Companion pour les neuf classes (`class_guide`, bouton Talents) et SkillUp (`profession`) ; (c) inversion de fixture
> (`VALUES_VERSION`, invariants, répétition générale verte) et aperçu du rejeu avec talents ajoutés ou retirés ; (d)
> Polestar au-delà de RestedXP (`forever/polestar.py`, `forever route polestar`). Reste : quêtes de classe de Forever
> Guide, poids de Naowh, assistant Métier du pont, mise à jour de Polestar par la veille.

## 0. Constat et règle
- Notre moteur maison casse à chaque refonte de classe : 229 tests rouges pour 1.60.1.70450 (8 vrais défauts, le
  reste figé sur l'ancien Mage), 119 pour 70291 ; une constante de version figée de plus à chaque refonte ;
  88 fichiers de tests lisent la version installée et restent exposés au prochain patch
  (`docs/research/audit-cap-288-2026-10-21.md`). Ce qui est lu dans le client et dans les addons s'adapte seul.
- **Décision 288** (consignée, et dans `CLAUDE.md`) : avant tout chantier, « qui maintient déjà ça mieux que nous ? » et
  « que se passe-t-il au prochain patch ? » ; si tout casse, on ne le construit pas : on lit et on alimente ce qui
  existe ; notre calcul ne sert qu'en recoupement et pour combler les trous ; une nouvelle version donne un rapport des
  valeurs qui changent, à valider, pas des tests rouges.

## 1. Urgent : Piercing Ice probablement retiré par le serveur
L'étude du simulateur (`docs/research/simulateur-communaute-2026-10-21.md`, lignes 25-29, 193, 257-259) relève que la
PR #594 de `wowsims/forever` (2026-10-20, correctif du serveur 112753 lu dans un `DBCache.bin` de la bêta à l'en-tête
70450) **retire le talent Piercing Ice** du Mage ; nos `talents.json` et `classes.json` de 70450, installés sans
correctifs du serveur (décision 285), le portent encore. Le rejeu d'hier le met dans le build PvP champ de bataille 40
et dans des alternatives Givre. **Effet** : le pont peut recommander un talent qui n'existe plus. Source tierce
(certitude au plus `suppose`), non vérifiée en jeu. Proposition en §7.1.

## 2. Études de l'existant (décision 264 ; lecture seule, sources citées et datées)
| Étude | Fichier | Constat principal |
| --- | --- | --- |
| Carte de notre code, ce qui casse | `docs/research/audit-cap-288-2026-10-21.md` | tout le calcul de combat est propre au Mage ; 11 branches du moteur suivent des marqueurs tirés du texte anglais du client, qui gardent l'ancien sens **sans rien dire** quand le texte change ; la veille se met en attente à chaque version qui touche le Mage et ne sait pas rejouer quand un talent ou un sort est ajouté |
| Addons installés | `docs/research/sources-addons-2026-10-21.md` | builds et rotations de Forever Companion (28 spécialisations, niveau 30 et « Leveling 1-60 », rotations en prose), builds populaires de Talents Forever (build 70425, arbres identiques à 70450), BiS (Companion du 20/10, Naowh du 11/10), métiers (SkillUp, généré sur 70450), quêtes de classe (Forever Guide) ; **défaut** : nous lisons `ForeverGuide/GearData.lua` sans `ItemBuild70425.lua`, que l'addon applique (291 objets modifiés, 20 retirés) ; trous pour toutes les classes : temps par monstre, DPS chiffré sous 60, poids par niveau, ordre de prise des talents, parcours au-delà du niveau 22 |
| Simulateur de la communauté | `docs/research/simulateur-communaute-2026-10-21.md` | `ElliotWood/Forever` n'existe plus ; référence `wowsims/forever` (MIT, plusieurs mainteneurs), suivi par MythicSim ; données plus à jour que les nôtres ; 12 spécialisations simulées (« Alpha »), 4 soigneurs en planificateur, 2 tanks non publiés ; **joueur fixé au niveau 60** ; **aucun binaire à jour** (compilation Go 1.25 et `protoc`) ; flux visant le produit de la bêta, qui change à la sortie |
| Méthodes de routes | `docs/research/routes-methodes-2026-10-21.md` | Polestar (paquets de zone, recuit, robustesse), Factoruide (évaluation incrémentale, ruine et recréation), outils écrits à la main ; méthodes retenues : insertion, recherche locale, acceptation tardive, ILS, LNS, GRASP ; écartées : génétique, fourmis, apprentissage par renforcement, MIP exact |
| Base locale, cache, sorties compactes | `docs/research/base-locale-2026-10-21.md` | caches actuels de 194 Mo (quêtes) et 14 Mo (donjons) sans arrêt anticipé ; base `<cache>/kb/` à deux étages d'empreintes, SQLite `STRICT`, provenance par champ, FTS5 ; reconstruction plutôt que migrations ; sorties sous 10 000 jetons |

Au passage : un agent de l'inventaire a ouvert les fichiers d'AlexAtlasLoot, contre la décision 229 ; aucune valeur
recopiée ; les comptes notés sont retirés du rapport ; la décision 229 reste en vigueur.

## 3. Les deux questions, domaine par domaine
| Domaine | Qui le maintient mieux que nous ? | Au prochain patch | Rôle de notre code |
| --- | --- | --- | --- |
| Builds de talents (contexte, niveau) | Talents Forever (builds populaires), Forever Companion, Naowh | leurs auteurs ; nous détectons un talent changé | lire, vérifier quand un calcul existe (moteur du Mage ; simulateur au 60 plus tard) ; ordre de prise : nous seulement pour le Mage |
| Rotations | Forever Companion (prose, niveau 30) ; simulateur au 60 | idem | lire ; aucune rotation écrite par nous pour une autre classe |
| Poids sous 60, temps par monstre, XP par heure | **personne** | notre moteur du Mage casse | Mage : notre moteur, signalé « en retard » quand il l'est ; autres classes : tes journaux (`kill_time.py`) ou « non calculé » ; pas de moteur générique (décision 252) |
| DPS et poids au 60 | `wowsims/forever` | ils le réparent | après la sortie (§7.2) |
| Listes BiS, équipement par niveau | Companion, Naowh, GearQuest, Forever Guide | leurs auteurs | lire, fusionner, classer par la meilleure source de poids à jour |
| Parcours de leveling | RestedXP (gratuit jusqu'au niveau 22 environ), Polestar (1-60) | leurs auteurs | personnaliser, insérer, livrer ; l'optimiseur comble les trous |
| Vols et pierre de foyer (1d) | les parcours de RestedXP les contiennent déjà | leurs auteurs | lire le squelette règle 1d sur les niveaux couverts |
| Réputations | Forever Guide (factions), Naowh (paliers, récompenses) ; aucun gain chiffré | — | lire ; route de réputation réduite à ce qui est lisible, gains `suppose` |
| Métiers | SkillUp Forever | son auteur | lire (lecteur à écrire), livrer |
| Données du jeu | le client (tables décodées), Questie | s'adapte seul | décoder, ranger |

**Nos propres constructions passées aux deux questions** : le registre des sources et la base locale sont neufs ;
ils ne cassent pas au prochain patch parce qu'ils ne portent **aucune valeur de jeu** : ils sont reconstruits depuis
le client et les fichiers des sources, et leur fraîcheur se lit dans ce que les sources portent (identifiants, champs
de build, version et date).

## 4. La réponse du 4 novembre, par classe (niveaux 1 à 20, le gros des joueurs à la sortie)
Pour chacune des neuf classes, chaque élément avec sa source et sa fraîcheur :
- **talents** : build de Talents Forever (builds populaires) ou de Forever Companion (« Level 30 », « Leveling 1-60 ») ;
  ordre de prise calculé seulement pour le Mage, « ordre non calculé » sinon ;
- **rotation** : celle de Forever Companion, en prose, au niveau 30, dite comme telle ;
- **équipement par niveau** : GearQuest et Forever Companion, Forever Guide corrigé (`ItemBuild70425`) ;
- **route** : parcours gratuit de RestedXP adapté (position, quêtes faites, quêtes de classe, donjons avec leurs
  quêtes), puis Polestar au-delà, avec attribution ;
- **métier** : SkillUp Forever ;
- **temps par monstre et XP par heure** : Mage par notre moteur ; autres classes par tes journaux, sinon « non calculé ».

## 5. Architecture retenue
### 5.1 Registre des sources et fraîcheur (cœur du changement)
- Un **registre des sources** par domaine (`forever/sources/`) : ce que chaque source fournit, pour quelles classes et
  spécialisations, sa fraîcheur et un ordre de préférence par domaine.
- **Fraîcheur par le contenu** : identifiants de nœuds de talents et de sorts de la source comparés à nos tables du
  client (et rangs, points de base, coefficients quand elle les porte) ; ainsi Talents Forever (build 70425, arbres
  identiques à 70450) n'est **pas** déclaré en retard à tort. Pour une source en prose (rotations de Companion), la
  fraîcheur n'est que « version et date de l'addon contre build du jeu », dite comme telle.
- **Repli** : une source en retard pour une entrée que la réponse utilise est écartée ; la réponse dit « calcul en
  cours de mise à jour », nomme la source écartée et prend la meilleure source encore à jour ; s'il n'en reste aucune,
  la meilleure source avec « source antérieure au patch » ; **jamais une panne**.
- Notre moteur du Mage passe par la même détection : un talent dont le texte du client a changé sans modèle connu met
  le moteur « en retard » au lieu de garder l'ancien sens sans rien dire (les 11 branches à marqueurs).

### 5.2 Vérification des builds et rapport des écarts entre sources
- Chaque build proposé par un addon, par contexte (leveling, donjon, raid, PvP), est recalculé là où un calcul existe :
  notre moteur pour le Mage (tous niveaux), le simulateur au 60 quand il sera là ; classement, verdict « le build de
  l'addon est le meilleur » ou « mieux existe », écart chiffré et raison ; ailleurs, le rapport le dit.
- **Rapport des écarts entre sources** par classe et spécialisation (addons, simulateur, notre moteur, tes journaux
  quand ils existent), source retenue et pourquoi, régénéré à chaque version (`docs/research/sources-ecarts-<version>.md`).

### 5.3 Une nouvelle version : un rapport, plus des tests rouges
- La veille produit **un rapport des valeurs qui changent** (sorts, talents, builds recommandés, poids, sources en
  retard), à valider ; ton accord installe ; plus d'attente bloquée à chaque version qui touche le Mage.
- **Inversion de fixture** (au lieu de migrer 88 fichiers) : `game_data` lit par défaut une `VALUES_VERSION` figée (la
  version où les valeurs attendues ont été validées) ; une fixture `game_data_installed` sert aux seuls tests
  d'invariants (structure, provenance, pas de panne, source en retard signalée). La prochaine version n'allume plus
  rien dans le `verify` du clone ; monter `VALUES_VERSION` est un acte délibéré, fait après le rapport des valeurs qui
  changent, avec les attentes mises à jour en une fois. Chaque famille garde un pendant « invariant » sur la version
  installée, pour ne pas perdre la couverture réelle.

### 5.4 Routes
- **Squelette** : parcours gratuits de RestedXP sur les niveaux qu'ils couvrent, puis **guides de Polestar** au-delà.
- **Décision 289** (proposée, amende la 278 comme tu l'as demandé) : les guides de Polestar sont lus comme squelette
  des routes au-delà des parcours gratuits de RestedXP, depuis un clone en cache hors du dépôt
  (`<cache>/third_party/polestar`, commit épinglé dans la provenance), en utilisation et modification privées
  (GPL-3.0), avec attribution dans chaque route livrée ; rien n'est redistribué ni copié dans le dépôt ; l'addon n'est
  jamais installé ni exécuté ; ses règles de jeu restent `suppose` sans source, et sa règle sur les donjons n'est
  toujours pas reprise.
- **Optimiseur en trois modes** : insertion dans le squelette (donjons avec leurs quêtes, quêtes de classe, métiers,
  chaque insertion avec sa raison), personnalisation (position réelle, quêtes faites, fenêtre glissante exacte sur 10
  à 12 arrêts), trous (contenu 30-60 propre à Forever, quêtes lancées par un objet ; paquets de zone, recherche locale,
  ruine et recréation, acceptation tardive, passe de robustesse). Ordre : P1 évaluation incrémentale, P2 insertion,
  P3 monstres en chemin, P4 objectif avec pénalités, P5 fenêtre glissante, P6 trous. Idées réécrites et citées, aucun
  code repris.

### 5.5 Lecteurs : réputations, métiers, équipement, rotations
- Correction du défaut de Forever Guide (`ItemBuild70425.lua` appliqué comme l'addon) ; lecteurs des rotations et
  builds de Forever Companion, des poids par défaut de Naowh, de SkillUp Forever, des quêtes de classe de Forever
  Guide ; route de réputation (4e) réduite à ce qui est lisible.

### 5.6 Simulateur de la communauté (après la sortie, §7.2)
- `wowsims/forever` compilé en local à un commit épinglé, lancé en sous-processus ; DPS et poids au 60 pour les 12
  spécialisations simulées, « Est-ce une amélioration ? », lots de builds ; certitude `suppose`, provenance (commit,
  builds par groupe de classes).

### 5.7 Base de connaissances locale (conçue, pilote après la sortie)
- `<cache>/kb/`, reconstruite depuis les sources, jamais dans le dépôt (décision 133) : étage 1, une sortie par source
  (JSON) avec sa clé d'empreintes (taille, date, sha256 des fichiers, version de l'addon, build du jeu, version du
  lecteur) ; étage 2, fusion SQLite dont la clé est faite des empreintes des sorties (arrêt anticipé), tables `STRICT`
  par type d'entité (quête, objet, PNJ, sort, zone) avec identifiant du jeu, provenance par champ, FTS5 sur les noms ;
  schéma versionné, reconstruction au lieu de migrations ; construction à la fin de la veille, au démarrage du pont
  et au premier appel ; outils : résumé et identifiants d'abord, détail à la demande, moins de 10 000 jetons.
- Pilote : `quests` et `dungeons`, mesure, puis objets, PNJ, sorts, zones.

## 6. Ce que le changement retire, ce qu'il garde
- **Retire** : toute rotation, tout build ou tout poids écrits par nous pour une classe qu'un addon ou le simulateur
  couvre ; l'attente bloquée de la veille ; les tests de valeurs sur la version installée (inversion de fixture) ; les
  marqueurs muets du moteur ; l'ambition « construire toute la route » de l'optimiseur (devient insertion et trous) ;
  à terme, le moteur du Mage comme réponse principale au 60 en raid et en donjon (quand le simulateur sera là).
- **Garde** : le décodage du client et l'installation des versions, les lecteurs d'addons existants, le pont et la
  fenêtre en jeu, les exports, la livraison RestedXP, la recette des routes, ForeverLogger et la mesure des journaux ;
  le moteur du Mage pour le leveling, le temps par monstre et les niveaux sous 60 (personne d'autre ne les calcule),
  en recoupement des journaux ; le registre des mécaniques.
- **Ne construit pas** : un moteur générique des classes (décision 252), un simulateur de leveling pour les autres
  classes, une rotation écrite à la main.

## 7. À trancher par l'utilisateur
1. **Piercing Ice et les correctifs du serveur** (urgent) : (a) marquer tout de suite Piercing Ice « probablement
   retiré par le serveur (correctif 112753, source `wowsims/forever`, `suppose`) » et l'exclure des recommandations
   jusqu'à la lecture des correctifs (révision numérotée de 70450, question ouverte) ; (b) en plus, lire les
   correctifs du serveur dans la liste publique des `DBCache.bin` vérifiés de raidbots, seul moyen d'avoir les
   correctifs avant le 4 novembre : nouvel accès réseau, à accepter ou non. Recommandé : (a) maintenant, (b) si tu
   l'acceptes.
2. **Simulateur avant ou après le 4 novembre** : tu as demandé d'avancer SIM1 ; l'advisor et moi recommandons de
   le **reporter après la sortie** : il est fixé au niveau 60 alors que tout le monde sera entre 1 et 20 ; ses flux
   visent le produit de la bêta et changeront le 4 novembre (travail à refaire le 5) ; il demande Go 1.25 et `protoc`
   hors de `uv` et un clone réseau, pour 12 spécialisations « Alpha ». Si tu le maintiens avant la sortie, il prend
   les jours 24-27 octobre et les routes glissent d'autant.
3. **Polestar** : le principe est tranché par ta demande (décision 289 ci-dessus) ; reste l'**accès réseau** pour le
   clone et ses mises à jour, à accepter.
4. **Base locale** : une seule base (recommandé) ou une par domaine ; recherche plein texte sur les noms seulement
   (recommandé) ou aussi les objectifs de quête. (Le pilote glisse après la sortie.)

## 8. Calendrier jusqu'au 4 novembre (sans jeu)
**Minimum pour le 4 novembre** :

| Dates | Travail |
| --- | --- |
| 21-22 oct. | Validation ; décisions 289 (Polestar) et amendements de 224, 250, 252 ; Piercing Ice (§7.1) ; défaut `ItemBuild70425` de Forever Guide |
| 22-25 oct. | (a) Registre des sources, fraîcheur par le contenu, repli « calcul en cours de mise à jour » ; marqueurs du moteur du Mage reliés à la même détection |
| 25-28 oct. | (b) Lecteurs pour les neuf classes entre 1 et 20 : rotations et builds de Companion, SkillUp, quêtes de classe de Forever Guide, poids de Naowh ; réponse du §4 dans `forever_build`, `forever_gear`, `forever_route` |
| 28-30 oct. | (c) Inversion de fixture (`VALUES_VERSION`, `game_data_installed`) et rapport des valeurs qui changent dans la veille |
| 30 oct.-2 nov. | (d) Squelette des routes : RestedXP puis Polestar avec attribution (lecture, découpe, livraison) ; vols et foyer des niveaux couverts par ce squelette (1d) |
| 3 nov. | Marge ; `docs/LANCEMENT.md` (essais des nouveautés) |
| 4 nov. | Sortie : version finale par la veille (rapport des valeurs qui changent), essais en jeu |

**Glisse après le 4 novembre** : simulateur (§5.6, sauf choix contraire au §7.2), vérification des builds au 60 et
rapport des écarts complet, P1 à P6 de l'optimiseur de routes, pilote de la base locale, réponses en cartes du bloc
6b (décision 287), route de réputation au-delà du lisible.

## 9. Avis de l'advisor (tel quel)
> **Verdict global.** L'architecture (registre des sources avec fraîcheur par sort et talent, repli « calcul en cours
> de mise à jour », squelette RestedXP puis Polestar, base locale à deux étages) est la bonne lecture de la décision
> 288 et des cinq études. Le plan pèche sur **l'ordre et le calendrier**, et il enterre un fait urgent que ses propres
> études ont trouvé.
>
> **Désaccords**
>
> 1. **Le simulateur n'est pas une priorité d'avant le 4 novembre ; le plan lui donne les trois meilleurs jours
> (24-27 oct.).** Trois raisons tirées de ton étude : il est fixé au niveau 60 alors que tout le monde sera entre 1 et
> 20 à la sortie ; ses flux visent le produit de la bêta et changeront à la sortie (travail à refaire le 5 novembre) ;
> il exige une chaîne Go et `protoc` hors de `uv`, pour 12 spécialisations « Alpha ». Je recommande de **le reporter
> après la sortie**, en le disant franchement à l'utilisateur comme un désaccord avec son point 1 (« avance SIM1 »), et
> de donner ces jours aux lecteurs et aux routes. Si l'utilisateur maintient SIM1 avant le 4, qu'il le fasse en
> connaissance de ces trois points.
>
> 2. **Piercing Ice.** L'étude du simulateur dit que le correctif du serveur 112753 retire Piercing Ice et que nos
> `talents.json` et `classes.json` de 70450 le portent encore. Or les builds rejoués hier le contiennent (Givre du PvP
> champ de bataille 40, alternatives Givre du leveling). Si c'est exact, le pont recommande aujourd'hui un talent qui
> n'existe plus. Ce n'est pas le point 3 de la section « à trancher » : c'est le **premier** point, avec son effet
> concret, et la liste publique de raidbots est le seul moyen d'avoir des correctifs avant le 4 novembre. À vérifier
> dans le rapport de l'étude (source et date) avant de l'affirmer.
>
> 3. **La migration des 88 fichiers de tests est le mauvais levier.** Le même résultat s'obtient par une inversion de
> fixture : `game_data` lit par défaut une `VALUES_VERSION` figée (celle où les valeurs ont été validées), et une
> fixture `game_data_installed` sert aux seuls tests d'invariants (structure, provenance, pas de panne, source en
> retard signalée). La prochaine version n'allume alors plus rien dans le `verify` du clone ; la montée de
> `VALUES_VERSION` est un acte délibéré, fait après le rapport des valeurs qui changent, avec les attentes mises à jour
> en une fois. C'est ce qui rend l'installation de la version finale du 4 novembre possible sans la journée de
> corrections d'hier. Garde quand même le pendant « invariant » promis dans les risques.
>
> 4. **Le calendrier ne tient pas.** Hier, la seule installation de 70450 a pris la journée ; les blocs de CJ1
> prenaient un à deux jours chacun. Sept chantiers en quatorze jours sans jeu, non. Nomme un **minimum pour le 4
> novembre** et marque tout le reste « glisse » : (a) registre des sources et repli, (b) lecteurs qui donnent une
> réponse aux neuf classes entre 1 et 20 (rotations et builds de Forever Companion, SkillUp, défaut `ItemBuild70425` de
> Forever Guide, quêtes de classe, poids de Naowh), (c) inversion de fixture et rapport des valeurs qui changent, (d)
> squelette RestedXP puis Polestar avec attribution. Simulateur, P1-P6 des routes, base locale : après.
>
> 5. **La base locale « à concevoir avec soin » en deux jours, en fin de calendrier, c'est la concevoir sans soin.** La
> conception est faite (l'étude) ; dis que le pilote glisse après la sortie, sauf marge.
>
> **Points à renforcer dans le texte**
>
> - Dis ce qu'est **la réponse du 4 novembre par classe** (niveaux 1 à 20) : build de Talents Forever ou de Companion
> sans ordre de prise (sauf Mage), rotation en prose de Companion, équipement par niveau de GearQuest et Companion,
> route RestedXP, métier SkillUp, chacun avec sa source et sa fraîcheur. C'est le livrable que l'utilisateur a demandé
> en premier ; le plan ne le nomme pas.
> - Fraîcheur : préférer la **comparaison de contenu** (identifiants de nœuds et de sorts) au numéro de build, sinon
> Talents Forever (build 70425, arbres identiques à 70450) sera déclaré en retard à tort. Pour une source en prose
> (rotations de Companion), dis que la fraîcheur n'est que « version et date de l'addon contre build du jeu ».
> - 1d (vols et pierre de foyer) : les parcours de RestedXP contiennent déjà ces étapes ; lire le squelette règle 1d
> sur les niveaux couverts. À écrire, c'est une bonne nouvelle.
> - Applique les deux questions au plan lui-même : le registre et la base locale sont des constructions neuves ; dis
> pourquoi elles ne cassent pas au prochain patch (reconstruites depuis le client et des champs de build que les
> sources portent).
> - Polestar : l'utilisateur a déjà dit « revois la décision 278 en ce sens » ; écris la décision 289 dans le plan
> (clone en cache, commit épinglé, attribution, rien redistribué, addon jamais installé) au lieu de la poser en
> question. La question qui reste est le réseau pour le clone, pas le principe.
> - AlexAtlasLoot : retire les comptes du rapport toi-même (la décision 229 dit « jamais lu ») et signale-le ; ne
> demande pas la permission de les garder.
>
> **Ce que je ne conteste pas** : décision 252 maintenue ; le moteur du Mage gardé pour le leveling et sous 60 parce
> que personne d'autre ne le calcule ; les marqueurs muets remplacés par « en retard » ; le rapport des écarts entre
> sources par classe ; la liste de ce qui est retiré et gardé.

### Ce que j'ai changé à cause de cet avis
- Simulateur reporté après la sortie dans le calendrier, présenté comme un désaccord avec ta demande (§7.2), avec
  les trois raisons ; tu tranches.
- Piercing Ice vérifié dans l'étude (PR #594 de `wowsims/forever`, 2026-10-20, correctif 112753) et passé en tête
  (§1, §7.1).
- Migration des 88 fichiers remplacée par l'inversion de fixture (§5.3).
- Calendrier réduit à un minimum pour le 4 novembre (a à d), le reste « glisse » (§8).
- Base locale : conception gardée, pilote après la sortie (§5.7).
- Ajouts : la réponse du 4 novembre par classe (§4) ; fraîcheur par le contenu (§5.1) ; 1d réglé par le squelette sur
  les niveaux couverts (§3) ; les deux questions appliquées au registre et à la base (§3) ; décision 289 écrite
  (§5.4), la question restante est le réseau (§7.3) ; comptes d'AlexAtlasLoot retirés du rapport (§2).

### Ce que je n'ai pas changé
- Rien de l'avis n'est écarté. Une nuance : la vérification des builds (§5.2) reste dans le plan pour le Mage dès
  avant la sortie (notre moteur existe) ; seule sa partie au niveau 60 attend le simulateur.
