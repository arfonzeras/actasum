# Verifiability card (draft v0.1)

Status: **draft**. Field names and rules may change without notice until v1.0.

The verifiability card (`actasum/verifiability/v0.1`) is a JSON document,
one per election. It says how much it would take for the published figures
to give another result, how much of the vote was cast away from the polling
station, and what the authority publishes that lets anyone check it. It is
computed from three inputs:

1. the statements of the election (core, section 3);
2. one or more official-totals documents (core, section 4);
3. a **context** document (`actasum/card-context/v0.1`, section 7), written
   by hand or by a profile, with what the data cannot say: the kind of
   contest, the seats to fill, the remote-vote channels, and facts such as
   whether images of the tally sheets are published, each with its source.

The card adds nothing to the statements or the official totals. Computing it
changes no identifier and no earlier result.

```sh
actasum card --statements statements.jsonl --official official.json [--official ...] \
    --context context.json --out card.json
```

## 1. Rules for every figure

- **Neutral language.** A card describes sizes and coincidences. It never
  calls anything manipulation, fraud or a vulnerability.
- **No polling station is named.** No field of a card holds a station
  identifier. Constituencies may be listed by identifier when the context
  allows it (section 7); municipalities never are, only as a distribution.
- **No relation between a way of voting and a candidature.** Remote-vote
  figures are totals of ballots; a card never splits them by candidature.
- **Every figure says where it comes from.** Each indicator carries `status`
  and `source`.
- **No floating-point numbers.** A ratio is `{"numerator", "denominator",
  "percent"}`, with the percentage as a string rounded half up to four
  decimals.

`status` is one of:

| Value | Meaning |
| --- | --- |
| `computed` | Computed by this procedure from the inputs named in `source` |
| `not_applicable` | The indicator does not apply to this kind of contest; `reason` says why |
| `not_computed` | It applies, but an input is missing or not exact; `reason` says which |
| `not_published` | The authority does not publish the figure separately, according to `source` |
| `unverified` | A fact this work has not checked |

`source` is `statements`, `official`, `context` or `verifier` (the result of
the core verification procedure), and for `context` the source the context
gives.

## 2. Which sum, which units

Every figure is computed on the **standing sum** (core, section 5.2), after
applying the `merge` and `count_as` that the first official-totals document
declares. A **unit** is a statement of that sum: a polling station or an
aggregate (core, section 3, `unit`). The card says how many units of each
kind there are.

When a figure depends on a value some statement could not read (core,
section 3.4), it is `not_computed`, with the number of statements concerned.

The **census** of a unit, `R`, is `counts.registered`. Where a unit has more
ballots counted than registered voters (in Spain, polling-station officials
may vote where they serve), the ballots are used instead: `R = max(registered,
ballots)`. Without a census in every unit, the figures that need it are
`not_computed`.

## 3. Margin

Notation, per unit *u*: *v_u(k)* votes of candidature *k*, *B_u* ballots
counted (candidatures, blank, null and other categories), *R_u* its census.
*V(k)* is the sum of *v_u(k)* over units.

### 3.1 Single winner (`single_winner`)

*W* is the candidature with most votes and *L* the second. The context
states the rule as `outcome_rule`; where the law has not been read it is
marked as assumed.

- **Margin in votes:** `M = V(W) − V(L)`.
- **Diluted margin:** `M / Σ B_u`. Lindeman and Stark (2012) define it as "the
  smallest reported margin (in votes), divided by the number of ballots
  cast", and divide by ballots rather than valid votes "to allow for the
  possibility that the vote tabulation system mistook an undervote or
  overvote for a valid vote". With one winner the smallest margin is that of
  *W* over the second.
- **Margin in units:** the least number *b* of units whose figures would have
  to be different for another candidature to have more votes than *W*. A tie
  does not count. Each unit has a capacity *c_u*, the most by which a
  different figure in that unit could reduce the margin; units are taken from
  the largest capacity down, and *b* is the least number whose capacities add
  up to at least `M + 1`:

  ```
  b = min { b : c_(1) + … + c_(b) ≥ M + 1 },   c_(1) ≥ c_(2) ≥ …
  ```

  Three assumptions, each a variant written next to its figure:

  | Assumption | `c_u` | Status |
  | --- | --- | --- |
  | `rewrite`: the unit's figures rewritten entirely, within its census | `v_u(W) − v_u(K) + R_u` | Main figure |
  | `move`: votes moved from *W* to another candidature | `2·v_u(W)` | Variant |
  | `add_to_census`: votes added to another candidature, up to the census | `R_u − B_u` | Variant |

  For each assumption *b* is the least over every losing candidature *K*,
  with threshold `V(W) − V(K) + 1`; it is almost always the second.

  `rewrite` gives the largest capacity a unit can have under its census, so
  its *b* is a lower bound: no smaller number of units, rewritten in any way
  within their census, changes the winner. The other two are lower bounds
  only under their own assumption.

  If all units together do not reach the threshold, the figure is `null` with
  `"reachable": false`.

  When some units are aggregates, each figure also comes `without_aggregates`:
  the same count with only the polling stations allowed to differ. An
  aggregate can have a census far above its ballots (the overseas row of a
  Spanish province, for example), and then one aggregate alone may reach the
  margin under `rewrite` or `add_to_census`.

**Relation to Aslam, Popa and Rivest.** The idea and the procedure are theirs:
"It assumes that the adversary corrupts the larger precincts first, yielding a
lower bound on the number *b_min* of precincts that must have been corrupted
if the election outcome was changed", where *b_min* "is the least integer such
that 2s Σ_{1≤i≤b_min} v_i ≥ M", with *v_i* "the total number of votes cast" in
precinct *i* and precincts sorted by size. Their per-precinct bound is
`e_i = 2 s v_i` (equation 2, "Linear Error Bound Assumption"), or, in their
section 10, the vote-dependent `e_i = 2 r_i1 + Σ_{j>2} r_ij = v_i + r_i1 − r_i2`,
where *r_ij* are the reported votes of candidate *j*. Three things differ
here, and are this work's:

1. `rewrite` is their section-10 bound with the size of the precinct, *v_i*,
   replaced by its census, *R_u*. They assume "reconciliation": the number of
   votes cast is the same on paper and in the electronic count. Here the
   number of ballots of a unit may itself be different, up to its census.
2. `move` is their equation (2) with `s = 1`, using the winner's votes rather
   than all votes cast in the unit, and `add_to_census` has no counterpart in
   their paper.
3. The threshold is `M + 1` throughout, a tie not counting. Their section 3
   asks for an error `E* > M`; their SAFE formula in section 6 and their
   linear programme in section 12 use `≥ M`.

Their paper is about choosing precincts to audit; this card uses only its
lower bound, and audits nothing.

### 3.2 First round of a two-round election (`first_round`)

Who passes to the second round, and whether anyone wins without one, depends
on rules this work has not read for any country in this state. The card gives
only two descriptive margins, with their diluted margins: between the first
and second candidatures, and between the second and third. It does not say
what either decides, and gives no margin in units.

### 3.3 Seats (`seats`)

Per constituency, with the seats to fill and the allocation rule the context
gives. The only rule implemented is the highest-averages method with
divisors 1, 2, 3… (D'Hondt), a threshold as a percentage of the valid votes
(candidatures plus blank) and equal quotients going to the candidature with
more votes; where the totals are equal too, the context's rule decides by lot
and the card says so. This is the rule of article 163.1 of Spain's LOREG
(and article 180 for local elections, with 5 per cent).

- **Votes to change the allocation, moved:** the least number *t* of votes
  that, moved from one candidature to another, give some candidature another
  number of seats. Every ordered pair is tried with the allocation itself.
  Moving votes only takes seats from the one that loses them and gives them
  to the one that gains them, so the least *t* of each pair is found by
  bisection.
- **Votes to change the allocation, added:** the same with votes added to a
  single candidature, at most `Σ (R_u − B_u)` of the constituency.
- **Diluted margin of the seat:** *t* moved divided by the ballots of the
  constituency. Lindeman and Stark give no diluted margin for an allocation
  by quotients; for a contest with several winners they speak of "the margin
  of decision (between the third-place and fourth-place candidates)". This
  adaptation is this work's.
- **Margin in units of the seat:** the least number of units, from the
  largest capacity down, that could satisfy at least one condition without
  which no allocation changes. If the allocation changes, either a
  candidature with seats falls below the threshold, or some candidature *Y*
  takes a seat that some *X* loses, which needs *Y*'s next quotient to reach
  *X*'s last one (and, if *Y* was below the threshold, needs *Y* to reach it).
  Each condition is linear in the votes. With *s_k* the seats of *k*, *τ* the
  threshold in per cent and *valid_u* the valid votes of a unit:

  | Condition | Gap to close | `rewrite` capacity |
  | --- | --- | --- |
  | *Y* reaches *X*'s last quotient | `(s_Y+1)·V(X) − s_X·V(Y)` | `(s_Y+1)·v_u(X) + s_X·(R_u − v_u(Y))` |
  | *X* falls below the threshold | `100·V(X) − τ·Valid + 1` | `100·v_u(X) + τ·(R_u − valid_u)` |
  | *Y* reaches the threshold | `τ·Valid − 100·V(Y)` | `τ·valid_u − 100·v_u(Y) + (100 − τ)·R_u` |

  With `move` (votes from *X* to *Y*) the capacities are `(s_X+s_Y+1)·v_u(X)`,
  `100·v_u(X)` and `100·v_u(X)`; with `add_to_census` they are
  `s_X·(R_u − B_u)`, `τ·(R_u − B_u)` and `(100 − τ)·(R_u − B_u)`. The figure is
  the least over all conditions, and at least one unit. A quotient tie counts
  here, because the rule gives it to the candidature with more votes. It is a
  lower bound, not the exact number: reaching a condition is necessary for
  the allocation to change, not always enough.

Each figure in units also comes `without_aggregates` when there are
aggregates. When the context does not allow constituencies to be listed, the
card gives only the distribution: how many constituencies would change with fewer than
10, 100 or 1,000 votes moved, or more, and with 1, 2 to 5, or more units
under `rewrite`.

### 3.4 Partial coverage (`partial`)

When the statements cover only part of a constituency that elects as a whole
(two departments of a national election, for example), no margin applies.
Only sections 4 and 5 are given.

## 4. Remote vote

A **channel** is a way of voting away from the voter's polling station:
postal, from abroad, early, or another one the context names. The context
says which units belong to each channel (a pattern on the station
identifier, or the aggregates), or that the authority does not publish the
channel separately.

| Indicator | Definition | Source |
| --- | --- | --- |
| Units and ballots | Units of the channel and their ballots counted | statements |
| Weight | Ballots of the channel over all ballots | statements |
| Against the margin | `single_winner`: whether the ballots of the channel are at least `M + 1`. `seats`: in how many constituencies they are at least the votes to change the allocation by moving | statements |
| Level of publication | `station`, `province`, `state`, `country` or `not_published_separately` | context |
| Chain of custody | Whether the authority publishes it: `yes`, `no` or `unverified` | context |
| By area | Ballots, census and their ratio per constituency, when the context asks for it (overseas vote in Spain) | statements |

"Against the margin" compares sizes only. It says nothing about how those
ballots were cast.

## 5. Verifiability

| Indicator | Definition | Source |
| --- | --- | --- |
| Units with a published result | Stations in the statements over the stations the official totals give, per official-totals document | statements, official |
| Images of the tally sheets | A share if counted; otherwise `published, not counted`, `not published` or `unverified` | context |
| Hashes of the published files | Who publishes them, with which algorithm, and whether they match the files read | context |
| The publications agree | Per official-totals document: areas compared, areas that match, figures that differ, and which sum the official totals match | verifier |
| Recommended practices | The seven practices of the thesis, section 7.1, each `yes`, `no`, `partly` or `unverified`, with its source | context |

## 6. Coverage bound

The margin in units, the other way round: could the stations that have no
statement change the winner, even if every one of their registered voters
had voted for another candidature? The context gives the census of those
stations, `R_without`, with its source.

- `single_winner`: they reach the margin if `R_without ≥ M + 1`, *M* being the
  margin of the statements there are. The card then says "the registered
  voters of the stations without a statement reach the margin", and
  otherwise that they do not. Nothing more.
- `seats`: with no station missing, "complete coverage". Otherwise
  `not_computed` in this version.
- `first_round` and `partial`: `not_applicable`.

## 7. Context

```json
{
  "spec": "actasum/card-context/v0.1",
  "election": "br/presidente/2026-10-04",
  "contest": {"kind": "first_round", "outcome_rule": {"status": "unverified", "note": "..."}},
  "channels": [
    {"name": "abroad", "match": {"station_pattern": "^br/zz/"},
     "published_at": "station", "custody_chain": {"value": "unverified"},
     "source": "..."}
  ],
  "coverage": {"stations_without_statement": 1, "registered_without_statement": 72,
               "source": "..."},
  "images": {"status": "unverified"},
  "hashes": {"value": "...", "status": "computed", "source": "..."},
  "practices": [{"n": 1, "value": "unverified", "source": "..."}],
  "proclamation": {"status": "unverified", "note": "..."}
}
```

For `seats`, `contest` also carries `seats` (constituency → seats to fill),
`threshold_percent`, `ties: "more_votes_then_lot"`, `detail`
(`by_constituency` or `distribution_only`) and the `source` of the seats.
A `channel` may also carry `by_area: true`. A key the context leaves out
makes the card say `unverified` or `not_computed`, never a guess.

## 8. Sources

- Lindeman, M. and Stark, P. B. "A Gentle Introduction to Risk-limiting
  Audits". *IEEE Security and Privacy*, special issue on electronic voting,
  2012. Read in full in the author's preprint "last edited 16 March 2012",
  which says "To appear in IEEE Security and Privacy" and gives no volume or
  pages.
- Aslam, J. A., Popa, R. A. and Rivest, R. L. "On Auditing Elections When
  Precincts Have Different Sizes". USENIX/ACCURATE Electronic Voting
  Technology Workshop (EVT), 2008, as the conference page gives it. Read in
  full in the HTML version printed to PDF; the printed text does not give the
  venue or the year. Formulas read on the page images, because the text
  layer leaves them out.
