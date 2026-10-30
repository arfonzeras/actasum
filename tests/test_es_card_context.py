"""The card context the Spanish profile drafts (docs/spec/profile-es.md, section 6)."""

import synth

from actasum import card
from actasum.profiles.es import infoelectoral


def test_spanish_context_reads_seats_and_names(tmp_path):
    def seats_row(province, code, votes, won):
        return synth._line(33, synth._head(province) + [
            (14, 14, "9"), (15, 20, code), (21, 28, votes), (29, 33, won),
        ])  # fmt: skip

    suffix = "021911.DAT"
    files = {
        "09" + suffix: [synth.station_row("28", "079", "05", "123 ", "A", 800, 9, 7, 560)],
        "07" + suffix: [synth.province_row("28", 1, 9, 7, 560), synth.province_row("99", 1, 1, 1, 1)],
        "08" + suffix: [seats_row("28", "000001", 300, 2), seats_row("28", "000002", 250, 1),
                        seats_row("99", "000001", 1, 350)],
    }  # fmt: skip
    for name, lines in files.items():
        (tmp_path / name).write_bytes(("\r\n".join(lines) + "\r\n").encode("iso-8859-1"))
    context = infoelectoral.card_context(infoelectoral.load_dataset(str(tmp_path)))
    assert context["election"] == "es/congreso/2019-11"
    assert context["contest"]["seats"] == {"es/28": 3}
    assert context["contest"]["names"] == {"es/28": "PROVINCIA 28"}
    assert context["contest"]["threshold_percent"] == 3
    assert [c["name"] for c in context["channels"]] == ["abroad (CERA)", "postal"]
    card.check_context(context)
