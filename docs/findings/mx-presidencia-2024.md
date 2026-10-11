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
The INE publishes no hash for either file that was found, so these only say
which bytes were read.

```sh
actasum mx replay --prep PREP/PRES_2024.csv --computos COMPUTOS/PRES_2024.csv --election 2024-06
actasum mx replay --prep PREP/PRES_2024.csv --computos COMPUTOS/PRES_2024.csv --election 2024-06 \
    --unreadable-as-zero
```

Everything below compares two publications of the same authority **with each
other**. No tally sheet was looked at and no declared result was read. The
PREP is the INE's capture of one copy of each tally sheet, which the INE
itself calls preliminary and not definitive. A difference between the PREP
and the canvass can be a capture error, a correction or the result of
counting the ballots again; these files do not say which, and nothing here
does either.

## Summary

| Check | Result |
| --- | --- |
| The PREP's rows add up to the totals it prints | Yes: tally sheets counted, votes and registered voters |
| The Cómputos rows add up to the totals it prints | Yes: tally sheets, votes and registered voters |
| Stations with a statement of both acts | 138,799 |
| Of them, with the same figures in both | 52,078 |
| Of them, with different figures | 86,721 |
| Stations in conflict, or left undetermined by the core | 0 |

## Each file against its own header

| | PREP | Cómputos |
| --- | --- | --- |
| Rows | 171,410 | 170,766 |
| Tally sheets expected, as printed | 170,648 | 170,766 |
| Tally sheets counted, printed and recomputed | 159,004 | 170,766 |
| Votes, printed and recomputed | 56,107,873 | 60,115,184 |
| Registered voters, printed and recomputed | 92,092,843 | 98,468,994 |

The PREP's extra 762 rows are tally sheets it could not match to a station.
Its total of votes is reproduced only when the cells it could not capture are
added up as zero, which is what the file's own total does.

## What gives no statement

PREP, of 171,410 rows:

| Rows | Why, as the file says |
| --- | --- |
| 8,131 | No tally sheet captured at the cut |
| 1,442 | `Sin acta`: the sheet did not reach the collection centre |
| 886 | All figures empty |
| 790 | All figures illegible |
| 762 | Could not be matched to a station |
| 395 | More votes than registered voters |
| 20,160 | Counted by the PREP, with at least one figure it could not capture |
| 32 | Vote from abroad, one row per state |

That leaves 138,812 statements of the count. With `--unreadable-as-zero` the
20,160 are kept and there are 158,972.

Cómputos, of 170,766 rows: 145 have no figures and 170,621 give a statement.
The 145 are 122 packages not received (`Paquete no recibido`, in three
variants) and 23 stations not installed (`Casilla no instalada`).

In the Cómputos file 116,397 rows, 68 per cent, are marked as a recount of
the ballots; the rest were compared against the council's copy.

## The two sums

| | Stations | Ballots |
| --- | --- | --- |
| As counted (PREP statements) | 138,812 | 49,460,877 |
| As standing | 170,634 | 60,119,464 |

The two sums are over different sets of stations and cannot be subtracted
from each other. The standing sum is the Cómputos total, 60,115,184, plus
4,280 ballots of 13 stations that have a statement of the count and none of
the canvass: the Cómputos file has no figures for them, or no row.

## Station by station

Of the 138,799 stations with both acts, 48,036 were compared and 90,763
recounted.

| | Stations | Figures changed |
| --- | --- | --- |
| Compared against the council's copy | 48,036 | 2,461 |
| Ballots counted again | 90,763 | 84,260 |

Of the 86,721 stations whose figures changed, 7,084 only move votes between
columns of one coalition: every candidature keeps its votes.

In the other 79,637, by how many votes changed hands, added up over
candidatures:

| Size of the change | Stations |
| --- | --- |
| Up to 5 votes | 45,823 |
| 6 to 20 | 22,536 |
| 21 to 100 | 9,043 |
| More than 100 | 2,235 |

Net change, canvass minus PREP, over the 86,721 stations:

| Item | All changed stations | Of which, the 2,235 largest |
| --- | --- | --- |
| `PVEM-PT-MORENA` | +167,955 | +97,267 |
| `PAN-PRI-PRD` | −31,681 | −17,329 |
| `MC` | −12,310 | −16,694 |
| Unregistered candidates | −4,216 | −2,833 |
| Null votes | −41,022 | −14,377 |

More than half of the largest net figure comes from the 2,235 stations with
the largest changes. None of those tally sheets was looked at. A change of
several hundred votes in one station is what a figure captured in the wrong
column would look like, and it is also what other causes would look like.

Among the stations that were only compared, where the canvass did not count
ballots again, 5.1 per cent (2,461 of 48,036) differ from the PREP.

## Figures the PREP could not read

In the 20,160 tally sheets the PREP counted without capturing every figure,
100,308 cells are marked `Sin dato` (93,167) or `Ilegible` (7,141). The PREP
adds them up as zero. They are not counted as null votes: null votes have
their own column, which is itself among the unreadable ones in 2,093 cells.

Run with `--unreadable-as-zero`, the reader keeps those sheets and the
canvass can be asked what it has in those cells:

| PREP says | Cells compared | Zero in the canvass | Not zero | Votes in the canvass |
| --- | --- | --- | --- | --- |
| `Sin dato` | 93,151 | 66,485 | 26,666 | 189,020 |
| `Ilegible` | 7,141 | 2,771 | 4,370 | 124,980 |

So about seven in ten of the empty cells are zeros in the canvass, and the
cells together hold 314,000 votes there. Treated as zero, they turn into
changes that nobody made: with `--unreadable-as-zero` the stations with
changed figures rise from 86,721 to 102,675 and the largest net figure from
+167,955 to +321,140. This is why the default gives those sheets no
statement.

Most of these cells are columns for combinations of two parties of a
coalition and for unregistered candidates, where a sheet often has nothing
written.

## The total written on the sheet

In 32,230 of the 159,004 tally sheets the PREP counted, the total written on
the sheet (`TOTAL_VOTOS_ASENTADO`) is not the sum of the captured figures.
This includes the sheets with unreadable figures.

## The vote from abroad

The PREP has 32 rows of type `M`, one per state, with 184,376 ballots. The
Cómputos file has 87 rows of type `M` and 64 of type `V`, with other keys.
The 32 rows give no statement: see the profile, section 6, point 3.

## What this run says about the format

The core was not changed. The two sums, the chain from the count to the
canvass and the list of changed stations came out of the core as it was
written for Spain and Colombia, and this is the first run with real
statements of both a count and a later act.

Seven things did not fit and are listed in
[`../spec/profile-mx.md`](../spec/profile-mx.md), section 6. Three of them
changed the numbers above: 20,160 tally sheets with an unreadable figure and
32 rows of the vote from abroad give no statement, and whether a station was
recounted is known to the profile but not to the verifier.

## What is not known

- Whether either file is the last version the INE published.
- The declared result, and the result validated by the electoral court.
- Why any station's figures differ: no tally sheet image was downloaded.
- What stations of type `V` are.
- Why the INE's catalogue of stations of 3 May 2024 has 161,965 rows.
