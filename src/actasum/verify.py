"""The verifier: recompute area totals and compare with the official ones.

The verifier reports *differences*. It does not say why a difference exists:
a transcription slip, a correction made lawfully during the official canvass
and fraud all look the same from here. See docs/spec/core.md, section 5.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
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
    # "" when both figures are totals. "recomputed" or "official" when that
    # side is a lower bound, because figures behind it could not be read:
    # the difference is then at least ``delta``, not ``delta``.
    bound: str = ""

    @property
    def delta(self) -> int:
        return self.recomputed - self.official

    @property
    def describe_delta(self) -> str:
        if not self.bound:
            return f"{self.delta:+d}"
        return f"at least {abs(self.delta)} {'above' if self.delta > 0 else 'below'}"


@dataclass(frozen=True)
class Bound:
    """A comparison nothing can be said about, because figures could not be read.

    One side is a lower bound that the other does not contradict, or both
    sides are lower bounds. Either way the two can be called neither matching
    nor differing. (A lower bound on one side only that already exceeds the
    other side is a ``Difference`` of at least that much.)
    """

    area: str
    item: str
    recomputed: int
    official: int
    # Statements in the area whose figure for this item is unread; when not
    # zero, ``recomputed`` is a lower bound.
    statements: int
    # Figures behind the official total that its source could not read; when
    # not zero, ``official`` is a lower bound too.
    official_unread: int = 0


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
    # item -> (earlier, standing), for the items both acts read and that differ
    items: dict[str, tuple[int, int]]
    # the act the earlier figures come from: "count" when the station's own
    # count is among the statements, otherwise the first act of the chain
    from_stage: str = STAGE_COUNT
    # Items one of the two acts could not read: nothing is said about them.
    not_compared: tuple[str, ...] = ()


@dataclass
class Resolution:
    """Which statement speaks for each station, as counted and as standing.

    Several statements may exist for one station. Those about the same act
    (same ``stage``) are captures of one thing and must agree, unless one of
    them says it replaces the other (``supersedes``): a board may correct its
    own figures. Statements of the same act that differ and do not refer to
    each other put that act in conflict, and it counts for nothing, the way
    contradictory copies of a tally sheet count for nothing. A figure one
    capture could not read contradicts nothing: captures that agree on every
    figure they both read are one act, with the figures any of them read.
    Statements about
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
    # Stations whose earliest and standing acts could be compared only in
    # part, because one of them has unread figures. They may or may not also
    # be among ``changes``.
    partly_compared: list[str] = field(default_factory=list)

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
            spoken = _combine(live)
            if spoken is not None:
                clean[stage] = spoken
                roots = [
                    group
                    for group in versions.values()
                    if not any(s.supersedes in by_id and by_id[s.supersedes].stage == stage
                               for _, s in group)
                ]
                first[stage] = (
                    _combine(roots) or min(roots[0], key=lambda pair: pair[0])[1]
                    if roots
                    else spoken
                )
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
                change = _change(earliest, standing)
                if change.items:
                    result.changes.append(change)
                if change.not_compared:
                    result.partly_compared.append(station)
        # Otherwise the one act left is in conflict (already listed) and
        # nothing stands for this station.
    return result


def _combine(groups: list[list[tuple[str, Statement]]]) -> Statement | None:
    """The statement that speaks for an act, given its versions.

    One version speaks for itself. Several speak together when no two of them
    differ in a figure both read: the result has the figures any of them
    read, on top of the one that read most. Otherwise there is none, and the
    act is in conflict.
    """
    if not groups:
        return None
    versions = [min(group, key=lambda pair: pair[0])[1] for group in groups]
    if len(versions) == 1:
        return versions[0]
    for index, one in enumerate(versions):
        if not all(one.agrees_with(other) for other in versions[index + 1 :]):
            return None
    base = min(versions, key=lambda s: (len(s.unread), s.statement_id()))
    blank, null = base.blank, base.null
    candidatures, other, unread = dict(base.candidatures), dict(base.other), dict(base.unread)
    for item in base.unread:
        value = next((s.value(item) for s in versions if s.value(item) is not None), None)
        if value is None:
            continue
        del unread[item]
        if item == "blank":
            blank = value
        elif item == "null":
            null = value
        elif item.startswith("candidature:"):
            candidatures[item.removeprefix("candidature:")] = value
        else:
            other[item.removeprefix("other:")] = value
    if len(unread) == len(base.unread):
        return base
    return replace(
        base, blank=blank, null=null, candidatures=candidatures, other=other, unread=unread
    )


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
    not_compared: list[str] = []
    names = earlier.items() | standing.items()
    # blank and null first, then other categories, then candidatures
    order = {"blank": 0, "null": 1}
    for item in sorted(names, key=lambda i: (order.get(i, 2 if i.startswith("other:") else 3), i)):
        a, b = earlier.value(item), standing.value(item)
        if a is None or b is None:
            not_compared.append(item)
        elif a != b:
            items[item] = (a, b)
    return Change(
        station=standing.station,
        stage=standing.stage,
        source=str(standing.evidence.get("kind", "")),
        items=items,
        from_stage=earlier.stage,
        not_compared=tuple(not_compared),
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
    # Sums that are a lower bound and do not exceed the official figure.
    bounds: list[Bound] = field(default_factory=list)
    station_issues: list[StationIssue] = field(default_factory=list)
    missing_official: list[str] = field(default_factory=list)  # in statements only
    missing_statements: list[str] = field(default_factory=list)  # in official only

    @property
    def ok(self) -> bool:
        """True when every area was covered on both sides and matched.

        An area with a sum that is only a lower bound has not matched.
        """
        return not (self.differences or self.bounds or self.gaps)

    @property
    def gaps(self) -> bool:
        return bool(self.missing_official or self.missing_statements)

    @property
    def undecided(self) -> bool:
        """True when nothing differs and nothing is missing, but some sums
        are lower bounds: the totals can be called neither matching nor
        differing."""
        return bool(self.bounds) and not (self.differences or self.gaps)

    @property
    def areas_differing(self) -> list[str]:
        return sorted({d.area for d in self.differences})

    @property
    def areas_undecided(self) -> list[str]:
        return sorted({b.area for b in self.bounds} - {d.area for d in self.differences})

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
                    # "recomputed" or "official": that side is a lower bound,
                    # and the difference is at least ``delta``.
                    **({"lower_bound": d.bound, "delta_is_a_minimum": True} if d.bound else {}),
                }
                for d in self.differences
            ],
            "lower_bounds": [
                {
                    "area": b.area,
                    "item": b.item,
                    "recomputed": b.recomputed,
                    "official": b.official,
                    "statements_with_the_figure_unread": b.statements,
                    "official_figures_unread": b.official_unread,
                }
                for b in self.bounds
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
    some_unread = any(item.startswith("candidature:") for item in statement.unread)
    # With a candidature figure unread, the rows that were read can only be
    # said to disagree with the total when they already exceed it.
    if total is not None and (
        statement.candidature_sum > total if some_unread else total != statement.candidature_sum
    ):
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
            {"blank": 0, "null": 0, "stations": 0, "candidatures": {}, "other": {}, "unread": {}},
        )
        bucket["blank"] += statement.blank or 0
        bucket["null"] += statement.null or 0
        for item in statement.unread:
            if item.startswith("candidature:"):
                code = item.removeprefix("candidature:")
                item = "candidature:" + merge.get(code, code)
            bucket["unread"][item] = bucket["unread"].get(item, 0) + 1
        if any(item.startswith("candidature:") for item in statement.unread):
            # Statements, not figures, behind the bound on the candidature total.
            bucket["unread"]["candidature_total"] = (
                bucket["unread"].get("candidature_total", 0) + 1
            )
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
            unread=value["unread"],
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
        if self.counted.undecided or self.standing.undecided:
            # At least one sum is only a lower bound and nothing contradicts it.
            return "undecided"
        return "neither"

    @property
    def ok(self) -> bool:
        """The official totals match one of the sums and no station is left
        in conflict or undetermined."""
        return self.official_matches not in ("neither", "undecided") and not (
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
            doc["stations_partly_compared"] = resolution.partly_compared
            doc["stations_changed"] = [
                {
                    "station": c.station,
                    "stage": c.stage,
                    "from_stage": c.from_stage,
                    "source": c.source,
                    "items": {
                        item: {"earlier": a, "standing": b} for item, (a, b) in c.items.items()
                    },
                    "not_compared": list(c.not_compared),
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

        open_sums: list[Bound] = []

        def compare(item: str, a: int | None, b: int | None) -> None:
            if a is None or b is None:
                return
            ours, theirs_unread = mine.unread.get(item, 0), theirs.unread.get(item, 0)
            if item == "candidature_total" and not theirs_unread:
                theirs_unread = sum(
                    n for name, n in theirs.unread.items() if name.startswith("candidature:")
                )
            if ours and theirs_unread:
                # Two lower bounds: nothing follows, whichever is larger.
                open_sums.append(Bound(key, item, a, b, ours, theirs_unread))
            elif ours:
                if a > b:
                    # The sum is at least a, so it exceeds b by at least a - b.
                    found.append(Difference(key, item, a, b, "recomputed"))
                else:
                    open_sums.append(Bound(key, item, a, b, ours))
            elif theirs_unread:
                if a < b:
                    found.append(Difference(key, item, a, b, "official"))
                else:
                    open_sums.append(Bound(key, item, a, b, 0, theirs_unread))
            elif a != b:
                found.append(Difference(key, item, a, b))

        compare("stations", mine.stations, theirs.stations)
        compare("blank", mine.blank, theirs.blank)
        compare("null", mine.null, theirs.null)
        compare("candidature_total", mine.candidature_total, theirs.candidature_total)
        if theirs.other is not None:
            for name in sorted(set(mine.other or {}) | set(theirs.other)):
                compare(
                    f"other:{name}", (mine.other or {}).get(name, 0), theirs.other.get(name, 0)
                )
        for code in sorted(set(mine.candidatures) | set(theirs.candidatures)):
            compare(
                f"candidature:{code}",
                mine.candidatures.get(code, 0),
                theirs.candidatures.get(code, 0),
            )
        report.areas_checked += 1
        if not found and not open_sums:
            report.areas_matching += 1
        report.differences.extend(found)
        report.bounds.extend(open_sums)
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
            ours = "at least " if d.bound == "recomputed" else ""
            theirs = "at least " if d.bound == "official" else ""
            lines.append(
                f"  {d.area} {d.item}: recomputed {ours}{d.recomputed}, "
                f"official {theirs}{d.official} ({d.describe_delta})"
            )
        if len(report.differences) > limit:
            lines.append(f"  ... and {len(report.differences) - limit} more")
    if report.bounds:
        lines.append(
            f"Sums that are only a lower bound, because figures could not be read: "
            f"{len(report.bounds)} in {len({b.area for b in report.bounds})} {areas}"
        )
        for b in report.bounds[:limit]:
            ours = "at least " if b.statements else ""
            theirs = "at least " if b.official_unread else ""
            why = [f"unread in {b.statements} statements"] if b.statements else []
            if b.official_unread:
                why.append(f"{b.official_unread} unread behind the official figure")
            lines.append(
                f"  {b.area} {b.item}: recomputed {ours}{b.recomputed}, "
                f"official {theirs}{b.official} ({', '.join(why)}): nothing is said"
            )
        if len(report.bounds) > limit:
            lines.append(f"  ... and {len(report.bounds) - limit} more")
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
            else "Result: some sums are lower bounds, because figures could not be read. "
            "They neither match nor differ from the official totals."
            if report.undecided
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
    listing(
        "Stations whose acts could be compared only in part, because figures could not be read",
        resolution.partly_compared,
    )
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
        if matches not in ("neither", "undecided") and not comparison.ok:
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
            "undecided": "Result: undecided. At least one sum is only a lower bound, because "
            "figures could not be read, and the official totals do not contradict it.",
        }[matches]
    )
    if matches not in ("neither", "undecided") and not comparison.ok:
        lines.append("Some stations are in conflict or undetermined; see above.")
    return "\n".join(lines)
