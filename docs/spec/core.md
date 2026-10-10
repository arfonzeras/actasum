# Core specification (draft v0.1)

Status: **draft**. Field names and rules may change without notice until v1.0.

This document defines two JSON documents and one procedure:

1. the **statement**, which records what one polling station's tally sheet says;
2. the **official totals**, which record what the electoral authority published;
3. the **verification procedure**, which recomputes totals from statements and
   compares them with the official totals.

Everything that depends on a country's law lives in a **profile**
(for example [`profile-es.md`](profile-es.md)). The core is country-neutral.

The key words MUST, SHOULD and MAY are used as in RFC 2119.

## 1. Scope

In scope: the result recorded at a polling station after the count, and its
aggregation up to the constituency.

Out of scope: how votes are cast, voter identity, and whether the count at the
polling station was itself correct. A statement faithfully copied from a wrong
tally sheet is still wrong.

Not yet specified (planned for later versions): signatures and submitter
credentials, the append-only log and its witnesses, several independent
statements for the same station, and image evidence.

## 2. Canonical JSON

Statements are hashed, so their byte form must be deterministic.

- Allowed values: objects, arrays, strings, integers, `true`, `false`, `null`.
  Floating-point numbers MUST NOT appear.
- Object keys are sorted by Unicode code point.
- No whitespace between tokens.
- The text is encoded as UTF-8, without escaping non-ASCII characters.

This is a deliberately small subset of what RFC 8785 (JCS) covers. Adopting
RFC 8785 outright is an open question.

## 3. Statement

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `spec` | string | yes | Always `tallylog/statement/v0.1` |
| `profile` | string | yes | Profile and version that define the remaining fields |
| `election` | string | yes | Election identifier, defined by the profile |
| `station` | string | yes | Polling-station identifier, defined by the profile. Stable and unique within the election |
| `constituency` | string | yes | Constituency whose total this station counts towards |
| `unit` | string | no | `station` (default) or `aggregate`. An aggregate carries votes but is not a polling station, for example overseas votes counted centrally. Omitted when it is `station` |
| `counts.blank` | integer | yes | Blank votes |
| `counts.null` | integer | yes | Null (spoilt) votes |
| `counts.candidatures` | object | yes | Votes per candidature: candidature code → integer |
| `counts.registered` | integer | no | Registered voters at the station |
| `counts.candidature_total` | integer | no | Total votes for candidatures, when the sheet states it separately |
| `evidence` | object | no | Where the figures come from (section 3.2) |
| `extra` | object | no | Profile-specific fields that do not take part in verification |

All counts are non-negative integers.

### 3.1 Statement identifier

The identifier of a statement is `sha256:` followed by the lowercase
hexadecimal SHA-256 of its canonical JSON form.

Two parties that transcribe the same tally sheet identically, with the same
`evidence` and `extra`, obtain the same identifier.

### 3.2 Evidence

`evidence.kind` names the source of the figures. v0.1 defines one kind:

- `official-dataset`: the statement was derived from a dataset published by the
  electoral authority. `evidence.sha256` SHOULD carry the hash of that dataset.

A later version will define `image`, for a photograph of the tally sheet.

## 4. Official totals

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `spec` | string | yes | Always `tallylog/official-totals/v0.1` |
| `profile` | string | yes | Profile and version |
| `election` | string | yes | Election identifier |
| `constituencies` | object | yes | Constituency identifier → totals |
| `source` | object | no | Where the totals come from |

Totals for one constituency:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `blank` | integer | yes | Blank votes |
| `null` | integer | yes | Null votes |
| `candidatures` | object | yes | Candidature code → votes |
| `candidature_total` | integer | no | Total votes for candidatures |
| `stations` | integer | no | Number of polling stations |

## 5. Verification procedure

Input: a set of statements and one official-totals document.

1. Every statement MUST belong to the election of the official totals.
   Otherwise verification stops with an error.
2. v0.1 expects **exactly one statement per station**. A second statement for
   the same station stops verification with an error.
3. For each statement, the verifier checks internal consistency and records
   an *issue* (it does not stop) when:
   - `candidature_total` is present and differs from the sum of `candidatures`;
   - `registered` is present and is lower than blank + null + candidature votes.
4. The verifier sums `blank`, `null` and each candidature's votes per
   constituency, and counts the statements whose `unit` is `station`.
   Aggregates add their votes but are not counted as stations.
5. For every constituency present on both sides it compares station count,
   blank, null, candidature total and each candidature. A candidature missing
   on one side counts as zero. Each mismatch is a *difference*.
6. A constituency present on only one side is a *gap*.

The result is **matching** only if there are no differences and no gaps.
Station issues are reported but do not change the result.

### 5.1 What a result means

- *Matching* means: the published constituency totals are the sum of these
  statements. It says nothing about whether the statements are true.
- A *difference* means the two do not add up. It does not say why. Lawful
  corrections during the official canvass, transcription slips and fraud all
  produce differences. Implementations MUST present differences in neutral
  language and MUST NOT label them as fraud.

## 6. Open questions

- Adopt RFC 8785 for canonicalization?
- Reuse the NIST Election Results Common Data Format (SP 1500-100) instead of
  a new vocabulary? Not yet evaluated outside the United States.
- How to express several conflicting statements for one station, and the
  station states (no data, single capture, confirmed, in conflict).
- A privacy rule for very small stations where publishing a result reveals
  individual votes.
