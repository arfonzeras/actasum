"""Brazil profile, on made-up rows in the layout of the TSE ballot-box report file.

The real file has one row per section, office and recipient of votes, in
Latin 1, with every field in quotes and separated by semicolons.
"""

import io
import json
import zipfile

import pytest

from actasum.cli import main
from actasum.profiles.br import tse
from actasum.statement import FormatError

COLUMNS = [
    "DT_GERACAO", "HH_GERACAO", "ANO_ELEICAO", "CD_TIPO_ELEICAO", "NM_TIPO_ELEICAO",
    "CD_PLEITO", "DT_PLEITO", "NR_TURNO", "CD_ELEICAO", "DS_ELEICAO", "SG_UF",
    "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO",
    "CD_CARGO_PERGUNTA", "DS_CARGO_PERGUNTA", "NR_PARTIDO", "SG_PARTIDO", "NM_PARTIDO",
    "DT_BU_RECEBIDO", "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES", "CD_TIPO_URNA",
    "DS_TIPO_URNA", "CD_TIPO_VOTAVEL", "DS_TIPO_VOTAVEL", "NR_VOTAVEL", "NM_VOTAVEL",
    "QT_VOTOS", "NR_URNA_EFETIVADA", "CD_CARGA_1_URNA_EFETIVADA", "CD_CARGA_2_URNA_EFETIVADA",
    "CD_FLASHCARD_URNA_EFETIVADA", "DT_CARGA_URNA_EFETIVADA", "DS_CARGO_PERGUNTA_SECAO",
    "DS_SECOES_AGREGADAS", "DT_ABERTURA", "DT_ENCERRAMENTO", "QT_ELEI_BIOM_SEM_HABILITACAO",
    "DT_EMISSAO_BU", "NR_JUNTA_APURADORA", "NR_TURMA_APURADORA",
]  # fmt: skip
TYPES = {"1": "Nominal", "2": "Branco", "3": "Nulo", "4": "Legenda"}


def row(zone, section, office, kind, number, votes, *, registered=300, turnout=None,
        status=("1", "Apurada"), aggregated="#NULO#", party="AAA", date="2026-10-04 00:00:00"):
    values = {
        "DT_GERACAO": "05/10/2026", "HH_GERACAO": "14:03:43", "ANO_ELEICAO": "2026",
        "CD_TIPO_ELEICAO": "0", "NM_TIPO_ELEICAO": "Eleição Ordinária", "CD_PLEITO": "1",
        "DT_PLEITO": date, "NR_TURNO": "1", "CD_ELEICAO": "6257" if office == "1" else "6259",
        "DS_ELEICAO": "Eleição Geral", "SG_UF": "RR", "CD_MUNICIPIO": "3018",
        "NM_MUNICIPIO": "BOA VISTA", "NR_ZONA": str(zone), "NR_SECAO": str(section),
        "NR_LOCAL_VOTACAO": "1015", "CD_CARGO_PERGUNTA": office,
        "DS_CARGO_PERGUNTA": {"1": "Presidente", "3": "Governador"}[office],
        "NR_PARTIDO": number if kind == "1" else "-1",
        "SG_PARTIDO": party if kind == "1" else "#NULO#",
        "NM_PARTIDO": "Partido" if kind == "1" else "#NULO#",
        "DT_BU_RECEBIDO": "2026-10-04 18:31:08", "QT_APTOS": str(registered),
        "QT_COMPARECIMENTO": str(turnout if turnout is not None else 0),
        "QT_ABSTENCOES": "0", "CD_TIPO_URNA": status[0], "DS_TIPO_URNA": status[1],
        "CD_TIPO_VOTAVEL": kind, "DS_TIPO_VOTAVEL": TYPES[kind], "NR_VOTAVEL": number,
        "NM_VOTAVEL": "Fulano", "QT_VOTOS": str(votes), "NR_URNA_EFETIVADA": "2020070",
        "CD_CARGA_1_URNA_EFETIVADA": "1.", "CD_CARGA_2_URNA_EFETIVADA": "2",
        "CD_FLASHCARD_URNA_EFETIVADA": "AB", "DT_CARGA_URNA_EFETIVADA": "2026-09-24 09:37:00",
        "DS_CARGO_PERGUNTA_SECAO": f"{office} - {section}", "DS_SECOES_AGREGADAS": aggregated,
        "DT_ABERTURA": "2026-10-04 07:00:56", "DT_ENCERRAMENTO": "2026-10-04 16:03:32",
        "QT_ELEI_BIOM_SEM_HABILITACAO": "4", "DT_EMISSAO_BU": "2026-10-04 16:06:34",
        "NR_JUNTA_APURADORA": "-1", "NR_TURMA_APURADORA": "-1",
    }  # fmt: skip
    return [values[c] for c in COLUMNS]


def section(zone, number, votes, **kw):
    """``votes``: {"22": n, "13": n, "blank": n, "null": n}; turnout is their sum."""
    kw.setdefault("turnout", sum(votes.values()))
    rows = []
    for key, value in votes.items():
        kind, recipient = {"blank": ("2", "95"), "null": ("3", "96")}.get(key, ("1", key))
        rows.append(row(zone, number, "1", kind, recipient, value, **kw))
    return rows


def write(path, rows, *, as_zip=False):
    text = io.StringIO(newline="")
    for values in [COLUMNS] + rows:
        text.write(";".join(f'"{v}"' for v in values) + "\r\n")
    raw = text.getvalue().encode("latin-1")
    if as_zip:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("bweb_1t_RR_051020261403.csv", raw)
            archive.writestr("_leiame-boletimurnaweb.pdf", b"%PDF")
    else:
        path.write_bytes(raw)
    return str(path)


ROWS = (
    section(1, 1, {"22": 150, "13": 48, "28": 1, "blank": 4, "null": 7}, registered=275)
    + section(1, 2, {"22": 160, "13": 42, "blank": 0, "null": 1}, aggregated="0182 / 0190")
    # Another office of the same section: not read.
    + [row(1, 1, "3", "1", "25", 99, turnout=210)]
)


def test_one_statement_per_section_of_the_office(tmp_path):
    reading = tse.read_bu(tse.load(write(tmp_path / "b.csv", ROWS)))
    assert reading.rows == 9
    assert [s.station for s in reading.statements] == ["br/rr/0001/0001", "br/rr/0001/0002"]
    first = reading.statements[0]
    assert first.election == "br/presidente/2026-10-04"
    assert first.constituency == "br"
    # What the machine's report says, including a candidate who later withdrew.
    assert first.candidatures == {"13": 48, "22": 150, "28": 1}
    assert (first.blank, first.null, first.registered) == (4, 7, 275)
    assert first.extra == {"turnout": 210}
    assert reading.statements[1].extra["aggregated_sections"] == ["0182", "0190"]
    assert reading.with_aggregated_sections == 1
    assert reading.turnout_differs == []
    assert reading.parties == {"13": "AAA", "22": "AAA", "28": "AAA"}


def test_reads_the_zip_and_hashes_the_csv_inside(tmp_path):
    from_zip = tse.load(write(tmp_path / "b.zip", ROWS, as_zip=True))
    from_csv = tse.load(write(tmp_path / "b.csv", ROWS))
    assert from_zip.sha256 == from_csv.sha256
    assert from_zip.name == "bweb_1t_RR_051020261403.csv"
    assert from_zip.generated == "05/10/2026 14:03:43"


def test_identifiers():
    assert tse.station_id("RR", "1", "585") == "br/rr/0001/0585"
    assert tse.election_id("1", "2026-10-25 00:00:00") == "br/presidente/2026-10-25"
    with pytest.raises(FormatError):
        tse.station_id("Roraima", "1", "1")


def test_turnout_that_is_not_the_sum_of_the_votes_is_reported(tmp_path):
    rows = section(1, 1, {"22": 10, "blank": 0, "null": 0}, turnout=11)
    reading = tse.read_bu(tse.load(write(tmp_path / "b.csv", rows)))
    assert reading.turnout_differs == ["br/rr/0001/0001"]


def test_a_machine_not_counted_gives_no_statement(tmp_path):
    rows = section(1, 1, {"22": 10, "blank": 0, "null": 0}) + section(
        1, 2, {"22": 0, "blank": 0, "null": 0}, status=("5", "Não instalada")
    )
    reading = tse.read_bu(tse.load(write(tmp_path / "b.csv", rows)))
    assert len(reading.statements) == 1
    assert reading.left_out == {"Não instalada": 1}
    assert reading.votes_left_out == {"Não instalada": 0}


def test_rows_of_one_section_that_disagree_are_refused(tmp_path):
    rows = section(1, 1, {"22": 10, "null": 0})
    rows[1][COLUMNS.index("QT_APTOS")] = "301"
    with pytest.raises(FormatError, match="QT_APTOS"):
        tse.read_bu(tse.load(write(tmp_path / "b.csv", rows)))


def test_unknown_recipient_type_is_refused(tmp_path):
    rows = section(1, 1, {"22": 10}) + [row(1, 1, "1", "4", "22", 3, turnout=10)]
    with pytest.raises(FormatError, match="recipient type 4"):
        tse.read_bu(tse.load(write(tmp_path / "b.csv", rows)))


def test_not_a_ballot_box_report_file(tmp_path):
    path = tmp_path / "x.csv"
    path.write_text('"A";"B"\r\n"1";"2"\r\n', encoding="latin-1")
    with pytest.raises(FormatError, match="not a ballot-box report file"):
        tse.load(str(path))


def official(tmp_path, candidatures, null):
    doc = {
        "spec": "actasum/official-totals/v0.1",
        "profile": "br/codigo-eleitoral/v0.1",
        "election": "br/presidente/2026-10-04",
        "level": "state",
        "grouping": "station-prefix/2",
        "areas": {"br/rr": {"candidatures": candidatures, "blank": 4, "null": null,
                            "candidature_total": sum(candidatures.values()), "stations": 2}},
    }  # fmt: skip
    path = tmp_path / "official.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return str(path)


def test_replay_matches_totals_that_add_up_the_same_way(tmp_path, capsys):
    bu = write(tmp_path / "b.zip", ROWS, as_zip=True)
    totals = official(tmp_path, {"22": 310, "13": 90, "28": 1}, 8)
    out = tmp_path / "statements.jsonl"
    assert main(["br", "replay", "--bu", bu, "--official", totals, "--out", str(out)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["statements"] == 2
    assert report["sum_of_the_statements"]["ballots"] == 413
    assert report["against_the_official_totals"]["matches"] is True
    assert len(out.read_text(encoding="utf-8").splitlines()) == 2


def test_replay_reports_votes_the_totals_give_another_destination(tmp_path, capsys):
    # The totals count the withdrawn candidate's vote as null: the verifier
    # reports it as a difference and does not explain it.
    bu = write(tmp_path / "b.csv", ROWS)
    totals = official(tmp_path, {"22": 310, "13": 90}, 9)
    assert main(["br", "replay", "--bu", bu, "--official", totals]) == 1
    found = json.loads(capsys.readouterr().out)["against_the_official_totals"]
    assert {(d["item"], d["difference"]) for d in found["differences"]} == {
        ("null", "-1"),
        ("candidature_total", "+1"),
        ("candidature:28", "+1"),
    }
