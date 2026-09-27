"""Erreurs métier : un code stable, un message en français et l'action à mener."""

from __future__ import annotations

from typing import NotRequired, TypedDict

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_INTEGRITY = 3
EXIT_NOT_FOUND = 4


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


class DataIntegrityError(ForeverError):
    exit_code = EXIT_INTEGRITY

    def __init__(self, message: str) -> None:
        super().__init__(
            "data_integrity",
            message,
            "vérifier la modification des données ; lancer `uv run forever manifest --update` si elle est voulue",
        )


class ManifestMissingError(ForeverError):
    exit_code = EXIT_INTEGRITY

    def __init__(self, message: str) -> None:
        super().__init__("manifest_missing", message, "lancer `uv run forever manifest --update`")


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
