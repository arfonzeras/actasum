# Brazil profile (draft `br/codigo-eleitoral/v0.1`)

Status: **draft, run on one state**: the presidential election of 4 October
2026, first round, in Roraima (see
[`../findings/br-presidente-2026-rr.md`](../findings/br-presidente-2026-rr.md)).
Everything here was learnt from files of the Tribunal Superior Eleitoral
(TSE), the `leiame` files inside them, the pages of the TSE's open-data portal
and two TSE news articles. Nothing has been checked against the law, no
printed ballot-box report has been looked at, and no Brazilian organisation
has reviewed it.

This profile was written to find out whether a fourth country fits the core
format without changing it. The reader needed nothing the core lacks. The
comparison with official totals shows one thing the core cannot express:
official totals that give the votes of a candidature another destination
(section 6, point 1). No change to the core has been made.

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
needed and is left out. In the Roraima file no section appears under more
than one municipality.

Only the presidential election (`CD_CARGO_PERGUNTA` 1) is supported. The same
file carries the other offices of the same election day; their rows are
skipped.

Official totals given per state use `grouping: station-prefix/2`, so that a
statement counts towards `br/<state>`.

## 3. Source

`bweb_<round>_<UF>_<generated>.csv`, inside a ZIP file of the same name with a
`_leiame-boletimurnaweb.pdf`, one per state and round, from the TSE's
open-data portal, dataset "Resultados - 2026 - Boletim de Urna". The portal
lists a SHA-512 hash next to each ZIP file. The dataset page gives the licence
as "Creative Commons Atribuição".

According to the `leiame`: Latin 1; every field in quotes and separated by
semicolons; `#NULO#` (text) or `-1` (number) for a value that is blank in the
database. There is one row per section, office and recipient of votes
(*votável*).

| Column | Used as |
| --- | --- |
| `SG_UF`, `NR_ZONA`, `NR_SECAO` | station identifier |
| `DT_PLEITO` | election identifier |
| `CD_TIPO_VOTAVEL` 1 (*Nominal*), `NR_VOTAVEL`, `QT_VOTOS` | `counts.candidatures`, by candidate number |
| `CD_TIPO_VOTAVEL` 2 (*Branco*) | `counts.blank` |
| `CD_TIPO_VOTAVEL` 3 (*Nulo*) | `counts.null` |
| `QT_APTOS` | `counts.registered` |
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

## 4. Personal data

According to the `leiame`, the only personal data in the file are the names
of candidates (`NM_VOTAVEL`). It has no column for voters, polling-station
staff, signatures or identity numbers. The identifiers of the machine, its
load code and its memory card are technical.

Statements copy numbers and codes only: no name of a person or a place.

The file gives the registered voters of each section; the smallest section
in Roraima has 32. Those figures are already public.

## 5. What gives no statement

| Sections | Why |
| --- | --- |
| Machine status other than *Apurada* (*Não apurada*, *Anulada e apurada em separado*, *Anulada*, *Não instalada*) | Counted and reported by status, with their votes. None in the Roraima file |

## 6. What did not fit the core

1. **Votes the totalisation gives another destination.** In Roraima the
   machines accepted votes for number 28, whose candidate withdrew according
   to the official report. The machines' reports give those votes to the
   candidate; the official report counts them as null ("nulo técnico"). The statement keeps what the machine's report says. The
   verifier then reports a difference in three items (that candidature, null
   votes and the candidature total), the same in size, and cannot say why.
   In Roraima this is 14 votes for number 28.

   **Proposed change to the core, not made:** let official totals say that
   they count the votes of a candidature as null, as `merge` already lets
   them say that they count it under another candidature. The verifier would
   then add up the statements the same way before comparing, and report the
   reclassification instead of a difference. Awaiting a decision.
2. **Official totals per state for a national office.** Solved without a
   change: `grouping: station-prefix/2`.
3. **Sections that vote on another section's machine.** One report covers
   them all and the file gives one row; the statement is of the main section
   and lists the others under `extra`.

## 7. Known gaps and unverified assumptions

1. **The law has not been read.** The profile is named after the *Código
   Eleitoral*, by analogy with the Colombia profile.
   - Articles read in the official text: **none**.
   - Nothing in this profile states what the law says. Section 1 rests on a
     TSE news article and says so.

   **Before publication:** read, in the official text in force on election
   day, the articles this profile relies on, and list them here.
2. One state of 27, and no vote from abroad (`ZZ`). One file, generated on
   5 October 2026 at 14:03:43 (Brasília time); the portal says the files are
   being updated.
3. The file read is the TSE's publication of the reports, not the reports
   themselves. The signed files the machines transmitted and the QR codes of
   the printed reports have not been read.
4. The only official totals compared are the TSE's own totalisation report
   for the state, issued on election night and marked as subject to change.
5. The TSE's per-section results file for president is published for the
   whole country (`votacao_secao_2026_BR.zip`) and has not been read; the
   per-section file of Roraima does not include the presidential election.
