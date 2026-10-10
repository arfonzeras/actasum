# Log specification (draft v0.1)

Status: **draft**. Checkpoints are not signed and there are no witnesses yet.
In this state the log detects accidental change and lets third parties repeat
the computation. It does **not** yet protect against a dishonest operator.

## 1. What the log is for

The verifier (see [`core.md`](core.md)) answers "do these statements add up to
the published totals?". The log answers a different question: "is this the
same set of statements everyone else is looking at, and has anything been
changed or removed since?".

It does so with three objects:

- a **checkpoint**, a few bytes that commit to every entry in the log;
- an **inclusion proof**, which shows that one statement is in the log a
  checkpoint describes, without downloading the log;
- a **consistency proof**, which shows that a later checkpoint only *added*
  entries to an earlier one.

## 2. Entries and hashing

- An entry is the canonical JSON form of a statement (`core.md`, section 2).
- Entries are kept in the order they were appended. Nothing is ever edited
  or removed.
- The log is a Merkle tree as defined in RFC 6962, section 2.1, with SHA-256:
  a leaf hashes as `SHA-256(0x00 || entry)` and an inner node as
  `SHA-256(0x01 || left || right)`.
- An entry identical to one already in the log is not appended again.
  Different statements about the same polling station are distinct entries.

## 3. Checkpoint

Three lines, each ended by a newline (`\n`):

```
<origin>
<size>
<base64 of the 32-byte root hash>
```

`origin` names the log; `size` is the number of entries, in decimal without
leading zeros. This is the body of a C2SP checkpoint without extension lines
and without signatures.

## 4. Proofs

Inclusion proof:

| Field | Meaning |
| --- | --- |
| `spec` | `tallylog/inclusion-proof/v0.1` |
| `checkpoint` | `origin`, `size` and base64 `root` the proof was made for |
| `leaf_index` | Position of the entry, counting from 0 |
| `statement` | The statement itself |
| `path` | Audit path, base64 hashes, from the leaf upwards |

Consistency proof:

| Field | Meaning |
| --- | --- |
| `spec` | `tallylog/consistency-proof/v0.1` |
| `old`, `new` | The two checkpoints |
| `path` | Base64 hashes as in RFC 6962, section 2.1.2 |

Both are verified with the algorithms of RFC 9162, section 2.1.

A proof says nothing about the size of the tree beyond what the checkpoint
states. A checker MUST compare the checkpoint in a proof with one it obtained
on its own. Checking a proof only against the checkpoint it carries shows that
the proof is internally coherent, not that the log is the one others see.

## 5. Storage

The reference implementation keeps a log as a directory:

| File | Content |
| --- | --- |
| `leaves.jsonl` | One entry per line, in log order |
| `checkpoint` | The current checkpoint |

Opening a log recomputes the root and refuses to continue if it differs from
the stored checkpoint.

## 6. What is missing

1. **Signatures.** Anyone can write a checkpoint. A later version will sign
   checkpoints in the C2SP signed-note format.
2. **Witnesses.** Independent parties that verify consistency and cosign each
   checkpoint, so that an operator cannot show different logs to different
   people. This is the property that matters most and it is not here yet.
3. **Static serving.** The layout above is not the C2SP `tlog-tiles` layout,
   which is the intended target so that existing tooling and mirrors work.
4. **Evidence.** Entries built from an official dataset carry the hash of
   that dataset. Entries built from a photograph of a tally sheet are not
   specified yet.

## References

- RFC 6962, *Certificate Transparency*, section 2.1.
- RFC 9162, *Certificate Transparency Version 2.0*, section 2.1.
- C2SP, *tlog-checkpoint*, *tlog-tiles*, *tlog-cosignature* and *signed-note*.
  These were consulted through search summaries only and have not been read
  in full for this draft.
