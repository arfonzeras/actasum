# tallylog

**English** · [Español](README.es.md)

An open format and a verifier for polling-station tally sheets.

After an election, each polling station records its result on a tally sheet.
The electoral authority then adds those sheets up. `tallylog` lets anyone
repeat that addition from the station-level figures and compare it with the
published totals.

It does not handle voting, voter identity or ballots. It audits the step
between the polling station and the published result.

> **Status: early draft (v0.1).** The format will change. The Spain reader has
> been run against one real election so far (see below). Do not rely on its
> output for anything else yet.

## First result

On 11 October 2026 the verifier was run on the Ministry of the Interior's
files for the Congreso election of November 2019 (`02201911_MESA.zip` and
`02201911_TOTA.zip`).

| | |
| --- | --- |
| Polling stations read | 59,555 |
| Overseas-vote rows read (one per constituency) | 52 |
| Constituencies compared | 52 |
| Constituencies whose recomputed totals match | 52 |
| Polling stations with internal inconsistencies | 0 |

Blank votes, null votes, every candidature's votes and the number of polling
stations all match in every constituency. This shows that the Ministry's
per-station publication adds up to its province totals for that election. It
does not show that the per-station figures match the paper tally sheets.

## What is here

| Path | Content |
| --- | --- |
| [`docs/spec/core.md`](docs/spec/core.md) | Country-neutral format and verification procedure |
| [`docs/spec/profile-es.md`](docs/spec/profile-es.md) | Spain profile: identifiers, data source, known gaps ([Spanish translation](docs/spec/profile-es.es.md)) |
| [`schemas/statement.schema.json`](schemas/statement.schema.json) | JSON Schema for a statement |
| `src/tallylog/` | Reference implementation, Python standard library only |
| `tests/` | Tests on synthetic data |

## Quick start

Requires Python 3.10 or later. No dependencies.

```sh
pip install -e .
```

Download the per-station (`_MESA`) and totals (`_TOTA`) ZIP files of a
Congreso election from the Spanish Ministry of the Interior's
[download area](https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/),
then:

```sh
tallylog es replay --mesa 02201911_MESA.zip --tota 02201911_TOTA.zip
```

The command prints how many constituencies match and lists every difference.
It exits with `0` when everything matches, `1` when there are differences or
gaps, and `2` when the input cannot be read.

The same thing in separate steps, producing the neutral intermediate files:

```sh
tallylog es convert  --mesa 02201911_MESA.zip --out statements.jsonl
tallylog es official --tota 02201911_TOTA.zip --out official.json
tallylog verify --statements statements.jsonl --official official.json
```

## What a result means, and what it does not

- **Matching** means the published constituency totals equal the sum of the
  station-level figures. Nothing more.
- A **difference** means they do not add up. It does not say why: lawful
  corrections during the official canvass, transcription slips and fraud all
  look the same here. A difference is a reason to ask, not a conclusion.
- In this first version both inputs come from the same authority. A match
  shows that its two publications are consistent with each other. It does not
  show that either reflects the paper tally sheets. Independent captures of
  the sheets are the subject of later milestones.

## Design in one paragraph

A country-neutral core defines the statement, the official totals and the
verification rules. A profile per country maps local law and data onto the
core. Spain is the first profile because its results are public down to the
polling station. Later milestones add an append-only transparency log
(a Merkle tree with independent witnesses, as used for web certificates),
signed statements from accredited observers using W3C Verifiable Credentials,
and several independent captures per station.

## Roadmap

1. **Format and verifier** on a past election, from public data. *(this repository, in progress)*
2. Load a full election into a transparency log and serve inclusion proofs.
3. Replay the 2026 Colombian presidential runoff from the published E-14 forms.
4. An external witness that cosigns the log state.
5. Credentials and a capture app, with on-device signing and offline use.
6. A small real pilot together with a local election-observation organization.

## Running the tests

```sh
pip install pytest
pytest
```

## Data sources and acknowledgements

- Election results: Ministerio del Interior (Spain), *Área de descargas*.
  No election data is included in this repository.
- The column layout of the Ministry's files was taken from the rOpenSpain
  [`infoelectoral`](https://github.com/rOpenSpain/infoelectoral) R package by
  Héctor Meleiro. No code from that package is included here.

## License

[Apache License 2.0](LICENSE).
