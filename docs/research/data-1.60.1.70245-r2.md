# data: 1.60.1.70245 r1 → r2

Mesure du journal du 2026-10-07 sous le client 1.60.1.70245, par `forever measures refresh`, en session, **jeu
fermé** (décision 205 : aucun processus `WowB.exe`, journal non modifié depuis 11:20). Simulation montrée à
l'utilisateur, accords du 2026-10-07. Attente `measures-1.60.1.70245-b72cf86c140d` fermée (« mesure écrite en
session »).

- Première tentative annulée avant le commit : le journal avait grossi entre la simulation montrée et l'écriture
  (8 PNJ de plus, dont Polly qui fixait seule la valeur du niveau 50). Les données ont été remises à la révision 1 et
  l'instantané du cache renommé (`<cache>/measures/last.json.bak-20261007-1111`) pour que la mesure soit reproposée.
  D'où la règle du journal en cours d'écriture (décision 205).
- `WoWCombatLog-100726_080346.txt` : seul journal de 1.60.1.70245 (empreinte à l'écriture dans `revisions.json`).
- Journaux des versions antérieures : lus mais jamais écrits dans 70245 (décision 135) ; les PNJ des journaux
  disparus du dossier sont conservés.

| Fichier | Changement |
| --- | --- |
| monsters.json | 33 PNJ ajoutés, 7 changés (mesurés), 100 au total |
| monsters.json | `hp_by_level` : **aucune valeur changée** ; certitude du niveau 12 `certain` → `probable` (Sunscale Lashtail à 218 PV au niveau 12, sous les 272 des autres PNJ), niveau 15 `probable` → `certain` |
| monsters.json | `questie_correction` : ajustement inchangé (pente 0,0251, 16 niveaux mesurés, plage 1 à 24) |
| monsters.json | `curve_excluded` : 21 PNJ ajoutés (ci-dessous) |
| sources.json | source de `monsters.json`, révision 2 |
| revisions.json | révision 2 : commandes, journal et empreintes, 47 changements (46 mesurés, 1 écrit à la main) |

## PNJ ajoutés ou changés

- **Dans la courbe** (PNJ normaux) : Elder Mottled Boar, Bloodtalon Taillasher, Bloodtalon Scythemaw, Venomtail
  Scorpid, Lightning Hide, Corrupted Mottled Boar (Durotar) ; Sunscale Screecher, Razormane Mystic, Venture Co.
  Drudger, Southsea Brigand, Southsea Cannoneer, Hecklefang Hyena (les Tarides).
- **Changés** : Zhevra Runner (niveau 13 ajouté), Sunscale Lashtail (niveau 12 ajouté), Razormane Defender (niveau
  12 ajouté) ; Fleeting Plainstrider, Razormane Hunter, Razormane Geomancer, Savannah Prowler : mêmes niveaux et mêmes
  PV, individus du nouveau journal ajoutés à la source.

## PNJ écartés de la courbe (toujours mesurés un par un dans `npcs`)

- **Élites et élite rare de Questie** (écartés d'office, décision 186) : Ragefire Trogg, Ragefire Shaman, Earthborer,
  Molten Elemental, Searing Blade Cultist, Searing Blade Enforcer, Searing Blade Warlock, Oggleflint, Jergosh the
  Invoker, Bazzalan, Taragaman the Hungerer (Ragefire Chasm) ; Elder Mystic Razorsnout.
- **Élites probables de Forever** (accord du 2026-10-07) : Razormane Flesheater et Razormane Berserker, absents de
  Questie, PV doubles de la courbe à leur niveau (1042 et 1144 aux niveaux 18 et 19, contre 521 et 572).
- **PNJ nommés de quête** (décision 189, accord du 2026-10-07) : Polly (3600 au niveau 50, sans valeur Questie : elle
  aurait fixé seule la valeur du niveau 50, 5685 → 3600), Brewmaster Drohn, Tazan, Kreenig Snarlsnout, Baron
  Longshore (PV égaux à la courbe).
- **Démons de quête** (décisions 189 et 204, accord du 2026-10-07) : Summoned Voidwalker et Summoned Succubus.
  Le journal les montre contrôlés par le serveur (drapeaux `0xa28` : PNJ hostiles, sans propriétaire), combattus par
  un Démoniste et par son propre familier : ce ne sont pas des familiers de joueur, que la décision 204 écarte d'office.
- **Candidats proposés, non écartés** : Burning Blade Toxicologist et Burning Blade Crusher (PNJ d'événement, PV de la
  courbe, comme en révision 5 de 1.60.1.70170).

## Effet sur les builds du Mage

Rejeu des 16 cas de `scripts/replay_builds.py` (`m70245-r2` contre `m70245-avant`, données de la révision 1) :
**aucune recommandation changée**, talents, ordre et mesures identiques dans les 16 cas (la courbe des PV par niveau,
seule entrée du moteur qui bouge d'habitude, n'a pas changé). Détail : `docs/research/builds-T05.md`, section
« Rejeu 1.60.1.70245 révision 2 ».
