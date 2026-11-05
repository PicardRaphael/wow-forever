---
name: forever-builds
description: "Builds de talents de WoW Forever pour les 9 classes (Mage, Paladin, Démoniste, Prêtre, Chasseur, Chaman, Guerrier, Voleur, Druide) : builds populaires de Talents Forever et builds de la communauté vérifiés sur les données du client (légalité, paliers, prérequis, effet des talents), build le plus proche de mes talents, lien Talents Forever et code Naowh. Déclencher pour « meilleur build Paladin », « ce build de Voleur est-il légal », « que fait ce talent de Druide ». Pas pour WoW retail ni WoW Classic hors Forever, ni la programmation."
---

# Builds (WoW Forever, 9 classes)

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé », forme de la réponse, règle
« je ne sais pas ». Aucun chiffre de mémoire : tout vient des outils forever.

## Noms du client

Le joueur lit les noms dans son client : sa langue est `game_locale`, rendue par `forever_player_profile`. Cite
chaque sort, talent, capacité, objet et zone **tel qu'il apparaît dans son client** (en anglais pour `enUS`), suivi du
nom français entre parenthèses quand l'outil le rend (`name_fr`, `name.fr`) ; le reste de la réponse reste en
français. Sans `game_locale` connue, cite le nom anglais du client et le nom français entre parenthèses.

## Toutes les classes, Mage compris : builds de la communauté vérifiés
- Le build du Mage n'est plus calculé (décision 299) : il suit le même chemin que les autres classes. Ordre des
  talents, prochain talent ou respec demandés : dis que ce n'est plus calculé (choix de joueurs de Talents Forever ;
  ordre de prise généré par palier et prérequis, pas optimisé), puis donne `closest`.
- Au niveau 60, `forever_simulate` (wowsims/forever) calcule les dégâts, races et poids de toutes les classes.
  Depuis la décision 301, au 60 seulement : un build choisi se mesure par `action="compare"` avec `talents`
  (« clé=rang,… », légalité contrôlée, talent sans correspondance chez le moteur refusé en le nommant), par les deux
  moteurs avec `engine="both"` (MythicSim en recoupement, Mage et Chaman : deux colonnes et leur écart, jamais de
  moyenne) ; `action="builds"` cherche un meilleur build depuis le préréglage, tes talents et les builds
  populaires (verdict « meilleur » ou « non départagé » : dis-le tel quel, avec le seuil). Cite le moteur, son commit
  et sa date de mise à jour (`committed_at`) ; rotation et équipement du préréglage sont gardés : dis-le. Sous
  le 60, aucun calcul chiffré du build (tranche SIM2, le Chaman d'abord : CM1 ; Mage : temps par monstre et XP/h du
  moteur gelé seulement, skill `forever-leveling`) : dis-le, certitude au mieux supposé pour le choix du build.
- Question personnelle : `forever_player_profile` d'abord (classe, niveau, talents du profil) ; question générale :
  rien à demander, hypothèse neutre annoncée.
- Chaque build populaire et chaque contrôle `build_check` légal portent aussi `naowh` (code `!NFB1!`, ordre
  généré) : donne-le à côté du lien Talents Forever, tel quel.
- Macros de la classe ou profil EllesmereUI demandés : `forever_lookup(kind="export", name="naowh_macros")` (avec
  `class_name`, `level`) ou `name="ellesmere"` (avec `character`, `realm`, `class_name`, `level`, `role`) ; recopie
  `code` et `import` tels quels, certitude supposé (choix de catalogue).
- Guide de la classe (plan « Sources d'abord ») : `forever_lookup(kind="class_guide", name=<classe>,
  level=<niveau>)` rend le guide de Forever Companion : par spécialisation, le build adapté au niveau (`pick`, légal à
  son niveau ou non), les builds écartés avec leur raison (`set_aside`) et la rotation en prose (`rotation.single`,
  `rotation.aoe`, écrite pour le niveau 30) ; dis que l'ordre de prise n'est pas calculé ; `freshness.status` autre que
  « à jour » : « calcul en cours de mise à jour » et sa raison ; `available` faux : addon absent, dis-le.
- Ordre de leveling niveau par niveau d'une spécialisation : `forever_lookup(kind="leveling_plan", name=<classe>[, class_name=<spé>, level=<niveau>])` (LV1, décision 303) (tranches, `next`, code `naowh` à
  importer et suivre dans Naowh) ; points `genere` et écarts de Polestar dits tels quels.
- Builds populaires de Talents Forever d'abord : `forever_lookup(kind="tf_popular", name=<classe>)` (addon lu sur
  disque) : part de chaque spécialisation, date `asOf` et fenêtre, puis chaque build avec son lien, sa commande
  `import` et sa légalité déjà contrôlée sur le client (`légal`, `illégal`, ou `non vérifiable` avec le talent
  sans correspondance nommé). Certitude supposé (choix de joueurs) ; cite la date. Addon absent : dis-le.
- Question personnelle avec les talents actuels connus (profil, ou contexte du jeu) : ajoute
  `current=<clé=rang,…>` ; l'outil rend `closest`, le build populaire le plus proche (même spécialisation, points
  absents `missing_points`, écarts `differences`) : donne-le tel quel, n'en choisis pas un autre ; `closest` vide :
  aucun point placé, prends le build le plus joué (rang 1).
- Builds de la communauté en plus (ou addon absent) : sous-agent `forever-web-researcher`, chaque build avec sa
  source, son type et sa date, présenté comme l'avis de cette source (section « Sources extérieures » de
  `format-reponse.md`).
- Vérifie chaque build : `forever_lookup(kind="build_check", name=<classe>, level=<niveau>,
  talents=<clé=rang,…>)` rend légal ou la liste des erreurs (paliers, prérequis, rangs, points au niveau) et la
  description des talents du client. Un build illégal se dit tel, avec les erreurs de l'outil.
- Effet d'un talent : `forever_lookup(kind="talent", name=<nom anglais ou clé>, class_name=<classe>)` : arbre,
  palier, prérequis, description du client (valeurs par rang non décodées hors du Mage : dis-le ; talent du Mage :
  skill `forever-mage`).
- Palier communautaire (probable) ou légalité non décidable (nœud hors grille) : répète ce que dit l'outil.

## Hors de ce skill
- PvP d'une classe (contrôles, défensifs, affrontement) : skill `forever-pvp`.
- Dégâts, rotations et leveling sous le 60 des classes autres que le Mage : « je ne sais pas » + tranche SIM2.
