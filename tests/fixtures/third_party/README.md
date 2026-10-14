# Bibliothèques tierces des tests (oracle d'EX1, décision 267)

Copiées telles quelles, octet pour octet, depuis Naowh Forever 1.1.12 installé
(`Interface/AddOns/NaowhForever/Libs/`, client 1.60.1.70374), le 2026-10-14. Elles servent **seulement aux tests**
(`tests/unit/test_export_codec_lua.py` et suivants), exécutées sous `lupa` pour relire les chaînes produites par
`forever/exports/` et en produire que forever relit. Elles ne sont **jamais livrées** avec un addon de forever-core ni
appelées par le code de `forever/`.

| Fichier | Bibliothèque | Version | Licence | SHA-256 |
| --- | --- | --- | --- | --- |
| `LibSerialize/LibSerialize.lua` | LibSerialize (Ross Nichols, https://github.com/rossnichols/LibSerialize) | MINOR 7 | MIT (texte complet dans l'en-tête du fichier) | `165b5716915c083a6df41fa3c5df27815cf45cc9224ea722797a77664f7e92a6` |
| `LibDeflate/LibDeflate.lua` | LibDeflate (Haoqian He, https://github.com/SafeteeWoW/LibDeflate) | 1.0.2 | zlib (`LibDeflate/LICENSE.txt`) | `b6cf1bdc38dfae0c2deadfcb2cbf4e53d9dee6fb8f0ad5a03820ccf3635b7195` |
| `LibDeflate/LICENSE.txt` | licence de LibDeflate | — | — | `d789a4b3d104bb9f559b2f19048d356c67ea695dde4b1748f900ccb210a42450` |

Aucune modification : les tests posent un `LibStub` minimal avant de les charger. Une mise à jour se refait par la même
copie, empreintes revues ici.
