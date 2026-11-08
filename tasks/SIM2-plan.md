# Plan SIM2 — Dégâts par tranche de niveaux par les simulateurs de la communauté, corrigés chez nous (2026-11-08, en attente de validation)

Demande de l'utilisateur (2026-11-08) :
- « analyser = calculer », par tranche de niveaux **10-19, 20-29, 30-39, 40-49, 50-59 et 60** ;
- « DPS » veut dire, le plus souvent, le DPS de chaque tranche ;
- « tout est faux sur le Mage, modifie, ça doit s'adapter à tout » ;
- « regarde comment fonctionnent wowsims et MythicSim pour que tu puisses faire mes tranches » ;
- « s'il n'accepte pas, tu modifies leur code ».

Cette demande lève la condition de SIM2 dans `docs/ROADMAP.md`, qui attendait la réponse des auteurs. La réponse de
wowsims/forever#624 (2026-10-26) est connue : niveau 60 seulement, une adaptation locale est possible, mais elle n'est
pas dans leurs priorités.

## 1. Les deux questions (décision 288)

**Qui maintient déjà ça mieux que nous ?**
- **wowsims/forever** (Go, MIT) a déjà les neuf classes, le familier et tous les rangs de sorts dans sa base générée
  (`sim/core/spelldata/spells_auto_gen.go`). Ses mainteneurs mesurent déjà des journaux de bas niveau (PR #452 aux
  niveaux 10-14, #906 aux niveaux 20-24, #908 aux niveaux 22-25), mais n'évaluent leurs formules qu'au niveau 60.
- **MythicSim** (Rust, MIT) : même lignée, niveau 60.
- **Recherche du 2026-11-08** (deux études) : aucun outil ne donne de DPS par tranche pour Forever.
  - foreverdb.net/sim annonce un réglage de niveau, mais il comble les trous avec les règles de Classic (CMaNGOS). Il
    est écarté par la décision 294, sauf avis contraire (question 1).
  - Warcraft Logs (donjons de leveling de Forever depuis le 4 novembre environ) et foreverlogs.gg (niveaux 20 et 30 de
    la bêta) **mesurent**. Ils servent de recoupement.
- **Verdict** : on reprend wowsims, on ne récrit rien. On ajoute un jeu de correctifs minces qui le font calculer au
  niveau L. Notre moteur du Mage, gelé, est retiré du calcul.

**Que se passe-t-il au prochain patch ?**
- Les correctifs sont gardés **à part**, en fichiers de patch, et réappliqués par `forever update` sur chaque nouveau
  commit épinglé de wowsims.
- **Patch qui s'applique** : recompilation, puis rejeu des cas de référence de chaque tranche, avec le rapport des
  valeurs qui changent (décision 288).
- **Patch qui ne s'applique plus** : le binaire précédent reste en service, et la veille le dit sur la carte
  « Mis à jour » (exception « intégrité cassée » de la décision 295). Aucun calcul ne casse en silence.
- **Mainteneurs qui intègrent l'équivalent** : notre patch est retiré.
- **Données par niveau** (statistiques de base, `ExpectedStat`) : elles viennent des fichiers du client par l'outillage
  de wowsims (`make db`), ou de nos mesures en jeu, donc elles suivent le client.

## 2. Ce que l'étude du code de wowsims a montré (commit `64b21da`, lecture seule)

| Ce qui suppose le niveau 60 | Où | Correctif |
|---|---|---|
| `CharacterLevel = 60` (joueur, familier, cible par défaut, valeurs des sorts `Average/Roll`, buffs) | `sim/core/constants.go:9` et ses usages | Constante remplacée par un niveau lu dans la requête (réglage `level` du `.siml`) |
| **Rang de sort toujours au maximum** (`Highest()`, `ByID(rang max)` : environ 30 endroits pour le Mage, 25 pour le Chasseur, `pets.go:225` pour le familier) ; `levelGain` remet à 0 un écart négatif, donc il **surestime** fortement | `sim/mage`, `sim/hunter`, `spelldata/effect.go:96` | Plus haut rang tel que `SpellLevel ≤ L`, sur le modèle existant de `sim/shaman/ranks.go` ; sorts non appris retirés de l'APL ; `names.json` régénéré |
| Familier et faucon : PV, armure, puissance d'attaque et frappe tirés de `Creature*MaxLevel` | `sim/hunter/pets.go:40-61`, `summon_hawk.go` | Valeurs de `ExpectedStat` au niveau L (fichiers du client), recoupées par les mesures du code aux niveaux 11, 17 et 30 |
| Attributs de base par classe (Agi, Int, Esp, puissance d'attaque), saisis à la main au niveau 60 | `sim/core/base_stats.go:120-205` (« The game files carry no table ») | Mesurés en jeu par ForeverLogger (feuille du personnage nu, à chaque niveau), sinon `suppose` (question 2) |
| Critique par Agi et par Int, mana de base, critique de base | `base_stats_auto_gen.go` (`PlayerExpectedStat`, parseur qui suit déjà `CharacterLevel`) | Table par niveau générée par `make db` à partir des fichiers du client |
| Buffs et consommables des préréglages au rang maximal | préréglages `.siml` | Leveling en solo : aucun buff ni consommable par défaut ; option « groupe » |
| Cible des préréglages : niveau 63, armure 3731 | `sim/encounters` | Monstre normal de niveau L (PV mesurés dans nos journaux, sinon Questie corrigé, avec la certitude dite) |
| Talents : aucun contrôle du nombre de points | — | Contrôle chez nous (`check_talents` au niveau L) avant l'envoi |

Ce qui suit déjà `Unit.Level` ne change pas : table d'attaque, échecs, résistances (coefficient ajusté sur des journaux
aux niveaux 20 à 30), armure `400+85L`, compétence d'arme, notations (identiques à tous les niveaux).

Les objets de bas niveau sont dans la base de wowsims (`db.json` et `leftover_db.json`, environ 2 000 objets par
tranche sous le niveau 30), ainsi que les munitions de bas niveau.

## 3. Ce qui change

### a) Correctifs de wowsims (`forever/sims/patches/wowsims/*.patch`)
- Un patch par sujet : `level` (constante devenue réglage), `ranks-mage`, `ranks-hunter`, `pet-level`, `base-stats`,
  puis les autres classes une à une.
- Mention de licence MIT gardée ; chaque patch cite le fichier d'origine et la raison.
- Appliqués par `forever/pipeline/wowsims_build.py` après le checkout du commit épinglé (`git apply --3way`), avant la
  compilation. Empreinte du jeu de patchs dans `pin.json` et dans la provenance (« wowsims/forever 64b21da + correctifs
  forever <empreinte> »).
- Tests du simulateur repris : ceux qui supposent le niveau 60 restent verts au niveau 60, parce que le défaut ne
  change pas.

### b) MythicSim
- **Réparer d'abord la traduction des talents** : MythicSim refuse aujourd'hui les trois Mages (« arbre 1 plus long que
  l'arbre », essai du 2026-11-08). Ça vient de la dérive entre l'ordre des talents de wowsims au commit actuel et notre
  table de conversion. C'est exactement le « prochain patch » à rendre robuste : la conversion est relue à chaque mise à
  jour, et un écart est signalé par la veille.
- **Sous le niveau 60** : même étude (constante de niveau, rangs) sur son moteur Rust, puis le même principe de patchs
  (`forever/sims/patches/mythicsim/`). Il sert de second avis, sans moyenne entre les deux moteurs (décision 301).

### c) Calcul par tranche (`forever_simulate(action="brackets")`, `forever sims brackets`)
- **Entrées** : classe, spécialisation, race, parcours de talents, et une rotation par tranche si le préréglage ne
  convient pas.
  - Parcours de talents : un build avec ordre (Talents Forever, Polestar, `leveling_plan`), ou une liste collée comme
    celle de Maxroll.
- **Pour chaque tranche**, on simule un niveau représentatif (15, 25, 35, 45, 55, 60 ; ou chaque niveau, question 3).
  - **Talents** : le parcours tronqué au niveau L, légal au niveau L.
  - **Équipement** : choix de GearQuest obtenables au niveau L (`forever_gear(action="leveling")`). Option : ton
    équipement réel, par l'API Blizzard (`forever api character`), au niveau où tu es.
  - **Sorts** : rang appris au niveau L (patch), sorts non appris retirés.
  - **Cible** : monstre normal de niveau L, PV mesurés ou corrigés, certitude dite.
  - **Familier** : au niveau L, sa famille prise dans le réglage `pet_type`.
- **Sorties par tranche** :
  - DPS total, séparé entre le joueur et le familier ;
  - temps pour tuer le monstre de la tranche ;
  - XP par heure, avec le repos et la mana entre les combats repris de la route (aucune mécanique nouvelle) ;
  - écart type, et provenance avec le commit et les patchs.
- **Comparaison de parcours** : deux parcours de talents (par exemple Maxroll contre un build populaire), tranche par
  tranche, avec l'écart et « non départagé » sous deux écarts types (règle de MS1).

### d) Le Mage
- `forever_sim_leveling` et le moteur du Mage gelé (révision 7) **ne répondent plus** aux questions de dégâts : ils
  renvoient vers les tranches. Ils restent gelés pour la parité des tests, puis sont retirés après l'essai en jeu
  (décision 293 : le code redondant est retiré).
- Une seule voie pour toutes les classes : le Mage n'est plus un cas à part.

### e) Mesure et recoupement (ce qui rend les chiffres justes)
- **Tes journaux de combat de chaque tranche** sont l'étalon. Il faut activer le journal de combat avancé (l'addon
  Forever Logs Companion le fait) pour avoir équipement, talents et statistiques.
  - On les analyse hors du jeu : DPS du joueur et du familier, temps pour tuer, XP par heure.
  - On les compare à la simulation de la même tranche, avec le même équipement et les mêmes talents, lus dans le
    journal.
- **Écart au-delà du bruit** : il est consigné dans `docs/OPEN_QUESTIONS.md`, et le patch concerné est corrigé.
- **Certitude** : `suppose` tant qu'une tranche n'est pas mesurée, `probable` une fois recoupée par tes journaux.
- Les journaux publics (Warcraft Logs, foreverlogs.gg) servent de recoupement s'ils sont lisibles par programme
  (vérification au début de l'exécution).

### f) Tests (sans réseau, `tests/fixtures/`)
- Application des patchs sur un petit dépôt factice : un patch qui s'applique ; un patch qui échoue donne l'ancien
  binaire gardé et une carte de veille.
- Parcours de talents tronqué au niveau L : légal ; un point de trop est refusé.
- Requête par tranche : niveau, équipement, cible et talents écrits dans le `.siml` ; sortie lue (binaire factice).
- Conversion des talents vers MythicSim : ordre du commit actuel, plus le cas « arbre plus long » qui échoue
  aujourd'hui.
- Les tests de simulation réelle sont marqués `slow`.

### g) Documents
- `docs/DECISIONS.md`, décision 305 : correctifs locaux des simulateurs autorisés (demande du 2026-11-08), qui révise
  « compilé tel quel » des décisions 293 et 301 ; tranches de niveaux comme sortie par défaut d'un calcul ; foreverdb
  écarté ou non selon la question 1.
- `docs/ROADMAP.md` : SIM2 sort de l'attente ; CM1 et les tranches de classe s'appuient sur SIM2.
- `docs/MECHANICS_REGISTRY.yaml` : entrées « rang selon le niveau », « familier selon le niveau » et « statistiques de
  base selon le niveau », chacune avec sa source (fichier de wowsims et patch) et ses tests.
- Plugin (skills `forever-leveling`, `forever-mage`, routeur) : « calculer » = tranches ; plus de réponse de dégâts
  par le moteur gelé.

## 4. Ordre d'exécution
1. Réparer la traduction des talents vers MythicSim (rapide, débloque les deux moteurs au niveau 60).
2. Patch `level` et `ranks-mage` dans wowsims, puis Mage par tranche.
3. `ranks-hunter` et `pet-level`, puis Chasseur par tranche (parcours de Maxroll comparé au build populaire).
4. `base-stats` par niveau (`make db`, et mesures ForeverLogger).
5. Les sept autres classes, une à une (rangs par classe).
6. MythicSim sous le niveau 60 (même principe).
7. Essai en jeu, et retrait du moteur du Mage gelé.

## 5. Questions pour toi (avant l'exécution)
1. **foreverdb.net/sim** (règles de Classic là où le client se tait) : écarté, ou gardé comme simple recoupement
   `suppose` ?
2. **Attributs de base par niveau** (Agi, Int, Esp, puissance d'attaque de base) : les mesurer en jeu par ForeverLogger
   (personnage nu, une fois par niveau ; un relevé automatique à chaque montée de niveau suffit), ou partir des formules
   en commentaire dans wowsims (`2L−10` et `2L−20`, `suppose`) en attendant ?
3. **Une tranche = un niveau représentatif** (15, 25, 35, 45, 55, 60 : rapide) ou **la moyenne de chaque niveau de la
   tranche** (10 simulations par tranche : plus juste, environ 10 fois plus long) ?
4. **Proposer nos patchs aux mainteneurs** de wowsims (PR publique sur GitHub, sous ton compte) : oui ou non ? S'ils
   les intègrent, la maintenance passe chez eux.

## 6. Essai en jeu (décision 273)
- Avant : installer Forever Logs Companion, ou activer à la main le journal de combat avancé.
- Avec Rose-Krypto (Mage, niveau 22) : 15 minutes de quêtes en tranche 20-29 avec `/combatlog`, puis `uv run forever
  sims brackets --class Mage --spec Frost --level 22 --log <journal>`. Le DPS mesuré et le DPS simulé s'affichent côte
  à côte avec leur écart.
- Avec un Chasseur, dans une tranche au choix : même procédure ; le familier est mesuré à part.
- La tranche ne se ferme qu'avec ton accord.

## 7. Durée et dépendances
- Pas de nouvelle dépendance Python. Go, protoc et Rust sont déjà installés (Rust le 2026-11-08, avec ton accord).
- Réseau : seulement celui de `forever sims update` et de `forever update`, déjà autorisés. `make db` lit les fichiers
  du client par l'outillage de wowsims ; s'il demande un téléchargement, je m'arrête et je te demande.
- Gros chantier : étapes 1 à 3 (Mage et Chasseur) d'abord, livrables seules ; le reste suit, classe par classe.
