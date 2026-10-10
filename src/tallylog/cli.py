"""Command-line interface.

    tallylog es replay   --mesa MESA.zip [--tota TOTA.zip] [--level municipality|overseas]
    tallylog es convert  --mesa MESA.zip --out statements.jsonl
    tallylog es official --tota TOTA.zip --out official.json
    tallylog verify      --statements statements.jsonl --official official.json

    tallylog log build       --statements statements.jsonl --out LOGDIR
    tallylog log append      --log LOGDIR --statements more.jsonl
    tallylog log checkpoint  --log LOGDIR
    tallylog log prove       --log LOGDIR --station ID
    tallylog log check-proof --proof proof.json [--checkpoint FILE]
    tallylog log consistency --log LOGDIR --old-size N
    tallylog log check-consistency --proof proof.json [--old FILE] [--new FILE]

Exit status: 0 when the recomputed totals match, 1 when there are differences
or gaps, 2 when the input could not be read.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .log import Checkpoint, Log, verify_consistency_proof, verify_inclusion_proof
from .profiles.es import infoelectoral
from .statement import FormatError, OfficialTotals, read_jsonl, write_jsonl
from .verify import VerificationError, format_report, verify


def _open_out(path: str):
    return sys.stdout if path == "-" else open(path, "w", encoding="utf-8", newline="\n")


def _emit(report, args) -> int:
    if args.json:
        json.dump(report.to_dict(), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print(format_report(report, limit=args.limit))
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
    official = infoelectoral.load_dataset(args.tota or args.mesa)
    if args.level == "municipality":
        totals = infoelectoral.read_municipal_totals(official)
    elif args.level == "overseas":
        totals = infoelectoral.read_overseas_residuals(official)
        statements = [s for s in statements if s.unit == "aggregate"]
    else:
        totals = infoelectoral.read_official_totals(official)
    return _emit(verify(statements, totals), args)


def _verify(args) -> int:
    statements = _read_statements(args.statements)
    with open(args.official, encoding="utf-8") as handle:
        totals = OfficialTotals.from_dict(json.load(handle))
    return _emit(verify(statements, totals), args)


def _read_statements(path: str):
    with open(path, encoding="utf-8") as handle:
        return list(read_jsonl(handle))


def _read_checkpoint(path: str | None) -> Checkpoint | None:
    if path is None:
        return None
    with open(path, encoding="utf-8", newline="") as handle:
        return Checkpoint.parse(handle.read())


def _write_json(doc, path: str) -> None:
    out = _open_out(path)
    try:
        json.dump(doc, out, indent=2, ensure_ascii=False)
        out.write("\n")
    finally:
        if out is not sys.stdout:
            out.close()


def _log_build(args) -> int:
    statements = _read_statements(args.statements)
    if not statements:
        raise FormatError("no statements to load")
    origin = args.origin or f"tallylog/{statements[0].election}"
    log = Log.create(args.out, origin)
    added, skipped = log.append(statements)
    print(f"{added} entries added, {skipped} duplicates skipped", file=sys.stderr)
    sys.stdout.write(log.checkpoint().text())
    return 0


def _log_append(args) -> int:
    log = Log.open(args.log)
    before = log.checkpoint().size
    added, skipped = log.append(_read_statements(args.statements))
    print(
        f"{added} entries added, {skipped} duplicates skipped (size {before} -> {before + added})",
        file=sys.stderr,
    )
    sys.stdout.write(log.checkpoint().text())
    return 0


def _log_checkpoint(args) -> int:
    sys.stdout.write(Log.open(args.log).checkpoint().text())
    return 0


def _log_prove(args) -> int:
    log = Log.open(args.log)
    indexes = log.find(args.station)
    if not indexes:
        raise FormatError(f"no entry for polling station {args.station}")
    proofs = [log.prove_inclusion(index) for index in indexes]
    _write_json(proofs[0] if len(proofs) == 1 else proofs, args.out)
    return 0


def _log_check_proof(args) -> int:
    with open(args.proof, encoding="utf-8") as handle:
        doc = json.load(handle)
    trusted = _read_checkpoint(args.checkpoint)
    for proof in doc if isinstance(doc, list) else [doc]:
        statement, checkpoint = verify_inclusion_proof(proof, trusted)
        print(
            f"OK: {statement.station} ({statement.statement_id()}) is entry "
            f"{proof['leaf_index']} of the log {checkpoint.origin} at size {checkpoint.size}"
        )
    if trusted is None:
        print(
            "Note: checked against the checkpoint inside the proof. Pass --checkpoint with a "
            "checkpoint obtained independently to rule out a made-up log.",
            file=sys.stderr,
        )
    return 0


def _log_consistency(args) -> int:
    _write_json(Log.open(args.log).prove_consistency(args.old_size), args.out)
    return 0


def _log_check_consistency(args) -> int:
    with open(args.proof, encoding="utf-8") as handle:
        doc = json.load(handle)
    old, new = verify_consistency_proof(
        doc, _read_checkpoint(args.old), _read_checkpoint(args.new)
    )
    print(
        f"OK: the log {new.origin} at size {new.size} contains, unchanged and in the same "
        f"order, the {old.size} entries it had before"
    )
    return 0


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
    check.add_argument("--limit", type=int, default=20, help="lines to list per section")
    check.set_defaults(run=_verify)

    log = commands.add_parser("log", help="append-only log of statements with proofs")
    log_commands = log.add_subparsers(dest="log_command", required=True)

    build = log_commands.add_parser("build", help="create a log from a statements file")
    build.add_argument("--statements", required=True)
    build.add_argument("--out", required=True, help="directory for the new log")
    build.add_argument("--origin", help="name of the log (default: tallylog/<election>)")
    build.set_defaults(run=_log_build)

    append = log_commands.add_parser("append", help="append statements to a log")
    append.add_argument("--log", required=True)
    append.add_argument("--statements", required=True)
    append.set_defaults(run=_log_append)

    show = log_commands.add_parser("checkpoint", help="check a log and print its checkpoint")
    show.add_argument("--log", required=True)
    show.set_defaults(run=_log_checkpoint)

    prove = log_commands.add_parser("prove", help="inclusion proof for a polling station")
    prove.add_argument("--log", required=True)
    prove.add_argument("--station", required=True)
    prove.add_argument("--out", default="-")
    prove.set_defaults(run=_log_prove)

    check_proof = log_commands.add_parser("check-proof", help="check an inclusion proof")
    check_proof.add_argument("--proof", required=True)
    check_proof.add_argument("--checkpoint", help="a checkpoint obtained independently")
    check_proof.set_defaults(run=_log_check_proof)

    consistency = log_commands.add_parser("consistency", help="proof that the log only grew")
    consistency.add_argument("--log", required=True)
    consistency.add_argument("--old-size", type=int, required=True)
    consistency.add_argument("--out", default="-")
    consistency.set_defaults(run=_log_consistency)

    check_consistency = log_commands.add_parser(
        "check-consistency", help="check a consistency proof"
    )
    check_consistency.add_argument("--proof", required=True)
    check_consistency.add_argument("--old", help="the earlier checkpoint, kept by the checker")
    check_consistency.add_argument("--new", help="the later checkpoint")
    check_consistency.set_defaults(run=_log_check_consistency)

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
    replay.add_argument(
        "--level",
        choices=["constituency", "municipality", "overseas"],
        default="constituency",
        help="compare per constituency (default); per municipality, to locate a difference; "
        "or the overseas row of each constituency against what the official totals leave for it",
    )
    replay.add_argument("--json", action="store_true", help="print the report as JSON")
    replay.add_argument("--limit", type=int, default=20, help="lines to list per section")
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
