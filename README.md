# actasum

**English** · [Español](https://github.com/arfonzeras/actasum/blob/main/README.es.md)

*Formerly `tallylog`; renamed on 11 October 2026.*

An open format and a verifier for polling-station tally sheets.

After an election, each polling station records its result on a tally sheet.
The electoral authority then adds those sheets up. `actasum` lets anyone
repeat that addition from the station-level figures and compare it with the
published totals.

It does not handle voting, voter identity or ballots. It looks at the step
between the polling station and the published result.

> **Status: early draft (v0.1).** The format will change. The verifier has
> been run on published files of Spain, Colombia, Mexico and Brazil (below).
> Do not rely on its output for anything else yet.

## Elections run

Every run compares publications of one electoral authority with each other:
its station-level files against its own totals. A **match** means those
publications are consistent: the published totals are the sum of the
published station figures. It is not a verification. No run has compared
the files with paper tally sheets, and a difference does not say which
figure is right or why.

All runs are therefore marked **run, not verified**.

| Country | Election | Stations | What matches | What does not | Status | Findings |
| --- | --- | --- | --- | --- | --- | --- |
| Spain | Congreso, March 2008 | 59,346 | 50 of 52 constituencies; 8,111 of 8,112 municipalities | Overseas rows of Barcelona and Murcia; one municipality in Soria | run, not verified | [es-congreso](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) |
| Spain | Congreso, June 2016 | 57,531 | 52 of 52 constituencies | — | run, not verified | [es-congreso](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) |
| Spain | Congreso, April 2019 | 60,038 | 52 of 52 constituencies | — | run, not verified | [es-congreso](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) |
| Spain | Congreso, November 2019 | 59,555 | 52 of 52 constituencies; 8,131 of 8,131 municipalities | — | run, not verified | [es-congreso](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) |
| Spain | Congreso, July 2023 | 60,314 | 50 of 52 constituencies; 8,131 of 8,131 municipalities | Overseas rows of Cantabria and Toledo | run, not verified | [es-congreso](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) |
| Spain | European Parliament, June 2024 | 58,556, plus 52 overseas rows | The country and all 52 provinces | — | run, not verified | [es-other-elections](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md) |
| Spain | European Parliament, May 2019 | 60,076, plus 52 overseas rows | 38 of 52 provinces; 8,126 of 8,131 municipalities | The country: the three levels published do not add up to each other | run, not verified | [es-other-elections](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md) |
| Spain | Local, May 2023 | 57,681 | 5,248 of 5,272 municipalities | 24 municipalities; in 5 the station votes would give other seats | run, not verified | [es-other-elections](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md) |
| Spain | Local, May 2019 | 57,188 | 5,270 of 5,291 municipalities | 21 municipalities; 8 seat allocations to explain | run, not verified | [es-other-elections](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md) |
| Colombia | President, 31 May 2026, Bogotá D.C. | 17,157 | All 16 vote figures of the official result (E-26); 6,410 of 6,410 changes recorded in the AGE agree with the file | Stations: 17,164 on the E-24. The file as published is the commission's shifted by 13 bytes; repaired and checked against the hash in the AGE | run, not verified | [co-presidente-2026](https://github.com/arfonzeras/actasum/blob/main/docs/findings/co-presidente-2026.md) |
| Colombia | President, 31 May 2026, Córdoba | 4,176 | All 16 vote figures of the E-26 | — (the record of changes is a scan and was not read) | run, not verified | [co-presidente-2026](https://github.com/arfonzeras/actasum/blob/main/docs/findings/co-presidente-2026.md) |
| Mexico | President, 2 June 2024 | 158,972 in the count, 170,621 in the canvass | The canvass statements equal an INE press statement in every figure it gives | Neither sum equals it: the count has unread figures and is at least 1,883 above for unregistered candidates; the standing sum includes 5,265 ballots of 16 stations whose package was not received | run, not verified | [mx-presidencia-2024](https://github.com/arfonzeras/actasum/blob/main/docs/findings/mx-presidencia-2024.md) |
| Brazil | President, 4 October 2026, first round | 499,206 | Every vote figure of the 28 reports of the states and abroad, and of the national report | One section abroad has no row in the file (its report gives 0 voters) | run, not verified | [br-presidente-2026](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026.md) |
| Brazil | President, 25 October 2026, second round | 499,205 | Every vote figure of the 28 reports of the states and abroad, and of the national report | Two sections abroad have no row for president in the file (their report gives 0 voters) | run, not verified | [br-presidente-2026-2t](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026-2t.md) |

In Brazil, 5,246 votes for number 28 are compared as null votes because the
official reports declare that they count them so; the verifier says it in
its result. In the second round no votes are counted as another item. The
Brazilian reports say their result is subject to change.

### How to reproduce each run

No election data is in this repository. Each run starts from files
downloaded from the authority; the hash is that of the file as downloaded.

**Spain.** Per-station ZIP files `02YYYYMM_MESA.zip` (Congreso),
`07YYYYMM_MESA.zip` (European Parliament) and `04YYYYMM_MESA.zip` (local),
from the Ministry of the Interior's
[download area](https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/).

```sh
actasum es replay --mesa 02201911_MESA.zip                       # per constituency
actasum es replay --mesa 02202307_MESA.zip --level municipality  # per municipality
actasum es replay --mesa 07202406_MESA.zip --level province      # per province
actasum es seats  --mesa 04202305_MESA.zip                       # would a difference change a seat?
```

| File | SHA-256 |
| --- | --- |
| `02201911_MESA.zip` | `e7b621f295d7bf79b794941d4f11e7bcf7bd971ecbd6eb21dd4269d59926e441` |
| `07202406_MESA.zip` | `ed30e4cf11772afb0785f2992f44fa191b8671f933865335b7093ac9ccb6659b` |
| `07201905_MESA.zip` | `8199711babd4b61ee4940469351ab4a263b0cf84a84ccfbe04ab1970a4c1a474` |
| `04202305_MESA.zip` | `20dac696cd2efaa63c9346384ddb682f3da4fda92c6af67447159a60f1ab0de3` |
| `04201905_MESA.zip` | `b8b1c649e3841ba735383152fd3a38259a336698d1eb79f7a653cae54c02e204` |
| `02200803_MESA.zip`, `02201606_MESA.zip`, `02201904_MESA.zip`, `02202307_MESA.zip` | not recorded |

**Colombia.** The per-station file (`MMV_…csv`) and the *Acta General de
Escrutinio* (AGE) of each department's general scrutiny commission, from the
Registraduría's [scrutiny site](https://escrutiniospresidente2026.registraduria.gov.co/published).
The official totals were typed from the scanned E-26 and are in
[`docs/findings/official/`](https://github.com/arfonzeras/actasum/tree/main/docs/findings/official/).

```sh
# Bogotá: the AGE's text gives the changes and the hash of the original file
pdftotext -layout AGE.pdf AGE.txt
actasum co convert --mmv MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv --election 2026-05 \
    --age-text AGE.txt --out statements.jsonl
actasum verify --statements statements.jsonl \
    --official docs/findings/official/co-presidente-2026-05-bogota.official.json

# Córdoba
actasum co convert --mmv MMV_XXX_13_000_XXX_XX_XX_XXX_1007.csv --election 2026-05 \
    --sha256 2799c27a52574d85753ee0d31475cebdafd7819f88f1d977fe3b718fc6d636c9 \
    --out statements.jsonl
actasum verify --statements statements.jsonl \
    --official docs/findings/official/co-presidente-2026-05-cordoba.official.json
```

| File | SHA-256 |
| --- | --- |
| Bogotá, `MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv` as downloaded | `6cec1c68ac67c73407fb1cfd30a337bab08b8b850e6d679c918d98f5e4ec000e` |
| Bogotá, the same file as the commission generated it, as the AGE records | `dfa5612022c2763666cd72d9553bbcfd5cfcab60076fc4a95889503a34a6ce25` |
| Córdoba, `MMV_XXX_13_000_XXX_XX_XX_XXX_1007.csv` | `2799c27a52574d85753ee0d31475cebdafd7819f88f1d977fe3b718fc6d636c9` |

**Mexico.** The INE's PREP and Cómputos Distritales databases of the
presidential election. The address they were downloaded from was not
recorded. The official totals are typed from INE press statement 368.

```sh
# PRES_2024.csv inside 20240603_2005_PREP.zip › 20240603_2005_PREP_PRES.zip, and
# inside 20240608_2030_COMPUTOS.zip › 20240608_2030_COMPUTOS_PRES.zip
actasum mx replay --prep PREP/PRES_2024.csv --computos COMPUTOS/PRES_2024.csv \
    --election 2024-06 --official docs/findings/official/mx-presidencia-2024-06.official.json
```

| File | SHA-256 |
| --- | --- |
| `20240603_2005_PREP.zip` | `dcccf23088f81a4ab7c7942a79504b04c4a9347b0a4744f6c328c59fd4d6c31d` |
| its `PRES_2024.csv` | `c9d7282e9ba0dabdc6d0378eb3383010ad3f301a26d79c3035a9f2a2fd6d5c45` |
| `20240608_2030_COMPUTOS.zip` | `f0b0f90483720374eaac50cfb356b43425697fabfa3f963d22a5b8f2d849312f` |
| its `PRES_2024.csv` | `860c1a539ac98b5def4dff3e82e87a19be3ebba7cb435b680ae79799942d1628` |

**Brazil.** The TSE's 28 ballot-box report files `bweb_1t_<UF>_051020261403.zip`
(26 states, the Distrito Federal and `ZZ`, abroad), from the dataset
[Resultados - 2026 - Boletim de Urna](https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna),
and the 29 presidential totalisation reports
`Relatorio_Resultado_Totalizacao_2026_<UF>.zip` (the same 27, plus `BR`),
from `https://cdn.tse.jus.br/estatistica/sead/odsele/relatorio_resultado_totalizacao/`.
`actasum br official` needs `pdftotext` (Poppler).

```sh
actasum br official --round 1 \
    $(for f in Relatorio_Resultado_Totalizacao_2026_*.zip; do printf -- '--report %s ' "$f"; done) \
    --states-out states.official.json --country-out brasil.official.json
actasum br replay \
    $(for f in bweb_1t_*_051020261403.zip; do printf -- '--bu %s ' "$f"; done) \
    --official docs/findings/official/br-presidente-2026-10-04-states.official.json \
    --official docs/findings/official/br-presidente-2026-10-04-brasil.official.json
```

The TSE publishes a SHA-512 next to each ballot-box file; the 28 are in
[`docs/findings/br-presidente-2026-1t.sha512`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026-1t.sha512)
(`shasum -a 512 -c` checks them). The SHA-256 of each report, and its issue
time, are in the two official-totals files above. The report ZIP files now
also hold the reports of the second round, and four reports of the first
(MG, RN, RO, RS) were issued again with the same figures: written from the
files published now, the first round's official totals have the same figures
and `count_as`, and other hashes and issue times.

The second round: the 28 files `bweb_2t_<UF>_261020260742.zip` from the same
dataset (on the portal, listed by the page in English), and the same 29
report ZIP files.

```sh
actasum br official --round 2 \
    $(for f in Relatorio_Resultado_Totalizacao_2026_*.zip; do printf -- '--report %s ' "$f"; done) \
    --states-out states.official.json --country-out brasil.official.json
actasum br replay \
    $(for f in bweb_2t_*_261020260742.zip; do printf -- '--bu %s ' "$f"; done) \
    --official docs/findings/official/br-presidente-2026-10-25-states.official.json \
    --official docs/findings/official/br-presidente-2026-10-25-brasil.official.json
```

Their SHA-512 are in
[`docs/findings/br-presidente-2026-2t.sha512`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026-2t.sha512).

## What is here

| Path | Content |
| --- | --- |
| [`docs/spec/core.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/core.md) | Country-neutral format and verification procedure |
| [`docs/spec/log.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/log.md) | Append-only log: checkpoints, inclusion and consistency proofs |
| [`docs/spec/witness.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/witness.md) | Signed checkpoints and witnesses that cosign them |
| [`docs/spec/profile-es.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/profile-es.md) | Spain profile: identifiers, data source, known gaps ([Spanish translation](https://github.com/arfonzeras/actasum/blob/main/docs/spec/profile-es.es.md)) |
| [`docs/findings/es-congreso.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) | What the first runs on real data found |
| [`docs/findings/es-other-elections.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md) | Runs on two European Parliament elections and two local elections |
| [`docs/spec/profile-co.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/profile-co.md) | Colombia profile (draft, one file run) |
| [`docs/findings/co-presidente-2026.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/co-presidente-2026.md) | Colombia, presidential election of May 2026: Bogotá and Córdoba compared with the commissions' own hash and totals |
| [`docs/spec/profile-mx.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/profile-mx.md) | Mexico profile (draft): INE PREP and Cómputos Distritales databases |
| [`docs/findings/mx-presidencia-2024.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/mx-presidencia-2024.md) | Mexico, presidential election of June 2024: the count as captured and the canvass, station by station |
| [`docs/spec/profile-br.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/profile-br.md) | Brazil profile (draft): TSE ballot-box report files |
| [`docs/findings/br-presidente-2026.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026.md) | Brazil, presidential election of October 2026, first round: every state and abroad against the TSE's totalisation reports |
| [`docs/findings/br-presidente-2026-2t.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026-2t.md) | The same, second round |
| [`schemas/statement.schema.json`](https://github.com/arfonzeras/actasum/blob/main/schemas/statement.schema.json) | JSON Schema for a statement |
| `src/actasum/` | Reference implementation, Python; standard library only except for signatures |
| [`docs/releasing.md`](https://github.com/arfonzeras/actasum/blob/main/docs/releasing.md) | How a release is published to PyPI |
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
[`docs/findings/es-other-elections.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md).
For a first look at a ZIP:

```sh
actasum es describe --mesa 07202406_MESA.zip
```

A station may have several statements: several captures of the same tally
sheet, which must agree, and later acts such as a correction in the general
canvass or a repeated vote, which may lawfully differ. The verifier then
shows two sums, what the stations counted and what was left standing, and
says which one the official totals coincide with
([core specification](https://github.com/arfonzeras/actasum/blob/main/docs/spec/core.md), sections 3.3 and 5.2).

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
See [`docs/spec/log.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/log.md).

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
[`docs/spec/witness.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/witness.md) for what is and is not done.

## What a result means, and what it does not

- **Matching** means the published totals equal the sum of the published
  station-level figures. That is consistency between two publications, not
  verification. Nothing more.
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

1. **Format and verifier** on a past election, from public data. *(run on elections of Spain, Colombia, Mexico and Brazil)*
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

- Election results: Ministerio del Interior (Spain), *Área de descargas*;
  Registraduría Nacional del Estado Civil (Colombia), scrutiny site;
  Instituto Nacional Electoral (Mexico); Tribunal Superior Eleitoral
  (Brazil), open-data portal. No election data is included in this
  repository.
- The column layout of the Ministry's files was first taken from the
  rOpenSpain [`infoelectoral`](https://github.com/rOpenSpain/infoelectoral)
  R package by Héctor Meleiro, then checked against the Ministry's own layout
  document. No code from that package is included here.

## License

[Apache License 2.0](https://github.com/arfonzeras/actasum/blob/main/LICENSE).
