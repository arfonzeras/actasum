# Findings: Spain, Congreso elections

Runs of 11 October 2026 on the per-station ZIP files published by the
Ministry of the Interior (`02YYYYMM_MESA.zip`), with `actasum` at the commit
that adds this file. Each run can be repeated with:

```sh
actasum es replay --mesa 02202307_MESA.zip                       # per constituency
actasum es replay --mesa 02202307_MESA.zip --level municipality  # per municipality
actasum es replay --mesa 02202307_MESA.zip --level overseas      # overseas rows
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

### Comparison with the proclaimed results

The results proclaimed by the electoral boards were published in the official
gazette (Resolution of 30 August 2023 of the Presidency of the Junta Electoral
Central, [BOE-A-2023-18907](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2023-18907)).
For Toledo it gives:

| Candidature (as named in the gazette) | Proclaimed | Ministry totals file | Sum of the per-station file |
| --- | --- | --- | --- |
| PP | 146,533 | 146,533 | 146,813 |
| PSOE | 126,072 | 126,072 | 126,131 |
| VOX | 76,044 | 76,044 | 76,112 |
| SUMAR | 31,876 | 31,876 | 31,863 |
| PACMA | 2,024 | 2,024 | 2,027 |
| FO | 985 | 985 | 764 |
| PUM+J | 499 | 499 | 498 |

So in Toledo the Ministry's **totals file agrees with the proclaimed
results**, and the overseas row of the **per-station file is the figure that
differs**. The pairing of gazette names with Ministry codes is inferred from
the vote figures, not read from file `03`.

Applying the D'Hondt rule to either column gives the same six seats (3, 2, 1).
That calculation was done here and is not an official one.

The gazette page was read through an automatic extract. Blank and null votes
are in a table published as an image, so Cantabria, which differs only in
those, could not be compared.

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

## Log checkpoint

On 11 October 2026 the November 2019 statements were loaded into a log:
59,607 entries, the 59,555 polling stations plus the 52 overseas rows. The
source file `02201911_MESA.zip` had SHA-256
`e7b621f295d7bf79b794941d4f11e7bcf7bd971ecbd6eb21dd4269d59926e441`; every
entry carries that hash as its evidence.

Three checks were run on that log the same day:

- an inclusion proof for station `es/04/003/02/001/B` (entry 0) verified
  against the checkpoint;
- after changing one figure in a copy of the log, the tool refused to open
  the copy, reporting the same size but a different root;
- the checkpoint was signed by the log, cosigned by a witness and accepted
  with a quorum of one. Both ran on the same machine, so this shows that the
  mechanism works, not that the log is independently attested.

The project was then renamed from `tallylog` to `actasum`. The format
identifiers are part of every entry, so the root changed and the checkpoint
obtained on the 10th is no longer reproducible with the current code.

Rebuilt on 11 October 2026 from the same ZIP file, at commit `c078345`, the
log gives this checkpoint:

```
actasum/es/congreso/2019-11
59607
YbzbgsGgE5v03X6nJf60aQsBRVt/QTm7Rjsd6vTDuvs=
```

Anyone who starts from the same ZIP file and the same version of the format
should obtain the same three lines. The checkpoint is recorded here so that
the computation can be repeated, not as an attestation: it is not signed by a
published key and no independent witness has cosigned it. A change to the
statement format changes the root.

## What is not known

- Which of the two figures is correct in each difference.
- Whether the per-station files hold provisional or final results, and
  whether the totals were updated after the general canvass while the
  per-station files were not, or the other way round.
- For Cantabria (2023) and for the 2008 cases, whether the results proclaimed
  by the electoral boards agree with either figure. For Toledo (2023) they
  agree with the totals file.
- Why the per-station file's overseas row for Toledo differs from the
  proclaimed overseas vote.
