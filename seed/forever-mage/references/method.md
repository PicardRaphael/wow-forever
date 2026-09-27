# Méthode de l'optimiseur

## Leveling
- Espace : tous les ordres légaux (1 point par niveau à partir de 10, paliers de 5 points par arbre, prérequis au maximum).
- Critère : temps total pondéré = somme sur les niveaux de (temps par monstre × monstres équivalents pour passer le niveau). Temps par monstre = combat + repos + trajet (6 s par défaut). On prend à chaque niveau la meilleure rotation (Givre ou Feu) pour le build courant.
- Recherche en faisceau : pour chaque état, présélection des 4 meilleurs ajouts au modèle analytique avec anticipation (on complète gloutonnement 4 points pour voir l'effet des talents déclencheurs), puis décision au Monte Carlo (tirages communs pour comparer à égalité de hasard).
- Validation : relancer `sim_leveling.py --n 2000` sur le build obtenu et sur l'alternative sérieuse. Écart < 2 % = égalité : le dire et choisir selon le confort (mana, sécurité, PvP).
- Résultat connu (build 70009, Orc sans fiche) : 3 Improved Frostbolt, puis Elemental Precision au niveau 13 (les points 4 et 5 d'Improved Frostbolt ne servent qu'à partir de l'Éclair rang 3 au niveau 14), Improved Frostbolt 4-5 aux niveaux 14-15, Frostbite avant Ice Lance, Ice Lance au 20, puis Frost Channeling. Les choix entre talents faibles (Ice Shards, Piercing Ice, Frost Channeling) sont dans le bruit.

## Raid
- Faisceau sur les 51 points, noté par le moteur analytique (pve_raid.py) : modèles Givre (Fingers of Frost, Winter's Chill, Shatter), Feu (Hot Streak en chaîne de Markov, Ignite, Brûlure), Arcanes (cumuls de Déflagration, Missile Barrage, Arcane Power).
- Facteur de calage sur MythicSim ≈ 1,04-1,07 pour les trois spés du Mage. Le chiffre absolu se confirme avec wowsims Forever ; le classement entre builds proches aussi.

## PvP
- Faisceau noté par pvp.score() : burst (fenêtre de 6 s), contrôle (s/min), survie (s gagnées/min), soutenu en mouvement. Poids réglables. Statut EST : sert à comparer des builds, pas à prédire un duel.

## Respec
- Gain = heures économisées × or par heure ; coût = barème + trajet. Or par heure : EST, à remplacer par le vrai rythme du joueur.
