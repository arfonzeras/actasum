# Mexico profile (draft `mx/lgipe/v0.1`)

Status: **draft, run on one election**: the presidential election of 2 June
2024 (see [`../findings/mx-presidencia-2024.md`](../findings/mx-presidencia-2024.md)).
Everything here was learnt from two database files of the Instituto Nacional
Electoral (INE), their `LEEME.txt` files and the two manuals the INE publishes
for them. Nothing has been checked against the law, no tally sheet has been
looked at, and no Mexican organisation has reviewed it.

This profile was written to find out whether a third country fits the core
format without changing it. It does, and section 6 lists what did not fit and
was left as a limit of the profile.

## 1. How the count travels

According to the INE's manuals for the two databases (June 2024):

1. At the polling station (*casilla*) the officials fill in a tally sheet
   (*acta de escrutinio y cómputo*, AEC). One copy, the *Acta PREP*, travels to
   a collection centre, or is photographed at the station.
2. The **PREP** (*Programa de Resultados Electorales Preliminares*) captures
   and publishes the figures of those copies during the night and the
   following day. The INE describes its results as preliminary, not definitive
   and strictly informative.
3. In the following days the district councils carry out the **cómputos
   distritales**. A tally sheet is either compared with the copy held by the
   council (*cotejo*) or, in the cases the manual lists, the ballots of the
   station are counted again (*recuento*).

## 2. Identifiers

| Core field | Form | Example |
| --- | --- | --- |
| `election` | `mx/presidencia/<yyyy>-<mm>` | `mx/presidencia/2024-06` |
| `constituency` | `mx` | `mx` |
| `station` | `mx/<state>/<section>/<station>` | `mx/01/0338/B0100` |
| candidature code | party, or parties of one coalition joined by `-` | `PVEM-PT-MORENA` |

The station identifier is the `CLAVE_CASILLA` of the files (`010338B0100`):
state (2 digits), section (4), then the type of station, its number and the
number of the adjoining station (`B0100`). The federal district is not part of
it: the two files do not give the same district for 434 stations.

Only the presidential election is supported. Senate and Chamber of Deputies
files have the same layout with other constituencies and are refused.

## 3. Sources

Both files are named `PRES_2024.csv` and come inside ZIP files named after the
date and time they were generated. They do not carry the date of the
election, which is given on the command line.

| | PREP database | Cómputos Distritales database |
| --- | --- | --- |
| Encoding, line ending | UTF-8 with a byte-order mark, CR | ISO-8859-1, CR LF |
| Separator | comma | `\|`, announced by a first line `sep=\|` |
| Guards around values | station keys in single quotes | also `="01"` around codes |
| Coalition columns | `PAN-PRI-PRD`, `PVEM_PT_MORENA` | `PAN_PRI_PRD`, `PVEM_PT_MORENA` |
| Unregistered candidates, null votes | `NO_REGISTRADAS`, `NULOS` | `CANDIDATO/A NO REGISTRADO/A`, `VOTOS NULOS` |
| A row is | a tally sheet as captured | a tally sheet as computed |

Above the rows each file prints its own totals: number of tally sheets, total
of votes and registered voters. The reader recomputes all three from the rows
(`check_header`).

| Column | Used as |
| --- | --- |
| `CLAVE_CASILLA` | station identifier |
| one column per party and per combination of parties of a coalition | `counts.candidatures`, as on the tally sheet |
| `NO_REGISTRADAS` | `counts.other.unregistered` |
| `NULOS` | `counts.null` |
| `LISTA_NOMINAL` | `counts.registered`; absent for special stations, which have no voter list |
| PREP: `CONTABILIZADA` | only rows with `1` give a statement |
| PREP: `TOTAL_VOTOS_ASENTADO` | `extra.stated_total`: the total written on the sheet |
| PREP: `CODIGO_INTEGRIDAD` | `extra.image_sha256`: SHA-256 of the scanned sheet, as the file gives it |
| PREP: `TIPO_DOCUMENTO` | `extra.document`: which copy was captured |
| Cómputos: `OBSERVACIONES` | `extra.observation`, and `extra.canvass`: `recount` or `collation` |

`counts.blank` is always `0`: these tally sheets have no figure for blank
votes, and the core requires one.

A coalition's candidate receives the votes of each of its parties and of
every combination of them. Statements keep one figure per column.
`coalition_merge` gives the mapping from each column to the whole coalition,
in the form the core's `merge` expects (core, section 4.2).

## 4. Two acts

- A PREP row gives a statement with the default stage, `count`.
- A Cómputos row gives a statement with `stage: canvass`, which names the PREP
  statement of the same station in `supersedes` when there is one.

The core then works out, without anything specific to Mexico, the sum of what
the stations counted, the sum of what was left standing, and the stations
whose figures changed (core, section 5.2). `actasum mx replay` prints them and
adds two things from `extra.canvass` and from the coalition mapping: how many
changes come from a recount, and how many only move votes between columns of
one coalition.

A PREP statement is not the tally sheet: it is the INE's capture of one copy
of it. A difference between the two acts can be a capture error, a correction
or the result of counting the ballots again, and these files do not say which.

## 5. What gives no statement

| Rows | Why |
| --- | --- |
| PREP rows with `CONTABILIZADA` other than `1` | The PREP itself did not count them: no tally sheet at the cut, all figures empty or illegible, more votes than registered voters, or a sheet that could not be matched to a station |
| PREP rows counted with a cell marked `Sin dato` or `Ilegible` | See section 6, point 1. `--unreadable-as-zero` gives them a statement |
| PREP rows of the vote from abroad, one per state (section `0000`) | See section 6, point 3 |
| Cómputos rows with `-` in every vote cell | Package not received, or station not installed |

Every one of these is counted and reported by reason. None is dropped
silently.

## 6. What did not fit the core

The core was not changed for this profile. These are the cases where it had
to be worked around, in the order of how much they matter.

1. **A figure that could not be read is not a zero.** The PREP counts a tally
   sheet when at least one figure was captured, marks the others `Sin dato` or
   `Ilegible`, and adds them up as zero. The core only has non-negative
   integers, and treats a missing candidature as zero when it compares two
   statements. By default this profile gives such a sheet no statement.
2. **No blank-vote figure.** `counts.blank` is required by the core. It is
   written as `0`, which says something the tally sheet does not say.
3. **One earlier row, several later ones.** The PREP gives the vote from
   abroad as one row per state; the Cómputos file gives it per counting
   table, under other keys. The core replaces one statement by one statement.
   Kept as statements, those 32 rows would stand next to the rows that
   replaced them and their votes would be added twice, so they give none.
4. **Recount or collation.** Whether the ballots were counted again changes
   what a difference means. The core has one stage, `canvass`, for both; the
   distinction is kept under `extra`, where the verifier does not look.
5. **Official totals with only a grand total.** The files print the total of
   votes but no total per candidature other than the rows themselves. The
   core's official totals need figures per candidature, so `actasum verify`
   is not run; the header check is done by this profile.
6. **The total written on the sheet** includes null votes and votes for
   unregistered candidates. The core's `candidature_total` does not, so the
   figure is kept under `extra` and the verifier does not check it.
7. **A hash per tally-sheet image.** The core says image evidence will be
   specified later, so the hash is kept under `extra`.

## 7. Known gaps and unverified assumptions

1. The profile is named after the *Ley General de Instituciones y
   Procedimientos Electorales*, by analogy with the other profiles. That law
   has not been read. Section 1 rests on the INE's two manuals.
2. One election, one pair of files: the PREP as generated on 3 June 2024 at
   20:05 and the Cómputos as generated on 8 June 2024 at 20:30. Whether these
   are the last versions the INE published has not been checked.
3. No official result has been compared with either file. The results
   declared by the INE and those validated by the electoral court have not
   been read.
4. No tally-sheet image has been downloaded, so `extra.image_sha256` has not
   been checked against any image.
5. All rows are given `unit: station`, including counting tables for the vote
   from abroad, early voting and voting in pre-trial detention, because the
   files count each of them as a tally sheet.
6. Stations of type `V`, present only in the Cómputos file, are read like any
   other; what they are has not been looked up.
7. The INE's catalogue of stations dated 3 May 2024 lists 161,965 stations;
   the PREP expects 170,648 tally sheets and the Cómputos file 170,766. The
   difference has not been looked into.
