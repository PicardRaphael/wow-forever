# CJ1, bloc 6 — Maquettes de la nouvelle fenêtre de ForeverBridge (à valider avant tout code)

Écrites le 2026-10-15 d'après l'étude locale des fenêtres de Naowh Forever 1.1.15 (barre latérale, cartes, onglets,
recherche), Forever Companion 1.0.0 (onglets latéraux à icône), EllesmereUI 9.5.4 (barre latérale, en-tête, fabrique de
contrôles, API publique d'habillage) et RestedXP 4.11.23 (étapes empilées, thèmes) ; aucun code repris. Étude web
(bonnes pratiques d'interface des addons) non faite : à faire sur ton accord, en lecture seule. Principes retenus dans
`docs/research/interface-addons.md` (à écrire avec le code).

## Principes
1. **Une conversation d'abord** : le chat reste l'écran principal ; chaque autre écran est un raccourci vers une
   question ou une action, jamais une copie de l'interface d'un addon (décision 272 : on renvoie à Naowh, Forever
   Companion, RestedXP, GearQuest pour leurs affichages).
2. **Navigation à gauche** (comme Naowh et EllesmereUI), six entrées fixes, l'écran courant surligné ; la largeur de
   la barre se replie en icônes quand la fenêtre est étroite.
3. **Barre d'actions hiérarchisée** : au plus trois actions principales visibles, le reste dans « Plus ▾ » ; largeur
   mesurée sur le texte, jamais de chevauchement (test à toutes les tailles permises).
4. **Réponses en cartes** : titre, icône de certitude (●certain ◐probable ○supposé), lignes courtes, liens et boutons
   dans la carte ; la question en cours et ses réponses sont des boutons dans la carte.
5. **« À valider » cohérent** : le compteur et les réponses comptent les mêmes cartes ; jamais de question dedans.
6. **Thème** : si EllesmereUI est chargé, notre fenêtre prend sa couleur d'accent et sa police par son API publique
   (lecture seule, EllesmereUI jamais modifié) ; sinon thème sombre sobre, une couleur d'accent, police du jeu.
7. **Rien en combat**, aucune fonction protégée ; l'ancienne fenêtre reste derrière `/fv classique` jusqu'à ton accord.

## 1. Fenêtre, écran « Chat » (taille par défaut)

```
┌─ Forever ───────────────────────────────── Données 1.60.1.70374 · à jour ●  ─ □ ✕ ┐
│ ▸ Chat         │ ┌───────────────────────────────────────────────────────────────┐ │
│   Feuille de   │ │ Vous · Prépare ma feuille de route.                           │ │
│   route        │ └───────────────────────────────────────────────────────────────┘ │
│   Talents      │ ┌ Feuille de route 1 → 10 ─────────────────────────── ◐ probable ┐ │
│   Équipement   │ │ 3,1 h · environ 2 900 XP/h · Coldridge Valley → Dun Morogh     │ │
│   Exports      │ │ Base : parcours gratuit de RestedXP adapté (+1 quête de classe)│ │
│   Mises à jour │ │ Premiers arrêts : Dwarven Outfitters, Coldridge Mail…          │ │
│      (2)       │ │                                                                │ │
│                │ │ Combien de niveaux ?                                          │ │
│                │ │ [ 3 niveaux ] [ 5 niveaux ] [ 10 niveaux ]  [ Valider et livrer ]│
│                │ └────────────────────────────────────────────────────────────────┘ │
│                │                                                                   │
│  ? Aide        │ ┌───────────────────────────────────────────────┐ [ Envoyer ]     │
│                │ │ Écris ta question…                            │ [ Plus ▾ ]      │
└────────────────┴─┴───────────────────────────────────────────────┴─────────────────┘
```
- Barre du bas : « Envoyer » et « Plus ▾ » (Nouvelle conversation, Coller /simc, Diagnostic) ; les boutons de tranche
  (Talents, Leveling, PvP, Familiers…) passent dans la navigation ou dans « Plus ▾ » selon l'écran.
- « Mises à jour (2) » : le nombre est celui des cartes réellement montrées (le modèle reçoit le même compte).

## 2. Écran « Feuille de route » (assistant, sans saisie obligatoire)

```
┌ Feuille de route ───────────────────────────────────────────────────────────────┐
│ Personnage : Jen · Mage Orc · niveau 19 · Durotar (position lue en jeu)         │
│                                                                                  │
│ Du niveau  [ 19 ▾ ]   au niveau  [ 25 ▾ ]        Base : RestedXP adapté ✓       │
│                                                                                  │
│ ☑ Donjons avec leurs quêtes (au meilleur niveau)   ☑ Quêtes de classe           │
│ ☐ Métiers sur le chemin (Herboristerie 85)          ☐ Réputations visées         │
│                                                                                  │
│                         [ Calculer ]                                             │
│ ┌ Aperçu ─────────────────────────────────────────────────────── ◐ probable ┐   │
│ │ 2,4 h · 3 100 XP/h · The Barrens → Stonetalon → The Barrens               │   │
│ │ Donjons : Wailing Caverns au niveau 21 (5 quêtes)                         │   │
│ │ Récompenses : Robe of the Moccasin (21) · Ancient Moonstone Seal (23)     │   │
│ │ Écarts au parcours : +1 quête de classe, +1 donjon                        │   │
│ └────────────────────────────────────────────────────────────────────────────┘   │
│                 [ Valider et livrer ]   [ Ajuster ]   [ Voir les arrêts ]        │
└──────────────────────────────────────────────────────────────────────────────────┘
```
- « Calculer » envoie au pont la même demande que la conversation (même outil, même aperçu) ; « Ajuster » rouvre les
  contrôles ; « Valider et livrer » livre « Forever · Jen · 19-25 » dans RestedXP et dit où le trouver.

## 3. Écran « Talents »

```
┌ Talents ───────────────────────────────────────────────────────────────────────┐
│ Prochain point (niveau 20) : Improved Frostbolt, rang 5          ◐ probable    │
│ Plan jusqu'au niveau 60 : 10-14 Improved Frostbolt · 15-19 Elemental Precision │
│   · 20 Ice Shards… [ Tout l'ordre ▾ ]                                          │
│ [ Talents Forever ] [ Naowh : build ]   (copier, puis coller dans l'addon)     │
│ Respec : aucun gain mesurable, tu gardes ton build.                            │
└────────────────────────────────────────────────────────────────────────────────┘
```

## 4. Écran « Équipement »

```
┌ Équipement ───────────────────────────────────────────────────────────────────┐
│ Poids (Mage, niveau 19) : Int 1 · Puissance des sorts 31 · Critique 17/% …     │
│ [ Naowh : poids ]  [ Forever Companion : échelle ]                            │
│ Liste BiS (frost-mage) : 17 emplacements · [ Naowh : BiS ]                     │
│ À viser au niveau 19 (GearQuest) : Tête · Robe of … (quête, Ashenvale) [ /gq ] │
│ Est-ce une amélioration ? Maj+clic sur un objet ici ou dans le chat.          │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 5. Écran « Exports » et « Mises à jour »

```
┌ Exports ─────────────────────────────┐   ┌ Mises à jour (2) ─────────────────────────┐
│ Naowh : build actuel   [ Copier ]    │   │ ● Données 1.60.1.70391 : prêtes [Valider] │
│ Naowh : macros         [ Copier ]    │   │   [Refuser] [Expliquer]                    │
│ Naowh : poids          [ Copier ]    │   │ ◐ Profil : niveau 19 dans le jeu, 18 au    │
│ Forever Companion      [ Copier ]    │   │   profil [Écrire] [Ignorer]                │
│ Naowh : BiS            [ Copier ]    │   └────────────────────────────────────────────┘
│ (EllesmereUI : éteint, /fb eui on)   │
└──────────────────────────────────────┘
```

## 6. Aide d'accueil (premier lancement seulement, refermable)

```
┌ Bienvenue ─────────────────────────────────────────────────────────────┐
│ Pose ta question en bas, ou choisis un écran à gauche.                 │
│ Maj+clic sur un objet, un sort ou une quête : il part avec ta question.│
│ Les liens [ … ] se copient d'un clic ; colle-les dans l'addon indiqué. │
│                                                        [ Compris ]     │
└────────────────────────────────────────────────────────────────────────┘
```

## Questions pour toi (défaut proposé en premier)
1. **Navigation** : barre latérale à gauche (défaut, comme Naowh et EllesmereUI) ; *autre* : onglets en haut.
2. **Taille par défaut** : 640 × 440, redimensionnable de 520 × 380 à tout l'écran ; *autre* : garder 520 × 360.
3. **Thème** : habillage par EllesmereUI quand il est chargé (défaut) ; *autre* : thème propre toujours.
4. **Ancienne fenêtre** : gardée derrière `/fv classique` jusqu'à ton accord (défaut) ; *autre* : remplacée d'un coup.
5. **Étude web** des bonnes pratiques d'interface (forums, dépôts d'addons, lecture seule) : *défaut* oui, sur ton
   accord ; *autre* : étude locale seulement.
