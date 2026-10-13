# Findings: Brazil, presidential election of 4 October 2026, first round

**The official figures compared are those of the TSE's totalisation reports,
which each say their result is subject to change ("sujeito a
modificações").** The reports of the states and abroad were issued between
the night of 4 October and the morning of 5 October 2026; the national
report on 7 October. The second round is on 25 October 2026 and is not
covered.

Run of 13 October 2026 on files published by the Tribunal Superior
Eleitoral (TSE), with `actasum` on branch `profile-br`:

- 28 ballot-box report files, `bweb_1t_<UF>_051020261403.zip`: the 26 states,
  the Distrito Federal and the vote from abroad (`ZZ`), all generated on
  5 October 2026 at 14:03:43 (Brasília). The SHA-512 of each ZIP file equals
  the one the TSE publishes next to it.
- 29 presidential totalisation reports, `6257_<UF>_..._T1_PRESIDENTE.pdf`
  inside `Relatorio_Resultado_Totalizacao_2026_<UF>.zip`: one per state and
  abroad, and the national one. Their hashes, issue times and the time of
  their result are in the two official-totals files below.

```sh
actasum br replay --bu bweb_1t_AC_051020261403.zip [--bu ... one per state and ZZ] \
    --official docs/findings/official/br-presidente-2026-10-04-states.official.json \
    --official docs/findings/official/br-presidente-2026-10-04-brasil.official.json
```

On the machine used, the run took 11 minutes and 1.7 GB of memory; the 28
files hold 67.9 million rows, of which 3.8 million are for president.

**Status: run, not verified.** Two publications of the same authority are
compared with each other. The ballot-box files are the TSE's publication of
the content of the reports the voting machines printed; they are not those
reports, nor the signed files the machines transmitted, and none of those
was looked at. What is checked is the sum of the reports, not that the
machines counted correctly.

## Summary

| Check | Result |
| --- | --- |
| Statements: sections with a report in the files | 499,206 |
| Each of the 28 reports of the states and abroad | Equal in every figure of votes; abroad, one section fewer (below) |
| The national report | Equal in every figure of votes; one section fewer, the same one |
| Sections whose votes add up to their turnout | All 499,206 |
| The 28 reports of the states and abroad, added up | Equal to the national report in every figure, sections included |
| Votes for number 28 | 5,246, in 5,145 sections, compared as null because the official totals declare it (below) |

## Votes

The national figures, as the statements add them up. Each equals the national
report's.

| Number | Party in the file | Votes |
| --- | --- | --- |
| 22 | PL | 56,104,503 |
| 13 | PT | 53,879,538 |
| 70 | AVANTE | 3,448,569 |
| 14 | MISSÃO | 2,675,887 |
| 55 | PSD | 2,605,148 |
| 30 | NOVO | 326,488 |
| 80 | UP | 122,911 |
| 16 | PSTU | 43,103 |
| 27 | DC | 40,043 |
| 21 | PCB | 22,693 |
| 35 | DEMOCRATA | 16,881 |
| 29 | PCO | 15,024 |
| Votes for candidatures | | 119,300,788 |
| Null, including the 5,246 for number 28 | | 3,674,249 |
| Blank | | 2,300,798 |
| Total | | 125,275,835 |

## By state

| State | Sections in the file | Sections that functioned, report | Votes |
| --- | --- | --- | --- |
| AC | 2,270 | 2,270 | 488,330 |
| AL | 7,101 | 7,101 | 1,938,428 |
| AM | 8,157 | 8,157 | 2,234,549 |
| AP | 1,914 | 1,914 | 476,562 |
| BA | 35,476 | 35,476 | 9,053,601 |
| CE | 23,765 | 23,765 | 5,910,471 |
| DF | 6,969 | 6,969 | 1,831,396 |
| ES | 9,844 | 9,844 | 2,352,282 |
| GO | 15,686 | 15,686 | 3,971,587 |
| MA | 18,093 | 18,093 | 4,160,343 |
| MG | 52,062 | 52,062 | 12,637,274 |
| MS | 7,106 | 7,106 | 1,541,220 |
| MT | 8,287 | 8,287 | 2,052,133 |
| PA | 20,827 | 20,827 | 5,066,504 |
| PB | 10,712 | 10,712 | 2,683,988 |
| PE | 21,418 | 21,418 | 5,911,062 |
| PI | 10,225 | 10,225 | 2,240,883 |
| PR | 27,142 | 27,142 | 6,841,457 |
| RJ | 37,675 | 37,675 | 9,859,802 |
| RN | 8,115 | 8,115 | 2,171,013 |
| RO | 4,698 | 4,698 | 991,080 |
| RR | 1,519 | 1,519 | 332,772 |
| RS | 27,547 | 27,547 | 6,702,903 |
| SC | 17,326 | 17,326 | 4,648,159 |
| SE | 5,923 | 5,923 | 1,439,082 |
| SP | 103,656 | 103,656 | 26,431,992 |
| TO | 4,384 | 4,384 | 965,196 |
| ZZ (abroad) | 1,309 | 1,310 | 341,766 |

In every state and abroad, blank votes, null votes and the votes of each
candidature equal the report's.

## The 5,246 votes for number 28

- The ballot-box files give 5,246 votes to number 28, in 5,145 sections, as
  votes for a candidate (`Nominal`). The statements keep that.
- Each of the 28 reports of the states and abroad lists number 28 in annex
  III with *Nulo técnico* as the destination of its votes, gives it no figure
  in annex IV, and counts that many "nulos técnicos" among its null votes.
  Their "nulos técnicos" add up to the national figure, 5,246. The national
  report has no annex III.
- The official totals declare `count_as: {"28": "null"}`, and the verifier
  says so in its result, per state and for the country. For the country:

  > br: 5246 votes of candidature 28, from 5145 statements, compared as
  > null, because the official totals declare that they count them so

## One section abroad

The report for abroad gives 1,310 sections that functioned; the file has
1,309. The one missing is section 0091 of zone 0001 abroad. The report's
annex I lists it with 72 registered voters, 0 voters who turned out, and
"Sistema de apuração" as its occurrence: it was counted by the system for
manual counting, not by an electronic machine. The file has no row for it.
The file has one row per recipient of votes, so a section in which nobody
voted would have none; that is consistent with the report's figures, but the
file does not say so.

The verifier reports this as a difference of one section, abroad and in the
national count, and nothing else differs: no vote is missing. It is also why
the registered voters of the statements, 158,745,007, are 72 fewer than the
report's voters in sections that functioned, 158,745,079.

The national report counts 31 sections by that system: 29 abroad and 2 in
Minas Gerais. The other 30 are in the files, among the sections the files
mark as *Apurada*.

## The two sums

Every statement is of the count. These files carry no later act on a
section, so the sum of what the sections counted and the sum of what was
left standing are the same.

## Sections

16,142 sections have a report that covers other sections as well; together
they list 17,931 aggregated sections, the number the national report gives.
The report gives 41 sections abroad as not installed; they have no rows in
the file.

The smallest section has 20 registered voters. That figure is already
public in the files.

## Log

The 499,206 statements, in a log built on 13 October 2026: origin
`actasum/br/presidente/2026-10-04`, size 499,206, root
`HMr/oOLjGZGzuzLrlMg2G3gi1WzdlL1FZ5geIXCzBBs=`. The checkpoint is not signed
with a published key and no witness has cosigned it: it lets anyone repeat
the computation, and is not an attestation.

## What this run says about the format

Brazil did not enter without changing the core: the official totals needed
`count_as` (core, section 8). The reader needed nothing new from the core.
The stopping rule is not met.

## What is not known

- Whether the files read are the last versions the TSE published, and
  whether the results changed after the reports were issued.
- Whether the files match the signed files the machines transmitted, or the
  printed reports.
- Why the report for abroad was issued on 4 October 2026 at 23:03:02 while
  it gives its result "as of" 5 October 2026 at 09:19:47. The report prints
  both and does not explain it.
- What the law says: no article has been read.
- The second round.
