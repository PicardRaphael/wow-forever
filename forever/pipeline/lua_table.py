"""Analyseur de tables Lua littérales (sous-ensemble produit par les addons : bases de Questie, SavedVariables).

Aucun Lua n'est exécuté. Pris en charge : chaînes `'…'` et `"…"` (échappements `\\n`, `\\t`, `\\ddd`…), chaînes
longues `[[…]]`, nombres (décimaux, exposants, hexadécimaux), `nil`, `true`, `false`, tables imbriquées avec clés
`[expr]=`, `nom=` ou positionnelles, séparateurs `,` et `;`, commentaires `--` et `--[[…]]`.
Une table seulement positionnelle devient une liste (les `nil` y restent) ; sinon un dict (positions 1, 2… en clés
entières). Toute erreur lève ValueError avec la ligne et la colonne."""

from __future__ import annotations

import re

_SPACE = re.compile(r"(?:\s+|--\[(=*)\[.*?\]\1\]|--[^\n]*)*", re.DOTALL)
_NUMBER = re.compile(r"-?(?:0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LONG = re.compile(r"\[(=*)\[(.*?)\]\1\]", re.DOTALL)
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v", "\\": "\\", '"': '"'}
_ESCAPES |= {"'": "'", "\n": "\n"}
_KEYWORDS: dict[str, object] = {"nil": None, "true": True, "false": False}


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def fail(self, message: str, pos: int | None = None) -> ValueError:
        at = self.pos if pos is None else pos
        line = self.text.count("\n", 0, at) + 1
        col = at - (self.text.rfind("\n", 0, at) + 1) + 1
        return ValueError(f"table Lua illisible, ligne {line}, colonne {col} : {message}")

    def skip(self) -> None:
        match = _SPACE.match(self.text, self.pos)
        if match:
            self.pos = match.end()

    def peek(self) -> str:
        self.skip()
        return self.text[self.pos : self.pos + 1]

    def value(self) -> object:
        c = self.peek()
        if c == "{":
            return self.table()
        if c in ("'", '"'):
            return self.string(c)
        if c == "[":
            match = _LONG.match(self.text, self.pos)
            if not match:
                raise self.fail("chaîne longue non terminée")
            self.pos = match.end()
            text = match[2]
            return text.removeprefix("\n")
        match = _NUMBER.match(self.text, self.pos)
        if match:
            self.pos = match.end()
            token = match[0]
            if "x" in token.lower():
                return int(token, 16)
            return float(token) if any(ch in token for ch in ".eE") else int(token)
        match = _NAME.match(self.text, self.pos)
        if match and match[0] in _KEYWORDS:
            self.pos = match.end()
            return _KEYWORDS[match[0]]
        raise self.fail(f"valeur attendue, « {c or 'fin du texte'} » lu")

    def string(self, quote: str) -> str:
        start = self.pos
        self.pos += 1
        out: list[str] = []
        text = self.text
        while True:
            end = self.pos
            while end < len(text) and text[end] not in (quote, "\\", "\n"):
                end += 1
            out.append(text[self.pos : end])
            if end >= len(text) or text[end] == "\n":
                raise self.fail("chaîne non terminée", start)
            if text[end] == quote:
                self.pos = end + 1
                return "".join(out)
            nxt = text[end + 1 : end + 2]
            if nxt.isdigit():
                digits = re.match(r"\d{1,3}", text[end + 1 :])
                assert digits is not None
                out.append(chr(int(digits[0])))
                self.pos = end + 1 + len(digits[0])
            elif nxt in _ESCAPES:
                out.append(_ESCAPES[nxt])
                self.pos = end + 2
            else:
                raise self.fail(f"échappement inconnu « \\{nxt} »", end)

    def table(self) -> object:
        self.pos += 1  # {
        positional: list[object] = []
        keyed: dict[object, object] = {}
        while True:
            c = self.peek()
            if c == "}":
                self.pos += 1
                break
            if c == "[" and not _LONG.match(self.text, self.pos):
                self.pos += 1
                key = self.value()
                self.expect("]")
                self.expect("=")
                keyed[key] = self.value()
            else:
                name = _NAME.match(self.text, self.pos)
                after = name and _SPACE.match(self.text, name.end())
                if name and name[0] not in _KEYWORDS and after and self.text[after.end() : after.end() + 1] == "=":
                    self.pos = after.end() + 1
                    keyed[name[0]] = self.value()
                else:
                    positional.append(self.value())
            c = self.peek()
            if c in (",", ";"):
                self.pos += 1
            elif c != "}":
                raise self.fail(f"« , » ou « }} » attendu, « {c or 'fin du texte'} » lu")
        if not keyed:
            return positional
        out: dict[object, object] = {i: v for i, v in enumerate(positional, start=1)}
        out.update(keyed)
        return out

    def expect(self, token: str) -> None:
        if self.peek() != token:
            raise self.fail(f"« {token} » attendu")
        self.pos += 1


def parse_lua_value(text: str) -> object:
    """Valeur Lua littérale unique (espaces et commentaires autour admis)."""
    parser = _Parser(text)
    value = parser.value()
    parser.skip()
    if parser.pos != len(text):
        raise parser.fail("texte en trop après la valeur")
    return value
