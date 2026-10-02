# Notes de développement de Blizzard du 24/09/2026 : lecture et recoupement avec le client

Relevé le 2026-09-28 (T05, bloc B), à la demande de l'utilisateur : lecture de la source primaire, version du client concernée, recoupement de chaque changement du Mage avec les données du client 1.60.1.70009.

## Source
- Message officiel : « WoW Forever Beta Development Notes – Updated September 24 », Kaivax (Community Manager), forum de Blizzard, 24/09/2026 à 22 h 23 (heure du Pacifique) : <https://us.forums.blizzard.com/en/wow/t/2360696/1>. Relais consultés pour retrouver l'adresse, non utilisés comme source : bluetracker.gg, mobalytics.gg, icy-veins.com.
- Formule du message : « Today, we updated the WoW Forever Beta with a new build that includes the following updates. » Aucun numéro de build n'est cité.

## Version concernée : 1.60.1.70009 (probable)
`uv run forever builds` (wago.tools, produit `wow_classic_beta`, 1.60.x, relevé le 2026-09-28) : 1.60.1.70009 publié le 2026-09-24 à 22:02:03 UTC, dernier build ; le précédent, 1.60.1.69977, date du 2026-09-23. Le message parle d'un build mis en ligne « aujourd'hui » (24/09) et aucun build ne suit 70009 : les notes décrivent 70009. Les deux changements visibles dans les tables du client le confirment (ci-dessous).

## Changements du Mage, recoupés avec le client
| Changement (texte du message) | Client 1.60.1.70009 | Verdict |
| --- | --- | --- |
| « Arcane Missiles no longer checks line of sight on each missile, just once at the beginning of the channel. » | Règle du serveur, absente des tables | Sans effet sur les simulateurs (aucune ligne de vue modélisée) ; rien à changer |
| « Wake of Fire buff duration has been increased to 30 seconds (was 20 seconds). » | Aura 1312934 « Wake of Fire » : `SpellMisc.DurationIndex` 9 → `SpellDuration` 30 000 ms ; talent 11078 : infobulle « within {1} sec » = 30 (`talents.json`) | Concorde. Le bonus de critique du Fire Blast après une mise à mort n'est pas modélisé (seule la réduction de recharge l'est, B13) : angle mort du Feu en leveling |
| « Hot Streak buff duration has been increased to 20 seconds (was 15 seconds). » | Infobulle du talent décodée : 20 (`confirmed_changes.json`, 15 dans la référence 69893 ; `talents.json` : `duration_s` 20) | Concorde. Le Hot Streak modélisé en T05 (bloc C) prend 20 s |
| « Ignite no longer double dips on % damage increase modifiers. » | Règle du serveur ; aura 412538 (4 s, période 2 s, non cumulable) inchangée | Le moteur prend déjà Ignite sur le critique final, tics non remultipliés : calcul conforme, verrouillé par `tests/unit/test_variants.py::test_ignite_takes_percentage_bonuses_once` (registre A18) |

Aucun écart entre les notes et le client : rien pour `docs/OPEN_QUESTIONS.md` hors la mention ajoutée à A18, rien pour T08.

## Seconde lecture du 2026-10-02 (version 2 du message, « Updated October 1 »)
`uv run forever notes` (lancé à la main, accord réseau de l'utilisateur du 2026-10-02) : le sujet 2360696 est révisé le 2026-10-01 (version 2). Le premier message a été relu en JSON (même hôte, `robots.txt` respecté). L'historique des révisions (`/posts/<id>/revisions/2.json`) est refusé (HTTP 403) : on ne sait pas quels points datent du 24 septembre et lesquels du 1er octobre. Sujets officiels lus aussi : problèmes connus (2352687, « Known Issues - October 1 », version 5), Guerrier du 2026-10-02 (2369360), annonce de la BlizzCon (2347170 : liens vers des vidéos seulement). Pistes du 2026-10-01 vérifiées : `tasks/pistes-open-questions-2026-10-01.md`.

| Point (paraphrase du texte) | Client et données | Suite |
| --- | --- | --- |
| Hunter > Pets : Tame Beast refusé sur une bête de niveau supérieur au Chasseur | Absent du client (`SpellTargetRestrictions`) | `pet_rules.json` `tame.level_margin` à 0, `probable` (révision 6, `docs/research/data-1.60.1.70124-r6.md`) |
| Furious Howl : bonus de puissance d'attaque réduit de 40 % | Points de base identiques en 70009 et 70124 ; aucune table antérieure | Non vérifiable |
| Sonic Blast désormais disponible pour les chauves-souris | Sorts 1264478 à 1264488 présents, rattachés à aucune ligne de familier dans 70124 | Non reflété dans les tables lues, à revoir avec 1.60.1.70170 |
| Mage : Arcane Missiles, Wake of Fire, Hot Streak, Ignite | Inchangés depuis la première lecture | Concordance (tableau ci-dessus) |
| Classes : respec à coût réduit, temporaire, bêta seulement | `respec.json` `beta_observed.temporary_beta` | Non modélisé (`docs/modeling-decisions.md`) |
| Problèmes connus : Arcane Missiles sous les coups tire un projectile à pleins dégâts au lieu d'un projectile tronqué | Règle du serveur | Bug reconnu, jamais modélisé (registre B6) |
| Problèmes connus : fenêtre Legacy ouverte avant le niveau 25 | — | Signal pour LG1 (ROADMAP) |

Le plafond de niveau à 30, Legacy (défis, rangs, perks), les règles de royaume, Darkspear Islands, la date de lancement et l'API ne figurent dans aucun des sujets officiels lus.

Complément du 2026-10-02 (installation de 1.60.1.70170, tables de wago.tools) : Sonic Blast est rattaché à la ligne « Pet - Bat » (653) dans `SkillLineAbility` de 70170 ; les points de base de Furious Howl (`SpellEffect`, rangs 1 à 4) passent de 9, 56, 100, 136 en 70124 à 5, 34, 60, 82 en 70170. Les deux points de la note concordent avec le client 70170.
