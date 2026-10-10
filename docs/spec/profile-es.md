# Spain profile (draft `es/loreg/v0.1`)

**English** · [Español](profile-es.es.md)

This English text is the normative one.

Status: **draft, not validated against real files yet** (see section 5).

This profile maps Spanish general-election results onto the core format.
The governing law is the Ley Orgánica 5/1985 del Régimen Electoral General
(LOREG).

## 1. Scope

- Supported: elections to the Congreso de los Diputados (Ministry election
  type `02`), where the constituency is the province. Ceuta and Melilla carry
  their own province codes.
- Not supported yet: Senate, municipal, European and regional elections.
  Regional elections have their own laws and tally-sheet models.

## 2. Identifiers

| Core field | Form | Example |
| --- | --- | --- |
| `election` | `es/congreso/<yyyy>-<mm>` | `es/congreso/2019-11` |
| `constituency` | `es/<province>` | `es/08` |
| `station` | `es/<province>/<municipality>/<district>/<section>/<station>` | `es/08/019/01/001/A` |

Codes are the ones used in the Ministry's files: province (2 digits),
municipality (3), district (2), section (up to 4 characters, surrounding
spaces removed) and polling-station letter (1).

Candidature codes are the 6-digit codes of the Ministry's files for that
election. They are not stable across elections.

## 3. Source of official data

The Ministry of the Interior publishes ZIP files per election at
<https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/>.
Each ZIP contains fixed-width text files, ISO-8859-1 encoded, named
`NNTTYYMM.DAT`.

| ZIP | File | Content | Used for |
| --- | --- | --- | --- |
| `…_MESA.zip` | `09` | One row per polling station | Statement header and totals |
| `…_MESA.zip` | `10` | One row per station and candidature | `counts.candidatures` |
| `…_TOTA.zip` | `07` | One row per province or higher | Official totals |
| `…_TOTA.zip` | `08` | One row per province (or higher) and candidature | Official candidature totals |

Columns read (1-based, inclusive):

| File | Field | Columns |
| --- | --- | --- |
| all | election type, year, month | 1–2, 3–6, 7–8 |
| all | province | 12–13 |
| 09, 10 | municipality, district, section, station | 14–16, 17–18, 19–22, 23 |
| 09 | registered voters (INE census) | 24–30 |
| 09 | blank, null, candidature votes | 66–72, 73–79, 80–86 |
| 09 | official-data flag | 101 |
| 10 | candidature code, votes | 24–29, 30–36 |
| 07 | number of stations | 73–77 |
| 07 | blank, null, candidature votes | 126–133, 134–141, 142–149 |
| 08 | candidature code, votes | 15–20, 21–28 |

Rows with province code `99` are subtotals and are ignored: national and
regional totals in files `07` and `08`, and overseas-vote (CERA) totals per
region in files `09` and `10`. The overseas votes also appear as one row per
province, with municipality code `999`. Those rows are kept, with
`unit` set to `aggregate`: they add votes to the province, but the Ministry's
station count does not include them.

In the November 2019 files the `_MESA` ZIP also contains files `07` and `08`
and a copy of the Ministry's record-layout document (`FICHEROS.doc`).

These positions were taken from the record layout as implemented in the
rOpenSpain [`infoelectoral`](https://github.com/rOpenSpain/infoelectoral)
R package (Meleiro, 2024), not from the Ministry's own layout document.

## 4. Mapping to the tally sheet

Article 97.2 LOREG lists what the polling station's tally sheet (*acta de
escrutinio*) records: registered voters, census certificates presented,
voters, null ballots, blank ballots and votes per candidature.

| Tally sheet (art. 97.2) | Statement field | In the Ministry files? |
| --- | --- | --- |
| Registered voters | `counts.registered` | Yes (file 09) |
| Census certificates presented | — | Not found |
| Voters | derived: blank + null + candidature votes | Not as a separate final figure |
| Null ballots | `counts.null` | Yes |
| Blank ballots | `counts.blank` | Yes |
| Votes per candidature | `counts.candidatures` | Yes (file 10) |

Overseas-voter figures present in file 09 (`censo_cera`, `censo_cere`,
`votantes_cere`) are kept under `extra` and do not take part in verification.

## 5. Known gaps and unverified assumptions

1. **No complete run against real data yet.** A first attempt on the November
   2019 files exposed the province-99 rows described in section 3. The reader
   is otherwise tested with synthetic files and two real rows.
2. The LOREG articles were read in an unofficial transcription, not in the
   official gazette (BOE). An amendment published on 2 July 2026 has not been
   reviewed.
3. It is assumed that candidature codes in file 10 and file 08 are the same
   code set. If the Ministry aggregates candidatures under different codes at
   province level, the comparison needs the mapping in file `03`.
4. Overseas votes (CERA) appear as one station-like row per province
   (municipality `999`). This was seen in the November 2019 files; whether
   those rows make station sums reach the province total is not yet confirmed.
5. It is not known whether the per-station files hold provisional or final
   results, nor how they treat corrections made during the general canvass
   (LOREG arts. 103–108). Differences may therefore be legitimate.
6. A statement built from these files is evidence about the **published
   dataset**, not about the paper tally sheet. Matching totals show that the
   Ministry's two publications are consistent with each other.
