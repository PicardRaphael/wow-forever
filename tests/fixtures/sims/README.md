# Extraits des simulateurs de la communauté (MS1, décision 301)

Copiés le 2026-11-04 (puis le 2026-11-08 pour SIM2) depuis les clones épinglés en cache, sans modification (seulement tronqués aux blocs lus) :

| Fichier | Source | Révision |
| --- | --- | --- |
| `wowsims/proto/shaman.proto`, `wowsims/proto/mage.proto` | wowsims/forever (MIT), `proto/<classe>.proto`, message `<Classe>Talents` seulement | `3a3176c5a81968d2141cf6550f15526e765997a4` |
| `wowsims-64b21da/proto/mage.proto` | wowsims/forever (MIT), `proto/mage.proto`, message `MageTalents` seulement (copié le 2026-11-08, SIM2 : option `talent_max_rank`) | `64b21da8f8b2f3bb2a38921d2257158b774bbbf2` |
| `mythicsim/engine/src/classes/shaman/prepare/layout.rs` | sage3648/mythicsim-forever-engine (MIT), fichier entier | `b1f646eabd5fa3e9a8168af7e1ee4e53843d8eb3` |
| `mythicsim/engine/src/classes/mage/prepare.rs` | même dépôt, constantes `FOREVER_ARCANE` à `FOREVER_TREES` seulement | `b1f646eabd5fa3e9a8168af7e1ee4e53843d8eb3` |
| `mythicsim/engine/upstream/sources.json`, `mythicsim/engine/rust-toolchain.toml` | même dépôt, fichiers entiers | `b1f646eabd5fa3e9a8168af7e1ee4e53843d8eb3` |
| `mythicsim/go/ui/sim/talents/trees/shaman.json`, `mage.json` | sage3648/mythicsim-forever-engine-go (MIT), fichiers entiers | `a667dce8492bd9fb94269a9f864289cb74006775` |

Ils servent seulement à tester la conversion des talents par identifiant de sort (`forever/sims/talents.py`).
