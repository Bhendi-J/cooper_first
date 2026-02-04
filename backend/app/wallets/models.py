"""Wallet models."""
from dataclasses import dataclass


@dataclass
class PersonalWallet:
    user_id: str
    balance: float = 0.0


@dataclass
class SharedWallet:
    event_id: str
    balance: float = 0.0
