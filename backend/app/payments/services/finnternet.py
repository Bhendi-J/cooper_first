"""Finternet integration placeholder."""
def create_payment_intent(amount, currency="USD"):
    return {"id": "pi_mock", "amount": amount, "currency": currency, "status": "requires_confirmation"}


def fetch_intent(intent_id):
    return {"id": intent_id, "status": "succeeded"}
