import hashlib

import pytest

from actasum import merkle


def naive_root(leaves):
    """RFC 6962 section 2.1, written as literally as possible."""
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return hashlib.sha256(b"\x00" + leaves[0]).digest()
    k = 1
    while k * 2 < n:
        k *= 2
    return hashlib.sha256(b"\x01" + naive_root(leaves[:k]) + naive_root(leaves[k:])).digest()


LEAVES = [f"leaf-{i}".encode() for i in range(70)]
HASHES = [merkle.leaf_hash(leaf) for leaf in LEAVES]


def test_known_values():
    assert merkle.root([]).hex() == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    # SHA-256 of the single byte 0x00: the tree holding one empty leaf.
    assert merkle.root([merkle.leaf_hash(b"")]).hex() == (
        "6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d"
    )


@pytest.mark.parametrize("size", range(0, 70))
def test_root_matches_the_recursive_definition(size):
    assert merkle.root(HASHES[:size]) == naive_root(LEAVES[:size])


@pytest.mark.parametrize("size", [1, 2, 3, 4, 5, 7, 8, 9, 16, 17, 31, 33, 64, 70])
def test_inclusion_proofs_verify_and_bind_position(size):
    hashes = HASHES[:size]
    tree_root = merkle.root(hashes)
    for index in range(size):
        path = merkle.inclusion_proof(hashes, index)
        assert merkle.verify_inclusion(hashes[index], index, size, path, tree_root)
        # A wrong leaf, a wrong position and a damaged path all fail. (A wrong
        # size is not always caught by the path alone: trees of 3 and 4 leaves
        # have the same shape around leaf 0. The size is bound by the
        # checkpoint, not by the proof.)
        assert not merkle.verify_inclusion(merkle.leaf_hash(b"x"), index, size, path, tree_root)
        if size > 1:
            other = (index + 1) % size
            assert not merkle.verify_inclusion(hashes[index], other, size, path, tree_root)
            damaged = [bytes(32)] + path[1:]
            assert not merkle.verify_inclusion(hashes[index], index, size, damaged, tree_root)


def test_consistency_proofs_for_every_pair_of_sizes():
    for new in range(1, 40):
        new_root = merkle.root(HASHES[:new])
        for old in range(1, new + 1):
            old_root = merkle.root(HASHES[:old])
            proof = merkle.consistency_proof(HASHES[:new], old)
            assert merkle.verify_consistency(old, new, old_root, new_root, proof), (old, new)


def test_consistency_fails_when_history_was_rewritten():
    old, new = 13, 29
    old_root = merkle.root(HASHES[:old])
    rewritten = list(HASHES[:new])
    rewritten[5] = merkle.leaf_hash(b"altered after the fact")
    proof = merkle.consistency_proof(rewritten, old)
    assert not merkle.verify_consistency(old, new, old_root, merkle.root(rewritten), proof)
    # A log that drops an entry cannot prove consistency either.
    shorter = HASHES[:5] + HASHES[6:new]
    proof = merkle.consistency_proof(shorter, old)
    assert not merkle.verify_consistency(old, len(shorter), old_root, merkle.root(shorter), proof)


def test_bad_arguments():
    with pytest.raises(IndexError):
        merkle.inclusion_proof(HASHES[:4], 4)
    with pytest.raises(ValueError):
        merkle.consistency_proof(HASHES[:4], 5)
    assert not merkle.verify_consistency(0, 4, merkle.EMPTY_ROOT, merkle.root(HASHES[:4]), [])
