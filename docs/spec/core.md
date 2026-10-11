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
credentials, and image evidence. The append-only log and its witnesses are
specified in [`log.md`](log.md) and [`witness.md`](witness.md).

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
| `counts.blank` | integer | yes, unless unread or not on the sheet | Blank votes |
| `counts.null` | integer | yes, unless unread or not on the sheet | Null (spoilt) votes |
| `counts.candidatures` | object | yes | Votes per candidature: candidature code → integer |
| `counts.registered` | integer | no | Registered voters at the station |
| `counts.candidature_total` | integer | no | Total votes for candidatures, when the sheet states it separately |
| `counts.other` | object | no | Ballots that are neither blank, null nor for a candidature: category → integer. Profiles define the categories, for example ballots left unmarked. Omitted when empty |
| `counts.unread` | object | no | Figures of the sheet that could not be read: item → reason (section 3.4). Omitted when empty |
| `counts.not_on_sheet` | object | no | Figures the sheet does not have at all: item → reason (section 3.5). Omitted when empty |
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

### 3.4 Figures that could not be read

A figure of a tally sheet may be impossible to read, and a field may be left
empty. Neither is a zero. `counts.unread` lists such figures, each with the
reason:

| Reason | Meaning |
| --- | --- |
| `illegible` | Something is written in the field and could not be read |
| `empty` | Nothing is written in the field |

The two are kept apart because they are different facts about the sheet: in
the one run that has both, empty fields turned out to be zeros far more often
than illegible ones.

An item is named `blank`, `null`, `candidature:<code>` or `other:<category>`.
An item listed in `counts.unread` MUST NOT carry a value anywhere else in the
statement: the candidature or category is absent from its object, and `blank`
or `null` is absent from `counts`. A statement MUST NOT give a zero, or any
other value, to a figure it lists as unread.

A candidature that is neither in `counts.candidatures` nor in `counts.unread`
has zero votes, as before.

`counts.unread` is omitted when empty, so statements written before it existed
keep their identifier.

### 3.5 Figures the sheet does not have

A tally sheet may have no field at all for something the format names. The
tally sheets of one country have no figure for blank votes. Writing `0` would
say something the sheet does not say.

`counts.not_on_sheet` lists such figures. It has the same shape as
`counts.unread`, sits next to it and uses the same item names; the only
reason defined is `no-field`. The same rule applies: an item listed there
MUST NOT carry a value anywhere else in the statement, and `blank` or `null`
is then absent from `counts`.

Each figure of a statement is therefore in exactly one of three states: it
has a value, it is unread (with a reason), or the sheet does not have it. An
item MUST NOT be in both `counts.unread` and `counts.not_on_sheet`.

The difference matters to the verifier. An unread figure is missing from a
sum, which becomes a lower bound. A figure the sheet does not have is not
missing: there is nothing to add, and the sum is not a lower bound because of
it.

`counts.not_on_sheet` is omitted when empty, so statements written before it
existed keep their identifier.

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
| `blank` | integer | no | Blank votes. Omitted when the totals do not give them |
| `null` | integer | no | Null votes. Omitted when the totals do not give them |
| `candidatures` | object | yes | Candidature code → votes |
| `candidature_total` | integer | no | Total votes for candidatures |
| `other` | object | no | Other categories of ballots, as in `counts.other`. Compared only when present |
| `stations` | integer | no | Number of polling stations |
| `unread` | object | no | Items whose figure is a lower bound because its source could not read some figure behind it: item → how many. Omitted when empty |

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
   votes but are not counted as stations. For each item it also counts the
   statements that list it in `counts.unread`.
5. For every area present on both sides it compares station count, blank,
   null, candidature total and each candidature. A candidature missing on one
   side counts as zero. Each mismatch is a *difference*, except as step 6
   says.
6. When at least one statement of the area could not read an item, the sum
   for that item is a **lower bound**, not a total: the true sum is at least
   that. The same holds for the candidature total when any candidature
   figure is unread.
   - A lower bound **above** the official figure is a *difference*: the true
     sum can only be higher still. Its size is a minimum too, and the
     verifier MUST say "at least N above", never "N above".
   - A lower bound **equal to or below** the official figure is neither a
     match nor a difference. Nothing is said about it; it is listed as a
     lower bound, with the number of statements concerned.
   - When the official figure is a lower bound as well (`unread` in the
     official totals), there are **two lower bounds** and nothing is said in
     any case, whichever is larger.

   An official figure that is a lower bound, against a sum that is not, is
   treated the same way round: a sum below it differs by at least that much,
   and nothing is said otherwise.
7. When every statement of the area that mentions an item says the sheet
   does not have it (`counts.not_on_sheet`), nothing is added for it. If the
   official totals nevertheless give a figure for that item, the item is
   **not comparable**: it is reported as such, and is neither a match nor a
   difference. The same holds the other way round, when the statements give
   blank or null votes and the official totals do not.
8. When some statements of the area say the sheet does not have an item and
   others give it a figure, or say it could not be read, the statements are
   **inconsistent** about what the sheet has. The verifier reports the item
   with both numbers of statements and does not choose: nothing is said
   about that item, and the area is not matching.
9. An area present on only one side is a *gap*.

A sum is **matching** only if there are no differences, no lower bounds, no
inconsistent items and no gaps. Items that are not comparable do not prevent
a match; the result names them. A sum with lower bounds or inconsistent
items and nothing else is **undecided**. Station
issues are reported but do not change the result.

For a single statement, a sheet total (`candidature_total`) is contradicted
by rows of which some are unread only when the rows that were read already
exceed it.

The verifier reports both sums and says which of them the official totals
coincide with: both, what the stations counted, what was left standing, or
neither. When neither matches and at least one is undecided, it says
*undecided*, which is not a positive result. It MUST NOT show one sum without the other when they differ, and it
makes no assumption about which of the two an official file contains.

### 5.2 Which statements enter the sums

Statements with the same identifier are one statement.

1. Statements are grouped by station and `stage`. A group whose statements
   all give the same figures (blank, null, other categories and votes per
   candidature, a zero and a missing entry being the same) counts as one.
   When they differ, a version stays only if no statement of the same
   `stage` names it in `supersedes`: an authority may correct its own
   figures, and the corrected version then speaks for the act. Versions that
   stay and differ only where one of them could not read a figure are not in
   conflict: an unread figure contradicts nothing. (A version that says the
   sheet does not have a figure does contradict one that gives it a value or
   says it is unread: they describe different sheets.) They count as one act,
   whose figures are those any of them read; a figure none of them read
   stays unread. Versions of which two read the same item differently are an
   act **in conflict**: it enters no sum and is listed. Contradictory copies
   count for nothing.
2. **As counted**: for each station, its `count` act, unless in conflict.
3. An act is *replaced* when a statement of another `stage` names one of its
   statements in `supersedes`. **As standing**: for each station, the one
   act that is not replaced, unless it is in conflict.
4. A station with more than one act not replaced is **undetermined**: it is
   left out of the standing sum and listed. The format does not guess an
   order between acts that do not refer to each other.
5. The verifier lists the stations whose standing figures differ from those
   of an earlier act (the count when there is a statement of it, otherwise
   the first act of the chain), item by item, with both acts and the class
   of source. An item either act could not read is not a change: nothing is
   said about it, and the station is listed as compared only in part. It
   also lists the stations
   that have a later act but no statement of the count; and the statements
   whose `supersedes` names a statement that was not provided.

The overall result is positive only if the official totals coincide with at
least one sum and no station is in conflict or undetermined.

When every station has a single statement of its count, the two sums are the
same sum.

### 5.1 What a result means

- *Matching* means: the published totals are the sum of these
  statements. It says nothing about whether the statements are true.
- A *lower bound* means some figures could not be read, so the statements
  add up to at least that much. It is not a match, and it is not a
  difference.
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

## 7. Conventions for `extra`

`extra` takes no part in verification, and profiles are free to use it. One
key is shared, so that reports can be read across countries:

- `extra.recount`: `true` when the figures of a statement come from counting
  the ballots of the station again, `false` when they come from tally sheets
  without counting again. Omitted when the source does not say. It applies to
  acts after the count. Whether ballots were recounted changes what a
  difference between two acts can mean, but it is not a different act.

## 8. What each country changed in the core

The core is meant to be country-neutral. This is the record of how far that
has held: every time a new profile could not be written without changing the
core, the change is listed here.

| Profile added | What the core lacked | Change |
| --- | --- | --- |
| Spain | Rows that carry votes but are not polling stations (overseas vote) | `unit` |
| Spain | Totals published at several levels | `grouping`, areas |
| Spain | Candidatures added up under one code at some level | `merge` |
| Colombia | Lawful acts after the count that change a station's figures | `stage`, `supersedes`, two sums |
| Colombia | Ballots that are neither blank, null nor for a candidature | `counts.other` |
| Colombia | An authority correcting its own figures within one act | same-stage `supersedes` |
| Mexico | Figures the source could not read | `counts.unread`, with a reason; a sum that includes one is a lower bound; a difference found against a lower bound is "at least" |
| Mexico | A figure the tally sheet does not have (blank votes) | `counts.not_on_sheet`; `blank` and `null` optional in official totals; "not comparable" and "inconsistent" in the report |
| Mexico | Official totals whose own source could not read a figure | `unread` in official totals; two lower bounds say nothing |

The Mexico profile also showed things that were left as they are, and are
known limits: one earlier statement replaced by several later ones, a later
act that has a row and no figures for a station, official totals that are
only a grand total, and a sheet total that includes null votes. See
[`profile-mx.md`](profile-mx.md).

**Stopping rule.** Countries stop being added when one enters without a
change to the core. Mexico did not meet it: it needed the three changes
above. So far no country has been added without a change to the core, and
another one is needed.
