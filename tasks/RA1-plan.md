# RA1 — Rappels d'aura en jeu (Chasseur d'abord), dans le panneau d'EllesmereUI

Demande du 2026-11-16 (Jen-Krypto, Chasseur) : une icône que je peux déplacer, qui me rappelle en combat
l'aura qui manque (Aspect du faucon : Aspects mortels 5/5 ne joue que sous Faucon) et hors combat un autre rappel
(Guépard, familier…). Réglages dans EllesmereUI, sans modifier EllesmereUI, et sans rien perdre à ses mises à jour.

## Avant le chantier (décision 288)

- **Qui maintient déjà ça mieux que nous ?**
  - EllesmereUI AuraBuff Reminders 9.8.8 (installé) : rappel « Aspect » du Chasseur, mais le Guépard et la Meute y
    comptent comme aspects valables ; en combat, il ne lit qu'une liste blanche de sorts (les aspects n'y sont pas)
    et garde sinon l'état d'avant le combat. Ne couvre pas « Guépard encore actif en combat ».
  - HunterSuite (CurseForge, Forever 1.60.1, mis à jour le 2026-11-14, non installé) : alerte « aucun aspect » et
    « Guépard ou Meute en combat », carte du familier, minuteur du Tir automatique. **Fait déjà l'essentiel** ; pas
    d'intégration à EllesmereUI ni de règles réglables.
  - AppelSwingsForever (installé) : minuteur du Tir automatique ; rien à refaire ici.
- **Que se passe-t-il au prochain patch ?** Aucun identifiant ni nom de sort dans le Lua : les sorts d'une règle
  sont lus dans `classes.json` (tous les rangs) et écrits par `forever` dans un fichier de données de l'addon à
  l'installation, régénéré par la veille. Seul risque : l'API de plugin d'EllesmereUI (`EllesmereUI.RegisterPlugin`,
  `EllesmereUI_Panel.lua`) change ; sous `pcall`, l'addon garde alors ses commandes `/` et le signale.

## Décisions à prendre avant l'exécution (à moi)

**Plan validé le 2026-11-16 (« Oui, on le construit »)** : 1. construire RA1 (HunterSuite non installé) ;
2. exception aux lignes rouges accordée pour la seule icône de rappel d'aura (décision à écrire dans
`docs/DECISIONS.md`, `docs/ADDON.md` et `CLAUDE.md` amendés en conséquence) ; 3. icône non cliquable (défaut du plan).

1. **Construire ou installer HunterSuite ?** RA1 apporte : règles réglables (toute classe plus tard), intégration
   au panneau d'EllesmereUI, données tenues par la veille. Sinon : installer HunterSuite et s'arrêter là.
2. **Lignes rouges (nouvelle décision)** : `docs/ADDON.md` dit « seul ForeverBridge dessine » et « aucun conseil de
   rotation en combat ». Une icône de rappel d'aura (texture d'icône, pas de bande de pixels, rien de lu à l'écran)
   affichée en combat demande une décision qui les amende pour ce seul usage.
3. **Icône cliquable ?** Par défaut, non : elle prévient seulement. Option : bouton sécurisé que je clique moi-même
   pour lancer l'aspect (aucune fonction d'action appelée par le code, mais à trancher face à la ligne rouge).

## Blocs

### 0. Sonde en jeu (bloquante, avant tout code)

En combat, le client de Forever masque la plupart des auras aux addons (valeurs secrètes). À relever, hors combat
puis en combat contre un monstre facile, avec Faucon puis Guépard :

```
/dump C_Spell.GetSpellInfo("Aspect du faucon")
/dump C_UnitAuras.GetPlayerAuraBySpellID(<spellID lu juste au-dessus>)
/dump issecretvalue and issecretvalue(C_UnitAuras.GetPlayerAuraBySpellID(<spellID>))
/dump C_UnitAuras.GetAuraDataByIndex("player", 1, "HELPFUL")
/dump GetShapeshiftForm()
```

Et si `UNIT_AURA` et `UNIT_SPELLCAST_SUCCEEDED` (joueur) arrivent en combat avec un sort lisible (petite sonde de
ForeverBridge, `docs/ADDON.md` §7). Issue :
- **aura lisible en combat** → rappel exact (s'affiche tant que l'aura manque, disparaît dès qu'elle est posée) ;
- **secrète** → rappel à l'entrée en combat d'après l'état d'avant le combat, effacé quand le sort attendu est vu
  lancé (si `UNIT_SPELLCAST_SUCCEEDED` reste lisible), sinon au bout d'un délai réglable ; dit dans l'aide de
  l'addon ;
- résultat écrit dans `docs/ADDON.md` et `docs/RESOLVED_QUESTIONS.md`.

### 1. Addon `addon/ForeverRappels` (0.1.0)

- Règles : `{ quand = "combat" | "hors_combat", attendu = <groupe de sorts>, interdit = <groupe>, son, active }`.
  Règles par défaut du Chasseur : en combat, Faucon attendu, Guépard et Meute interdits ; hors combat, familier
  absent ou mort ; Guépard hors combat proposé mais éteint par défaut.
- Groupes de sorts (`aspect_faucon`, `aspect_guepard`…) lus dans `RappelsData.lua`, généré par `forever` depuis
  `classes.json` (tous les rangs, version et empreinte des données en tête).
- Icône : celle du sort attendu, déplaçable (verrouiller/déverrouiller), position gardée dans `ForeverRappelsDB`
  (initialisée à `ADDON_LOADED`), taille, son facultatif, lueur.
- Lecture des auras sous `pcall` et `issecretvalue` ; mise à jour sur `UNIT_AURA`, `PLAYER_REGEN_DISABLED`,
  `PLAYER_REGEN_ENABLED`, `UNIT_PET` ; chaque `RegisterEvent` sous `pcall` ; aucun journal de combat, aucune
  fonction d'action.
- Commandes : `/rappels` (verrouiller, tester, liste des règles).

### 2. Page dans EllesmereUI

- `EllesmereUI.RegisterPlugin("ForeverRappels", { label = "Rappels", modules = { … } })` sous `pcall`, si
  EllesmereUI est chargé (`## OptionalDeps: EllesmereUI`) : activer chaque règle, son, taille, verrou, bouton
  « Tester ». Habillage par sa couleur et sa police (décision 274 : lecture seulement).
- Sans EllesmereUI, ou si la fonction a changé : les commandes `/rappels` suffisent, message une fois.

### 3. Installation et veille

- `scripts/install_addon.py` installe `ForeverRappels` comme ForeverLogger (jeu fermé) ; la veille régénère `RappelsData.lua`
  quand `classes.json` change (rapport « valeurs qui changent », décision 288).

## Tests (d'abord, rouges, committés)

- Lua sous `lupa` (client simulé `tests/fixtures/bridge/wow_stub.lua` étendu : `C_UnitAuras`, `issecretvalue`,
  `EllesmereUI.RegisterPlugin`) : en combat sans Faucon → icône visible ; Faucon posé → cachée ; Guépard en
  combat → visible ; aura secrète → repli décrit au bloc 0 ; hors combat sans familier → rappel ; position
  relue après rechargement ; sans EllesmereUI → pas d'erreur ; `RegisterPlugin` qui lève → pas d'erreur.
- `RappelsData.lua` généré depuis une fixture `classes.json` (aucun chiffre de jeu dans les tests) ; version et
  empreinte présentes.
- `scripts/check_addon.py` et `tests/unit/test_addon_rules.py` passent sur le nouvel addon ; aucun nombre de jeu
  dans `addon/ForeverRappels`.

## Registre et questions

- Pas de mécanique de combat calculée : pas d'entrée au registre. `docs/OPEN_QUESTIONS.md` : lisibilité des auras
  en combat (fermée par le bloc 0) ; relance d'un aspect actif avec `!` (temps de recharge global, mana).

## Essai en jeu (décision 273)

1. `/reload` ; EllesmereUI → section « Rappels » visible ; « Tester » montre l'icône ; la déplacer, `/reload`,
   elle reste en place.
2. Guépard, attaquer un monstre : l'icône Faucon apparaît (et le son) ; lancer Faucon : elle disparaît.
3. Hors combat, renvoyer le familier : rappel « familier » ; l'appeler : il disparaît.
4. Mettre EllesmereUI à jour (ou le désactiver) : ForeverRappels marche toujours.
