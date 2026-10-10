"""Command-line interface.

    tallylog es replay   --mesa MESA.zip [--tota TOTA.zip]
    tallylog es convert  --mesa MESA.zip --out statements.jsonl
    tallylog es official --tota TOTA.zip --out official.json
    tallylog verify      --statements statements.jsonl --official official.json

Exit status: 0 when the recomputed totals match, 1 when there are differences
or gaps, 2 when the input could not be read.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .profiles.es import infoelectoral
from .statement import FormatError, OfficialTotals, read_jsonl, write_jsonl
from .verify import VerificationError, format_report, verify


def _open_out(path: str):
    return sys.stdout if path == "-" else open(path, "w", encoding="utf-8", newline="\n")


def _emit(report, as_json: bool) -> int:
    if as_json:
        json.dump(report.to_dict(), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print(format_report(report))
    return 0 if report.ok else 1


def _es_convert(args) -> int:
    statements = infoelectoral.read_statements(infoelectoral.load_dataset(args.mesa))
    out = _open_out(args.out)
    try:
        count = write_jsonl(statements, out)
    finally:
        if out is not sys.stdout:
            out.close()
    print(f"{count} statements written", file=sys.stderr)
    return 0


def _es_official(args) -> int:
    totals = infoelectoral.read_official_totals(infoelectoral.load_dataset(args.tota))
    out = _open_out(args.out)
    try:
        json.dump(totals.to_dict(), out, indent=2, ensure_ascii=False, sort_keys=True)
        out.write("\n")
    finally:
        if out is not sys.stdout:
            out.close()
    return 0


def _es_replay(args) -> int:
    statements = infoelectoral.read_statements(infoelectoral.load_dataset(args.mesa))
    totals = infoelectoral.read_official_totals(
        infoelectoral.load_dataset(args.tota or args.mesa)
    )
    return _emit(verify(statements, totals), args.json)


def _verify(args) -> int:
    with open(args.statements, encoding="utf-8") as handle:
        statements = list(read_jsonl(handle))
    with open(args.official, encoding="utf-8") as handle:
        totals = OfficialTotals.from_dict(json.load(handle))
    return _emit(verify(statements, totals), args.json)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tallylog",
        description="Recompute election totals from polling-station tally sheets.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("verify", help="compare statements with official totals")
    check.add_argument("--statements", required=True, help="JSON Lines file of statements")
    check.add_argument("--official", required=True, help="official totals (JSON)")
    check.add_argument("--json", action="store_true", help="print the report as JSON")
    check.set_defaults(run=_verify)

    es = commands.add_parser("es", help="Spain profile: Ministry of the Interior files")
    es_commands = es.add_subparsers(dest="es_command", required=True)

    convert = es_commands.add_parser("convert", help="per-station ZIP -> statements")
    convert.add_argument("--mesa", required=True, help="the _MESA ZIP file or a directory")
    convert.add_argument("--out", default="-", help="output file (default: stdout)")
    convert.set_defaults(run=_es_convert)

    official = es_commands.add_parser("official", help="totals ZIP -> official totals")
    official.add_argument("--tota", required=True, help="the _TOTA ZIP file or a directory")
    official.add_argument("--out", default="-", help="output file (default: stdout)")
    official.set_defaults(run=_es_official)

    replay = es_commands.add_parser("replay", help="convert, aggregate and compare in one step")
    replay.add_argument("--mesa", required=True, help="the _MESA ZIP file or a directory")
    replay.add_argument(
        "--tota",
        help="the _TOTA ZIP file or a directory (default: read the totals from --mesa, "
        "which also carries them)",
    )
    replay.add_argument("--json", action="store_true", help="print the report as JSON")
    replay.set_defaults(run=_es_replay)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.run(args)
    except (FormatError, VerificationError, OSError, json.JSONDecodeError) as exc:
        print(f"tallylog: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
