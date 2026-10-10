"""The verifier: recompute area totals and compare with the official ones.

The verifier reports *differences*. It does not say why a difference exists:
a transcription slip, a correction made lawfully during the official canvass
and fraud all look the same from here. See docs/spec/core.md, section 5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .statement import (
    GROUP_BY_CONSTITUENCY,
    AreaTotals,
    OfficialTotals,
    Statement,
    area_of,
)


@dataclass(frozen=True)
class StationIssue:
    station: str
    code: str
    detail: str


@dataclass(frozen=True)
class Difference:
    area: str
    item: str  # "blank", "null", "candidature_total", "stations" or "candidature:<code>"
    recomputed: int
    official: int

    @property
    def delta(self) -> int:
        return self.recomputed - self.official


@dataclass
class Report:
    election: str
    level: str = "constituency"
    stations: int = 0
    aggregates: int = 0
    # Aggregates left out because they do not belong to any area at this level.
    aggregates_left_out: int = 0
    areas_checked: int = 0
    areas_matching: int = 0
    differences: list[Difference] = field(default_factory=list)
    station_issues: list[StationIssue] = field(default_factory=list)
    missing_official: list[str] = field(default_factory=list)  # in statements only
    missing_statements: list[str] = field(default_factory=list)  # in official only

    @property
    def ok(self) -> bool:
        """True when every area was covered on both sides and matched."""
        return not (
            self.differences or self.missing_official or self.missing_statements
        )

    @property
    def areas_differing(self) -> list[str]:
        return sorted({d.area for d in self.differences})

    def to_dict(self) -> dict:
        return {
            "election": self.election,
            "level": self.level,
            "ok": self.ok,
            "stations": self.stations,
            "aggregates": self.aggregates,
            "aggregates_left_out": self.aggregates_left_out,
            "areas_checked": self.areas_checked,
            "areas_matching": self.areas_matching,
            "differences": [
                {
                    "area": d.area,
                    "item": d.item,
                    "recomputed": d.recomputed,
                    "official": d.official,
                    "delta": d.delta,
                }
                for d in self.differences
            ],
            "station_issues": [
                {"station": i.station, "code": i.code, "detail": i.detail}
                for i in self.station_issues
            ],
            "areas_without_official_totals": self.missing_official,
            "areas_without_statements": self.missing_statements,
        }


class VerificationError(ValueError):
    """The inputs cannot be compared at all (wrong election, duplicates...)."""


def check_station(statement: Statement) -> list[StationIssue]:
    """Internal consistency checks on a single tally sheet."""
    issues: list[StationIssue] = []
    total = statement.candidature_total
    if total is not None and total != statement.candidature_sum:
        issues.append(
            StationIssue(
                statement.station,
                "candidature-sum",
                f"candidature rows add up to {statement.candidature_sum}, "
                f"the sheet total says {total}",
            )
        )
    if statement.registered is not None and statement.ballots > statement.registered:
        issues.append(
            StationIssue(
                statement.station,
                "more-ballots-than-registered",
                f"{statement.ballots} ballots counted, {statement.registered} registered",
            )
        )
    return issues


def aggregate(
    statements: Iterable[Statement], grouping: str = GROUP_BY_CONSTITUENCY
) -> dict[str, AreaTotals]:
    """Sum statements by area."""
    sums: dict[str, dict] = {}
    for statement in statements:
        bucket = sums.setdefault(
            area_of(statement, grouping),
            {"blank": 0, "null": 0, "stations": 0, "candidatures": {}},
        )
        bucket["blank"] += statement.blank
        bucket["null"] += statement.null
        if statement.unit == "station":
            bucket["stations"] += 1
        for code, votes in statement.candidatures.items():
            bucket["candidatures"][code] = bucket["candidatures"].get(code, 0) + votes
    return {
        key: AreaTotals(
            blank=value["blank"],
            null=value["null"],
            stations=value["stations"],
            candidatures=value["candidatures"],
            candidature_total=sum(value["candidatures"].values()),
        )
        for key, value in sums.items()
    }


def verify(statements: Iterable[Statement], official: OfficialTotals) -> Report:
    """Compare the totals recomputed from ``statements`` with ``official``."""
    statements = list(statements)
    report = Report(
        election=official.election,
        level=official.level,
        stations=sum(1 for s in statements if s.unit == "station"),
        aggregates=sum(1 for s in statements if s.unit != "station"),
    )

    seen: set[str] = set()
    for statement in statements:
        if statement.election != official.election:
            raise VerificationError(
                f"statement for {statement.station} belongs to election "
                f"{statement.election}, official totals are for {official.election}"
            )
        if statement.station in seen:
            raise VerificationError(
                f"more than one statement for polling station {statement.station}; "
                "this version expects exactly one per station"
            )
        seen.add(statement.station)
        report.station_issues.extend(check_station(statement))

    if official.grouping != GROUP_BY_CONSTITUENCY:
        # An aggregate is assigned to a constituency only. Below that level it
        # belongs to no area, so it is left out and counted.
        report.aggregates_left_out = report.aggregates
        statements = [s for s in statements if s.unit == "station"]

    recomputed = aggregate(statements, official.grouping)
    report.missing_official = sorted(set(recomputed) - set(official.areas))
    report.missing_statements = sorted(set(official.areas) - set(recomputed))

    for key in sorted(set(recomputed) & set(official.areas)):
        mine, theirs = recomputed[key], official.areas[key]
        found: list[Difference] = []

        def compare(item: str, a: int | None, b: int | None) -> None:
            if a is not None and b is not None and a != b:
                found.append(Difference(key, item, a, b))

        compare("stations", mine.stations, theirs.stations)
        compare("blank", mine.blank, theirs.blank)
        compare("null", mine.null, theirs.null)
        compare("candidature_total", mine.candidature_total, theirs.candidature_total)
        for code in sorted(set(mine.candidatures) | set(theirs.candidatures)):
            compare(
                f"candidature:{code}",
                mine.candidatures.get(code, 0),
                theirs.candidatures.get(code, 0),
            )
        report.areas_checked += 1
        if not found:
            report.areas_matching += 1
        report.differences.extend(found)
    return report


def _plural(noun: str) -> str:
    return noun[:-1] + "ies" if noun.endswith("y") else noun + "s"


def format_report(report: Report, *, limit: int = 20, station_issues: bool = True) -> str:
    """Human-readable summary, in deliberately neutral wording."""
    areas = _plural(report.level)
    lines = [
        f"Election: {report.election}",
        f"Level: {report.level}",
        f"Polling stations read: {report.stations}",
    ]
    if report.aggregates:
        lines.append(
            f"Aggregate rows read (votes counted outside a polling station): {report.aggregates}"
        )
    if report.aggregates_left_out:
        lines.append(
            f"Aggregate rows left out at this level: {report.aggregates_left_out}"
        )
    lines.append(
        f"{areas.capitalize()} compared: {report.areas_checked} "
        f"({report.areas_matching} match the official totals)"
    )

    def listing(title: str, names: list[str]) -> None:
        if names:
            shown = ", ".join(names[:limit])
            more = f" ... and {len(names) - limit} more" if len(names) > limit else ""
            lines.append(f"{title} ({len(names)}): {shown}{more}")

    listing(f"{areas.capitalize()} with official totals but no statements", report.missing_statements)
    listing(f"{areas.capitalize()} with statements but no official totals", report.missing_official)
    if report.differences:
        lines.append(
            f"Unexplained differences: {len(report.differences)} "
            f"in {len(report.areas_differing)} {areas}"
        )
        for d in report.differences[:limit]:
            lines.append(
                f"  {d.area} {d.item}: recomputed {d.recomputed}, "
                f"official {d.official} ({d.delta:+d})"
            )
        if len(report.differences) > limit:
            lines.append(f"  ... and {len(report.differences) - limit} more")
    if station_issues and report.station_issues:
        lines.append(
            f"Polling stations with internal inconsistencies: {len(report.station_issues)}"
        )
        for issue in report.station_issues[:limit]:
            lines.append(f"  {issue.station} [{issue.code}]: {issue.detail}")
        if len(report.station_issues) > limit:
            lines.append(f"  ... and {len(report.station_issues) - limit} more")
    lines.append(
        "Result: recomputed totals match the official totals."
        if report.ok
        else "Result: there are differences or gaps to explain. "
        "A difference is not, by itself, evidence of wrongdoing."
    )
    return "\n".join(lines)
