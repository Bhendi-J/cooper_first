import requests
from flask import current_app

class FinternetService:
    def __init__(self):
        self.api_key = current_app.config['FINTERNET_API_KEY']
        self.base_url = current_app.config['FINTERNET_BASE_URL']
        self.headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def create_payment_intent(self, amount, currency='USD', description='', 
                            payment_type='CONDITIONAL', settlement_method='OFF_RAMP_MOCK', 
                            settlement_destination='test_account'):
        """Create a payment intent for collecting funds from users"""
        url = f"{self.base_url}/payment-intents"
        payload = {
            "amount": str(amount),
            "currency": currency,
            "type": payment_type,
            "description": description,
            "settlementMethod": settlement_method,
            "settlementDestination": settlement_destination
        }
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()
    
    def get_payment_intent(self, intent_id):
        """Get payment intent status"""
        url = f"{self.base_url}/payment-intents/{intent_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def confirm_payment_intent(self, intent_id, signature, payer_address, submitted_by="cooper_app"):
        """Confirm a payment intent after user signs"""
        url = f"{self.base_url}/payment-intents/{intent_id}/confirm"
        payload = {
            "signature": signature,
            "payerAddress": payer_address,
            "submittedBy": submitted_by
        }
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()
    
    def get_merchant_balance(self):
        """Get merchant account balance"""
        url = f"{self.base_url}/payment-intents/account/balance"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_ledger_entries(self, limit=20, offset=0):
        """Get account ledger entries"""
        url = f"{self.base_url}/payment-intents/account/ledger-entries"
        params = {"limit": limit, "offset": offset}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()