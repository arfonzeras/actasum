"""Reader for the ballot-box report files of Brazil's Tribunal Superior Eleitoral.

The TSE publishes, per state and per round, a file with the content of every
*boletim de urna* (BU): the report each electronic voting machine prints and
signs when voting closes at its polling station (*seção eleitoral*). The file
is ``bweb_<round>_<UF>_<generated>.csv``, inside a ZIP file of the same name,
with a ``leiame`` that describes its columns. It has one row per section,
office and recipient of votes (*votável*).

One section gives one statement of the count, per office. The figures are
those of the machine's report; nothing else is added up or moved. Votes the
totalisation later gives another destination, such as those for a candidate
who withdrew, stay where the report has them (see docs/spec/profile-br.md,
section 6).

The file carries the names of candidates and of municipalities. Statements
copy only numbers and codes.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field

from ...statement import FormatError, Statement
from . import PROFILE

COUNTRY = "br"

# Offices this profile reads: code in the file -> name in identifiers.
OFFICES = {"1": "presidente"}

# Codes of recipient types (CD_TIPO_VOTAVEL) and of machine status
# (CD_TIPO_URNA), as the leiame and the 2026 files give them.
NOMINAL, BLANK, NULL, PARTY = "1", "2", "3", "4"
COUNTED = "1"  # Apurada

_COLUMNS = (
    "SG_UF", "NR_ZONA", "NR_SECAO", "CD_CARGO_PERGUNTA", "DT_PLEITO", "NR_TURNO",
    "CD_ELEICAO", "CD_TIPO_URNA", "DS_TIPO_URNA", "CD_TIPO_VOTAVEL", "NR_VOTAVEL",
    "QT_VOTOS", "QT_APTOS", "QT_COMPARECIMENTO", "DS_SECOES_AGREGADAS",
    "DT_GERACAO", "HH_GERACAO", "CD_MUNICIPIO",
)  # fmt: skip
# Fields that describe the section, not one recipient of votes: every row of a
# section and office must give them the same value.
_SECTION_FIELDS = (
    "DT_PLEITO", "NR_TURNO", "CD_ELEICAO", "CD_TIPO_URNA", "DS_TIPO_URNA",
    "QT_APTOS", "QT_COMPARECIMENTO", "DS_SECOES_AGREGADAS", "CD_MUNICIPIO",
)  # fmt: skip
_NULL_TEXT = "#NULO#"


@dataclass
class Table:
    """One ballot-box report file, not yet read.

    The files are large (several GB for the largest states), so they are read
    once, row by row, by ``read_bu``; the hash of the CSV and the time it was
    generated are filled in by that pass.
    """

    path: str
    name: str  # file name of the CSV
    columns: list[str]
    sha256: str = ""  # of the CSV file itself, not of the ZIP around it
    generated: str = ""  # DT_GERACAO and HH_GERACAO, as the file gives them

    def open(self) -> io.RawIOBase:
        if zipfile.is_zipfile(self.path):
            archive = zipfile.ZipFile(self.path)
            return archive.open(self.name)
        return open(self.path, "rb")


class _Hashing(io.RawIOBase):
    """A binary stream that hashes what is read through it."""

    def __init__(self, raw):
        self.raw, self.hash = raw, hashlib.sha256()

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        data = self.raw.read(len(buffer))
        self.hash.update(data)
        buffer[: len(data)] = data
        return len(data)


def _csv_name(path: str) -> str:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise FormatError(f"{path}: expected one CSV file inside, found {len(names)}")
        return names[0]
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def load(path: str) -> Table:
    """Open ``bweb_*.csv``, or the ZIP file the TSE publishes it in, and check
    its columns. The rows are read by ``read_bu``."""
    table = Table(path=path, name=_csv_name(path), columns=[])
    with table.open() as raw:
        # The leiame: Latin 1, fields in quotes and separated by semicolons.
        text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
        header = next(csv.reader(text, delimiter=";"), [])
    missing = [c for c in _COLUMNS if c not in header]
    if missing:
        raise FormatError(f"{path}: not a ballot-box report file; missing {missing}")
    table.columns = header
    return table


def _number(text: str, what: str) -> int:
    if not re.fullmatch(r"\d+", text):
        raise FormatError(f"{what} is not a non-negative integer: {text!r}")
    return int(text)


def election_id(office: str, date: str) -> str:
    """``br/presidente/2026-10-04``: office and date of the vote, from the file.

    Both rounds of an election fall in the same month, so the full date is
    part of the identifier.
    """
    match = re.match(r"(\d{4}-\d{2}-\d{2})", date)
    if not match:
        raise FormatError(f"not a date: {date!r}")
    return f"{COUNTRY}/{OFFICES[office]}/{match[1]}"


def station_id(state: str, zone: str, section: str) -> str:
    """``br/rr/0001/0585``: state, electoral zone, section.

    A section number is unique within its zone and a zone number within its
    state. The municipality is not needed and is left out.
    """
    if not re.fullmatch(r"[A-Z]{2}", state):
        raise FormatError(f"not a state: {state!r}")
    return f"{COUNTRY}/{state.lower()}/{_number(zone, 'zone'):04d}/{_number(section, 'section'):04d}"


@dataclass
class Reading:
    """Statements built from one file, and what was left out."""

    statements: list[Statement] = field(default_factory=list)
    rows: int = 0  # rows of the office read
    # Sections that gave no statement, by the machine status the file gives.
    left_out: Counter = field(default_factory=Counter)
    # Votes in the sections left out, by machine status.
    votes_left_out: Counter = field(default_factory=Counter)
    # Sections whose votes do not add up to the voters who turned out.
    turnout_differs: list[str] = field(default_factory=list)
    # Sections whose report also covers other sections (*seções agregadas*).
    with_aggregated_sections: int = 0
    # Party acronym per candidature number, as the file gives it.
    parties: dict[str, str] = field(default_factory=dict)
    rows_in_file: int = 0  # all rows, of every office


def read_bu(table: Table, office: str = "1") -> Reading:
    """One statement of the count per section whose machine was counted.

    The file is read once. Rows of other offices are skipped. A section whose
    machine status is not *Apurada* gives no statement; it is counted in
    ``left_out`` with the status as the file writes it. The hash of the CSV
    and the time it was generated are set on ``table``.
    """
    if office not in OFFICES:
        raise FormatError(f"office {office!r} is not supported by this profile version")
    at = {name: table.columns.index(name) for name in _COLUMNS + ("SG_PARTIDO", "DS_TIPO_VOTAVEL")
          if name in table.columns}  # fmt: skip
    kept = [n for n in _COLUMNS + ("SG_PARTIDO", "DS_TIPO_VOTAVEL") if n in at]
    office_at, width = at["CD_CARGO_PERGUNTA"], len(table.columns)
    generated_at = (at["DT_GERACAO"], at["HH_GERACAO"])
    sections: dict[str, list[dict[str, str]]] = {}
    reading = Reading()
    generated: set[str] = set()
    with table.open() as raw:
        hashing = _Hashing(raw)
        text = io.TextIOWrapper(io.BufferedReader(hashing, 1 << 20), encoding="latin-1", newline="")
        rows = csv.reader(text, delimiter=";")
        next(rows)  # the header, read by load()
        for fields in rows:
            reading.rows_in_file += 1
            if len(fields) != width:
                raise FormatError(
                    f"{table.path}: data line {reading.rows_in_file + 1}: "
                    f"{len(fields)} columns, expected {width}"
                )
            generated.add(f"{fields[generated_at[0]]} {fields[generated_at[1]]}")
            if fields[office_at] != office:
                continue
            reading.rows += 1
            row = {name: fields[at[name]] for name in kept}
            key = station_id(row["SG_UF"], row["NR_ZONA"], row["NR_SECAO"])
            sections.setdefault(key, []).append(row)
        table.sha256 = "sha256:" + hashing.hash.hexdigest()
    if not reading.rows_in_file:
        raise FormatError(f"{table.path}: no rows")
    if len(generated) != 1:
        raise FormatError(f"{table.path}: rows generated at different times: {sorted(generated)}")
    table.generated = generated.pop()
    if not sections:
        raise FormatError(f"{table.path}: no rows for office {office}")
    for station, rows in sorted(sections.items()):
        first = rows[0]
        for name in _SECTION_FIELDS:
            if any(row[name] != first[name] for row in rows):
                raise FormatError(f"{table.path}: {station}: rows disagree on {name}")
        election = election_id(office, first["DT_PLEITO"])
        if first["CD_TIPO_URNA"] != COUNTED:
            reading.left_out[first["DS_TIPO_URNA"]] += 1
            reading.votes_left_out[first["DS_TIPO_URNA"]] += sum(
                _number(row["QT_VOTOS"], "QT_VOTOS") for row in rows
            )
            continue
        blank = null = 0
        candidatures: Counter = Counter()
        seen: set[tuple[str, str]] = set()
        for row in rows:
            kind, number = row["CD_TIPO_VOTAVEL"], row["NR_VOTAVEL"]
            if (kind, number) in seen:
                raise FormatError(f"{table.path}: {station}: recipient {number} appears twice")
            seen.add((kind, number))
            votes = _number(row["QT_VOTOS"], f"{station}: QT_VOTOS")
            if kind == NOMINAL:
                candidatures[number] += votes
                if row.get("SG_PARTIDO", _NULL_TEXT) != _NULL_TEXT:
                    reading.parties.setdefault(number, row["SG_PARTIDO"])
            elif kind == BLANK:
                blank += votes
            elif kind == NULL:
                null += votes
            else:
                # Votes for a party list (*legenda*) exist only for
                # proportional offices; any other type is unknown here.
                raise FormatError(
                    f"{table.path}: {station}: recipient type {kind} "
                    f"({row.get('DS_TIPO_VOTAVEL', '')}) is not read by this profile"
                )
        turnout = _number(first["QT_COMPARECIMENTO"], f"{station}: QT_COMPARECIMENTO")
        extra: dict = {"turnout": turnout}
        aggregated = first["DS_SECOES_AGREGADAS"]
        if aggregated != _NULL_TEXT:
            extra["aggregated_sections"] = [s.strip() for s in aggregated.split("/")]
            reading.with_aggregated_sections += 1
        statement = Statement(
            profile=PROFILE,
            election=election,
            station=station,
            constituency=COUNTRY,
            blank=blank,
            null=null,
            candidatures=dict(sorted(candidatures.items())),
            registered=_number(first["QT_APTOS"], f"{station}: QT_APTOS"),
            evidence={"kind": "official-dataset", "sha256": table.sha256},
            extra=extra,
        )
        if statement.ballots != turnout:
            reading.turnout_differs.append(station)
        reading.statements.append(statement)
    return reading
