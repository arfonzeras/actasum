# Findings: Brazil, presidential election of 25 October 2026, second round

**The official figures compared are those of the TSE's totalisation reports,
which each say their result is subject to change ("sujeito a
modificações").** The reports of the states and abroad were issued on the
evening and night of 25 October 2026, the national report at 23:28:44 that
night. The first round is in [`br-presidente-2026.md`](br-presidente-2026.md).

Run of 28 October 2026 on files published by the Tribunal Superior
Eleitoral (TSE), with `actasum` on branch `profile-br-2t`:

- 28 ballot-box report files, `bweb_2t_<UF>_261020260742.zip`: the 26 states,
  the Distrito Federal and the vote from abroad (`ZZ`), all generated on
  26 October 2026 at 07:42:38 (Brasília). The SHA-512 of each ZIP file equals
  the one the TSE publishes next to it; the 28 hashes are in
  [`br-presidente-2026-2t.sha512`](br-presidente-2026-2t.sha512).
- 29 presidential totalisation reports of round 2,
  `6258_<UF>_..._T2_PRESIDENTE.pdf`, inside the same
  `Relatorio_Resultado_Totalizacao_2026_<UF>.zip` files as in the first
  round, which now hold one report per round. Their hashes, issue times and
  the time of their result are in the two official-totals files below.

```sh
actasum br official --report Relatorio_Resultado_Totalizacao_2026_AC.zip [--report ... 29 in all] \
    --round 2 --states-out states.official.json --country-out brasil.official.json

actasum br replay --bu bweb_2t_AC_261020260742.zip [--bu ... one per state and ZZ] \
    --official docs/findings/official/br-presidente-2026-10-25-states.official.json \
    --official docs/findings/official/br-presidente-2026-10-25-brasil.official.json
```

The first command, run again on the 29 report files, writes the two
official-totals files byte for byte. On the machine used, the second took
74 seconds and 1.2 GB of memory; the 28 files hold 2.09 million rows, of
which 1.93 million are for president.

**Status: run, not verified.** Two publications of the same authority are
compared with each other. The ballot-box files are the TSE's publication of
the content of the reports the voting machines printed; they are not those
reports, nor the signed files the machines transmitted, and none of those
was looked at. What is checked is the sum of the reports, not that the
machines counted correctly.

## Summary

| Check | Result |
| --- | --- |
| Statements: sections with a report in the files | 499,205 |
| Each of the 28 reports of the states and abroad | Equal in every figure of votes; abroad, two sections fewer (below) |
| The national report | Equal in every figure of votes; two sections fewer, the same two |
| Sections whose votes add up to their turnout | All 499,205 |
| The 28 reports of the states and abroad, added up | Equal to the national report in every figure, sections included |
| Votes the official totals count as another item | None: annex III gives both candidates *Válido*, and the reports count no "nulos técnicos" |

## Votes

The national figures, as the statements add them up. Each equals the national
report's.

| Number | Party in the file | Votes |
| --- | --- | --- |
| 13 | PT | 64,256,232 |
| 22 | PL | 59,826,041 |
| Votes for candidatures | | 124,082,273 |
| Null | | 2,723,305 |
| Blank | | 1,430,496 |
| Total | | 128,236,074 |

The total equals the voters who turned out, as the files give them per
section and the national report gives them.

## By state

| State | Sections in the file | Sections that functioned, report | Votes |
| --- | --- | --- | --- |
| AC | 2,270 | 2,270 | 453,654 |
| AL | 7,101 | 7,101 | 1,951,632 |
| AM | 8,157 | 8,157 | 2,192,059 |
| AP | 1,914 | 1,914 | 429,975 |
| BA | 35,476 | 35,476 | 9,422,047 |
| CE | 23,765 | 23,765 | 6,024,843 |
| DF | 6,969 | 6,969 | 1,868,280 |
| ES | 9,844 | 9,844 | 2,409,214 |
| GO | 15,686 | 15,686 | 4,047,280 |
| MA | 18,093 | 18,093 | 4,127,771 |
| MG | 52,062 | 52,062 | 13,044,203 |
| MS | 7,106 | 7,106 | 1,594,460 |
| MT | 8,287 | 8,287 | 2,085,334 |
| PA | 20,827 | 20,827 | 4,989,573 |
| PB | 10,712 | 10,712 | 2,743,560 |
| PE | 21,418 | 21,418 | 6,126,467 |
| PI | 10,225 | 10,225 | 2,239,830 |
| PR | 27,142 | 27,142 | 7,059,339 |
| RJ | 37,675 | 37,675 | 10,077,449 |
| RN | 8,115 | 8,115 | 2,232,823 |
| RO | 4,698 | 4,698 | 988,489 |
| RR | 1,519 | 1,519 | 308,597 |
| RS | 27,547 | 27,547 | 6,889,638 |
| SC | 17,326 | 17,326 | 4,762,303 |
| SE | 5,923 | 5,923 | 1,466,659 |
| SP | 103,656 | 103,656 | 27,364,389 |
| TO | 4,384 | 4,384 | 954,763 |
| ZZ (abroad) | 1,308 | 1,310 | 381,443 |

In every state and abroad, blank votes, null votes and the votes of each
candidature equal the report's.

Six files also carry rows of another office, which the reader skips: AC, AM,
DF, ES, RN and TO. Abroad, two rows have no office at all (next section).

## Two sections abroad

The report for abroad gives 1,310 sections that functioned; the statements
are 1,308. The two missing are sections 0091 and 0443 of zone 0001 abroad.
The report's annex I lists both with "Sistema de apuração" as their
occurrence, with 72 and 30 registered voters and 0 voters who turned out.

Unlike the first round, when section 0091 had no row, the file has one row
for each, and it is not a row for president: `CD_CARGO_PERGUNTA` is `-1`
and the office, the party, the recipient type and the recipient are
`#NULO#`, with 0 votes. The rest of the row describes the section: machine
status `Apurada`, 72 and 30 registered voters (`QT_APTOS`), turnout 0. The
reader reads only the rows of office 1, so the two sections give no
statement. Both rows give the same machine, load codes and memory card
(`NR_URNA_EFETIVADA` 1808076); the file does not say why.

The verifier reports this as a difference of two sections, abroad and in the
national count, and nothing else differs: no vote is missing. The registered
voters of the statements add up to 158,744,977; the two sections missing
have 102.

The national report counts 29 sections by that system, all abroad. The other
27 are in the file among the sections it marks as *Apurada*, with their
votes. Annex I also lists one section abroad, 3869 of zone 0001, with the
occurrence "BU gerado por RED em urna de seção"; it is in the file and its
statement adds up to its turnout, 208.

## Reports of the first round, issued again

The report ZIP files downloaded for this run also hold the reports of the
first round. 25 of those are the same files, by SHA-256, as the ones the
first round's official totals record. The other 4 were issued again:

| State | Issued first | Issued again | Result "as of", both |
| --- | --- | --- | --- |
| MG | 05/10/2026 00:52:55 | 15/10/2026 19:14:58 | 05/10/2026 - 00:45:39 |
| RN | 04/10/2026 23:03:59 | 24/10/2026 12:07:46 | 04/10/2026 - 22:50:36 |
| RO | 04/10/2026 19:52:34 | 16/10/2026 15:24:44 | 04/10/2026 - 19:49:42 |
| RS | 04/10/2026 21:15:52 | 16/10/2026 11:51:18 | 04/10/2026 - 21:04:14 |

Every figure the official totals take from them is the same, and so is
`count_as`. Their text, taken with `pdftotext -layout` and compared line by
line without regard to spacing or order, differs from the first issue only
in:

- the issue date and time;
- annex III: the last column, the candidate's situation in the totalisation,
  empty in the first issue, now says "Não eleito" or "2º turno";
- annex V, special occurrences of machines: every occurrence "Contingência"
  now says "Apurada" (18 in RO, 33 in RN, 197 in RS, 201 in MG);
- in MG and RN, the spelling of the signatory's title in the closing text.

The reader of the reports did not foresee a filled last column in annex III.
On the 4 reports issued again it read no destination and gave an empty
`count_as` without saying so. It now reads the column, and refuses a report whose annex III
names a number whose destination it cannot read, or that counts "nulos
técnicos" while every number in annex III is *Válido* (profile, section 3.1).
The first round's official totals, written again from the original reports,
are the same byte for byte; written from the 4 issued again, they have the
same figures and `count_as`, and other hashes and issue times.

All 29 ZIP files now have other hashes than the ones the first round
recorded, because each now also holds the report of round 2.

## The download

- The page of the dataset in Portuguese and the portal's API did not list
  the files of the second round; the page in English
  (`dadosabertos.tse.jus.br/en/dataset/...`) did.
- That page listed 55 links instead of 56: the ZIP file of Roraima was
  missing, while its `.sha512` was listed. It was downloaded from the same
  address without `.sha512`, and its SHA-512 equals the published one.

## The two sums

Every statement is of the count. These files carry no later act on a
section, so the sum of what the sections counted and the sum of what was
left standing are the same.

## Sections

16,142 sections have a report that covers other sections as well; together
they list 17,931 aggregated sections, the number the national report gives,
the same as in the first round. The report gives 41 sections abroad as not
installed; they have no rows in the file.

The smallest section has 20 registered voters. That figure is already
public in the files.

## Log

The 499,205 statements, in a log built on 28 October 2026: origin
`actasum/br/presidente/2026-10-25`, size 499,205, root
`z4RPmZHISbTEvMWGONrk/BYTGrH/X6w8te5hsZtgR3M=`. The checkpoint is not signed
with a published key and no witness has cosigned it: it lets anyone repeat
the computation, and is not an attestation.

## What this run says about the format

The second round needed no change to the core. It needed one change to the
profile, in the reader of the reports, for a layout of annex III first seen
in reports of the first round issued again. The stopping rule is not met:
Brazil changed the core in the first round.

## What is not known

- Whether the files read are the last versions the TSE published, and
  whether the results changed after the reports were issued.
- Whether the files match the signed files the machines transmitted, or the
  printed reports.
- Why the two sections in which nobody voted have a row with no office in
  this round and had none (section 0091) in the first, and why both rows give
  the same machine.
- Why the report for abroad was issued on 25 October 2026 at 22:15:34 while
  it gives its result "as of" 26 October 2026 at 09:05:23, later than the
  national report's (25 October, 23:26:38). The figures of both agree. The
  same happened in the first round.
- Why the registered voters of every state and abroad differ from those of
  the first round's reports, while the national figure, 158,745,502, is the
  same. The verifier does not compare registered voters.
- Why 4 reports of the first round were issued again, and why the portal
  listed the files as it did.
- What the law says: no article has been read.
