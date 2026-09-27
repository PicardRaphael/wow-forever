---
name: revue
description: Revue de la tranche en cours par les sous-agents relecteur et auditeur-mecaniques, avec recommandation fusionner ou corriger.
disable-model-invocation: true
---
1. Lancer le sous-agent `relecteur` sur le diff de la tranche (`git diff main...HEAD`).
2. Lancer le sous-agent `auditeur-mecaniques` sur le registre et les tests.
3. Rapporter : bloquant, mineur, écarts au registre, recommandation (fusionner ou corriger). Ne pas corriger soi-même sans accord.
