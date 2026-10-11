"""Reader for the scrutiny files published by Colombia's Registraduría.

Two documents of one scrutiny commission are read:

* the ``MMV`` file, a semicolon-separated table with one row per polling
  station (*mesa*) and voting option that received votes;
* the text of the *Acta General de Escrutinio* (AGE), which records every
  change the commission made to a station's figures as "previous vote" and
  "new vote" for one option.

The MMV holds the figures as the commission left them. Undoing the changes
recorded in the AGE gives the figures as the commission received them. Neither
is the tally sheet the station filled in (form E-14): commissions below this
one may have changed the figures before. Both are therefore statements of the
canvass, chained by ``supersedes``.

See docs/spec/profile-co.md.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ...statement import FormatError, Statement
from . import PROFILE

# Election types this profile reads, by the corporation code of the MMV file.
CORPORATIONS = {"01": "presidente"}

# Rows of the MMV file that are not a candidate. The party code is 0000.
BLANK, NULL, UNMARKED = "996", "997", "998"
TOTALS_PARTY = "0000"
UNMARKED_NAME = "unmarked"

COUNTRY = "co"

COLUMNS = [
    "DEP", "DEPNOMBRE", "MUN", "MUNNOMBRE", "ZONA", "PUESTO", "PUESNOMBRE", "MESA",
    "COMUCODIGO", "COMUNOMBRE", "CORCODIGO", "CORNOMBRE", "CIR", "PAR", "PARNOMBRE",
    "CAN", "CANCEDULA", "CANNOMBRE", "VOTOS",
]  # fmt: skip


@dataclass(frozen=True)
class Table:
    """The rows of an MMV file, and what was wrong with the file itself."""

    path: str
    sha256: str
    rows: list[dict[str, str]]
    # Lines before the header that are not part of the table.
    leading_lines: int
    # True when the last line stops before its last column.
    truncated: bool


def load_mmv(path: str) -> Table:
    """Read an MMV file as published.

    The file is kept as it is, defects included, and the defects are
    reported: a published file has been seen to start with a stray line and
    to end in the middle of a row.
    """
    with open(path, "rb") as handle:
        raw = handle.read()
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    lines = raw.decode("utf-8").splitlines()
    header = ";".join(COLUMNS)
    try:
        start = lines.index(header)
    except ValueError:
        raise FormatError(f"{path}: no MMV header line found") from None
    rows: list[dict[str, str]] = []
    truncated = False
    body = [line for line in lines[start + 1 :] if line.strip()]
    for number, line in enumerate(body, start=start + 2):
        fields = line.split(";")
        if len(fields) != len(COLUMNS):
            if number == start + 1 + len(body) and len(fields) < len(COLUMNS):
                truncated = True
                continue
            raise FormatError(
                f"{path}:{number}: {len(fields)} columns, expected {len(COLUMNS)}"
            )
        rows.append(dict(zip(COLUMNS, fields)))
    if not rows:
        raise FormatError(f"{path}: no rows")
    return Table(path=path, sha256=digest, rows=rows, leading_lines=start, truncated=truncated)


def _election(row: dict[str, str], year_month: str, where: str) -> str:
    code = row["CORCODIGO"]
    if code not in CORPORATIONS:
        raise FormatError(
            f"{where}: corporation {code} ({row['CORNOMBRE']}) is not supported "
            "by this profile version"
        )
    return f"co/{CORPORATIONS[code]}/{year_month}"


def station_id(dep: str, mun: str, zona: str, puesto: str, mesa: str) -> str:
    return f"co/{dep}/{mun}/{zona}/{puesto}/{int(mesa):03d}"


def read_statements(table: Table, year_month: str) -> list[Statement]:
    """One statement per station, with the figures the commission left.

    ``year_month`` (``2026-05``) names the election: the file does not carry
    its date. The candidates' identity numbers in the file are not copied.
    """
    if not re.fullmatch(r"\d{4}-\d{2}", year_month):
        raise FormatError("the election date must be given as YYYY-MM")
    stations: dict[str, dict] = {}
    for number, row in enumerate(table.rows, start=1):
        where = f"{table.path}: row {number}"
        election = _election(row, year_month, where)
        key = station_id(row["DEP"], row["MUN"], row["ZONA"], row["PUESTO"], row["MESA"])
        bucket = stations.setdefault(
            key, {"election": election, "blank": 0, "null": 0, "unmarked": 0, "votes": {}}
        )
        if not row["VOTOS"].isdigit():
            raise FormatError(f"{where}: votes are not a number: {row['VOTOS']!r}")
        votes = int(row["VOTOS"])
        if row["PAR"] == TOTALS_PARTY:
            name = {BLANK: "blank", NULL: "null", UNMARKED: "unmarked"}.get(row["CAN"])
            if name is None:
                raise FormatError(f"{where}: unknown totals row {row['CAN']}")
            bucket[name] += votes
        else:
            code = f"{row['PAR']}-{row['CAN']}"
            if code in bucket["votes"]:
                raise FormatError(f"{where}: option {code} repeated for {key}")
            bucket["votes"][code] = votes
    evidence = {"kind": "official-dataset", "sha256": table.sha256}
    return [
        Statement(
            profile=PROFILE,
            election=bucket["election"],
            station=key,
            constituency=COUNTRY,
            blank=bucket["blank"],
            null=bucket["null"],
            candidatures=bucket["votes"],
            other={UNMARKED_NAME: bucket["unmarked"]} if bucket["unmarked"] else {},
            stage="canvass",
            evidence=dict(evidence),
        )
        for key, bucket in stations.items()
    ]


@dataclass(frozen=True)
class Modification:
    """One change to one figure of one station, as the AGE records it."""

    zona: str
    puesto: str
    mesa: str
    party: str
    option: str
    previous: int
    new: int
    when: str  # as printed, e.g. "02-06-2026 10:14:15 a. m."


_FURNITURE = re.compile(
    r"\n[ \t]*Fecha de Generación:[^\n]*\n[^\n]*\n[^\n]*\n[ \t]*Página\s*\d+\s*de\s*\d+[ \t]*\n"
)
_ENTRY = re.compile(
    r"ZONA\s+(\w+),\s+PUESTO\s+(\w+)-\s*(.{1,120}?),\s+MESA\s+N°\s+(\d+)\s*:\s*"
    r"(?:[A-ZÁÉÍÓÚ]+:)?\s*En\s+la\s+fecha\s+(\d\d-\d\d-\d{4}\s+\d\d:\d\d:\d\d\s+[ap]\.\s+m\.)"
    r"\s+-\s+se\s+modificó\s+la\s+votación\.",
    re.S,
)
_ROW = re.compile(r"(\d+)\s+(\d+)\s+(\d{4})-.{0,120}?/\s*(\d{3})-", re.S)
_MENTION = re.compile(r"se\s+modificó\s+la\s+votación\.")


def read_modifications(text: str) -> tuple[list[Modification], int]:
    """Parse the changes recorded in the text of an AGE.

    ``text`` is the output of ``pdftotext -layout`` on the AGE. Returns the
    changes in the order of the record, and the number of entries that were
    seen but could not be parsed; that number should be zero and is reported
    rather than hidden.
    """
    text = _FURNITURE.sub("\n", text.replace("\f", "\n"))
    entries = list(_ENTRY.finditer(text))
    found: list[Modification] = []
    for index, entry in enumerate(entries):
        end = entries[index + 1].start() if index + 1 < len(entries) else entry.end() + 800
        rows = _ROW.findall(text[entry.end() : end][:800])
        if len(rows) != 1:
            continue
        previous, new, party, option = rows[0]
        found.append(
            Modification(
                zona=entry.group(1),
                puesto=entry.group(2),
                mesa=entry.group(4),
                party=party,
                option=option,
                previous=int(previous),
                new=int(new),
                when=" ".join(entry.group(5).split()),
            )
        )
    return found, len(_MENTION.findall(text)) - len(found)


@dataclass
class Chain:
    """Statements before and after a commission's changes, and the checks made."""

    statements: list[Statement]
    stations_changed: int = 0
    # Changes whose "new vote" is not the figure in the MMV file, or whose
    # "previous vote" is not what undoing later changes gives.
    inconsistent: list[Modification] = None  # type: ignore[assignment]
    # Changes that name a station the MMV file does not have.
    unknown_station: list[Modification] = None  # type: ignore[assignment]


def chain(
    statements: list[Statement], modifications: list[Modification], dep: str, mun: str
) -> Chain:
    """Add, for each changed station, the statement the commission started from.

    The changes are undone from last to first. Each one is checked on the way:
    its "new vote" has to be the figure that stands at that point. The statement
    read from the MMV file is re-issued with ``supersedes`` pointing at the
    earlier one, so the two form a chain.
    """
    by_station = {statement.station: statement for statement in statements}
    result = Chain(statements=[], inconsistent=[], unknown_station=[])
    per_station: dict[str, list[Modification]] = {}
    for change in modifications:
        key = station_id(dep, mun, change.zona, change.puesto, change.mesa)
        if key in by_station:
            per_station.setdefault(key, []).append(change)
        else:
            result.unknown_station.append(change)

    for statement in statements:
        changes = per_station.get(statement.station)
        if not changes:
            result.statements.append(statement)
            continue
        figures = {
            "blank": statement.blank,
            "null": statement.null,
            "unmarked": statement.other.get(UNMARKED_NAME, 0),
        }
        votes = dict(statement.candidatures)
        consistent = True
        for change in reversed(changes):
            if change.party == TOTALS_PARTY:
                name = {BLANK: "blank", NULL: "null", UNMARKED: "unmarked"}.get(change.option)
                current = figures.get(name) if name else None
            else:
                name = f"{change.party}-{change.option}"
                current = votes.get(name, 0)
            if current != change.new:
                result.inconsistent.append(change)
                consistent = False
                continue
            if change.party == TOTALS_PARTY:
                figures[name] = change.previous
            else:
                votes[name] = change.previous
        if not consistent:
            # Do not build an earlier statement on a record that does not
            # agree with the file.
            result.statements.append(statement)
            continue
        earlier = Statement(
            profile=statement.profile,
            election=statement.election,
            station=statement.station,
            constituency=statement.constituency,
            blank=figures["blank"],
            null=figures["null"],
            candidatures={code: count for code, count in votes.items() if count},
            other={UNMARKED_NAME: figures["unmarked"]} if figures["unmarked"] else {},
            stage="canvass",
            evidence={
                "kind": "official-publication",
                "derived": "figures of the MMV file with the changes recorded in the AGE undone",
            },
        )
        later = Statement(
            profile=statement.profile,
            election=statement.election,
            station=statement.station,
            constituency=statement.constituency,
            blank=statement.blank,
            null=statement.null,
            candidatures=statement.candidatures,
            other=statement.other,
            stage="canvass",
            supersedes=earlier.statement_id(),
            evidence=statement.evidence,
        )
        result.statements.extend([earlier, later])
        result.stations_changed += 1
    return result
