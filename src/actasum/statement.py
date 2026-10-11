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

# Which act the figures of a statement come from. The count at the polling
# station is the default; the others are acts that may lawfully change it.
STAGE_COUNT = "count"
STAGES = ("count", "canvass", "ruling", "rerun")

# Why a figure of the tally sheet has no value in a statement. "illegible":
# something is written and could not be read. "empty": nothing is written.
# Neither is a zero, and the two are not the same thing.
UNREAD_REASONS = ("illegible", "empty")
# Why a figure does not exist on a tally sheet at all. "no-field": the sheet
# has no field for it. Such a figure is not missing: there is nothing to add.
NOT_ON_SHEET_REASONS = ("no-field",)
_ITEM_CANDIDATURE, _ITEM_OTHER = "candidature:", "other:"


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
    # None only when the figure is listed in ``unread`` or ``not_on_sheet``.
    blank: int | None
    null: int | None
    candidatures: dict[str, int]
    registered: int | None = None
    # Total of valid votes for candidatures as written on the sheet, when the
    # sheet (or the dataset) states it separately from the per-candidature rows.
    candidature_total: int | None = None
    # Ballots that are neither blank, null nor for a candidature, by category.
    # Profiles define the categories, for example ballots left unmarked.
    other: dict[str, int] = field(default_factory=dict)
    # Figures of the sheet that could not be read: item -> reason. An item is
    # "blank", "null", "candidature:<code>" or "other:<category>", and carries
    # no value anywhere else in the statement. Never a zero.
    unread: dict[str, str] = field(default_factory=dict)
    # Figures the sheet does not have at all: item -> reason. Same shape and
    # same item names as ``unread``; an item is in at most one of the two,
    # and carries no value either way.
    not_on_sheet: dict[str, str] = field(default_factory=dict)
    # "station" for a polling station. "aggregate" for a row that carries votes
    # but is not a polling station, such as overseas votes counted centrally.
    unit: str = "station"
    # The act the figures come from: the count at the station ("count"), the
    # general canvass by an electoral board ("canvass"), a resolution of a
    # board or a court ("ruling") or a repeated vote ("rerun").
    stage: str = STAGE_COUNT
    # Identifier of the statement this one replaces, if it says so.
    supersedes: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name, reasons in (
            ("unread", UNREAD_REASONS),
            ("not_on_sheet", NOT_ON_SHEET_REASONS),
        ):
            for item, reason in getattr(self, field_name).items():
                if reason not in reasons:
                    raise FormatError(
                        f"counts.{field_name}[{item}] must be one of {list(reasons)}"
                    )
                if item.startswith(_ITEM_CANDIDATURE):
                    valued = item[len(_ITEM_CANDIDATURE) :] in self.candidatures
                elif item.startswith(_ITEM_OTHER):
                    valued = item[len(_ITEM_OTHER) :] in self.other
                elif item in ("blank", "null"):
                    valued = getattr(self, item) is not None
                else:
                    raise FormatError(
                        f"counts.{field_name}: {item!r} is not blank, null, "
                        "candidature:<code> or other:<category>"
                    )
                if valued:
                    raise FormatError(
                        f"{item} is listed in counts.{field_name} and cannot also carry a value"
                    )
        both = set(self.unread) & set(self.not_on_sheet)
        if both:
            raise FormatError(
                f"{sorted(both)[0]} cannot be both unread and not on the sheet"
            )
        for name in ("blank", "null"):
            if (
                getattr(self, name) is None
                and name not in self.unread
                and name not in self.not_on_sheet
            ):
                raise FormatError(f"counts.{name} must be a non-negative integer")

    @property
    def candidature_sum(self) -> int:
        """Sum of the candidature votes that were read."""
        return sum(self.candidatures.values())

    @property
    def ballots(self) -> int:
        """Ballots counted: candidature votes, blank, null and other categories.

        When figures are unread this is the sum of those that were read, and
        the true number is at least that.
        """
        return (
            self.candidature_sum
            + (self.blank or 0)
            + (self.null or 0)
            + sum(self.other.values())
        )

    @property
    def figures(self) -> tuple:
        """The figures of the statement, in a form that can be compared.

        Two statements with the same figures say the same thing. A
        candidature with zero votes and one that is not listed are the same
        thing; a figure that is unread is neither.
        """
        return (
            self.blank,
            self.null,
            tuple(sorted((code, votes) for code, votes in self.candidatures.items() if votes)),
            tuple(sorted((name, count) for name, count in self.other.items() if count)),
            tuple(sorted(self.unread.items())),
            tuple(sorted(self.not_on_sheet.items())),
        )

    def items(self) -> set[str]:
        """Every item this statement has a figure or an unread mark for."""
        return (
            {"blank", "null"}
            | {_ITEM_CANDIDATURE + code for code in self.candidatures}
            | {_ITEM_OTHER + name for name in self.other}
            | set(self.unread)
            | set(self.not_on_sheet)
        )

    def value(self, item: str) -> int | None:
        """The figure for ``item``, or None when the statement gives none:
        it could not be read, or the sheet does not have it."""
        if item in self.unread or item in self.not_on_sheet:
            return None
        if item.startswith(_ITEM_CANDIDATURE):
            return self.candidatures.get(item[len(_ITEM_CANDIDATURE) :], 0)
        if item.startswith(_ITEM_OTHER):
            return self.other.get(item[len(_ITEM_OTHER) :], 0)
        return getattr(self, item)

    def agrees_with(self, other: "Statement") -> bool:
        """True when no figure that both statements read differs.

        A figure one of them could not read contradicts nothing. Saying that
        the sheet does not have a figure does contradict a statement that
        gives one, or that says it is there and could not be read.
        """
        for item in self.items() | other.items():
            if (item in self.not_on_sheet) != (item in other.not_on_sheet):
                return False
            mine, theirs = self.value(item), other.value(item)
            if mine is not None and theirs is not None and mine != theirs:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        counts: dict[str, Any] = {"candidatures": dict(sorted(self.candidatures.items()))}
        if self.blank is not None:
            counts["blank"] = self.blank
        if self.null is not None:
            counts["null"] = self.null
        if self.unread:
            counts["unread"] = dict(sorted(self.unread.items()))
        if self.not_on_sheet:
            counts["not_on_sheet"] = dict(sorted(self.not_on_sheet.items()))
        if self.registered is not None:
            counts["registered"] = self.registered
        if self.candidature_total is not None:
            counts["candidature_total"] = self.candidature_total
        if self.other:
            counts["other"] = dict(sorted(self.other.items()))
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
        if self.stage != STAGE_COUNT:
            doc["stage"] = self.stage
        if self.supersedes is not None:
            doc["supersedes"] = self.supersedes
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
        other = counts.get("other") or {}
        if not isinstance(other, dict):
            raise FormatError("counts.other must be an object")
        unread = counts.get("unread") or {}
        if not isinstance(unread, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in unread.items()
        ):
            raise FormatError("counts.unread must map items to reasons")
        absent = counts.get("not_on_sheet") or {}
        if not isinstance(absent, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in absent.items()
        ):
            raise FormatError("counts.not_on_sheet must map items to reasons")
        unit = doc.get("unit", "station")
        if unit not in UNITS:
            raise FormatError(f"unit must be one of {sorted(UNITS)}")
        stage = doc.get("stage", STAGE_COUNT)
        if stage not in STAGES:
            raise FormatError(f"stage must be one of {list(STAGES)}")
        supersedes = doc.get("supersedes")
        if supersedes is not None and not _is_statement_id(supersedes):
            raise FormatError("supersedes must be a statement identifier (sha256:<64 hex>)")
        evidence = doc.get("evidence") or {}
        if not isinstance(evidence, dict) or not isinstance(evidence.get("kind", ""), str):
            raise FormatError("evidence must be an object, and evidence.kind a string")
        return cls(
            profile=doc["profile"],
            election=doc["election"],
            station=doc["station"],
            constituency=doc["constituency"],
            blank=_count(
                counts.get("blank"),
                "counts.blank",
                optional="blank" in unread or "blank" in absent,
            ),
            null=_count(
                counts.get("null"), "counts.null", optional="null" in unread or "null" in absent
            ),
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
            other={
                str(name): _count(count, f"counts.other[{name}]")
                for name, count in other.items()
            },
            unread=dict(unread),
            not_on_sheet=dict(absent),
            unit=unit,
            stage=stage,
            supersedes=supersedes,
            evidence=evidence,
            extra=doc.get("extra") or {},
        )

    def canonical(self) -> bytes:
        return canonical_json(self.to_dict())

    def statement_id(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical()).hexdigest()


def _is_statement_id(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value[len("sha256:") :]
    return len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)


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

    # None when the totals do not give that category at all.
    blank: int | None
    null: int | None
    candidatures: dict[str, int]
    stations: int | None = None
    candidature_total: int | None = None
    # Other categories of ballots; None when the authority does not give them.
    other: dict[str, int] | None = None
    # Items whose figure is a lower bound, not a total, with how many figures
    # behind it could not be read. In totals recomputed from statements:
    # item -> number of statements that could not read it, and
    # "candidature_total" -> number that could not read some candidature. In
    # official totals: item -> number of figures the source of the totals
    # could not read.
    unread: dict[str, int] = field(default_factory=dict)
    # Only in totals recomputed from statements: item -> number of statements
    # that say the sheet does not have that figure, and item -> number of
    # statements that give it a figure, or say it could not be read, although
    # others say the sheet does not have it.
    not_on_sheet: dict[str, int] = field(default_factory=dict)
    contradicted: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {"candidatures": dict(sorted(self.candidatures.items()))}
        if self.blank is not None:
            doc["blank"] = self.blank
        if self.null is not None:
            doc["null"] = self.null
        if self.stations is not None:
            doc["stations"] = self.stations
        if self.candidature_total is not None:
            doc["candidature_total"] = self.candidature_total
        if self.other is not None:
            doc["other"] = dict(sorted(self.other.items()))
        if self.unread:
            doc["unread"] = dict(sorted(self.unread.items()))
        return doc

    @classmethod
    def from_dict(cls, doc: dict[str, Any]) -> "AreaTotals":
        if not isinstance(doc, dict) or not isinstance(
            doc.get("candidatures"), dict
        ):
            raise FormatError("area totals need a candidatures object")
        return cls(
            blank=_count(doc.get("blank"), "blank", optional=True),
            null=_count(doc.get("null"), "null", optional=True),
            candidatures={
                str(code): _count(votes, f"candidatures[{code}]")
                for code, votes in doc["candidatures"].items()
            },
            stations=_count(doc.get("stations"), "stations", optional=True),
            candidature_total=_count(
                doc.get("candidature_total"), "candidature_total", optional=True
            ),
            other=None
            if doc.get("other") is None
            else {
                str(name): _count(count, f"other[{name}]")
                for name, count in doc["other"].items()
            },
            unread={
                str(item): _count(count, f"unread[{item}]")
                for item, count in (doc.get("unread") or {}).items()
                if count
            },
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
    # Candidature codes these totals report under another code: when the
    # authority adds up several candidatures at this level, the verifier has
    # to add them up the same way before comparing.
    merge: dict[str, str] = field(default_factory=dict)
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
        if self.merge:
            doc["merge"] = dict(sorted(self.merge.items()))
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
        merge = doc.get("merge") or {}
        if not isinstance(merge, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in merge.items()
        ):
            raise FormatError("merge must map candidature codes to candidature codes")
        return cls(
            profile=str(doc.get("profile", "")),
            election=str(doc.get("election", "")),
            areas={key: AreaTotals.from_dict(value) for key, value in areas.items()},
            level=str(doc.get("level", "constituency")),
            grouping=str(doc.get("grouping", GROUP_BY_CONSTITUENCY)),
            merge=dict(merge),
            source=doc.get("source") or {},
        )
