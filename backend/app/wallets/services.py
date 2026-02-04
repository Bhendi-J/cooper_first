"""Wallet debit/credit operations."""

def credit(wallet, amount):
    wallet.balance += amount
    return wallet


def debit(wallet, amount):
    if wallet.balance < amount:
        raise ValueError("insufficient funds")
    wallet.balance -= amount
    return wallet
