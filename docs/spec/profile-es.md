# Spain profile (draft `es/loreg/v0.1`)

**English** · [Español](profile-es.es.md)

This English text is the normative one.

Status: **draft, run against five Congreso elections** (2008 to 2023; see
section 5 and [`../findings/es-congreso.md`](../findings/es-congreso.md)).
One European Parliament election (2024) and one local election (2023) have
been run as well; see
[`../findings/es-other-elections.md`](../findings/es-other-elections.md).

This profile maps Spanish election results onto the core format.
The governing law is the Ley Orgánica 5/1985 del Régimen Electoral General
(LOREG).

## 1. Scope

- Supported and run on real files: elections to the Congreso de los
  Diputados (Ministry election type `02`), where the constituency is the
  province. Ceuta and Melilla carry their own province codes.
- Supported and run on one real file each: local elections (type `04`),
  where the constituency is the municipality, and European Parliament
  elections (type `07`), where the constituency is the whole country. See
  section 3.3.
- Not supported: Senate (votes go to candidates, not candidatures), regional
  elections (their own laws and tally-sheet models), island councils and
  referendums.

## 2. Identifiers

| Core field | Form | Example |
| --- | --- | --- |
| `election` | `es/<type>/<yyyy>-<mm>`, type being `congreso`, `municipales` or `europeas` | `es/congreso/2019-11` |
| `constituency` (Congreso) | `es/<province>` | `es/08` |
| `constituency` (local) | `es/<province>/<municipality>` | `es/08/019` |
| `constituency` (European Parliament) | `es` | `es` |
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
| `…_MESA.zip` | `05` | One row per municipality and per municipal district | Official totals per municipality |
| `…_MESA.zip` | `06` | One row per municipality (or district) and candidature | Official candidature totals per municipality |
| `…_TOTA.zip` | `07` | One row per province or higher | Official totals |
| `…_TOTA.zip` | `08` | One row per province (or higher) and candidature | Official candidature totals |

Columns read (1-based, inclusive):

| File | Field | Columns |
| --- | --- | --- |
| all | election type, year, month | 1–2, 3–6, 7–8 |
| all | province | 12–13 |
| 09, 10 | municipality, district, section, station | 14–16, 17–18, 19–22, 23 |
| 09 | registered voters (*censo de escrutinio*, or CERA census in overseas rows) | 31–37 |
| 09 | INE census (kept under `extra` when it differs) | 24–30 |
| 09 | blank, null, candidature votes | 66–72, 73–79, 80–86 |
| 09 | official-data flag | 101 |
| 10 | candidature code, votes | 24–29, 30–36 |
| 07 | number of stations | 73–77 |
| 07 | blank, null, candidature votes | 126–133, 134–141, 142–149 |
| 08 | candidature code, votes | 15–20, 21–28 |
| 05 | municipality, district (`99` = whole municipality) | 14–16, 17–18 |
| 05 | number of stations | 137–141 |
| 05 | blank, null, candidature votes | 190–197, 198–205, 206–213 |
| 06 | province, municipality, district | 10–11, 12–14, 15–16 |
| 06 | candidature code, votes | 17–22, 23–30 |

Rows with province code `99` are subtotals and are ignored: national and
regional totals in files `07` and `08`, and overseas-vote (CERA) totals per
region in files `09` and `10`. The overseas votes also appear as one row per
province, with municipality code `999`. Those rows are kept, with
`unit` set to `aggregate`: they add votes to the province, but the Ministry's
station count does not include them.

The `_MESA` ZIP also contains files `07` and `08`, so it is enough on its
own, and a copy of the Ministry's record-layout document (`FICHEROS.doc`).

These positions were first taken from the rOpenSpain
[`infoelectoral`](https://github.com/rOpenSpain/infoelectoral) R package
(Meleiro, 2024) and then checked against the Ministry's own record-layout
document, *Ficheros de Carga de Datos de Elecciones* (2010), which ships
inside the ZIP files as `FICHEROS.doc`. Every position in the table above
agrees with that document.

### 3.1 Municipality level

The constituency is the province, but the same ZIP publishes totals per
municipality. The reader can compare at that level too
(`grouping: station-prefix/3`, areas such as `es/45/168`), which shows in
which municipalities a province-level difference arises. Only rows for the
whole municipality (district `99`) are used. Overseas rows belong to no
municipality and are left out of this comparison.

### 3.2 Overseas residual

The files carry no separate official overseas total per province. The
province total minus the sum of its municipalities is what the official
figures leave for the overseas vote. `--level overseas` compares that
residual with the overseas row of the per-station file. Together with the
municipality level it tells whether a province-level difference sits in the
polling stations or in the overseas row.

### 3.3 Local and European Parliament elections

What follows comes from the layout document, dated 2010. The files of the
June 2024 European Parliament election and of the May 2023 local elections
agree with it on every point marked *(seen)*.

**Local elections (type `04`).** The constituency is the municipality, so the
official totals per constituency are the whole-municipality rows of files
`05` and `06`. According to the layout document:

- the per-station files hold only municipalities of more than 250
  inhabitants and no overseas rows *(no overseas rows: seen; the threshold:
  not checked)*. Smaller municipalities are in files `11` and `12`, with one
  row per municipality and no station detail *(seen: 2,815 rows in 2023)*.
  This profile does not read them, so those municipalities are outside the
  comparison;
- the ZIP also carries files of election type `10` (judicial districts and
  provincial councils) that reuse file numbers `05` to `08`. They are set
  aside *(seen)*.

The 250-inhabitant threshold is the one in the 2010 document. The law on
small municipalities changed after that date and this has not been followed
up here.

**European Parliament elections (type `07`).** There is one national
constituency. The official totals are the national row of files `07` and
`08` (region `99`, province `99`). File `03` gives, for each candidature, the
code under which its votes are accumulated at national level (columns
227–232); the reader passes that mapping to the verifier as `merge`
(core, section 4.2). Without file `03` nothing is merged *(seen: 26 of 60
candidatures merged in 2024, and the totals match once merged)*. Province
rows can be compared as a lower level (`--level province`), overseas rows
included *(seen: no merging at that level)*.

`actasum es seats --mesa ZIP` (local elections only) allocates the seats of
each municipality from the municipal file's votes and from the station
votes, by LOREG articles 163.1 and 180, and compares both with the seats
published in file `06` (columns 31–33; seats to fill in file `05`, columns
214–216). Ties that the law settles by lot are left out.

`actasum es describe --mesa ZIP` lists what a ZIP contains (files, line
lengths, subtotal and overseas rows, merged candidatures) without comparing
anything. It is the first thing to run on an election type or year that has
not been tried.

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

Other figures present in file 09 (`censo_ine`, and the foreign-resident
figures `censo_cere` and `votantes_cere`) are kept under `extra` and do not
take part in verification.

## 5. Known gaps and unverified assumptions

1. **Five real runs so far**, all Congreso elections between 2008 and 2023.
   The layout held in all of them. Older elections and other election types
   have not been tried.
2. Articles 79 and 95 to 108 of the LOREG were checked on 11 October 2026
   against the consolidated text published by the official gazette (BOE,
   reference BOE-A-1985-11672, last amended 2 July 2026). The rest of the
   law has not been read for this profile. The July 2026 amendment (Organic
   Law 2/2026) changes articles 161.2 and 165.2, on Senate constituencies,
   and does not touch the count.
   One European Parliament election and one local election have been run.
   In the local-election files, 3,223 of 5,423 candidatures are accumulated
   under another code at province level, so the province rows of file `08`
   cannot be compared with station sums without that mapping; this profile
   does not attempt it. Municipalities listed only in file `11` are not
   compared.
3. Candidature codes in file 10 and file 08 are the same code set in the
   November 2019 files, since every candidature total matches. This is not
   confirmed for other elections; if it fails, the mapping is in file `03`.
4. Overseas votes (CERA) appear as one station-like row per province
   (municipality `999`). In the November 2019 files, station rows plus these
   rows add up exactly to the province totals.
5. It is not known in general whether the per-station files hold provisional
   or final results, nor how they treat corrections made during the general
   canvass (LOREG arts. 103–108). Differences may therefore be legitimate. In
   the May 2023 local elections there are three municipalities where the
   result changed afterwards (one correction, two repeated votes) and the
   municipal file shows the later figures while the per-station file shows
   the earlier ones; see the findings.
6. A statement built from these files is evidence about the **published
   dataset**, not about the paper tally sheet. Matching totals show that the
   Ministry's two publications are consistent with each other.
