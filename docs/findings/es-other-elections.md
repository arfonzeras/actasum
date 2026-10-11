# Findings: Spain, European Parliament and local elections

Runs of 11 October 2026 on the per-station ZIP files published by the
Ministry of the Interior, with `actasum` at commit `4a69045`. One election of
each type has been run so far.

```sh
actasum es describe --mesa 07202406_MESA.zip                  # what the ZIP contains
actasum es replay   --mesa 07202406_MESA.zip                  # national constituency
actasum es replay   --mesa 07202406_MESA.zip --level province # per province
actasum es replay   --mesa 04202305_MESA.zip                  # one constituency per municipality
```

As in the Congreso runs, everything below compares the Ministry's
publications **with each other**. Nothing here has been compared with paper
tally sheets or with the results proclaimed by the electoral boards. A
difference means two published figures do not add up; it does not say which
one is right, or why.

| Election | ZIP (SHA-256) | Polling stations | Constituencies matching |
| --- | --- | --- | --- |
| European Parliament, June 2024 | `07202406_MESA.zip` (`ed30e4cf…b6659b`) | 58,556, plus 52 overseas rows | 1 of 1 |
| Local, May 2023 | `04202305_MESA.zip` (`20dac696…ab0de3`) | 57,681 | 5,248 of 5,272 |

Full hashes:
`ed30e4cf11772afb0785f2992f44fa191b8671f933865335b7093ac9ccb6659b` and
`20dac696cd2efaa63c9346384ddb682f3da4fda92c6af67447159a60f1ab0de3`.

## European Parliament, June 2024

The station rows and the 52 overseas rows add up exactly to the national row:
number of stations, blank votes, null votes and every candidature. Compared
per province, all 52 provinces match too.

The national rows merge candidatures. File `03` lists 60 candidatures, 26 of
which are accumulated at national level under the code of another one, and
the national candidature rows are 34, which is 60 minus 26. The match was
obtained after merging the station votes the same way. None of the 60 is
merged at province or region level.

The files follow the layout document: same line lengths as in the Congreso
files, 20 overseas subtotal rows with province `99` in file `09` (19 regions
and the country), 52 overseas rows.

Not run for this election: the municipality level and the overseas residual.

## Local, May 2023

What the ZIP contains agrees with the layout document on three points: the
per-station files have no overseas rows and no subtotal rows; a second set of
files of election type `10` reuses numbers `05` to `08` and was set aside;
and files `11` and `12` hold municipalities without station detail.

- 5,272 municipalities have a whole-municipality row in file `05`, and the
  per-station file has stations for exactly those 5,272.
- File `11` lists 2,815 more municipalities. This profile does not read
  them, so they are outside the comparison. Together that makes 8,087; the
  Congreso files of July 2023 have 8,131 municipalities. The gap of 44 has
  not been looked into.

Of the 5,272 municipalities compared, 5,248 match their polling stations in
every figure and 24 do not. The report lists 105 differing items in those 24.
The first 20, as printed:

| Municipality | Item | From stations | Municipal file | Difference |
| --- | --- | --- | --- | --- |
| `es/04/045` | blank | 10 | 9 | +1 |
| `es/04/045` | null | 10 | 7 | +3 |
| `es/04/045` | all candidatures | 1,358 | 1,390 | −32 |
| `es/04/045` | candidature 000006 | 357 | 388 | −31 |
| `es/04/045` | candidature 000007 | 346 | 329 | +17 |
| `es/04/045` | candidature 000027 | 31 | 12 | +19 |
| `es/04/045` | candidature 000030 | 596 | 648 | −52 |
| `es/04/045` | candidature 000286 | 28 | 13 | +15 |
| `es/04/049` | all candidatures | 4,007 | 4,127 | −120 |
| `es/04/049` | candidature 000006 | 1,526 | 1,549 | −23 |
| `es/04/049` | candidature 000007 | 238 | 228 | +10 |
| `es/04/049` | candidature 000030 | 1,586 | 1,656 | −70 |
| `es/04/049` | candidature 000036 | 231 | 245 | −14 |
| `es/04/049` | candidature 000287 | 426 | 449 | −23 |
| `es/07/057` | candidature 000006 | 2,895 | 3,011 | −116 |
| `es/07/057` | candidature 000423 | 645 | 470 | +175 |
| `es/07/057` | candidature 000507 | 977 | 1,036 | −59 |
| `es/09/330` | all candidatures | 990 | 993 | −3 |
| `es/10/159` | null | 4 | 5 | −1 |
| `es/10/159` | all candidatures | 281 | 280 | +1 |

The remaining 85 items have not been recorded here yet.

Two things can be read off these rows without explaining them:

- In `es/07/057` the three differences cancel out (−116 + 175 − 59 = 0). The
  two files agree on the municipality's total and differ on how it is split
  among three candidatures.
- In `es/09/330` the stations fall 3 votes short, and two stations of that
  municipality have candidature rows that add up to 1 and 2 votes less than
  the station's own total (see below).

In a local election the municipality is the constituency, so these are
differences at the level where seats are allotted. Whether any of them could
change an allocation has not been computed, and which of the two files
corresponds to the proclaimed result is not known. Local results are
proclaimed by the area electoral boards and are not published in the official
gazette the way national results are, so the cross-check used for the Congreso
is not available here.

### Stations with internal inconsistencies

| Station | Check | Detail |
| --- | --- | --- |
| `es/09/330/01/001/A` | candidature sum | rows add up to 382, station total 383 |
| `es/09/330/01/001/B` | candidature sum | rows add up to 315, station total 317 |
| `es/24/056/01/001/B` | candidature sum | rows add up to 392, station total 394 |
| `es/15/066/01/001/B` | candidature sum | rows add up to 401, station total 408 |
| `es/03/019/03/005/A` | candidature sum | rows add up to 367, station total 368 |
| `es/03/019/04/002/U` | candidature sum | rows add up to 472, station total 468 |
| `es/46/104/01/002/U` | more ballots than registered | 492 ballots, 487 registered |

The candidature-sum check did not fire in any of the five Congreso runs or in
the European Parliament run.
