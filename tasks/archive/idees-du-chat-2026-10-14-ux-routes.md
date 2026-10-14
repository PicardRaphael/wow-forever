# Idées du chat à intégrer (2026-10-14) : interface du chat en jeu et feuilles de route

Fichier d'entrée écrit depuis la conversation claude.ai de Raphaël, à sa demande, après son essai en jeu du
2026-10-14 (personnage neuf « Bob », Alliance, niveau 1, Coldridge Valley / Dun Morogh). À traiter **après LN1** :
une tranche d'interface (proposée : UX1) et des corrections de RX1 (dans RX2 ou avant). Puis archiver dans
`tasks/archive/`.

## 1. Interface : « digne des plus grands addons » (demande de Raphaël)

Constat en jeu : la fenêtre est jugée laide et peu claire.
- La barre de boutons déborde : « Feuille de route » et « Livrer dans RestedXP » se chevauchent ; huit boutons sur une
  ligne, sans hiérarchie.
- Le bouton « Feuille de route » envoie une phrase toute faite, puis rien n'indique qu'il faut écrire dans la zone de
  saisie ; on ne comprend pas quoi faire.
- « À valider (4) » s'affiche alors que la réponse dit « Aucune question n'attend de validation » : contradiction.
- Les réponses sont des blocs de texte denses (aperçu, premiers arrêts, attention), difficiles à lire.

Attendu : une refonte complète de l'interface de ForeverBridge, au niveau des meilleurs addons (Naowh Forever,
EllesmereUI, RestedXP, Questie). Pistes à étudier au plan :
- **Étude de l'existant (décision 264)** : regarder en local, sans recopier leur code, comment Naowh Forever,
  EllesmereUI et RestedXP organisent leurs fenêtres (onglets, panneaux, cartes, typographie, couleurs, icônes, aides),
  et les bonnes pratiques d'interface des addons WoW.
- **Organisation** : onglets ou navigation claire (Chat, Routes, Exports, Mises à jour, Addons), barre d'actions
  hiérarchisée (actions principales visibles, le reste dans un menu), jamais de bouton qui déborde ; tailles et
  espacements cohérents ; fenêtre redimensionnable sans casser la mise en page.
- **Feuille de route en assistant** : un écran dédié avec de vrais contrôles (niveau de départ et d'arrivée par
  curseur ou liste, cases à cocher pour donjons, quêtes de classe, métiers, réputations), un bouton « Calculer », puis
  un aperçu lisible (durée, XP/h, zones dans l'ordre, donjons, récompenses) et un bouton « Livrer dans RestedXP » ;
  aucune saisie libre obligatoire.
- **Réponses mises en forme** : cartes avec titres, icônes de certitude, listes courtes, liens cliquables ; textes en
  langage de joueur.
- **Cohérence** : le compteur « À valider » et les réponses disent toujours la même chose ; une aide d'accueil courte
  au premier lancement.
- **Thème** : sobre et lisible, compatible avec EllesmereUI (couleurs, police), clair et sombre si possible.
- Tests sous lupa et procédure en jeu ; aucune fonction protégée, rien en combat.

## 2. Feuilles de route : défauts vus sur la première route réelle (à corriger dans RX2 ou avant)

- **PRIORITÉ 1, BLOQUANT avant la sortie — mauvais point de départ** : pour un Gnome de niveau 1 à Coldridge Valley
  (Dun Morogh), la route commence en Elwynn Forest (zone de départ humaine) ; la réponse le reconnaît elle-même.
  Raphaël l'a signalé deux fois : c'est le premier défaut à corriger après LN1, avant toute autre chose. La route doit
  partir de la position actuelle du personnage (carte et coordonnées du contexte envoyé par le jeu) et, au niveau 1,
  des quêtes de la zone de départ de sa race (Gnome et Nain : Coldridge Valley ; Humain : Northshire ; etc.) ; trouver
  pourquoi l'état de départ l'ignore (race non reliée à sa zone de départ, position non transmise au planificateur,
  coût du trajet initial absent) et ajouter un test par race de départ, Alliance et Horde.
- **Quêtes suspectes** : la route 1 à 10 passe par Stormwind puis des quêtes « The Alliance Needs… » (cuir, bandages)
  rendues à Ironforge, dont l'XP « paraît très élevée » d'après la réponse elle-même. Vérifier leur nature (quêtes
  d'effort de guerre, répétables, niveau requis, XP réelle du client) et les exclure si elles ne sont pas des quêtes de
  leveling normales à ce niveau.
- **Deux aperçus contradictoires** dans la même conversation (1 à 6, puis 1 à 10) : un seul aperçu à jour, remplacé
  quand on ajuste.
- **Nom du guide livré** dans RestedXP : il doit être clair et reconnaissable dans la liste de RestedXP (par exemple
  « Forever · Bob · 1-10 »), et la réponse doit dire où le trouver après la livraison.

## 3. Suite de l'essai du 2026-10-14

- **Questions dans le chat, pas dans « À valider »** : les questions de la feuille de route (donjons, etc.) sont
  arrivées comme des cartes du panneau « À valider », ce que Raphaël trouve mauvais. L'agent pose ses questions dans
  la conversation elle-même, comme un humain (une question à la fois, avec des boutons de réponse sous le message si
  utile) ; le panneau « À valider » reste réservé aux mises à jour et au profil.

- **Livraison dans RestedXP vérifiée en jeu** (répond à RXP1) : après un clic sur « Livrer dans RestedXP », le guide
  apparaît bien dans RestedXP. Le mécanisme `ImportGuide` fonctionne.
- **Livraison automatique** : Raphaël ne veut pas de bouton séparé. Quand il demande une feuille de route et valide
  l'aperçu, elle est livrée d'office dans RestedXP (et remplace la précédente du même personnage), avec un message
  qui dit où la trouver.
- **Qualité de la route : « une catastrophe »** (mots de Raphaël). Le simulateur la donnait plus rapide que le parcours
  de RestedXP, alors qu'elle est absurde en jeu : la comparaison chiffrée ne suffit pas. À ajouter avant toute nouvelle
  route :
  - des **garde-fous de vraisemblance** vérifiés par des tests : départ dans la zone de départ de la race au niveau 1,
    puis la zone voisine prévue pour sa faction ; aucune quête d'une autre race, d'une autre faction, d'effort de
    guerre, répétable ou d'artisanat sans raison ; aucun détour vers une capitale ou un autre continent aux bas
    niveaux sans raison ; pas de farm quand des quêtes de la zone restent disponibles ;
  - une **recette de référence** : pour chaque zone de départ (Alliance et Horde), la route 1 à 10 calculée doit suivre
    le même enchaînement de zones que les parcours gratuits de RestedXP (comparaison qualitative, décision 270), sinon
    elle est refusée et l'écart expliqué ;
  - une **relecture humaine** de la première route de chaque zone de départ (texte de la route montré à Raphaël avant
    d'être livré par défaut).

## 4. Exports : ce que Raphaël veut vraiment (2026-10-14)

- Il ne veut **pas** de profil EllesmereUI par rôle : le lien [EllesmereUI : rôle] et la bascule de profil ne doivent
  plus être proposés par défaut (réglage à activer seulement s'il le demande un jour).
- Ce qu'il veut dans Naowh Forever, c'est sa **liste BiS** (format « !NBIS1! », déjà prêt depuis EX1, rempli par T10a),
  pour la voir dans la fenêtre BiS de Naowh avec les lieux de butin. À discuter au calendrier : avancer T10a (BiS par
  niveau pour le leveling dès la sortie, pour toutes les classes selon la décision 250 et suivantes : calculé pour le
  Mage, listes des addons pour les autres) plutôt que de la laisser glisser après le 4 novembre.
- **Ordre validé par Raphaël le 2026-10-14, après LN1** : 1) correction des feuilles de route (section 2 et 3,
  priorité absolue) ; 2) T10a, liste BiS exportée vers Naowh, avancée avant la sortie ; 3) refonte de l'interface
  (section 1). Les macros Naowh restent proposées (utiles mais facultatives).
- **EllesmereUI : « mon UI, c'est mon UI ».** Rien ne doit jamais modifier son interface sans demande explicite : pas
  de bascule de profil automatique ni par rôle (la bascule de `/fb role` est désactivée par défaut), pas de profil
  proposé d'office ; l'export de profil EllesmereUI reste disponible seulement s'il le demande.
- **Talents proposés même sans point à placer.** Au niveau 1, le bouton Talents répond « pas de point avant le
  niveau 10, pas de lien » : il doit au contraire proposer dès maintenant le **plan de talents** du personnage (build
  conseillé du niveau 10 à l'objectif, point par point dans l'ordre de prise), avec le lien Talents Forever **et** le
  code Naowh `!NFB1!`, pour qu'il l'importe dans le Training Planner de Naowh (onglet Builds, « Import ») et le suive
  niveau par niveau ; calculé pour le Mage, build de la communauté le plus proche pour les autres classes (ordre généré
  signalé comme tel). Naowh affiche « Level by level : the order the points are taken in » : c'est exactement ce que le
  plan doit remplir.
