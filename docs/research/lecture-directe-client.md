# Lecture directe du client, sans wago.tools (secours documenté, T08b, bloc G)

Note du 2026-10-01, sans code : ce qu'il faudrait pour décoder une version du jeu si wago.tools devenait indisponible
ou en retard sur un build. Rien n'est implémenté ; la voie actuelle (`forever fetch`, `forever fetch --gametables`)
reste la seule utilisée. Aucune valeur de jeu ici.

## Ce que porte le dossier du client

| Élément | Où | Rôle |
| --- | --- | --- |
| Archives CASC | `<installation>/Data/data/*.idx`, `data.*` | contenu du jeu : fichiers DB2 (`dbfilesclient/*.db2`), GameTables (`gametables/*.txt`) |
| `.build.info` | racine de l'installation | build installé, clé de construction (`BuildKey`), clé de configuration CDN (`CDNKey`), produit |
| Configuration de build | archives CASC, par `BuildKey` | racine (`root`) : identifiant de fichier (FileDataID) → clé de contenu ; encodage : clé de contenu → clé d'encodage |
| Clés TACT | `Logs/Hotfix.log` (lignes `Requesting TactKey`, `DBReply Table TactKey`) et `DBCache.bin` | déchiffrent les blocs chiffrés de certaines tables ; une table chiffrée sans sa clé est illisible |
| `Cache/ADB/<locale>/DBCache.bin` | dossier du client | valeurs des correctifs du serveur (enregistrements ajoutés ou remplacés), poussées listées dans `Hotfix.log` (décodage prévu en T08) |

## Étapes d'une lecture autonome

1. Lire `.build.info` : produit `wow_classic_beta`, `BuildKey`, version (déjà fait par `forever/pipeline/client_builds.py`).
2. Ouvrir les index CASC locaux (`*.idx`) pour retrouver un fichier par sa clé d'encodage ; lire la configuration de
   build puis le fichier `root` (FileDataID → clé de contenu) et `encoding` (clé de contenu → clé d'encodage).
3. Résoudre chaque table voulue par son **FileDataID** : les identifiants des GameTables sont déjà notés dans
   `decode_rules.json` (`gametables`) ; ceux des DB2 se trouvent dans la liste communautaire de fichiers (listfile)
   ou dans WoWDBDefs, à noter de la même façon.
4. Décompresser les blocs BLTE (zlib, parfois chiffrés : clé TACT nécessaire, sinon la table est déclarée illisible,
   jamais remplacée par une autre).
5. Décoder le format WDC (DB2) avec les définitions de colonnes de WoWDBDefs pour le build (les noms de colonnes de
   `forever/pipeline/tables.py` viennent de là) et écrire le même CSV que wago.tools, pour que `forever decode` reste
   inchangé ; les GameTables sont déjà du texte.
6. Comparer, sur un build où les deux voies existent, chaque CSV produit à celui de wago.tools (empreinte par table)
   avant de se fier à la voie autonome.

## Ce qui resterait côté serveur

Les fichiers `gametablesserver/*` ne sont jamais livrés au client (statistiques de base par race, esquive et parade,
bonus d'XP) : aucune lecture directe ne les rend. Les correctifs du serveur n'existent que dans `DBCache.bin`.

## Coût estimé et décision

Lecteur CASC, BLTE et WDC à écrire et maintenir (plusieurs formats, clés TACT), sans dépendance ajoutée selon la
décision 16 : à n'entreprendre que si wago.tools manque un build joué ; décision à prendre à ce moment, avec
l'utilisateur.
