"""Payments models."""
from dataclasses import dataclass


@dataclass
class PaymentIntent:
    id: str
    amount: float
    status: str
