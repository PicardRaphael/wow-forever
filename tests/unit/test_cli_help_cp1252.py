"""L'aide de chaque commande s'affiche dans une console Windows en cp1252 (`forever pets --help` plantait sur « ↔ »,
UnicodeEncodeError, relevé du 2026-10-22)."""

import argparse

from forever.cli import build_parser


def parsers(parser):
    yield parser
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for sub in action.choices.values():
                yield from parsers(sub)


def test_every_help_text_is_printable_in_cp1252():
    bad = []
    for parser in parsers(build_parser()):
        try:
            parser.format_help().encode("cp1252")
        except UnicodeEncodeError as exc:
            bad.append(f"{parser.prog} : {exc.object[exc.start : exc.end]!r}")
    assert bad == []
