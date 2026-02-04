import hashlib
import json
from typing import List, Dict, Any

class MerkleTree:
    """Merkle Tree for tamper-proof expense tracking"""
    
    def __init__(self, leaves: List[str] = None):
        self.leaves = leaves or []
        self.tree = []
        self.root = None
        if self.leaves:
            self.build_tree()
    
    @staticmethod
    def hash_data(data: str) -> str:
        """Create SHA-256 hash of data"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def hash_expense(expense: Dict[str, Any]) -> str:
        """Create hash from expense data"""
        expense_str = json.dumps(expense, sort_keys=True, default=str)
        return MerkleTree.hash_data(expense_str)
    
    def build_tree(self):
        """Build the Merkle tree from leaves"""
        if not self.leaves:
            self.root = None
            return
        
        current_level = [self.hash_data(leaf) for leaf in self.leaves]
        self.tree = [current_level.copy()]
        
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                next_level.append(self.hash_data(combined))
            current_level = next_level
            self.tree.append(current_level.copy())
        
        self.root = current_level[0] if current_level else None
    
    def add_leaf(self, leaf: str):
        """Add a new leaf and rebuild tree"""
        self.leaves.append(leaf)
        self.build_tree()
    
    def get_proof(self, index: int) -> List[Dict[str, str]]:
        """Get Merkle proof for a leaf at given index"""
        if index < 0 or index >= len(self.leaves):
            return []
        
        proof = []
        current_index = index
        
        for level in self.tree[:-1]:
            sibling_index = current_index + 1 if current_index % 2 == 0 else current_index - 1
            if sibling_index < len(level):
                direction = 'right' if current_index % 2 == 0 else 'left'
                proof.append({
                    'hash': level[sibling_index],
                    'direction': direction
                })
            current_index //= 2
        
        return proof
    
    def verify_proof(self, leaf: str, proof: List[Dict[str, str]], root: str) -> bool:
        """Verify a Merkle proof"""
        current_hash = self.hash_data(leaf)
        
        for step in proof:
            if step['direction'] == 'left':
                current_hash = self.hash_data(step['hash'] + current_hash)
            else:
                current_hash = self.hash_data(current_hash + step['hash'])
        
        return current_hash == root
    
    def get_root(self) -> str:
        return self.root

class EventMerkleTree:
    """Helper class for event-specific Merkle tree operations"""
    
    @staticmethod
    def expense_to_leaf(expense: Dict[str, Any]) -> str:
        """Convert expense to leaf string"""
        leaf_data = {
            'id': str(expense.get('_id', '')),
            'event_id': str(expense.get('event_id', '')),
            'payer_id': str(expense.get('payer_id', '')),
            'amount': expense.get('amount', 0),
            'description': expense.get('description', ''),
            'created_at': str(expense.get('created_at', ''))
        }
        return json.dumps(leaf_data, sort_keys=True)
    
    @staticmethod
    def build_event_tree(event_id: str, expenses: List[Dict]) -> MerkleTree:
        """Build Merkle tree from event expenses"""
        leaves = [EventMerkleTree.expense_to_leaf(e) for e in expenses]
        return MerkleTree(leaves)