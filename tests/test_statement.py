import io
import json

import pytest

from actasum.statement import (
    FormatError,
    Statement,
    canonical_json,
    read_jsonl,
    write_jsonl,
)


def make(**overrides):
    base = dict(
        profile="es/loreg/v0.1",
        election="es/congreso/2019-11",
        station="es/08/019/01/001/A",
        constituency="es/08",
        registered=500,
        blank=4,
        null=3,
        candidatures={"000002": 200, "000001": 120},
        candidature_total=320,
    )
    base.update(overrides)
    return Statement(**base)


def test_canonical_json_is_sorted_and_compact():
    assert canonical_json({"b": 1, "a": {"d": [1, 2], "c": "ñ"}}) == (
        '{"a":{"c":"ñ","d":[1,2]},"b":1}'.encode("utf-8")
    )


def test_canonical_json_rejects_floats():
    with pytest.raises(FormatError):
        canonical_json({"votes": 1.0})


def test_statement_id_ignores_key_order():
    a = make()
    b = make(candidatures={"000001": 120, "000002": 200})
    assert a.statement_id() == b.statement_id()
    assert a.statement_id().startswith("sha256:")
    assert len(a.statement_id()) == len("sha256:") + 64


def test_statement_id_changes_with_any_count():
    assert make().statement_id() != make(null=4).statement_id()


def test_round_trip_through_jsonl():
    statements = [make(), make(station="es/08/019/01/001/B", blank=0)]
    buffer = io.StringIO()
    assert write_jsonl(statements, buffer) == 2
    buffer.seek(0)
    assert list(read_jsonl(buffer)) == statements


def test_derived_counts():
    s = make()
    assert s.candidature_sum == 320
    assert s.ballots == 327


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(spec="other/v9"),
        lambda d: d.update(station=""),
        lambda d: d["counts"].update(blank=-1),
        lambda d: d["counts"].update(null="3"),
        lambda d: d["counts"].update(blank=True),
        lambda d: d["counts"].update(candidatures=[1, 2]),
        lambda d: d["counts"]["candidatures"].update({"000001": 1.5}),
    ],
)
def test_invalid_statements_are_rejected(mutate):
    doc = json.loads(make().canonical())
    mutate(doc)
    with pytest.raises(FormatError):
        Statement.from_dict(doc)


def test_read_jsonl_reports_the_line_number():
    with pytest.raises(FormatError, match="line 2"):
        list(read_jsonl(io.StringIO(make().canonical().decode() + "\n{not json}\n")))


def test_sheet_total_that_disagrees_with_rows_is_flagged():
    from actasum.verify import check_station

    issues = check_station(make(candidature_total=321))
    assert [i.code for i in issues] == ["candidature-sum"]
    assert check_station(make()) == []


def test_unit_defaults_to_station_and_is_omitted():
    assert b'"unit"' not in make().canonical()
    aggregate = make(unit="aggregate")
    assert Statement.from_dict(json.loads(aggregate.canonical())) == aggregate
    doc = json.loads(make().canonical())
    doc["unit"] = "province"
    with pytest.raises(FormatError):
        Statement.from_dict(doc)
