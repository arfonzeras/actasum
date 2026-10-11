# Findings: Spain, European Parliament and local elections

Runs of 11 October 2026 on the per-station ZIP files published by the
Ministry of the Interior, with `actasum` at commit `4a69045`; the seat check and the 2019 runs were
added afterwards the same day. Two elections of each type have been run.

```sh
actasum es describe --mesa 07202406_MESA.zip                  # what the ZIP contains
actasum es replay   --mesa 07202406_MESA.zip                  # national constituency
actasum es replay   --mesa 07202406_MESA.zip --level province # per province
actasum es replay   --mesa 04202305_MESA.zip                  # one constituency per municipality
actasum es seats    --mesa 04202305_MESA.zip                  # would a difference change a seat?
```

As in the Congreso runs, everything below compares the Ministry's
publications **with each other**. Nothing here has been compared with paper
tally sheets or with the results proclaimed by the electoral boards. A
difference means two published figures do not add up; it does not say which
one is right, or why.

| Election | ZIP (SHA-256) | Polling stations | Constituencies matching |
| --- | --- | --- | --- |
| European Parliament, June 2024 | `07202406_MESA.zip` (`ed30e4cf…b6659b`) | 58,556, plus 52 overseas rows | 1 of 1 |
| European Parliament, May 2019 | `07201905_MESA.zip` (`8199711b…c1a474`) | 60,076, plus 52 overseas rows | 0 of 1 |
| Local, May 2023 | `04202305_MESA.zip` (`20dac696…ab0de3`) | 57,681 | 5,248 of 5,272 |
| Local, May 2019 | `04201905_MESA.zip` (`b8b1c649…02e204`) | 57,188 | 5,270 of 5,291 |

Full hashes, in the same order:
`ed30e4cf11772afb0785f2992f44fa191b8671f933865335b7093ac9ccb6659b`,
`8199711babd4b61ee4940469351ab4a263b0cf84a84ccfbe04ab1970a4c1a474`,
`20dac696cd2efaa63c9346384ddb682f3da4fda92c6af67447159a60f1ab0de3` and
`b8b1c649e3841ba735383152fd3a38259a336698d1eb79f7a653cae54c02e204`.

All four ZIPs follow the layout document: same files, same line lengths, same
kinds of rows. In both local elections the smallest population in file `05`
is 251 and the largest in file `11` is 250.

## European Parliament, June 2024

The station rows and the 52 overseas rows add up exactly to the national row:
number of stations, blank votes, null votes and every candidature. Compared
per province, all 52 provinces match too.

The national rows merge candidatures. File `03` lists 60 candidatures, 26 of
which are accumulated at national level under the code of another one, and
the national candidature rows are 34, which is 60 minus 26. The match was
obtained after merging the station votes the same way. None of the 60 is
merged at province or region level.

The files follow the layout document: same line lengths as in the Congreso
files, 20 overseas subtotal rows with province `99` in file `09` (19 regions
and the country), 52 overseas rows.

Not run for this election: the municipality level and the overseas residual.

## European Parliament, May 2019

Here the three levels the Ministry publishes do not add up to each other.

| Level compared with the stations | Areas matching |
| --- | --- |
| Country (the constituency) | 0 of 1 |
| Province | 38 of 52 |
| Municipality | 8,126 of 8,131 |
| Overseas row against province total minus municipalities | 42 of 52 |

Votes for candidatures, added up four ways:

| Source | Votes for candidatures |
| --- | --- |
| National row of file `07` | 22,209,330 |
| Sum of the 52 province rows of file `07` | 22,209,330 |
| Sum of the municipal rows of file `05`, plus the 52 overseas rows | 22,257,948 |
| Sum of the station rows of file `09`, plus the 52 overseas rows | 22,258,966 |

The station file and the municipal file are 1,018 votes apart, all of it in
five municipalities. The province rows are 49,636 votes below the stations,
in 14 provinces, and 42,782 of those are in Barcelona (`es/08`); the Balearic
Islands (`es/07`) follow with 3,080 and Huesca (`es/22`) with 1,297. In
Barcelona and the Balearic Islands the province row is lower than the sum of
its own municipalities, so the residual left for the overseas vote is
negative. The number of polling stations is the same at every level. Every
candidature is lower in the province rows; none is higher.

The national figures of file `07` are the ones commonly given as the result
of that election (for example 7,369,789 votes for the first list, 216,736
blank and 193,918 null). That was checked against a secondary source only,
not against the official gazette. If it holds, the totals file carries the
final figures here and the two lower levels carry something else; why they
are higher has not been looked into.

The national rows merge 49 of 81 candidatures.

Two stations have more ballots than registered voters:
`es/08/019/06/020/U` (902 and 821) and `es/45/075/01/001/U` (125 and 124).

## Local, May 2019

5,270 of 5,291 municipalities match their stations in every figure; 21 do
not, with 117 differing items. No station has an internal inconsistency.
File `11` lists 2,830 more municipalities, which are not compared.

The 21 municipalities, by the name in file `05`: el Campello, Cordobilla de
Lácara, Herrera del Duque, Aranda de Duero, Jerez de la Frontera,
Peñarroya-Pueblonuevo, Mengíbar, Bedmar y Garcíez, Astorga, Valdevimbre,
Monterroso, Burela, Funes, Las Palmas de Gran Canaria, Puerto del Rosario,
Cambados, Pelabravo, Sebúlcor, Miguel Esteban, la Granja de la Costera and
Melilla. `actasum es replay --mesa 04201905_MESA.zip --limit 200` prints
every item.

`actasum es seats --mesa 04201905_MESA.zip`: in 5,274 municipalities both
sets of votes lead to the published seats, 9 are left out because the last
seat is settled by lot, and 8 need explaining. They fall into three kinds.

Station votes lead to a different allocation; the municipal file's votes
lead to the published one (the pattern of the five municipalities of 2023):

| Municipality | Published seats | What the station votes give | What differs in the votes |
| --- | --- | --- | --- |
| Cordobilla de Lácara (`es/06/038`) | PSOE 4, ESTREMEÑUS 3 | PSOE 3, ESTREMEÑUS 3, Cs 1 | every candidature, and blank and null votes |
| Valdevimbre (`es/24/187`) | PP 3, PSOE 2, CRA 1, Cs 1, an independent list 1, U.P.L. 1 | PSOE 3 and the independent list 0 | the independent list has 59 votes in the municipal file and none in the station file |
| Pelabravo (`es/37/240`) | PP 5, PSOE 3, Cs 1 | PP 5, Cs 3, PSOE 1 | PSOE and Cs have each other's figures (255 and 84) |
| la Granja de la Costera (`es/46/137`) | PP 4, PSOE 3 | PSOE 4, PP 3 | PP 120 against 106, PSOE 103 against 107 |

The published seats are what the station votes give, not what the municipal
file's own votes give (as in Guadassuar in 2023):

- Monterroso (`es/27/032`): published PSOE 3, IxM 4. The municipal file has
  PSOE 799 and IxM 798; the station file has them the other way round.

The published seats are what neither set of votes gives, and the two sets of
votes agree with each other:

- León (`es/24/089`): published U.P.L. 2 and VOX 1. VOX has 3,199 of 64,449
  valid votes, 4.96 per cent, below the 5 per cent threshold, so the votes
  give U.P.L. 3 and VOX none. The threshold is applied here to candidature
  votes plus blank votes.
- Bonrepòs i Mirambell (`es/46/074`): published PP 3 and COMPROMÍS 3; the
  votes give PP 4 and COMPROMÍS 2, the last seat by 150.5 against 150.33.
- els Poblets (`es/03/901`): the published seats add up to 10 and there are
  11 to fill; the votes give COMPROMÍS a third seat.

None of these eight has been checked against a third source.

## Local, May 2023

What the ZIP contains agrees with the layout document on three points: the
per-station files have no overseas rows and no subtotal rows; a second set of
files of election type `10` reuses numbers `05` to `08` and was set aside;
and files `11` and `12` hold municipalities without station detail.

- 5,272 municipalities have a whole-municipality row in file `05`, and the
  per-station file has stations for exactly those 5,272.
- File `11` lists 2,815 more municipalities. This profile does not read
  them, so they are outside the comparison. The split is the one the law
  draws (LOREG arts. 179 and 184): the smallest population in file `05` is
  251 and the largest in file `11` is 250. Together that makes 8,087
  municipalities; the Congreso files of July 2023 have 8,131. The gap of 44
  has not been looked into.

Of the 5,272 municipalities compared, 5,248 match their polling stations in
every figure and 24 do not. The report lists 105 differing items in those 24;
`actasum es replay --mesa 04202305_MESA.zip --limit 200` prints them all.

| Municipality | Name in file `05` | Seats | Differing items | Largest difference | Votes for candidatures, stations minus municipal file | Seats implied by the station votes |
| --- | --- | --- | --- | --- | --- | --- |
| `es/04/045` | Fiñana | 9 | 8 | 52 | −32 | same |
| `es/04/049` | Garrucha | 17 | 6 | 120 | −120 | **different** |
| `es/07/057` | Santanyí | 17 | 3 | 175 | 0 | **different** |
| `es/09/330` | Salas de los Infantes | 9 | 1 | 3 | −3 | same |
| `es/10/159` | Robledollano | 7 | 3 | 1 | +1 | same |
| `es/19/046` | Azuqueca de Henares | 21 | 3 | 1 | −1 | same |
| `es/19/130` | Guadalajara | 25 | 2 | 1 | −1 | same |
| `es/30/003` | Águilas | 21 | 2 | 185 | 0 | same |
| `es/30/018` | Ceutí | 17 | 7 | 26 | +5 | **different** |
| `es/30/024` | Lorca | 25 | 6 | 11 | −11 | same |
| `es/32/023` | Castro Caldelas | 9 | 6 | 77 | −77 | same |
| `es/39/044` | Miengo | 13 | 7 | 42 | −42 | **different** |
| `es/40/219` | Vallelado | 7 | 3 | 1 | −1 | **different** |
| `es/46/116` | L'Eliana | 17 | 3 | 1 | +1 | same |
| `es/46/139` | Guadassuar | 13 | 2 | 152 | 0 | same (see below) |
| `es/47/054` | Cogeces del Monte | 7 | 3 | 28 | −28 | same |
| `es/48/071` | Muskiz | 13 | 3 | 1 | −1 | same |
| `es/48/082` | Santurtzi | 21 | 3 | 2 | −2 | same |
| `es/49/023` | Bermillo de Sayago | 9 | 5 | 1 | −1 | same |
| `es/49/127` | Morales del Vino | 11 | 2 | 4 | 0 | same |
| `es/49/275` | Zamora | 25 | 3 | 3 | −3 | same |
| `es/50/067` | Calatayud | 17 | 2 | 1 | −1 | same |
| `es/51/001` | Ceuta | 25 | 11 | 135 | −135 | same |
| `es/52/001` | Melilla | 25 | 11 | 211 | −211 | same |

### Would a difference change who gets a seat?

In a local election the municipality is the constituency, so these are
differences at the level where seats are allotted. File `05` gives the seats
to fill in each municipality and file `06` the seats each candidature
obtained. `actasum es seats --mesa 04202305_MESA.zip` applies the method of
LOREG articles 163.1 and 180 (highest quotients, 5 per cent threshold) twice,
to the votes of the municipal file and to the votes added up from the
stations, and compares both with the published seats.

- In 5,257 municipalities both sets of votes lead to the published seats.
- 9 municipalities are left out because the last seat falls on a tie that the
  law settles by lot.
- In 5 municipalities the station votes lead to a different allocation from
  the published one, while the municipal file's own votes lead to the
  published one:

| Municipality | Published seats (and what the municipal file's votes give) | What the station votes give |
| --- | --- | --- |
| Garrucha (`es/04/049`) | PSOE 7, PP 6, CON ANDALUCÍA 2, UCIN 1, VOX 1 | PP 7 and CON ANDALUCÍA 1 |
| Santanyí (`es/07/057`) | PP 11, SUMA 4, PSIB-PSOE 1, VOX 1 | SUMA 3 and PSIB-PSOE 2 |
| Ceutí (`es/30/018`) | PSOE 8, PP 5, VOX 3, CS 1 | PSOE 9 and VOX 2 |
| Miengo (`es/39/044`) | PP 7, PSOE 2, P.R.C. 2, EQUO 1, VOX 1 | EQUO 2 and VOX 0 |
| Vallelado (`es/40/219`) | PP 5, PSOE 2 | PP 6 and PSOE 1 |

  Party labels are the short names in file `03`.

- In Guadassuar (`es/46/139`) it is the other way round. The published seats
  (PP 6, ACORD PER GUANYAR 4, PSOE 3) are what the station votes give. The
  municipal file's own votes (PP 1,711, ACORD PER GUANYAR 842, PSOE 842)
  would give PP 7 and ACORD PER GUANYAR 3. The station votes are PP 1,559
  and ACORD PER GUANYAR 994: 152 votes sit with a different candidature in
  each file.

In Vallelado the whole difference is one ballot: the station file has 93
votes for PSOE and 9 null votes, the municipal file 94 and 8.

### What a third source says, for three of them

For three municipalities a source outside the Ministry's files was found. In
all three it agrees with the municipal file, not with the per-station file.

- **Fiñana and Ceutí.** A resolution of the Presidency of the Junta Electoral
  Central of 28 December 2023
  ([BOE-A-2024-129](https://www.boe.es/boe/dias/2024/01/02/pdfs/BOE-A-2024-129.pdf))
  publishes the results of partial local elections held on 26 November 2023.
  Its figures for Fiñana (PSOE 648, PP 388, VOX 329, 9 blank, 7 null) and for
  Ceutí (PSOE 2,842 and 8 councillors, PP 1,845 and 5, VOX 956 and 3, Cs 347
  and 1, 56 blank, 146 null) are those of the municipal file. A press report
  of 5 July 2023 says a court had ordered the vote to be repeated in two
  polling stations of Ceutí
  ([elDiario.es](https://www.eldiario.es/murcia/politica/tsj-ordena-repita-votacion-mesas-electorales-municipio-murciano-ceuti_1_10352202.html)).
- **Santanyí.** A press report of 31 May 2023 says the figures first
  published for Santanyí were wrong and gives the corrected ones (PP 3,011,
  Suma 1,036, PSOE 470, VOX 302), with one councillor passing from PSOE to
  Suma
  ([Última Hora](https://www.ultimahora.es/noticias/elecciones-28m/2023/05/31/1947535/resultados-elecciones-28m-mallorca-error-provoca-psoe-pierda.html)).
  The corrected figures are those of the municipal file; the earlier ones
  (PP 2,895, Suma 977, PSOE 645) are those of the per-station file.

Both web sources were read through an automatic extract, not in full.

What this supports, for these three municipalities: the municipal file was
brought up to date after the results changed (a correction in one case, a
repeated vote in two) and the per-station file was not. The dates of the
files inside the ZIP point the same way without proving it: file `06` is
dated June 2025 and files `09` and `10` September 2024. Whether the same
holds for the other 21 municipalities has not been checked. No third source
was found for Garrucha, Miengo or Vallelado with one search each.

This bears on a gap noted in the profile: a statement built from the
per-station file may describe the count as first recorded, not the result
that stood in the end.

### Stations with internal inconsistencies

| Station | Check | Detail |
| --- | --- | --- |
| `es/09/330/01/001/A` | candidature sum | rows add up to 382, station total 383 |
| `es/09/330/01/001/B` | candidature sum | rows add up to 315, station total 317 |
| `es/24/056/01/001/B` | candidature sum | rows add up to 392, station total 394 |
| `es/15/066/01/001/B` | candidature sum | rows add up to 401, station total 408 |
| `es/03/019/03/005/A` | candidature sum | rows add up to 367, station total 368 |
| `es/03/019/04/002/U` | candidature sum | rows add up to 472, station total 468 |
| `es/46/104/01/002/U` | more ballots than registered | 492 ballots, 487 registered |

The candidature-sum check did not fire in the European Parliament run or in
the November 2019 Congreso run repeated the same day. For the other Congreso
runs the findings record only stations with more ballots than registered.
