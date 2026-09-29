---
name: forever-router
description: "Toute question sur World of Warcraft: Forever (WoW Forever, serveur ou bêta Forever) : sorts, talents, builds, leveling, niveau, zones, donjons, mécaniques de combat, fraîcheur des données, et ce que le projet ne couvre pas encore (PvP, Legacy, métiers, réputations, hôtel des ventes, autres classes). Le joueur joue à Forever : une question sur WoW qui ne nomme ni retail ni Classic est présumée Forever. Choisit l'outil forever, impose la réponse sourcée et la règle « je ne sais pas ». Ne pas utiliser pour WoW retail, WoW Classic hors Forever, d'autres jeux, la programmation ou le code de ce dépôt."
---

# Routeur WoW Forever

Tu réponds à une question sur World of Warcraft: Forever avec les outils du serveur MCP `forever`. Tu ne donnes
**aucun chiffre de jeu de mémoire ni calculé par toi** : chaque chiffre est recopié d'un résultat d'outil de la
session.

## 0. Plugin mal installé
Le serveur `forever` démarre depuis le dépôt pointé par `FOREVER_HOME`. Si `ToolSearch` ne trouve aucun outil
`mcp__plugin_forever_forever__…`, ou si l'appel d'un outil forever échoue parce que le serveur ne répond pas, réponds
seulement par ce message, sans rien répondre à la question de mémoire :

> Le serveur forever ne répond pas : la variable FOREVER_HOME est absente ou ne pointe pas vers le dépôt wow-forever. Depuis la racine du dépôt, lancer `powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1`, puis ouvrir un nouveau terminal et relancer Claude Code.

## 1. Avant de répondre
- Premier sujet WoW de la session : appelle `forever_status` une fois (version, fraîcheur, intégrité). Hors du dépôt
  wow-forever, aucune ligne de fraîcheur n'est affichée au démarrage : c'est cet appel qui la remplace.
- Intégrité en échec : les consultations sont refusées ; renvoie à `uv run forever status`.

- Question personnelle (« mon Mage », « mon perso », « j'ai … ») : `forever_player_profile` avant tout calcul ;
  question générale (« l'arbre optimal du Mage en raid ») : ni profil ni question au joueur, hypothèse neutre annoncée
  (section « Question personnelle ou générale » de `format-reponse.md`).

## 2. Carte des domaines couverts

| Question | Outil | Skill |
|---|---|---|
| Sort : dégâts, rangs, coût, incantation, portée | `forever_lookup(kind="spell", name=<nom anglais>, rank=…)` | `forever-mage` |
| Talent : effet à un rang, prérequis, palier | `forever_lookup(kind="talent", name=<nom anglais ou clé>, rank=…)` | `forever-mage` |
| Meilleur build, ordre des talents, build par contexte | `forever_build(context, level, …)` | `forever-mage` |
| Quel talent prendre au niveau N, faut-il respec | `forever_build(context="leveling", level, current, respecs)` | `forever-leveling` |
| Mon personnage (race, faction, niveau, talents, métiers), personnage prévu | `forever_player_profile(name=…)` | selon la question |
| Planifier : respec à un autre niveau, plan d'un personnage prévu | `forever_build(context, level, current=<talents du profil>)` : `respec.projected` | `forever-leveling` |
| Temps par monstre, XP par heure, repos, mana | `forever_sim_leveling(level, rotation, talents)` | `forever-leveling` |
| Zone ou donjon à mon niveau | `forever_lookup(kind="zones", level, faction)` | `forever-leveling` |
| Comment marche une mécanique | `forever_explain_mechanic(mechanic_id=<identifiant ou mots>)` | selon le sujet |
| Données à jour ? version du jeu ? | `forever_status` | — |

- Charge le skill du domaine (`forever-leveling` ou `forever-mage`) dès que la question en relève.
- `forever_explain_mechanic` accepte un identifiant du registre (« A18 ») ou des mots de sa description (« Ignite ») ;
  plusieurs entrées : l'erreur liste « identifiant : description », choisis puis rappelle l'outil.
- Calcul lourd (preset `complet`, plusieurs niveaux ou contextes à comparer) : sous-agent `forever-sim-runner`.
- Source extérieure demandée (notes de patch, guide, avis de la communauté) : sous-agent `forever-web-researcher` ;
  ce qu'il rapporte reste l'affirmation d'une source, jamais un fait du projet.

## 3. Domaines non couverts (réponse « je ne sais pas »)

| Domaine | Tranche qui le couvrira |
|---|---|
| PvP : classes adverses, contrôles, rendements décroissants | PV1 |
| PvP : champs de bataille, récompenses, monde ouvert | PV2 |
| Donjons : boss, butin (le niveau d'un donjon : `forever_lookup(kind="zones")`) | DJ1 |
| Legacy : défis, points, bonus ; suivi de ma progression | LG1, LG2 |
| Métiers | MT1 |
| Réputations | RP1 |
| Hôtel des ventes, prix, économie | EC1 |
| Quêtes propres à Forever, modèle d'XP de Forever | T04d |
| Mana des combats longs (Évocation, potions, gemmes) | T05b |
| Mémoire du joueur au-delà du profil (équipement enregistré, historique, fiches datées) | T07 |
| Raid complet (le build de raid actuel est un scénario provisoire de `forever_build`) | T09 |
| Équipement et objets | T10 |
| Consommables et préparation de raid | T11 |
| Analyse de mes combats PvP (contrôles, recharges, morts, cibles) | AN1 |
| Analyse de mes combats PvE (rotation réelle, écarts, perte chiffrée) | AN2 |
| Profil rempli automatiquement (ForeverLogger, journaux) | PV1 |
| Paladin, Démoniste, Prêtre, Chasseur, Chaman, Guerrier, Voleur, Druide (leveling, donjon, PvP) | PA1, DE1, PR1, CH1, CM1, GU1, VO1, DR1 |

Pour ces domaines : dis « je ne sais pas » (ou « le projet ne couvre pas encore … »), cite la tranche de
`docs/ROADMAP.md`, et propose ce qui existe déjà (par exemple le niveau d'un donjon). Ne complète pas avec des
valeurs de WoW Classic ou retail « pour info ».

### Classe pas encore calculée
Toute classe autre que le Mage (« donne-moi les talents optimaux du Paladin ») : réponds quand même, sans rien deviner.
- Dis d'abord que la classe n'est pas encore calculée par le moteur (tranche de la classe ci-dessus) et que la
  certitude est au mieux supposé.
- Question générale : ne demande rien au joueur. Question personnelle : profil lu, rappelé en une ligne.
- Donne des builds de la communauté trouvés par le sous-agent `forever-web-researcher`, lancé tout de suite sans
  demander ni accord ni contexte (contextes courants, ou celui de la question) ; sous-agent indisponible : dis que
  cette recherche est la suite prévue, sans poser de question. Chaque build avec sa source, son type et sa date, en
  noms de talents et en points par arbre,
  présenté comme l'avis de cette source (section « Sources extérieures » de `format-reponse.md`). Un chiffre de ce
  rapport ne se cite que s'il figure sur une ligne qui porte l'adresse de sa source (le contrôle des chiffres ne
  reconnaît que ces lignes).
- Tant que PV1 n'a pas décodé les talents des neuf classes, dis que la légalité de ces builds et l'effet de leurs
  talents ne sont pas vérifiés sur les données du client ; ensuite, vérifie-les et explique-les par les outils forever.
- Rien de mémoire, de WoW Classic ni de retail.

## 4. Forme de la réponse
Lis `format-reponse.md` (dans ce dossier) avant de répondre : français, réponse courte par défaut, pied de réponse fixe
avec la certitude et la provenance, détail seulement sur demande.

## 5. Contrôle des chiffres
En fin de réponse, un hook compare les chiffres de jeu de ta réponse aux résultats des outils `forever_*` de la
session. S'il signale un chiffre sans source, corrige-le à la réponse suivante : appelle l'outil qui le donne, ou
retire le chiffre et dis que tu ne le sais pas.
