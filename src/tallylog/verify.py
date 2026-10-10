"""The verifier: recompute constituency totals and compare with the official ones.

The verifier reports *differences*. It does not say why a difference exists:
a transcription slip, a correction made lawfully during the official canvass
and fraud all look the same from here. See docs/spec/core.md, section 5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .statement import ConstituencyTotals, OfficialTotals, Statement


@dataclass(frozen=True)
class StationIssue:
    station: str
    code: str
    detail: str


@dataclass(frozen=True)
class Difference:
    constituency: str
    item: str  # "blank", "null", "candidature_total", "stations" or "candidature:<code>"
    recomputed: int
    official: int

    @property
    def delta(self) -> int:
        return self.recomputed - self.official


@dataclass
class Report:
    election: str
    stations: int = 0
    constituencies_checked: int = 0
    constituencies_matching: int = 0
    differences: list[Difference] = field(default_factory=list)
    station_issues: list[StationIssue] = field(default_factory=list)
    missing_official: list[str] = field(default_factory=list)  # in statements only
    missing_statements: list[str] = field(default_factory=list)  # in official only

    @property
    def ok(self) -> bool:
        """True when every constituency was covered on both sides and matched."""
        return not (
            self.differences or self.missing_official or self.missing_statements
        )

    def to_dict(self) -> dict:
        return {
            "election": self.election,
            "ok": self.ok,
            "stations": self.stations,
            "constituencies_checked": self.constituencies_checked,
            "constituencies_matching": self.constituencies_matching,
            "differences": [
                {
                    "constituency": d.constituency,
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
            "constituencies_without_official_totals": self.missing_official,
            "constituencies_without_statements": self.missing_statements,
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


def aggregate(statements: Iterable[Statement]) -> dict[str, ConstituencyTotals]:
    """Sum statements by constituency."""
    sums: dict[str, dict] = {}
    for statement in statements:
        bucket = sums.setdefault(
            statement.constituency,
            {"blank": 0, "null": 0, "stations": 0, "candidatures": {}},
        )
        bucket["blank"] += statement.blank
        bucket["null"] += statement.null
        bucket["stations"] += 1
        for code, votes in statement.candidatures.items():
            bucket["candidatures"][code] = bucket["candidatures"].get(code, 0) + votes
    return {
        key: ConstituencyTotals(
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
    report = Report(election=official.election, stations=len(statements))

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

    recomputed = aggregate(statements)
    report.missing_official = sorted(set(recomputed) - set(official.constituencies))
    report.missing_statements = sorted(set(official.constituencies) - set(recomputed))

    for key in sorted(set(recomputed) & set(official.constituencies)):
        mine, theirs = recomputed[key], official.constituencies[key]
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
        report.constituencies_checked += 1
        if not found:
            report.constituencies_matching += 1
        report.differences.extend(found)
    return report


def format_report(report: Report, *, limit: int = 20) -> str:
    """Human-readable summary, in deliberately neutral wording."""
    lines = [
        f"Election: {report.election}",
        f"Polling stations read: {report.stations}",
        f"Constituencies compared: {report.constituencies_checked} "
        f"({report.constituencies_matching} match the official totals)",
    ]
    if report.missing_statements:
        lines.append(
            "Constituencies with official totals but no statements: "
            + ", ".join(report.missing_statements)
        )
    if report.missing_official:
        lines.append(
            "Constituencies with statements but no official totals: "
            + ", ".join(report.missing_official)
        )
    if report.differences:
        lines.append(f"Unexplained differences: {len(report.differences)}")
        for d in report.differences[:limit]:
            lines.append(
                f"  {d.constituency} {d.item}: recomputed {d.recomputed}, "
                f"official {d.official} ({d.delta:+d})"
            )
        if len(report.differences) > limit:
            lines.append(f"  ... and {len(report.differences) - limit} more")
    if report.station_issues:
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
