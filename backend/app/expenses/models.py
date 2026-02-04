"""Expense models."""
from dataclasses import dataclass
from typing import List


@dataclass
class Expense:
    id: str
    payer_id: str
    amount: float
    participants: List[str]
    category: str = "general"
