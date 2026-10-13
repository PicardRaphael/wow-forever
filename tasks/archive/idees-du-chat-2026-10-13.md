# Idées et demandes du chat à intégrer (2026-10-13)

> **Intégré le 2026-10-13** : décisions 250 à 260 de `docs/DECISIONS.md` (une par section, dans l'ordre),
> `docs/ROADMAP.md`, `docs/OPEN_QUESTIONS.md` (BR5, BR9, RXP1, NFB1, PET1, MON7) et
> `docs/research/moteur-generique.md`. Calendrier retenu (décision 251) : T04f, DJ1, RX1, puis LN1 au plus tard le
> 24 octobre, puis EX1, SIM1 et T10a, sans sonde obligatoire (décision 247).

Fichier d'entrée écrit depuis la conversation claude.ai de Raphaël, à sa demande, pour que rien de ce qui a été dit ne se perde.
Ce ne sont **pas encore des décisions** : une session Claude Code les intègre dans `docs/ROADMAP.md`, `docs/DECISIONS.md`
(décisions numérotées), `docs/OPEN_QUESTIONS.md` et les plans concernés, en signalant tout ce qui contredit l'existant,
puis archive ce fichier (ne pas le supprimer). Rien ici n'autorise un accès réseau, une dépendance ou une écriture de
données : ces accords se demandent au plan de chaque tranche, comme d'habitude.

## 1. Règle générale : tout pour toutes les classes (prolonge la décision 243)

Raphaël : « il faut que tout marche pour tout ». Aucune fonction n'est réservée à une classe ; chaque fonction donne la
meilleure source disponible (calcul de notre moteur, sinon addons installés lus en local, sinon données du client), et
la réponse dit ce qui est calculé, ce qui vient d'un addon, ce qui manque. Conséquences à appliquer :

- **Équipement et BiS (T10a)** : aujourd'hui « Mage seulement, les autres classes attendent leur moteur », et « aucune
  liste BiS de la communauté n'est reprise ». À revoir : pour le Mage, poids et BiS calculés ; pour les autres classes,
  dès T10a, les listes BiS des addons installés (Naowh Forever BiS, module AtlasLoot Forever [BiS ToolTip], Forever
  Companion) lues en local, marquées `suppose` et « liste de la communauté », avec l'endroit où looter chaque objet ;
  remplacées par le calcul quand la tranche de la classe arrive.
- **« Est-ce une amélioration ? »** (objet passé par Maj+clic) : utile à tous les niveaux, pas seulement au 60. Au 60,
  par la simulation (SIM1) ; avant, par les poids des statistiques du niveau (calculés pour les classes qui ont un
  moteur, sinon poids de la communauté ou des addons, `suppose`), avec la certitude affichée.
- **BiS par niveau** pour le leveling (déjà dans T10a pour le Mage) : pour toutes les classes, avec la même règle.

## 2. Calendrier jusqu'à la sortie du 4 novembre

La bêta ferme le 21 octobre. Tout ce qui demande une sonde en jeu doit passer avant :
- jusqu'au 20 octobre : T04d (en cours), puis T04f, DJ1, RX1, EX1, chacune avec sa sonde en jeu courte ;
- du 21 octobre au 3 novembre, sans jeu : LN1, SIM1, T10a ;
- le 4 novembre : `docs/LANCEMENT.md`.
Si tout ne tient pas, ce qui sert dès le premier jour passe en premier (LN1, leveling, routes RestedXP) ; SIM1 et T10a
(utiles surtout au niveau 60) peuvent glisser. À réconcilier avec l'ordre actuel de la ROADMAP (LN1 en tête de la
fenêtre sans jeu, puis T04f, DJ1, SIM1, T10a, EX1) : la décision tranche.

## 3. Moteur générique des classes : pas avant la sortie

Étude `docs/research/moteur-generique.md` : écart plausible de 20 à 40 %, impossible à vérifier sans jeu entre le
21 octobre et le 4 novembre. Décision de Raphaël : pas de moteur générique avant la sortie ; CM1 démarre à la sortie,
vérifiée sur ses journaux. Corriger l'étude : un simulateur WoWSims pour Forever existe bien (ElliotWood/Forever,
licence MIT, données au build 1.60.1.70291, `wowsimcli-windows.exe` publié chaque semaine ; fork de MythicSim
sage3648/mythicsim-forever-engine-go), voir décision 224 et `docs/research/wowsims-forever.md`.

## 4. RX1 — Feuilles de route RestedXP (tranche complète, à créer)

Objectif : à ma demande dans le chat, l'agent construit avec moi une feuille de route sur mesure et la livre dans
RestedXP.
- **Questions avant la route**, avec des boutons dans le panneau d'action plutôt qu'un texte à taper : niveaux de
  départ et d'arrivée ; donjons à inclure (avec leurs quêtes) ; solo ou groupe ; récolte de mes métiers sur le chemin ;
  priorité aux quêtes dont la récompense est une amélioration pour moi ; quêtes de classe ; réputations visées.
- **Aperçu avant livraison** : niveaux gagnés, temps estimé, XP par heure, donjons placés, récompenses notables ;
  ajustable (« enlève Wailing Caverns », « ajoute les quêtes de réputation X »).
- **Personnalisation** : classe (quêtes de classe au bon niveau : totems du Chaman, familier du Chasseur, démons du
  Démoniste… ; zones et donjons adaptés) et métiers (voir section 5).
- **Donjons** : un donjon vaut surtout par ses quêtes, qui rapportent beaucoup mais une seule fois ; la route place
  chaque donjon au moment où ses quêtes rapportent le plus (premier passage avec quêtes), jamais en boucle sans raison.
- **Livraison** : API publique de RXPGuides (`_G.RXPGuides.ImportGuide` dans `GuideLoader.lua`, qui analyse un guide
  en texte, l'ajoute et le garde dans `addon.db.profile.guides` ; `RegisterGuide` existe aussi) appelée depuis un
  emplacement de réponse du pont, sans fichier ni `/reload` ; repli : petit addon de guide écrit par le pont jeu fermé.
  Seul le bouton « Import guide » de RestedXP exige un code chiffré lié au compte (guides payants).
- **Format** : syntaxe des guides personnels d'après le code local de RXPGuides (`ParseGuide`) et la documentation
  officielle « create your own RestedXP guide » (lecture réseau à demander au plan).
- **Sources**, en priorité les addons installés, lus en local, seuls nos agrégats entrant dans le dépôt (décision 133) :
  distances et trajets (Shortest Path Forever, qui suit aussi la cible courante de RestedXP ; réseau de marche de Naowh
  Journeys) ; quêtes et chaînes (Questie, Naowh Completo, liste fusionnée de T04d dans le cache) ; donjons et leurs
  quêtes (Naowh Dungeon Journal, Forever Guide, ForeverDungeonJournal) ; objets et récompenses (GearQuest, Naowh BiS,
  AtlasLoot) ; métiers (SkillUp Forever, recettes de Forever Guide) ; XP réelle des quêtes (QuestXP et
  `questcache.wdb`, T04d) ; XP par heure de notre moteur.
- **Exemples de demandes** : « route du niveau 15 à 25 », « route avec les donjons pour mon Chasseur », « monte ma
  réputation X », « monte mon herboristerie de 75 à 150 ».
- **Interdits** : jamais de reprise des guides payants de RestedXP ni d'aucun guide chiffré ; RXPGuides reste exclu
  des données du projet (on n'appelle que son API publique) ; aucun site de « re-chiffrement » de guides.
- **Bouton** « Feuille de route » dans le panneau d'action. Première version par zones (prérequis et niveaux respectés,
  donjons au bon niveau), améliorée ensuite par mes mesures réelles.
- Dépend de T04d et DJ1 ; sonde en jeu avant le 21 octobre si possible, sinon le jour de la sortie.

## 5. Métiers dans le contexte et le profil

Le contexte envoyé par le jeu (ForeverBridge) doit inclure mes métiers et leur niveau de compétence, écrits au profil
au clic comme le reste. Utilisé par RX1 (récolte sur le chemin, quêtes de métier, routes de montée de métier) et MT1.

## 6. EX1 — talents aussi vers Naowh Forever

Export des builds de talents vers Naowh Forever en plus de Talents Forever : module Training de Naowh, préfixe
`!NFB1!` (`NaowhForever_Training\Builds.lua` : table sérialisée par LibSerialize, compressée par LibDeflate, encodée
par EncodeForPrint ; un build porte la classe, le nom, la spécialisation et la liste ordonnée des nœuds de talents, un
point par entrée ; Naowh peut suivre et apprendre ce build). Naowh 1.1.11 ne livre aucun build, mais importe ceux
qu'on lui donne. Format réimplémenté d'après l'observation, sans recopier le code de Naowh (tous droits réservés), tests
de va-et-vient sur un build exporté par Naowh en jeu. Le chat donne pour chaque build le lien Talents Forever et le
code Naowh ; Raphaël pourra abandonner Talents Forever plus tard.

## 7. Sauvegarde et restauration (leçon de la remise à zéro du PC du 2026-10-12)

L'agent sauvegarde ce qui n'est pas sur GitHub : profil `~/.forever/profile.json`, réglages des addons (dossier `WTF`
du jeu : SavedVariables de mes addons), réglages du pont (dossier de la conversation « addons », modèle), journal des
attentes ; copie dans Documents ou OneDrive ; restauration par `forever doctor` (LN1).

## 8. LN1 — cas réels de la remise à zéro à faire vérifier par `forever doctor`

- Jeu déplacé dans `C:\Program Files (x86)\World of Warcraft\_classic_beta_` (avec « (x86) ») : FOREVER_WOW_DIR, pont,
  tâches, addons, journaux.
- Python de base sans les paquets du projet (corrigé, décision 241) : vérification d'import au démarrage.
- GitHub CLI absent ou déconnecté : `gh --version`, `gh auth status`.
- Connexion de Claude Code expirée (« OAuth session expired ») : la conversation du pont échoue ; `forever doctor`
  le détecte et dit de lancer `claude` puis `/login`.
- Tâches planifiées à recréer, addons à réinstaller, profil à recréer, exclusions de l'antivirus.

## 9. Fenêtre du chat : idées d'ergonomie

- Liens par Maj+clic envoyés d'office dans la saisie de `/fv` quand la fenêtre est ouverte.
- Pouvoir réafficher les cartes masquées (aujourd'hui, une carte masquée ne revient que si l'attente change).
- Mécanisme général de questions à choix (boutons dans le panneau) réutilisable par toutes les conversations, pas
  seulement RX1.
- Ne jamais annoncer « voir À valider » quand aucune carte n'est visible.

## 10. Idées notées, non planifiées

- Notifications Discord par webhook (adresse dans `.env`, jamais suivie par git ; utile seulement loin du PC).
- Mode « mise à jour automatique complète » (installer aussi quand un conseil change) : refusé pour l'instant.
- Taille de la réserve du pont (200 emplacements) à revoir avec plus de sessions mesurées.
- FojjiCore lisible seulement en local tant que ForeverAuras n'est pas installé.
- Chaman (CM1) avant la sortie : écarté tant que la fenêtre est pleine (voir section 3).

## 11. Vérifications en jeu restantes

- PET1 : vérifier avec Beast Lore le rang enseigné par une bête (11 rangs supposés, par exemple Ukorsbane).
- BR5 : Maj+clic sur une pile d'objets, la fenêtre de partage de pile s'ouvre-t-elle aussi ?
- Talents d'une autre classe : vu sur le Chasseur, à confirmer avec le build populaire le plus proche.
- MON7 (PV par famille de monstres : ours +20 à 25 %, raptor −20 %) : tuer des monstres de familles variées.
