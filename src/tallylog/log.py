"""An append-only log of statements, with inclusion and consistency proofs.

The log is a directory with two files:

* ``leaves.jsonl``: one canonical statement per line, in the order appended.
* ``checkpoint``: the log's origin, its size and its Merkle root.

A *checkpoint* commits to the whole log. An *inclusion proof* shows that one
statement is in the log a checkpoint describes. A *consistency proof* shows
that a later checkpoint only added entries to an earlier one.

The log can sign its checkpoint and collect cosignatures from witnesses (see
``note.py`` and ``witness.py``). Without them it only protects against
accidental change. See docs/spec/log.md.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Iterable

from . import merkle
from .statement import FormatError, Statement, canonical_json

INCLUSION_SPEC = "tallylog/inclusion-proof/v0.1"
CONSISTENCY_SPEC = "tallylog/consistency-proof/v0.1"
LEAVES = "leaves.jsonl"
CHECKPOINT = "checkpoint"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(text: Any, name: str) -> bytes:
    try:
        data = base64.b64decode(text, validate=True)
    except (ValueError, TypeError) as exc:
        raise FormatError(f"{name} is not valid base64") from exc
    if len(data) != 32:
        raise FormatError(f"{name} must be a 32-byte hash")
    return data


@dataclass(frozen=True)
class Checkpoint:
    """Origin, size and root hash of a log: the body of a C2SP checkpoint."""

    origin: str
    size: int
    root: bytes

    def text(self) -> str:
        return f"{self.origin}\n{self.size}\n{_b64(self.root)}\n"

    @classmethod
    def parse(cls, text: str) -> "Checkpoint":
        lines = text.split("\n")
        if len(lines) != 4 or lines[3] != "":
            raise FormatError("a checkpoint has three lines, each ended by a newline")
        origin, size, root = lines[0], lines[1], lines[2]
        if not origin:
            raise FormatError("checkpoint origin is empty")
        if not size.isdigit() or (len(size) > 1 and size[0] == "0"):
            raise FormatError("checkpoint size is not a decimal number")
        return cls(origin=origin, size=int(size), root=_unb64(root, "checkpoint root"))

    def to_dict(self) -> dict[str, Any]:
        return {"origin": self.origin, "size": self.size, "root": _b64(self.root)}

    @classmethod
    def from_dict(cls, doc: Any) -> "Checkpoint":
        if not isinstance(doc, dict) or not isinstance(doc.get("origin"), str):
            raise FormatError("checkpoint must be an object with an origin")
        size = doc.get("size")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise FormatError("checkpoint size must be a non-negative integer")
        return cls(doc["origin"], size, _unb64(doc.get("root"), "checkpoint root"))


class Log:
    """A log held in memory and mirrored to a directory."""

    def __init__(
        self, path: str, origin: str, leaves: list[bytes], signatures: str = ""
    ):
        self.path = path
        self.origin = origin
        self.leaves = leaves
        self.signatures = signatures  # signature lines for the current checkpoint
        self.hashes = [merkle.leaf_hash(leaf) for leaf in leaves]
        self._ids = {merkle.leaf_hash(leaf) for leaf in leaves}

    # -- storage ---------------------------------------------------------

    @classmethod
    def create(cls, path: str, origin: str) -> "Log":
        if not origin or "\n" in origin:
            raise FormatError("origin must be a non-empty single line")
        os.makedirs(path, exist_ok=True)
        if os.path.exists(os.path.join(path, LEAVES)):
            raise FormatError(f"{path}: a log already exists here")
        log = cls(path, origin, [])
        log._write([])
        return log

    @classmethod
    def open(cls, path: str) -> "Log":
        """Load a log and check it against its own checkpoint."""
        try:
            with open(os.path.join(path, CHECKPOINT), encoding="utf-8", newline="") as handle:
                stored = handle.read()
            with open(os.path.join(path, LEAVES), "rb") as handle:
                raw = handle.read()
        except FileNotFoundError as exc:
            raise FormatError(f"{path}: not a log directory") from exc
        body, separator, signatures = stored.partition("\n\n")
        recorded = Checkpoint.parse(body + "\n" if separator else stored)
        if separator:
            from .note import parse_signature_lines

            parse_signature_lines(signatures)  # refuse a damaged checkpoint file
        leaves = raw.split(b"\n")
        if leaves.pop() != b"":
            raise FormatError(f"{path}: {LEAVES} does not end with a newline")
        for number, leaf in enumerate(leaves, start=1):
            try:
                statement = Statement.from_dict(json.loads(leaf))
            except (json.JSONDecodeError, FormatError) as exc:
                raise FormatError(f"{path}: entry {number}: {exc}") from exc
            if statement.canonical() != leaf:
                raise FormatError(f"{path}: entry {number} is not in canonical form")
        log = cls(path, recorded.origin, leaves, signatures)
        if log.checkpoint() != recorded:
            raise FormatError(
                f"{path}: the entries do not match the checkpoint "
                f"(checkpoint says size {recorded.size}, found {len(leaves)} entries"
                + (", same size but a different root" if recorded.size == len(leaves) else "")
                + ")"
            )
        return log

    def _write(self, new_leaves: list[bytes]) -> None:
        if new_leaves:
            with open(os.path.join(self.path, LEAVES), "ab") as handle:
                handle.write(b"".join(leaf + b"\n" for leaf in new_leaves))
        elif not os.path.exists(os.path.join(self.path, LEAVES)):
            open(os.path.join(self.path, LEAVES), "wb").close()
        temporary = os.path.join(self.path, CHECKPOINT + ".tmp")
        with open(temporary, "w", encoding="utf-8", newline="") as handle:
            handle.write(self.signed_checkpoint())
        os.replace(temporary, os.path.join(self.path, CHECKPOINT))

    # -- operations ------------------------------------------------------

    def checkpoint(self) -> Checkpoint:
        return Checkpoint(self.origin, len(self.leaves), merkle.root(self.hashes))

    def signed_checkpoint(self) -> str:
        """The checkpoint as stored: a signed note once it has signatures."""
        text = self.checkpoint().text()
        return text + "\n" + self.signatures if self.signatures else text

    def sign(self, signer) -> None:
        """Sign the current checkpoint with the log's own key."""
        if signer.name != self.origin:
            raise FormatError(
                f"the key is named {signer.name!r} but the log's origin is {self.origin!r}"
            )
        self.add_signatures(signer.sign(self.checkpoint().text()))

    def add_signatures(self, lines: str) -> int:
        """Attach signature lines to the current checkpoint. Returns how many were new."""
        from .note import parse_signature_lines

        have = {(s.name, s.id) for s in parse_signature_lines(self.signatures)} if self.signatures else set()
        added = 0
        for signature in parse_signature_lines(lines):
            if (signature.name, signature.id) not in have:
                have.add((signature.name, signature.id))
                self.signatures += signature.line
                added += 1
        self._write([])
        return added

    def witness_request(self, old_size: int) -> str:
        """The body of an add-checkpoint request, per c2sp.org/tlog-witness."""
        size = len(self.leaves)
        if not 0 <= old_size <= size:
            raise FormatError(f"old size must be between 0 and {size}, got {old_size}")
        if not self.signatures:
            raise FormatError("sign the checkpoint before asking a witness to cosign it")
        proof = (
            merkle.consistency_proof(self.hashes, old_size) if 0 < old_size < size else []
        )
        lines = [f"old {old_size}"] + [_b64(h) for h in proof]
        return "\n".join(lines) + "\n\n" + self.signed_checkpoint()

    def append(self, statements: Iterable[Statement]) -> tuple[int, int]:
        """Append statements. Returns (added, skipped as already present)."""
        added: list[bytes] = []
        skipped = 0
        for statement in statements:
            leaf = statement.canonical()
            digest = merkle.leaf_hash(leaf)
            if digest in self._ids:
                skipped += 1
                continue
            self._ids.add(digest)
            self.leaves.append(leaf)
            self.hashes.append(digest)
            added.append(leaf)
        if added:
            self.signatures = ""  # they belonged to the previous checkpoint
        self._write(added)
        return len(added), skipped

    def find(self, station: str) -> list[int]:
        """Indexes of every entry for ``station``, in log order."""
        return [
            index
            for index, leaf in enumerate(self.leaves)
            if json.loads(leaf)["station"] == station
        ]

    def prove_inclusion(self, index: int) -> dict[str, Any]:
        return {
            "spec": INCLUSION_SPEC,
            "checkpoint": self.checkpoint().to_dict(),
            "leaf_index": index,
            "statement": json.loads(self.leaves[index]),
            "path": [_b64(h) for h in merkle.inclusion_proof(self.hashes, index)],
        }

    def prove_consistency(self, old_size: int) -> dict[str, Any]:
        if not 0 < old_size <= len(self.leaves):
            raise FormatError(
                f"old size must be between 1 and {len(self.leaves)}, got {old_size}"
            )
        return {
            "spec": CONSISTENCY_SPEC,
            "old": Checkpoint(
                self.origin, old_size, merkle.root(self.hashes[:old_size])
            ).to_dict(),
            "new": self.checkpoint().to_dict(),
            "path": [_b64(h) for h in merkle.consistency_proof(self.hashes, old_size)],
        }


def check_checkpoint(data: str, log_key, witness_keys=(), quorum: int = 0):
    """Check a signed checkpoint against a trust policy.

    The log's own signature must verify, and at least ``quorum`` of the given
    witnesses must have cosigned. Returns the checkpoint and the verifications.
    """
    from .note import COSIGNATURE, LOG_SIGNATURE, SignatureError, open_note

    if log_key.kind != LOG_SIGNATURE:
        raise FormatError("the log key must be a log-signature key")
    if any(key.kind != COSIGNATURE for key in witness_keys):
        raise FormatError("witness keys must be cosignature keys")
    note, verified = open_note(data, [log_key, *witness_keys])
    checkpoint = Checkpoint.parse(note.text)
    if log_key.name != checkpoint.origin:
        raise SignatureError("the log key does not belong to this log's origin")
    if not any(v.verifier == log_key for v in verified):
        raise SignatureError("the checkpoint is not signed by the log's key")
    witnesses = {v.verifier.name for v in verified if v.verifier != log_key}
    if len(witnesses) < quorum:
        raise SignatureError(
            f"{len(witnesses)} trusted witness(es) cosigned, the policy requires {quorum}"
        )
    return checkpoint, verified


def _path(doc: dict[str, Any]) -> list[bytes]:
    path = doc.get("path")
    if not isinstance(path, list):
        raise FormatError("proof path must be an array")
    return [_unb64(item, "proof path entry") for item in path]


def verify_inclusion_proof(
    proof: dict[str, Any], trusted: Checkpoint | None = None
) -> tuple[Statement, Checkpoint]:
    """Check an inclusion proof. Raises ``FormatError`` if it does not hold.

    ``trusted`` is a checkpoint the caller obtained on its own (from a witness,
    a mirror, an earlier download). Without it the proof is checked against the
    checkpoint it carries, which shows internal coherence and nothing more.
    """
    if not isinstance(proof, dict) or proof.get("spec") != INCLUSION_SPEC:
        raise FormatError("not an inclusion proof")
    embedded = Checkpoint.from_dict(proof.get("checkpoint"))
    checkpoint = trusted or embedded
    if trusted is not None and trusted != embedded:
        raise FormatError(
            "the proof was made for a different checkpoint than the trusted one "
            f"(proof: size {embedded.size}; trusted: size {trusted.size})"
        )
    index = proof.get("leaf_index")
    if isinstance(index, bool) or not isinstance(index, int):
        raise FormatError("leaf_index must be an integer")
    statement = Statement.from_dict(proof.get("statement"))
    if canonical_json(proof["statement"]) != statement.canonical():
        raise FormatError("the statement in the proof has fields the format does not define")
    leaf = merkle.leaf_hash(statement.canonical())
    if not merkle.verify_inclusion(leaf, index, checkpoint.size, _path(proof), checkpoint.root):
        raise FormatError("the inclusion proof does not hold")
    return statement, checkpoint


def verify_consistency_proof(
    proof: dict[str, Any],
    trusted_old: Checkpoint | None = None,
    trusted_new: Checkpoint | None = None,
) -> tuple[Checkpoint, Checkpoint]:
    """Check that the new checkpoint only adds entries to the old one."""
    if not isinstance(proof, dict) or proof.get("spec") != CONSISTENCY_SPEC:
        raise FormatError("not a consistency proof")
    old = Checkpoint.from_dict(proof.get("old"))
    new = Checkpoint.from_dict(proof.get("new"))
    if trusted_old is not None and trusted_old != old:
        raise FormatError("the proof starts from a different checkpoint than the trusted old one")
    if trusted_new is not None and trusted_new != new:
        raise FormatError("the proof ends at a different checkpoint than the trusted new one")
    if old.origin != new.origin:
        raise FormatError("the two checkpoints belong to different logs")
    if not merkle.verify_consistency(old.size, new.size, old.root, new.root, _path(proof)):
        raise FormatError("the consistency proof does not hold")
    return old, new
