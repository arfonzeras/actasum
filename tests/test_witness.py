import pytest

pytest.importorskip("cryptography")

import synth  # noqa: E402
from tallylog import merkle  # noqa: E402
from tallylog.cli import main  # noqa: E402
from tallylog.log import Log, check_checkpoint  # noqa: E402
from tallylog.note import COSIGNATURE, LOG_SIGNATURE, Signer, SignatureError  # noqa: E402
from tallylog.profiles.es import infoelectoral  # noqa: E402
from tallylog.statement import FormatError  # noqa: E402
from tallylog.witness import Witness  # noqa: E402

ORIGIN = "tallylog/test"
NOW = lambda: 1_791_000_000  # noqa: E731


@pytest.fixture
def setup(tmp_path):
    (tmp_path / "data").mkdir()
    mesa, _ = synth.build(tmp_path / "data")
    statements = infoelectoral.read_statements(infoelectoral.load_dataset(str(mesa)))
    key = Signer.generate(ORIGIN, LOG_SIGNATURE)
    log = Log.create(str(tmp_path / "log"), ORIGIN)
    witness = Witness.create(str(tmp_path / "witness"), "witness.example/w1")
    witness.trust(key.verifier)
    return tmp_path, statements, key, log, witness


def grow(log, key, statements):
    log.append(statements)
    log.sign(key)


def test_first_checkpoint_then_growth_are_cosigned(setup):
    _, statements, key, log, witness = setup
    grow(log, key, statements[:2])
    status, body = witness.add_checkpoint(log.witness_request(0), NOW)
    assert status == 200 and body.startswith("— witness.example/w1 ")
    log.add_signatures(body)

    checkpoint, verified = check_checkpoint(
        log.signed_checkpoint(), key.verifier, [witness.signer.verifier], quorum=1
    )
    assert checkpoint.size == 2
    assert [(v.verifier.name, v.timestamp) for v in verified] == [
        (ORIGIN, None),
        ("witness.example/w1", 1_791_000_000),
    ]

    grow(log, key, statements[2:])
    assert log.signatures.count("\n") == 1  # the old cosignature was dropped
    status, body = witness.add_checkpoint(log.witness_request(2), NOW)
    assert status == 200
    assert witness.status()["logs"][ORIGIN]["size"] == 4
    # Reopening the log keeps the signed checkpoint.
    log.add_signatures(body)
    assert Log.open(log.path).signed_checkpoint() == log.signed_checkpoint()


def test_policy_fails_without_enough_witnesses(setup):
    _, statements, key, log, witness = setup
    grow(log, key, statements)
    with pytest.raises(SignatureError, match="requires 1"):
        check_checkpoint(log.signed_checkpoint(), key.verifier, [witness.signer.verifier], 1)
    other = Signer.generate(ORIGIN, LOG_SIGNATURE)
    with pytest.raises(SignatureError):
        check_checkpoint(log.signed_checkpoint(), other.verifier)


def test_rewritten_log_is_refused(setup):
    tmp_path, statements, key, log, witness = setup
    grow(log, key, statements[:2])
    assert witness.add_checkpoint(log.witness_request(0), NOW)[0] == 200

    # A different log with the same key and origin: entry 0 was altered.
    altered = type(statements[0])(**{**statements[0].__dict__, "null": 99})
    forged = Log.create(str(tmp_path / "forged"), ORIGIN)
    grow(forged, key, [altered, statements[1], statements[2]])
    status, body = witness.add_checkpoint(forged.witness_request(2), NOW)
    assert (status, body) == (422, "the consistency proof does not verify\n")
    assert witness.status()["logs"][ORIGIN]["size"] == 2  # nothing was recorded


def test_split_view_at_the_same_size_is_refused(setup):
    tmp_path, statements, key, log, witness = setup
    grow(log, key, statements[:2])
    assert witness.add_checkpoint(log.witness_request(0), NOW)[0] == 200
    other = Log.create(str(tmp_path / "other"), ORIGIN)
    grow(other, key, [statements[2], statements[3]])
    status, body = witness.add_checkpoint(other.witness_request(2), NOW)
    assert status == 422 and "different root" in body
    # The same checkpoint again is fine: it is what the witness already saw.
    assert witness.add_checkpoint(log.witness_request(2), NOW)[0] == 200


def test_status_codes_of_the_protocol(setup):
    tmp_path, statements, key, log, witness = setup
    grow(log, key, statements[:3])
    good = log.witness_request(0)

    assert witness.add_checkpoint("no blank line", NOW)[0] == 400
    assert witness.add_checkpoint(good.replace("old 0", "new 0"), NOW)[0] == 400
    assert witness.add_checkpoint(good.replace("old 0", "old 00"), NOW)[0] == 400
    assert witness.add_checkpoint(good.replace("old 0", "old 9"), NOW)[0] == 400  # old > size

    stranger = Log.create(str(tmp_path / "s"), "tallylog/unknown")
    grow(stranger, Signer.generate("tallylog/unknown", LOG_SIGNATURE), statements[:1])
    assert witness.add_checkpoint(stranger.witness_request(0), NOW)[0] == 404

    impostor = Log.create(str(tmp_path / "i"), ORIGIN)
    grow(impostor, Signer.generate(ORIGIN, LOG_SIGNATURE), statements[:1])
    assert witness.add_checkpoint(impostor.witness_request(0), NOW)[0] == 403

    body, lines = good.rsplit("\n\n", 1)
    damaged = body.replace("\n3\n", "\n4\n") + "\n\n" + lines  # signature no longer matches
    assert witness.add_checkpoint(damaged, NOW)[0] == 403

    proof_line = merkle.leaf_hash(b"x")
    import base64
    extra = good.replace("old 0\n", "old 0\n" + base64.b64encode(proof_line).decode() + "\n")
    assert witness.add_checkpoint(extra, NOW)[0] == 422  # proof must be empty from size 0

    assert witness.add_checkpoint(good, NOW)[0] == 200
    assert witness.add_checkpoint(good, NOW) == (409, "3\n")  # old size is now 3


def test_witness_key_is_private_and_setup_is_guarded(setup):
    tmp_path, _, key, _, witness = setup
    import os, stat
    mode = stat.S_IMODE(os.stat(tmp_path / "witness" / "key").st_mode)
    assert mode == 0o600
    with pytest.raises(FormatError, match="already exists"):
        Witness.create(str(tmp_path / "witness"), "witness.example/w1")
    with pytest.raises(FormatError):
        witness.trust(Signer.generate("x.example/w", COSIGNATURE).verifier)
    with pytest.raises(FormatError, match="not a witness"):
        Witness(str(tmp_path / "nowhere"))


def test_unsigned_log_cannot_ask_for_a_cosignature(setup):
    _, statements, key, log, _ = setup
    log.append(statements)
    with pytest.raises(FormatError, match="sign the checkpoint"):
        log.witness_request(0)
    with pytest.raises(FormatError, match="origin"):
        log.sign(Signer.generate("tallylog/other", LOG_SIGNATURE))


def test_cli_full_ceremony(tmp_path, capsys):
    mesa, _ = synth.build(tmp_path)
    p = lambda name: str(tmp_path / name)  # noqa: E731
    assert main(["es", "convert", "--mesa", str(mesa), "--out", p("s.jsonl")]) == 0
    assert main(["log", "build", "--statements", p("s.jsonl"), "--out", p("log"),
                 "--origin", "tallylog/demo"]) == 0
    capsys.readouterr()
    assert main(["key", "new", "--name", "tallylog/demo", "--out", p("log.key")]) == 0
    log_vkey = capsys.readouterr().out.strip()
    assert main(["key", "new", "--name", "tallylog/demo", "--out", p("log.key")]) == 2
    assert main(["log", "sign", "--log", p("log"), "--key", p("log.key")]) == 0
    assert main(["witness", "init", "--dir", p("w"), "--name", "witness.example/w1"]) == 0
    witness_vkey = capsys.readouterr().out.strip().splitlines()[-1]
    assert main(["witness", "trust", "--dir", p("w"), "--log-key", log_vkey]) == 0
    assert main(["log", "witness-request", "--log", p("log"), "--old-size", "0",
                 "--out", p("req.txt")]) == 0
    assert main(["witness", "add-checkpoint", "--dir", p("w"), "--request", p("req.txt"),
                 "--out", p("cosig.txt")]) == 0
    assert main(["log", "cosign", "--log", p("log"), "--signatures", p("cosig.txt")]) == 0
    capsys.readouterr()
    args = ["log", "check-checkpoint", "--checkpoint", p("log/checkpoint"),
            "--log-key", log_vkey, "--witness-key", witness_vkey]
    assert main(args + ["--quorum", "1"]) == 0
    out = capsys.readouterr().out
    assert "OK: tallylog/demo at size 4" in out and "witness.example/w1" in out
    assert main(args + ["--quorum", "2"]) == 1
    # The same request again: the witness is now at size 4, not 0.
    assert main(["witness", "add-checkpoint", "--dir", p("w"), "--request", p("req.txt")]) == 1
    assert "409" in capsys.readouterr().err
    assert main(["witness", "status", "--dir", p("w")]) == 0
    assert "tallylog/demo: last cosigned size 4" in capsys.readouterr().out
    # An inclusion proof still checks against the signed checkpoint file.
    assert main(["log", "prove", "--log", p("log"), "--station", "es/28/079/05/123/A",
                 "--out", p("proof.json")]) == 0
    assert main(["log", "check-proof", "--proof", p("proof.json"),
                 "--checkpoint", p("log/checkpoint")]) == 0


def test_key_roles_cannot_be_swapped_in_the_policy(setup):
    _, statements, key, log, witness = setup
    grow(log, key, statements)
    log.add_signatures(witness.add_checkpoint(log.witness_request(0), NOW)[1])
    signed = log.signed_checkpoint()
    with pytest.raises(FormatError, match="cosignature keys"):
        check_checkpoint(signed, key.verifier, [key.verifier], quorum=1)
    with pytest.raises(FormatError, match="log-signature key"):
        check_checkpoint(signed, witness.signer.verifier)


def test_damaged_checkpoint_file_is_refused_on_open(setup):
    _, statements, key, log, _ = setup
    grow(log, key, statements)
    path = log.path + "/checkpoint"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("not a signature line\n")
    with pytest.raises(FormatError):
        Log.open(log.path)
