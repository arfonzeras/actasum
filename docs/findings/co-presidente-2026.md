# Findings: Colombia, presidential election of 31 May 2026

Two departments have been run: Bogotá D.C., in full, and Córdoba, where the
record of changes is a scan that could not be read reliably. Córdoba is at
the end of this page.

| | Bogotá D.C. | Córdoba |
| --- | --- | --- |
| Stations in the per-station file | 17,157 | 4,176 |
| Published file is the one the commission generated | after undoing a 13-byte shift | yes, as published |
| Stations add up to the E-26 | yes, all 16 vote figures | yes, all 16 vote figures |
| Changes in the AGE agree with the file | 6,410 of 6,410 | not read (scan) |

## Bogotá D.C.

Run of 11 October 2026 on four documents of the general scrutiny commission of
Bogotá D.C., downloaded that day from the Registraduría's scrutiny site
(<https://escrutiniospresidente2026.registraduria.gov.co/published>):

- the per-station file `MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv`;
- the *Acta General de Escrutinio* (AGE), 1,184 pages, generated on 2 June
  2026;
- forms E-26 (result of the general scrutiny) and E-24 (results table), both
  scanned, generated the same day.

```sh
pdftotext -layout AGE.pdf AGE.txt
actasum co convert --mmv MMV.csv --election 2026-05 --age-text AGE.txt --out statements.jsonl
actasum verify --statements statements.jsonl \
    --official docs/findings/official/co-presidente-2026-05-bogota.official.json
```

Everything below compares the commission's publications **with each other**,
and in one case with one scanned tally sheet. A difference means two published
figures do not agree; it does not say which one is right, or why.

## Summary

| Check | Result |
| --- | --- |
| The per-station file is the one the commission generated | Yes, once a publishing defect is undone; the hash then equals the one in the AGE |
| The stations add up to the official result of Bogotá (E-26) | Yes, in all 16 vote figures |
| Number of stations | 17,157 in the file, 17,164 on the E-24 |
| Every change recorded in the AGE agrees with the file | 6,410 of 6,410 |

## The published file, and the file the commission generated

The AGE records the SHA-256 of the MMV file the commission generated:
`dfa5612022c2763666cd72d9553bbcfd5cfcab60076fc4a95889503a34a6ce25`.

The file as downloaded has 24,565,302 bytes and SHA-256
`6cec1c68ac67c73407fb1cfd30a337bab08b8b850e6d679c918d98f5e4ec000e`. It is not
the same file. It starts with 13 bytes that are not part of the table (a line
reading `=/;HttpOnly`), and it stops 13 bytes before the end, in the middle of
its last row.

Dropping the first line and completing the last row gives a file with exactly
the recorded hash. The reader does this without guessing: it completes the
option's name from an earlier row and tries each vote figure in turn, and
accepts the result only if its hash is the recorded one. Here the missing
figure is 1.

So the content of the commission's file is known byte for byte, and what the
site serves is that file shifted by 13 bytes. Why the site does that has not
been looked into. On the Congress scrutiny site the same links returned the
site's own page instead of a file on that day.

Without the hash in the AGE there would have been no way to tell that the
published file is not the original, nor to prove that the repair is right.

## The stations add up to the official result

141,301 rows, 17,157 stations. Station sums against the E-26:

| | From the stations | E-26 |
| --- | --- | --- |
| For candidatures | 4,019,154 | 4,019,154 |
| Blank | 70,220 | 70,220 |
| Null | 33,257 | 33,257 |
| Unmarked | 5,699 | 5,699 |

Each of the thirteen candidates matches too; the two who withdrew have zero
in both. The E-26 and E-24 are scans: their figures were typed by hand into
[`official/co-presidente-2026-05-bogota.official.json`](official/co-presidente-2026-05-bogota.official.json)
and checked against the amounts in words on the E-26 and against the municipal
total of the E-24.

One figure differs. The E-24 says 17,164 stations were to be scrutinised and
17,164 were; the file has rows for 17,157. The file only has rows for options
with votes, so a station where nobody voted would leave no trace in it. That
would explain the seven, but it has not been checked, and the verifier reports
it as a difference.

The E-24 also gives totals per zone. They have not been compared: the scan did
not survive character recognition well enough.

## One station against its tally sheet

The scan of the E-14 form (copy *delegados*) of zone 01, post 01, station 001
was read by eye. Its seven non-zero figures are the seven rows the MMV file has
for that station (`co/16/001/01/01/001`): 130, 49, 29, 9, 3 and 1 votes for
six candidates and 2 blank. One station, one reader, handwriting.

## A lawful change to three thousand stations

The tally sheet lists thirteen candidates; the file has eleven. The AGE says
why. Two candidates had withdrawn, the commission read out their withdrawals
on 2 June, and then moved their votes, station by station, to unmarked votes.

The AGE has 6,410 entries of the form "se modificó la votación", each with one
option, its previous vote and its new vote. All were parsed.

| Check | Result |
| --- | --- |
| The "new vote" of every change equals the figure in the MMV file at that point | 6,410 of 6,410 |
| Changes naming a station the file does not have | 0 |
| Stations with at least one change | 3,016 |

Net effect of the changes:

| Option | Change |
| --- | --- |
| Candidate `1005-013` | −2,350 |
| Candidate `1006-009` | −1,160 |
| Unmarked votes | +3,510 |

For each of the 3,016 stations the reader writes two statements, both of the
canvass: the figures before the commission's changes, obtained by undoing
them, and the figures of the file, which names the earlier one in
`supersedes`. The verifier then lists, station by station, what changed.

The earlier figures are those the general commission started from. They are
not necessarily the tally sheet: the commissions below may have changed
figures before, and their records have not been read.

## Why this matters for the format

A verifier with a single sum would have to choose between two wrong pictures:
3,510 votes that the stations counted for two candidates and that the result
does not show, or a result that silently differs from every one of 3,016 tally
sheets. Nobody miscounted. The change is recorded, dated and public, and both
sets of figures are true of their own act.

## Córdoba

Documents of the general scrutiny commission of Córdoba, downloaded on 11
October 2026 from the same site: the per-station file
`MMV_XXX_13_000_XXX_XX_XX_XXX_1007.csv` (4,305,124 bytes), its AGE (194 pages,
a scan with no text) and its E-26 (a PDF with text).

```sh
actasum co convert --mmv MMV.csv --election 2026-05 \
    --sha256 2799c27a52574d85753ee0d31475cebdafd7819f88f1d977fe3b718fc6d636c9 \
    --out statements.jsonl
actasum verify --statements statements.jsonl \
    --official docs/findings/official/co-presidente-2026-05-cordoba.official.json
```

- **The published file is the commission's file.** Its SHA-256 is
  `2799c27a52574d85753ee0d31475cebdafd7819f88f1d977fe3b718fc6d636c9`, the
  hash the AGE records for it. It has no stray first line and its last row is
  whole. The 13-byte shift seen in the Bogotá file is therefore not general.
  The hash in the AGE was read by character recognition from a scan and
  agreed with the computed one character for character.
- **The stations add up to the E-26.** 27,483 rows, 4,176 stations in 30
  municipalities: 698,100 votes for candidatures, 9,623 blank, 4,045 null and
  2,028 unmarked, and each of the thirteen candidates, are the figures of the
  E-26. The E-26 does not give the number of stations, and the E-24 was not
  read.
- **The changes could not be read.** The AGE is a scan. Character recognition
  without a Spanish model found several hundred entries but read only 90 of
  them completely, and 13 of those did not agree with the file, as misread
  digits would not. Nothing was built from them. The check that each change
  must agree with the file is what kept bad readings out.
- The file has no rows for the two candidates who withdrew, as in Bogotá, and
  the E-26 gives both zero votes.

## Personal data

The MMV file carries each candidate's identity number, and the AGE and the
E-14 carry names and identity numbers of officials and jurors. None of it is
in the statements or in this repository.
