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
