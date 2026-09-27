"""Évaluation des variables d'une infobulle du client (`Spell.Description_lang`), en fonction pure.

La valeur de chaque variable vient d'un résolveur fourni par l'appelant (le décodeur, qui connaît les tables) :
`resolve(sort, lettre, effet)` renvoie les valeurs signées de la variable (deux pour `$s` d'un effet à variance :
minimum et maximum). Ce module ne fait que lire le gabarit, appliquer les opérations écrites et l'affichage :
- `$s1`, `$m1`, `$M1`, `$d`, `$u`, `$n`, `$o2`, `$t1`, avec un sort cité en préfixe (`$400573s1`) : valeur absolue ;
- `$/1000;S1` : valeur absolue divisée ;
- `${expression}` et `${expression}.N` : valeurs signées, opérations + - * / et parenthèses, arrondi au demi
  supérieur à N décimales (0 par défaut) ;
- `$lsingulier:pluriel;` : texte, ignoré.
Tout autre motif (`$<variable>`, `$?s123[…][…]`, lettre inconnue) lève ValueError : le décodeur le signale, il ne
devine jamais."""

from __future__ import annotations

import ast
import math
import re
from collections.abc import Callable, Sequence

Resolver = Callable[[int | None, str, int], Sequence[float]]
"""(sort cité, None pour le sort de l'infobulle ; lettre en minuscule sauf M ; indice d'effet à partir de 0)
-> valeurs signées."""

LETTERS = frozenset("smMdunot")

_VAR = re.compile(r"(\d*)([A-Za-z])(\d?)")
_DIVIDE = re.compile(r"/(\d+);")
_INNER = re.compile(r"\$(\d*)([A-Za-z])(\d?)")
_DECIMALS = re.compile(r"\.(\d)")


def half_up(x: float, decimals: int = 0) -> float:
    """Arrondi au demi supérieur (0,5 -> 1), à `decimals` décimales."""
    scale = 10**decimals
    return math.floor(round(x * scale, 9) + 0.5) / scale


def normalize(x: float) -> int | float:
    """Entier si la valeur est entière (à 1e-9 près), sinon flottant arrondi à 9 décimales."""
    rounded = round(float(x), 9)
    return int(rounded) if rounded.is_integer() else rounded


def _letter(raw: str) -> str:
    letter = raw if raw == "M" else raw.lower()
    if letter not in LETTERS:
        raise ValueError(f"variable d'infobulle non prise en charge : ${raw}")
    return letter


def _values(resolve: Resolver, spell: str, raw_letter: str, index: str) -> Sequence[float]:
    return resolve(int(spell) if spell else None, _letter(raw_letter), int(index or 1) - 1)


def _evaluate(expression: str) -> float:
    """Expression arithmétique (+ - * /, parenthèses, nombres) ; ValueError pour tout le reste."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"expression d'infobulle illisible : {expression}") from exc

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
            value = walk(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add | ast.Sub | ast.Mult | ast.Div):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            return left / right
        raise ValueError(f"expression d'infobulle non prise en charge : {expression}")

    return walk(tree)


def _expression(body: str, resolve: Resolver) -> float:
    def substitute(m: re.Match[str]) -> str:
        return repr(float(_values(resolve, m[1], m[2], m[3])[0]))

    if "$<" in body or "$?" in body:
        raise ValueError(f"expression d'infobulle non prise en charge : {body}")
    expression = _INNER.sub(substitute, body)
    if "$" in expression:
        raise ValueError(f"expression d'infobulle non prise en charge : {body}")
    return _evaluate(expression)


def tooltip_values(template: str, resolve: Resolver) -> list[int | float]:
    """Valeurs affichées par l'infobulle, dans l'ordre d'apparition des variables."""
    out: list[int | float] = []
    i = 0
    while (start := template.find("$", i)) != -1:
        rest = template[start + 1 :]
        if rest.startswith("{"):
            end = rest.find("}")
            if end == -1:
                raise ValueError(f"expression d'infobulle non fermée : {template[start:]}")
            value = _expression(rest[1:end], resolve)
            i = start + 2 + end
            decimals = _DECIMALS.match(template, i)
            places = 0
            if decimals:
                places = int(decimals[1])
                i = decimals.end()
            out.append(normalize(half_up(value, places)))
            continue
        if rest[:1] in ("l", "L") and ":" in rest and ";" in rest:
            i = start + 1 + rest.index(";") + 1  # texte singulier / pluriel
            continue
        divisor = 1
        if divide := _DIVIDE.match(rest):
            divisor = int(divide[1])
            rest = rest[divide.end() :]
            start += divide.end()
        var = _VAR.match(rest)
        if not var:
            raise ValueError(f"motif d'infobulle non pris en charge : {template[start : start + 12]}")
        out += [normalize(abs(v) / divisor) for v in _values(resolve, var[1], var[2], var[3])]
        i = start + 1 + var.end()
    return out
