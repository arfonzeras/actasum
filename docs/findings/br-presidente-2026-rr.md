# Findings: Brazil, presidential election of 4 October 2026, first round, Roraima

**One state of 27, and the vote from abroad is not included.** The official
figures compared are those of the TSE's totalisation report for Roraima as
issued on election night, which the report itself says are subject to
change ("sujeito a modificações"). Nothing here is a result for Brazil.

Run of 12 October 2026 on two files published by the Tribunal Superior
Eleitoral (TSE), with `actasum` on branch `profile-br`:

| File | Generated | SHA-256 |
| --- | --- | --- |
| Ballot-box reports, `bweb_1t_RR_051020261403.zip` | 5 October 2026, 14:03:43 (Brasília) | ZIP `b2833692aaa3b51e814b223206cf98b66c9d1a9faeb75ae2f914ae308fe847e2`; CSV inside `40544177c4a72deb5533d0d9ba099de351837710ff1eda254d8c014c7e5b1741` |
| Totalisation report, `6257_RR_RORAIMA_2026_T1_PRESIDENTE.pdf`, inside `Relatorio_Resultado_Totalizacao_2026_RR.zip` | issued 4 October 2026, 20:13:45; result as of 20:05:17 | PDF `306c1fa7ff1637d5ac20d7df29314d7d543e2467346f8721dd15e4ba1c96005b`; ZIP `d3766b7ba1abba6ebbcb17b263f51ba60323af7c8f11b86f181c72f717f6ba26` |

The SHA-512 of the ballot-box ZIP file is the one the TSE publishes next to
it (`4cde1919…a8dc5c6`). No hash published for the totalisation report was
found.

```sh
actasum br replay --bu bweb_1t_RR_051020261403.zip \
    --official docs/findings/official/br-presidente-2026-10-04-rr.official.json
```

**Status: run, not verified.** Two publications of the same authority are
compared with each other. The first is the TSE's publication of the content
of the reports the voting machines printed; it is not those reports, nor the
signed files the machines transmitted. No printed report and no signed file
was looked at. What is checked is the sum of the reports, not that the
machines counted correctly.

## Summary

| Check | Result |
| --- | --- |
| Sections in the file, against the report | 1,519 and 1,519 |
| Registered voters, against the report | 401,521 and 401,521 |
| Voters who turned out, against the report | 332,772 and 332,772 |
| Sections whose votes add up to their turnout | All 1,519 |
| Blank votes | Equal: 2,618 |
| Each of the twelve candidatures in the report | Equal |
| Null votes | Equal, 4,609, with the 14 votes for number 28 counted as null, as the report declares |
| Votes for candidatures | Equal, 325,545, on the same terms |
| Verifier's answer | The official totals are the sum of the statements, with 14 votes of candidature 28 compared as null because the official totals declare it |

## The 14 votes for number 28

- The ballot-box file gives 14 votes to number 28, one in each of 14
  sections, as votes for a candidate (`Nominal`). The statements keep that.
- The report's annex III lists number 28 with *Renúncia* as its current
  status and *Nulo técnico* as the destination of its votes. Its summary
  gives 4,609 null votes: 4,595 "nulos na urna" and 14 "nulos técnicos".
- The official totals transcribed from the report declare
  `count_as: {"28": "null"}`. The verifier adds those 14 votes to null votes
  before comparing, and says so in its result:

  > br/rr: 14 votes of candidature 28, from 14 statements, compared as null,
  > because the official totals declare that they count them so

Without that declaration the same comparison gives three differences of 14
(null votes, votes for candidatures and candidature 28), which the TSE's own
report explains. The core could not express this before; `count_as` was
added for it (core, sections 4.3 and 8).

## The two sums

Every statement is of the count. These files carry no later act on a
section, so the sum of what the sections counted and the sum of what was
left standing are the same.

## Sections

The report lists 108 sections aggregated to others. The file gives 104
sections whose report covers other sections, 108 of them in all. All 1,519
machines have the status *Apurada*; the report gives none not installed,
annulled or not counted.

## Log

The 1,519 statements, in a log built on 12 October 2026: origin
`actasum/br/presidente/2026-10-04`, size 1,519, root
`hB7pXSl38j4clt/nd6dMo5UUU2MG2TtkuTT2L0hRZS4=`. The checkpoint is not signed
with a published key and no witness has cosigned it: it lets anyone repeat
the computation, and is not an attestation. The origin names the national
election; the log holds Roraima only.

## What this run says about the format

Brazil did not enter without changing the core. The reader needed nothing
new, but the official totals did: `count_as`, for votes an authority counts
as another item (core, section 8). The stopping rule is not met.

## What is not known

- Whether the files read are the last versions the TSE published. The
  report was issued on election night and says its result is subject to
  change; the portal says the files are being updated.
- Whether the file matches the signed files the machines transmitted, or the
  printed reports.
- The other 26 states and the vote from abroad.
- What the law says: no article has been read.
