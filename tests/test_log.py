import json

import pytest

import synth
from tallylog.cli import main
from tallylog.log import (
    Checkpoint,
    Log,
    verify_consistency_proof,
    verify_inclusion_proof,
)
from tallylog.profiles.es import infoelectoral
from tallylog.statement import FormatError


@pytest.fixture
def statements(tmp_path):
    (tmp_path / "data").mkdir()
    mesa, _ = synth.build(tmp_path / "data")
    return infoelectoral.read_statements(infoelectoral.load_dataset(str(mesa)))


def test_checkpoint_text_round_trip():
    checkpoint = Checkpoint("tallylog/es/congreso/2019-11", 4, bytes(range(32)))
    text = checkpoint.text()
    assert text.count("\n") == 3 and text.endswith("\n")
    assert Checkpoint.parse(text) == checkpoint
    for bad in ("", "origin\n4\n", "origin\n04\n" + text.split("\n")[2] + "\n", "o\n1\nxx\n"):
        with pytest.raises(FormatError):
            Checkpoint.parse(bad)


def test_build_reopen_and_prove(tmp_path, statements):
    log = Log.create(str(tmp_path / "log"), "tallylog/test")
    assert log.append(statements) == (4, 0)
    assert log.append(statements) == (0, 4)  # the same statements again add nothing

    reopened = Log.open(str(tmp_path / "log"))
    assert reopened.checkpoint() == log.checkpoint()
    assert reopened.checkpoint().size == 4

    (index,) = reopened.find("es/28/079/05/123/A")
    proof = json.loads(json.dumps(reopened.prove_inclusion(index)))
    statement, checkpoint = verify_inclusion_proof(proof, reopened.checkpoint())
    assert statement == statements[index]
    assert checkpoint.size == 4


def test_a_changed_figure_breaks_the_proof(tmp_path, statements):
    log = Log.create(str(tmp_path / "log"), "tallylog/test")
    log.append(statements)
    proof = log.prove_inclusion(0)
    proof["statement"]["counts"]["null"] += 1
    with pytest.raises(FormatError, match="does not hold"):
        verify_inclusion_proof(proof)


def test_proof_for_another_checkpoint_is_refused(tmp_path, statements):
    log = Log.create(str(tmp_path / "log"), "tallylog/test")
    log.append(statements[:3])
    earlier = log.checkpoint()
    log.append(statements[3:])
    with pytest.raises(FormatError, match="different checkpoint"):
        verify_inclusion_proof(log.prove_inclusion(0), earlier)


def test_consistency_between_two_checkpoints(tmp_path, statements):
    log = Log.create(str(tmp_path / "log"), "tallylog/test")
    log.append(statements[:2])
    earlier = log.checkpoint()
    log.append(statements[2:])
    proof = json.loads(json.dumps(log.prove_consistency(earlier.size)))
    old, new = verify_consistency_proof(proof, earlier, log.checkpoint())
    assert (old.size, new.size) == (2, 4)


def test_rewritten_history_cannot_prove_consistency(tmp_path, statements):
    honest = Log.create(str(tmp_path / "honest"), "tallylog/test")
    honest.append(statements[:2])
    earlier = honest.checkpoint()

    altered = type(statements[0])(**{**statements[0].__dict__, "null": 99})
    forged = Log.create(str(tmp_path / "forged"), "tallylog/test")
    forged.append([altered, statements[1], statements[2], statements[3]])
    proof = forged.prove_consistency(2)
    with pytest.raises(FormatError):
        verify_consistency_proof(proof, earlier, forged.checkpoint())


def test_tampering_with_the_stored_log_is_detected_on_open(tmp_path, statements):
    path = tmp_path / "log"
    Log.create(str(path), "tallylog/test").append(statements)
    leaves = path / "leaves.jsonl"
    leaves.write_bytes(leaves.read_bytes().replace(b'"null":3', b'"null":4', 1))
    with pytest.raises(FormatError, match="do not match the checkpoint"):
        Log.open(str(path))
    # Dropping the last entry is caught too.
    Log.create(str(tmp_path / "log2"), "tallylog/test").append(statements)
    leaves2 = tmp_path / "log2" / "leaves.jsonl"
    leaves2.write_bytes(b"\n".join(leaves2.read_bytes().split(b"\n")[:-2]) + b"\n")
    with pytest.raises(FormatError, match="do not match the checkpoint"):
        Log.open(str(tmp_path / "log2"))


def test_cli_end_to_end(tmp_path, capsys):
    mesa, _ = synth.build(tmp_path)
    s, log, proof = tmp_path / "s.jsonl", tmp_path / "log", tmp_path / "proof.json"
    assert main(["es", "convert", "--mesa", str(mesa), "--out", str(s)]) == 0
    assert main(["log", "build", "--statements", str(s), "--out", str(log)]) == 0
    checkpoint_text = capsys.readouterr().out
    assert checkpoint_text.startswith("tallylog/es/congreso/2019-11\n4\n")
    (tmp_path / "cp").write_text(checkpoint_text, encoding="utf-8", newline="")

    assert main(["log", "prove", "--log", str(log), "--station", "es/08/101/02/010/U",
                 "--out", str(proof)]) == 0
    assert main(["log", "check-proof", "--proof", str(proof),
                 "--checkpoint", str(tmp_path / "cp")]) == 0
    assert "is entry 2 of the log" in capsys.readouterr().out

    assert main(["log", "prove", "--log", str(log), "--station", "es/00/none"]) == 2
    assert main(["log", "build", "--statements", str(s), "--out", str(log)]) == 2
    capsys.readouterr()

    cons = tmp_path / "cons.json"
    assert main(["log", "consistency", "--log", str(log), "--old-size", "3",
                 "--out", str(cons)]) == 0
    assert main(["log", "check-consistency", "--proof", str(cons)]) == 0
    assert "the 3 entries it had before" in capsys.readouterr().out
    assert main(["log", "checkpoint", "--log", str(log)]) == 0
    assert capsys.readouterr().out == checkpoint_text
