"""A witness: an independent party that cosigns a log's checkpoints.

A witness remembers, for each log it follows, the last checkpoint it cosigned.
It cosigns a new one only if the log's own signature is valid and a
consistency proof shows the log has only grown since. A log that rewrites or
drops entries can therefore not obtain a cosignature, and a log that shows
different contents to different people cannot get the same witness to cosign
both.

``Witness.add_checkpoint`` implements the checks of the ``add-checkpoint`` call
of c2sp.org/tlog-witness and returns the HTTP status code and body that call
would produce. The HTTP transport itself is not implemented: requests and
responses travel as files.
"""

from __future__ import annotations

import json
import os
import time
from typing import Callable

from . import merkle
from .log import Checkpoint
from .note import (
    COSIGNATURE,
    LOG_SIGNATURE,
    Signer,
    SignatureError,
    Verifier,
    b64,
    parse_note,
    unb64,
    verify_signatures,
)
from .statement import FormatError

KEY_FILE = "key"
STATE_FILE = "state.json"
LOCK_FILE = "lock"
MAX_PROOF_LINES = 63


class Witness:
    def __init__(self, path: str):
        self.path = path
        try:
            with open(os.path.join(path, KEY_FILE), encoding="utf-8") as handle:
                self.signer = Signer.parse(handle.read())
        except FileNotFoundError as exc:
            raise FormatError(f"{path}: not a witness directory") from exc
        if self.signer.kind != COSIGNATURE:
            raise FormatError("the witness key is not a cosignature key")

    # -- setup -----------------------------------------------------------

    @classmethod
    def create(cls, path: str, name: str) -> "Witness":
        os.makedirs(path, exist_ok=True)
        key_path = os.path.join(path, KEY_FILE)
        if os.path.exists(key_path):
            raise FormatError(f"{path}: a witness already exists here")
        signer = Signer.generate(name, COSIGNATURE)
        descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(signer.encode() + "\n")
        witness = cls(path)
        witness._save({"logs": {}})
        return witness

    def trust(self, log_key: Verifier) -> None:
        """Start following the log whose origin is the key's name."""
        if log_key.kind != LOG_SIGNATURE:
            raise FormatError("a log is trusted through its log-signature key")
        with self._locked():
            state = self._load()
            entry = state["logs"].setdefault(
                log_key.name, {"keys": [], "size": 0, "root": None}
            )
            if log_key.vkey() not in entry["keys"]:
                entry["keys"].append(log_key.vkey())
            self._save(state)

    def status(self) -> dict:
        return self._load()

    # -- state -----------------------------------------------------------

    def _load(self) -> dict:
        with open(os.path.join(self.path, STATE_FILE), encoding="utf-8") as handle:
            return json.load(handle)

    def _save(self, state: dict) -> None:
        temporary = os.path.join(self.path, STATE_FILE + ".tmp")
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, os.path.join(self.path, STATE_FILE))

    def _locked(self):
        return _Lock(os.path.join(self.path, LOCK_FILE))

    # -- the protocol ----------------------------------------------------

    def add_checkpoint(
        self, request: str, now: Callable[[], float] = time.time
    ) -> tuple[int, str]:
        """Handle an add-checkpoint request body. Returns (status, body)."""
        # Checking the old size and storing the new checkpoint must be one
        # atomic step, or two concurrent requests could roll the witness back.
        with self._locked():
            return self._add_checkpoint(request, now)

    def _add_checkpoint(self, request: str, now: Callable[[], float]) -> tuple[int, str]:
        head, separator, signed = request.partition("\n\n")
        if not separator:
            return 400, "the request needs an empty line before the checkpoint\n"
        lines = head.split("\n")
        first = lines[0].split(" ")
        if len(first) != 2 or first[0] != "old" or not _is_decimal(first[1]):
            return 400, "the first line must be 'old <size>'\n"
        old_size = int(first[1])
        if len(lines) - 1 > MAX_PROOF_LINES:
            return 400, "too many consistency proof lines\n"
        try:
            proof = [unb64(line, "proof line") for line in lines[1:]]
            if any(len(item) != 32 for item in proof):
                raise FormatError("a proof line is not a 32-byte hash")
            note = parse_note(signed)
            checkpoint = Checkpoint.parse(note.text)
        except FormatError as exc:
            return 400, f"{exc}\n"

        state = self._load()
        entry = state["logs"].get(checkpoint.origin)
        if entry is None:
            return 404, "unknown log origin\n"
        try:
            verified = verify_signatures(
                note.text, note.signatures, [Verifier.parse(k) for k in entry["keys"]]
            )
        except SignatureError as exc:
            return 403, f"{exc}\n"
        if not verified:
            return 403, "no signature from a trusted key for this log\n"

        if old_size > checkpoint.size:
            return 400, "the old size is larger than the checkpoint size\n"
        if old_size != entry["size"]:
            return 409, f"{entry['size']}\n"
        if checkpoint.size == 0 and checkpoint.root != merkle.EMPTY_ROOT:
            return 422, "a checkpoint of size zero must have the empty root\n"
        if old_size == 0:
            if proof:
                return 422, "the proof must be empty when the old size is zero\n"
        elif old_size == checkpoint.size:
            if proof or unb64(entry["root"], "stored root") != checkpoint.root:
                return 422, "same size as the last cosigned checkpoint, different root\n"
        else:
            old_root = unb64(entry["root"], "stored root")
            if not merkle.verify_consistency(
                old_size, checkpoint.size, old_root, checkpoint.root, proof
            ):
                return 422, "the consistency proof does not verify\n"

        entry["size"] = checkpoint.size
        entry["root"] = b64(checkpoint.root)
        entry["checkpoint"] = note.text
        self._save(state)  # persist before answering
        return 200, self.signer.sign(note.text, timestamp=int(now()))


def _is_decimal(text: str) -> bool:
    return text.isascii() and text.isdigit() and (text == "0" or text[0] != "0")


class _Lock:
    """A lock file: creating it fails if another process holds it."""

    def __init__(self, path: str):
        self.path = path

    def __enter__(self):
        deadline = time.monotonic() + 10
        while True:
            try:
                os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                if time.monotonic() > deadline:
                    raise FormatError(
                        f"{self.path}: the witness is busy, or a previous run left "
                        "this lock file behind"
                    )
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        return False
