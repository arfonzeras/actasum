"""Signed notes and checkpoint signatures, following the C2SP specifications.

* c2sp.org/signed-note: the text format, key IDs and verifier keys.
* c2sp.org/tlog-checkpoint: which signatures a checkpoint may carry.
* c2sp.org/tlog-cosignature: what a witness signs.

Two signature types are implemented, both Ed25519:

* ``0x01``, a log signing its own checkpoint, over the note text;
* ``0x04``, a timestamped checkpoint cosignature, over
  ``cosignature/v1\\ntime <timestamp>\\n`` followed by the note text.

The specifications recommend ML-DSA-44 (type ``0x06``) for new deployments.
It is not implemented here yet.

Ed25519 comes from the ``cryptography`` package, which is an optional
dependency: nothing else in actasum needs it.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import struct
from dataclasses import dataclass
from typing import Iterable, Sequence

from .statement import FormatError

LOG_SIGNATURE = 0x01  # Ed25519 over the note text
COSIGNATURE = 0x04  # timestamped Ed25519 checkpoint cosignature
_TYPE_NAMES = {LOG_SIGNATURE: "log", COSIGNATURE: "witness"}

EM_DASH = "—"
MAX_SIGNATURES = 64
_PRIVATE_PREFIX = "PRIVATE+KEY+"


class SignatureError(FormatError):
    """A note is malformed or is not validly signed by a trusted key."""


def _ed25519():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise FormatError(
            "signatures need the 'cryptography' package: pip install 'actasum[sign]'"
        ) from exc
    return ed25519, serialization, InvalidSignature


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def unb64(text: str, what: str) -> bytes:
    """Decode canonical base64 with padding; reject anything else."""
    try:
        data = base64.b64decode(text.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError, ValueError) as exc:
        raise FormatError(f"{what} is not valid base64") from exc
    if b64(data) != text:
        raise FormatError(f"{what} is not canonical base64")
    return data


def check_name(name: str) -> str:
    """Key names, cosigner names and log origins share these rules."""
    if (
        not name
        or len(name.encode("utf-8")) > 255
        or "+" in name
        or any(ch.isspace() or ord(ch) < 0x20 for ch in name)
    ):
        raise FormatError(f"invalid key name or origin: {name!r}")
    return name


def key_id(name: str, kind: int, public: bytes) -> bytes:
    return hashlib.sha256(name.encode("utf-8") + b"\n" + bytes([kind]) + public).digest()[:4]


@dataclass(frozen=True)
class Verifier:
    """A public key trusted for one name and one signature type."""

    name: str
    kind: int
    public: bytes

    def __post_init__(self) -> None:
        check_name(self.name)
        if self.kind not in _TYPE_NAMES:
            raise FormatError(f"unsupported signature type 0x{self.kind:02x}")
        if len(self.public) != 32:
            raise FormatError("an Ed25519 public key is 32 bytes")

    @property
    def id(self) -> bytes:
        return key_id(self.name, self.kind, self.public)

    def vkey(self) -> str:
        return f"{self.name}+{self.id.hex()}+{b64(bytes([self.kind]) + self.public)}"

    @classmethod
    def parse(cls, vkey: str) -> "Verifier":
        # The base64 part may itself contain "+": split on the first two only.
        parts = vkey.strip().split("+", 2)
        if len(parts) != 3:
            raise FormatError("a verifier key is <name>+<hex key id>+<base64 key>")
        name, hex_id, encoded = parts
        material = unb64(encoded, "verifier key")
        if len(material) < 1:
            raise FormatError("verifier key is empty")
        verifier = cls(name, material[0], material[1:])
        if verifier.id.hex() != hex_id:
            raise FormatError("verifier key: the key ID does not match the name and key")
        return verifier

    def verify(self, text: str, signature: bytes) -> tuple[bool, int | None]:
        """Returns (valid, timestamp). The timestamp is set for cosignatures."""
        ed25519, _, InvalidSignature = _ed25519()
        timestamp: int | None = None
        message = text.encode("utf-8")
        if self.kind == COSIGNATURE:
            if len(signature) != 8 + 64:
                return False, None
            (timestamp,) = struct.unpack(">Q", signature[:8])
            message = f"cosignature/v1\ntime {timestamp}\n".encode("ascii") + message
            signature = signature[8:]
        elif len(signature) != 64:
            return False, None
        try:
            ed25519.Ed25519PublicKey.from_public_bytes(self.public).verify(signature, message)
        except InvalidSignature:
            return False, None
        return True, timestamp


@dataclass(frozen=True)
class Signer:
    """A private key. Keep the file that holds it private."""

    name: str
    kind: int
    seed: bytes

    @classmethod
    def generate(cls, name: str, kind: int) -> "Signer":
        import os

        _ed25519()
        return cls(check_name(name), kind, os.urandom(32))

    def _private(self):
        ed25519, _, _ = _ed25519()
        return ed25519.Ed25519PrivateKey.from_private_bytes(self.seed)

    @property
    def verifier(self) -> Verifier:
        _, serialization, _ = _ed25519()
        public = self._private().public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        return Verifier(self.name, self.kind, public)

    def encode(self) -> str:
        verifier = self.verifier
        return (
            f"{_PRIVATE_PREFIX}{self.name}+{verifier.id.hex()}+"
            f"{b64(bytes([self.kind]) + self.seed)}"
        )

    @classmethod
    def parse(cls, text: str) -> "Signer":
        text = text.strip()
        if not text.startswith(_PRIVATE_PREFIX):
            raise FormatError("not a private key file")
        parts = text[len(_PRIVATE_PREFIX) :].split("+", 2)
        if len(parts) != 3:
            raise FormatError("malformed private key")
        name, hex_id, encoded = parts
        material = unb64(encoded, "private key")
        if len(material) != 33:
            raise FormatError("malformed private key")
        signer = cls(check_name(name), material[0], material[1:])
        if signer.verifier.id.hex() != hex_id:
            raise FormatError("private key: the key ID does not match")
        return signer

    def sign(self, text: str, timestamp: int | None = None) -> str:
        """Return one signature line (with its newline) for ``text``."""
        message = text.encode("utf-8")
        prefix = b""
        if self.kind == COSIGNATURE:
            if timestamp is None or timestamp < 0:
                raise FormatError("a cosignature needs a timestamp")
            prefix = struct.pack(">Q", timestamp)
            message = f"cosignature/v1\ntime {timestamp}\n".encode("ascii") + message
        signature = self._private().sign(message)
        return f"{EM_DASH} {self.name} {b64(self.verifier.id + prefix + signature)}\n"


@dataclass(frozen=True)
class SignatureLine:
    name: str
    id: bytes
    signature: bytes
    line: str  # as it appeared, with its newline


@dataclass(frozen=True)
class Note:
    text: str  # ends with a newline
    signatures: tuple[SignatureLine, ...]

    def render(self) -> str:
        return self.text + "\n" + "".join(s.line for s in self.signatures)


def parse_signature_lines(block: str) -> tuple[SignatureLine, ...]:
    if not block.endswith("\n"):
        raise SignatureError("signature lines must end with a newline")
    lines = block[:-1].split("\n")
    if len(lines) > MAX_SIGNATURES:
        raise SignatureError("too many signatures")
    parsed = []
    for line in lines:
        parts = line.split(" ")
        if len(parts) != 3 or parts[0] != EM_DASH:
            raise SignatureError("malformed signature line")
        check_name(parts[1])
        raw = unb64(parts[2], "signature")
        if len(raw) < 5:
            raise SignatureError("signature is too short")
        parsed.append(SignatureLine(parts[1], raw[:4], raw[4:], line + "\n"))
    seen = {(s.name, s.id) for s in parsed}
    if len(seen) != len(parsed):
        raise SignatureError("two signature lines share a key name and key ID")
    return tuple(parsed)


def parse_note(data: str) -> Note:
    """Split a signed note into its text and its signature lines."""
    if any(ord(ch) < 0x20 and ch != "\n" for ch in data):
        raise SignatureError("a note must not contain control characters")
    # The text is separated from the signatures by the last empty line.
    cut = data.rfind("\n\n")
    if cut < 0:
        raise SignatureError("a signed note needs a blank line before its signatures")
    text, block = data[: cut + 1], data[cut + 2 :]
    if not block:
        raise SignatureError("a signed note needs at least one signature")
    return Note(text, parse_signature_lines(block))


@dataclass(frozen=True)
class Verified:
    verifier: Verifier
    timestamp: int | None


def verify_signatures(
    text: str, signatures: Iterable[SignatureLine], trusted: Sequence[Verifier]
) -> list[Verified]:
    """Verify the signatures made by trusted keys.

    Signatures from unknown keys are ignored. A signature whose key name and
    ID match a trusted key but which does not verify makes the whole note
    invalid. Returns the verifications that succeeded, possibly none.
    """
    known = {(v.name, v.id): v for v in trusted}
    verified: list[Verified] = []
    for signature in signatures:
        verifier = known.get((signature.name, signature.id))
        if verifier is None:
            continue
        valid, timestamp = verifier.verify(text, signature.signature)
        if not valid:
            raise SignatureError(f"the signature by {signature.name} does not verify")
        verified.append(Verified(verifier, timestamp))
    return verified


def open_note(data: str, trusted: Sequence[Verifier]) -> tuple[Note, list[Verified]]:
    """Parse a note and require at least one valid signature from a trusted key."""
    note = parse_note(data)
    verified = verify_signatures(note.text, note.signatures, trusted)
    if not verified:
        raise SignatureError("no signature from a trusted key")
    return note, verified
