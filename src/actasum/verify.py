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
    STAGE_COUNT,
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


@dataclass(frozen=True)
class Conflict:
    """Statements about the same act of the same station that do not agree."""

    station: str
    stage: str
    statements: int
    versions: int


@dataclass(frozen=True)
class Change:
    """A station whose standing figures are not those of its earliest act."""

    station: str
    stage: str  # the act the standing figures come from
    source: str  # evidence.kind of the standing statement, "" if not given
    # item -> (earlier, standing), for the items that differ
    items: dict[str, tuple[int, int]]
    # the act the earlier figures come from: "count" when the station's own
    # count is among the statements, otherwise the first act of the chain
    from_stage: str = STAGE_COUNT


@dataclass
class Resolution:
    """Which statement speaks for each station, as counted and as standing.

    Several statements may exist for one station. Those about the same act
    (same ``stage``) are captures of one thing and must agree, unless one of
    them says it replaces the other (``supersedes``): a board may correct its
    own figures. Statements of the same act that differ and do not refer to
    each other put that act in conflict, and it counts for nothing, the way
    contradictory copies of a tally sheet count for nothing. Statements about
    different acts may differ lawfully; a later act replaces an earlier one
    when it names it in ``supersedes``.
    """

    statements: int = 0  # distinct statements read
    counted: list[Statement] = field(default_factory=list)
    standing: list[Statement] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    # Stations with more than one act left standing because none of them
    # supersedes the others. They are left out of the standing sum.
    undetermined: list[str] = field(default_factory=list)
    # Stations with a later act but no statement of the count itself.
    without_count: list[str] = field(default_factory=list)
    # Stations of statements whose ``supersedes`` names a statement that was not provided.
    dangling: list[str] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)

    @property
    def plain(self) -> bool:
        """True when every station has one statement, of the count."""
        return not (
            self.conflicts
            or self.undetermined
            or self.without_count
            or self.dangling
            or self.changes
            or len(self.counted) != self.statements
        )


def resolve(statements: Iterable[Statement]) -> Resolution:
    """Decide which statements enter the two sums. See ``Resolution``."""
    by_id: dict[str, Statement] = {}
    for statement in statements:
        by_id.setdefault(statement.statement_id(), statement)
    result = Resolution(statements=len(by_id))

    # station -> stage -> figures -> [(identifier, statement)]
    acts: dict[str, dict[str, dict[tuple, list[tuple[str, Statement]]]]] = {}
    for identifier, statement in by_id.items():
        acts.setdefault(statement.station, {}).setdefault(statement.stage, {}).setdefault(
            statement.figures, []
        ).append((identifier, statement))
    # identifier -> stages of the statements that say they replace it
    replaced_by: dict[str, set[str]] = {}
    for statement in by_id.values():
        if statement.supersedes is not None:
            replaced_by.setdefault(statement.supersedes, set()).add(statement.stage)
    result.dangling = sorted(
        s.station for s in by_id.values() if s.supersedes and s.supersedes not in by_id
    )

    for station in sorted(acts):
        clean: dict[str, Statement] = {}  # stage -> the statement that speaks for it
        first: dict[str, Statement] = {}  # stage -> its earliest version
        left: list[str] = []  # stages no statement of another stage replaces
        for stage in sorted(acts[station]):
            versions = acts[station][stage]
            # A version stays unless a statement of the same act replaces it.
            live = [
                group
                for group in versions.values()
                if not any(stage in replaced_by.get(identifier, ()) for identifier, _ in group)
            ]
            if len(live) == 1:
                clean[stage] = min(live[0], key=lambda pair: pair[0])[1]
                roots = [
                    group
                    for group in versions.values()
                    if not any(s.supersedes in by_id and by_id[s.supersedes].stage == stage
                               for _, s in group)
                ]
                first[stage] = min(roots[0] if roots else live[0], key=lambda pair: pair[0])[1]
            else:
                result.conflicts.append(
                    Conflict(
                        station,
                        stage,
                        sum(len(group) for group in versions.values()),
                        max(len(live), 2),
                    )
                )
            if not any(
                other != stage
                for group in versions.values()
                for identifier, _ in group
                for other in replaced_by.get(identifier, ())
            ):
                left.append(stage)
        counted = clean.get(STAGE_COUNT)
        if counted is not None:
            result.counted.append(counted)
        if len(left) > 1:
            result.undetermined.append(station)
        elif len(left) == 1 and left[0] in clean:
            standing = clean[left[0]]
            result.standing.append(standing)
            if counted is None:
                result.without_count.append(station)
            earliest = counted if counted is not None else _earliest(first, by_id, standing)
            if earliest.figures != standing.figures:
                result.changes.append(_change(earliest, standing))
        # Otherwise the one act left is in conflict (already listed) and
        # nothing stands for this station.
    return result


def _earliest(
    first: dict[str, Statement], by_id: dict[str, Statement], standing: Statement
) -> Statement:
    """Follow ``supersedes`` back from the standing act to the first one known."""
    current, seen = standing, set()
    while True:
        current = first.get(current.stage, current)
        identifier = current.statement_id()
        if identifier in seen or current.supersedes not in by_id:
            return current
        seen.add(identifier)
        current = by_id[current.supersedes]


def _change(earlier: Statement, standing: Statement) -> Change:
    items: dict[str, tuple[int, int]] = {}
    if earlier.blank != standing.blank:
        items["blank"] = (earlier.blank, standing.blank)
    if earlier.null != standing.null:
        items["null"] = (earlier.null, standing.null)
    for name in sorted(set(earlier.other) | set(standing.other)):
        a, b = earlier.other.get(name, 0), standing.other.get(name, 0)
        if a != b:
            items[f"other:{name}"] = (a, b)
    for code in sorted(set(earlier.candidatures) | set(standing.candidatures)):
        a, b = earlier.candidatures.get(code, 0), standing.candidatures.get(code, 0)
        if a != b:
            items[f"candidature:{code}"] = (a, b)
    return Change(
        station=standing.station,
        stage=standing.stage,
        source=str(standing.evidence.get("kind", "")),
        items=items,
        from_stage=earlier.stage,
    )


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
    statements: Iterable[Statement],
    grouping: str = GROUP_BY_CONSTITUENCY,
    merge: dict[str, str] | None = None,
) -> dict[str, AreaTotals]:
    """Sum statements by area.

    ``merge`` maps a candidature code to the code its votes are added to.
    """
    merge = merge or {}
    sums: dict[str, dict] = {}
    for statement in statements:
        bucket = sums.setdefault(
            area_of(statement, grouping),
            {"blank": 0, "null": 0, "stations": 0, "candidatures": {}, "other": {}},
        )
        bucket["blank"] += statement.blank
        bucket["null"] += statement.null
        for name, count in statement.other.items():
            bucket["other"][name] = bucket["other"].get(name, 0) + count
        if statement.unit == "station":
            bucket["stations"] += 1
        for code, votes in statement.candidatures.items():
            code = merge.get(code, code)
            bucket["candidatures"][code] = bucket["candidatures"].get(code, 0) + votes
    return {
        key: AreaTotals(
            blank=value["blank"],
            null=value["null"],
            stations=value["stations"],
            candidatures=value["candidatures"],
            candidature_total=sum(value["candidatures"].values()),
            other=value["other"],
        )
        for key, value in sums.items()
    }


@dataclass
class Comparison:
    """The official totals against both sums."""

    resolution: Resolution
    counted: Report
    standing: Report

    @property
    def official_matches(self) -> str:
        """Which sum the official totals coincide with."""
        if self.counted.ok and self.standing.ok:
            return "both"
        if self.counted.ok:
            return "as counted"
        if self.standing.ok:
            return "as standing"
        return "neither"

    @property
    def ok(self) -> bool:
        """The official totals match one of the sums and no station is left
        in conflict or undetermined."""
        return self.official_matches != "neither" and not (
            self.resolution.conflicts or self.resolution.undetermined
        )

    def to_dict(self) -> dict:
        resolution = self.resolution
        doc = self.standing.to_dict()
        doc["ok"] = self.ok
        doc["official_matches"] = self.official_matches
        if not resolution.plain:
            doc["as_counted"] = self.counted.to_dict()
            doc["statements"] = resolution.statements
            doc["conflicts"] = [
                {
                    "station": c.station,
                    "stage": c.stage,
                    "statements": c.statements,
                    "versions": c.versions,
                }
                for c in resolution.conflicts
            ]
            doc["stations_undetermined"] = resolution.undetermined
            doc["stations_without_count"] = resolution.without_count
            doc["supersedes_unknown"] = resolution.dangling
            doc["stations_changed"] = [
                {
                    "station": c.station,
                    "stage": c.stage,
                    "from_stage": c.from_stage,
                    "source": c.source,
                    "items": {
                        item: {"earlier": a, "standing": b} for item, (a, b) in c.items.items()
                    },
                }
                for c in resolution.changes
            ]
        return doc


def compare(statements: Iterable[Statement], official: OfficialTotals) -> Comparison:
    """Compare ``official`` with what the stations counted and with what stands.

    Neither sum is preferred: the report says which one the official totals
    coincide with, without assuming what an official file contains.
    """
    statements = list(statements)
    for statement in statements:
        if statement.election != official.election:
            raise VerificationError(
                f"statement for {statement.station} belongs to election "
                f"{statement.election}, official totals are for {official.election}"
            )
    resolution = resolve(statements)
    return Comparison(
        resolution=resolution,
        counted=verify(resolution.counted, official),
        standing=verify(resolution.standing, official),
    )


def verify(statements: Iterable[Statement], official: OfficialTotals) -> Report:
    """Compare the totals recomputed from ``statements`` with ``official``.

    Expects one statement per station; ``compare`` is the entry point when a
    station may have several.
    """
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
                "use compare() to resolve several statements per station"
            )
        seen.add(statement.station)
        report.station_issues.extend(check_station(statement))

    if official.grouping != GROUP_BY_CONSTITUENCY:
        # An aggregate has no place of its own below the constituency. It is
        # kept when the official totals have an area for it (an overseas row
        # counts towards its province) and otherwise left out and counted (it
        # counts towards no municipality).
        kept = [
            s
            for s in statements
            if s.unit == "station" or area_of(s, official.grouping) in official.areas
        ]
        report.aggregates_left_out = len(statements) - len(kept)
        statements = kept

    recomputed = aggregate(statements, official.grouping, official.merge)
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
        if theirs.other is not None:
            for name in sorted(set(mine.other or {}) | set(theirs.other)):
                compare(f"other:{name}", (mine.other or {}).get(name, 0), theirs.other.get(name, 0))
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


def format_report(
    report: Report, *, limit: int = 20, station_issues: bool = True, verdict: bool = True
) -> str:
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
    if verdict:
        lines.append(
            "Result: recomputed totals match the official totals."
            if report.ok
            else "Result: there are differences or gaps to explain. "
            "A difference is not, by itself, evidence of wrongdoing."
        )
    return "\n".join(lines)


def format_comparison(comparison: Comparison, *, limit: int = 20) -> str:
    """Both sums side by side, in neutral wording.

    When every station has a single statement of its count, the two sums are
    the same sum and the report is the plain one.
    """
    resolution = comparison.resolution
    if resolution.plain:
        return format_report(comparison.standing, limit=limit)

    lines = [
        f"Statements read: {resolution.statements}",
        f"Stations with a statement of their count: {len(resolution.counted)}",
        f"Stations with figures left standing: {len(resolution.standing)}",
    ]

    def listing(title: str, names: list[str]) -> None:
        if names:
            shown = ", ".join(names[:limit])
            more = f" ... and {len(names) - limit} more" if len(names) > limit else ""
            lines.append(f"{title} ({len(names)}): {shown}{more}")

    if resolution.conflicts:
        lines.append(
            f"Acts with statements that do not agree, left out of both sums: "
            f"{len(resolution.conflicts)}"
        )
        for conflict in resolution.conflicts[:limit]:
            lines.append(
                f"  {conflict.station} [{conflict.stage}]: {conflict.statements} statements, "
                f"{conflict.versions} different sets of figures"
            )
    listing(
        "Stations with several acts and no link between them, left out of the standing sum",
        resolution.undetermined,
    )
    listing("Stations with a later act but no statement of the count", resolution.without_count)
    listing("Stations whose statement replaces one that was not provided", resolution.dangling)
    if resolution.changes:
        lines.append(
            "Stations whose standing figures differ from an earlier act: "
            f"{len(resolution.changes)}"
        )
        for change in resolution.changes[:limit]:
            source = f", source {change.source}" if change.source else ""
            lines.append(
                f"  {change.station} [{change.from_stage} -> {change.stage}{source}]"
            )
            word = "counted" if change.from_stage == STAGE_COUNT else "earlier"
            for item, (earlier, standing) in list(change.items.items())[:limit]:
                lines.append(
                    f"    {item}: {word} {earlier}, standing {standing} ({standing - earlier:+d})"
                )
        if len(resolution.changes) > limit:
            lines.append(f"  ... and {len(resolution.changes) - limit} more")

    for title, report, issues in (
        ("AS COUNTED AT THE STATIONS", comparison.counted, True),
        ("AS LEFT STANDING", comparison.standing, False),
    ):
        lines.append("")
        lines.append(f"--- {title} ---")
        lines.append(format_report(report, limit=limit, station_issues=issues, verdict=False))
    lines.append("")
    matches = comparison.official_matches
    if not resolution.counted and matches in ("as standing", "neither"):
        # Nothing to add up on the count side: say so instead of reporting a mismatch.
        lines.append(
            "Result: the official totals match what was left standing."
            if matches == "as standing"
            else "Result: the official totals do not match what was left standing. "
            "A difference is not, by itself, evidence of wrongdoing."
        )
        lines.append(
            "No statement of a station's own count was provided, so that sum could not be made."
        )
        if matches != "neither" and not comparison.ok:
            lines.append("Some stations are in conflict or undetermined; see above.")
        return "\n".join(lines)
    lines.append(
        {
            "both": "Result: the official totals match both sums.",
            "as counted": "Result: the official totals match what the stations counted, "
            "not what was left standing.",
            "as standing": "Result: the official totals match what was left standing, "
            "not what the stations counted.",
            "neither": "Result: the official totals match neither sum. "
            "A difference is not, by itself, evidence of wrongdoing.",
        }[matches]
    )
    if matches != "neither" and not comparison.ok:
        lines.append("Some stations are in conflict or undetermined; see above.")
    return "\n".join(lines)
