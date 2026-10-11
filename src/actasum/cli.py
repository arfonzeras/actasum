"""Command-line interface.

    actasum es replay   --mesa MESA.zip [--tota TOTA.zip]
                        [--level constituency|province|municipality|overseas]
    actasum es describe --mesa MESA.zip
    actasum es seats    --mesa MESA.zip            (local elections only)
    actasum es convert  --mesa MESA.zip --out statements.jsonl
    actasum es official --tota TOTA.zip --out official.json
    actasum verify      --statements statements.jsonl --official official.json

    actasum co convert  --mmv MMV.csv --election 2026-05 [--age-text AGE.txt]
                        --out statements.jsonl

    actasum log build       --statements statements.jsonl --out LOGDIR
    actasum log append      --log LOGDIR --statements more.jsonl
    actasum log checkpoint  --log LOGDIR
    actasum log prove       --log LOGDIR --station ID
    actasum log check-proof --proof proof.json [--checkpoint FILE]
    actasum log consistency --log LOGDIR --old-size N
    actasum log check-consistency --proof proof.json [--old FILE] [--new FILE]

    actasum key new --name NAME --out FILE          (a log's signing key)
    actasum log sign --log LOGDIR --key FILE
    actasum witness init --dir WDIR --name NAME
    actasum witness trust --dir WDIR --log-key VKEY
    actasum log witness-request --log LOGDIR --old-size N --out request.txt
    actasum witness add-checkpoint --dir WDIR --request request.txt --out cosig.txt
    actasum log cosign --log LOGDIR --signatures cosig.txt
    actasum log check-checkpoint --checkpoint FILE --log-key VKEY
                                  [--witness-key VKEY ...] [--quorum N]

Exit status: 0 when the check passes, 1 when it does not (differences, gaps,
a signature that does not verify, a witness that refuses), 2 when the input
could not be read.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .log import (
    Checkpoint,
    Log,
    check_checkpoint,
    verify_consistency_proof,
    verify_inclusion_proof,
)
from .note import SignatureError
from .profiles.co import escrutinio as co_escrutinio
from .profiles.es import infoelectoral, seats as es_seats
from .statement import FormatError, OfficialTotals, read_jsonl, write_jsonl
from .verify import VerificationError, aggregate, compare, format_comparison


def _open_out(path: str):
    return sys.stdout if path == "-" else open(path, "w", encoding="utf-8", newline="\n")


def _emit(comparison, args) -> int:
    if args.json:
        json.dump(comparison.to_dict(), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print(format_comparison(comparison, limit=args.limit))
    return 0 if comparison.ok else 1


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
    elif args.level == "province":
        totals = infoelectoral.read_province_totals(official, as_level=True)
    elif args.level == "overseas":
        totals = infoelectoral.read_overseas_residuals(official)
        statements = [s for s in statements if s.unit == "aggregate"]
    else:
        totals = infoelectoral.read_official_totals(official)
    return _emit(compare(statements, totals), args)


def _co_convert(args) -> int:
    """MMV file, and optionally the text of the AGE, to statements."""
    age_text = None
    if args.age_text:
        with open(args.age_text, encoding="utf-8") as handle:
            age_text = handle.read()
    recorded = args.sha256 or (co_escrutinio.recorded_hash(age_text) if age_text else None)
    published = co_escrutinio.load_mmv(args.mmv)
    table = co_escrutinio.load_mmv(args.mmv, recorded) if recorded else published
    statements = co_escrutinio.read_statements(table, args.election)
    summary: dict = {
        "file": published.path,
        "sha256_as_published": published.sha256,
        "lines_before_the_header": published.leading_lines,
        "last_row_cut_short": published.truncated,
        "sha256_recorded_by_the_commission": recorded,
        "hash_check": "no recorded hash to compare with"
        if recorded is None
        else "the published file is the recorded one"
        if published.sha256 == recorded
        else "the published file differs; the original was rebuilt and matches the recorded hash"
        if table.published_sha256
        else "the published file differs and the original could not be rebuilt",
        "stations": len(statements),
    }
    if args.age_text:
        places = {(row["DEP"], row["MUN"]) for row in table.rows}
        if len(places) != 1:
            raise FormatError(
                f"{table.path}: the record of changes can only be applied to a file "
                "with a single municipality"
            )
        (dep, mun), = places
        changes, unparsed = co_escrutinio.read_modifications(age_text)
        chained = co_escrutinio.chain(statements, changes, dep, mun)
        statements = chained.statements
        summary.update(
            {
                "changes_recorded": len(changes),
                "changes_not_parsed": unparsed,
                "stations_changed": chained.stations_changed,
                "changes_not_matching_the_file": len(chained.inconsistent),
                "changes_for_stations_not_in_the_file": len(chained.unknown_station),
            }
        )
    out = _open_out(args.out)
    try:
        summary["statements_written"] = write_jsonl(statements, out)
    finally:
        if out is not sys.stdout:
            out.close()
    json.dump(summary, sys.stderr, indent=2, ensure_ascii=False)
    sys.stderr.write("\n")
    return 0


def _es_describe(args) -> int:
    json.dump(
        infoelectoral.describe(infoelectoral.load_dataset(args.mesa)),
        sys.stdout,
        indent=2,
        ensure_ascii=False,
    )
    sys.stdout.write("\n")
    return 0


def _es_seats(args) -> int:
    """Would the differences change who gets a seat? Local elections only."""
    dataset = infoelectoral.load_dataset(args.mesa)
    official = infoelectoral.read_official_totals(dataset)
    published = infoelectoral.read_municipal_seats(dataset)
    recomputed = aggregate(infoelectoral.read_statements(dataset))
    rows = []
    by_lot = 0
    for area in sorted(set(official.areas) & set(recomputed) & set(published)):
        to_fill, in_file = published[area]
        theirs, mine = official.areas[area], recomputed[area]
        threshold = es_seats.LOCAL_THRESHOLD_PERCENT
        from_totals = es_seats.allocate(theirs.candidatures, theirs.blank, to_fill, threshold)
        from_stations = es_seats.allocate(mine.candidatures, mine.blank, to_fill, threshold)
        if from_totals.by_lot or from_stations.by_lot:
            by_lot += 1
            continue
        if from_totals.seats != in_file or from_stations.seats != in_file:
            rows.append(
                {
                    "area": area,
                    "seats_to_fill": to_fill,
                    "published": dict(sorted(in_file.items())),
                    "from_published_votes": dict(sorted(from_totals.seats.items())),
                    "from_station_votes": dict(sorted(from_stations.seats.items())),
                }
            )
    doc = {
        "election": official.election,
        "municipalities_compared": len(set(official.areas) & set(recomputed) & set(published)),
        "left_out_last_seat_settled_by_lot": by_lot,
        "municipalities_where_an_allocation_differs": rows,
    }
    if args.json:
        json.dump(doc, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print(f"Election: {doc['election']}")
        print(f"Municipalities compared: {doc['municipalities_compared']}")
        print(f"Left out because the last seat is settled by lot: {by_lot}")
        print(
            "Municipalities where the published seats differ from the allocation "
            f"computed from either set of votes: {len(rows)}"
        )

        def show(seats: dict[str, int]) -> str:
            return ", ".join(f"{code}: {count}" for code, count in seats.items()) or "none"

        for row in rows:
            print(f"  {row['area']} ({row['seats_to_fill']} seats)")
            print(f"    seats in the municipal file:        {show(row['published'])}")
            print(f"    computed from its own votes:        {show(row['from_published_votes'])}")
            print(f"    computed from the station votes:    {show(row['from_station_votes'])}")
        print(
            "Result: the two sets of votes lead to the published seats everywhere."
            if not rows
            else "Result: there are allocations to explain. "
            "A difference is not, by itself, evidence of wrongdoing."
        )
    return 0 if not rows else 1


def _verify(args) -> int:
    statements = _read_statements(args.statements)
    with open(args.official, encoding="utf-8") as handle:
        totals = OfficialTotals.from_dict(json.load(handle))
    return _emit(compare(statements, totals), args)


def _read_statements(path: str):
    with open(path, encoding="utf-8") as handle:
        return list(read_jsonl(handle))


def _read_checkpoint(path: str | None) -> Checkpoint | None:
    if path is None:
        return None
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    # A signed checkpoint is accepted too; its signatures are not checked here
    # (use `log check-checkpoint` for that).
    body, separator, _ = text.partition("\n\n")
    return Checkpoint.parse(body + "\n" if separator else text)


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
    origin = args.origin or f"actasum/{statements[0].election}"
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


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def _write_text(text: str, path: str) -> None:
    if path == "-":
        sys.stdout.write(text)
    else:
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)


def _key_new(args) -> int:
    import os

    from .note import LOG_SIGNATURE, Signer

    signer = Signer.generate(args.name, LOG_SIGNATURE)
    descriptor = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(signer.encode() + "\n")
    print(f"private key written to {args.out}; keep it secret", file=sys.stderr)
    print(signer.verifier.vkey())
    return 0


def _log_sign(args) -> int:
    from .note import Signer

    log = Log.open(args.log)
    log.sign(Signer.parse(_read_text(args.key)))
    sys.stdout.write(log.signed_checkpoint())
    return 0


def _log_witness_request(args) -> int:
    _write_text(Log.open(args.log).witness_request(args.old_size), args.out)
    return 0


def _log_cosign(args) -> int:
    log = Log.open(args.log)
    added = log.add_signatures(_read_text(args.signatures))
    print(f"{added} signature line(s) added", file=sys.stderr)
    sys.stdout.write(log.signed_checkpoint())
    return 0


def _log_check_checkpoint(args) -> int:
    from .note import Verifier

    checkpoint, verified = check_checkpoint(
        _read_text(args.checkpoint),
        Verifier.parse(args.log_key),
        [Verifier.parse(key) for key in args.witness_key],
        args.quorum,
    )
    print(f"OK: {checkpoint.origin} at size {checkpoint.size}")
    for item in verified:
        when = f", cosigned at Unix time {item.timestamp}" if item.timestamp is not None else ""
        print(f"  valid signature: {item.verifier.name}{when}")
    return 0


def _witness_init(args) -> int:
    from .witness import Witness

    witness = Witness.create(args.dir, args.name)
    print(f"witness created in {args.dir}; its key file must stay private", file=sys.stderr)
    print(witness.signer.verifier.vkey())
    return 0


def _witness_trust(args) -> int:
    from .note import Verifier
    from .witness import Witness

    key = Verifier.parse(args.log_key)
    Witness(args.dir).trust(key)
    print(f"now following the log {key.name}", file=sys.stderr)
    return 0


def _witness_add_checkpoint(args) -> int:
    from .witness import Witness

    status, body = Witness(args.dir).add_checkpoint(_read_text(args.request))
    if status == 200:
        _write_text(body, args.out)
        return 0
    meaning = {
        400: "bad request",
        403: "the log's signature is missing or invalid",
        404: "this witness does not follow that log",
        409: "the witness last cosigned a different size; retry from that size",
        422: "the log is not consistent with what this witness cosigned before",
    }[status]
    print(f"actasum: witness refused ({status}, {meaning}): {body.strip()}", file=sys.stderr)
    return 1


def _witness_status(args) -> int:
    from .witness import Witness

    witness = Witness(args.dir)
    print(f"witness key: {witness.signer.verifier.vkey()}")
    for origin, entry in sorted(witness.status()["logs"].items()):
        print(f"{origin}: last cosigned size {entry['size']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="actasum",
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
    build.add_argument("--origin", help="name of the log (default: actasum/<election>)")
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

    sign = log_commands.add_parser("sign", help="sign the current checkpoint")
    sign.add_argument("--log", required=True)
    sign.add_argument("--key", required=True, help="the log's private key file")
    sign.set_defaults(run=_log_sign)

    request = log_commands.add_parser(
        "witness-request", help="request asking a witness to cosign the checkpoint"
    )
    request.add_argument("--log", required=True)
    request.add_argument(
        "--old-size", type=int, required=True,
        help="size of the last checkpoint that witness cosigned (0 the first time)",
    )
    request.add_argument("--out", default="-")
    request.set_defaults(run=_log_witness_request)

    cosign = log_commands.add_parser("cosign", help="attach a witness's cosignature")
    cosign.add_argument("--log", required=True)
    cosign.add_argument("--signatures", required=True, help="the witness's answer")
    cosign.set_defaults(run=_log_cosign)

    check_cp = log_commands.add_parser(
        "check-checkpoint", help="check a signed checkpoint against a trust policy"
    )
    check_cp.add_argument("--checkpoint", required=True)
    check_cp.add_argument("--log-key", required=True, help="the log's verifier key")
    check_cp.add_argument("--witness-key", action="append", default=[], help="repeatable")
    check_cp.add_argument("--quorum", type=int, default=0, help="witnesses required")
    check_cp.set_defaults(run=_log_check_checkpoint)

    key = commands.add_parser("key", help="signing keys")
    key_commands = key.add_subparsers(dest="key_command", required=True)
    key_new = key_commands.add_parser("new", help="create a log signing key")
    key_new.add_argument("--name", required=True, help="the log's origin")
    key_new.add_argument("--out", required=True, help="file for the private key")
    key_new.set_defaults(run=_key_new)

    witness = commands.add_parser("witness", help="cosign checkpoints of logs that only grow")
    witness_commands = witness.add_subparsers(dest="witness_command", required=True)
    w_init = witness_commands.add_parser("init", help="create a witness and its key")
    w_init.add_argument("--dir", required=True)
    w_init.add_argument("--name", required=True, help="e.g. witness.example/w1")
    w_init.set_defaults(run=_witness_init)
    w_trust = witness_commands.add_parser("trust", help="start following a log")
    w_trust.add_argument("--dir", required=True)
    w_trust.add_argument("--log-key", required=True, help="the log's verifier key")
    w_trust.set_defaults(run=_witness_trust)
    w_add = witness_commands.add_parser("add-checkpoint", help="check a request and cosign")
    w_add.add_argument("--dir", required=True)
    w_add.add_argument("--request", required=True)
    w_add.add_argument("--out", default="-")
    w_add.set_defaults(run=_witness_add_checkpoint)
    w_status = witness_commands.add_parser("status", help="what this witness has cosigned")
    w_status.add_argument("--dir", required=True)
    w_status.set_defaults(run=_witness_status)

    co = commands.add_parser("co", help="Colombia profile: Registraduría scrutiny files")
    co_commands = co.add_subparsers(dest="co_command", required=True)
    co_convert = co_commands.add_parser(
        "convert", help="per-station MMV file (and the changes in an AGE) -> statements"
    )
    co_convert.add_argument("--mmv", required=True, help="the MMV .csv file as downloaded")
    co_convert.add_argument("--election", required=True, help="election date as YYYY-MM")
    co_convert.add_argument(
        "--age-text",
        help="text of the Acta General de Escrutinio of the same commission, "
        "as produced by `pdftotext -layout`",
    )
    co_convert.add_argument(
        "--sha256",
        help="hash of the MMV file as recorded by the commission "
        "(default: the one found in --age-text)",
    )
    co_convert.add_argument("--out", default="-", help="output file (default: stdout)")
    co_convert.set_defaults(run=_co_convert)

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
        choices=["constituency", "province", "municipality", "overseas"],
        default="constituency",
        help="compare per constituency (default: the province for the Congreso, the "
        "municipality for local elections, the country for the European Parliament); per "
        "province or per municipality, to locate a difference; or the overseas row of each "
        "province against what the official totals leave for it",
    )
    replay.add_argument("--json", action="store_true", help="print the report as JSON")
    replay.add_argument("--limit", type=int, default=20, help="lines to list per section")
    replay.set_defaults(run=_es_replay)

    describe = es_commands.add_parser(
        "describe", help="list what a ZIP contains, without comparing anything"
    )
    describe.add_argument("--mesa", required=True, help="a ZIP file or a directory")
    describe.set_defaults(run=_es_describe)

    seats = es_commands.add_parser(
        "seats",
        help="local elections: do the station votes and the municipal totals "
        "lead to the published seats?",
    )
    seats.add_argument("--mesa", required=True, help="the _MESA ZIP file or a directory")
    seats.add_argument("--json", action="store_true", help="print the result as JSON")
    seats.set_defaults(run=_es_seats)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.run(args)
    except SignatureError as exc:
        # The input was readable but is not validly signed, or not by enough
        # trusted parties: a negative result, not a usage problem.
        print(f"actasum: not verified: {exc}", file=sys.stderr)
        return 1
    except (FormatError, VerificationError, OSError, json.JSONDecodeError) as exc:
        print(f"actasum: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
