"""The verifiability card (docs/spec/verifiability.md)."""

import itertools
import random

import pytest

from actasum import card
from actasum.profiles.es import seats as es_seats
from actasum.statement import AreaTotals, FormatError, OfficialTotals, Statement

ELECTION = "xx/test/2026"


def st(station, votes, *, blank=0, null=0, registered=None, constituency="xx", unit="station",
       unread=None):  # fmt: skip
    candidatures = dict(votes)
    unread_map = {}
    for code in unread or ():
        candidatures.pop(code, None)
        unread_map["candidature:" + code] = "illegible"
    return Statement(
        profile="xx/test/v0", election=ELECTION, station=station, constituency=constituency,
        blank=blank, null=null, candidatures=candidatures, registered=registered,
        unit=unit, unread=unread_map,
    )  # fmt: skip


def official(statements, *, merge=None, count_as=None, grouping="constituency"):
    areas = {}
    for s in statements:
        area = areas.setdefault(s.constituency, {"c": {}, "b": 0, "n": 0, "st": 0})
        for code, v in s.candidatures.items():
            area["c"][code] = area["c"].get(code, 0) + v
        area["b"] += s.blank
        area["n"] += s.null
        area["st"] += s.unit == "station"
    return OfficialTotals(
        profile="xx/test/v0", election=ELECTION,
        areas={k: AreaTotals(blank=a["b"], null=a["n"], candidatures=a["c"], stations=a["st"])
               for k, a in areas.items()},
        grouping=grouping, merge=merge or {}, count_as=count_as or {},
    )  # fmt: skip


def context(kind="single_winner", **extra):
    return {"spec": card.CONTEXT_SPEC, "election": ELECTION, "contest": {"kind": kind}, **extra}


def test_ratio_has_no_float_and_rounds_half_up():
    assert card.ratio(1, 3) == {"numerator": 1, "denominator": 3, "percent": "33.3333"}
    assert card.ratio(2, 3)["percent"] == "66.6667"
    assert card.ratio(1, 8)["percent"] == "12.5000"
    assert card.ratio(1, 0) is None


def three_stations():
    # W has 60+40+10 = 110, L has 30+20+5 = 55: M = 55.
    return [
        st("xx/1", {"W": 60, "L": 30}, null=10, registered=120),
        st("xx/2", {"W": 40, "L": 20}, blank=5, registered=100),
        st("xx/3", {"W": 10, "L": 5}, registered=40),
    ]


def test_margin_diluted_margin_and_units():
    statements = three_stations()
    result = card.build_card(statements, [official(statements)], context())
    contest = result["contest"]
    assert contest["margin_votes"]["value"] == 55
    assert contest["margin_votes"]["between"] == ["W", "L"]
    assert contest["margin_diluted"]["value"] == card.ratio(55, 180)
    units = {row["assumption"]: row for row in contest["margin_units"]}
    # rewrite: 60-30+120 = 150 >= 56 -> one unit
    assert units["rewrite"]["value"] == 1
    # move: 2*60 = 120 >= 56 -> one unit
    assert units["move"]["value"] == 1
    # add to census: 120-100=20, 100-65=35, 40-15=25 -> 35+25 = 60 >= 56 -> two
    assert units["add_to_census"]["value"] == 2
    assert units["add_to_census"]["margin_units_needed"] == 56


def test_a_tie_does_not_count():
    statements = [st("xx/1", {"W": 3, "L": 1}, registered=4)]
    units = card.single_winner([card.to_unit(s, {}, {}) for s in statements])["margin_units"]
    move = next(row for row in units if row["assumption"] == "move")
    # M = 2: moving one vote gives a tie, which does not count; 2*3 = 6 >= 3
    assert move["value"] == 1 and move["margin_units_needed"] == 3
    add = next(row for row in units if row["assumption"] == "add_to_census")
    assert add["value"] is None and add["reachable"] is False


def test_unread_figures_block_the_margin():
    statements = [st("xx/1", {"W": 5}, registered=10, unread=["L"]), st("xx/2", {"W": 1, "L": 3})]
    contest = card.single_winner([card.to_unit(s, {}, {}) for s in statements])
    assert contest["margin_votes"]["status"] == "not_computed"
    assert "could not be read" in contest["margin_votes"]["reason"]


def test_without_census_only_move_is_computed():
    statements = [st("xx/1", {"W": 5, "L": 2}), st("xx/2", {"W": 4, "L": 1})]
    rows = card.single_winner([card.to_unit(s, {}, {}) for s in statements])["margin_units"]
    status = {row["assumption"]: row["status"] for row in rows}
    assert status == {"rewrite": "not_computed", "move": "computed", "add_to_census": "not_computed"}


def test_census_never_below_the_ballots():
    unit = card.to_unit(st("xx/1", {"W": 5, "L": 2}, null=1, registered=6), {}, {})
    assert unit.census == 8


def test_merge_and_count_as_follow_the_official_totals():
    statements = [st("xx/1", {"A1": 3, "A2": 4, "B": 6, "Z": 2}, registered=20)]
    totals = official(statements)
    totals = OfficialTotals(
        profile=totals.profile, election=ELECTION,
        areas={"xx": AreaTotals(blank=0, null=2, candidatures={"A1": 7, "B": 6}, stations=1)},
        merge={"A2": "A1"}, count_as={"Z": "null"},
    )  # fmt: skip
    result = card.build_card(statements, [totals], context())
    assert result["contest"]["margin_votes"]["between"] == ["A1", "B"]
    assert result["contest"]["margin_votes"]["value"] == 1
    assert result["verifiability"]["publications_agree"][0]["areas_matching"] == 1


def test_first_round_gives_descriptive_margins_only():
    statements = [st("xx/1", {"A": 50, "B": 30, "C": 25}, registered=120)]
    result = card.build_card(statements, [official(statements)], context("first_round"))
    pairs = result["contest"]["descriptive_margins"]
    assert [p["value"] for p in pairs] == [20, 5]
    assert "margin_units" not in result["contest"]
    assert result["coverage_bound"]["status"] == "not_applicable"


def test_partial_coverage_gives_no_margin():
    statements = [st("xx/1", {"A": 5, "B": 3})]
    result = card.build_card(statements, [official(statements)], context("partial"))
    assert result["contest"]["status"] == "not_applicable"
    assert result["verifiability"]["units_with_result"][0]["share"]["percent"] == "100.0000"


def test_remote_channel_against_the_margin_and_by_area():
    statements = three_stations() + [
        st("xx/abroad/1", {"W": 10, "L": 50}, registered=900, unit="aggregate"),
    ]
    ctx = context(channels=[
        {"name": "abroad", "match": {"unit": "aggregate"}, "published_at": "country",
         "by_area": True},
        {"name": "postal", "published_at": "not_published_separately", "source": "layout"},
    ])  # fmt: skip
    result = card.build_card(statements, [official(statements)], ctx)
    abroad, postal = result["remote_vote"]
    assert abroad["ballots"] == 60 and abroad["units"] == 1
    # M = 110+10 - (55+50) = 15; 60 ballots >= 16
    assert abroad["against_margin"]["value"] is True
    assert abroad["by_area"][0]["census"] == 900
    assert postal["status"] == "not_published"
    assert result["units"] == {"stations": 3, "aggregates": 1}


def test_coverage_bound():
    statements = three_stations()
    ctx = context(coverage={"stations_without_statement": 2, "registered_without_statement": 55,
                            "source": "report"})  # fmt: skip
    bound = card.build_card(statements, [official(statements)], ctx)["coverage_bound"]
    assert bound["reaches_margin"] is False  # 55 < 56
    ctx["coverage"]["registered_without_statement"] = 56
    bound = card.build_card(statements, [official(statements)], ctx)["coverage_bound"]
    assert bound["reaches_margin"] is True
    ctx["coverage"] = {"stations_without_statement": 0}
    bound = card.build_card(statements, [official(statements)], ctx)["coverage_bound"]
    assert bound["value"] == "complete coverage"


def test_the_card_never_names_a_station():
    statements = three_stations()
    ctx = context(images={"value": "xx/2", "status": "unverified"})
    with pytest.raises(FormatError, match="must not name a polling station"):
        card.build_card(statements, [official(statements)], ctx)


def test_context_is_checked():
    statements = three_stations()
    with pytest.raises(FormatError, match="card-context"):
        card.build_card(statements, [official(statements)], {"contest": {"kind": "x"}})
    with pytest.raises(FormatError, match="contest.kind"):
        card.build_card(statements, [official(statements)], context("nope"))
    with pytest.raises(FormatError, match="seats per constituency"):
        card.build_card(statements, [official(statements)], context("seats"))


# ---------------------------------------------------------------- seats


def test_allocation_is_the_spanish_profile_allocation():
    rng = random.Random(7)
    for _ in range(400):
        parties = [f"{n:06d}" for n in rng.sample(range(1, 40), rng.randint(1, 7))]
        votes = {p: rng.choice([0, rng.randint(1, 60), rng.randint(1, 600)]) for p in parties}
        if rng.random() < 0.3:  # force ties
            votes[parties[0]] = votes[parties[-1]]
        blank = rng.randint(0, 50)
        seats = rng.randint(1, 9)
        threshold = rng.choice([0, 3, 5])
        mine = card.allocate(votes, blank, seats, threshold)
        theirs = es_seats.allocate(votes, blank, seats, threshold)
        assert mine.seats == theirs.seats and mine.by_lot == theirs.by_lot, (votes, blank, seats)


def brute_votes_moved(votes, blank, seats, tau):
    base = card.allocate(votes, blank, seats, tau).seats
    best = None
    for x, y in itertools.permutations(votes, 2):
        for n in range(1, votes[x] + 1):
            changed = dict(votes)
            changed[x] -= n
            changed[y] += n
            if card.allocate(changed, blank, seats, tau).seats != base:
                best = n if best is None else min(best, n)
                break
    return best


def test_votes_to_change_the_allocation_are_exact():
    rng = random.Random(11)
    for _ in range(60):
        votes = {c: rng.randint(0, 40) for c in "ABCD"}
        blank = rng.randint(0, 10)
        seats = rng.randint(1, 4)
        tau = rng.choice([0, 3, 5, 20])
        moved, _ = card.votes_to_change(votes, blank, seats, tau, None)
        assert moved == brute_votes_moved(votes, blank, seats, tau), (votes, blank, seats, tau)


def rewrites(unit, codes, census):
    """Every way to rewrite a unit's figures within its census (small)."""
    for split in itertools.product(range(census + 1), repeat=len(codes) + 1):
        if sum(split) <= census:
            yield dict(zip(codes, split[:-1])), split[-1]


def least_units_by_brute_force(units, codes, seats, tau, base):
    votes, blank, _ = card._totals(units)
    for k in range(1, len(units) + 1):
        for subset in itertools.combinations(range(len(units)), k):
            options = [list(rewrites(units[i], codes, units[i].census)) for i in subset]
            for combo in itertools.product(*options):
                total, new_blank = dict(votes), blank
                for i, (new_votes, nb) in zip(subset, combo):
                    for c in codes:
                        total[c] = total.get(c, 0) - units[i].votes.get(c, 0) + new_votes[c]
                    new_blank += nb - units[i].blank
                if card.allocate(total, new_blank, seats, tau).seats != base:
                    return k
    return None


def test_the_seat_lower_bound_is_never_above_the_real_least():
    rng = random.Random(9)
    codes = ["A", "B"]
    for _ in range(25):
        raw = []
        for i in range(3):
            v = {"A": rng.randint(0, 7), "B": rng.randint(0, 4)}
            blank = rng.randint(0, 1)
            raw.append(st(f"xx/{i}", v, blank=blank,
                          registered=sum(v.values()) + blank + rng.randint(0, 2)))  # fmt: skip
        units = [card.to_unit(s, {}, {}) for s in raw]
        seats, tau = rng.randint(1, 3), rng.choice([0, 20, 34])
        votes, blank, _ = card._totals(units)
        base = card.allocate(votes, blank, seats, tau).seats
        bound = card.seat_units_needed(units, base, codes, tau, "rewrite")
        least = least_units_by_brute_force(units, codes, seats, tau, base)
        if least is not None:
            assert bound is not None and bound <= least, (raw, seats, tau, bound, least)


def test_with_nobody_holding_a_seat_one_unit_may_be_enough():
    raw = [st("xx/0", {"A": 0, "B": 0}, blank=1, registered=2)]
    units = [card.to_unit(s, {}, {}) for s in raw]
    assert card.seat_units_needed(units, {}, ["A", "B"], 0, "rewrite") == 1


def test_a_seats_card():
    statements = [
        st("xx/a/1", {"A": 50, "B": 30, "C": 9}, blank=1, registered=100, constituency="xx/a"),
        st("xx/a/2", {"A": 40, "B": 35, "C": 2}, registered=90, constituency="xx/a"),
        st("xx/b/1", {"A": 10, "B": 70}, registered=100, constituency="xx/b"),
    ]
    ctx = context("seats")
    ctx["contest"] = {"kind": "seats", "seats": {"xx/a": 3, "xx/b": 2}, "threshold_percent": 3,
                      "detail": "by_constituency"}  # fmt: skip
    result = card.build_card(statements, [official(statements)], ctx)
    rows = {r["constituency"]: r for r in result["contest"]["constituencies"]}
    assert rows["xx/a"]["seats"] == 3 and rows["xx/a"]["votes_moved"] >= 1
    assert result["contest"]["distribution"]["computed"] == 2
    ctx["contest"]["detail"] = "distribution_only"
    hidden = card.build_card(statements, [official(statements)], ctx)
    assert "constituencies" not in hidden["contest"]
    assert hidden["contest"]["distribution"] == result["contest"]["distribution"]

