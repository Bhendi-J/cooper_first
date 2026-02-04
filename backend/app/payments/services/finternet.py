"""Finternet Payment Gateway Integration with Mock Mode for Demo."""
import os
import uuid
import time
import random
from typing import Optional, Dict, Any

# Set to False to use real Finternet API
MOCK_MODE = False


class FinternetService:
    """Service for interacting with Finternet Payment Gateway API."""
    
    BASE_URL = "https://api.fmm.finternetlab.io/api/v1"
    MOCK_PAYMENT_URL = "http://localhost:5173/payment/processing"
    
    # In-memory store for mock intents
    _mock_intents: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self, api_key: Optional[str] = None):
        if MOCK_MODE:
            self.api_key = "mock_api_key"
        else:
            self.api_key = api_key or os.environ.get("FINTERNET_API_KEY")
            if not self.api_key:
                raise ValueError("Finternet API key is required")
    
    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _generate_tx_hash(self) -> str:
        """Generate a realistic-looking Ethereum transaction hash."""
        return "0x" + uuid.uuid4().hex + uuid.uuid4().hex[:24]
    
    def _generate_contract_address(self) -> str:
        """Generate a realistic-looking smart contract address."""
        return "0x" + uuid.uuid4().hex[:40]
    
    def create_payment_intent(
        self,
        amount: str,
        currency: str = "USD",
        payment_type: str = "DELIVERY_VS_PAYMENT",
        settlement_method: str = "OFF_RAMP_MOCK",
        settlement_destination: str = "bank_account_123",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new payment intent (mocked for demo)."""
        
        if MOCK_MODE:
            intent_id = f"intent_{uuid.uuid4().hex[:12]}"
            formatted_amount = "{:.2f}".format(float(amount))
            
            mock_response = {
                "id": intent_id,
                "object": "payment_intent",
                "status": "INITIATED",
                "data": {
                    "id": intent_id,
                    "object": "payment_intent",
                    "status": "INITIATED",
                    "amount": formatted_amount,
                    "currency": currency,
                    "type": payment_type,
                    "description": description or "Cooper Payment",
                    "settlementMethod": settlement_method,
                    "settlementDestination": settlement_destination,
                    "contractAddress": self._generate_contract_address(),
                    "chainId": 11155111,  # Sepolia testnet
                    "transactionHash": None,
                    "paymentUrl": f"{self.MOCK_PAYMENT_URL}?intent={intent_id}",
                    "created": int(time.time()),
                    "updated": int(time.time())
                },
                "created": int(time.time()),
                "updated": int(time.time())
            }
            
            # Store for later retrieval
            self._mock_intents[intent_id] = mock_response
            return mock_response
        
        # Real API call - based on official Finternet docs
        import requests
        payload = {
            "amount": "{:.2f}".format(float(amount)),
            "currency": currency,
            "type": payment_type,
            "settlementMethod": settlement_method,
            "settlementDestination": settlement_destination,
            "description": description or "Cooper Payment",
            "metadata": {
                "source": "cooper_app",
                "timestamp": str(int(time.time()))
            }
        }
        
        response = requests.post(
            f"{self.BASE_URL}/payment-intents",
            headers=self._headers(),
            json=payload
        )
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            error_msg = response.text if response.content else str(e)
            raise ValueError(f"Finternet API Error: {error_msg}") from e
        return response.json()
    
    def get_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """Retrieve a payment intent by ID (mocked for demo)."""
        
        if MOCK_MODE:
            if intent_id in self._mock_intents:
                intent = self._mock_intents[intent_id]
                # Simulate progression: INITIATED -> PROCESSING -> SUCCEEDED
                current_status = intent["data"]["status"]
                
                if current_status == "INITIATED":
                    intent["data"]["status"] = "PROCESSING"
                elif current_status == "PROCESSING":
                    intent["data"]["status"] = "SUCCEEDED"
                    intent["data"]["transactionHash"] = self._generate_tx_hash()
                
                intent["status"] = intent["data"]["status"]
                intent["data"]["updated"] = int(time.time())
                return intent
            
            # Return a default succeeded intent for unknown IDs
            return {
                "id": intent_id,
                "status": "SUCCEEDED",
                "data": {
                    "id": intent_id,
                    "status": "SUCCEEDED",
                    "amount": "100.00",
                    "currency": "USDC",
                    "transactionHash": self._generate_tx_hash(),
                    "contractAddress": self._generate_contract_address()
                }
            }
        
        import requests
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
        """Confirm a payment intent (mocked for demo)."""
        
        if MOCK_MODE:
            if intent_id in self._mock_intents:
                intent = self._mock_intents[intent_id]
                intent["data"]["status"] = "SUCCEEDED"
                intent["data"]["transactionHash"] = self._generate_tx_hash()
                intent["data"]["signerAddress"] = payer_address
                intent["status"] = "SUCCEEDED"
                return intent
            
            return {
                "id": intent_id,
                "status": "SUCCEEDED",
                "data": {
                    "status": "SUCCEEDED",
                    "transactionHash": self._generate_tx_hash()
                }
            }
        
        import requests
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
        """Cancel a payment intent (mocked for demo)."""
        
        if MOCK_MODE:
            if intent_id in self._mock_intents:
                intent = self._mock_intents[intent_id]
                intent["data"]["status"] = "CANCELLED"
                intent["status"] = "CANCELLED"
                return intent
            return {"id": intent_id, "status": "CANCELLED"}
        
        import requests
        response = requests.post(
            f"{self.BASE_URL}/payment-intents/{intent_id}/cancel",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()


# Split payment calculation utility
def calculate_split(total_amount: float, num_participants: int, weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    Calculate split amounts for participants.
    
    Args:
        total_amount: Total amount to split
        num_participants: Number of people to split among
        weights: Optional dict of participant_id -> weight (for unequal splits)
    
    Returns:
        Split breakdown with per-person amounts
    """
    if weights:
        total_weight = sum(weights.values())
        splits = {
            pid: round((w / total_weight) * total_amount, 2)
            for pid, w in weights.items()
        }
    else:
        per_person = round(total_amount / num_participants, 2)
        splits = {f"participant_{i+1}": per_person for i in range(num_participants)}
    
    return {
        "total": total_amount,
        "num_participants": num_participants,
        "per_person": round(total_amount / num_participants, 2),
        "splits": splits,
        "currency": "USDC"
    }


# Backwards compatibility functions
def create_payment_intent(amount, currency="USDC"):
    """Legacy function for backwards compatibility."""
    service = FinternetService()
    return service.create_payment_intent(str(amount), currency)


def fetch_intent(intent_id):
    """Legacy function for backwards compatibility."""
    service = FinternetService()
    return service.get_payment_intent(intent_id)
