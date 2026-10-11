"""Merkle tree hashing and proofs as defined in RFC 6962, section 2.1.

A leaf is hashed as SHA-256(0x00 || leaf) and an inner node as
SHA-256(0x01 || left || right). The different prefixes stop a leaf from being
passed off as an inner node. Verification follows RFC 9162, section 2.1.
"""

from __future__ import annotations

import hashlib
from typing import Sequence


def leaf_hash(leaf: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + leaf).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


EMPTY_ROOT = hashlib.sha256(b"").digest()


def _split(n: int) -> int:
    """Largest power of two strictly smaller than n (n > 1)."""
    return 1 << ((n - 1).bit_length() - 1)


def _subtree(hashes: Sequence[bytes], start: int, end: int) -> bytes:
    n = end - start
    if n == 1:
        return hashes[start]
    k = _split(n)
    return node_hash(_subtree(hashes, start, start + k), _subtree(hashes, start + k, end))


def root(hashes: Sequence[bytes]) -> bytes:
    """Root of the tree over ``hashes``, which are leaf hashes in log order."""
    if not hashes:
        return EMPTY_ROOT
    # Iterative form of the recursive definition: fold complete subtrees.
    stack: list[tuple[int, bytes]] = []  # (height, hash)
    for value in hashes:
        height = 0
        while stack and stack[-1][0] == height:
            _, left = stack.pop()
            value = node_hash(left, value)
            height += 1
        stack.append((height, value))
    value = stack.pop()[1]
    while stack:
        value = node_hash(stack.pop()[1], value)
    return value


def inclusion_proof(hashes: Sequence[bytes], index: int) -> list[bytes]:
    """Audit path for leaf ``index`` in the tree over ``hashes``."""
    if not 0 <= index < len(hashes):
        raise IndexError("leaf index out of range")
    path: list[bytes] = []
    start, end = 0, len(hashes)
    pending: list[bytes] = []
    while end - start > 1:
        k = _split(end - start)
        if index - start < k:
            pending.append(_subtree(hashes, start + k, end))
            end = start + k
        else:
            pending.append(_subtree(hashes, start, start + k))
            start = start + k
    path.extend(reversed(pending))
    return path


def verify_inclusion(
    leaf: bytes, index: int, size: int, path: Sequence[bytes], expected_root: bytes
) -> bool:
    """Check that ``leaf`` (a leaf hash) is entry ``index`` of a tree of ``size``."""
    if not 0 <= index < size:
        return False
    fn, sn, r = index, size - 1, leaf
    for p in path:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            r = node_hash(p, r)
            if not fn & 1:
                while fn and not fn & 1:
                    fn >>= 1
                    sn >>= 1
        else:
            r = node_hash(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and r == expected_root


def consistency_proof(hashes: Sequence[bytes], old_size: int) -> list[bytes]:
    """Proof that the first ``old_size`` leaves are a prefix of ``hashes``."""
    size = len(hashes)
    if not 0 < old_size <= size:
        raise ValueError("old size must be between 1 and the current size")

    def sub(m: int, start: int, end: int, complete: bool) -> list[bytes]:
        n = end - start
        if m == n:
            return [] if complete else [_subtree(hashes, start, end)]
        k = _split(n)
        if m <= k:
            return sub(m, start, start + k, complete) + [_subtree(hashes, start + k, end)]
        return sub(m - k, start + k, end, False) + [_subtree(hashes, start, start + k)]

    return sub(old_size, 0, size, True)


def verify_consistency(
    old_size: int, new_size: int, old_root: bytes, new_root: bytes, proof: Sequence[bytes]
) -> bool:
    """Check that a tree of ``new_size`` extends a tree of ``old_size``."""
    if old_size < 1 or old_size > new_size:
        return False
    if old_size == new_size:
        return not proof and old_root == new_root
    path = list(proof)
    if old_size & (old_size - 1) == 0:
        path.insert(0, old_root)
    if not path:
        return False
    fn, sn = old_size - 1, new_size - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    fr = sr = path[0]
    for c in path[1:]:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            fr = node_hash(c, fr)
            sr = node_hash(c, sr)
            if not fn & 1:
                while fn and not fn & 1:
                    fn >>= 1
                    sn >>= 1
        else:
            sr = node_hash(sr, c)
        fn >>= 1
        sn >>= 1
    return sn == 0 and fr == old_root and sr == new_root
