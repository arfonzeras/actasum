# Findings: Colombia, presidential election of 31 May 2026, Bogotá D.C.

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

## Personal data

The MMV file carries each candidate's identity number, and the AGE and the
E-14 carry names and identity numbers of officials and jurors. None of it is
in the statements or in this repository.
