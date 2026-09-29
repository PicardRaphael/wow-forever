# T05 — état d'avancement (reprise de session)

Branche `t05`. Un cycle rouge → vert par bloc ; demandes de correction regroupées dans `tasks/T05-corrections.md`.

## Blocs
- A1 (documentation) : fait, `18687bf`.
- A2 (données : recharges des talents actifs, `respec.json` chargé, `build.*`, `respec.*`) : vert, `a0062cc`.
- B (hypothèses pilotées par les données, variantes, notes de Blizzard du 24/09/2026) : vert, `d405274`. Lecture des notes : `docs/research/notes-blizzard-2026-09-24.md`.
- C (Arcane Power, Hot Streak, Missile Barrage, portées) : implémenté, `5fc91eb` ; **un test verrouillé en attente de correction** (`test_pyroblast_enters_the_fire_rotation_after_enough_crits`, voir corrections n° 1) ; `tasks/.rouge` le garde.
- D (mc_stats, écart apparié, décision, stabilité) : vert, `9dec4c5`.
- E (scénarios provisoires : `forever/sim/encounter.py`, règles dans `forever/engine/encounter.py`) : vert. Analytique à ≤ 1,5 % du Monte Carlo au niveau 40 (Fire Blast à période arrondie aux incantations, rotation arcane déroulée lancer par lancer).
- F (optimiseur : `forever/optimize/leveling.py`, parité exacte avec le seed ; `forever/optimize/endgame.py`) : implémenté ; **un test verrouillé en attente de correction** (`test_talented_bonus_adds_legal_points`, corrections n° 2). Défaut de l'analytique du bloc E corrigé au passage (rotation à une cible sur un paquet), avec son test.
- G (profil PvP porté, parité exacte ; contextes pvp-bg et pvp-world) : vert.
- H (respec : parité exacte avec le seed ; conseil forever par niveau) : vert.
- I à K : à faire (ordre du plan).

## Constats à reporter (angles morts, rapport final, bloc J/K)
- **Arcane Power, politique « au pull » (D1)** : au Monte Carlo, l'aura couvre les lancers qui finissent dans ses 15 s ; en rotation arcane, la décharge Arcane Missiles finit vers 16 s et n'en profite pas, les Arcane Blast de montée en profitent. Niveau 40, build Arcanes 31 points, décharge Arcane Missiles, n = 600 : temps par monstre 73,45 s (auto) contre 72,71 s (off) au Monte Carlo (graine 7 ; 73,14 contre 72,21 graine 8) : le surcoût de mana (+5 %) l'emporte. L'analytique, à dégâts uniformes, donne l'inverse (66,51 contre 67,92) : **l'analytique surestime Arcane Power en leveling** ; la décision revient au Monte Carlo. Angle mort : un joueur lance Arcane Power juste avant la décharge (sous-évalue Arcane Power en rotation arcane).
- **Hot Streak en leveling au niveau 25** (critique de base) : à 3 cumuls, Pyroblast presque jamais lancé (combats de ~18 s) ; à 1 cumul, temps par monstre 51,54 s contre 50,87 s sans Hot Streak au Monte Carlo (DoT de 12 s de Pyroblast perdu à la mort du monstre, mana) ; l'analytique y voit un gain de 0,1 %. Pyroblast d'ouverture non modélisé (angle mort, sous-évalue le Feu en leveling).
- Écart analytique / Monte Carlo : −5 à −10 % sur ces builds (l'analytique est optimiste), cohérent entre variantes proches sauf Arcane Power.
- **Wake of Fire** : bonus de critique du Fire Blast après une mise à mort (30 s) non modélisé (sous-évalue le Feu en leveling).
- Cumuls de Hot Streak remis à zéro entre deux combats (sous-évalue un peu).
- **Scénarios, niveau 40, fiche de base** : la rotation arcane épuise 2 322 mana en ~18 s (132 mana/s) ; sans Évocation ni potion (B10), l'Arcane est fortement pénalisé en boss de 60 s et 180 s. La rotation ne s'adapte pas à la mana restante (angle mort : un joueur passe à Frostbolt).
- Boss insensibles au gel (suppose, question ouverte ajoutée) : pas d'Ice Lance sur gel en boss, Fingers of Frost seulement.
- **Optimiseur, premiers résultats (préréglage rapide, fiche de base)** : leveling 10 → 30 en Feu (Improved Fireball, Elemental Precision, Ignite, Burning Soul) ; raid et donjon au niveau 30 en Arcanes (`ab_stacks` 1, mana limitée) ; raid au niveau 60 : Arcanes 46/5, beaucoup de points sur des talents sans effet modélisé (Wand Specialization, Magic Absorption, Arcane Shielding…) : égalités, à signaler dans les raisons et les angles morts.
- **Analytique des scénarios avec fin de mana** : ~10 % sous le Monte Carlo (niveau 60, raid, Arcanes : 75,6 contre 83,5) ; le hasard de Missile Barrage et de Clearcasting prolonge le Monte Carlo. Décision au Monte Carlo.
