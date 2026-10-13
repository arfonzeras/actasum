"""Official totals from the TSE's presidential totalisation reports.

The TSE publishes, per state, abroad (``ZZ``) and for the whole country
(``BR``), a ZIP file ``Relatorio_Resultado_Totalizacao_<year>_<UF>.zip`` with
one PDF per election and round: ``<code>_<UF>_<NAME>_<year>_T<round>_PRESIDENTE.pdf``
for the president. The report is a "Relatório Resultado da Totalização":
a summary, then annexes. This module reads the PDF's own text layer, as
``pdftotext -layout`` prints it, and nothing else: no figure is typed or read
from an image.

From each report it takes the summary (sections, voters, votes, null votes
split into "na urna" and "técnico", blank votes), the votes per candidate
(annex IV, or the national table) and the destination of each candidate's
votes (annex III). It checks that the report adds up: the candidates to the
valid votes, valid, null and blank votes to the total, and the two kinds of
null votes to null votes. A report that does not is refused.

``pdftotext`` comes with Poppler; it is the only tool outside Python's
standard library that this module needs, and only to turn a PDF into text.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field

from ...statement import FormatError
from . import PROFILE
from .tse import COUNTRY

NATIONAL = "BR"

_SUMMARY = {
    "sections_total": r"1\.Seções eleitorais",
    "aggregated": r"1\.1 Total de seções agregadas",
    "main_sections": r"1\.2 Total de seções principais \(mesas receptoras de votos\)",
    "not_installed": r"1\.3 Total de seções não instaladas",
    "functioned": r"2\.1 Seções que funcionaram",
    "electronic": r"2\.1\.1 Seções apuradas em urnas eletrônicas",
    "manual": r"2\.1\.2 Seções apuradas pelo Sistema de Apuração \(SA\)",
    "annulled_sections": r"2\.1\.3 Seções anuladas",
    "not_counted": r"2\.1\.4 Seções não apuradas",
    "registered": r"2\.2 Eleitorado apto a votar",
    "turnout": r"2\.3 Comparecimento",
    "total": r"2\.5\.1 Total de votos - Presidente",
    "valid": r"Votos válidos",
    "annulled_sub_judice": r"Votos anulados sub judice",
    "annulled": r"Votos anulados",
    "null": r"b\) Votos nulos",
    "null_in_machines": r"Votos nulos na urna",
    "null_technical": r"Votos nulos técnico",
    "blank": r"c\) Votos em branco",
}
_REQUIRED = ("functioned", "electronic", "manual", "not_installed", "total", "valid",
             "null", "null_in_machines", "null_technical", "blank")  # fmt: skip
# Destination of a candidate's votes (annex III) -> the item the totals count
# them as. "Válido" is a vote for the candidate. Others are refused until seen.
_DESTINATIONS = {"Válido": None, "Nulo técnico": "null"}
_REPORT_NAME = re.compile(r"Relatorio_Resultado_Totalizacao_(\d{4})_([A-Z]{2})\.zip$")


@dataclass
class Report:
    """What one presidential report says, as read from its text."""

    unit: str  # UF, "ZZ" or "BR"
    election_date: str  # YYYY-MM-DD, from the report's own header
    round: int
    issued: str  # "DD/MM/YYYY HH:MM:SS", as printed
    result_as_of: str | None  # "DD/MM/YYYY - HH:MM:SS", as printed
    summary: dict[str, int]
    candidatures: dict[str, int]
    destinations: dict[str, str] = field(default_factory=dict)
    file: str = ""
    zip_file: str = ""
    sha256: str = ""
    zip_sha256: str = ""

    @property
    def count_as(self) -> dict[str, str]:
        out = {}
        for number, destination in self.destinations.items():
            if destination not in _DESTINATIONS:
                raise FormatError(
                    f"{self.unit}: destination {destination!r} of number {number} "
                    "is not read by this profile version"
                )
            if _DESTINATIONS[destination]:
                out[number] = _DESTINATIONS[destination]
        return out


def _number(text: str) -> int:
    return int(text.replace(".", ""))


def parse(text: str, unit: str = "") -> Report:
    """Read the text of one presidential report (``pdftotext -layout``)."""
    # The national report repeats the summary for each state after its own;
    # only the first summary is read.
    first = re.search(r"Resumo Geral[^\n]*\n", text)
    if first is None:
        raise FormatError(f"{unit}: not a totalisation report: no summary")
    later = re.search(r"Resumo Geral \(", text[first.end() :])
    head = text if later is None else text[: first.end() + later.start()]
    summary: dict[str, int] = {}
    for key, label in _SUMMARY.items():
        found = re.search(r"^\s*" + label + r"\s+(?:[\d,]+%\s+)?([\d.]+)\s*$", head, re.M)
        if found:
            summary[key] = _number(found[1])
    missing = [key for key in _REQUIRED if key not in summary]
    if missing:
        raise FormatError(f"{unit}: the summary lacks {missing}")

    header = re.search(r"Eleições Gerais \d{4} - (\d{2})/(\d{2})/(\d{4})", text)
    round_ = re.search(r"Eleição Geral Federal \d{4} - (\d)º Turno", text)
    issued = re.search(
        r"Justiça Eleitoral/\w+\s+(\d{2}/\d{2}/\d{4})\s*\n[^\n]*?(\d{2}:\d{2}:\d{2})", text
    )
    if not (header and round_ and issued):
        raise FormatError(f"{unit}: the report's header could not be read")
    as_of = re.search(
        r"Resultado em (\d{2}/\d{2}/\d{4} - \d{2}:\d{2}:\d{2}), sujeito a modificações", text
    )

    start = text.find("Resultado de votação")
    end = text.find("Resultado em", start)
    if start < 0 or end < 0:
        raise FormatError(f"{unit}: the table of votes per candidate could not be found")
    candidatures: dict[str, int] = {}
    for row in re.finditer(
        r"^\s*\*?(\d+) - .*?\s([\d.]+)\s+[\d,]+%\s+(\S+(?: \S+)?)\s*(?:\S.*)?$",
        text[start:end],
        re.M,
    ):
        if row[3] != "Válido":
            raise FormatError(f"{unit}: number {row[1]} has destination {row[3]!r} in the table")
        if row[1] in candidatures:
            raise FormatError(f"{unit}: number {row[1]} appears twice in the table")
        candidatures[row[1]] = _number(row[2])

    destinations: dict[str, str] = {}
    for block in re.finditer(
        r"Destinação de votos de candidatas e candidatos(.*?)(?=Anexo IV|Resultado de votação|\Z)",
        text,
        re.S,
    ):
        for row in re.finditer(
            r"^\s*(\d+) - .*?\s{2,}(Válido|Nulo técnico|Anulado sub judice|Anulado)\s*$",
            block[1],
            re.M,
        ):
            destinations[row[1]] = row[2]

    report = Report(
        unit=unit,
        election_date=f"{header[3]}-{header[2]}-{header[1]}",
        round=int(round_[1]),
        issued=f"{issued[1]} {issued[2]}",
        result_as_of=as_of[1] if as_of else None,
        summary=summary,
        candidatures=candidatures,
        destinations=destinations,
    )
    check(report)
    return report


def check(report: Report) -> None:
    """Refuse a report whose own figures do not add up."""
    s, unit = report.summary, report.unit
    failures = []
    if sum(report.candidatures.values()) != s["valid"]:
        failures.append("the candidates do not add up to the valid votes")
    if s["valid"] + s["null"] + s["blank"] + s.get("annulled", 0) + s.get(
        "annulled_sub_judice", 0
    ) != s["total"]:
        failures.append("valid, null and blank votes do not add up to the total")
    if s["null_in_machines"] + s["null_technical"] != s["null"]:
        failures.append("the two kinds of null votes do not add up to null votes")
    if s["electronic"] + s["manual"] != s["functioned"]:
        failures.append("the sections counted do not add up to those that functioned")
    if failures:
        raise FormatError(f"{unit}: " + "; ".join(failures))


def pdf_text(pdf: bytes) -> str:
    """The PDF's text layer, as ``pdftotext -layout`` prints it."""
    tool = shutil.which("pdftotext")
    if tool is None:
        raise FormatError("pdftotext (Poppler) is needed to read the reports and was not found")
    done = subprocess.run(
        [tool, "-layout", "-enc", "UTF-8", "-", "-"], input=pdf, capture_output=True, check=False
    )
    if done.returncode != 0:
        raise FormatError(f"pdftotext failed: {done.stderr.decode(errors='replace').strip()}")
    return done.stdout.decode("utf-8")


def read_zip(path: str, round_: int) -> Report:
    """The presidential report of one round inside a ``Relatorio_...zip`` file."""
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    match = _REPORT_NAME.search(name)
    if match is None:
        raise FormatError(f"{path}: not named Relatorio_Resultado_Totalizacao_<year>_<UF>.zip")
    with open(path, "rb") as handle:
        raw = handle.read()
    with zipfile.ZipFile(path) as archive:
        pdfs = [n for n in archive.namelist() if n.endswith(f"_T{round_}_PRESIDENTE.pdf")]
        if len(pdfs) != 1:
            raise FormatError(
                f"{path}: expected one presidential report of round {round_}, found {len(pdfs)}"
            )
        pdf = archive.read(pdfs[0])
    report = parse(pdf_text(pdf), match[2])
    if report.round != round_:
        raise FormatError(f"{path}: {pdfs[0]} says it is of round {report.round}")
    report.file, report.zip_file = pdfs[0], name
    report.sha256 = hashlib.sha256(pdf).hexdigest()
    report.zip_sha256 = hashlib.sha256(raw).hexdigest()
    return report


_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/relatorio_resultado_totalizacao/"


def _area(report: Report) -> dict:
    s = report.summary
    return {
        "candidatures": dict(sorted(report.candidatures.items())),
        "blank": s["blank"],
        "null": s["null"],
        "candidature_total": s["valid"],
        "stations": s["functioned"],
    }


def _provenance(report: Report) -> dict:
    s = report.summary
    doc = {
        "file": f"{report.file}, inside {report.zip_file}",
        "url": _URL + report.zip_file,
        "pdf_sha256": report.sha256,
        "zip_sha256": report.zip_sha256,
        "issued": report.issued,
        "result_as_of": report.result_as_of,
        "null": f"{s['null_in_machines']} in the machines and {s['null_technical']} "
        '"nulos técnicos"',
        "stations": f"item 2.1, sections that functioned: {s['electronic']} counted in "
        f"electronic machines and {s['manual']} by the Sistema de Apuração (SA); "
        f"{s['not_installed']} not installed",
    }
    if report.count_as:
        doc["count_as"] = "annex III: " + ", ".join(
            f'number {n}, destination "{report.destinations[n]}"' for n in sorted(report.count_as)
        )
    return doc


_TRANSCRIPTION = (
    "taken from each PDF's own text layer with pdftotext -layout by `actasum br official`, "
    "not typed and not read from an image; the command refuses a report whose candidatures "
    "do not add up to its valid votes, whose valid, null and blank votes do not add up to "
    'its total, or whose null votes in the machines and "nulos técnicos" do not add up to '
    "its null votes"
)


def official_totals(reports: list[Report]) -> tuple[dict | None, dict | None]:
    """Official totals per state (and abroad), and for the country.

    Every report must be of the same election day and round. ``count_as`` is
    what annex III of the reports declares. The national report has no annex
    III: it takes the declarations of the state reports, and only when their
    "nulos técnicos" add up to its own.
    """
    if not reports:
        raise FormatError("no report given")
    days = {(r.election_date, r.round) for r in reports}
    if len(days) != 1:
        raise FormatError(f"the reports are of different elections or rounds: {sorted(days)}")
    day, round_ = days.pop()
    units = [r.unit for r in reports]
    if len(set(units)) != len(units):
        raise FormatError("a report is given twice")
    common = {
        "spec": "actasum/official-totals/v0.1",
        "profile": PROFILE,
        "election": f"{COUNTRY}/presidente/{day}",
    }
    states = sorted((r for r in reports if r.unit != NATIONAL), key=lambda r: r.unit)
    national = next((r for r in reports if r.unit == NATIONAL), None)
    declared: dict[str, str] = {}
    for report in states:
        for number, item in report.count_as.items():
            if declared.setdefault(number, item) != item:
                raise FormatError(f"number {number} is counted as different items")
    by_state = None
    if states:
        by_state = dict(
            common,
            level="state",
            grouping="station-prefix/2",
            **({"count_as": dict(sorted(declared.items()))} if declared else {}),
            areas={f"{COUNTRY}/{r.unit.lower()}": _area(r) for r in states},
            source={
                "kind": "official-publication",
                "document": 'Tribunal Superior Eleitoral, SISTOT, "Relatório Resultado da '
                f'Totalização", Eleição Geral Federal, {round_}º Turno, Oficial: the '
                "presidential report of each state and abroad given; each says its result "
                'is subject to change ("sujeito a modificações")',
                "transcription": _TRANSCRIPTION,
                **(
                    {"count_as": "annex III of the reports: "
                     + "; ".join(f'number {n} counted as {i}' for n, i in sorted(declared.items()))}
                    if declared else {}
                ),  # fmt: skip
                "reports": {f"{COUNTRY}/{r.unit.lower()}": _provenance(r) for r in states},
            },
        )
    by_country = None
    if national is not None:
        technical = sum(r.summary["null_technical"] for r in states)
        country_count_as = declared
        if declared and technical != national.summary["null_technical"]:
            raise FormatError(
                'the "nulos técnicos" of the state reports do not add up to the national '
                "report's, so the national totals cannot take their declarations"
            )
        by_country = dict(
            common,
            level="country",
            grouping="constituency",
            **({"count_as": dict(sorted(country_count_as.items()))} if country_count_as else {}),
            areas={COUNTRY: _area(national)},
            source=dict(
                {"kind": "official-publication",
                 "document": 'Tribunal Superior Eleitoral, SISTOT, "Relatório Resultado da '
                 f'Totalização", Eleição Geral Federal, {round_}º Turno, Oficial, Resumo Geral '
                 'do Brasil; it says its result is subject to change ("sujeito a '
                 'modificações")',
                 "transcription": _TRANSCRIPTION + "; from the national summary and the "
                 "national table of votes per candidate, not from the per-state summaries "
                 "that follow them"},
                **_provenance(national),
                **(
                    {"count_as": "the national report has no annex III; the reports of the "
                     f"states and abroad given declare it, and their {technical:,} \"nulos "
                     "técnicos\" add up to the national figure"}
                    if country_count_as else {}
                ),
            ),  # fmt: skip
        )
    return by_state, by_country
