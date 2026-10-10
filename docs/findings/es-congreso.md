# Findings: Spain, Congreso elections

Runs of 11 October 2026 on the per-station ZIP files published by the
Ministry of the Interior (`02YYYYMM_MESA.zip`), with `tallylog` at the commit
that adds this file. Each run can be repeated with:

```sh
tallylog es replay --mesa 02202307_MESA.zip                       # per constituency
tallylog es replay --mesa 02202307_MESA.zip --level municipality  # per municipality
tallylog es replay --mesa 02202307_MESA.zip --level overseas      # overseas rows
```

Everything below compares the Ministry's publications **with each other**.
Nothing here has been compared with paper tally sheets or with the results
proclaimed by the electoral boards. A difference means two published figures
do not add up; it does not say which one is right, or why.

## Summary

| Election | Polling stations | Constituencies matching | Municipalities matching | Overseas rows matching |
| --- | --- | --- | --- | --- |
| March 2008 | 59,346 | 50 of 52 | 8,111 of 8,112 | 49 of 52 |
| June 2016 | 57,531 | 52 of 52 | not run | not run |
| April 2019 | 60,038 | 52 of 52 | not run | not run |
| November 2019 | 59,555 | 52 of 52 | 8,131 of 8,131 | 52 of 52 |
| July 2023 | 60,314 | 50 of 52 | 8,131 of 8,131 | 50 of 52 |

"Overseas rows matching" compares each constituency's overseas (CERA) row in
the per-station file with the province total minus the sum of its
municipalities. That residual is derived here; the Ministry does not publish
it as such.

## July 2023

All 8,131 municipalities match their polling stations. The two constituencies
that differ do so only in the overseas row.

| Constituency | Item | Per-station file | Implied by totals | Difference |
| --- | --- | --- | --- | --- |
| Cantabria (`es/39`) | blank | 19 | 15 | +4 |
| Cantabria (`es/39`) | null | 51 | 39 | +12 |
| Toledo (`es/45`) | blank | 12 | 7 | +5 |
| Toledo (`es/45`) | null | 35 | 25 | +10 |
| Toledo (`es/45`) | all candidatures | 1,664 | 1,489 | +175 |
| Toledo (`es/45`) | candidature 000001 | 7 | 228 | −221 |
| Toledo (`es/45`) | candidature 000002 | 632 | 573 | +59 |
| Toledo (`es/45`) | candidature 000003 | 7 | 8 | −1 |
| Toledo (`es/45`) | candidature 000005 | 497 | 217 | +280 |
| Toledo (`es/45`) | candidature 000006 | 217 | 149 | +68 |
| Toledo (`es/45`) | candidature 000007 | 39 | 36 | +3 |
| Toledo (`es/45`) | candidature 000010 | 256 | 269 | −13 |

Candidature codes are the Ministry's codes for that election; their names are
in file `03` of the same ZIP and have not been looked up here.

## March 2008

| Where | What differs |
| --- | --- |
| Barcelona (`es/08`) | Overseas row: four candidatures differ by 2 votes each (+2, +2, −2, −2). All municipalities match |
| Murcia (`es/30`) | Overseas row: two candidatures differ by −2 and −1. All municipalities match |
| Soria, municipality `es/42/161` | The municipal file gives 124 candidature votes and 1 blank vote; the per-station file has that station at zero. The province total agrees with the per-station file |

The Soria case also shows up in the overseas comparison (+124, +1), because
the residual is computed from the municipal totals. It is one discrepancy,
not two.

## Polling stations with more ballots than registered voters

Registered voters are taken from the count roll (*censo de escrutinio*).

| Election | Station | Ballots | Registered |
| --- | --- | --- | --- |
| March 2008 | `es/09/450/01/001/U` | 29 | 28 |
| March 2008 | `es/03/082/03/001/A` | 285 | 249 |
| March 2008 | `es/46/211/01/001/A` | 778 | 775 |
| March 2008 | `es/30/005/01/006/A` | 556 | 513 |
| April 2019 | `es/28/079/07/092/A` | 514 | 466 |
| July 2023 | `es/24/206/01/001/B` | 468 | 251 |
| July 2023 | `es/24/206/01/001/C` | 349 | 207 |
| July 2023 | `es/24/222/02/001/B` | 503 | 143 |
| July 2023 | `es/24/222/02/001/C` | 436 | 89 |

None in June 2016 or November 2019. One possible explanation for small
excesses is party agents voting at the station where they are accredited
rather than where they are registered. Neither that rule nor whether it
applies to any of these stations has been checked here.

## What is not known

- Which of the two figures is correct in each difference.
- Whether the per-station files hold provisional or final results, and
  whether the totals were updated after the general canvass while the
  per-station files were not, or the other way round.
- Whether the results proclaimed by the electoral boards and published in the
  official gazette agree with either figure.
