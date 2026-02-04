"""Simple Merkle tree placeholder implementation."""
import hashlib
from typing import List, Any, Optional


class MerkleTree:
    def __init__(self, leaves=None):
        self.leaves = leaves or []
        self._hashed_leaves = []
        self._tree = []
        if self.leaves:
            self._build_tree()

    def _hash(self, data: bytes) -> bytes:
        return hashlib.sha256(data).digest()
    
    def hash_data(self, data: str) -> str:
        """Hash a string and return hex representation."""
        return self._hash(data.encode()).hex()

    def _build_tree(self):
        """Build the Merkle tree from leaves."""
        self._hashed_leaves = [self._hash(str(leaf).encode()) for leaf in self.leaves]
        self._tree = [self._hashed_leaves[:]]
        
        current_level = self._hashed_leaves[:]
        while len(current_level) > 1:
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])
            next_level = []
            for i in range(0, len(current_level), 2):
                combined = current_level[i] + current_level[i + 1]
                next_level.append(self._hash(combined))
            self._tree.append(next_level)
            current_level = next_level

    def root(self) -> bytes:
        """Get the Merkle root as bytes."""
        if not self._tree:
            return b""
        return self._tree[-1][0] if self._tree[-1] else b""
    
    def get_root(self) -> str:
        """Get the Merkle root as hex string."""
        root = self.root()
        return root.hex() if root else ""

    def get_proof(self, index: int) -> List[str]:
        """Get the Merkle proof for a leaf at the given index."""
        if index < 0 or index >= len(self.leaves):
            return []
        
        proof = []
        current_index = index
        
        for level in self._tree[:-1]:
            if len(level) == 1:
                break
                
            # Determine sibling index
            if current_index % 2 == 0:
                sibling_index = current_index + 1
                direction = "right"
            else:
                sibling_index = current_index - 1
                direction = "left"
            
            if sibling_index < len(level):
                proof.append({
                    "hash": level[sibling_index].hex(),
                    "direction": direction
                })
            
            current_index = current_index // 2
        
        return proof

    def verify_proof(self, leaf: str, proof: List[dict], root: str) -> bool:
        """Verify a Merkle proof."""
        if not root:
            return False
        
        current_hash = self._hash(leaf.encode())

        # If no proof provided, just check if leaf hash matches root (single leaf tree)
        if not proof:
            return current_hash.hex() == root

        for step in proof:
            if not isinstance(step, dict) or "hash" not in step or "direction" not in step:
                return False
            
            hash_value = step["hash"]
            # Validate hex string
            if not isinstance(hash_value, str) or not all(c in '0123456789abcdefABCDEF' for c in hash_value):
                return False
            
            try:
                sibling_hash = bytes.fromhex(hash_value)
            except ValueError:
                return False
                
            else:
                current_hash = self._hash(sibling_hash + current_hash)
        
        return current_hash.hex() == root


class EventMerkleTree(MerkleTree):
    """Merkle tree for event expense verification."""
    
    def __init__(self, leaves=None):
        super().__init__(leaves)
    
    @staticmethod
    def expense_to_leaf(expense: dict) -> str:
        """Convert an expense document to a leaf string."""
        expense_id = str(expense.get('_id', ''))
        amount = str(expense.get('amount', ''))
        payer_id = str(expense.get('payer_id', ''))
        description = expense.get('description', '')
        created_at = str(expense.get('created_at', ''))
        return f"{expense_id}|{amount}|{payer_id}|{description}|{created_at}"
    
    @classmethod
    def build_event_tree(cls, event_id: str, expenses: List[dict]) -> 'EventMerkleTree':
        """Build a Merkle tree from a list of expenses."""
        leaves = [cls.expense_to_leaf(exp) for exp in expenses]
        return cls(leaves)
    
    def get_root_hex(self) -> Optional[str]:
        """Return the Merkle root as a hex string."""
        return self.get_root() or None
