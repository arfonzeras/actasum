# Brazil profile (draft `br/codigo-eleitoral/v0.1`)

Status: **draft, run on one election**: the presidential election of
4 October 2026, first round, in every state and abroad (see
[`../findings/br-presidente-2026.md`](../findings/br-presidente-2026.md)).
Everything here was learnt from files of the Tribunal Superior Eleitoral
(TSE), the `leiame` files inside them, the pages of the TSE's open-data portal
and two TSE news articles. Nothing has been checked against the law, no
printed ballot-box report has been looked at, and no Brazilian organisation
has reviewed it.

This profile was written to find out whether a fourth country fits the core
format without changing it. It does not: the reader needed nothing the core
lacks, but the official totals needed one change, `count_as`, for votes an
authority counts as another item (section 6, point 1; core, sections 4.3
and 8).

## 1. How the count travels

According to a TSE news article of 6 October 2026, read through an automatic
extract:

1. Voting is electronic. When voting closes, each machine (*urna*) adds up the
   votes of its section and prints its report, the *boletim de urna* (BU),
   in five copies, with a QR code that lets anyone compare it with the
   results the TSE publishes.
2. The machine's result is transmitted, signed, to the Electoral Justice.
3. The TSE's totalisation system (SISTOT) adds up the reports and publishes
   the results.

The file this profile reads is the TSE's publication of the content of those
reports. It is not the printed report, nor the signed file the machine
produced. The TSE also publishes those signed files ("arquivos transmitidos
para totalização"), which this profile does not read yet.

Every statement is of the count (`stage: count`). These files carry no later
act on a section.

## 2. Identifiers

| Core field | Form | Example |
| --- | --- | --- |
| `election` | `br/<office>/<yyyy>-<mm>-<dd>` | `br/presidente/2026-10-04` |
| `constituency` | `br` | `br` |
| `station` | `br/<state>/<zone>/<section>` | `br/rr/0001/0585` |
| candidature code | the candidate's number on the ballot | `22` |

Both rounds fall in the same month, so the election identifier carries the
full date, taken from `DT_PLEITO`. A section number is unique within its
electoral zone, and a zone number within its state: the municipality is not
needed and is left out. The reader checks it: rows of one section that give
two municipalities are refused. In the 28 files of the first round of 2026
none did. Abroad, the state is `ZZ` and the identifier `br/zz/<zone>/<section>`.

Only the presidential election (`CD_CARGO_PERGUNTA` 1) is supported. The same
file carries the other offices of the same election day; their rows are
skipped.

Official totals given per state use `grouping: station-prefix/2`, so that a
statement counts towards `br/<state>` (`br/zz` abroad). National totals use
`grouping: constituency`, area `br`.

## 3. Source

`bweb_<round>_<UF>_<generated>.csv`, inside a ZIP file of the same name with a
`_leiame-boletimurnaweb.pdf`, one per state and round, from the TSE's
open-data portal, dataset "Resultados - 2026 - Boletim de Urna". The portal
lists a SHA-512 hash next to each ZIP file. The dataset page gives the licence
as "Creative Commons Atribuição".

According to the `leiame`: Latin 1; every field in quotes and separated by
semicolons; `#NULO#` (text) or `-1` (number) for a value that is blank in the
database. There is one row per section, office and recipient of votes
(*votável*). A recipient with no votes has no row, as far as the files show:
a section abroad in which nobody voted has no row at all.

The files are large: from 1 MB (abroad) to 1.4 GB (São Paulo) compressed,
and about six times that as CSV. The reader goes through each file once, row
by row, keeps only the rows of the office read, and hashes the CSV on the
way.

| Column | Used as |
| --- | --- |
| `SG_UF`, `NR_ZONA`, `NR_SECAO` | station identifier |
| `DT_PLEITO` | election identifier |
| `CD_TIPO_VOTAVEL` 1 (*Nominal*), `NR_VOTAVEL`, `QT_VOTOS` | `counts.candidatures`, by candidate number |
| `CD_TIPO_VOTAVEL` 2 (*Branco*) | `counts.blank` |
| `CD_TIPO_VOTAVEL` 3 (*Nulo*) | `counts.null` |
| `QT_APTOS` | `counts.registered` |
| `CD_MUNICIPIO` | not copied; the reader checks that a section has one |
| `QT_COMPARECIMENTO` | `extra.turnout`: the reader checks that the votes add up to it |
| `DS_SECOES_AGREGADAS` | `extra.aggregated_sections`: other sections whose voters used this machine |
| `CD_TIPO_URNA` | only 1 (*Apurada*) gives a statement |

Rows of one section must agree on every field that describes the section
(date, round, election, machine status, voters, turnout, aggregated
sections); otherwise the file is refused. A recipient type other than 1, 2
or 3 is refused: type 4 (*Legenda*, a vote for a party list) exists only for
proportional offices.

`SG_PARTIDO` is reported per candidate number, for reading, and is not part
of the statements.

### 3.1 Official totals

The official totals are the TSE's presidential totalisation reports,
`Relatorio_Resultado_Totalizacao_<year>_<UF>.zip`, one per state, abroad
(`ZZ`) and for the country (`BR`), each with one PDF per round.
`actasum br official` reads them:

```sh
actasum br official --report Relatorio_Resultado_Totalizacao_2026_AC.zip [--report ...] \
    --round 1 --states-out states.official.json --country-out brasil.official.json
```

It takes the PDF's own text layer with `pdftotext -layout` (Poppler), the
only tool outside Python's standard library this profile needs, and only for
this command. From each report it reads the summary, the votes per candidate
and annex III, the destination of each candidate's votes. A report whose
candidates do not add up to its valid votes, whose valid, null and blank
votes do not add up to its total, or whose two kinds of null votes do not add
up to its null votes, is refused. So is a destination other than *Válido*
and *Nulo técnico*, until one is seen. `count_as` is what annex III
declares; the national report has none, and takes the declarations of the
state reports only when their "nulos técnicos" add up to its own.

The official totals of the first round of 2026 in `docs/findings/official/`
were written by this command; its figures are the same as those first taken
from the same text by a script outside the repository.

## 4. Personal data

According to the `leiame`, the only personal data in the file are the names
of candidates (`NM_VOTAVEL`). It has no column for voters, polling-station
staff, signatures or identity numbers. The identifiers of the machine, its
load code and its memory card are technical.

Statements copy numbers and codes only: no name of a person or a place.

The file gives the registered voters of each section; the smallest section
in the first round of 2026 has 20. Those figures are already public.

## 5. What gives no statement

| Sections | Why |
| --- | --- |
| Machine status other than *Apurada* (*Não apurada*, *Anulada e apurada em separado*, *Anulada*, *Não instalada*) | Counted and reported by status, with their votes. None in the files of the first round of 2026 |
| A section with no row in the file | Nothing to read. The 41 sections abroad the report gives as not installed, and one section abroad counted by the system for manual counting in which, according to the report, nobody voted |

## 6. What did not fit the core

1. **Votes the totalisation gives another destination.** *Changed the
   core.* The machines accepted votes for number 28, whose candidate withdrew
   according to the official reports. The machines' reports give those votes
   to the candidate; the official reports count them as null ("nulo
   técnico"). The statement keeps what the machine's report says. Without a
   way to declare the reclassification, the verifier reported, in Roraima, a
   difference of 14 in three items (that candidature, null votes and the
   candidature total) and could not say why.

   The official totals now declare it: `count_as: {"28": "null"}`, taken
   from annex III of the reports. The verifier counts those votes as null
   before comparing, and its result always says so, with the votes and
   statements concerned (core, section 4.3).
2. **Official totals per state for a national office.** Solved without a
   change: `grouping: station-prefix/2`.
3. **Sections that vote on another section's machine.** One report covers
   them all and the file gives one row; the statement is of the main section
   and lists the others under `extra`.
4. **A section in which nobody voted.** The file has no row for it, so it
   gives no statement, and the verifier counts one section fewer than the
   official totals. Left as it is: the profile does not make up a statement
   the file does not give. It concerns one section abroad in 2026.

## 7. The second round

The second round is on 25 October 2026. Nothing is run before the TSE
publishes its files. When it does:

1. Download the ballot-box files of the second round,
   `bweb_2t_<UF>_<generated>.zip`, with their `.sha512`, taking the links
   from the dataset page (their names carry the time they were generated,
   unknown until then), and the 29 report ZIP files again. Check every
   SHA-512.
2. Check that each report ZIP has a presidential report of round 2
   (`_T2_PRESIDENTE.pdf`), and compare the hash of its round-1 report with
   the one recorded in the official totals of the first round. A changed
   report of round 1 is reported, not silently used.
3. `actasum br official --round 2`, then `actasum br replay` with the 28
   files. The election identifier comes from the files: `br/presidente/2026-10-25`.
4. What may differ from the first round, and is checked rather than
   assumed: the number of candidates; whether any annex III declares a
   destination other than *Válido*; sections with no row; and rows for
   other offices, such as governor where a state has a second round, which
   the reader skips.

## 8. Known gaps and unverified assumptions

1. **The law has not been read.** The profile is named after the *Código
   Eleitoral*, by analogy with the Colombia profile.
   - Articles read in the official text: **none**.
   - Nothing in this profile states what the law says. Section 1 rests on a
     TSE news article and says so.

   **Before publication:** read, in the official text in force on election
   day, the articles this profile relies on, and list them here.
2. One election, the first round of 2026: 28 files, all generated on
   5 October 2026 at 14:03:43 (Brasília time); the portal says the files are
   being updated.
3. The file read is the TSE's publication of the reports, not the reports
   themselves. The signed files the machines transmitted and the QR codes of
   the printed reports have not been read.
4. The only official totals compared are the TSE's own totalisation reports,
   per state and national, which say they are subject to change. They were
   read from the PDF's text layer.
5. The TSE's per-section results file for president is published for the
   whole country (`votacao_secao_2026_BR.zip`) and has not been read; the
   per-section file of Roraima does not include the presidential election.
6. Of the 31 sections the reports say were counted by the system for manual
   counting (*Sistema de Apuração*), 30 appear in the files like the others,
   as *Apurada*; the files do not tell them apart. The other one has no row
   (section 6, point 4).
