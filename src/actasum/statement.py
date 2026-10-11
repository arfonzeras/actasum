"""Core data model: the tally-sheet statement and the official totals.

A *statement* says "this is what the tally sheet of polling station S recorded
for election E". It carries counts, never a verdict. Its identifier is the
SHA-256 of its canonical JSON form, so two parties that transcribe the same
tally sheet in the same way obtain the same identifier.

See docs/spec/core.md for the normative description.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, TextIO

STATEMENT_SPEC = "actasum/statement/v0.1"
OFFICIAL_SPEC = "actasum/official-totals/v0.1"
UNITS = frozenset({"station", "aggregate"})


class FormatError(ValueError):
    """Raised when a document does not follow the specification."""


def canonical_json(obj: Any) -> bytes:
    """Serialize ``obj`` deterministically.

    Keys are sorted, there is no insignificant whitespace, and the output is
    UTF-8. The format only allows strings, integers, booleans, null, objects
    and arrays; floats are rejected because their text form is ambiguous.
    """
    _reject_floats(obj)
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _reject_floats(obj: Any) -> None:
    if isinstance(obj, float):
        raise FormatError("floating-point numbers are not allowed")
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise FormatError("object keys must be strings")
            _reject_floats(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            _reject_floats(value)


def _count(value: Any, name: str, *, optional: bool = False) -> int | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FormatError(f"{name} must be a non-negative integer")
    return value


@dataclass(frozen=True)
class Statement:
    """Counts recorded on one polling station's tally sheet."""

    profile: str
    election: str
    station: str
    constituency: str
    blank: int
    null: int
    candidatures: dict[str, int]
    registered: int | None = None
    # Total of valid votes for candidatures as written on the sheet, when the
    # sheet (or the dataset) states it separately from the per-candidature rows.
    candidature_total: int | None = None
    # "station" for a polling station. "aggregate" for a row that carries votes
    # but is not a polling station, such as overseas votes counted centrally.
    unit: str = "station"
    evidence: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def candidature_sum(self) -> int:
        return sum(self.candidatures.values())

    @property
    def ballots(self) -> int:
        """Ballots counted: candidature votes plus blank plus null."""
        return self.candidature_sum + self.blank + self.null

    def to_dict(self) -> dict[str, Any]:
        counts: dict[str, Any] = {
            "blank": self.blank,
            "null": self.null,
            "candidatures": dict(sorted(self.candidatures.items())),
        }
        if self.registered is not None:
            counts["registered"] = self.registered
        if self.candidature_total is not None:
            counts["candidature_total"] = self.candidature_total
        doc: dict[str, Any] = {
            "spec": STATEMENT_SPEC,
            "profile": self.profile,
            "election": self.election,
            "station": self.station,
            "constituency": self.constituency,
            "counts": counts,
        }
        if self.unit != "station":
            doc["unit"] = self.unit
        if self.evidence:
            doc["evidence"] = self.evidence
        if self.extra:
            doc["extra"] = self.extra
        return doc

    @classmethod
    def from_dict(cls, doc: dict[str, Any]) -> "Statement":
        if not isinstance(doc, dict):
            raise FormatError("a statement must be a JSON object")
        if doc.get("spec") != STATEMENT_SPEC:
            raise FormatError(f"unsupported spec: {doc.get('spec')!r}")
        for key in ("profile", "election", "station", "constituency"):
            if not isinstance(doc.get(key), str) or not doc[key]:
                raise FormatError(f"{key} must be a non-empty string")
        counts = doc.get("counts")
        if not isinstance(counts, dict):
            raise FormatError("counts must be an object")
        candidatures = counts.get("candidatures")
        if not isinstance(candidatures, dict):
            raise FormatError("counts.candidatures must be an object")
        unit = doc.get("unit", "station")
        if unit not in UNITS:
            raise FormatError(f"unit must be one of {sorted(UNITS)}")
        return cls(
            profile=doc["profile"],
            election=doc["election"],
            station=doc["station"],
            constituency=doc["constituency"],
            blank=_count(counts.get("blank"), "counts.blank"),
            null=_count(counts.get("null"), "counts.null"),
            candidatures={
                str(code): _count(votes, f"counts.candidatures[{code}]")
                for code, votes in candidatures.items()
            },
            registered=_count(
                counts.get("registered"), "counts.registered", optional=True
            ),
            candidature_total=_count(
                counts.get("candidature_total"),
                "counts.candidature_total",
                optional=True,
            ),
            unit=unit,
            evidence=doc.get("evidence") or {},
            extra=doc.get("extra") or {},
        )

    def canonical(self) -> bytes:
        return canonical_json(self.to_dict())

    def statement_id(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical()).hexdigest()


def write_jsonl(statements: Iterable[Statement], out: TextIO) -> int:
    """Write one canonical statement per line. Returns the number written."""
    written = 0
    for statement in statements:
        out.write(statement.canonical().decode("utf-8"))
        out.write("\n")
        written += 1
    return written


def read_jsonl(src: TextIO) -> Iterator[Statement]:
    for number, line in enumerate(src, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            yield Statement.from_dict(json.loads(line))
        except (json.JSONDecodeError, FormatError) as exc:
            raise FormatError(f"line {number}: {exc}") from exc


@dataclass(frozen=True)
class AreaTotals:
    """Totals published by the electoral authority for one area."""

    blank: int
    null: int
    candidatures: dict[str, int]
    stations: int | None = None
    candidature_total: int | None = None

    def to_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "blank": self.blank,
            "null": self.null,
            "candidatures": dict(sorted(self.candidatures.items())),
        }
        if self.stations is not None:
            doc["stations"] = self.stations
        if self.candidature_total is not None:
            doc["candidature_total"] = self.candidature_total
        return doc

    @classmethod
    def from_dict(cls, doc: dict[str, Any]) -> "AreaTotals":
        if not isinstance(doc, dict) or not isinstance(
            doc.get("candidatures"), dict
        ):
            raise FormatError("area totals need a candidatures object")
        return cls(
            blank=_count(doc.get("blank"), "blank"),
            null=_count(doc.get("null"), "null"),
            candidatures={
                str(code): _count(votes, f"candidatures[{code}]")
                for code, votes in doc["candidatures"].items()
            },
            stations=_count(doc.get("stations"), "stations", optional=True),
            candidature_total=_count(
                doc.get("candidature_total"), "candidature_total", optional=True
            ),
        )


GROUP_BY_CONSTITUENCY = "constituency"
_STATION_PREFIX = "station-prefix/"


def area_of(statement: Statement, grouping: str) -> str:
    """The area a statement counts towards under ``grouping``.

    ``constituency`` uses the statement's own constituency. ``station-prefix/N``
    uses the first N ``/``-separated parts of the station identifier, which
    works because profiles define hierarchical station identifiers.
    """
    if grouping == GROUP_BY_CONSTITUENCY:
        return statement.constituency
    if grouping.startswith(_STATION_PREFIX):
        tail = grouping[len(_STATION_PREFIX) :]
        if tail.isdigit() and int(tail) > 0:
            return "/".join(statement.station.split("/")[: int(tail)])
    raise FormatError(f"unknown grouping: {grouping!r}")


@dataclass(frozen=True)
class OfficialTotals:
    """What the electoral authority published, per area."""

    profile: str
    election: str
    areas: dict[str, AreaTotals]
    # What an area is ("constituency", "municipality"...), for display only.
    level: str = "constituency"
    # How statements are assigned to areas. See ``area_of``.
    grouping: str = GROUP_BY_CONSTITUENCY
    source: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "spec": OFFICIAL_SPEC,
            "profile": self.profile,
            "election": self.election,
            "level": self.level,
            "grouping": self.grouping,
            "areas": {key: value.to_dict() for key, value in sorted(self.areas.items())},
        }
        if self.source:
            doc["source"] = self.source
        return doc

    @classmethod
    def from_dict(cls, doc: dict[str, Any]) -> "OfficialTotals":
        if not isinstance(doc, dict) or doc.get("spec") != OFFICIAL_SPEC:
            raise FormatError("not an official-totals document")
        areas = doc.get("areas")
        if not isinstance(areas, dict):
            raise FormatError("areas must be an object")
        return cls(
            profile=str(doc.get("profile", "")),
            election=str(doc.get("election", "")),
            areas={key: AreaTotals.from_dict(value) for key, value in areas.items()},
            level=str(doc.get("level", "constituency")),
            grouping=str(doc.get("grouping", GROUP_BY_CONSTITUENCY)),
            source=doc.get("source") or {},
        )
