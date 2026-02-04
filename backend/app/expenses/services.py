"""Expense split logic."""

def split_equal(expense):
    participants = expense.participants
    share = expense.amount / max(1, len(participants))
    return {p: share for p in participants}
