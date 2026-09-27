# Addon (fixtures)

- `ForeverLoggerDB.lua` : SavedVariable d'exemple au format écrit par le client (`WTF/Account/<COMPTE>/SavedVariables/ForeverLogger.lua`), rédigée pour les tests : GUID du joueur « à moi » de la fixture de journal anonymisée, **niveau d'exemple** 14 à 14:50:00 puis 15 à 15:33:20 (heure locale, comme le journal). Valeurs inventées : ce n'est pas une mesure.
- `bad/` : un défaut par fichier pour `tests/unit/test_addon_rules.py` (alias de fichier, `RegisterEvent` nu, fonction d'action, abonnement au journal de combat, initialisation hors d'`ADDON_LOADED`, `.toc` à lignes fusionnées — copie du `.toc` corrompu trouvé le 2026-09-27 —, interface différente de 16001).
