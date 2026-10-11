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
| `spec` | string | yes | Always `actasum/statement/v0.1` |
| `profile` | string | yes | Profile and version that define the remaining fields |
| `election` | string | yes | Election identifier, defined by the profile |
| `station` | string | yes | Polling-station identifier, defined by the profile. Stable and unique within the election |
| `constituency` | string | yes | Constituency whose total this station counts towards |
| `unit` | string | no | `station` (default) or `aggregate`. An aggregate carries votes but is not a polling station, for example overseas votes counted centrally. Omitted when it is `station` |
| `stage` | string | no | The act the figures come from (section 3.3): `count` (default), `canvass`, `ruling` or `rerun`. Omitted when it is `count` |
| `supersedes` | string | no | Identifier of the statement this one replaces (section 3.3) |
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

`evidence.kind` names the class of source behind the figures. Kinds defined
so far:

- `official-dataset`: the statement was derived from a dataset published by the
  electoral authority. `evidence.sha256` SHOULD carry the hash of that dataset.
- `official-publication`: the figures come from a document published by an
  electoral board, a court or an official gazette.
- `party-copy`: the figures come from the copy of a record handed to a
  candidature or its agents.
- `observer-capture`: the figures were captured by an observer from the
  posted or read-out record.

`evidence` records what the source is, not how much it is to be trusted. The
format carries no confidence score: whether a station's figures are
confirmed, in conflict or changed is worked out by the verifier from the
statements themselves (section 5).

A later version will define how a photograph of the tally sheet is attached.

### 3.3 Several statements for one station

A station may have more than one statement, for two different reasons.

- **Several captures of the same act.** Two witnesses transcribe the same
  tally sheet, or a dataset and a photograph say the same thing. These
  statements have the same `stage` and must give the same figures.
- **Successive acts.** The count at the station may lawfully be followed by a
  correction in the general canvass, by a resolution of a board or a court,
  or by a repeated vote. These statements have different `stage` values and
  may give different figures.

`stage` says which act the figures come from:

| `stage` | Act |
| --- | --- |
| `count` | The count at the polling station, as recorded on its tally sheet |
| `canvass` | The general canvass carried out by an electoral board |
| `ruling` | A resolution of an electoral board or a court |
| `rerun` | A vote held again |

A statement of a later act SHOULD name the statement it replaces in
`supersedes`. The earlier statement is never altered or removed: both stay in
the record, and the difference between them is itself information.

Profiles say which acts exist under their law and who may be the source of
each.

## 4. Official totals

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `spec` | string | yes | Always `actasum/official-totals/v0.1` |
| `profile` | string | yes | Profile and version |
| `election` | string | yes | Election identifier |
| `level` | string | no | What an area is, for display: `constituency` (default), `municipality`… |
| `grouping` | string | no | How statements are assigned to areas (section 4.1). Default `constituency` |
| `areas` | object | yes | Area identifier → totals |
| `merge` | object | no | Candidature code → the code these totals report it under (section 4.2) |
| `source` | object | no | Where the totals come from |

Totals for one area:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `blank` | integer | yes | Blank votes |
| `null` | integer | yes | Null votes |
| `candidatures` | object | yes | Candidature code → votes |
| `candidature_total` | integer | no | Total votes for candidatures |
| `stations` | integer | no | Number of polling stations |

### 4.1 Grouping

The result of an election is decided per constituency, but authorities often
publish totals at other levels too. Comparing at a lower level shows *where*
station sums and published totals part ways.

- `constituency`: a statement counts towards its own `constituency`.
- `station-prefix/N`: a statement counts towards the area named by the first
  N `/`-separated parts of its `station` identifier. Profiles define
  hierarchical station identifiers so that this is meaningful.

An aggregate (section 3, `unit`) has no place of its own below the
constituency. Under a `station-prefix/N` grouping it is kept when the official
totals have an area for it, and otherwise left out and counted as such. An
overseas row counts towards its province; it counts towards no municipality.

### 4.2 Merged candidatures

An authority may add up several candidatures under one code at a given level,
for example one list that runs under different names in different regions.
When `merge` is present, the verifier replaces each candidature code of a
statement by the code `merge` gives for it, if any, before adding up. Statements
themselves keep the code that appears on the tally sheet.

## 5. Verification procedure

Input: a set of statements and one official-totals document. Below, *area*
means whatever the document's `grouping` defines.

1. Every statement MUST belong to the election of the official totals.
   Otherwise verification stops with an error.
2. The verifier decides which statements enter the sums (section 5.2) and
   then runs steps 3 to 6 twice: once with what the stations counted and
   once with what was left standing.
3. For each statement, the verifier checks internal consistency and records
   an *issue* (it does not stop) when:
   - `candidature_total` is present and differs from the sum of `candidatures`;
   - `registered` is present and is lower than blank + null + candidature votes.
4. The verifier sums `blank`, `null` and each candidature's votes per area,
   and counts the statements whose `unit` is `station`. Aggregates add their
   votes but are not counted as stations.
5. For every area present on both sides it compares station count, blank,
   null, candidature total and each candidature. A candidature missing on one
   side counts as zero. Each mismatch is a *difference*.
6. An area present on only one side is a *gap*.

A sum is **matching** only if there are no differences and no gaps. Station
issues are reported but do not change the result.

The verifier reports both sums and says which of them the official totals
coincide with: both, what the stations counted, what was left standing, or
neither. It MUST NOT show one sum without the other when they differ, and it
makes no assumption about which of the two an official file contains.

### 5.2 Which statements enter the sums

Statements with the same identifier are one statement.

1. Statements are grouped by station and `stage`. A group whose statements
   all give the same blank votes, null votes and votes per candidature (a
   candidature with zero votes and a missing one being the same) counts as
   one. A group whose statements differ is an act **in conflict**: it enters
   no sum and is listed. Contradictory copies count for nothing.
2. **As counted**: for each station, its `count` act, unless in conflict.
3. An act is *replaced* when any statement names one of its statements in
   `supersedes`. **As standing**: for each station, the one act that is not
   replaced, unless it is in conflict.
4. A station with more than one act not replaced is **undetermined**: it is
   left out of the standing sum and listed. The format does not guess an
   order between acts that do not refer to each other.
5. The verifier lists the stations whose standing figures differ from the
   count, item by item, with the act and the class of source; the stations
   that have a later act but no statement of the count; and the statements
   whose `supersedes` names a statement that was not provided.

The overall result is positive only if the official totals coincide with at
least one sum and no station is in conflict or undetermined.

When every station has a single statement of its count, the two sums are the
same sum.

### 5.1 What a result means

- *Matching* means: the published totals are the sum of these
  statements. It says nothing about whether the statements are true.
- A *difference* means the two do not add up. It does not say why. Lawful
  corrections during the official canvass, transcription slips and fraud all
  produce differences. Implementations MUST present differences in neutral
  language and MUST NOT label them as fraud.

## 6. Open questions

- Adopt RFC 8785 for canonicalization?
- Reuse the NIST Election Results Common Data Format (SP 1500-100) instead of
  a new vocabulary? Not yet evaluated outside the United States.
- Several statements per station are defined in sections 3.3 and 5.2. Still
  open there: whether `supersedes` is enough to order acts or a date is
  needed too; what to do with acts that do not refer to each other, which
  are left undetermined for now; how many agreeing captures from unrelated
  sources make a station *confirmed*; and whether these additions call for a
  new version of the `spec` string. They do not change the identifier of any
  statement written before.
- A privacy rule for very small stations where publishing a result reveals
  individual votes.
