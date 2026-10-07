# Arbres de talents : forever face à Talents Forever (FA1)

Généré par `uv run forever talents tf crosscheck --out <fichier>` (lecture locale, écarts seulement ; rien de l'addon n'est recopié). Le client fait foi : un écart est signalé, jamais tranché par l'addon.

- Talents Forever 0.37.1 : `Data.lua` build 1.60.1.70170, généré le 2026-10-04, codes v6, empreinte `4f5f53571fb7`.
- forever : données installées 1.60.1.70245.
- Appariement : arbre au même indice, même sort, même rangée, même colonne.
- Écarts : nœuds numérotés autrement 4, sans correspondance 3, prérequis 1, noms d'arbres 2.

| Classe | Positions TF | Talents forever | Appariés | Export |
| --- | --- | --- | --- | --- |
| Druid | 52 | 52 | 52 | possible |
| Hunter | 50 | 51 | 50 | bloque |
| Mage | 54 | 54 | 54 | possible |
| Paladin | 50 | 50 | 50 | possible |
| Priest | 53 | 53 | 53 | possible |
| Rogue | 53 | 53 | 53 | possible |
| Shaman | 50 | 50 | 50 | possible |
| Warlock | 52 | 52 | 50 | bloque |
| Warrior | 52 | 52 | 52 | possible |

## Écarts

### Hunter

- Sans correspondance (seulement_forever) : Improved Serpent Sting (`improvedSerpentSting`, Marksmanship ; position chez forever : rangée 4, colonne 4, sort 19464).
- Prérequis : Intimidation (`intimidation`), forever `—`, Talents Forever `bestialSwiftness`.
- Export : export bloqué (Hunter) : Improved Serpent Sting (improvedSerpentSting, Marksmanship, rangée 4, colonne 4) absent de Talents Forever 0.37.1. Talent sans correspondance jamais deviné ; table reconstruite à chaque appel, donc revérifiée à chaque mise à jour de l'addon.

### Priest

- Nom d'arbre (cosmétique, arbres appariés par indice) : arbre 3, forever « Shadow Magic », Talents Forever « Shadow ».

### Shaman

- Nom d'arbre (cosmétique, arbres appariés par indice) : arbre 1, forever « Elemental Combat », Talents Forever « Elemental ».

### Warlock

- Sans correspondance (position_inconnue) : Improved Life Tap (`improvedLifeTap`, Affliction ; position chez Talents Forever : rangée 1, colonne 1, sort 18182).
- Sans correspondance (position_inconnue) : Amplify Curse (`amplifyCurse`, Affliction ; position chez Talents Forever : rangée 3, colonne 3, sort 18288).
- Export : export bloqué (Warlock) : Improved Life Tap (improvedLifeTap, Affliction) : rangée inconnue dans nos données (question CLS1), rangée 1 chez Talents Forever ; Amplify Curse (amplifyCurse, Affliction) : rangée inconnue dans nos données (question CLS1), rangée 3 chez Talents Forever. Talent sans correspondance jamais deviné ; table reconstruite à chaque appel, donc revérifiée à chaque mise à jour de l'addon.

### Warrior

- Nœud numéroté autrement : Lingering Rage (`lingeringRage`), forever 110857, Talents Forever 113564.
- Nœud numéroté autrement : Furious Precision (`furiousPrecision`), forever 105953, Talents Forever 113565.
- Nœud numéroté autrement : Gore Drinker (`goreDrinker`), forever 113569, Talents Forever 113566.
- Nœud numéroté autrement : Iron Will (`ironWill`), forever 113570, Talents Forever 110857.
