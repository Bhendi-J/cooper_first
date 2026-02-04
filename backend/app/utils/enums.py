"""Common enums and constants."""
from enum import Enum


class ExpenseStatus(Enum):
    PENDING = "pending"
    SETTLED = "settled"
