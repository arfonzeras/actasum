# actasum

**English** · [Español](README.es.md)

*Formerly `tallylog`; renamed on 11 October 2026.*

An open format and a verifier for polling-station tally sheets.

After an election, each polling station records its result on a tally sheet.
The electoral authority then adds those sheets up. `actasum` lets anyone
repeat that addition from the station-level figures and compare it with the
published totals.

It does not handle voting, voter identity or ballots. It audits the step
between the polling station and the published result.

> **Status: early draft (v0.1).** The format will change. The Spain reader has
> been run against five real elections so far (see below). Do not rely on its
> output for anything else yet.

## Results so far

On 11 October 2026 the verifier was run on the Ministry of the Interior's
per-station files for five Congreso elections.

| Election | Polling stations | Constituencies whose recomputed totals match |
| --- | --- | --- |
| March 2008 | 59,346 | 50 of 52 |
| June 2016 | 57,531 | 52 of 52 |
| April 2019 | 60,038 | 52 of 52 |
| November 2019 | 59,555 | 52 of 52 |
| July 2023 | 60,314 | 50 of 52 |

Where totals match, blank votes, null votes, every candidature's votes and
the number of polling stations all agree. In the four constituencies that
differ, the municipalities still match their polling stations; the difference
sits in the overseas-vote row. Details and caveats are in
[`docs/findings/es-congreso.md`](docs/findings/es-congreso.md).

These runs compare the Ministry's publications with each other. They do not
show that the per-station figures match the paper tally sheets, and a
difference does not say which published figure is right.

## What is here

| Path | Content |
| --- | --- |
| [`docs/spec/core.md`](docs/spec/core.md) | Country-neutral format and verification procedure |
| [`docs/spec/log.md`](docs/spec/log.md) | Append-only log: checkpoints, inclusion and consistency proofs |
| [`docs/spec/witness.md`](docs/spec/witness.md) | Signed checkpoints and witnesses that cosign them |
| [`docs/spec/profile-es.md`](docs/spec/profile-es.md) | Spain profile: identifiers, data source, known gaps ([Spanish translation](docs/spec/profile-es.es.md)) |
| [`docs/findings/es-congreso.md`](docs/findings/es-congreso.md) | What the first runs on real data found |
| [`docs/findings/es-other-elections.md`](docs/findings/es-other-elections.md) | Runs on two European Parliament elections and two local elections |
| [`docs/spec/profile-co.md`](docs/spec/profile-co.md) | Colombia profile (draft, one file run) |
| [`docs/findings/co-presidente-2026.md`](docs/findings/co-presidente-2026.md) | Colombia, presidential election of May 2026: Bogotá and Córdoba verified against the commissions' own hashes and totals |
| [`docs/spec/profile-mx.md`](docs/spec/profile-mx.md) | Mexico profile (draft): INE PREP and Cómputos Distritales databases |
| [`docs/findings/mx-presidencia-2024.md`](docs/findings/mx-presidencia-2024.md) | Mexico, presidential election of June 2024: the count as captured and the canvass, station by station |
| [`schemas/statement.schema.json`](schemas/statement.schema.json) | JSON Schema for a statement |
| `src/actasum/` | Reference implementation, Python; standard library only except for signatures |
| `tests/` | Tests on synthetic data |

## Quick start

Requires Python 3.10 or later. No dependencies, except `cryptography` for
signing and witnesses.

```sh
pip install -e .
```

Download the per-station (`_MESA`) ZIP file of a Congreso election from the
Spanish Ministry of the Interior's
[download area](https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/),
then:

```sh
actasum es replay --mesa 02201911_MESA.zip
```

That ZIP carries both the per-station files and the province totals. Pass
`--tota` to read the totals from a separate file instead.

To see in which municipalities a difference arises, compare one level down:

```sh
actasum es replay --mesa 02202307_MESA.zip --level municipality
```

Local elections (`04…_MESA.zip`) and European Parliament elections
(`07…_MESA.zip`) are read too, with the municipality and the whole country as
constituency. Two elections of each type have been run so far; see
[`docs/findings/es-other-elections.md`](docs/findings/es-other-elections.md).
For a first look at a ZIP:

```sh
actasum es describe --mesa 07202406_MESA.zip
```

A station may have several statements: several captures of the same tally
sheet, which must agree, and later acts such as a correction in the general
canvass or a repeated vote, which may lawfully differ. The verifier then
shows two sums, what the stations counted and what was left standing, and
says which one the official totals coincide with
([core specification](docs/spec/core.md), sections 3.3 and 5.2).

The command prints how many constituencies match and lists every difference.
It exits with `0` when everything matches, `1` when there are differences or
gaps, and `2` when the input cannot be read.

The same thing in separate steps, producing the neutral intermediate files:

```sh
actasum es convert  --mesa 02201911_MESA.zip --out statements.jsonl
actasum es official --tota 02201911_MESA.zip --out official.json
actasum verify --statements statements.jsonl --official official.json
```

## The log

Statements can be loaded into an append-only log. A checkpoint of three lines
commits to every entry, and short proofs show that one polling station's
statement is in the log, or that the log has only grown.

```sh
actasum es convert --mesa 02201911_MESA.zip --out statements.jsonl
actasum log build --statements statements.jsonl --out log-2019-11 > checkpoint.txt

actasum log prove --log log-2019-11 --station es/04/003/02/001/B --out proof.json
actasum log check-proof --proof proof.json --checkpoint checkpoint.txt
```

Anyone who builds the log from the same ZIP file obtains the same checkpoint.
See [`docs/spec/log.md`](docs/spec/log.md).

### Signing and witnesses

The log can sign its checkpoint, and a witness can cosign it after checking
that the log only grew. This needs the optional `cryptography` package
(`pip install -e '.[sign]'`).

```sh
# the log operator
actasum key new --name actasum/es/congreso/2019-11 --out log.key      # prints the log's public key
actasum log sign --log log-2019-11 --key log.key
actasum log witness-request --log log-2019-11 --old-size 0 --out request.txt

# the witness, ideally another organization on another machine
actasum witness init --dir witness --name witness.example/w1           # prints the witness's public key
actasum witness trust --dir witness --log-key '<the log public key>'
actasum witness add-checkpoint --dir witness --request request.txt --out cosignature.txt

# back at the log, then anyone
actasum log cosign --log log-2019-11 --signatures cosignature.txt
actasum log check-checkpoint --checkpoint log-2019-11/checkpoint \
    --log-key '<the log public key>' --witness-key '<the witness public key>' --quorum 1
```

A witness refuses to cosign a log that changed or dropped an entry it had
seen. That only means something when the witness is run by someone
independent of the log operator; running both yourself shows that the
mechanism works and nothing else. Formats follow the C2SP specifications; see
[`docs/spec/witness.md`](docs/spec/witness.md) for what is and is not done.

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
signed checkpoints, signed statements from accredited observers using W3C Verifiable Credentials,
and several independent captures per station.

## Roadmap

1. **Format and verifier** on a past election, from public data. *(done for five Congreso elections)*
2. **Load a full election into a log** and serve inclusion proofs. *(first version)*
3. Replay the 2026 Colombian presidential runoff from the published E-14 forms.
4. **A witness that cosigns the log state.** *(mechanism done; no external witness yet)*
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
- The column layout of the Ministry's files was first taken from the
  rOpenSpain [`infoelectoral`](https://github.com/rOpenSpain/infoelectoral)
  R package by Héctor Meleiro, then checked against the Ministry's own layout
  document. No code from that package is included here.

## License

[Apache License 2.0](LICENSE).
