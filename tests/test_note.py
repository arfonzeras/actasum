import pytest

pytest.importorskip("cryptography")

from tallylog import note  # noqa: E402
from tallylog.note import COSIGNATURE, LOG_SIGNATURE, Signer, SignatureError, Verifier  # noqa: E402
from tallylog.statement import FormatError  # noqa: E402

# The example of c2sp.org/signed-note, section "Verifier keys".
SPEC_VKEY = "example.com/foo+530d903a+AekyeRrm56hApGFkyQR4ZCbV54Id2LKaANYcrnKv3U2k"
SPEC_NOTE = (
    "This is an example message.\n"
    "\n"
    "— example.com/foo Uw2QOkn8srV1yJGh2VYRlL1Tnagv1YEq6TfXppzi2ONncAlTgK7Ztg1ERYNZXsYjOBH3mFXmRKuwHjG1Yu72IneyaQM=\n"
)


def test_the_example_of_the_specification_verifies():
    verifier = Verifier.parse(SPEC_VKEY)
    assert (verifier.name, verifier.kind) == ("example.com/foo", LOG_SIGNATURE)
    assert verifier.vkey() == SPEC_VKEY
    parsed, verified = note.open_note(SPEC_NOTE, [verifier])
    assert parsed.text == "This is an example message.\n"
    assert [v.verifier for v in verified] == [verifier]
    assert parsed.render() == SPEC_NOTE


def test_a_changed_text_is_rejected():
    verifier = Verifier.parse(SPEC_VKEY)
    with pytest.raises(SignatureError, match="does not verify"):
        note.open_note(SPEC_NOTE.replace("example message", "example massage"), [verifier])


def test_unknown_keys_are_ignored_and_then_nothing_is_trusted():
    stranger = Signer.generate("example.com/foo", LOG_SIGNATURE).verifier  # same name, other key
    with pytest.raises(SignatureError, match="no signature from a trusted key"):
        note.open_note(SPEC_NOTE, [stranger])


def test_sign_and_verify_round_trip_with_both_types():
    text = "tallylog/test\n4\nRaTDqfj7aHzjaTdadU8GJq9omf6di07amxCw3DARqAc=\n"
    log_key = Signer.generate("tallylog/test", LOG_SIGNATURE)
    witness = Signer.generate("witness.example/w1", COSIGNATURE)
    data = text + "\n" + log_key.sign(text) + witness.sign(text, timestamp=1_791_000_000)
    parsed, verified = note.open_note(data, [log_key.verifier, witness.verifier])
    assert [(v.verifier.name, v.timestamp) for v in verified] == [
        ("tallylog/test", None),
        ("witness.example/w1", 1_791_000_000),
    ]
    # A cosignature covers its own timestamp.
    line = parsed.signatures[1]
    raw = bytearray(line.signature)
    raw[7] ^= 1
    forged = note.SignatureLine(line.name, line.id, bytes(raw), line.line)
    with pytest.raises(SignatureError):
        note.verify_signatures(text, [forged], [witness.verifier])


def test_key_files_round_trip_and_reject_damage():
    signer = Signer.generate("witness.example/w1", COSIGNATURE)
    again = Signer.parse(signer.encode())
    assert again == signer and again.verifier.vkey() == signer.verifier.vkey()
    assert Verifier.parse(signer.verifier.vkey()) == signer.verifier
    name, hex_id, key = signer.verifier.vkey().split("+", 2)
    with pytest.raises(FormatError):
        Verifier.parse(f"{name}+00000000+{key}")
    with pytest.raises(FormatError):
        Verifier.parse("no-plus-signs")
    with pytest.raises(FormatError):
        Signer.parse(signer.verifier.vkey())
    with pytest.raises(FormatError):
        Signer.generate("has space", LOG_SIGNATURE)
    with pytest.raises(FormatError):
        Signer.generate("has+plus", LOG_SIGNATURE)


@pytest.mark.parametrize(
    "data",
    [
        "no signatures at all\n",
        "text\n\n",
        "text\n\n- example.com/foo AAAAAAAA\n",
        "text\n\n— example.com/foo AAAA\n",
        "text\n\n— example.com/foo not base64!\n",
        "tab\there\n\n— example.com/foo AAAAAAAA\n",
        "text\n\n— example.com/foo AAAAAAAA",
    ],
)
def test_malformed_notes_are_rejected(data):
    with pytest.raises(FormatError):
        note.parse_note(data)


def test_duplicate_key_name_and_id_is_rejected():
    line = SPEC_NOTE.split("\n\n")[1]
    with pytest.raises(SignatureError, match="share a key name"):
        note.parse_note("This is an example message.\n\n" + line + line)


def test_non_canonical_base64_is_rejected():
    with pytest.raises(FormatError, match="canonical"):
        note.unb64("AAAAAB==", "value")


def test_keys_whose_base64_contains_a_plus_sign():
    # 0xfb 0xef 0xbe encodes to "++++", the separator character. Two leading
    # bytes line the pattern up after the one-byte signature type.
    signer = Signer("witness.example/w1", COSIGNATURE, bytes([0, 0] + [0xFB, 0xEF, 0xBE] * 10))
    assert "++++" in signer.encode().split("+", 4)[4]
    assert Signer.parse(signer.encode()) == signer
    for _ in range(200):
        fresh = Signer.generate("tallylog/test", LOG_SIGNATURE)
        assert Verifier.parse(fresh.verifier.vkey()) == fresh.verifier
        assert Signer.parse(fresh.encode()) == fresh
