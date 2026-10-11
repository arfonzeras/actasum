"""Colombia profile, on made-up data in the layout of the published files.

No real name or identity number appears here. The real files carry the
candidates' identity numbers; the reader must not copy them.
"""

import json

import pytest

from actasum.cli import main
from actasum.profiles.co import escrutinio as co
from actasum.statement import AreaTotals, FormatError, OfficialTotals, read_jsonl
from actasum.verify import compare, resolve

HEADER = ";".join(co.COLUMNS)


def row(zona, puesto, mesa, party, option, votes, name="OPCION"):
    return (f"16;DEPTO;001;CIUDAD;{zona};{puesto};PUESTO {puesto};{mesa:03d};001;COMISION;"
            f"01;PRESIDENTE;0;{party};PARTIDO {party};{option};99999999;{name};{votes:04d}")


ROWS = [
    row("01", "01", 1, "0000", "996", 2, "VOTOS EN BLANCO"),
    row("01", "01", 1, "0009", "011", 49),
    row("01", "01", 1, "0026", "001", 29),
    row("01", "01", 1, "0000", "998", 3, "VOTOS NO MARCADOS"),
    row("01", "C7", 2, "0026", "001", 10),
    row("01", "C7", 2, "0000", "997", 1, "VOTOS NULOS"),
]


def write_mmv(tmp_path, rows=ROWS, *, stray=False, cut=False):
    lines = (["=/;HttpOnly"] if stray else []) + [HEADER] + list(rows)
    text = "\r\n".join(lines) + "\r\n"
    if cut:
        text += "16;DEPTO;001;CIUDAD;01;C7;PUESTO C7;003;001;COMISION;01;PRESIDENTE;0;0026;PARTIDO"
    path = tmp_path / "MMV.csv"
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def entry(zona, puesto, mesa, previous, new, party, option):
    return f"""
DEPARTAMENTO DEPTO, MUNICIPIO CIUDAD, ZONA {zona}, PUESTO {puesto}- PUESTO DE NOMBRE
LARGO SEDE B, MESA N° {mesa}:En la fecha 02-06-2026 10:14:15 a. m. - se modificó la votación.

     Votación        Nueva           Partido/Movimiento Político/GSC/Candidato
     Anterior        Votación

     {previous}               {new}               {party}-NOMBRE DEL PARTIDO / {option}-NOMBRE DE LA
                                     OPCION

"""


# Station 1: two votes of a withdrawn option, and one of another, became unmarked.
AGE = (
    "texto del acta\n"
    + entry("01", "01", 1, 2, 0, "1005", "013")
    + entry("01", "01", 1, 0, 2, "0000", "998")
    + "\n                    Fecha de Generación: 2 de junio de 2026\n   AGE_X\n   SB 2\n"
      "                    Página3de9\n"
    + entry("01", "01", 1, 1, 0, "1006", "009")
    + entry("01", "01", 1, 2, 3, "0000", "998")
)


def test_reads_stations_and_leaves_identity_numbers_out(tmp_path):
    table = co.load_mmv(write_mmv(tmp_path))
    statements = co.read_statements(table, "2026-05")
    first = statements[0]
    assert first.station == "co/16/001/01/01/001"
    assert (first.election, first.constituency, first.stage) == (
        "co/presidente/2026-05", "co", "canvass")
    assert (first.blank, first.null, first.other) == (2, 0, {"unmarked": 3})
    assert first.candidatures == {"0009-011": 49, "0026-001": 29}
    assert statements[1].station == "co/16/001/01/C7/002"
    assert "99999999" not in json.dumps([s.to_dict() for s in statements])


def test_defects_of_the_published_file_are_reported_not_hidden(tmp_path):
    clean = co.load_mmv(write_mmv(tmp_path))
    assert (clean.leading_lines, clean.truncated) == (0, False)
    flawed = co.load_mmv(write_mmv(tmp_path, stray=True, cut=True))
    assert (flawed.leading_lines, flawed.truncated) == (1, True)
    assert len(flawed.rows) == len(clean.rows)
    assert flawed.sha256 != clean.sha256


def test_a_short_row_in_the_middle_is_an_error(tmp_path):
    rows = [ROWS[0], "16;DEPTO;001", ROWS[1]]
    with pytest.raises(FormatError, match="columns"):
        co.load_mmv(write_mmv(tmp_path, rows))


def test_unsupported_corporation(tmp_path):
    rows = [ROWS[1].replace(";01;PRESIDENTE;", ";02;CAMARA;")]
    with pytest.raises(FormatError, match="not supported"):
        co.read_statements(co.load_mmv(write_mmv(tmp_path, rows)), "2026-03")


def test_modifications_are_parsed_across_wraps_and_page_breaks():
    changes, unparsed = co.read_modifications(AGE)
    assert unparsed == 0
    assert [(c.puesto, c.mesa, c.party, c.option, c.previous, c.new) for c in changes] == [
        ("01", "1", "1005", "013", 2, 0), ("01", "1", "0000", "998", 0, 2),
        ("01", "1", "1006", "009", 1, 0), ("01", "1", "0000", "998", 2, 3),
    ]
    assert changes[0].when == "02-06-2026 10:14:15 a. m."


def test_a_date_broken_across_lines_is_still_read():
    broken = entry("01", "01", 1, 2, 0, "1005", "013").replace("02-06-2026", "02-06-\n2026")
    changes, unparsed = co.read_modifications(broken)
    assert unparsed == 0 and changes[0].when == "02-06-2026 10:14:15 a. m."


def test_a_damaged_copy_is_rebuilt_only_if_the_hash_agrees(tmp_path):
    import hashlib

    # The cut row has to be of an option that has an earlier, complete row:
    # that is where its name is taken from.
    rows = ROWS[:4] + [ROWS[5], ROWS[4]]
    original = ("\r\n".join([HEADER] + rows) + "\r\n").encode("utf-8")
    recorded = hashlib.sha256(original).hexdigest()
    # As seen in a published file: a stray first line, and as many bytes
    # missing at the end.
    damaged = b"=/;HttpOnly\r\n" + original[:-13]
    path = tmp_path / "MMV.csv"
    path.write_bytes(damaged)
    assert co.restore(damaged, recorded) == original
    assert co.restore(damaged, "0" * 64) is None
    table = co.load_mmv(str(path), "sha256:" + recorded)
    assert table.sha256 == "sha256:" + recorded
    assert table.published_sha256 == "sha256:" + hashlib.sha256(damaged).hexdigest()
    assert (table.truncated, table.leading_lines, len(table.rows)) == (False, 0, len(ROWS))
    statement = co.read_statements(table, "2026-05")[0]
    assert statement.evidence["published_sha256"] == table.published_sha256
    # With a hash that nothing matches, the file is read as published.
    assert co.load_mmv(str(path), "0" * 64).truncated is True


def test_recorded_hash_is_read_from_the_record_and_partial_files_are_skipped():
    text = ("Se generó el archivo de votación MMV_XXX_16_000_XXX_XX_XX_XXX_1009_P.csv con hash\n"
            "(SHA-256): " + "a" * 64 + ". Más tarde se generó el\narchivo   de   votación   "
            "MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv   con   hash   (SHA-256):\n" + "b" * 64 + ".")
    assert co.recorded_hash(text) == "sha256:" + "b" * 64
    assert co.recorded_hash("nada") is None


def test_entries_that_cannot_be_parsed_are_counted():
    _, unparsed = co.read_modifications(AGE + "\nalgo raro - se modificó la votación.\n")
    assert unparsed == 1


def chained(tmp_path, age=AGE):
    statements = co.read_statements(co.load_mmv(write_mmv(tmp_path)), "2026-05")
    return co.chain(statements, co.read_modifications(age)[0], "16", "001")


def test_undoing_the_changes_gives_the_earlier_statement(tmp_path):
    result = chained(tmp_path)
    assert (result.stations_changed, result.inconsistent, result.unknown_station) == (1, [], [])
    earlier, later, untouched = result.statements
    assert earlier.candidatures == {"0009-011": 49, "0026-001": 29, "1005-013": 2, "1006-009": 1}
    assert earlier.other == {}
    assert later.other == {"unmarked": 3}
    assert later.supersedes == earlier.statement_id()
    assert earlier.stage == later.stage == "canvass"
    assert untouched.supersedes is None


def test_a_change_that_does_not_match_the_file_builds_nothing(tmp_path):
    age = AGE + entry("01", "C7", 2, 5, 99, "0026", "001")
    result = chained(tmp_path, age)
    assert [(c.puesto, c.new) for c in result.inconsistent] == [("C7", 99)]
    assert result.stations_changed == 1
    assert sum(1 for s in result.statements if s.station.endswith("C7/002")) == 1


def test_a_change_for_an_unknown_station_is_listed(tmp_path):
    result = chained(tmp_path, AGE + entry("09", "01", 7, 1, 0, "0026", "001"))
    assert [(c.zona, c.mesa) for c in result.unknown_station] == [("09", "7")]


def test_chain_within_the_canvass_is_not_a_conflict(tmp_path):
    resolution = resolve(chained(tmp_path).statements)
    assert resolution.conflicts == [] and resolution.undetermined == []
    assert len(resolution.standing) == 2 and resolution.counted == []
    (change,) = resolution.changes
    assert (change.from_stage, change.stage) == ("canvass", "canvass")
    assert change.items == {
        "other:unmarked": (0, 3),
        "candidature:1005-013": (2, 0),
        "candidature:1006-009": (1, 0),
    }


def test_official_totals_with_another_category_are_compared(tmp_path):
    statements = chained(tmp_path).statements
    official = OfficialTotals(
        profile=co.PROFILE, election="co/presidente/2026-05",
        areas={"co": AreaTotals(blank=2, null=1, stations=2, other={"unmarked": 3},
                                candidatures={"0009-011": 49, "0026-001": 39})},
    )
    assert OfficialTotals.from_dict(official.to_dict()).areas["co"].other == {"unmarked": 3}
    result = compare(statements, official)
    assert result.standing.ok and result.official_matches == "as standing"
    wrong = OfficialTotals(
        profile=co.PROFILE, election="co/presidente/2026-05",
        areas={"co": AreaTotals(blank=2, null=1, stations=2, other={"unmarked": 0},
                                candidatures={"0009-011": 49, "0026-001": 39})},
    )
    assert {d.item for d in compare(statements, wrong).standing.differences} == {"other:unmarked"}


def test_cli_convert_writes_the_chain_and_a_summary(tmp_path, capsys):
    mmv = write_mmv(tmp_path, stray=True, cut=True)
    age = tmp_path / "AGE.txt"
    age.write_text(AGE, encoding="utf-8")
    out = tmp_path / "statements.jsonl"
    assert main(["co", "convert", "--mmv", mmv, "--election", "2026-05",
                 "--age-text", str(age), "--out", str(out)]) == 0
    summary = json.loads(capsys.readouterr().err)
    assert summary["last_row_cut_short"] is True and summary["lines_before_the_header"] == 1
    assert (summary["stations"], summary["stations_changed"], summary["statements_written"]) == (
        2, 1, 3)
    assert summary["changes_recorded"] == 4 and summary["changes_not_parsed"] == 0
    with open(out, encoding="utf-8") as handle:
        assert len(list(read_jsonl(handle))) == 3
