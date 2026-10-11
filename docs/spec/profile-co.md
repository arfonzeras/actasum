# Colombia profile (draft `co/codigo-electoral/v0.1`)

Status: **draft, run on two departments**: the per-station file of Bogotá D.C. for
the presidential election of 31 May 2026 (see
[`../findings/co-presidente-2026.md`](../findings/co-presidente-2026.md)).
Everything here was learnt from that file, from three records of scrutiny
commissions and from two scanned tally sheets. Nothing has been checked
against the law itself, and no Colombian organisation has reviewed it.

## 1. How the count travels

According to a document of the Registraduría Nacional del Estado Civil
(*Conoce los distintos formularios electorales y en qué casos se usan*, 2026):

1. At the polling station (*mesa*) the jurors fill in form **E-14** by hand,
   in three copies (*claveros*, *delegados*, *transmisión*). Party witnesses
   and observers may photograph it. The three copies are scanned and
   published.
2. Scrutiny commissions then go over the results. The records seen name four
   levels above the station: auxiliary, zonal, municipal or district, and
   general (departmental). A commission may change a station's figures
   because of arithmetic errors, erasures, incomplete data, claims, or a
   decision that applies to every station, such as a candidate's withdrawal.
3. Each commission issues form **E-24** (results table), form **E-26**
   (summary) and an *Acta General de Escrutinio* (AGE) that records, among
   other things, every change it made to a station: date and time, the
   option, the previous vote and the new vote.

The Registraduría's document says that differences between the E-14 and the
commissions' forms are not irregularities in themselves.

## 2. Identifiers

| Core field | Form | Example |
| --- | --- | --- |
| `election` | `co/presidente/<yyyy>-<mm>` | `co/presidente/2026-05` |
| `constituency` | `co` | `co` |
| `station` | `co/<department>/<municipality>/<zone>/<post>/<station>` | `co/16/001/01/01/001` |
| candidature code | `<party>-<option>` | `0026-001` |

Codes are those of the published files. The post (*puesto*) code can contain
letters. The station number is written with three digits.

Only the presidential election (corporation code `01`) is supported. Congress
elections use preferential votes within lists and need their own mapping.

## 3. Source: the MMV file

The scrutiny site of each election publishes, per commission, a file named
`MMV_….csv`: semicolon-separated, UTF-8, with a header, one row per station
and voting option that received votes.

| Column | Used as |
| --- | --- |
| `DEP`, `MUN`, `ZONA`, `PUESTO`, `MESA` | station identifier |
| `CORCODIGO` | election type |
| `PAR`, `CAN` | candidature code; party `0000` marks the three rows below |
| `CAN` = `996` | `counts.blank` |
| `CAN` = `997` | `counts.null` |
| `CAN` = `998` | `counts.other.unmarked` (*votos no marcados*) |
| `VOTOS` | the figure |
| `CANCEDULA` | **not copied**: the candidate's identity number |

The file does not carry the date of the election; it is given on the command
line.

Statements built from this file have `stage: canvass`: the file holds the
figures as the commission left them, not the tally sheet. In the one file
run, options with no votes left have no row at all.

## 4. Source: the changes recorded in the AGE

`actasum co convert --age-text` takes the text of the AGE of the same
commission (`pdftotext -layout AGE.pdf AGE.txt`) and reads every entry of the
form "se modificó la votación" with its previous and new vote.

For each station with changes the reader builds a second statement by undoing
them, from last to first. Each change is checked on the way: its new vote has
to be the figure standing at that point, starting from the MMV file. If any
change of a station fails that check, no earlier statement is built for it and
the change is reported.

The two statements are both `stage: canvass`, and the one from the MMV file
names the earlier one in `supersedes`. The earlier one is **not** the tally
sheet: commissions below this one may already have changed the figures. A
statement with `stage: count` can only come from an E-14.

The AGE and the E-14 carry names and identity numbers of officials and
jurors. None of that is read or stored.

## 5. Known gaps and unverified assumptions

1. One election, two departments (Bogotá D.C. and Córdoba). Other
   departments, the second round and Congress elections have not been tried.
1a. The record of changes can be read when the AGE is a PDF with text, as
   Bogotá's is. Córdoba's is a scan; character recognition was not reliable
   enough, and the profile has no answer for that yet.
2. Official totals come from scanned forms (E-26, E-24) typed by hand. The
   profile has no reader for them.
3. The published MMV file run was not the file the commission generated: it
   starts with a stray line and its last row is cut short. When the hash the
   commission recorded is known (it is read from the AGE, or given with
   `--sha256`), the reader rebuilds the original and accepts it only if the
   hash agrees; the statements then carry both hashes. Otherwise it reports
   the defects and reads what is there. Only this one pattern of damage is
   handled.
3a. A station with no votes at all has no row in the file and so produces no
   statement. The station count then falls short of the official one.
4. On the Congress scrutiny site the links to the MMV files returned the
   site's own page instead of a file on 11 October 2026.
5. E-14 forms are scanned handwriting. Nothing here transcribes them. Bulk
   download of the scans is offered to parties and observer missions with
   credentials, not to the public; the site's terms of use have not been read.
6. The legal basis (Código Electoral, Ley 1475 de 2011, resolutions of the
   Consejo Nacional Electoral) has not been read. The profile's name was
   checked on 11 October 2026 against one document only: the Registraduría's
   handbook for scrutiny commissions of the 2026 presidential election, read
   through an automatic extract, bases them on the Código Electoral (Decreto
   Ley 2241 de 1986, articles 134 to 193) and on Ley 1475 de 2011 (articles
   41 to 45), and mentions no newer code. The description in section 1
   rests on the Registraduría's own explanatory document and on the records.
7. Whether a withdrawn candidate's votes must become unmarked votes is taken
   from what the record shows the commission did, not from the rule.
