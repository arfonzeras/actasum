# Findings: Colombia, presidential election of 31 May 2026, Bogotá D.C.

Run of 11 October 2026 on two documents of the general scrutiny commission of
Bogotá D.C., downloaded that day from the Registraduría's scrutiny site
(<https://escrutiniospresidente2026.registraduria.gov.co/published>):

- the per-station file `MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv`, 24,565,302
  bytes, SHA-256
  `6cec1c68ac67c73407fb1cfd30a337bab08b8b850e6d679c918d98f5e4ec000e`;
- the *Acta General de Escrutinio* (AGE) of the same commission, 1,184 pages,
  generated on 2 June 2026.

```sh
pdftotext -layout AGE.pdf AGE.txt
actasum co convert --mmv MMV.csv --election 2026-05 --age-text AGE.txt --out statements.jsonl
```

Everything below compares the commission's publications **with each other**,
and in one case with one scanned tally sheet. A difference means two published
figures do not agree; it does not say which one is right, or why.

## The published file is not the file the commission generated

The AGE records the SHA-256 of the MMV file the commission generated:
`dfa5612022c2763666cd72d9553bbcfd5cfcab60076fc4a95889503a34a6ce25`. The file
downloaded has a different hash. Two defects are visible in it:

- it starts with one line that is not part of the table (`=/;HttpOnly`);
- its last row stops before the vote column.

Removing the first line, and trying other line endings and encodings, did not
give the recorded hash. The file has 17,157 complete stations; the
Registraduría's site for the tally-sheet scans shows 17,164 stations for
Bogotá in this election. A file cut short on publication would explain all
three facts. That has not been confirmed.

Without the hash in the AGE there would have been no way to tell that the file
is not the original.

## What the file holds

141,300 rows, 17,157 stations, 11 candidatures plus blank, null and unmarked
votes. Added up:

| | Votes |
| --- | --- |
| For candidatures | 4,019,153 |
| Blank | 70,220 |
| Null | 33,257 |
| Unmarked | 5,699 |

These are sums of an incomplete file and have not been compared with any
official total: the E-26 form of the commission has not been read.

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
option, its previous vote and its new vote. 6,409 were parsed; one was not.

| Check | Result |
| --- | --- |
| The "new vote" of every parsed change equals the figure in the MMV file at that point | 6,409 of 6,409 |
| Changes naming a station the file does not have | 0 |
| Stations with at least one change | 3,016 |

Net effect of the parsed changes:

| Option | Change |
| --- | --- |
| Candidate `1005-013` | −2,350 |
| Candidate `1006-009` | −1,159 |
| Unmarked votes | +3,510 |

The three do not add up to zero by one vote, which is the size of the entry
that was not parsed.

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
