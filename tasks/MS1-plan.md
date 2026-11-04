# Plan MS1 — Second simulateur (MythicSim) et builds au 60 par simulation (2026-11-04, en attente de validation)

Demande de l'utilisateur (2026-11-04) : comparer Chaman et Mage après les notes du 2 novembre, « être meilleur que ce
que font les gens » pour les builds, chercher au-delà de wowsims, et brancher MythicSim « tout propre ». Rust et un clone
de MythicSim sont installés en local avec son accord (`~/.cache/forever/third_party/mythicsim`, chaîne
`1.99.1-x86_64-pc-windows-gnu`).

## 1. Les deux questions (décision 288)
- **Qui maintient déjà ça mieux que nous ?**
  - wowsims/forever (moteur Go, MIT) : neuf classes, mis à jour plusieurs fois par jour le jour d'un patch.
  - MythicSim (sage3648/mythicsim-forever-engine, Rust, MIT) : porté de wowsims via son fork Go
    (sage3648/mythicsim-forever-engine-go, épinglé `a667dce`), lui aussi suivi à la journée (changelog
    https://mythicsim.com/changelog). Il intègre parfois une classe avant wowsims, parfois après.
  - Les deux sont maintenus par d'autres ; nous n'écrivons aucune mécanique.
- **Que se passe-t-il au prochain patch ?**
  - Les deux moteurs publient leurs mises à jour ; `forever update` recompile les deux et rejoue les cas de référence
    (rapport des valeurs qui changent, décision 288).
  - Risque mesuré le 2026-11-04 : la dérive des épinglages. MythicSim refuse les rotations du wowsims actuel
    (`spellIsCasting`, `OtherActionResourcePotion` inconnus de son proto `a667dce`). Les préréglages doivent donc venir
    de son propre fork Go, à son épinglage, jamais de wowsims.
  - Rien ne casse chez nous : un refus du moteur est rendu tel quel (code et raison), jamais remplacé en silence.

## 2. Ce qui change
### a) Talents choisis dans `forever_simulate` (et `forever sims`)
- Paramètre `talents` (« clé=rang,… », nos clés) sur `action="compare"` : légalité contrôlée sur les arbres du client
  (`check_talents`), puis conversion vers la chaîne du moteur.
- Conversion par identifiant de sort, jamais par position :
  - wowsims lit l'ordre des champs de `proto/<classe>.proto` (`talent_spell_id`) ;
  - MythicSim lit, selon la classe et les règles de Forever, l'ordre du client 70707 (fixture
    `dev-notes-20261102/README.md`, `src/classes/*/prepare*.rs`) : table de conversion par classe, lue dans son code
    épinglé.
  - Un talent sans correspondance refuse le calcul en le nommant (Chaman : Call of Thunder, nœud de Lava Burst).
- Revient sur la décision 299 au niveau 60 seulement : la comparaison de builds se fait par les simulateurs de la
  communauté, sans moteur à nous. Sous le 60, rien ne change (pas d'optimiseur, pas de conseil de respec).

### b) MythicSim, second moteur
- `forever/sims/mythicsim.py`, adaptateur mince :
  - préréglages lus dans le clone du fork Go épinglé (`w.read_presets`, même format `ui/specs`) ;
  - binaire `forever-engine sim --request --gate --outfile` ;
  - sortie : DPS moyen, écart type, combats, `identity` (révision de référence ; `client_build` de l'identité est la
    version du contrat, jamais présentée comme la version simulée).
- Code 5 (`prepared:false`) ou refus de la porte : erreur `mythicsim_refused` avec le code et la raison du moteur.
- `forever sims update` : clone ou met à jour MythicSim et son fork Go, compile (`cargo build --locked --release`,
  chaîne épinglée par `rust-toolchain.toml`), épingle commit et empreinte du binaire comme pour wowsims.
- `forever_simulate(action="compare", engine="wowsims"|"mythicsim"|"both")` : `both` rend les deux colonnes et l'écart,
  sans moyenne ni choix.
- Rejeu de la veille : les cas de référence passent aussi par MythicSim.

### c) Recherche de builds au 60 (`action="builds"`)
- Point de départ : préréglages du moteur, builds populaires de Talents Forever, guide de Forever Companion.
- Échange d'un point à la fois tant que le DPS monte, tirages appariés (même graine).
- Confirmation sur 10 000 combats : un gain sous le seuil de bruit (écart type apparié ×2) est rendu « non départagé ».
- Limites dites dans la provenance : rotation et équipement du préréglage gardés ; un talent que la rotation n'utilise
  pas ne peut rien rapporter.

### d) Tests (sans réseau, `tests/fixtures/`)
- Conversion des talents : ordre du proto Chaman (Improved Ghost Wolf), ordre du client 70707 pour MythicSim,
  talent sans correspondance refusé.
- Adaptateur : requête écrite, sortie lue, refus (code 5) rendu ; binaire simulé par un exécutable factice.
- Recherche : arrêt sur gain nul, « non départagé » sous le seuil.
- `forever sims update` : épinglage des deux moteurs (git et cargo simulés).
- Test de contrat `provenance` pour les nouvelles sorties.

### e) Documents
- `docs/DECISIONS.md` : décision 301 (second simulateur, conversion par identifiant de sort, recherche de builds au 60
  par les simulateurs, retour partiel sur 299).
- `docs/DATA_SOURCES.md`, `docs/ARCHITECTURE.md`, skills `forever-router`, `forever-builds`, `forever-mage` : moteur
  utilisé par classe et date de sa dernière mise à jour à citer.
- `docs/OPEN_QUESTIONS.md` :
  - recharge partagée Ice Lance et Fire Blast modélisée par quel moteur ;
  - valeurs de Lightning Bolt (deux sites de datamining divergent) ;
  - effet réel de Call of Thunder.

## 3. Essai en jeu (décision 273)
- Ce soir après connexion, une seule bulle d'aide :
  - Lightning Bolt rang 10 ;
  - Call of Thunder ;
  - Arcane Blast ;
  - Ice Lance.
- Comparer aux deux moteurs.

## 4. Durée et dépendances
- Environ une demi-journée ; aucune dépendance Python nouvelle.
- Accès réseau : clones git de MythicSim et de son fork Go, téléchargements de `cargo` (même statut que `go` pour
  wowsims).
