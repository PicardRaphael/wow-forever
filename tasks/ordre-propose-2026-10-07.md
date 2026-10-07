# Ordre des tranches proposé le 2026-10-07 (non appliqué)

**Statut : proposition en attente de validation** (décision 201). L'ordre en vigueur reste celui de la table de
`docs/ROADMAP.md`. Ce document propose un ordre qui sert d'abord les trois paris de `docs/VISION.md` : (1) chat et
boutons en jeu, (2) exports vers les addons, (3) boucle de mesure.

## Contraintes de calendrier

| Période | Dates | Ce qui est possible |
| --- | --- | --- |
| Fin de la bêta | du 2026-10-07 au 2026-10-21 (deux semaines) | tout, **dont les tests en jeu** |
| Sans jeu | du 2026-10-21 au 2026-11-04 (deux semaines) | **hors ligne seulement** : fixtures, tables du client, formats d'export, lecteurs d'addons, documentation |
| Lancement | à partir du 2026-11-04 | nouveau départ probable des personnages (leveling à refaire), produit TACT inconnu (DON4, alerte `silent` possible), renommage possible du suffixe `_Camelot.toc`, mises à jour des addons en rafale, champs de bataille annoncés, API Blizzard peut-être (EC1) |

Capacité : une tranche fait une à trois sessions ; à une session par jour environ, chaque période de deux semaines
absorbe quatre à six tranches courtes, ou deux à trois longues.

Règle tirée du calendrier : **tout ce qui exige un test en jeu** (lien Talents Forever ouvert dans l'addon,
transport du pont, import des chaînes dans Naowh Forever et EllesmereUI, protocoles de mesure) doit être fini avant
le 21 octobre ou attendre le 4 novembre ; la fenêtre sans jeu sert au hors-ligne pur.

## Ordre proposé

### Phase A — fin de la bêta (7 au 21 octobre) : ce qui a besoin du jeu

1. **T08e** (une demi-session à une session) : la correction de `forever update` évite une attente à chaque version
   qui ne touche que les fiches PvP ; elle compte surtout au lancement, où les versions vont s'enchaîner. Pari 3.
2. **FA1, resserrée sur Talents Forever** : export v6 avec la table de correspondance des nœuds, builds populaires,
   recoupement des arbres. Le va-et-vient dans l'addon se teste en jeu : avant le 21. **Proposé** : sortir de FA1 la
   comparaison d'équipement de ForeverAssist V1 (point 4), que Naowh Forever (BiS, poids, score) et GearQuest Forever
   couvrent déjà ; elle sera remplacée par l'export BiS et poids vers Naowh (T10a plus bas) ou abandonnée (refus
   « refaire ce que font les addons »). Pari 2, et le bouton Talents de P06.
3. **P06, pont et boutons** : le transport (bande, réserve d'addons, signal, secours) ne se met au point qu'en jeu,
   donc avant le 21. Boutons disponibles dès P06 : Mettre à jour (T08d), Talents (FA1, Mage), Familiers (CH0), PvP
   (PV1), Leveling dans sa forme actuelle (Mage, zone à mon niveau). Pari 1.

Si P06 déborde au-delà du 21, la partie hors ligne (protocole sur fixtures, conversations, liste d'autorisations,
journal) continue dans la fenêtre sans jeu et le test en jeu se fait le 4 novembre.

### Phase B — sans jeu (21 octobre au 4 novembre) : hors ligne pur, pour le lancement

4. **T04d puis T04f** (modèle d'XP de Forever, puis bonus d'XP cumulés) : à partir des tables de quêtes et des sorts
   des auras du client (accès wago.tools sur accord, comme toute tranche), sans jeu. Au lancement, tout le monde
   remonte de niveau : c'est le moment où le bouton Leveling (objectif suivant, bonus actifs) a le plus de valeur.
   Les mesures de LVL3 et de l'XP réelle se font après le 4 novembre. Paris 1 et 3.
5. **DJ1, partie hors ligne** (lecteurs d'AtlasLoot, de ForeverDungeonJournal et du journal de Naowh Forever en
   recoupement ; « où looter tel objet ») ; le relevé hors combat de ForeverLogger (butin, marchands) se teste au
   lancement. Préalable de l'équipement.
6. **T10a — Équipement du Mage vers Naowh Forever** (découpe proposée de T10) : base d'objets lue dans le client,
   **poids des statistiques calculés par le moteur du Mage** (ligne `NFSW1:`), BiS par niveau et par contexte
   (`!NBIS1!`) avec l'endroit où looter chaque objet (DJ1) ; le reste de T10 (toutes les classes, réputation, PvP,
   coûts) reste à sa place. Va-et-vient sur fixtures hors ligne, import en jeu au lancement. Pari 2 et bouton
   Équipement.
7. **EX1** (profils EllesmereUI, macros par classe vers Naowh Forever, objet LibDataBroker) : formats sur fixtures
   hors ligne, import en jeu au lancement. Pari 2. Peut glisser après le lancement sans dommage.

Priorité dans la fenêtre si elle manque de place : T04d et T04f, puis DJ1 et T10a, puis EX1.

### Phase C — lancement (à partir du 4 novembre)

8. **Mise en route du lancement** (pas une tranche : passages de `forever update` et décisions au fil de l'eau) :
   nouvelle version installée, produit TACT relevé (DON4), suffixe des `.toc` vérifié pour ForeverLogger et l'addon du
   pont, addons relus (`forever addons status`), tests en jeu restés en attente (P06, T10a, EX1, LVL3). Pari 3.
9. **PV2 puis AN1** dès l'ouverture des champs de bataille : rendements décroissants mesurés, analyse de mes combats
   PvP ; ouvre le bouton « Analyse du dernier combat ». Pari 3.
10. **Tranches de classe** dans l'ordre actuel (PA1, DE1, PR1, CH1, CM1, GU1, VO1, DR1) : chacune ouvre les boutons
    Talents, Équipement et Leveling pour sa classe et ajoute ses exports (talents, poids, BiS, macros).
11. Puis T05b, AN2, LG1, T07, LG2, MT1, RP1, T08, EC1 (gardée par le lancement et la couverture de l'API), T09 et les
    parties raid, le reste de T10, T11, T13 : ordre actuel inchangé.

## Tranches que l'ordre proposé fusionne ou retire (à valider)

| Tranche | Proposition | Raison |
| --- | --- | --- |
| FA1 point 4 (ForeverAssist V1, comparaison d'équipement en infobulle) | retirée de FA1 ; remplacée par l'export vers Naowh Forever (T10a) | Naowh Forever et GearQuest Forever le font ; refus de refaire ce que font les addons |
| FA1p (fiche PvP de la cible en jeu) | fondue dans le bouton PvP de P06 | même donnée (PV1), affichée par le pont ; plus de panneau `/fa` à maintenir |
| ForeverAssist V2 (contexte du personnage écrit dans une SavedVariable) | remplacée par le contexte envoyé par P06 | le pont transmet le contexte à chaque message, sans `/reload` |
| FA3 (compagnon de bureau, analyse après le combat) | fondue dans AN1, AN2 et le bouton « Analyse du dernier combat » de P06 | le compagnon de bureau, c'est le pont |
| T10 | découpée : T10a (Mage, poids et BiS vers Naowh) avant le lancement, le reste à sa place | le moteur du Mage suffit pour des poids calculés ; les autres classes attendent leur moteur |

## Ce que l'ordre proposé ne change pas

Une tranche à la fois, tests d'abord, `verify` vert, CI verte sous Ubuntu et Windows ; aucune tranche ne démarre un
chantier parallèle ; les tranches gardées par un événement (EC1) restent sautées tant que la condition n'est pas
remplie (décision 62).

## Risques

- **Pont (P06)** : zone grise assumée par la décision 194 ; fragile à chaque build du client, donc à revérifier au
  lancement.
- **Formats des addons** : Talents Forever (v6), Naowh Forever et EllesmereUI peuvent changer leurs chaînes au
  lancement ; chaque export garde un test de va-et-vient sur fixture et une procédure de test en jeu, et
  `forever addons status` signale le changement.
- **Accès réseau** : T04d, T04f et T10a lisent des tables du client par wago.tools ; accord de l'utilisateur au plan
  de chaque tranche, comme d'habitude.
- **Capacité** : si la phase A déborde, P06 passe avant FA1 pour garder le premier pari, et le lien Talents Forever
  se teste au lancement.
