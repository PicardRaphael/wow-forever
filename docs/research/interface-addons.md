# Interface des addons : principes pour la fenêtre de ForeverBridge (CJ1, bloc 6)

Étude du 2026-10-15 : locale d'abord (fenêtres de Naowh Forever 1.1.15, Forever Companion 1.0.0, EllesmereUI 9.5.4,
RestedXP 4.11.23, lues sur disque, aucun code repris), puis web en lecture seule (accord de l'utilisateur du
2026-10-15). Idées reformulées avec leur source, consultées le 2026-10-15 ; aucun code copié ni exécuté.

## Constat de départ
- Forever partage l'architecture d'interface de Mainline et la plupart de ses API (notes du 1.60.1 ; valeurs secrètes
  actives) : https://warcraft.wiki.gg/wiki/Patch_1.60.1/API_changes/notes. Les conseils « Retail » valent donc ici ;
  bêta : à revérifier au lancement.

## Principes retenus
1. **Barre latérale** : libellés toujours visibles (un repli en icônes reste une option, jamais le défaut) ; l'entrée
   choisie porte deux repères (barre d'accent et étiquette plus vive), pas une couleur seule ; fond distinct du
   contenu. Sources : https://www.nngroup.com/articles/tabs-used-right/, https://www.nngroup.com/articles/icon-usability/,
   largeur de liste d'AceGUI TreeGroup (https://github.com/WoWUIDev/Ace3) et de WeakAuras (ordre de 170 px).
2. **Pas de chevauchement** : largeur des boutons mesurée sur leur libellé, passage à la ligne au-delà de la largeur
   disponible, recalcul dans `OnSizeChanged` ; `FontString:GetUnboundedStringWidth` en jeu
   (https://warcraft.wiki.gg/wiki/API:FontString_GetStringWidth) ; `SetResizeBounds` pour les bornes
   (https://warcraft.wiki.gg/wiki/API:Frame_SetResizeBounds).
3. **Menus** : UIDropDownMenu est déprécié ; un vrai menu déroulant passerait par Blizzard_Menu (`MenuUtil`,
   `DropdownButton`) : https://warcraft.wiki.gg/wiki/Blizzard_Menu_implementation_guide. Notre menu « Plus » est un
   simple cadre de boutons (aucun menu de Blizzard touché, aucun taint).
4. **Sécurité** : rien de protégé, parent `UIParent`, aucun ancrage à un cadre de Blizzard ou de combat ; Échap par
   `UISpecialFrames` ; une action d'affichage en combat se diffère à `PLAYER_REGEN_ENABLED`
   (https://warcraft.wiki.gg/wiki/Secure_Execution_and_Tainting, https://warcraft.wiki.gg/wiki/Secret_Values).
5. **Habillage par EllesmereUI en lecture seule** : fonctions publiques lues sur disque (`ResolveActiveAccent`,
   `GetFontPath`), appel protégé, accent de repli sans EllesmereUI, aucune dépendance dans le `.toc`, rien d'écrit
   (pas de `RegAccent`, qui enregistre un rappel chez lui). Exemples de skins qui relisent l'accent sans le modifier :
   https://www.curseforge.com/wow/addons/mountsjournal-ellesmereui-skin.
6. **Accessibilité** : jamais une information par la couleur seule (WCAG 1.4.1,
   https://developer.mozilla.org/en-US/docs/Web/Accessibility/Understanding_WCAG/Perceivable/Color_contrast) ;
   contraste visé 4,5:1 pour le texte et 3:1 pour les repères, accent d'EllesmereUI compris.

## Appliqué au bloc 6a
Barre latérale de 150 px (libellés visibles, barre d'accent et étiquette vive pour l'entrée choisie) ; fenêtre
640 × 440, bornes 520 × 380 ; rangée des réponses qui passe à la ligne (largeur mesurée en caractères, faute de mesure
du texte dans le client simulé des tests) ; menu « Plus » en boutons ; thème lu chez EllesmereUI sans écriture ; type
choisi dans l'assistant marqué par un bouton grisé et son libellé, pas par la couleur.

## À reprendre (6b ou essai en jeu)
- Mesure réelle du texte (`GetUnboundedStringWidth`) en plus de l'estimation par caractères.
- Réponses en cartes avec une liste à défilement (`ScrollBox`) ; taille de texte et échelle de la fenêtre réglables.
- Contraste de l'accent d'EllesmereUI sur notre fond sombre (éclaircir s'il est trop faible).

## Incertain
Build de Forever différent entre les notes (70291) et les pages d'API (69913) ; `GetUnboundedStringWidthForText`
(12.0.5) récente ; aucune variable du jeu trouvée pour la taille du texte ou le mode daltonien.
