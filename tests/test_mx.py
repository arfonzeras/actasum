"""Mexico profile, on made-up data in the layout of the two published files.

The two databases come from the same authority and differ in separator,
encoding, line ending and column names; the fixtures keep those differences.
"""

import json

import pytest

from actasum.cli import main
from actasum.profiles.mx import ine
from actasum.statement import FormatError
from actasum.verify import resolve

PARTIES = ["PAN", "PRI", "PVEM", "MC", "MORENA"]
PREP_COMBOS = ["PAN-PRI", "PVEM_MORENA"]  # the real file mixes both spellings
CODES = ["PAN", "PRI", "PVEM", "MC", "MORENA", "PAN-PRI", "PVEM-MORENA"]
MERGE = {"PAN": "PAN-PRI", "PRI": "PAN-PRI", "PVEM": "PVEM-MORENA", "MORENA": "PVEM-MORENA"}

PREP_COLUMNS = (
    ["CLAVE_CASILLA", "CLAVE_ACTA", "ID_ENTIDAD", "ENTIDAD", "ID_DISTRITO_FEDERAL",
     "DISTRITO_FEDERAL", "SECCION", "ID_CASILLA", "TIPO_CASILLA", "EXT_CONTIGUA",
     "UBICACION_CASILLA", "TIPO_ACTA", "TOTAL_BOLETAS_SOBRANTES", "TOTAL_PERSONAS_VOTARON",
     "TOTAL_REP_PARTIDO_CI_VOTARON", "TOTAL_VOTOS_SACADOS"]
    + PARTIES + PREP_COMBOS
    + ["NO_REGISTRADAS", "NULOS", "TOTAL_VOTOS_ASENTADO", "TOTAL_VOTOS_CALCULADO",
       "LISTA_NOMINAL", "REPRESENTANTES_PP_CI", "OBSERVACIONES", "CONTABILIZADA",
       "MECANISMOS_TRASLADO", "CODIGO_INTEGRIDAD", "FECHA_HORA_ACOPIO", "FECHA_HORA_CAPTURA",
       "FECHA_HORA_VERIFICACION", "ORIGEN", "DIGITALIZACION", "TIPO_DOCUMENTO", "COTEJADA"]
)  # fmt: skip
COMPUTOS_COLUMNS = (
    ["CLAVE_CASILLA", "CLAVE_ACTA", "ID_ENTIDAD", "ENTIDAD", "ID_DISTRITO_FEDERAL",
     "DISTRITO_FEDERAL", "SECCION", "ID_CASILLA", "TIPO_CASILLA", "EXT_CONTIGUA", "CASILLA",
     "TIPO_ACTA"]
    + PARTIES + ["PAN_PRI", "PVEM_MORENA"]
    + ["CANDIDATO/A NO REGISTRADO/A", "VOTOS NULOS", "TOTAL_VOTOS_CALCULADOS", "LISTA_NOMINAL",
       "OBSERVACIONES", "MECANISMOS_TRASLADO", "FECHA_HORA"]
)  # fmt: skip
HASH = "ab" * 32


def prep_row(key, votes, *, stated=None, registered=500, counted="1", note=" ", kind=None):
    """``votes``: seven candidature cells, unregistered and null, as text or numbers."""
    cells = [str(v) for v in votes]
    total = sum(int(c) for c in cells if c.isdigit())
    stated = total if stated is None else stated
    return (
        [f"'{key}'", f"'{key}1'", key[:2].lstrip("0"), "ESTADO", "001", "Distrito", key[2:6],
         key[7:9], kind or key[6], key[9:], "1", "2", "10", str(total), "0", str(total)]
        + cells
        + [str(stated), str(total), str(registered), "4", note, counted, "D", HASH,
           "03/06/2024 02:14:32", "03/06/2024 02:29:06", "03/06/2024 02:29:52", "CASILLA",
           "Móvil", "Acta PREP", "0"]
    )  # fmt: skip


def write_prep(tmp_path, rows, *, summary=None, title="PRESIDENCIA DE LA REPÚBLICA"):
    counted = [r for r in rows if r[PREP_COLUMNS.index("CONTABILIZADA")] == "1"]
    first, last = PREP_COLUMNS.index("PAN"), PREP_COLUMNS.index("NULOS")
    votes = sum(int(c) for r in counted for c in r[first : last + 1] if c.isdigit())
    registered = sum(int(r[PREP_COLUMNS.index("LISTA_NOMINAL")]) for r in counted)
    names = ["ACTAS_ESPERADAS", "ACTAS_CONTABILIZADAS", "LISTA_NOMINAL_ACTAS_CONTABILIZADAS",
             "TOTAL_VOTOS_C_CS"]  # fmt: skip
    values = summary or [str(len(rows)), str(len(counted)), str(registered), str(votes)]

    def line(fields):
        return ",".join(f'"{f}"' if "," in f else f for f in fields)

    lines = [title, "03/06/2024 20:05 (UTC-6)", "", line(names), line(values), "",
             line(PREP_COLUMNS)] + [line(r) for r in rows]  # fmt: skip
    path = tmp_path / "prep.csv"
    path.write_bytes(("\r".join(lines) + "\r").encode("utf-8-sig"))
    return str(path)


def computos_row(key, votes, *, registered=500, note="Cotejo (Levantada en Casilla)"):
    cells = [str(v) for v in votes]
    total = sum(int(c) for c in cells if c.isdigit())
    return (
        [f"'{key}'", f"'{key}1'", f'="{key[:2]}"', "ESTADO", '="001"', "DISTRITO",
         f'="{key[2:6]}"', f'="{key[7:9]}"', key[6], f'="{key[9:]}"', "Urbana", "2"]
        + cells
        + [str(total), str(registered), note, "D", "05/06/2024 22:18:55"]
    )  # fmt: skip


def write_computos(tmp_path, rows, *, total=None):
    first = COMPUTOS_COLUMNS.index("PAN")
    last = COMPUTOS_COLUMNS.index("VOTOS NULOS")
    votes = sum(int(c) for r in rows for c in r[first : last + 1] if c.isdigit())
    registered = sum(int(r[COMPUTOS_COLUMNS.index("LISTA_NOMINAL")]) for r in rows)
    names = ["ACTAS_ESPERADAS", "ACTAS_COMPUTADAS", "LISTA_NOMINAL_ACTAS_COMPUTADAS",
             "TOTAL_VOTOS"]  # fmt: skip
    values = [str(len(rows)), str(len(rows)), f"{registered:,}", f"{total or votes:,}"]
    lines = ["sep=|", "PRESIDENCIA", "08/06/2024 20:30 (UTC-6)", "", "|".join(names),
             "|".join(values), "", "|".join(COMPUTOS_COLUMNS)] + ["|".join(r) for r in rows]
    path = tmp_path / "computos.csv"
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode("latin-1"))
    return str(path)


A, B, C = "010338B0100", "010338C0100", "010339B0100"
#          PAN PRI PVEM MC MORENA PAN-PRI PVEM-MORENA unregistered null
VOTES_A = [69, 14, 17, 40, 193, 2, 10, 0, 12]
VOTES_B = [74, 11, 17, 42, 182, 3, 13, 1, 20]


def test_both_layouts_are_read_and_give_the_same_codes(tmp_path):
    prep = ine.load(write_prep(tmp_path, [prep_row(A, VOTES_A)]))
    computos = ine.load(write_computos(tmp_path, [computos_row(A, VOTES_A)]))
    assert (prep.kind, computos.kind) == (ine.PREP, ine.COMPUTOS)
    assert prep.codes == computos.codes == CODES
    assert computos.rows[0]["SECCION"] == "0338"  # the ="0338" guard is undone
    assert prep.rows[0]["CLAVE_CASILLA"] == A  # and so are the quotes


def test_a_statement_of_the_count(tmp_path):
    table = ine.load(write_prep(tmp_path, [prep_row(A, VOTES_A, stated=350)]))
    reading = ine.read_prep(table, "2024-06")
    (statement,) = reading.statements
    assert statement.station == "mx/01/0338/B0100"
    assert statement.election == "mx/presidencia/2024-06"
    assert statement.stage == "count" and statement.constituency == "mx"
    assert statement.candidatures["PVEM-MORENA"] == 10 and statement.null == 12
    assert statement.other == {"unregistered": 0} and statement.blank == 0
    assert statement.registered == 500
    assert statement.evidence == {"kind": "official-dataset", "sha256": table.sha256}
    assert statement.extra == {"document": "Acta PREP", "image_sha256": HASH, "stated_total": 350}
    assert reading.stated_total_differs == 1


def test_header_totals_are_recomputed_from_the_rows(tmp_path):
    rows = [prep_row(A, VOTES_A), prep_row(B, VOTES_B)]
    assert all(check.ok for check in ine.check_header(ine.load(write_prep(tmp_path, rows))))
    wrong = ine.load(write_prep(tmp_path, rows, summary=["2", "2", "1000", "999"]))
    assert [check.name for check in ine.check_header(wrong) if not check.ok] == [
        "TOTAL_VOTOS_C_CS"
    ]
    computos = ine.load(write_computos(tmp_path, [computos_row(A, VOTES_A)]))
    assert [check.ok for check in ine.check_header(computos)] == [True, True, True]


def test_a_figure_that_could_not_be_read_is_not_a_zero(tmp_path):
    votes = [69, 14, 17, 40, 193, "Sin dato", "Ilegible", 0, 12]
    table = ine.load(write_prep(tmp_path, [prep_row(A, votes), prep_row(B, VOTES_B)]))
    reading = ine.read_prep(table, "2024-06")
    assert [s.station for s in reading.statements] == ["mx/01/0338/C0100"]
    assert reading.with_unreadable_figures == 1
    assert reading.unreadable_cells == {"no-figure": 1, "illegible": 1}
    assert "mx/01/0338/B0100" not in reading.identifiers


def test_unreadable_as_zero_reproduces_the_total_the_file_prints(tmp_path):
    votes = [69, 14, 17, 40, 193, "Sin dato", "Ilegible", 0, "Sin dato"]
    table = ine.load(write_prep(tmp_path, [prep_row(A, votes), prep_row(B, VOTES_B)]))
    reading = ine.read_prep(table, "2024-06", unreadable_as_zero=True)
    assert sum(s.ballots for s in reading.statements) == int(table.summary["TOTAL_VOTOS_C_CS"])
    first = reading.statements[0]
    assert "PAN-PRI" not in first.candidatures and first.null == 0
    assert first.extra["unreadable"] == {
        "PAN-PRI": "no-figure", "PVEM-MORENA": "illegible", "null": "no-figure",
    }  # fmt: skip


def test_what_the_canvass_gives_for_figures_the_prep_could_not_read(tmp_path):
    votes = [69, 14, 17, 40, 193, "Sin dato", "Ilegible", "Sin dato", 12]
    counts = ine.read_prep(
        ine.load(write_prep(tmp_path, [prep_row(A, votes)])), "2024-06", unreadable_as_zero=True
    )
    canvass = ine.read_computos(
        ine.load(write_computos(tmp_path, [computos_row(A, [69, 14, 17, 40, 193, 0, 7, 2, 12])])),
        "2024-06",
        counts.identifiers,
    )
    assert ine.unreadable_against_canvass(resolve(counts.statements + canvass.statements)) == {
        "illegible": {"cells": 1, "not_zero_in_the_canvass": 1, "votes_in_the_canvass": 7},
        "no-figure": {
            "cells": 2, "zero_in_the_canvass": 1, "not_zero_in_the_canvass": 1,
            "votes_in_the_canvass": 2,
        },
    }  # fmt: skip


def test_rows_the_prep_did_not_count_give_no_statement(tmp_path):
    blank = ["-"] * 9
    rows = [
        prep_row(A, VOTES_A),
        prep_row(B, VOTES_B, counted="0", note="['Excede Lista Nominal']"),
        prep_row(C, blank, counted="-", note=" "),
    ]
    rows.append(prep_row(A, VOTES_A, counted="2", note="Fuera de Catálogo"))
    rows[-1][0] = "-"
    reading = ine.read_prep(ine.load(write_prep(tmp_path, rows)), "2024-06")
    assert len(reading.statements) == 1
    assert reading.left_out == {
        "['Excede Lista Nominal']": 1,
        "no tally sheet captured at the cut": 1,
        "Fuera de Catálogo": 1,
    }


def test_the_vote_from_abroad_given_per_state_gives_no_statement(tmp_path):
    rows = [prep_row(A, VOTES_A), prep_row("010000M0100", VOTES_B)]
    reading = ine.read_prep(ine.load(write_prep(tmp_path, rows)), "2024-06")
    assert len(reading.statements) == 1
    assert reading.left_out == {ine.STATE_WIDE: 1}
    assert reading.state_wide_ballots == sum(VOTES_B)


def test_the_canvass_replaces_the_count_and_says_how(tmp_path):
    counts = ine.read_prep(ine.load(write_prep(tmp_path, [prep_row(A, VOTES_A)])), "2024-06")
    table = ine.load(
        write_computos(
            tmp_path,
            [
                computos_row(A, VOTES_A, note="Recuento (Para recuento-SRA)"),
                computos_row(B, VOTES_B),
                computos_row(C, ["-"] * 9, note="Paquete no recibido"),
            ],
        )
    )
    reading = ine.read_computos(table, "2024-06", counts.identifiers)
    first, second = reading.statements
    assert first.stage == second.stage == "canvass"
    assert first.supersedes == counts.statements[0].statement_id()
    assert second.supersedes is None
    assert first.extra == {"canvass": "recount", "observation": "Recuento (Para recuento-SRA)"}
    assert second.extra["canvass"] == "collation"
    assert reading.left_out == {"Paquete no recibido": 1}


def test_coalition_columns_are_merged_into_the_whole_coalition():
    assert ine.coalition_merge(CODES) == MERGE
    three = ["A", "B", "C", "D", "A-B-C", "A-B", "A-C", "B-C"]
    merge = ine.coalition_merge(three)
    assert merge["A-C"] == merge["B"] == "A-B-C" and "D" not in merge and "A-B-C" not in merge


def test_changes_inside_a_coalition_are_told_apart(tmp_path):
    # A: one vote moves from PAN to PAN-PRI, the candidature gets the same.
    # B: three null votes become votes for MORENA after a recount.
    moved = [68, 14, 17, 40, 193, 3, 10, 0, 12]
    recounted = [74, 11, 17, 42, 185, 3, 13, 1, 17]
    counts = ine.read_prep(
        ine.load(write_prep(tmp_path, [prep_row(A, VOTES_A), prep_row(B, VOTES_B)])), "2024-06"
    )
    canvass = ine.read_computos(
        ine.load(
            write_computos(
                tmp_path,
                [
                    computos_row(A, moved),
                    computos_row(B, recounted, note="Recuento (Para recuento-SC)"),
                    computos_row(C, VOTES_A),
                ],
            )
        ),
        "2024-06",
        counts.identifiers,
    )
    resolution = resolve(counts.statements + canvass.statements)
    assert not resolution.conflicts and not resolution.undetermined
    described = ine.describe(resolution, MERGE)
    assert described["stations_with_both_acts"] == 2
    assert described["stations_whose_figures_changed"] == 2
    assert described["changed_by_canvass"] == {"collation": 1, "recount": 1}
    assert described["changed_only_within_a_coalition"] == 1
    assert described["net_change_by_candidature"] == {"PVEM-MORENA": 3, "null": -3}
    assert described["changed_by_size"] == {"6 to 20": 1}
    assert described["net_change_of_the_largest"] == {}
    assert described["stations_with_a_canvass_but_no_count"] == 1
    assert described["stations_with_a_count_but_no_canvass"] == 0


def test_other_elections_and_other_files_are_refused(tmp_path):
    senate = ine.load(write_prep(tmp_path, [prep_row(A, VOTES_A)], title="SENADURÍAS"))
    with pytest.raises(FormatError, match="not supported"):
        ine.read_prep(senate, "2024-06")
    prep = ine.load(write_prep(tmp_path, [prep_row(A, VOTES_A)]))
    with pytest.raises(FormatError, match="not a Cómputos"):
        ine.read_computos(prep, "2024-06")
    with pytest.raises(FormatError, match="YYYY-MM"):
        ine.read_prep(prep, "junio")
    other = tmp_path / "other.csv"
    other.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(FormatError, match="no header line"):
        ine.load(str(other))


def test_a_figure_that_is_neither_a_number_nor_a_known_mark_is_an_error(tmp_path):
    votes = [69, 14, 17, 40, 193, 2, 10, 0, "doce"]
    with pytest.raises(FormatError, match="not a number"):
        ine.read_prep(ine.load(write_prep(tmp_path, [prep_row(A, votes)])), "2024-06")


def test_cli_replay_reports_both_sums_and_writes_the_statements(tmp_path, capsys):
    prep = write_prep(tmp_path, [prep_row(A, VOTES_A), prep_row(B, VOTES_B)])
    computos = write_computos(
        tmp_path, [computos_row(A, VOTES_A), computos_row(B, [74, 11, 17, 42, 185, 3, 13, 1, 17])]
    )
    out = tmp_path / "statements.jsonl"
    code = main(["mx", "replay", "--prep", prep, "--computos", computos,
                 "--election", "2024-06", "--out", str(out)])  # fmt: skip
    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["as_counted"]["ballots"] == sum(VOTES_A) + sum(VOTES_B)
    assert report["as_standing"]["candidatures"]["PVEM-MORENA"] == 17 + 193 + 10 + 17 + 185 + 13
    assert report["between_the_two_acts"]["stations_whose_figures_changed"] == 1
    assert report["statements_written"] == 4 and len(out.read_text().splitlines()) == 4


def test_cli_replay_fails_when_a_file_does_not_add_up_to_its_own_header(tmp_path, capsys):
    computos = write_computos(tmp_path, [computos_row(A, VOTES_A)], total=999)
    assert main(["mx", "replay", "--computos", computos, "--election", "2024-06"]) == 1
    report = json.loads(capsys.readouterr().out)
    checks = report["files"][0]["header_totals_recomputed_from_the_rows"]
    assert [c["name"] for c in checks if not c["equal"]] == ["TOTAL_VOTOS"]
