"""Event schemas (placeholders)."""
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Participant:
    user_id: str
    share: float


@dataclass
class Event:
    id: str
    name: str
    participants: List[Participant]
    rules: Dict
