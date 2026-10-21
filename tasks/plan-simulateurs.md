# Plan « Calculs réutilisés » (2026-10-21, en attente de validation)

Principe (décision 293, consignée dans `docs/DECISIONS.md` et `CLAUDE.md`) : les calculs se basent sur ce qui existe et
est maintenu par d'autres, par des adaptateurs minces, épinglés et mis à jour automatiquement ; on n'écrit plus de code
de calcul qui recopie une mécanique du jeu ; notre code redondant est retiré ou gelé.

Étude : `docs/research/simulateurs-2026-10-21.md`.

## 0. Addons à installer de ton côté
**Aucun n'est nécessaire pour ce plan.** Le contexte du pont donne déjà race, classe, niveau, talents, équipement et
stats du personnage connecté. En option : **Sims Forever** (auteur Blueteak, MIT,
https://www.curseforge.com/wow/addons/sims-forever), seulement si tu veux coller ton personnage dans simsforever.com
à la main (`/simf`). AllTheThings n'est pas étudié ici : il le sera au chantier des quêtes manquantes.

## 1. Les deux questions (décision 288)
- **Qui maintient déjà ça mieux que nous ?** Au niveau 60 : **wowsims/forever** (MIT, en local, neuf classes, suit 70450
  et ses correctifs à la journée). Sous le 60 : **personne** de façon réutilisable. Sims Forever a un moteur de
  leveling, mais il n'est ni publié ni appelable, et n'a pas encore le Mage ni le Chaman. ForeverDB et DPS Forever
  sont fermés. MythicSim est un fork de wowsims, en retard d'une version.
- **Que se passe-t-il au prochain patch ?** wowsims publie la mise à jour, le binaire épinglé change de version, on
  rejoue les cas de référence. Notre moteur du Mage, lui, demande chaque fois une journée comme HF2 : c'est ce qu'on
  arrête.

## 2. Adoption (ce que je propose)
- **wowsims/forever, moteur principal au niveau 60, neuf classes** : dégâts par seconde de fin de partie (donjon,
  raid), poids des statistiques par tirages appariés, comparaison des races et des classes, builds du 60 (nos
  candidats évalués par wowsims). Adaptateur mince `forever/sims/wowsims.py` :
  - écrit une `RaidSimRequest` (protojson) depuis le personnage connecté (race, classe, talents, équipement) ;
  - lance `wowsimcli sim` en sous-processus local, sans réseau ;
  - lit `RaidSimResult` ;
  - provenance : version et sha256 du binaire, commit, certitude `suppose`.
- **Sous le 60 (leveling)** : aucune source réutilisable. Je propose de **geler** notre moteur du Mage tel qu'il est
  en r7 : plus aucune mécanique ajoutée, résultats marqués « calcul gelé, 70450 r7 ». Il est recoupé par nos journaux
  de combat, la seule mesure réelle. Pour les autres classes : temps par monstre mesuré dans les journaux, sinon
  « non calculé ». On regarde à chaque veille si Sims Forever publie son moteur ou si wowsims accepte un niveau
  inférieur. Dès que l'un des deux le fait, il remplace notre leveling.
- **PvP** : aucune source ne le calcule. Notre profil PvP analytique est gelé ; les conseils viennent des fiches
  (raciaux, contres) et des guides.

### Ce que notre moteur fait en double, et son sort
| Code | Sort |
| --- | --- |
| rencontres du 60 (`forever/sim/encounter.py`, scénarios de donjon et de raid au 60) | **retiré** au profit de wowsims ; gardé pour les niveaux inférieurs au 60, gelé |
| poids du Mage au 60 (`gear.py` `mage_weights` au niveau 60) | **retiré** au profit des poids de wowsims ; sous le 60, gelé |
| optimiseur de fin de partie (`optimize/endgame.py`) | **gelé** ; les candidats du 60 sont évalués par wowsims |
| mécaniques du Mage (`forever/engine/`, HF2 compris) | **gelées** à 70450 r7 ; plus aucune mécanique nouvelle |
| Eureka! actif (branche `races`, non fusionnée) | **abandonné** (nouveau code de calcul) ; wowsims modélise Eureka! |
| PvP analytique (`engine/pvp.py`) | **gelé** |

### Ce qu'on garde (aucune source ne le fait)
XP réelle de Forever, routes et leur personnalisation, livre des quêtes et ses sources, respécialisations, profil et
pont, mesures tirées des journaux de combat, lecteurs du client et des addons, veille.

### Ce que l'adoption simplifie
- Plus de révision du moteur à chaque patch du Mage (HF2 a pris une journée).
- Plus de rejeu de 16 cas sur deux heures pour le 60 : quelques secondes par cas dans wowsims.
- Moins de tests de mécaniques : ceux du gel restent, figés ; les nouveaux tests portent sur l'adaptateur (format
  d'entrée et de sortie, provenance, erreurs).
- Neuf classes au 60 d'un coup, sans moteur par classe (CM1 au niveau 60 devient l'adaptateur).

## 3. Apprendre en continu (registre des sources et veille)
- **Registre des sources** (`forever/sources.py`) : ajout de wowsims/forever (commit, version du binaire, date),
  Sims Forever, DPS Forever, ForeverDB et MythicSim. Ces quatre derniers en **référence relue à la main** : pas
  d'API, `robots.txt` interdit leurs `/api/`, et leur code est fermé (sauf MythicSim).
- **Veille** : nouvelle étape `simulateurs` de `forever update`, après `guides`.
  - Elle lit la dernière publication de wowsims/forever (API GitHub publique, lecture seule).
  - Si une nouvelle version paraît, elle la télécharge, l'épingle (version, sha256) et rejoue les cas de référence
    du 60 et nos cas du Mage.
  - Les écarts avec notre calcul gelé vont dans `docs/research/simulateurs-veille-<date>.md`, avec la source retenue
    et pourquoi.
  - Site ou GitHub injoignable : « non mis à jour », copie précédente gardée, passage non bloqué (comme Polestar).
- **Accès réseau déclarés** dans `CLAUDE.md` : GitHub (publications de wowsims/forever, lecture et téléchargement du
  binaire épinglé). Aucun autre site n'est appelé automatiquement.

## 4. Calendrier (sortie le 4 novembre, coupure le 2, le 3 réservé au dernier verify et à `docs/LANCEMENT.md`)
| Dates | Livraison |
| --- | --- |
| 22 oct. | Décision 293 et `CLAUDE.md` (faits avec ce plan) ; registre des sources étendu (références à la main) |
| 23-25 oct. | Adaptateur wowsims : binaire épinglé, `RaidSimRequest` depuis le personnage connecté, lecture du résultat ; tests sur des sorties enregistrées (sans réseau) |
| 26-27 oct. | Poids et comparaisons des races et des classes au 60 par wowsims ; outils `forever_build` et `forever_gear` branchés au 60 ; ta comparaison Mage, Chaman et races refaite dessus |
| 28-29 oct. | Étape `simulateurs` de la veille, rapport des écarts ; gel du moteur (marquage, retraits du 60) |
| 30 oct.-2 nov. | Reste de ta demande précédente : `docs/LANCEMENT.md` (préférences de départ, neuf classes, plusieurs personnages) ; correction de `lookup_zones` filtré sur le Mage ; proposition du type de serveur (ci-dessous) |
| après le 4 nov. | Leveling par une source externe dès qu'il en existe une ; type de serveur et zones disputées si tu le valides |

## 5. À trancher par toi
1. **Binaire de wowsims** : le télécharger épinglé (version, sha256, depuis les publications GitHub ; accès réseau
   nouveau) ou le compiler (Go, dépendance hors de `uv`) ? Je recommande le binaire épinglé.
2. **Leveling** : geler notre moteur du Mage comme seul calcul sous le 60 (recommandé) ou ne plus rien calculer sous
   le 60 (journaux seulement) ?
3. **Branche `races`** (Eureka! actif) : je propose de l'abandonner.
4. **Type de serveur (JcJ ou normal)** : aujourd'hui, rien ne le connaît (ni l'addon, ni le profil, ni les routes,
   ni l'équipement, ni le PvP). Je propose :
   - un champ du profil par personnage, déclaré par toi ;
   - les zones disputées lues dans un addon (Naowh porte `territory`) ;
   - un signalement dans les routes sur un serveur JcJ.
   Le client Classic ne donne pas ce type de façon sûre, d'où ta déclaration. Avant ou après le 4 novembre ?

## 6. Décisions du 2026-10-21 (suite), validées
- wowsims/forever **compilé chez nous** depuis un commit épinglé, sans aucune modification du code (pas de binaire
  publié : la liste des publications GitHub est vide, les workflows de publication sont désactivés). Épinglé par le
  commit et l'empreinte de notre binaire ; recompilé par la veille à chaque nouveau commit. Outils : Go 1.27.0 et
  protoc 36.0, déjà installés ; `protoc-gen-go` installé par `go install` (réseau, une fois). Essai : le commit
  5f0a367 compile en 12 s (`go build --tags=with_db ./cmd/wowsimcli`, binaire de 27 Mo) ; 2 000 combats en moins
  d'une seconde.
- Messages envoyés : https://github.com/wowsims/forever/issues/624 (autres niveaux, publication des binaires) et
  https://github.com/Blueteak/SimsForeverExporter/issues/1 (moteur de leveling).
- Règle 294 appliquée avant le 4 novembre : l'outil des zones et le bouton Leveling reposent sur le livre de quêtes
  fusionné des sources Forever, plus sur la base Classic Era de Questie ; les valeurs de `mechanics.json` et
  `origins.json` qui viennent de la Classic sont recensées et marquées, et toute réponse qui s'appuie sur elles le
  dit ; leur remplacement par des valeurs de Forever vient après la sortie, avec les mesures de l'utilisateur.

## 7. Étapes de l'adaptateur
1. `forever sims update` (réseau, lecture seule) : clone en cache `<cache>/third_party/wowsims`, remise sur le dernier
   commit, génération protobuf, `go build`, épinglage (`pin.json` : commit, date, empreinte, versions de Go et protoc).
2. `forever/sims/wowsims.py` (aucun réseau) : requête de combat depuis un build du dépôt de wowsims (joueur, combat,
   buffs) ou depuis le personnage connecté (race, classe, talents, équipement), lancement du binaire épinglé,
   lecture du résultat ; provenance (commit, empreinte, certitude `suppose`).
3. Comparaisons au 60 : races, spécialisations, poids par tirages appariés (`bonusStats`), même graine.
4. Branchement dans `forever_build` et `forever_gear` au niveau 60 ; sous le 60, moteur du Mage gelé, dit comme tel.
5. Étape `simulateurs` de la veille, rapport des écarts.
