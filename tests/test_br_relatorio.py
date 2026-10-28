"""Official totals from the TSE's presidential totalisation reports.

The fixtures are made-up texts in the layout ``pdftotext -layout`` gives for
the real reports. A test that turns a real PDF into text needs Poppler and is
skipped without it.
"""

import json
import shutil
import zipfile

import pytest

from actasum.cli import main
from actasum.profiles.br import relatorio
from actasum.statement import FormatError, OfficialTotals


def report_text(*, unit="RORAIMA", date="04/10/2026", round_=1, votes=None, null=(10, 2),
                blank=5, manual=0, destinations=None, national=False, states=(),
                situations=None):  # fmt: skip
    votes = votes or {"22": 300, "13": 100}
    valid = sum(votes.values())
    null_total = sum(null)
    total = valid + null_total + blank
    sections = 3 + manual
    head = f"""      Justiça Eleitoral

Relatório Resultado da Totalização
           Eleição Geral Federal 2026
                   {unit}
                   {round_}º Turno
                {date[:2]} de outubro de 2026
                      20:13:45
                         Justiça Eleitoral/XX                                                {date}
                         SISTOT - SISTEMA DE GERENCIAMENTO DA TOTALIZAÇÃO                      20:13:45
                         Eleições Gerais 2026 - {date}
                         Eleição Geral Federal 2026 - {round_}º Turno
                         Oficial

                                      Relatório Resultado da Totalização
                                   Resumo Geral {'do Brasil' if national else 'da Circunscrição - ' + unit}

Descrição                                                                      Percentual    Valor

1.Seções eleitorais                                                                          {sections + 1}
      1.1 Total de seções agregadas                                                           1
      1.2 Total de seções principais (mesas receptoras de votos)                             {sections}
      1.3 Total de seções não instaladas                                                      0
2. Eleição Majoritária
      2.1 Seções que funcionaram                                                             {sections}
            2.1.1 Seções apuradas em urnas eletrônicas                                       3
            2.1.2 Seções apuradas pelo Sistema de Apuração (SA)                               {manual}
            2.1.3 Seções anuladas                                                             0
            2.1.4 Seções não apuradas                                                          0
      2.2 Eleitorado apto a votar                                                           900
      2.3 Comparecimento                                                          82,88%    {total}
      2.4 Abstenção                                                               17,12%    {900 - total}
      2.5 Totalização
            2.5.1 Total de votos - Presidente                                                              {total}
                 a) Votos a candidatos(as) concorrentes                                97,83%              {valid}
                         Votos válidos                                                100,00%              {valid}
                         Votos anulados sub judice                                     0,00%                  0
                         Votos anulados                                                0,00%                  0
                 b) Votos nulos                                                        1,39%                {null_total}
                        Votos nulos na urna                                            99,70%               {null[0]}
                        Votos nulos técnico                                             0,30%                 {null[1]}
                 c) Votos em branco                                                    0,79%                {blank}
3. Recursos interpostos nas juntas eleitorais *                                                                0
"""
    annex = ""
    if destinations:
        annex = "                                    Anexo III - Destinação de votos de candidatas e candidatos\nCargo: Presidente\n"
        for number, destination in destinations.items():
            if situations is None:
                annex += f"{number} - FULANO DE TAL               Deferido    Deferido   Deferido                                                               {destination}\n"
            else:
                # As in reports issued again later: the line naming the party,
                # and the candidate's situation filled in the last column.
                annex += f"{number} - PARTIDO DE TAL\n"
                annex += f"{number} - FULANO DE TAL               Deferido    Deferido   Deferido                                                               {destination}     {situations[number]}\n"
    table = "                                                              Anexo IV - Resultado de votação\nCargo: Presidente\n"
    for number, n in votes.items():
        table += f"{number} - FULANO DE TAL                                            {n:,}".replace(",", ".") + "           50,00%            Válido\nVICE\n"
    table += "Resultado em 04/10/2026 - 20:05:17, sujeito a modificações.\n"
    tail = "".join(f"\n                                   Resumo Geral ({s})\n" for s in states)
    return head + annex + table + tail


def test_a_state_report():
    text = report_text(destinations={"22": "Válido", "13": "Válido", "28": "Nulo técnico"})
    report = relatorio.parse(text, "RR")
    assert (report.election_date, report.round) == ("2026-10-04", 1)
    assert report.issued == "04/10/2026 20:13:45"
    assert report.result_as_of == "04/10/2026 - 20:05:17"
    assert report.candidatures == {"22": 300, "13": 100}
    assert report.summary["null"] == 12 and report.summary["null_technical"] == 2
    assert report.count_as == {"28": "null"}


def test_the_national_report_reads_only_its_own_summary():
    text = report_text(unit="BRASIL", national=True, states=["EXTERIOR", "ACRE"])
    report = relatorio.parse(text, "BR")
    assert report.summary["functioned"] == 3


def test_a_report_that_does_not_add_up_is_refused():
    text = report_text().replace("Votos válidos                                                100,00%              400",
                                 "Votos válidos                                                100,00%              401")  # fmt: skip
    with pytest.raises(FormatError, match="candidates do not add up"):
        relatorio.parse(text, "RR")


def test_annex_iii_of_reports_issued_later():
    destinations = {"22": "Válido", "13": "Válido", "28": "Nulo técnico"}
    situations = {"22": "2º turno", "13": "2º turno", "28": "Não eleito"}
    report = relatorio.parse(report_text(destinations=destinations, situations=situations), "RR")
    assert report.destinations == destinations
    assert report.count_as == {"28": "null"}


def test_an_annex_iii_row_not_read_is_refused():
    text = report_text(destinations={"22": "Válido", "28": "Nulo técnico"},
                       situations={"22": "2º turno", "28": "Situação nova"})  # fmt: skip
    with pytest.raises(FormatError, match=r"annex III names numbers \['28'\]"):
        relatorio.parse(text, "RR")


def test_nulos_tecnicos_with_every_destination_valid_are_refused():
    with pytest.raises(FormatError, match="every number in annex III has destination"):
        relatorio.parse(report_text(destinations={"22": "Válido", "13": "Válido"}), "RR")


def test_an_unknown_destination_is_refused():
    report = relatorio.parse(report_text(destinations={"28": "Anulado sub judice"}), "RR")
    with pytest.raises(FormatError, match="not read by this profile version"):
        report.count_as


def test_official_totals_per_state_and_for_the_country():
    rr = relatorio.parse(report_text(destinations={"28": "Nulo técnico"}), "RR")
    ac = relatorio.parse(
        report_text(unit="ACRE", votes={"22": 10, "13": 20}, null=(1, 3),
                    destinations={"28": "Nulo técnico"}), "AC")  # fmt: skip
    br = relatorio.parse(
        report_text(unit="BRASIL", national=True, votes={"22": 310, "13": 120}, null=(11, 5)),
        "BR",
    )
    states, country = relatorio.official_totals([rr, ac, br])
    assert sorted(states["areas"]) == ["br/ac", "br/rr"]
    assert states["count_as"] == {"28": "null"} and country["count_as"] == {"28": "null"}
    assert states["election"] == "br/presidente/2026-10-04"
    assert country["areas"]["br"]["null"] == 16
    assert OfficialTotals.from_dict(json.loads(json.dumps(states))).grouping == "station-prefix/2"
    assert OfficialTotals.from_dict(json.loads(json.dumps(country))).grouping == "constituency"


def test_the_country_takes_the_states_declarations_only_if_they_add_up():
    rr = relatorio.parse(report_text(destinations={"28": "Nulo técnico"}), "RR")
    br = relatorio.parse(report_text(unit="BRASIL", national=True, null=(10, 3)), "BR")
    with pytest.raises(FormatError, match="do not add up to the national"):
        relatorio.official_totals([rr, br])


def test_reports_of_different_rounds_are_refused():
    first = relatorio.parse(report_text(), "RR")
    second = relatorio.parse(report_text(unit="ACRE", date="25/10/2026", round_=2), "AC")
    assert (second.election_date, second.round) == ("2026-10-25", 2)
    with pytest.raises(FormatError, match="different elections or rounds"):
        relatorio.official_totals([first, second])


def test_the_round_is_read_from_the_zip(tmp_path, monkeypatch):
    path = tmp_path / "Relatorio_Resultado_Totalizacao_2026_RR.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("6257_RR_RORAIMA_2026_T1_PRESIDENTE.pdf", b"one")
        archive.writestr("9999_RR_RORAIMA_2026_T2_PRESIDENTE.pdf", b"two")
    texts = {b"one": report_text(), b"two": report_text(date="25/10/2026", round_=2)}
    monkeypatch.setattr(relatorio, "pdf_text", lambda pdf: texts[pdf])
    assert relatorio.read_zip(str(path), 2).round == 2
    first = relatorio.read_zip(str(path), 1)
    assert first.file == "6257_RR_RORAIMA_2026_T1_PRESIDENTE.pdf"
    assert first.zip_file == path.name
    texts[b"two"] = report_text()  # a T2 file that says it is of round 1
    with pytest.raises(FormatError, match="says it is of round 1"):
        relatorio.read_zip(str(path), 2)


def test_the_command_writes_both_files(tmp_path, monkeypatch, capsys):
    paths = []
    for unit, kw in (("RR", {"destinations": {"28": "Nulo técnico"}}),
                     ("BR", {"unit": "BRASIL", "national": True})):  # fmt: skip
        path = tmp_path / f"Relatorio_Resultado_Totalizacao_2026_{unit}.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(f"6257_{unit}_X_2026_T1_PRESIDENTE.pdf", report_text(**kw).encode())
        paths += ["--report", str(path)]
    monkeypatch.setattr(relatorio, "pdf_text", lambda pdf: pdf.decode())
    states, country = tmp_path / "states.json", tmp_path / "country.json"
    argv = ["br", "official", *paths, "--round", "1",
            "--states-out", str(states), "--country-out", str(country)]  # fmt: skip
    assert main(argv) == 0
    assert json.loads(states.read_text(encoding="utf-8"))["areas"]["br/rr"]["null"] == 12
    assert json.loads(country.read_text(encoding="utf-8"))["count_as"] == {"28": "null"}
    assert [r["unit"] for r in json.loads(capsys.readouterr().out)["reports"]] == ["RR", "BR"]


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="needs pdftotext (Poppler)")
def test_pdftotext_is_called_on_the_bytes():
    with pytest.raises(FormatError, match="pdftotext failed"):
        relatorio.pdf_text(b"not a pdf")
