"""Command-line interface.

    actasum es replay   --mesa MESA.zip [--tota TOTA.zip]
                        [--level constituency|province|municipality|overseas]
    actasum es describe --mesa MESA.zip
    actasum es seats    --mesa MESA.zip            (local elections only)
    actasum es convert  --mesa MESA.zip --out statements.jsonl
    actasum es official --tota TOTA.zip --out official.json
    actasum es context  --mesa MESA.zip --out context.json  (draft for `card`)
    actasum verify      --statements statements.jsonl --official official.json
    actasum card        --statements statements.jsonl --official official.json [--official ...]
                        --context context.json [--out card.json]

    actasum co convert  --mmv MMV.csv --election 2026-05 [--age-text AGE.txt]
                        --out statements.jsonl

    actasum mx replay   --prep PRES_2024.csv --computos PRES_2024.csv --election 2024-06
                        [--official official.json] [--out statements.jsonl]

    actasum br replay   --bu bweb_1t_RR_....zip [--bu ...] [--official official.json ...]
                        [--out statements.jsonl]
    actasum br official --report Relatorio_Resultado_Totalizacao_2026_RR.zip [--report ...]
                        --round 1|2 [--states-out FILE] [--country-out FILE]

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
import hashlib
import json
import os
import sys
from typing import Sequence

from .card import build_card
from .log import (
    Checkpoint,
    Log,
    check_checkpoint,
    verify_consistency_proof,
    verify_inclusion_proof,
)
from .note import SignatureError
from .profiles.br import relatorio as br_relatorio
from .profiles.br import tse as br_tse
from .profiles.co import escrutinio as co_escrutinio
from .profiles.es import infoelectoral, seats as es_seats
from .profiles.mx import ine as mx_ine
from .statement import FormatError, OfficialTotals, read_jsonl, write_jsonl
from .verify import (
    VerificationError,
    aggregate,
    compare,
    format_comparison,
    resolve,
    verify,
)


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


def _es_context(args) -> int:
    context = infoelectoral.card_context(infoelectoral.load_dataset(args.mesa))
    _write_json(context, args.out)
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
    if recorded:
        recorded = "sha256:" + recorded.removeprefix("sha256:").lower()
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
        changes, unparsed = co_escrutinio.read_modifications(age_text)
        chained = co_escrutinio.chain(statements, changes, co_escrutinio.municipalities(table))
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


def _mx_replay(args) -> int:
    """PREP and Cómputos Distritales databases to statements of two acts."""
    report: dict = {"files": []}
    statements = []
    counts: dict[str, str] = {}
    no_figures: dict[str, str] = {}
    headers_ok = True
    codes: list[str] = []
    for path, kind in ((args.prep, mx_ine.PREP), (args.computos, mx_ine.COMPUTOS)):
        if not path:
            continue
        table = mx_ine.load(path)
        if table.kind != kind:
            raise FormatError(f"{path}: expected a {kind} database, found a {table.kind} one")
        codes = table.codes
        checks = mx_ine.check_header(table)
        headers_ok = headers_ok and all(check.ok for check in checks)
        if kind == mx_ine.PREP:
            reading = mx_ine.read_prep(table, args.election)
            counts = reading.identifiers
        else:
            reading = mx_ine.read_computos(table, args.election, counts)
            no_figures = reading.no_figures
        statements.extend(reading.statements)
        entry: dict = {
            "file": table.path,
            "kind": table.kind,
            "sha256": table.sha256,
            "election": table.title,
            "cut": table.cut,
            "rows": reading.rows,
            "statements": len(reading.statements),
            "rows_without_a_statement": dict(reading.left_out.most_common()),
            "header_totals_recomputed_from_the_rows": [
                {"name": c.name, "in_header": c.in_header, "from_rows": c.from_rows, "equal": c.ok}
                for c in checks
            ],
        }
        if kind == mx_ine.PREP:
            entry.update(
                {
                    "tally_sheets_counted_with_unread_figures": dict(
                        sorted(reading.with_unread_figures.items())
                    ),
                    "unread_cells": dict(sorted(reading.unread_cells.items())),
                    "tally_sheets_whose_written_total_is_not_the_sum": reading.stated_total_differs,
                    "ballots_in_rows_of_the_vote_from_abroad_per_state": reading.state_wide_ballots,
                }
            )
        report["files"].append(entry)
    merge = mx_ine.coalition_merge(codes)
    resolution = resolve(statements)

    def totals(group) -> dict:
        area = aggregate(group, merge=merge).get(mx_ine.COUNTRY)
        if area is None:
            return {"stations": 0}
        doc = {
            "stations": area.stations,
            "candidatures": dict(sorted(area.candidatures.items())),
            "other": dict(sorted((area.other or {}).items())),
            "null": area.null,
            "ballots": area.candidature_total + area.null + sum((area.other or {}).values()),
        }
        if area.unread:
            doc["these_are_lower_bounds"] = (
                "figures could not be read; statements concerned, by item"
            )
            doc["unread"] = dict(sorted(area.unread.items()))
        return doc

    report["as_counted"] = totals(resolution.counted)
    report["as_standing"] = totals(resolution.standing)
    unreplaced = [s for s in resolution.standing if s.stage == "count"] if args.computos else []
    if unreplaced:
        said = sorted({no_figures.get(s.station, "no row for this station") for s in unreplaced})
        report["as_standing"]["includes"] = {
            "stations_whose_count_no_later_act_replaced": len(unreplaced),
            "their_ballots": sum(s.ballots for s in unreplaced),
            "what_the_canvass_file_says_of_them": said,
            "so": "this sum cannot equal the total of the canvass file, which has no "
            "figures for those stations",
        }
    report["between_the_two_acts"] = mx_ine.describe(resolution, merge)
    report["unread_figures_against_the_canvass"] = mx_ine.unread_against_canvass(resolution)
    # Their count is left standing by the core: nothing replaces it.
    report["stations_with_a_count_but_no_canvass"] = [
        {
            "station": s.station,
            "ballots_read_in_the_count": s.ballots,
            "figures_unread_in_the_count": len(s.unread),
            "the_canvass_file_says": no_figures.get(s.station, "no row for this station"),
        }
        for s in resolution.standing
        if s.stage == "count" and args.computos
    ]
    matched = True
    if args.official:
        with open(args.official, encoding="utf-8") as handle:
            totals = OfficialTotals.from_dict(json.load(handle))

        def against(found) -> dict:
            return {
                "stations": found.stations,
                "matches": found.ok,
                "undecided": found.undecided,
                "differences": [
                    {"item": d.item, "recomputed": d.recomputed, "official": d.official,
                     "difference": d.describe_delta}
                    for d in found.differences
                ],
                "nothing_is_said_about": [
                    {"item": b.item, "recomputed_at_least": b.recomputed, "official": b.official,
                     "statements_with_the_figure_unread": b.statements}
                    for b in found.bounds
                ],
            }  # fmt: skip

        comparison = compare(statements, totals)
        canvass = [s for s in statements if s.stage == "canvass"]
        report["against_the_official_totals"] = {
            "source": totals.source,
            "official_matches": comparison.official_matches,
            "as_counted": against(comparison.counted),
            "as_standing": against(comparison.standing),
            # The standing sum also holds stations whose count nothing replaced.
            "statements_of_the_canvass_alone": against(verify(canvass, totals)),
        }
        matched = comparison.ok
    if args.out:
        out = _open_out(args.out)
        try:
            report["statements_written"] = write_jsonl(statements, out)
        finally:
            if out is not sys.stdout:
                out.close()
    json.dump(report, sys.stderr if args.out == "-" else sys.stdout, indent=2, ensure_ascii=False)
    (sys.stderr if args.out == "-" else sys.stdout).write("\n")
    return 0 if headers_ok and matched else 1


def _br_replay(args) -> int:
    """TSE ballot-box report files to statements of the count, and a comparison."""
    statements = []
    files = []
    parties: dict[str, str] = {}
    for path in args.bu:
        table = br_tse.load(path)
        reading = br_tse.read_bu(table, args.office)
        statements.extend(reading.statements)
        parties.update(reading.parties)
        files.append(
            {
                "path": table.path,
                "csv": table.name,
                "sha256_of_the_csv": table.sha256,
                "generated": table.generated,
                "rows_in_the_file": reading.rows_in_file,
                "rows_of_this_office": reading.rows,
                "statements": len(reading.statements),
                "sections_without_a_statement": dict(reading.left_out.most_common()),
                "votes_in_sections_without_a_statement": dict(
                    reading.votes_left_out.most_common()
                ),
                "sections_whose_report_covers_other_sections": reading.with_aggregated_sections,
                "sections_whose_votes_are_not_their_turnout": reading.turnout_differs,
            }
        )
    elections = sorted({s.election for s in statements})
    if len(elections) > 1:
        raise FormatError(f"the files belong to different elections: {elections}")
    stations = [s.station for s in statements]
    if len(set(stations)) != len(stations):
        raise FormatError("a section appears in more than one file")

    def summed(group) -> dict:
        area = aggregate(group).get(br_tse.COUNTRY)
        return {
            "stations": area.stations,
            "candidatures": dict(sorted(area.candidatures.items())),
            "blank": area.blank,
            "null": area.null,
            "ballots": area.candidature_total + area.blank + area.null,
            "registered": sum(s.registered or 0 for s in group),
            "turnout": sum(s.extra.get("turnout", 0) for s in group),
        }

    report: dict = {
        "files": files,
        "election": elections[0] if elections else None,
        "statements": len(statements),
        "sum_of_the_statements": summed(statements),
        "party_of_each_candidature_number": dict(sorted(parties.items())),
    }
    matched = True
    comparisons = []
    for official in args.official or []:
        with open(official, encoding="utf-8") as handle:
            totals = OfficialTotals.from_dict(json.load(handle))
        found = verify(statements, totals)
        comparisons.append({
            "file": official,
            "source": totals.source,
            "areas_compared": sorted(totals.areas),
            "matches": found.ok,
            "differences": [
                {"area": d.area, "item": d.item, "recomputed": d.recomputed,
                 "official": d.official, "difference": d.describe_delta}
                for d in found.differences
            ],
            "areas_in_the_statements_only": found.missing_official,
            "areas_in_the_official_totals_only": found.missing_statements,
            "station_issues": [
                {"station": i.station, "issue": i.code, "detail": i.detail}
                for i in found.station_issues
            ],
        })  # fmt: skip
        if found.counted_as:
            # Never a silent match: what was compared as what, and why.
            comparisons[-1]["counted_as_the_official_totals_declare"] = [
                {"area": c.area, "candidature": c.candidature, "counted_as": c.counted_as,
                 "votes": c.votes, "statements": c.statements, "said": c.describe()}
                for c in found.counted_as
            ]  # fmt: skip
        matched = matched and found.ok
    if comparisons:
        report["against_the_official_totals"] = (
            comparisons[0] if len(comparisons) == 1 else comparisons
        )
    if args.out:
        out = _open_out(args.out)
        try:
            report["statements_written"] = write_jsonl(statements, out)
        finally:
            if out is not sys.stdout:
                out.close()
    stream = sys.stderr if args.out == "-" else sys.stdout
    json.dump(report, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
    return 0 if matched else 1


def _br_official(args) -> int:
    """TSE totalisation reports (ZIP files) to official totals."""
    reports = [br_relatorio.read_zip(path, args.round) for path in args.report]
    by_state, by_country = br_relatorio.official_totals(reports)
    written = {}
    for doc, path, what in ((by_state, args.states_out, "states"),
                            (by_country, args.country_out, "country")):  # fmt: skip
        if doc is None or not path:
            continue
        _write_json(doc, path)
        written[what] = {"file": path, "areas": sorted(doc["areas"])}
    summary = {
        "reports": [
            {"unit": r.unit, "file": r.file, "issued": r.issued, "result_as_of": r.result_as_of,
             "count_as": r.count_as}
            for r in reports
        ],
        "written": written,
    }  # fmt: skip
    json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
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


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _card(args) -> int:
    statements = _read_statements(args.statements)
    officials = []
    for path in args.official:
        with open(path, encoding="utf-8") as handle:
            officials.append(OfficialTotals.from_dict(json.load(handle)))
    with open(args.context, encoding="utf-8") as handle:
        context = json.load(handle)
    inputs = {
        "statements": {
            "file": os.path.basename(args.statements),
            "sha256": _sha256(args.statements),
            "statements": len(statements),
        },
        "official": [
            {"file": os.path.basename(path), "sha256": _sha256(path)} for path in args.official
        ],
        "context": {"file": os.path.basename(args.context), "sha256": _sha256(args.context)},
    }
    card = build_card(statements, officials, context, inputs)
    _write_json(card, args.out)
    return 0


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

    card = commands.add_parser(
        "card", help="verifiability card: margins, remote vote and what is published"
    )
    card.add_argument("--statements", required=True, help="JSON Lines file of statements")
    card.add_argument(
        "--official", required=True, action="append", help="official totals (JSON); repeatable"
    )
    card.add_argument("--context", required=True, help="card context (JSON)")
    card.add_argument("--out", default="-", help="output file (default: stdout)")
    card.set_defaults(run=_card)

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

    mx = commands.add_parser("mx", help="Mexico profile: INE PREP and Cómputos databases")
    mx_commands = mx.add_subparsers(dest="mx_command", required=True)
    mx_replay = mx_commands.add_parser(
        "replay",
        help="PREP and Cómputos Distritales databases -> statements of the count and "
        "of the canvass, and what changed between them",
    )
    mx_replay.add_argument("--prep", help="the PREP database of one election (a .csv file)")
    mx_replay.add_argument(
        "--computos", help="the Cómputos Distritales database of the same election"
    )
    mx_replay.add_argument("--election", required=True, help="election date as YYYY-MM")
    mx_replay.add_argument(
        "--official",
        help="official totals (JSON) from a source other than these two files, to compare "
        "both sums with",
    )
    mx_replay.add_argument("--out", help="also write the statements to this file")
    mx_replay.set_defaults(run=_mx_replay)

    br = commands.add_parser("br", help="Brazil profile: TSE ballot-box report files")
    br_commands = br.add_subparsers(dest="br_command", required=True)
    br_replay = br_commands.add_parser(
        "replay",
        help="a ballot-box report file (bweb_*.csv, or its ZIP) -> statements of the "
        "count, their sum, and a comparison with official totals",
    )
    br_replay.add_argument(
        "--bu", required=True, action="append",
        help="the bweb ZIP or CSV file of one state; repeat for several states",
    )  # fmt: skip
    br_replay.add_argument(
        "--office", default="1", help="office code in the file (default 1, president)"
    )
    br_replay.add_argument(
        "--official", action="append",
        help="official totals (JSON) to compare with; repeat to compare at several levels",
    )  # fmt: skip
    br_replay.add_argument("--out", help="also write the statements to this file")
    br_replay.set_defaults(run=_br_replay)
    br_official = br_commands.add_parser(
        "official",
        help="TSE presidential totalisation reports (Relatorio_Resultado_Totalizacao_*.zip) "
        "-> official totals per state and for the country; needs pdftotext",
    )
    br_official.add_argument(
        "--report", required=True, action="append",
        help="a Relatorio_Resultado_Totalizacao_<year>_<UF>.zip file; repeat for each state, "
        "ZZ and BR",
    )  # fmt: skip
    br_official.add_argument("--round", type=int, choices=[1, 2], required=True)
    br_official.add_argument("--states-out", help="official totals per state and abroad")
    br_official.add_argument("--country-out", help="official totals for the country (BR)")
    br_official.set_defaults(run=_br_official)

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

    context = es_commands.add_parser(
        "context", help="draft card context: seats, overseas and postal vote"
    )
    context.add_argument("--mesa", required=True, help="the _MESA ZIP file or a directory")
    context.add_argument("--out", default="-", help="output file (default: stdout)")
    context.set_defaults(run=_es_context)

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
