"""Erreurs métier : un code stable, un message en français et l'action à mener."""

from __future__ import annotations

from typing import NotRequired, TypedDict

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_INTEGRITY = 3
EXIT_NOT_FOUND = 4
EXIT_NETWORK = 5


class ErrorInfo(TypedDict):
    code: str
    message: str
    action: str
    suggestions: NotRequired[list[str]]


class ForeverError(Exception):
    """Erreur présentable à l'utilisateur (CLI) ou au modèle (MCP)."""

    exit_code = EXIT_USAGE

    def __init__(self, code: str, message: str, action: str, *, suggestions: list[str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.action = action
        self.suggestions = suggestions or []

    def to_info(self) -> ErrorInfo:
        info: ErrorInfo = {"code": self.code, "message": self.message, "action": self.action}
        if self.suggestions:
            info["suggestions"] = list(self.suggestions)
        return info


class InvalidArgumentError(ForeverError):
    exit_code = EXIT_USAGE

    def __init__(self, message: str, action: str) -> None:
        super().__init__("invalid_argument", message, action)


class UsageError(ForeverError):
    """Ligne de commande refusée par argparse ; `usage` garde la ligne d'usage de la (sous-)commande."""

    exit_code = EXIT_USAGE

    def __init__(self, prog: str, message: str, usage: str = "") -> None:
        super().__init__("usage", f"Usage incorrect de `{prog}` : {message}.", f"voir `{prog} --help`")
        self.usage = usage


class DataIntegrityError(ForeverError):
    exit_code = EXIT_INTEGRITY

    def __init__(self, message: str, action: str | None = None) -> None:
        super().__init__(
            "data_integrity",
            message,
            action
            or "vérifier la modification des données ; lancer `uv run forever manifest --update` si elle est voulue",
        )


class ManifestMissingError(ForeverError):
    exit_code = EXIT_INTEGRITY

    def __init__(self, message: str) -> None:
        super().__init__("manifest_missing", message, "lancer `uv run forever manifest --update`")


class DataSchemaError(ForeverError):
    """Fichier de données ou registre dont la structure ne correspond pas au schéma attendu."""

    exit_code = EXIT_INTEGRITY

    def __init__(self, message: str, action: str | None = None) -> None:
        super().__init__(
            "data_schema",
            message,
            action or "corriger le fichier signalé, puis lancer `uv run forever manifest --update` s'il est versionné",
        )


class UnknownMechanicError(ForeverError):
    exit_code = EXIT_NOT_FOUND

    def __init__(self, mechanic_id: str, suggestions: list[str]) -> None:
        hint = (
            "reprendre un identifiant suggéré"
            if suggestions
            else "consulter docs/MECHANICS_REGISTRY.yaml (identifiants de la forme A5)"
        )
        super().__init__("unknown_mechanic", f"Mécanique inconnue : « {mechanic_id} ».", hint, suggestions=suggestions)


class UnknownSpellError(ForeverError):
    exit_code = EXIT_NOT_FOUND

    def __init__(self, name: str, suggestions: list[str]) -> None:
        hint = "reprendre un nom suggéré" if suggestions else "vérifier l'orthographe (nom anglais du sort)"
        super().__init__("unknown_spell", f"Sort inconnu : « {name} ».", hint, suggestions=suggestions)


class UnknownRankError(ForeverError):
    exit_code = EXIT_NOT_FOUND

    def __init__(self, spell: str, rank: int, ranks_total: int) -> None:
        super().__init__(
            "unknown_rank",
            f"Rang {rank} inconnu pour {spell} : rangs disponibles 1-{ranks_total}.",
            f"choisir un rang entre 1 et {ranks_total}, ou omettre --rank pour tous les rangs",
        )


class UnsupportedKindError(ForeverError):
    exit_code = EXIT_NOT_FOUND

    def __init__(self, what: str, available: list[str]) -> None:
        super().__init__(
            "unsupported_kind",
            f"Consultation non prise en charge : {what}.",
            "consulter un sort de dégâts parmi les suggestions",
            suggestions=available,
        )


class OfflineError(ForeverError):
    exit_code = EXIT_NETWORK

    def __init__(self, what: str = "cette commande") -> None:
        super().__init__(
            "offline",
            f"Mode hors ligne : {what} a besoin du réseau.",
            "retirer --offline ou FOREVER_OFFLINE, ou travailler sur le cache local",
        )


class FetchFailedError(ForeverError):
    exit_code = EXIT_NETWORK

    def __init__(self, message: str) -> None:
        super().__init__("fetch_failed", message, "réessayer plus tard ou vérifier la table sur https://wago.tools/db2")


class UnknownVersionError(ForeverError):
    exit_code = EXIT_NOT_FOUND

    def __init__(self, version: str, available: list[str]) -> None:
        super().__init__(
            "unknown_version",
            f"Version de données inconnue : « {version} ».",
            "donner une version du dépôt ou le chemin d'une version candidate",
            suggestions=available,
        )


class CsvMissingError(ForeverError):
    exit_code = EXIT_NOT_FOUND

    def __init__(self, version: str, missing: list[str]) -> None:
        super().__init__(
            "csv_missing",
            f"Tables du client absentes pour {version} : {', '.join(missing)}.",
            f"lancer `uv run forever fetch --version {version}` (ou donner --csv-dir)",
        )


class CandidateExistsError(ForeverError):
    exit_code = EXIT_USAGE

    def __init__(self, path: str) -> None:
        super().__init__(
            "candidate_exists",
            f"Une version candidate existe déjà : {path}.",
            "ajouter --force pour la remplacer, ou choisir un autre dossier avec --out",
        )


class UnsupportedLogError(ForeverError):
    """Journal de combat vide, d'une autre version de format ou sans le bloc avancé."""

    exit_code = EXIT_INTEGRITY

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(
            "unsupported_log",
            f"Journal de combat non pris en charge : {path} ({reason}).",
            "activer le journal avancé (ForeverLogger) et fournir un journal au format 22 (COMBAT_LOG_VERSION 22, "
            "ADVANCED_LOG_ENABLED 1)",
        )


class PathNotFoundError(ForeverError):
    exit_code = EXIT_NOT_FOUND

    def __init__(self, what: str, path: str, action: str) -> None:
        super().__init__("path_not_found", f"{what} introuvable : {path}.", action)
