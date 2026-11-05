# Plan LV1 — Talents de leveling niveau par niveau (2026-11-05, validé : « oui fais tout »)

Demande (2026-11-05) : « de tel à tel niveau tu fais ça, ensuite tu reset », « à la perfection », avec les addons de
talents du joueur : **Naowh Forever** et **Talents Forever** (« moi pour talent on a naowh forever et talent forever »).
Révision du premier plan (centré sur Sharpie's Gear Judge Talents, que le joueur n'a pas) : Sharpie n'est plus
qu'un recoupement facultatif.

## 1. Les deux questions (décision 288)
- **Qui maintient déjà ça mieux que nous ?**
  - **Talents Forever** (installé) : builds les plus joués par spécialisation, relevés du jour (0.38.16, relevé du
    2026-11-05 sur 70755), contrôlés sur notre client. Pas d'ordre de prise.
  - **Polestar** (installé, `Polestar/Talents/Builds.lua`) : un point par niveau de 10 à 60 et des notes, pour les
    3 spécialisations des 9 classes. Écrit sur la bêta 70450 (`checkedOn`, en-tête du fichier), pas revérifié au
    commit 86a4c222 du 2026-11-05 : relevé du jour sur 70790 : Chaman Amélioration et Restauration entiers,
    Élémentaire cassé au point 21 (Lava Burst retiré), Mage cassé dans les trois spécialisations (Givre au point 11).
  - **Naowh Forever** (installé) : onglet Builds, suit un build point par point en jeu (« Follow ») ; aucun build
    livré dans cette version, aucun build du joueur. Le projet sait déjà écrire son code `!NFB1!` (EX1).
  - Sharpie's Gear Judge Talents : non installé ; recoupement facultatif seulement.
  - wowsims, MythicSim : niveau 60 seulement.
- **Que se passe-t-il au prochain patch ?** Talents Forever se met à jour seul (relevés quotidiens) ; Polestar
  quand ses auteurs le revérifient ; nous relisons les deux fichiers à chaque appel et contrôlons chaque point sur le
  client installé : un talent retiré ou un nœud réaffecté est signalé, jamais suivi. Aucun calcul de rendement à nous
  (décisions 293 et 299).

## 2. Ce qui change
### a) Lecteur Polestar (décision 272)
- `forever/polestar_talents.py` : lecture locale de `Interface/AddOns/Polestar/Talents/Builds.lua` (analyseur
  `lua_table`, aucun Lua exécuté) : par classe, résumé, source, version du client d'écriture (en-tête), builds
  (clé, spécialisation, répartition, points dans l'ordre, notes par niveau), table des nœuds (sort, nom).
- Chaque point relié à nos clés **par le nom du talent dans la classe** (pas par le nœud : Blizzard réutilise des
  nœuds, Primal Bite a pris celui de Berserk). Nom absent du client : « talent absent du client », point écarté.
  Nœud de Polestar qui porte aujourd'hui un autre talent : dit (« nœud réaffecté »).

### b) Plan de leveling (`forever_lookup(kind="leveling_plan", name=<classe>, class_name=<spé>, level=…)`, CLI
`forever talents plan`)
- **Build visé** : le build populaire de Talents Forever le plus joué de la spécialisation, légal sur le client ; à
  défaut, celui de Polestar s'il est entier.
- **Ordre** : celui de Polestar tant que le point suivant est dans le build visé et légal ; sinon point généré légal
  (moteur existant, `forever/engine/talents.py`), marqué `genere`. Chaque point dit sa source.
- **Tranches** : « niveaux A–B : talent, rangs » ; niveau d'un point = premier niveau de talent des données
  (`mechanics.json`), un point par niveau. Notes de Polestar reprises à leur niveau si le point est le même.
- **Naowh** : code `!NFB1!` de cet ordre (`order_source="leveling"`), à coller dans `/nftraining`, Builds, Import,
  puis Follow.
- **Resets** : aucun inventé. Aucune source n'en donne : dit tel quel, avec ce que disent les données
  (`respec.json`, relevés de la bêta, `suppose`) et la double spécialisation (prix inconnu, question ouverte).
- Provenance : versions de Polestar et de Talents Forever, version d'écriture de Polestar contre le client, certitude
  `suppose` (choix de joueurs et ordre d'un guide), écarts nommés.

### c) Tests (d'abord, sans réseau)
- `tests/fixtures/addons/Polestar/Talents/Builds.lua` synthétique (même forme, talents des fixtures).
- Lecture ; point → niveau ; talent absent ; nœud réaffecté ; fusion avec le build visé (ordre Polestar gardé,
  points générés marqués) ; tranches ; code Naowh ; provenance ; MCP et CLI.

### d) Documents
- Décision 303 ; `docs/DATA_SOURCES.md` ; skills `forever-leveling`, `forever-builds`, routeur ; plugin 0.22.2 ;
  `docs/OPEN_QUESTIONS.md` : prix du reset et de la double spécialisation dans la version finale.

## 3. Essai en jeu (décision 273)
- Coller le code `!NFB1!` du plan Chaman Amélioration dans `/nftraining`, Builds, Import ; Follow : le talent annoncé
  au prochain niveau est celui du plan.
- Chez le maître de classe : prix du premier reset ; double spécialisation proposée ou non, et son prix.

## 4. Hors de portée (dit)
- « Parfait » au sens d'un calcul : aucun moteur de leveling ouvert pour Forever sous le 60. Le plan est le meilleur
  avis sourcé disponible (joueurs + guide), contrôlé sur le client.
