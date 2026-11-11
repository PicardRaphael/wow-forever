# SIM3 — Plans de classe à la demande, familier qui encaisse, recoupement par les journaux

Demande du 2026-11-11 (« améliore-toi ») après le plan Chasseur fait à la main : ce qui a été fait par scripts de
passage doit devenir calculable à la demande, et les angles morts du modèle de leveling doivent être fermés ou dits.

## Avant le chantier (décision 288)

- **Qui maintient déjà ça mieux que nous ?** Les calculs : wowsims/forever (simulateur, épinglé, recompilé par la
  veille). L'équipement obtenable : GearQuest Forever et Naowh Forever (addons installés). Les talents : Talents
  Forever. Nous n'écrivons aucune formule : seulement l'assemblage (candidats, essais, classement, export Naowh).
- **Que se passe-t-il au prochain patch ?** La veille recompile wowsims et relit les addons ; le plan se recalcule
  à la demande sur la nouvelle version (cache par version des données et commit de wowsims). Rien de figé.

## Blocs

### 1. `forever gear plan` : listes Naowh par tranche, calculées

`forever gear plan --class Hunter --race Orc --faction horde [--spec …]` (et `forever_gear(action="plan")`) :

- une liste `!NBIS1!` par tranche 10-19, 20-29, 30-39, 40-49, 50-59 (objectif leveling : XP par heure avec repos,
  `optimise_gear(objective="leveling")`), et au 60 deux listes séparées : raid-donjon (DPS, spé du meilleur raid)
  et BG (DPS, pièces PvP de rang de la faction en tête) ;
- par emplacement : l'objet en tête et jusqu'à 9 alternatives, chacune avec son gain simulé et son verdict ; un
  objet ne passe devant qu'au-delà du bruit (« meilleur ») ;
- candidats : choix de GearQuest et listes de Naowh obtenables au niveau, plus la base d'objets des simulateurs du
  niveau de la tranche ; filtres sourcés seulement (classe autorisée, type d'armure et d'arme lus dans la base,
  faction lue dans GearQuest et les sources, raids fermés lus dans `dungeons.json`/l'état du jeu), **aucun poids ni
  coefficient inventé** ;
- objets de raid exclus tant que les raids sont fermés : butin de raid, récompense de quête de raid, fabrication à
  composant de raid (composants lus dans les recettes du client) ;
- doublons interdits sur les paires (bagues, bijoux, arme à deux mains sans main gauche) ;
- gardé dans le cache, relu ; rapport court (gains, objets écartés et pourquoi).

### 2. Familier qui encaisse (objectif leveling, Chasseur et Démoniste)

Aujourd'hui le monstre frappe toujours le joueur. Vérifier dans le proto et le code de wowsims épinglé si un
familier peut être déclaré tank (référence d'unité de type familier) :

- si oui : au leveling, le familier tient le monstre (option par défaut pour les classes à familier), dégâts subis
  et repos du joueur en conséquence, vie du familier lue par la sonde ;
- sinon : le dire dans la provenance (angle mort) et ajouter la question dans `docs/OPEN_QUESTIONS.md`, sans
  modèle maison.

### 3. Recoupement par les journaux

`forever sims validate` sur un Chasseur dès que des journaux existent (pas encore : Jen-Krypto niveau 3). Ce bloc
écrit seulement la procédure et le test de bout en bout sur fixtures ; le recoupement réel attend les journaux.

## Tests (d'abord, rouges, committés)

- `gear plan` : une liste par tranche et deux au 60 ; 10 objets au plus par emplacement ; verdicts et gains
  présents ; paires sans doublon ; arme à deux mains sans main gauche ; objet de raid, de quête de raid ou à
  composant de raid écarté ; objet de l'autre faction écarté ; chaîne `!NBIS1!` relue identique ; cache relu.
- Familier tank (si wowsims le permet) : la requête de leveling déclare le familier tank ; dégâts subis du joueur
  nuls quand le familier tient ; sinon note d'angle mort dans la provenance.
- Aucun chiffre de jeu dans les tests (fixtures fabriquées).

## Registre et questions

- Registre : entrée pour l'objectif leveling avec familier (statut, source wowsims, tests).
- `docs/OPEN_QUESTIONS.md` : familier tank si wowsims ne le permet pas ; vie des familiers après le correctif du
  10 novembre (115 %) à relever en jeu.

## Essai en jeu (décision 273)

1. `uv run forever gear plan --class Hunter --race Orc --faction horde`, importer la liste 10-19 dans Naowh
   (fenêtre BiS → Import a list) : les objets s'affichent, aucun objet de l'autre faction.
2. Importer le code de talents de leveling (`!NFB1!`) : Naowh accepte et suit l'ordre.
3. Avec un Chasseur au leveling, garder un journal de combat ; `forever sims validate` compare le DPS mesuré au
   calcul de la tranche.
