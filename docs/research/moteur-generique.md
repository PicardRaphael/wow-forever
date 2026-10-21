# Moteur générique pour les 9 classes : étude (2026-10-13)

Demande de l'utilisateur du 2026-10-13 : un moteur générique qui donne **dès maintenant** une première version calculée
pour les 9 classes (choix des talents, temps par monstre et XP par heure en leveling), à partir des données du client
et des priorités de rotation de wowsims Forever et des addons, marquée `suppose`, puis affinée par chaque tranche de
classe. Étude seulement : rien n'est implémenté ici.

> **Correction du 2026-10-13 (décision 252)** : la première version de cette étude disait qu'aucun simulateur
> wowsims pour Forever n'existait. C'est faux : **ElliotWood/Forever** (Go, MIT, fork de wowsims/classic) simule les
> 9 classes de Forever au niveau 60, avec des données au build 1.60.1.70291, et publie chaque semaine
> `wowsimcli-windows.exe` ; `sage3648/mythicsim-forever-engine-go` (moteur de MythicSim) en est un fork. Voir la
> décision 224, la tranche SIM1 et [l'étude wowsims](wowsims-forever.md). Les passages concernés sont corrigés plus
> bas. **Décision prise** (décision 252) : pas de moteur générique avant la sortie ; les tranches de classe gardent
> leur ordre (CM1 après PV2 et AN1, vérifiée sur les journaux de l'utilisateur).
>
> **Mise à jour du 2026-10-21** ([étude du jour](simulateur-communaute-2026-10-21.md)) : ElliotWood/Forever répond 404
> depuis environ le 19 octobre ; le simulateur de référence est `wowsims/forever` (MIT, données à 1.60.1.70450), sans
> binaire à jour publié ; MythicSim le suit directement.

## 1. Ce qui existe aujourd'hui

- **Moteur** (`forever/engine/`, environ 2 900 lignes) : écrit pour le **Mage** : sorts lancés (temps d'incantation,
  mana, toucher, critique, résistances), effets des talents du Mage, leveling (temps par monstre, repos, mana, XP par
  heure, Monte Carlo et modèle analytique), respec, PvP (contrôles et rendements décroissants, toutes classes).
- **Données de sorts** (`spells.json`) : 15 sorts du Mage seulement, avec rangs, dégâts, coûts et coefficients décodés
  du client. Les autres classes n'ont que leurs **arbres de talents** (`classes.json`, légalité et paliers) et leurs
  fiches PvP.
- **Monstres** (`monsters.json`) : PV par niveau mesurés dans mes journaux et corrigés par Questie ; armure des
  monstres : non mesurée (sans effet pour un Mage, décisive pour une classe physique).
- **Builds des autres classes** : populaires (Talents Forever), vérifiés sur le client ; aucun calcul.

## 2. Sources pour les autres classes

| Source | Ce qu'elle apporte | Certitude au mieux | Disponible |
| --- | --- | --- | --- |
| Client 1.60.1.70338 (wago.tools, décodé par `forever update`) | sorts de toutes les classes : rangs, dégâts (`SpellEffect`), temps d'incantation, coûts, recharges, niveaux ; effets des talents (auras de modification) | certain pour la valeur, `probable` pour son interprétation | oui, déjà téléchargé ; décodage limité au Mage |
| Coefficients des sorts | absents du client Classic : règle de Classic (temps d'incantation / 3,5, pénalités) | `suppose` | règle connue, appliquée au Mage |
| Rotations de wowsims | listes de priorités (APL) des 9 classes de Forever au niveau 60, dans le moteur d'ElliotWood/Forever (décision 233 : formules reprises en citant dépôt, commit et fichier) | `suppose` (source communautaire ; niveau 60 seulement, pas le leveling) | **oui** : ElliotWood/Forever (MIT, build 1.60.1.70291, `wowsimcli-windows.exe` hebdomadaire ; fork MythicSim `sage3648/mythicsim-forever-engine-go`), décision 224, [étude](wowsims-forever.md) ; *corrigé le 2026-10-13* (la première version disait « aucun simulateur wowsims pour Forever ») |
| Addons installés | Naowh Forever (arbres des talents, planificateur d'entraînement : sorts à apprendre par niveau), Forever Guide, Forever Companion | `suppose` | oui, lecture locale (décision 133) |
| Mes journaux de combat | dégâts réels, durée des combats, armure effective des monstres | `certain` après mesure | seulement pour les classes que je joue (Mage, Chasseur) |

## 3. Ce qui est faisable avant le 4 novembre

Trois niveaux, du plus sûr au plus ambitieux :

1. **Lanceurs de sorts** (Prêtre Ombre, Démoniste, Druide Équilibre, Chaman Élémentaire), **3 à 4 jours** :
   généraliser le décodage des sorts du Mage (mêmes tables du client) à leurs sorts de dégâts, et le moteur de
   lancement (mana, toucher, critique, résistances) qui sert déjà. Rotation : priorité simple par classe (DoT
   entretenus, puis sort principal), tirée des APL de wowsims Forever (niveau 60, à adapter aux sorts connus au
   niveau du personnage), `suppose`. Donne le temps par monstre et l'XP par
   heure. Choix des talents : seulement les talents qui modifient des dégâts, des coûts ou des temps d'incantation
   par des auras lisibles dans le client ; les autres restent « non calculé ».
2. **Classes physiques** (Guerrier, Voleur, Paladin Vindicte, Chaman Amélioration, Druide Farouche), **5 à 7 jours
   de plus** : rien n'existe aujourd'hui : attaques blanches avec l'arme équipée (vitesse, dégâts de l'objet),
   puissance d'attaque, rage ou énergie, coups spéciaux, armure des monstres (non mesurée : `suppose` par la formule de
   Classic), parade et esquive des monstres. Une première version sans les procs d'armes ni les poisons.
3. **Chasseur** : le tir automatique et les coups spéciaux relèvent du niveau 2 ; le familier comme entité est la
   tranche CH1 (prévue). Sans lui, l'XP par heure du Chasseur serait très sous-estimée : à ne pas publier avant CH1.

**Recommandation** : seul le niveau 1 est raisonnable avant le 4 novembre, et seulement après LN1 (qui ne peut pas
glisser). Le niveau 2 vaut une tranche par famille de classes, en novembre.

## 4. Temps et effet sur le calendrier

*Calendrier remplacé le 2026-10-13 par la décision 251* (T04d, T04f, DJ1, RX1, puis LN1 au plus tard le
24 octobre, puis EX1, SIM1 et T10a) ; le texte ci-dessous est celui de l'étude.

- Fenêtre réelle : du 13 au 21 octobre, la bêta est ouverte et les tests en jeu priment (P06b, sondes) ; du 21 octobre
  au 4 novembre, LN1 passe en tête (décision 231), puis T04d, T04f, DJ1, SIM1, T10a, EX1.
- **Niveau 1 (3 à 4 jours)** : il ne tient qu'en repoussant T04d et T04f après le lancement, ou en raccourcissant
  DJ1 ; LN1 garde sa place.
- **Niveau 2 (5 à 7 jours de plus)** : il repousse SIM1, T10a et EX1 après le lancement ; déconseillé avant le
  4 novembre.
- Les tranches de classe (CM1, CH1, DE1, PA1, GU1, VO1, PR1, DR1) restent nécessaires : le moteur générique leur donne
  un socle, il ne les remplace pas.

## 5. Risques

- **Fausse précision** : un nombre calculé inspire plus confiance qu'un build populaire ; sans mesure dans mes
  journaux, un écart de 20 à 40 % sur l'XP par heure est plausible (coefficients supposés, rotation pensée pour le
  niveau 60, armure des monstres inconnue). Parade : `suppose` partout, mention en clair dans chaque réponse, entrées du registre au
  statut `modelise`.
- **Rotations pensées pour le niveau 60** (*corrigé le 2026-10-13*) : wowsims a bien un moteur Forever
  (ElliotWood/Forever), dont les APL portent les sorts et talents propres à Forever, mais au niveau 60 seulement ;
  en leveling, une partie des sorts et des talents manque, et la rotation doit être adaptée sans source pour la
  valider. Le risque est réduit, pas levé.
- **Effets des talents** : beaucoup d'effets ne sont pas de simples pourcentages (procs, conditions, déclencheurs) ;
  le décodage générique n'en lira qu'une partie : talents non lus marqués « non calculé », jamais devinés.
- **Charge du registre** : chaque mécanique ajoutée demande son entrée dans `docs/MECHANICS_REGISTRY.yaml` (source,
  tests) ; compter environ une demi-journée par classe pour le registre et les questions ouvertes.
- **Validation** : aucune mesure avant que je joue ces classes ; AN1 et les tranches de classe la feront.

## 6. Décision à prendre

*Prise le 2026-10-13 (décision 252)* : tout garder pour les tranches de classe après le 4 novembre ; la règle de
la décision 243 reste la réponse en attendant.

- Lancer le **niveau 1** après LN1, en repoussant T04d et T04f après le lancement ? Ou tout garder pour les tranches de
  classe après le 4 novembre (calendrier actuel) ?
- Dans les deux cas, le bouton Leveling et le bouton Talents gardent la règle de la décision 243 : calcul quand il
  existe, build populaire et données des addons sinon, avec la mention de ce qui n'est pas calculé.
