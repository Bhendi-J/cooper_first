"""Finternet Payment Gateway Integration."""
import os
import requests
from typing import Optional, Dict, Any


class FinternetService:
    """Service for interacting with Finternet Payment Gateway API."""
    
    BASE_URL = "https://api.fmm.finternetlab.io/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FINTERNET_API_KEY")
        if not self.api_key:
            raise ValueError("Finternet API key is required")
    
    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def create_payment_intent(
        self,
        amount: str,
        currency: str = "USDC",
        payment_type: str = "CONDITIONAL",
        settlement_method: str = "OFF_RAMP_MOCK",
        settlement_destination: str = "bank_account_default",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new payment intent.
        
        Args:
            amount: Payment amount as string (e.g., "100.00")
            currency: Currency code (USDC, USDT, DAI)
            payment_type: Type of payment (CONDITIONAL, DELIVERY_VS_PAYMENT, etc.)
            settlement_method: Settlement method (OFF_RAMP_MOCK for testing)
            settlement_destination: Destination account for settlement
            description: Optional payment description
            
        Returns:
            Payment intent object with paymentUrl for user redirect
        """
        payload = {
            "amount": amount,
            "currency": currency,
            "type": payment_type,
            "settlementMethod": settlement_method,
            "settlementDestination": settlement_destination
        }
        
        if description:
            payload["description"] = description
        
        response = requests.post(
            f"{self.BASE_URL}/payment-intents",
            headers=self._headers(),
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def get_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """
        Retrieve a payment intent by ID.
        
        Args:
            intent_id: The payment intent ID
            
        Returns:
            Payment intent object with current status
        """
        response = requests.get(
            f"{self.BASE_URL}/payment-intents/{intent_id}",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def confirm_payment(
        self,
        intent_id: str,
        signature: str,
        payer_address: str
    ) -> Dict[str, Any]:
        """
        Confirm a payment intent after user signs the transaction.
        
        Args:
            intent_id: The payment intent ID
            signature: EIP-712 signature from user's wallet
            payer_address: User's wallet address
            
        Returns:
            Updated payment intent object
        """
        payload = {
            "signature": signature,
            "payerAddress": payer_address
        }
        
        response = requests.post(
            f"{self.BASE_URL}/payment-intents/{intent_id}/confirm",
            headers=self._headers(),
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def cancel_payment(self, intent_id: str) -> Dict[str, Any]:
        """
        Cancel a payment intent.
        
        Args:
            intent_id: The payment intent ID
            
        Returns:
            Cancelled payment intent object
        """
        response = requests.post(
            f"{self.BASE_URL}/payment-intents/{intent_id}/cancel",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()


# Backwards compatibility functions
def create_payment_intent(amount, currency="USDC"):
    """Legacy function for backwards compatibility."""
    service = FinternetService()
    return service.create_payment_intent(str(amount), currency)


def fetch_intent(intent_id):
    """Legacy function for backwards compatibility."""
    service = FinternetService()
    return service.get_payment_intent(intent_id)
