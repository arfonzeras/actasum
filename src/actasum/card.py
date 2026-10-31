"""The verifiability card: how much it would take for the figures to give
another result, how much was voted away from the polling station, and what
the authority publishes that lets anyone check it.

See docs/spec/verifiability.md for the normative description. The card adds
nothing to statements or official totals and changes no identifier.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .statement import FormatError, OfficialTotals, Statement, area_of
from .verify import compare, resolve

CARD_SPEC = "actasum/verifiability/v0.1"
CONTEXT_SPEC = "actasum/card-context/v0.1"
KINDS = ("single_winner", "first_round", "seats", "partial")
ASSUMPTIONS = ("rewrite", "move", "add_to_census")
_PUBLISHED_AT = ("station", "province", "state", "country", "not_published_separately")


def ratio(numerator: int, denominator: int) -> dict[str, Any] | None:
    """A ratio without floating point: both integers and a percentage string
    rounded half up to four decimals."""
    if denominator <= 0:
        return None
    scaled = Fraction(numerator * 100 * 10_000, denominator) + Fraction(1, 2)
    hundredths = scaled.numerator // scaled.denominator
    return {
        "numerator": numerator,
        "denominator": denominator,
        "percent": f"{hundredths // 10_000}.{hundredths % 10_000:04d}",
    }


# ---------------------------------------------------------------- units


@dataclass(frozen=True)
class Unit:
    """One statement of the standing sum, with merge and count_as applied."""

    station: str
    constituency: str
    aggregate: bool
    votes: dict[str, int]
    blank: int
    ballots: int
    registered: int | None
    unread: int  # figures that could not be read
    # The items those figures belong to, after merge and count_as:
    # "candidature:<code>", "blank", "null" or "other:<category>".
    unread_items: tuple[str, ...] = ()

    @property
    def valid(self) -> int:
        return sum(self.votes.values()) + self.blank

    @property
    def census(self) -> int | None:
        """The census of the unit, never below the ballots it counted."""
        if self.registered is None:
            return None
        return max(self.registered, self.ballots)


def to_unit(statement: Statement, merge: dict[str, str], count_as: dict[str, str]) -> Unit:
    votes: dict[str, int] = {}
    blank = statement.blank or 0
    for code, count in statement.candidatures.items():
        if code in count_as:
            if count_as[code] == "blank":
                blank += count
            continue
        target = merge.get(code, code)
        votes[target] = votes.get(target, 0) + count
    unread_items = []
    for item in sorted(statement.unread):
        if item.startswith("candidature:"):
            code = item.removeprefix("candidature:")
            item = count_as[code] if code in count_as else "candidature:" + merge.get(code, code)
        unread_items.append(item)
    return Unit(
        station=statement.station,
        constituency=statement.constituency,
        aggregate=statement.unit != "station",
        votes=votes,
        blank=blank,
        ballots=statement.ballots,
        registered=statement.registered,
        unread=len(statement.unread),
        unread_items=tuple(unread_items),
    )


def _totals(units: list[Unit]) -> tuple[dict[str, int], int, int]:
    votes: dict[str, int] = {}
    blank = ballots = 0
    for unit in units:
        for code, count in unit.votes.items():
            votes[code] = votes.get(code, 0) + count
        blank += unit.blank
        ballots += unit.ballots
    return votes, blank, ballots


def _ranking(votes: dict[str, int]) -> list[str]:
    return sorted((code for code in votes if votes[code] > 0), key=lambda c: (-votes[c], c))


def units_needed(capacities: Iterable[int], threshold: int) -> int | None:
    """Least number of units, from the largest capacity down, whose
    capacities add up to ``threshold``; at least one. None if all of them
    together do not."""
    total = 0
    count = 0
    for capacity in sorted(capacities, reverse=True):
        if total >= threshold and count:
            break
        if capacity <= 0:
            break
        total += capacity
        count += 1
    if total >= threshold:
        return max(count, 1)
    return None


def _unread_status(units: list[Unit]) -> dict[str, Any] | None:
    unread = sum(1 for unit in units if unit.unread)
    if unread:
        return {
            "value": None,
            "status": "not_computed",
            "reason": f"{unread} statements have figures that could not be read",
        }
    return None


def _no_census(units: list[Unit]) -> int:
    return sum(1 for unit in units if unit.registered is None)


# ------------------------------------------------------- single winner


def _capacity_single(unit: Unit, winner: str, loser: str, assumption: str) -> int:
    if assumption == "move":
        return 2 * unit.votes.get(winner, 0)
    census = unit.census
    assert census is not None
    if assumption == "rewrite":
        return unit.votes.get(winner, 0) - unit.votes.get(loser, 0) + census
    return census - unit.ballots  # add_to_census


def bounded_single_winner(units: list[Unit]) -> dict[str, Any]:
    """The margin as an interval when some figures could not be read: each
    unread figure may be anything from 0 to the census of its station."""
    with_unread = [u for u in units if u.unread]
    no_census = sum(1 for u in with_unread if u.registered is None)
    if no_census:
        blocked = {
            "value": None,
            "status": "not_computed",
            "reason": f"{len(with_unread)} statements have figures that could not be read, "
            f"and {no_census} of them have no census to bound them",
        }
        return {"margin_votes": blocked, "margin_diluted": blocked, "margin_units": [blocked]}
    votes, _, ballots = _totals(units)
    ranking = _ranking(votes)
    if len(ranking) < 2:
        na = {"value": None, "status": "not_applicable", "reason": "fewer than two candidatures with votes"}
        return {"margin_votes": na, "margin_diluted": na, "margin_units": [na]}
    up_to: dict[str, int] = {}  # candidature -> most its unread figures can add
    ballots_up_to = 0
    cells = 0
    for unit in with_unread:
        for item in unit.unread_items:
            cells += 1
            ballots_up_to += unit.registered
            if item.startswith("candidature:"):
                code = item.removeprefix("candidature:")
                up_to[code] = up_to.get(code, 0) + unit.registered
    winner, second = ranking[0], ranking[1]
    low = votes[winner] - votes[second] - up_to.get(second, 0)
    high = votes[winner] + up_to.get(winner, 0) - votes[second]
    change = any(
        votes.get(code, 0) + up_to.get(code, 0) >= votes[winner] + 1
        for code in set(votes) | set(up_to)
        if code != winner
    )
    bounded = {
        "statements": len(with_unread),
        "figures": cells,
        "rule": "each figure that could not be read is taken from 0 to the census of its station",
    }
    out: dict[str, Any] = {
        "margin_votes": {
            "value": None,
            "interval": [low, high],
            "between": [winner, second],
            "bounded_by_unread_figures": bounded,
            "includes_change_of_winner": change,
            "status": "computed",
            "source": "statements",
        },
    }
    if change:
        out["margin_votes"]["note"] = "the interval includes a change of winner"
    if low >= 0:
        out["margin_diluted"] = {
            "value": None,
            "interval": [ratio(low, ballots + ballots_up_to), ratio(high, ballots)],
            "ballots_interval": [ballots, ballots + ballots_up_to],
            "status": "computed",
            "source": "statements",
        }
    else:
        out["margin_diluted"] = {"value": None, "status": "not_computed",
                                 "reason": "the margin interval reaches below zero"}  # fmt: skip
    out["margin_units"] = [
        {"assumption": a, "value": None, "status": "not_computed",
         "reason": "the margin is an interval, bounded by figures that could not be read"}
        for a in ASSUMPTIONS
    ]  # fmt: skip
    return out


def _margin_bounds(contest_out: dict[str, Any]) -> tuple[int, int] | None:
    margin = contest_out.get("margin_votes", {})
    if isinstance(margin.get("value"), int):
        return margin["value"], margin["value"]
    if isinstance(margin.get("interval"), list):
        return margin["interval"][0], margin["interval"][1]
    return None


def single_winner(units: list[Unit]) -> dict[str, Any]:
    votes, _, ballots = _totals(units)
    ranking = _ranking(votes)
    if any(u.unread for u in units):
        return bounded_single_winner(units)
    if len(ranking) < 2:
        reason = "fewer than two candidatures with votes"
        na = {"value": None, "status": "not_applicable", "reason": reason}
        return {"margin_votes": na, "margin_diluted": na, "margin_units": [na]}
    winner, second = ranking[0], ranking[1]
    margin = votes[winner] - votes[second]
    out: dict[str, Any] = {
        "margin_votes": {
            "value": margin,
            "between": [winner, second],
            "status": "computed",
            "source": "statements",
        },
        "margin_diluted": {
            "value": ratio(margin, ballots),
            "ballots": ballots,
            "status": "computed",
            "source": "statements",
        },
    }
    missing = _no_census(units)
    rows = []
    for assumption in ASSUMPTIONS:
        row: dict[str, Any] = {"assumption": assumption, "of": len(units)}
        if assumption != "move" and missing:
            row.update(
                value=None,
                status="not_computed",
                reason=f"{missing} units have no census",
            )
            rows.append(row)
            continue
        def least(pool: list[Unit], assumption=assumption) -> int | None:
            best: int | None = None
            for loser in ranking[1:] if assumption == "rewrite" else [second]:
                threshold = votes[winner] - votes[loser] + 1
                needed = units_needed(
                    (_capacity_single(u, winner, loser, assumption) for u in pool), threshold
                )
                if needed is not None:
                    best = needed if best is None else min(best, needed)
            return best

        best = least(units)
        row["margin_units_needed"] = margin + 1
        if best is not None:
            row.update(value=best, share=ratio(best, len(units)))
        else:
            row.update(value=None, reachable=False)
        if any(u.aggregate for u in units):
            row["without_aggregates"] = least([u for u in units if not u.aggregate])
        row.update(status="computed", source="statements")
        rows.append(row)
    out["margin_units"] = rows
    return out


def first_round(units: list[Unit]) -> dict[str, Any]:
    blocked = _unread_status(units)
    votes, _, ballots = _totals(units)
    ranking = _ranking(votes)
    pairs = []
    for first, second in ((0, 1), (1, 2)):
        if blocked:
            pairs.append(dict(blocked, places=[first + 1, second + 1]))
            continue
        if len(ranking) <= second:
            pairs.append(
                {
                    "places": [first + 1, second + 1],
                    "value": None,
                    "status": "not_applicable",
                    "reason": "not enough candidatures with votes",
                }
            )
            continue
        a, b = ranking[first], ranking[second]
        margin = votes[a] - votes[b]
        pairs.append(
            {
                "places": [first + 1, second + 1],
                "between": [a, b],
                "value": margin,
                "diluted": ratio(margin, ballots),
                "ballots": ballots,
                "status": "computed",
                "source": "statements",
            }
        )
    return {
        "descriptive_margins": pairs,
        "note": "descriptive only: what a first round decides depends on rules not read",
    }


# ---------------------------------------------------------------- seats


@dataclass(frozen=True)
class Allocation:
    seats: dict[str, int]
    by_lot: bool = False


def allocate(votes: dict[str, int], blank: int, seats: int, threshold_percent: int) -> Allocation:
    """Highest averages with divisors 1, 2, 3... among candidatures with at
    least ``threshold_percent`` of the valid votes (candidatures plus blank).
    Equal quotients go to the candidature with more votes; equal votes too is
    flagged as a tie the context's rule settles by lot (the code then decides
    here, only to be reproducible)."""
    if seats <= 0:
        return Allocation({})
    valid = sum(votes.values()) + blank
    eligible = sorted(
        code
        for code, count in votes.items()
        if count > 0 and count * 100 >= threshold_percent * valid
    )
    won = {code: 0 for code in eligible}

    def key(code: str) -> tuple:
        # Quotient votes/(won+1) compared exactly, then votes, then code.
        return (Fraction(votes[code], won[code] + 1), votes[code], _neg(code))

    last = None
    for _ in range(seats):
        if not eligible:
            break
        best = max(eligible, key=key)
        last = key(best)
        won[best] += 1
    by_lot = False
    if eligible and last is not None:
        following = max(eligible, key=key)
        nxt = key(following)
        by_lot = nxt[0] == last[0] and nxt[1] == last[1]
    return Allocation({code: n for code, n in won.items() if n}, by_lot)


def _neg(code: str) -> tuple:
    # Larger tuple for the smaller code, so that max() picks the smaller code
    # on a full tie, as a sort by code ascending would.
    return tuple(-ord(ch) for ch in code) + (0,)


def _changes(votes: dict[str, int], blank: int, seats: int, tau: int, base: dict) -> bool:
    return allocate(votes, blank, seats, tau).seats != base


def _least(check, high: int) -> int | None:
    """Least x in 1..high for which check(x) holds, given it is monotone."""
    if high < 1 or not check(high):
        return None
    low = 1
    while low < high:
        mid = (low + high) // 2
        if check(mid):
            high = mid
        else:
            low = mid + 1
    return low


def votes_to_change(
    votes: dict[str, int], blank: int, seats: int, tau: int, headroom: int | None
) -> tuple[int | None, int | None]:
    """Least votes moved between two candidatures, and least votes added to
    one, that give some candidature another number of seats."""
    base = allocate(votes, blank, seats, tau).seats
    codes = sorted(votes)
    moved: int | None = None
    for x in codes:
        for y in codes:
            if x == y or votes[x] <= 0:
                continue

            def check(n: int, x=x, y=y) -> bool:
                changed = dict(votes)
                changed[x] -= n
                changed[y] += n
                return _changes(changed, blank, seats, tau, base)

            found = _least(check, votes[x] if moved is None else min(votes[x], moved))
            if found is not None:
                moved = found if moved is None else min(moved, found)
    added: int | None = None
    if headroom is not None:
        for y in codes:

            def check_add(n: int, y=y) -> bool:
                changed = dict(votes)
                changed[y] += n
                return _changes(changed, blank, seats, tau, base)

            found = _least(check_add, headroom if added is None else min(headroom, added))
            if found is not None:
                added = found if added is None else min(added, found)
    return moved, added


def seat_units_needed(
    units: list[Unit], seats_won: dict[str, int], codes: list[str], tau: int, assumption: str,
    *, only: list[Unit] | None = None,
) -> int | None:
    """Lower bound on the units whose figures would have to differ for the
    allocation to change (docs/spec/verifiability.md, section 3.3). With
    ``only``, just those units may differ; the totals are still all of them."""
    votes, blank, _ = _totals(units)
    for code in codes:
        votes.setdefault(code, 0)
    valid = sum(votes.values()) + blank
    qualified = {c: votes[c] > 0 and 100 * votes[c] >= tau * valid for c in codes}
    s = {c: seats_won.get(c, 0) for c in codes}

    def need(capacity, gap: int) -> int | None:
        if gap <= 0:
            return 1
        return units_needed((capacity(u) for u in (units if only is None else only)), gap)

    def headroom(u: Unit) -> int:
        return max(0, (u.registered or 0) - u.ballots)

    best: int | None = None
    for x in codes:
        if s[x] < 1:
            continue
        exit_gap = 100 * votes[x] - tau * valid + 1
        if assumption == "rewrite":
            cap_exit = lambda u, x=x: 100 * u.votes.get(x, 0) + tau * (u.census - u.valid)
        elif assumption == "move":
            cap_exit = lambda u, x=x: 100 * u.votes.get(x, 0)
        else:
            cap_exit = lambda u: tau * headroom(u)
        candidates = [need(cap_exit, exit_gap)]
        for y in codes:
            if y == x:
                continue
            pair_gap = (s[y] + 1) * votes[x] - s[x] * votes[y]
            if assumption == "rewrite":
                cap_pair = lambda u, x=x, y=y: (
                    (s[y] + 1) * u.votes.get(x, 0) + s[x] * (u.census - u.votes.get(y, 0))
                )
            elif assumption == "move":
                cap_pair = lambda u, x=x, y=y: (s[x] + s[y] + 1) * u.votes.get(x, 0)
            else:
                cap_pair = lambda u, x=x: s[x] * headroom(u)
            pair = need(cap_pair, pair_gap)
            if qualified[y]:
                candidates.append(pair)
                continue
            entry_gap = tau * valid - 100 * votes[y]
            if assumption == "rewrite":
                cap_entry = lambda u, y=y: (
                    tau * u.valid - 100 * u.votes.get(y, 0) + (100 - tau) * u.census
                )
            elif assumption == "move":
                cap_entry = lambda u, x=x: 100 * u.votes.get(x, 0)
            else:
                cap_entry = lambda u: (100 - tau) * headroom(u)
            entry = need(cap_entry, entry_gap)
            candidates.append(None if entry is None or pair is None else max(entry, pair))
        for found in candidates:
            if found is not None:
                best = found if best is None else min(best, found)
    if not any(s[c] >= 1 for c in codes):
        # Nobody holds a seat: any change starts with a candidature reaching
        # the threshold.
        for y in codes:
            entry_gap = tau * valid - 100 * votes[y]
            if assumption == "rewrite":
                cap_entry = lambda u, y=y: (
                    tau * u.valid - 100 * u.votes.get(y, 0) + (100 - tau) * u.census
                )
            elif assumption == "move":
                cap_entry = lambda u, y=y: 100 * (u.valid - u.blank - u.votes.get(y, 0))
            else:
                cap_entry = lambda u: (100 - tau) * headroom(u)
            found = need(cap_entry, max(entry_gap, 1 if votes[y] == 0 else entry_gap))
            if found is not None:
                best = found if best is None else min(best, found)
    return best


_VOTE_BUCKETS = ((1, 9, "1-9"), (10, 99, "10-99"), (100, 999, "100-999"), (1000, None, "1000+"))
_UNIT_BUCKETS = ((1, 1, "1"), (2, 5, "2-5"), (6, None, "6+"))


def _bucket(value: int | None, buckets) -> str:
    if value is None:
        return "not_reachable"
    for low, high, name in buckets:
        if value >= low and (high is None or value <= high):
            return name
    return "not_reachable"


def seat_contest(units: list[Unit], contest: dict[str, Any]) -> tuple[dict[str, Any], list]:
    """The seats part of the card, and every constituency's row (which the
    card lists only when the context allows it)."""
    seats_by_area = contest.get("seats") or {}
    tau = int(contest.get("threshold_percent", 0))
    by_area: dict[str, list[Unit]] = {}
    for unit in units:
        by_area.setdefault(unit.constituency, []).append(unit)
    rows = []
    for area in sorted(by_area):
        members = by_area[area]
        row: dict[str, Any] = {"constituency": area, "units": len(members)}
        if (contest.get("names") or {}).get(area):
            row["name"] = contest["names"][area]
        if area not in seats_by_area:
            row.update(status="not_computed", reason="the context gives no seats for it")
            rows.append(row)
            continue
        to_fill = int(seats_by_area[area])
        blocked = _unread_status(members)
        if blocked:
            row.update(status="not_computed", reason=blocked["reason"])
            rows.append(row)
            continue
        votes, blank, ballots = _totals(members)
        allocation = allocate(votes, blank, to_fill, tau)
        if allocation.by_lot:
            row.update(status="not_computed",
                       reason="the last seat falls on a tie the rule settles by lot")  # fmt: skip
            rows.append(row)
            continue
        missing = _no_census(members)
        headroom = None if missing else sum(max(0, u.registered - u.ballots) for u in members)
        moved, added = votes_to_change(votes, blank, to_fill, tau, headroom)
        codes = sorted(votes)
        row.update(
            seats=to_fill,
            ballots=ballots,
            by_lot=allocation.by_lot,
            votes_moved=moved,
            votes_added=added if not missing else None,
            diluted=ratio(moved, ballots) if moved is not None else None,
            status="computed",
            source="statements",
        )
        units_rows = []
        for assumption in ASSUMPTIONS:
            if assumption != "move" and missing:
                units_rows.append(
                    {
                        "assumption": assumption,
                        "value": None,
                        "status": "not_computed",
                        "reason": f"{missing} units have no census",
                    }
                )
                continue
            needed = seat_units_needed(members, allocation.seats, codes, tau, assumption)
            entry: dict[str, Any] = {"assumption": assumption, "of": len(members)}
            if needed is None:
                entry.update(value=None, reachable=False)
            else:
                entry.update(value=needed, share=ratio(needed, len(members)))
            if any(u.aggregate for u in members):
                entry["without_aggregates"] = seat_units_needed(
                    members, allocation.seats, codes, tau, assumption,
                    only=[u for u in members if not u.aggregate],
                )  # fmt: skip
            entry["status"] = "computed"
            units_rows.append(entry)
        row["margin_units"] = units_rows
        rows.append(row)
    computed = [r for r in rows if r.get("status") == "computed"]
    distribution = {
        "constituencies": len(rows),
        "computed": len(computed),
        "votes_moved": _count_buckets((r["votes_moved"] for r in computed), _VOTE_BUCKETS),
        "units_rewrite": _count_buckets(
            (_rewrite_value(r) for r in computed), _UNIT_BUCKETS
        ),
    }
    if any(u.aggregate for u in units):
        distribution["units_rewrite_without_aggregates"] = _count_buckets(
            (_rewrite_value(r, "without_aggregates") for r in computed), _UNIT_BUCKETS
        )
    out: dict[str, Any] = {
        "rule": "highest averages 1, 2, 3...; threshold on candidatures plus blank; "
        "equal quotients to more votes",
        "threshold_percent": tau,
        "distribution": distribution,
    }
    if contest.get("detail") == "by_constituency":
        out["constituencies"] = rows
    if contest.get("source"):
        out["seats_source"] = contest["source"]
    return out, rows


def _rewrite_value(row: dict[str, Any], key: str = "value") -> int | None:
    for entry in row.get("margin_units", []):
        if entry["assumption"] == "rewrite":
            return entry.get(key)
    return None


def _count_buckets(values: Iterable[int | None], buckets) -> dict[str, int]:
    counts = {name: 0 for _, _, name in buckets}
    counts["not_reachable"] = 0
    for value in values:
        counts[_bucket(value, buckets)] += 1
    return counts


# --------------------------------------------------------- remote vote


def _matcher(match: dict[str, Any]):
    if match.get("unit") == "aggregate":
        return lambda unit: unit.aggregate
    pattern = match.get("station_pattern")
    if isinstance(pattern, str):
        compiled = re.compile(pattern)
        return lambda unit: bool(compiled.search(unit.station))
    raise FormatError("a channel's match needs station_pattern or unit: aggregate")


def remote_vote(
    units: list[Unit], channels: list[dict[str, Any]], kind: str, contest_out: dict[str, Any]
) -> list[dict[str, Any]]:
    total_ballots = sum(u.ballots for u in units)
    out = []
    for channel in channels:
        name = str(channel.get("name", ""))
        published_at = channel.get("published_at", "unverified")
        entry: dict[str, Any] = {
            "channel": name,
            "published_at": {"value": published_at, "source": channel.get("source", "context")},
            "custody_chain": channel.get("custody_chain") or {"value": None, "status": "unverified"},
        }
        if published_at == "not_published_separately":
            entry.update(status="not_published", source=channel.get("source", "context"))
            out.append(entry)
            continue
        if published_at not in _PUBLISHED_AT:
            raise FormatError(f"channel {name}: unknown published_at {published_at!r}")
        selected = [u for u in units if _matcher(channel.get("match") or {})(u)]
        ballots = sum(u.ballots for u in selected)
        entry.update(
            units=len(selected),
            ballots=ballots,
            weight=ratio(ballots, total_ballots),
            status="computed",
            source="statements",
        )
        if kind == "single_winner":
            bounds = _margin_bounds(contest_out)
            if bounds is None:
                entry["against_margin"] = {"value": None, "status": "not_computed", "reason": "no margin"}
            elif bounds[0] == bounds[1]:
                entry["against_margin"] = {"value": ballots >= bounds[0] + 1,
                                           "margin_votes": bounds[0], "status": "computed"}  # fmt: skip
            else:
                low, high = bounds
                value = True if ballots >= high + 1 else False if ballots < low + 1 else None
                entry["against_margin"] = {
                    "value": value,
                    "margin_votes_interval": [low, high],
                    "status": "computed",
                    **({} if value is not None else
                       {"note": "depends on the figures that could not be read"}),
                }  # fmt: skip
        elif kind == "seats" and "constituencies_all" not in contest_out:
            entry["against_margin"] = {"value": None, "status": "not_computed",
                                       "reason": "no seat margin was computed"}  # fmt: skip
        elif kind == "seats":
            needed = {
                r["constituency"]: r.get("votes_moved")
                for r in contest_out.get("constituencies_all", [])
            }
            per_area: dict[str, int] = {}
            for unit in selected:
                per_area[unit.constituency] = per_area.get(unit.constituency, 0) + unit.ballots
            reach = sum(
                1
                for area, count in per_area.items()
                if needed.get(area) is not None and count >= needed[area]
            )
            entry["against_margin"] = {
                "constituencies_with_channel": len(per_area),
                "constituencies_where_ballots_reach_votes_moved": reach,
                "status": "computed",
            }
        else:
            entry["against_margin"] = {
                "value": None,
                "status": "not_applicable",
                "reason": f"no margin is given for a {kind.replace('_', ' ')} contest",
            }
        if channel.get("by_area"):
            per: dict[str, list[int]] = {}
            missing = 0
            for unit in selected:
                bucket = per.setdefault(unit.constituency, [0, 0])
                bucket[0] += unit.ballots
                if unit.registered is None:
                    missing += 1
                else:
                    bucket[1] += unit.registered
            entry["by_area"] = [
                {
                    "area": area,
                    "ballots": counts[0],
                    "census": counts[1] if not missing else None,
                    "turnout": ratio(counts[0], counts[1]) if not missing else None,
                }
                for area, counts in sorted(per.items())
            ]
        out.append(entry)
    return out


# -------------------------------------------------------- verifiability


def _context_fact(context: dict[str, Any], key: str) -> dict[str, Any]:
    fact = context.get(key)
    if fact is None:
        return {"value": None, "status": "unverified"}
    return fact


def verifiability(
    statements: list[Statement], units: list[Unit], officials: list[OfficialTotals],
    context: dict[str, Any],
) -> dict[str, Any]:  # fmt: skip
    stations = sum(1 for u in units if not u.aggregate)
    published = []
    agreement = []
    for official in officials:
        official_stations = sum(
            area.stations for area in official.areas.values() if area.stations is not None
        )
        by_station = {s.station: s for s in statements}
        in_areas = sum(
            1
            for u in units
            if not u.aggregate
            and area_of(by_station[u.station], official.grouping) in official.areas
        )
        published.append(
            {
                "level": official.level,
                "stations_in_statements": in_areas,
                "stations_in_official_totals": official_stations or None,
                "share": ratio(in_areas, official_stations) if official_stations else None,
                "status": "computed" if official_stations else "not_computed",
                **({} if official_stations else {"reason": "the official totals give no stations"}),
                "source": "statements, official",
            }
        )
        comparison = compare(statements, official)
        report = comparison.standing
        agreement.append(
            {
                "level": official.level,
                "areas_compared": report.areas_checked,
                "areas_matching": report.areas_matching,
                "figures_differing": len(report.differences),
                "official_matches": comparison.official_matches,
                "status": "computed",
                "source": "verifier",
            }
        )
    return {
        "stations": stations,
        "units_with_result": published,
        "sheet_images": _context_fact(context, "images"),
        "file_hashes": _context_fact(context, "hashes"),
        "publications_agree": agreement,
        "practices": context.get("practices")
        or [{"n": n, "value": None, "status": "unverified"} for n in range(1, 8)],
    }


# ------------------------------------------------------- coverage bound


def coverage_bound(
    kind: str, contest_out: dict[str, Any], context: dict[str, Any], missing_official: int | None
) -> dict:
    coverage = context.get("coverage") or {}
    source = coverage.get("source", "context")
    missing = coverage.get("stations_without_statement")
    if missing is None and missing_official is not None:
        missing, source = missing_official, "statements, official"
    if kind in ("first_round", "partial"):
        return {"status": "not_applicable", "reason": f"not given for a {kind.replace('_', ' ')} contest"}
    if missing == 0:
        return {"value": "complete coverage", "stations_without_statement": 0,
                "status": "computed", "source": source}  # fmt: skip
    if kind == "seats":
        return {"status": "not_computed", "reason": "not defined for seats with stations missing"}
    registered = coverage.get("registered_without_statement")
    bounds = _margin_bounds(contest_out)
    if not isinstance(registered, int) or bounds is None:
        return {"status": "not_computed",
                "reason": "the context gives no census of the stations without a statement"
                if not isinstance(registered, int) else "no margin"}  # fmt: skip
    low, high = bounds
    if registered >= high + 1:
        reaches: bool | None = True
        text = "the registered voters of the stations without a statement reach the margin"
    elif registered < low + 1:
        reaches = False
        text = "the registered voters of the stations without a statement do not reach the margin"
    else:
        reaches = None
        text = "whether the registered voters of the stations without a statement reach the "
        text += "margin depends on the figures that could not be read"
    return {
        "stations_without_statement": missing,
        "registered_without_statement": registered,
        **({"margin_votes": low} if low == high else {"margin_votes_interval": [low, high]}),
        "reaches_margin": reaches,
        "value": text,
        "status": "computed",
        "source": source,
    }


# ------------------------------------------------------------------ card


def _missing(units: list[Unit], official: OfficialTotals) -> int | None:
    """Stations the first official totals give and the statements do not,
    when the totals give stations for every area."""
    if not official.areas or any(a.stations is None for a in official.areas.values()):
        return None
    missing = sum(a.stations for a in official.areas.values()) - sum(
        1 for u in units if not u.aggregate
    )
    return missing if missing >= 0 else None


def check_context(context: dict[str, Any]) -> None:
    if not isinstance(context, dict) or context.get("spec") != CONTEXT_SPEC:
        raise FormatError("not a card-context document")
    contest = context.get("contest")
    if not isinstance(contest, dict) or contest.get("kind") not in KINDS:
        raise FormatError(f"contest.kind must be one of {', '.join(KINDS)}")
    if contest["kind"] == "seats" and contest.get("status") != "pending":
        if not isinstance(contest.get("seats"), dict):
            raise FormatError("a seats contest needs seats per constituency")
        if not isinstance(contest.get("threshold_percent"), int):
            raise FormatError("a seats contest needs an integer threshold_percent")
    for channel in context.get("channels") or []:
        if not isinstance(channel, dict) or not channel.get("name"):
            raise FormatError("every channel needs a name")


def build_card(
    statements: list[Statement],
    officials: list[OfficialTotals],
    context: dict[str, Any],
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    check_context(context)
    if not officials:
        raise FormatError("at least one official-totals document is needed")
    election = officials[0].election
    if context.get("election") not in (None, election):
        raise FormatError(f"the context is for {context['election']}, the totals for {election}")
    for statement in statements:
        if statement.election != election:
            raise FormatError(f"statement for {statement.station} is of {statement.election}")
    first = officials[0]
    standing = resolve(statements).standing
    units = [to_unit(s, first.merge, first.count_as) for s in standing]
    contest = context["contest"]
    kind = contest["kind"]

    if kind == "single_winner":
        margin = single_winner(units)
        contest_out = {"kind": kind, "outcome_rule": contest.get("outcome_rule")
                       or {"status": "unverified"}, **margin}  # fmt: skip
    elif kind == "first_round":
        contest_out = {"kind": kind, **first_round(units)}
    elif kind == "seats" and contest.get("status") == "pending":
        contest_out = {"kind": kind, "status": "not_computed",
                       "reason": contest.get("reason", "the allocation rule is pending")}  # fmt: skip
    elif kind == "seats":
        result, seat_rows = seat_contest(units, contest)
        contest_out = {"kind": kind, **result}
    else:
        contest_out = {
            "kind": kind,
            "status": "not_applicable",
            "reason": contest.get(
                "reason", "the statements cover only part of what elects as a whole"
            ),
        }

    # Remote vote needs the per-constituency votes of a seats contest even
    # when the card does not list constituencies.
    remote_input = dict(contest_out)
    if kind == "seats" and contest.get("status") != "pending":
        remote_input["constituencies_all"] = seat_rows
    card: dict[str, Any] = {
        "spec": CARD_SPEC,
        "election": election,
        "profile": first.profile,
        "inputs": inputs or {},
        "sum": "standing",
        "units": {
            "stations": sum(1 for u in units if not u.aggregate),
            "aggregates": sum(1 for u in units if u.aggregate),
        },
        "contest": contest_out,
        "remote_vote": remote_vote(units, context.get("channels") or [], kind, remote_input),
        "verifiability": verifiability(statements, units, officials, context),
        "coverage_bound": coverage_bound(kind, contest_out, context, _missing(units, first)),
    }
    if context.get("proclamation") is not None:
        card["proclamation"] = context["proclamation"]
    _no_station_named(card, {u.station for u in units})
    return card


def _no_station_named(doc: Any, stations: set[str]) -> None:
    """A card never holds a station identifier (section 1)."""
    if isinstance(doc, str):
        if doc in stations:
            raise FormatError("a card must not name a polling station")
    elif isinstance(doc, dict):
        for key, value in doc.items():
            _no_station_named(key, stations)
            _no_station_named(value, stations)
    elif isinstance(doc, list):
        for value in doc:
            _no_station_named(value, stations)
