# Verifiability cards

One card per election (docs/spec/verifiability.md), with the context it was
computed from. **Status: run, not verified**, like the runs they come from:
the cards compare publications of one authority with each other and add
nothing to them.

| Election | Card | Context | Notes |
| --- | --- | --- | --- |
| Spain, Congreso, November 2019 | [card](es-congreso-2019-11.card.json) | [context](es-congreso-2019-11.context.json) | Seats per province, listed by name; overseas (CERA) row per province |
| Mexico, president, 2 June 2024 | [card](mx-presidencia-2024-06.card.json) | [context](mx-presidencia-2024-06.context.json) | No margin: 3 statements of the standing sum have empty cells (below) |
| Brazil, president, 4 October 2026, first round | [card](br-presidente-2026-10-04.card.json) | [context](br-presidente-2026-10-04.context.json) | Descriptive margins only |

Not computed yet, for lack of the files in the environment where these were
built: the other eight Spanish elections (the Ministry's ZIP files), and
Bogotá and Córdoba (the commissions' MMV files). The European Parliament
elections also wait for the allocation articles of the LOREG.

**Mexico.** Three of the 16 stations whose package was not received keep
their PREP statement in the standing sum (profile-mx.md, section 6,
point 5), and those statements have empty cells for candidatures of both
coalitions. The card does not compute a margin from figures that could not be
read, and says so.

**Spain.** The overseas row of a province is one unit with a census much
larger than its ballots. Under `rewrite` and `add_to_census` it alone often
reaches the margin of the last seat, so each figure in units also comes
without aggregates.

## How to reproduce

```sh
# Spain, Congreso, November 2019 (02201911_MESA.zip from the Ministry)
actasum es convert  --mesa 02201911_MESA.zip --out es.jsonl
actasum es official --tota 02201911_MESA.zip --out es.official.json
actasum card --statements es.jsonl --official es.official.json \
    --context docs/findings/cards/es-congreso-2019-11.context.json

# Mexico: the statements of `actasum mx replay` (docs/findings/mx-presidencia-2024.md)
actasum card --statements mx.jsonl \
    --official docs/findings/official/mx-presidencia-2024-06.official.json \
    --context docs/findings/cards/mx-presidencia-2024-06.context.json

# Brazil: the statements of `actasum br replay` for the first round
actasum card --statements br.jsonl \
    --official docs/findings/official/br-presidente-2026-10-04-states.official.json \
    --official docs/findings/official/br-presidente-2026-10-04-brasil.official.json \
    --context docs/findings/cards/br-presidente-2026-10-04.context.json
```

The draft context of a Spanish election comes from `actasum es context
--mesa MESA.zip`; the facts it cannot read from the files were added by hand,
each with its source. Each card records the SHA-256 of its inputs.
