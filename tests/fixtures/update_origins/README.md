# Fixtures de T08e : sous-arbre du Guerrier et règles `correctif_serveur`

Extraits de `forever/data/<version>/classes.json` (`/classes/Warrior`) et des règles `correctif_serveur` de
`classes.json` dans `origins.json`, tirés de git le 2026-10-07 (script de l'étape 0 du plan T08e, hors du paquet).
JSON compact, fins de ligne LF. Empreinte : sha256 du JSON trié compact (`sort_keys`, séparateurs `,` et `:`).

| Fichier | Version | Commit | Empreinte |
| --- | --- | --- | --- |
| `warrior-70170-r5.json` | 1.60.1.70170 r5 | `2ca98f694cb3` (`14495a5~1`) | `7d8cde8a03f563c3f4559229f9bb985a6e024c20ad6f4067b3665502770d7f9b` |
| `warrior-70245-r1.json` | 1.60.1.70245 r1 | `14495a568db2` (`14495a5`) | `16324ac23376f4c9fd4103dbfc1c1815f556355ab4320739b77acd0a6a12431d` |
| `warrior-70245-r3.json` | 1.60.1.70245 r3 | `0769b8a91eea` (`0769b8a`) | `6b0700fb9dab7d1e67eb3f77ef19b7bdfa7fea37a89c6e28462a927d08ea8324` |
| `hotfix-rules-70170-r5.json` | 1.60.1.70170 r5 | `2ca98f694cb3` (`14495a5~1`) | `79bec9bb3b93bc8bea5f531284cdb86772e2fbd5e291f81f0be2c22d7ec2a252` |
| `hotfix-rules-70245-r3.json` | 1.60.1.70245 r3 | `0769b8a91eea` (`0769b8a`) | `052bcead333698c2b5839bf95c041364467d8aeca460647a8fe0ea4f97200521` |

Contrôles faits à l'extraction :

- 70245 r2 (`6f2e8af`) : sous-arbre du Guerrier identique à r1 (r2 n'a changé que `monsters.json`) ; aucune règle
  `correctif_serveur` dans r1 ni r2 (r1 décodée sans le `DBCache.bin` de 70245).
- r3 identique à 70170 r5 hors métadonnées (`metadata_keys` d'`origins.json`) : oui ;
  mêmes chemins `correctif_serveur` : oui (49 chemins, poussée(s) [112347]).
