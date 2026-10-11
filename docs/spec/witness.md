# Signed checkpoints and witnesses (draft v0.1)

Status: **draft, not reviewed by anyone outside the project, not audited**.
Do not rely on it to protect anything yet.

## 1. Why

A log on its own asks you to trust whoever runs it. The operator could show
one set of tally sheets to you and another to someone else, or rewrite an
entry and publish a new checkpoint. Two additions close that gap:

- the **log signs** each checkpoint, so a checkpoint can be attributed;
- **witnesses**, run by other organizations, cosign a checkpoint only after
  checking that the log has not changed anything it showed them before.

Someone who requires cosignatures from several independent witnesses can
then trust a checkpoint without trusting the log operator: the operator would
need all those witnesses to collude.

## 2. Formats

Nothing here is new. The formats are the C2SP ones, read in full for this
draft at commit `0b976ab` of the C2SP repository (8 October 2026):

| What | Specification |
| --- | --- |
| Signed text, key IDs, verifier keys | [c2sp.org/signed-note](https://c2sp.org/signed-note) |
| Checkpoint text and its signatures | [c2sp.org/tlog-checkpoint](https://c2sp.org/tlog-checkpoint) |
| What a cosignature signs | [c2sp.org/tlog-cosignature](https://c2sp.org/tlog-cosignature) |
| The request a witness answers | [c2sp.org/tlog-witness](https://c2sp.org/tlog-witness) |

A signed checkpoint looks like this:

```
tallylog/es/congreso/2019-11
59607
RaTDqfj7aHzjaTdadU8GJq9omf6di07amxCw3DARqAc=

— tallylog/es/congreso/2019-11 <base64: key ID and the log's signature>
— witness.example/w1 <base64: key ID, timestamp and the witness's signature>
```

Signature types implemented, both Ed25519:

| Type | Used by | Signs |
| --- | --- | --- |
| `0x01` | the log | the checkpoint text |
| `0x04` | a witness | `cosignature/v1`, the time, then the checkpoint text |

A verifier key has the form `<name>+<hex key ID>+<base64 of type and key>`.

## 3. What a witness does

For each log it follows, a witness stores the size and root of the last
checkpoint it cosigned. A request carries the size the log believes the
witness last saw, a consistency proof from that size, and the new signed
checkpoint. The witness answers as the `add-checkpoint` call specifies:

| Answer | When |
| --- | --- |
| 200, a cosignature line | The log's signature verifies and the log only grew |
| 400 | The request is malformed, or the old size exceeds the new one |
| 403 | No valid signature from a key the witness trusts for that log |
| 404 | The witness does not follow that log |
| 409, the size it has | The old size is not the one the witness last cosigned |
| 422 | The consistency proof fails, or same size with a different root |

The first checkpoint a witness sees for a log is accepted as it is: there is
nothing earlier to be consistent with. Checking the old size and storing the
new checkpoint happen under a lock, and the new state is written to disk
before the cosignature is returned.

## 4. What a checker does

`tallylog log check-checkpoint` takes the log's verifier key, the verifier
keys of the witnesses the checker trusts, and how many of them must have
cosigned (the quorum). It follows the signed-note rules: signatures from
unknown keys are ignored, and a signature that claims to come from a trusted
key but does not verify invalidates the whole checkpoint.

Which witnesses to trust and what quorum to require is a policy decision of
whoever checks. This draft does not set one.

## 5. Limits

1. **A witness on the same machine proves nothing.** The property comes from
   witnesses being run by organizations that do not answer to the log
   operator. This repository provides the mechanism, not the independence.
2. **Ed25519 only.** The specifications recommend ML-DSA-44 (type `0x06`) for
   new deployments, because it resists quantum computers and binds the
   cosigner's name. It is not implemented.
3. **No network protocol.** Requests and answers travel as files. The HTTP
   interface of the witness specification is not implemented, nor is the
   monitoring endpoint.
4. **Interoperability is only partly checked.** Log signatures (`0x01`) verify
   the example given in the signed-note specification. Cosignatures (`0x04`)
   follow the text of the specification but have not been checked against
   another implementation.
5. **Keys are plain files** readable only by their owner. There is no hardware
   key support, no rotation and no revocation.
6. **Checkpoint extension lines** are not supported; a checkpoint has exactly
   three lines.
7. A witness attests that the log is append-only. It says nothing about
   whether the entries are true.
