# Mode d'emploi du plugin forever

Poser ses questions sur World of Warcraft: Forever en langage naturel, depuis n'importe quel dossier, avec des
réponses sourcées par les outils du dépôt. Le plugin ne calcule rien : il aiguille vers le serveur MCP `forever`.

## Installation
Sur chaque PC (Windows), une fois :

1. Prérequis : [Git for Windows](https://git-scm.com/download/win) (il fournit aussi le bash des hooks),
   [uv](https://docs.astral.sh/uv/getting-started/installation/) et Claude Code (`claude`).
2. Cloner le dépôt, puis, **depuis sa racine**, dans PowerShell :

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1
   ```

   `-ExecutionPolicy Bypass` contourne la politique d'exécution des scripts pour ce seul lancement (sans rien changer
   au réglage de Windows). Client installé ailleurs que dans Program Files : ajouter `-WowDir "<dossier du client>"`.
3. Ouvrir un **nouveau** terminal (les variables d'environnement n'arrivent que dans les nouveaux terminaux).

Ce que fait le script (relançable sans risque) :
- fixe les variables d'environnement utilisateur `FOREVER_HOME` (le dépôt) et `FOREVER_WOW_DIR` (dossier du client,
  cherché dans `C:\Program Files (x86)\World of Warcraft\_classic_beta_` puis `C:\Program Files\World of Warcraft\_classic_beta_`) ;
- `uv sync` ;
- déclare la marketplace locale `wow-forever` (le dépôt) et installe le plugin `forever@wow-forever` en portée
  utilisateur ;
- contrôle : `claude plugin validate --strict` (plugin versionné : la mise à jour recopie le plugin quand la version
  de `plugin.json` change), `forever status --offline`, plugin présent et activé.

Second PC : même procédure. L'addon ForeverLogger s'installe à part : `uv run python scripts/install_addon.py`
(il lit `FOREVER_WOW_DIR`, sinon cherche le client dans les deux dossiers Program Files).

## Mise à jour
```powershell
git pull
powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1
```
Le script refait `uv sync`, met à jour la marketplace et recopie le plugin (`claude plugin update`). Redémarrer
Claude Code ensuite.

## Poser une question
Lancer `claude` dans n'importe quel dossier et poser la question en français. Exemples :

| Sujet | Question |
|---|---|
| Talent | « Que fait Improved Frostbolt au rang 3 ? », « Quel talent prendre au niveau 24 ? » |
| Build | « Meilleur build de leveling au niveau 30 ? », « Givre ou Feu en donjon au niveau 50 ? » |
| Respec | « J'ai tout mis en Feu, faut-il respec au niveau 40 ? » |
| Zone | « Où aller au niveau 22 côté Horde ? » |
| Mécanique | « Comment marche Ignite ? », « Hot Streak se cumule comment ? » |
| Leveling | « Combien de temps par monstre au niveau 18 en Givre ? », « XP par heure au niveau 35 ? » |

Dans le dépôt, une ligne de fraîcheur des données s'affiche au démarrage de la session. Ailleurs, rien au démarrage :
le routeur vérifie la fraîcheur (`forever_status`) à la première question sur WoW.

## Mon personnage (profil)
Le profil vit hors du dépôt (`%USERPROFILE%\.forever\profile.json`, ou le fichier désigné par `FOREVER_PROFILE`) ;
plusieurs personnages, un actif. Les réponses le lisent avant tout calcul et le rappellent en une ligne ; une donnée
absente est demandée avant le calcul.
```powershell
uv run forever profile set Givrelame --class Mage --race Orc --faction Horde --level 22 --talents "improvedFrostbolt=5,elementalPrecision=3"
uv run forever profile set Givrelame --profession "Couture=150"
uv run forever profile list
uv run forever profile use Givrelame
uv run forever profile show
uv run forever profile remove Givrelame
```

## Lire la réponse
Réponse courte par défaut ; demander « détaille » ou « pourquoi » pour les raisons, hypothèses et alternatives.
- **Chiffres** : chacun vient d'un outil forever de la session (outil cité entre parenthèses).
- **Certitude** : `certain` (lu dans le client), `probable`, `supposé` (hypothèse à vérifier en jeu).
- **Attention** : une hypothèse ou un angle mort qui peut changer la conclusion.
- **Pied de réponse** : `Certitude : … · Version … · Fraîcheur … (date)`.
- Réponse « Le serveur forever ne répond pas : … » : `FOREVER_HOME` est faux (ou le dépôt a bougé) ; relancer le script
  d'installation depuis le dépôt, puis ouvrir un nouveau terminal.
- Message `[forever:chiffres]` en fin de réponse : un chiffre de jeu de la réponse ne vient d'aucun outil forever de
  la session ; ne pas s'y fier, redemander la valeur.

## Ce que le plugin ne sait pas encore
PvP (PV1, PV2), boss et butin des donjons (DJ1), Legacy (LG1, LG2), métiers (MT1), réputations (RP1), hôtel des
ventes (EC1), quêtes et XP propres à Forever (T04d), mana des combats longs (T05b), mémoire du joueur (T07), raid
complet (T09), équipement (T10), consommables (T11), autres classes que le Mage (T12). Sur ces sujets, il répond
« je ne sais pas » et cite la tranche de `docs/ROADMAP.md` qui les couvrira.

## Évaluation
Jeu de questions : `plugin/evals/` (cas positifs et questions voisines qui ne doivent pas déclencher le plugin). La
CI contrôle la suite sans modèle (`tests/unit/test_plugin_evals.py`) ; le passage avec le modèle se lance à la main
(coût : voir `docs/research/plugin-eval-T06.md`), depuis la racine du dépôt :

```powershell
claude plugin eval plugin --trust-plugin --mocks off --allow-tools "mcp__plugin_forever_forever__*" --runs 1 --ablation none -j 4 --judge-model opus --max-cost-usd 15 --no-publish --keep-temp --json plugin/evals/results/passage.json
uv run python scripts/plugin_eval_report.py plugin/evals/results/passage.json
```

`--keep-temp` garde les traces (le rapport y relit les messages du contrôle des chiffres) ; les supprimer ensuite
(dossiers `claude-eval-*` du dossier temporaire). Le second script calcule les seuils de la tranche (aiguillage, outil attendu, aucun chiffre inventé, certitude
affichée) et le taux de fausses alertes du contrôle des chiffres. `plugin/evals/results/` n'est pas versionné. Un workflow GitHub manuel est prêt, non appliqué : `git apply tasks/plugin-eval.patch`
(secret `ANTHROPIC_API_KEY` du dépôt).
