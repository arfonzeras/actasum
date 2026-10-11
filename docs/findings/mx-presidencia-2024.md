# Findings: Mexico, presidential election of 2 June 2024

Run of 11 October 2026 on two database files published by the Instituto
Nacional Electoral (INE), with `actasum` on branch `profile-mx`:

| File | Generated | Inside | SHA-256 of `PRES_2024.csv` |
| --- | --- | --- | --- |
| PREP database | 3 June 2024, 20:05 (UTC-6) | `20240603_2005_PREP.zip` › `20240603_2005_PREP_PRES.zip` | `c9d7282e9ba0dabdc6d0378eb3383010ad3f301a26d79c3035a9f2a2fd6d5c45` |
| Cómputos Distritales database | 8 June 2024, 20:30 (UTC-6) | `20240608_2030_COMPUTOS.zip` › `20240608_2030_COMPUTOS_PRES.zip` | `860c1a539ac98b5def4dff3e82e87a19be3ebba7cb435b680ae79799942d1628` |

The outer ZIP files, as received, have SHA-256
`dcccf23088f81a4ab7c7942a79504b04c4a9347b0a4744f6c328c59fd4d6c31d` (PREP) and
`f0b0f90483720374eaac50cfb356b43425697fabfa3f963d22a5b8f2d849312f` (Cómputos).
No hash published by the INE for either file was found, so these only say
which bytes were read.

```sh
actasum mx replay --prep PREP/PRES_2024.csv --computos COMPUTOS/PRES_2024.csv \
    --election 2024-06 --official docs/findings/official/mx-presidencia-2024-06.official.json
```

**Status: run, not verified.** Three publications of the same authority are
compared with each other: the two files and one press statement. No tally
sheet was looked at, and the result validated by the electoral court was not
read.

The PREP is the INE's capture of one copy of each tally sheet, which the INE
itself calls preliminary and not definitive. A difference between the PREP
and the canvass can be a capture error, a correction or the result of
counting the ballots again. These files do not say which, and nothing here
does either.

Words used below: a **tally sheet** is the form of one polling station; a
**cell** is one figure on it. A tally sheet has 17 cells with votes: 15 for
parties and combinations of parties, one for unregistered candidates and one
for null votes.

## Summary

| Check | Result |
| --- | --- |
| The PREP's rows add up to the totals it prints | Yes |
| The Cómputos rows add up to the totals it prints | Yes |
| The statements of the canvass add up to the INE's press statement | Yes, in the three candidatures, unregistered candidates and null votes |
| The core's standing sum equals that press statement | No: it also holds the count of 16 stations the canvass file has no figures for |
| Stations with a statement of both acts | 158,956 |
| Of them, with no figure changed among those both acts read | 56,681 |
| Of them, with at least one figure changed | 102,275 |
| Stations in conflict, or left undetermined by the core | 0 |

## Each file against its own header

| | PREP | Cómputos |
| --- | --- | --- |
| Rows | 171,410 | 170,766 |
| Tally sheets expected, as printed | 170,648 | 170,766 |
| Tally sheets counted, printed and recomputed | 159,004 | 170,766 |
| Votes, printed and recomputed | 56,107,873 | 60,115,184 |
| Registered voters, printed and recomputed | 92,092,843 | 98,468,994 |

This is each file against itself, not an independent check. The PREP's extra
762 rows are tally sheets it could not match to a station. Its total of votes
is reproduced only when the cells it could not capture are added up as zero,
which is what the file's own total does.

## Against a source other than the two files

The INE's press statement 368, of 9 June 2024, gives the result of the
district canvass per candidature. It was read through an automatic extract of
the page and typed into
[`official/mx-presidencia-2024-06.official.json`](official/mx-presidencia-2024-06.official.json).

| | INE press statement | Statements of the canvass |
| --- | --- | --- |
| `PVEM-PT-MORENA` | 35,924,519 | 35,924,519 |
| `PAN-PRI-PRD` | 16,502,697 | 16,502,697 |
| `MC` | 6,204,710 | 6,204,710 |
| Unregistered candidates | 83,114 | 83,114 |
| Null votes | 1,400,144 | 1,400,144 |

The statement also says 116,397 packages were recounted, 68.16 per cent; the
Cómputos file has 116,397 rows marked as a recount.

The press statement and the file come from the same authority within a day
of each other. Their agreement shows that the file read is the one the INE
summed, and that the reader and the coalition mapping add it up the same way.
It does not show that either reflects the tally sheets.

The verifier's own answer is that the official totals match **neither** sum:

- **As counted**, the sums are lower bounds for null votes and for the three
  candidatures, because of the unread cells. None exceeds the official
  figure, so nothing is said about them. Unregistered candidates do: the
  PREP statements add up to at least 84,997 against 83,114, at least 1,883
  above.
- **As standing**, every figure is above the official one, by 5,265 ballots
  in all: 203 null votes and 512 for `MC`, and at least 1,305, 3,235 and 10
  for the other three items, which are lower bounds. The standing sum holds
  the canvass and, in addition, the PREP count of the 16 stations listed
  below.

## Stations with a count and no figures in the canvass

16 stations have a statement of the count and none of the canvass. All 16
have a row in the Cómputos file. In each, every vote cell holds `-`,
`TOTAL_VOTOS_CALCULADOS` is `0`, and `OBSERVACIONES` holds the text in the
last column:

| Station | Ballots read in the PREP | Cells unread in the PREP | `OBSERVACIONES` in the Cómputos file |
| --- | --- | --- | --- |
| `mx/07/0119/B0100` | 104 | 0 | `Paquete no recibido` |
| `mx/07/0120/B0100` | 161 | 0 | `Paquete no recibido` |
| `mx/07/0894/E0100` | 340 | 0 | `Paquete no recibido` |
| `mx/08/1139/E0100` | 222 | 6 | `Paquete no recibido` |
| `mx/08/1139/E0101` | 249 | 0 | `Paquete no recibido` |
| `mx/13/0264/C0500` | 292 | 0 | `Paquete no recibido` |
| `mx/13/0265/B0100` | 394 | 0 | `Paquete no recibido` |
| `mx/13/0270/B0100` | 383 | 0 | `Paquete no recibido` |
| `mx/13/0273/C0300` | 355 | 0 | `Paquete no recibido` |
| `mx/13/0273/C0400` | 351 | 0 | `Paquete no recibido` |
| `mx/14/1466/B0100` | 322 | 7 | `Paquete no recibido (Para recuento-SRA)` |
| `mx/16/0245/B0100` | 340 | 0 | `Paquete no recibido` |
| `mx/20/0943/B0100` | 467 | 0 | `Paquete no recibido` |
| `mx/20/0943/C0100` | 475 | 0 | `Paquete no recibido` |
| `mx/21/0870/C0100` | 369 | 0 | `Paquete no recibido` |
| `mx/21/2764/B0100` | 441 | 3 | `Paquete no recibido` |

The reader gives no statement to a row without figures. With no statement of
a later act, the core leaves the count of these stations standing, and their
5,265 ballots enter the standing sum. The other 129 rows of the Cómputos
file without figures belong to stations that have no statement of the count
either.

## What gives no statement

PREP, of 171,410 rows:

| Rows | Why, as the file says |
| --- | --- |
| 8,131 | No tally sheet captured at the cut |
| 1,442 | `Sin acta`: the sheet did not reach the collection centre |
| 886 | All cells empty |
| 790 | All cells illegible |
| 762 | Could not be matched to a station |
| 395 | More votes than registered voters |
| 32 | Vote from abroad, one row per state |

That leaves 158,972 statements of the count.

Cómputos, of 170,766 rows: 145 have no figures and 170,621 give a statement.
The 145 are 122 packages not received (`Paquete no recibido`, in three
variants) and 23 stations not installed (`Casilla no instalada`).

## Cells the PREP could not read

Of the 158,972 tally sheets with a statement of the count, 20,160 have at
least one cell the PREP could not capture:

| Tally sheets | Cells marked |
| --- | --- |
| 18,057 | only `Sin dato` (empty) |
| 1,560 | only `Ilegible` (illegible) |
| 543 | both |

In those 20,160 tally sheets there are 100,308 such cells: 93,167 `Sin dato`
and 7,141 `Ilegible`. The PREP adds them up as zero. It does not count them
as null votes: null votes have their own cell, which is itself among the
unread ones in 2,093 tally sheets.

In the statements these cells are listed under `counts.unread` and carry no
value. Where the same station has a statement of the canvass, the canvass
can be asked what it has in them:

| PREP says | Cells compared | Zero in the canvass | Not zero | Votes in the canvass |
| --- | --- | --- | --- | --- |
| `Sin dato` | 93,151 | 66,485 (71 %) | 26,666 | 189,020 |
| `Ilegible` | 7,141 | 2,771 (39 %) | 4,370 | 124,980 |

The two marks are different facts: an empty cell is a zero in the canvass far
more often than an illegible one. Together the cells hold 314,000 votes in
the canvass.

Most of these cells are for combinations of two parties of a coalition and
for unregistered candidates, where a sheet often has nothing written.

## The two sums

| | Stations | Ballots |
| --- | --- | --- |
| As counted (PREP statements) | 158,972 | at least 55,923,497 |
| As standing | 170,637 | at least 60,120,449 |

Both are lower bounds. The count has unread cells in 20,160 statements; the
standing sum in 3, among the 16 stations listed above. The
two sums are over different sets of stations and cannot be subtracted from
each other.

## Station by station

158,956 stations have a statement of both acts. For each, the figures both
acts read are compared; a cell the PREP could not read is not a change, and
20,157 stations are compared only in part for that reason.

| How the canvass computed the sheet | Stations | No figure changed | At least one figure changed |
| --- | --- | --- | --- |
| Compared with the council's copy (*cotejo*) | 52,302 | 49,414 | 2,888 (5.5 %) |
| Ballots counted again (*recuento*) | 106,654 | 7,267 | 99,387 (93.2 %) |
| All | 158,956 | 56,681 | 102,275 (64.3 %) |

Most stations were recounted, and nearly every recount gives a figure that
is not the one the PREP captured. By the largest change in a single cell of
the tally sheet:

| Largest change in one cell | *Cotejo* | *Recuento* | All |
| --- | --- | --- | --- |
| 1 vote | 334 | 26,252 | 26,586 |
| 2 to 10 votes | 1,122 | 53,087 | 54,209 |
| 11 to 100 votes | 1,243 | 18,203 | 19,446 |
| More than 100 votes | 189 | 1,845 | 2,034 |
| All | 2,888 | 99,387 | 102,275 |

In 7,749 of the 102,275 stations the changes only move votes between cells
of one coalition: every candidature keeps its votes.

Net change, canvass minus PREP, in the cells both acts read:

| Item | All 102,275 | The 86,721 where the PREP read every cell | The 15,554 where it did not |
| --- | --- | --- | --- |
| `PVEM-PT-MORENA` | +119,390 | +167,955 | −48,565 |
| `PAN-PRI-PRD` | −95,098 | −31,681 | −63,417 |
| `MC` | −25,348 | −12,310 | −13,038 |
| Unregistered candidates | −9,749 | −4,216 | −5,533 |
| Null votes | −57,290 | −41,022 | −16,268 |

These figures should not be read as a transfer of votes between
candidatures:

- They compare a capture with a count, cell by cell, and a large part comes
  from few stations. The 2,034 stations with a change of more than 100 votes
  in one cell account for +51,534, −48,983, −23,448, −4,843 and −17,902 of
  the first column, in the order of the rows.
- The two groups of stations behave differently. Where the PREP could not
  read some cell, every net figure is negative: on the cells it did read, the
  PREP has more votes than the canvass.
- The six stations of that group with the largest changes were looked at in
  the files. In four of them the PREP's figures are close to those of the
  canvass moved by one or two cells, with the first or last cell unread; the
  other two do not fit that pattern. Six stations say nothing about the
  rest: an exact test for "the PREP row is the canvass row moved one cell"
  finds 5 stations in all, and no looser test was run.
- No tally sheet image was downloaded for any of them.

## The total written on the sheet

In 32,198 of the 158,972 tally sheets, the total written on the sheet
(`TOTAL_VOTOS_ASENTADO`) is not the sum of the cells that were read. This
includes sheets with unread cells.

## The vote from abroad

The PREP has 32 rows of type `M`, one per state, with 184,376 ballots. The
Cómputos file has 87 rows of type `M` and 64 of type `V`, with other keys.
The 32 rows give no statement: see the profile, section 6, point 3.

## What this run says about the format

Mexico did not enter without changing the core. The PREP's unread cells
needed `counts.unread` and lower bounds in the verifier (core, sections 3.4
and 5). The rest of the run came out of the core as it was written for Spain
and Colombia, and it is the first run with real statements of both a count
and a later act.

What else did not fit, and was left as a limit, is in
[`../spec/profile-mx.md`](../spec/profile-mx.md), section 6.

## What is not known

- Whether either file is the last version the INE published.
- The result validated by the electoral court.
- Why any station's figures differ: no tally sheet image was downloaded.
- What stations of type `V` are.
- Why the INE's catalogue of stations of 3 May 2024 has 161,965 rows.
