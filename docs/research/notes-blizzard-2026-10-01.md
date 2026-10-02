# Notes de développement de Blizzard du 01/10/2026 : lecture et recoupement avec le client 1.60.1.70170

Relevé le 2026-10-02, à la demande de l'utilisateur. Pour chaque changement de la note : (a) visible dans les tables
du client 1.60.1.70170 (vérifié), (b) passé par un correctif du serveur (`Logs/Hotfix.log`), ou (c) règle du serveur
absente des données lues. Le texte du forum est sous licence CC BY-NC-SA 3.0 : il est paraphrasé ici, jamais recopié.

## Source
- Sujet officiel « WoW Forever Beta Development Notes – Updated October 1 » (Kaivax, Community Manager), forum de
  Blizzard : <https://us.forums.blizzard.com/en/wow/t/2360696>.
- **Message n° 4** : créé le 2026-10-01 à 22:56:04 UTC, **révision 4** du 2026-10-02 à 02:55:30 UTC :
  <https://us.forums.blizzard.com/en/wow/t/2360696/4>. C'est la provenance retenue partout dans le dépôt
  (« t/2360696/4, révision 4 »).
- Le lien donné par l'utilisateur (`/2360696/3`) mène à ce message : les n° 2 et 3, créés le 24/09 à 22:27 UTC par le
  même auteur, sont vides (texte de longueur nulle, version 1, ni masqués ni supprimés selon le JSON), et Discourse
  affiche le message suivant. Le n° 1 (notes du 24/09, révisé le 01/10, version 2) est déjà recoupé dans
  `notes-blizzard-2026-09-24.md`.
- Lecture : `uv run forever notes --post 2360696/4` (lecture ciblée ajoutée le 2026-10-02 : `robots.txt` puis le JSON
  du sujet, message de joueur refusé, texte rendu pour la lecture seulement), lancée à la main avec l'accord réseau de
  l'utilisateur ; une relecture de diagnostic du même JSON a établi la liste des messages.

## Version concernée : 1.60.1.70170 (probable)
La note annonce un nouveau build mis en ligne « aujourd'hui » (01/10). 1.60.1.70170 a été publié sur wago.tools le
2026-10-01 à 22:54 UTC (décision 167), deux minutes avant le message. Les changements du Mage sont tous visibles dans
les tables de 70170 et absents de celles de 70124 (Heating Up, Combustion à 3 charges : installés en révision 1). Les
talents du Guerrier sont absents des tables de 70170 mais présents dans les correctifs du serveur du 2026-10-02 : ils
sont arrivés par correctif après le build.

## Méthode
- (a) : comparaison des tables de wago.tools en cache, 1.60.1.70124 contre 1.60.1.70170 (`Spell*`, `Trait*`, et
  `CurvePoint` relié aux rangs par `TraitDefinitionEffectPoints`), ligne par ligne, reliée aux noms des sorts.
- (b) : journal des correctifs du cache (`forever hotfixes`, `Logs/Hotfix.log`) relié aux sorts et talents par les
  tables de 70170. Les **valeurs** corrigées sont dans `DBCache.bin`, non décodé (tranche T08c) : seules les lignes
  touchées sont connues.
- Sens des bits d'attributs (`SpellMisc.Attributes_*`) : définitions communautaires des émulateurs (noms de
  TrinityCore et CMaNGOS), non vérifiées dans le client : `probable`. Bits relevés : `Attributes_3` bit 18 (« le sort
  ne peut pas rater »), `Attributes_6` bit 23 (« marque la cible aussitôt »), `Attributes_8` bit 9 (« les effets
  périodiques peuvent être critiques »). Aura 77 : immunité à une mécanique, valeur 3 : désarmement.

## Changements touchant le Mage et le moteur
| Changement (paraphrase) | Classe | Preuve | Moteur | Tranche |
| --- | --- | --- | --- | --- |
| Hot Streak renommé Heating Up | (a) | `SpellName` 400624 et 400625, icône changée ; installé en révision 1 (décision 165) | Clé `hotStreak` gardée | Fait |
| Combustion revient à 3 charges | (a) | `SpellAuraOptions.ProcCharges` de 11129 : 4 → 3 ; installé en révision 1 | Combustion non modélisée (B18) | T09 (B18) |
| Fire Vulnerability (Improved Scorch) sans second jet de résistance | (a) | `Attributes_3` de 22959 : bit 18 ajouté | Fire Vulnerability hors des rotations (I8) ; Givre-feu compté feu (A20) | T09 (I8) |
| Winter's Chill sans jet de résistance (le sort qui le pose a déjà dû toucher) | (a) | `Attributes_3` de 12579 : bit 18 ajouté | **Concordance** : le Monte Carlo pose Winter's Chill seulement sur un sort qui touche (`on_impact` s'arrête sur un sort raté), un seul tirage à la chance du talent (`forever/sim/leveling_mc.py`) | Aucune |
| Parchemins du Mage (Comprehension) : nouvel équilibrage, plus d'incantation en mouvement | (a) partiel | `SpellInterrupts.InterruptFlags` 31 → 15 sur Comprehension (435563) et des sorts voisins (familiers, Polymorph, Minor Evocation…) ; le bit de mouvement est présent avant et après : sens du changement non établi | Non modélisé | Hors périmètre (aucune tranche ne porte ces parchemins) |
| Les rangs très inférieurs au niveau du personnage profitent moins de la puissance des sorts (pénalité E2) | (c) | Texte de l'infobulle de la fiche du personnage, absent des tables lues ; aucune formule donnée | Pénalité Classic déjà appliquée par défaut (`coefficient.low_level_default`) ; **existence** confirmée (probable), **formule** à mesurer (E2) | Mesure en jeu (protocole E2 de `docs/ADDON.md`) |
| Les mêmes rangs ont une chance réduite de déclencher les effets de classe et de talents (exemples : Frostbite, Omen of Clarity ; Frostbolt rang 1 au niveau 60 ne déclenche jamais Frostbite) | (c) | Même source ; aucune table lue ne porte la réduction | **Nouvelle mécanique**, registre B20 (`absent`, probable). Le moteur prend toujours le rang le plus haut (`best_rank`) : sans effet sur le leveling et les builds actuels | La première tranche dont une rotation descend de rang : T05b (rangs bas pour la mana) ; AN1 (Frostbolt rang 1 en PvP) |
| Plafond de niveau à 30 | (c) | Installé depuis l'observation de l'utilisateur (`meta.json` `game_state`, décision 166) ; la note en est la source officielle | Aucun | Fait |

## Autres classes et races (savoir du client, sans moteur)
| Changement (paraphrase) | Classe | Preuve | Tranche |
| --- | --- | --- | --- |
| Druide : formes d'ours, rage accrue sur un coup critique | (a) | Bear Form (Passive) 1178 et Dire Bear Form (Passive) 9635 : nouvel effet déclenché sur critique (`SpellAuraOptions`, chance 100) ; nouvel effet d'aura 668 sur 5487 et 9634 | DR1 |
| Druide : Swipe gagne une part de la puissance d'attaque | (c) | Aucun changement dans les tables (la note dit l'infobulle pas encore à jour) | DR1 |
| Druide : Tiger's Fury et King of the Jungle retirés ; nouveau talent Shifting Power, puis Improved Shifting Power | (a) | `TraitDefinition` 134412 : sort 417046 → 1322605 ; Shifting Power (recharge 16 s, coût 55 % de la mana de base, 40 d'énergie, forme de félin) ; Improved Shifting Power (2 rangs, arête depuis Shifting Power) ; courbe de King of the Jungle retirée | DR1 |
| Druide : toutes les formes immunisées au désarmement | (a) | Aura 77, valeur 3, ajoutée aux passifs des formes (félin 3025, ours 1178, ours redoutable 9635, voyage 5419, aquatique 5421, sélénien 24905) | DR1 ; fiches PvP (PV1) au prochain décodage |
| Druide : Faerie Fire ne remet plus à zéro le temps d'attaque | (a) partiel | Lignes `SpellInterrupts` de 770, 778, 9749, 9907 retirées : sens probable | DR1 |
| Druide : menace de Primal Bite à peu près doublée | (c) | Infobulle seule changée (« beaucoup de menace ») ; menace au serveur | DR1 |
| Chasseur : icônes d'Improved Stings et de Predator's Edge | (a) | `SpellMisc.SpellIconFileDataID` | — |
| Chasseur : Sniper Shot à 45 m, portée des 3 tirs suivants +10 m pendant 10 s | (a) | `RangeIndex` 114 → 582, nouvelle aura (3 charges, +10) | CH1 |
| Chasseur : parade de Deflection 1/2/3/4/5 % (au lieu de 2/4/6/8/10 %) | (a) | Courbe du talent 19295 | CH1 |
| Chasseur : mode agressif du familier rétabli | (c) | Interface, aucune table lue | CH1 |
| Chasseur : des bêtes apprivoisables enseignaient des rangs de capacités trop élevés pour leur niveau, toutes corrigées (risque d'un familier qui « oublie » une capacité) | (c) | Données des créatures au serveur, absentes du client lu ; **postérieur à la base de Forever Bestiary installée (0.5.0, base du 2026-09-25)** | CH0 : signal dans le guide d'apprivoisement (`pet_rules.json`, révision 3) ; CH1 |
| Paladin : blocage de Redoubt 4/8/12/16/20 % (au lieu de 6/12/18/24/30 %) | (a) | Courbe du talent 20127 | PA1 |
| Paladin : blocage de Holy Shield 30 % (au lieu de 20 %) | (a) | `SpellEffect` de 20925, 20927, 20928 : 20 → 30 | PA1 |
| Paladin : Champion of the Light 20/40/60 % de l'Intelligence (au lieu de 33/66/100 %), soins retirés de l'infobulle | (a) | Courbe du talent 1311084 ; effet de soins retiré (`SpellEffect` 1341130) | PA1 |
| Prêtre : Devouring Plague peut être critique | (a) | `Attributes_8` bit 9 ajouté sur les 6 rangs | PR1 |
| Prêtre : Shadow Word: Death ne profite plus toujours d'Early Demise | (c) | Correction du serveur ; infobulle seule retouchée | PR1 |
| Prêtre : Inner Focus ne donne plus de critique aux effets périodiques | (a) | Masque de classe de 14751 | PR1 |
| Prêtre : Shadow Weaving ne peut plus échouer | (a) | `Attributes_3` de 15258 : bit 18 ajouté (même bit que Winter's Chill) | PR1 |
| Voleur : un Expose Armor raté ne fait plus perdre les points de combo | (a) partiel | `Attributes_1` et `Attributes_4` des 5 rangs : sens non établi | VO1 |
| Voleur : Setup seulement sur la cible esquivée ou résistée | (a) | `SpellEffect` de 13983 : aura 42 → 4 ; infobulle | VO1 |
| Chaman : Ghost Wolf plus visible | — | Rendu graphique, hors données | — |
| Chaman : durée de Disease Cleansing Totem à 5 min ; Totemic Recall rend la mana | (a) | `DurationIndex` de 8170 : 4 → 5 ; nouveau sort 1323420 (part de la mana des totems rendue) | CM1 |
| Démoniste : Drain Soul interrompu par une autre incantation ; Hellfire peut être critique ; Soul Harvesting renommé Soul Harvest, régénération corrigée | (a) | `ChannelInterruptFlags` des rangs de Drain Soul ; `Attributes_8` bit 9 sur Hellfire Effect ; `SpellName` 437032, effet de 1242853 (aura 379 → 110) | DE1 |
| Démoniste : modèle de l'Incubus ; mode agressif du familier | — / (c) | Rendu ; interface | — |
| Guerrier : rage +75 % sur un coup critique d'une attaque de base, puis +100 % | (a) puis (b) | Nouveau sort « Rule of Rage (DND) » 1322574 dans 70170 ; son effet 1358385 corrigé par le serveur le 2026-10-02 | GU1 |
| Guerrier : Rend et Sunder Armor marquent aussitôt la cible | (a) | `Attributes_6` bit 23 ajouté sur tous les rangs | GU1 |
| Guerrier : Heroic Strike en file n'augmente plus le toucher de la main gauche | (c) | Règle du serveur | GU1 |
| Guerrier : bug de Dual Wield Specialization (toucher sur les deux armes) corrigé, rage de la main gauche retirée | (a) et (b) | Courbe 2/4/6/8/10 au lieu de 20…100 et effet de rage retiré dans 70170 ; effet 1315028 et points de talent 25094 et 25099 corrigés le 2026-10-02 | GU1 |
| Guerrier, Armes : Spearing Strike sans arme à deux mains, en posture de combat | (a) | `SpellShapeshift` ajouté au sort 1310222 | GU1 |
| Guerrier, Fureur : Booming Voice, Unbridled Wrath, Blood Craze, Raging Blows, Whirlwind, Bloodthirst (45 % de la puissance d'attaque), Berserker Rage au niveau 30 ; nouveaux talents Lingering Rage, Furious Precision, Gore Drinker ; Improved Cleave et Boundless Rage retirés ; Flurry exige Death Wish au lieu d'Enrage ; Improved Berserker Rage en rangée 5 | (b) | `Hotfix.log` du 2026-10-02 : `Spell`, `SpellName`, `SpellEffect`, `SpellAuraOptions`, `SpellClassOptions`, `SpellLevels`, `SpellMisc`, `Trait*` ; sorts 1323963 à 1323969 absents des tables (ajoutés par le serveur) ; arêtes Enrage → Flurry et Death Wish → Bloodthirst supprimées. Unbridled Wrath : chance 60 → 100 déjà dans 70170, puis corrigé | GU1 ; valeurs : T08c |
| Guerrier, Protection : Iron Will, Anticipation, Improved Bloodrage, Improved Revenge, Improved Disarm, Improved Shield Bash déplacés ; Toughness retiré | (b) | `TraitNode`, `TraitDefinition` (Iron Will), `TraitDefinitionEffectPoints` du 2026-10-02 | GU1 ; valeurs : T08c |
| Gnome : Eureka! ne profite plus aux effets périodiques | (a) | Masques de classe et descriptions (« non périodique ») des sorts 1259812 à 1259823 | Raciaux (G1, PV1) au prochain décodage |
| Mort-vivant : Cannibalize impossible sous immunité aux dégâts physiques | (c) | Règle du serveur | PV1 (racial) |

## Monde, quêtes, PvP, divers
| Changement (paraphrase) | Classe | Preuve | Tranche |
| --- | --- | --- | --- |
| Nouveau donjon Excavation Site: Wetlands (26-31) ; Razorfen Downs (25+) et Uldaman (30+) ouverts, en plus des onze donjons déjà ouverts | (c) | Tables de cartes et de donjons non téléchargées | DJ1 (niveaux d'accès à reprendre) |
| Quêtes de donjon : bonus d'XP au-delà de la valeur normale réduit de 50 % ; récompenses de certaines quêtes recalibrées | (c) | Règle du serveur | T04d (modèle d'XP des quêtes), DJ1 (quêtes de donjon) ; registre I9 |
| PvP : coûts en honneur de l'équipement et des jetons relevés d'environ 50 % ; plafond d'honneur de 15 000 à 25 000 | (c) | Coûts et plafond portés par des tables non téléchargées (coûts étendus des objets, monnaies) | PV2 (récompenses et équipement PvP), LG2 (suivi de l'honneur), EC1 ; registre K6 |
| Réapparition plus rapide dans plusieurs zones (Hillsbrad, Ashenvale, Wetlands, Duskwood, Thousand Needles) et corrections de quêtes | (c) | Serveur | Angle mort de I6 (réapparition non modélisée) |
| Camping : icône et infobulle de Boosted Rest ; les feux de camp ne blessent plus sous le niveau 5 et blessent moins sous 90 % de vie | (a) / (c) | `SpellMisc` et texte de 1229451 ; dégâts du feu au serveur | D5 (buffs de campement), non modélisé |
| Torche du Night Watchman (latence, impossible à annuler) | (b) | `Hotfix.log` du 2026-10-01 : `Spell`, `SpellName`, `SpellMisc` de 1309410 | — |
| Objets : Savory Whimsyfin Delight, objets liés quand on les vend sans en avoir l'apparence | (c) | Serveur | — |
| Métiers (Windshaper Skyborne, recettes, baguettes, filons, dépeçage une seule fois) | (c) | Serveur | MT1 |
| Graphismes, interface, manette, gestionnaire de recharges, salons de coiffure | — | Hors données de jeu | — |

## Problèmes connus nouveaux dans ce build (bugs reconnus : jamais modélisés)
Liste de la même note, section « Known Issues - New to this build ». Retenus pour le projet :
- Les ennemis parent et bloquent de dos si le joueur est trop près : à ne pas modéliser dans la table d'attaque de
  mêlée (PA1, GU1, VO1, A1).
- Eureka! ne touche pas tous les sorts de dégâts ou de soins de certaines classes (G1) : ne pas modéliser l'écart.
- Faerie Fire et Demoralizing Shout ne génèrent pas de menace (H9) : ne pas modéliser.
- Dual Wield Specialization donne encore le toucher aux deux mains, alors que la section « Fixed » du même message
  le dit corrigé : **contradiction interne**. La règle voulue (main gauche seulement) reste la référence ; le bug n'est
  pas modélisé (GU1).
- Retribution Aura prend la puissance des sorts de la cible au lieu de celle du Paladin (PA1) : ne pas modéliser.
- Accès à Research bloqué pour certains Mages : sans effet sur le moteur.

## Suites dans le dépôt
- Registre : G4 (existence de la pénalité, formule à mesurer), D4 (Winter's Chill sans jet de résistance,
  concordance), A20 et I8 (Fire Vulnerability), L1 et L3 (rangs des bêtes corrigés après Forever Bestiary 0.5.0) ;
  nouvelles entrées B20 (chance de déclenchement réduite pour un rang bas), I9 (XP des quêtes de donjon), K6
  (honneur : coûts et plafond), toutes `absent`, `probable`.
- Données (révision 3 de 1.60.1.70170, à la main) : certitude de `coefficient.low_level_default` (existence de la
  pénalité) relevée à `probable` avec cette note pour source ; correctif officiel des rangs enseignés par les bêtes
  ajouté à `pet_rules.json`, lu par le guide d'apprivoisement pour signaler une base de Forever Bestiary antérieure.
- `docs/OPEN_QUESTIONS.md` : E2, Winter's Chill, Fire Vulnerability, XP des quêtes, honneur, plafond de niveau,
  familiers mis à jour avec cette source.
- ROADMAP : DJ1 (donjons et niveaux d'accès), PV2 (honneur), LG1 (plafond de niveau désormais dans une note
  officielle) ; tranche T08c (décodage de `DBCache.bin`) pour lire les valeurs des correctifs du Guerrier.
