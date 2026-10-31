# Verifiability cards

One card per election (docs/spec/verifiability.md), with the context it was
computed from. **Status: run, not verified**, like the runs they come from:
the cards compare publications of one authority with each other and add
nothing to them.

| Election | Card | Context | Notes |
| --- | --- | --- | --- |
| Spain, Congreso, November 2019 | [card](es-congreso-2019-11.card.json) | [context](es-congreso-2019-11.context.json) | Seats per province, listed by name; overseas (CERA) row per province |
| Spain, European Parliament, May 2019 | [card](es-europeas-2019-05.card.json) | [context](es-europeas-2019-05.context.json) | No seat margin until the allocation articles are read |
| Spain, local, May 2019 | [card](es-municipales-2019-05.card.json) | [context](es-municipales-2019-05.context.json) | Municipalities only as a distribution; 9 decided by lot left out |
| Spain, local, May 2023 | [card](es-municipales-2023-05.card.json) | [context](es-municipales-2023-05.context.json) | Same; 9 decided by lot left out |
| Colombia, president, 31 May 2026, Bogotá D.C. | [card](co-presidente-2026-05-bogota.card.json) | [context](co-presidente-2026-05-bogota.context.json) | Partial: no margin |
| Colombia, same election, Córdoba | [card](co-presidente-2026-05-cordoba.card.json) | [context](co-presidente-2026-05-cordoba.context.json) | Partial: no margin |
| Mexico, president, 2 June 2024 | [card](mx-presidencia-2024-06.card.json) | [context](mx-presidencia-2024-06.context.json) | Margin bounded by figures that could not be read (below) |
| Brazil, president, 4 October 2026, first round | [card](br-presidente-2026-10-04.card.json) | [context](br-presidente-2026-10-04.context.json) | Descriptive margins only |

Not computed yet, for lack of the files: the Congreso of March 2008, June
2016, April 2019 and July 2023, and the European Parliament of June 2024. The
European Parliament elections also wait for the allocation articles of the
LOREG.

**Mexico.** Three of the 16 stations whose package was not received keep
their PREP statement in the standing sum (profile-mx.md, section 6,
point 5), and those statements have 16 figures that could not be read. Each
is taken from 0 to the census of its station, and the margin is the interval
from 19,419,032 to 19,427,046 votes, which does not include a change of
winner.

**Spain.** The overseas row of a province is one unit with a census much
larger than its ballots. Under `rewrite` and `add_to_census` it alone often
reaches the margin of the last seat, so each figure in units also comes
without aggregates. In local elections, a municipality where no move of votes
changes the allocation (a single candidature, for example) counts as
`not_reachable` in the distribution of votes.

## How to reproduce

```sh
# Spain (02201911_MESA.zip from the Ministry; the same for 07201905, 04201905, 04202305)
actasum es convert  --mesa 02201911_MESA.zip --out es.jsonl
actasum es official --tota 02201911_MESA.zip --out es.official.json
actasum card --statements es.jsonl --official es.official.json \
    --context docs/findings/cards/es-congreso-2019-11.context.json

# Mexico: the statements of `actasum mx replay` (docs/findings/mx-presidencia-2024.md)
actasum card --statements mx.jsonl \
    --official docs/findings/official/mx-presidencia-2024-06.official.json \
    --context docs/findings/cards/mx-presidencia-2024-06.context.json

# Colombia: the statements of `actasum co convert` (docs/findings/co-presidente-2026.md)
actasum card --statements bogota.jsonl \
    --official docs/findings/official/co-presidente-2026-05-bogota.official.json \
    --context docs/findings/cards/co-presidente-2026-05-bogota.context.json

# Brazil: the statements of `actasum br replay` for the first round
actasum card --statements br.jsonl \
    --official docs/findings/official/br-presidente-2026-10-04-states.official.json \
    --official docs/findings/official/br-presidente-2026-10-04-brasil.official.json \
    --context docs/findings/cards/br-presidente-2026-10-04.context.json
```

The draft context of a Spanish election comes from `actasum es context
--mesa MESA.zip`; the facts it cannot read from the files were added by hand,
each with its source. Each card records the SHA-256 of its inputs.
