# Questions ouvertes

Chaque règle de jeu incertaine, avec la façon de la vérifier (journal, test en jeu, source).

- Regroupement des actions serveur dans Forever : mesurer sur journaux (intervalles entre lancers).
- Recul d'incantation : 0,5 s sans limite ? Mesurer.
- Transfert (Blink) utilisable sous étourdissement ? Tester en jeu.
- Coût en mana des rangs issus de talents (Ice Lance r1, Pyroblast r1, Arcane Blast r1, Blast Wave r1).
- Produit TACT au lancement (wow_classic_forever ?).
- Talents : la plupart des rangs de `talents.json` sont lus sur le build 1.60.1.69893 (certitude `probable` pour 1.60.1.70009). Revérifier sur les tables du client 70009 (diff en T03).
- École Givre-feu (Frostfire Bolt) comptée à la fois en givre et en feu : double bénéfice des talents des deux écoles ; pour le multiplicateur de critique, la branche givre (Ice Shards) l'emporte (comportement de `fm.py`, conservé en T02). À vérifier en jeu.
- Winter's Chill : source de la valeur de +2 % de critique par cumul dans Forever (Frostbolt et Ice Lance seulement) ; relever la table du client.
- `int_per_crit` entre les niveaux 1 et 60 : interpolation linéaire estimée (EST) ; remplacer par la table du client ou la fiche du personnage.
- Modèle de personnage : `leveling.json.player_model` (texte) omet les termes `0,8 × max(0, niveau − 5)` (Intelligence) et `0,5 × max(0, niveau − 5)` (Esprit) que `fm.py` applique ; le code du seed fait foi pour la parité (`mechanics.json` : `late_bonus_per_level`). À trancher avec des fiches de personnage réelles.
- Coût en mana des rangs issus de talents : repli estimé à 0,75 × premier coût publié du sort, sinon 50 (`mechanics.json` : `mana.talent_rank_cost`) ; à remplacer par les coûts relevés en jeu (voir la question sur Ice Lance r1, Pyroblast r1, Arcane Blast r1, Blast Wave r1).
