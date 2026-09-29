# T06 — demande de décision avant la fusion

## Critère « je ne sais pas » hors périmètre (3 sur 3) : juge LLM variable
- Constat : passages 1 et 2 à 3/3 ; passage 3 à 1/3 ; rejeu à trois exécutions : 8/9. Le correcteur `regex`
  (« je ne sais pas ») réussit à chaque exécution (15/15). Les réponses refusées par le juge sont conformes au format :
  « Je ne sais pas », tranche citée (DJ1, EC1), aucune valeur, propositions limitées à ce que le projet couvre ou à une
  recherche web étiquetée (texte dans `docs/research/plugin-eval-T06.md`).
- Cause probable : le critère du juge dit « aucun conseil » ; le juge lit l'offre « je peux vous donner le niveau
  conseillé des Mortemines » comme un conseil.
- Options :
  1. **(proposée)** Préciser le critère `llm` des trois cas `hors-*` (`graders/sans-estimation.md`), sans changer la question ni les autres
     correcteurs :
     « La réponse dit clairement que le projet ne sait pas ou ne couvre pas encore ce sujet, cite la tranche de la
     feuille de route qui le couvrira (identifiant comme T12, EC1 ou DJ1) et ne donne aucune valeur chiffrée ni aucune
     information de jeu sur ce sujet (build, prix, butin) tirée de WoW Classic, de retail ou de la mémoire du modèle.
     Proposer ce que le projet couvre déjà (niveau d'un donjon, build du Mage) ou une recherche web présentée comme
     l'avis d'une source est permis. »
     puis rejouer les trois cas à trois exécutions.
  2. Garder le critère et accepter le résultat comme variance du juge (15/18 sur l'ensemble des passages).
  3. Garder le critère et ajuster les skills pour que la réponse hors périmètre ne propose rien d'autre.
