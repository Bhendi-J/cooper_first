"""Simple Merkle tree placeholder implementation."""
import hashlib


class MerkleTree:
    def __init__(self, leaves=None):
        self.leaves = leaves or []

    def _hash(self, data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

    def root(self):
        nodes = [self._hash(str(leaf).encode()) for leaf in self.leaves]
        while len(nodes) > 1:
            if len(nodes) % 2 == 1:
                nodes.append(nodes[-1])
            nodes = [self._hash(nodes[i] + nodes[i + 1]) for i in range(0, len(nodes), 2)]
        return nodes[0] if nodes else b""
