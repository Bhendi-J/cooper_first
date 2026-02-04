"""
Finternet Payment Gateway Integration.

Based on official Finternet API documentation.
Default Sandbox: https://api.finternet.in/v1

Supports MOCK_MODE for demos/presentations when API is unavailable.
"""
import os
import uuid
import time
import requests
from typing import Optional, Dict, Any, List

# In-memory storage for mock mode
_mock_intents: Dict[str, Dict[str, Any]] = {}


class FinternetService:
    """
    Service for interacting with Finternet Payment Gateway API.
    
    Supports:
    - Payment Intents (create, retrieve, confirm, cancel)
    - Conditional Payments (escrow, delivery proof, disputes)
    - Mock Mode for demos/presentations
    
    Payment Flow:
    1. Create payment intent -> get paymentUrl
    2. Redirect user to paymentUrl
    3. User signs EIP-712 message with wallet
    4. Confirm payment with signature
    5. Track status: INITIATED -> PROCESSING -> SUCCEEDED -> SETTLED -> FINAL
    """
    
    # Default base URL (can be overridden by FINTERNET_BASE_URL env var)
    DEFAULT_BASE_URL = "https://api.fmm.finternetlab.io/v1"
    
    # Payment statuses
    STATUS_INITIATED = "INITIATED"
    STATUS_REQUIRES_SIGNATURE = "REQUIRES_SIGNATURE"
    STATUS_PROCESSING = "PROCESSING"
    STATUS_SUCCEEDED = "SUCCEEDED"
    STATUS_SETTLED = "SETTLED"
    STATUS_FINAL = "FINAL"
    STATUS_FAILED = "FAILED"
    STATUS_CANCELLED = "CANCELLED"
    
    # Payment types
    TYPE_CONDITIONAL = "CONDITIONAL"
    TYPE_DELIVERY_VS_PAYMENT = "DELIVERY_VS_PAYMENT"
    
    # Settlement methods
    SETTLEMENT_OFF_RAMP_MOCK = "OFF_RAMP_MOCK"  # For testing
    SETTLEMENT_BANK_TRANSFER = "BANK_TRANSFER"
    
    # Currencies
    CURRENCY_USDC = "USDC"
    CURRENCY_USDT = "USDT"
    CURRENCY_DAI = "DAI"
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, mock_mode: Optional[bool] = None):
        """
        Initialize FinternetService.
        
        Args:
            api_key: Finternet API key (sk_test_xxx, sk_hackathon_xxx, or sk_live_xxx).
                    Falls back to FINTERNET_API_KEY env var.
            base_url: API base URL. Falls back to FINTERNET_BASE_URL env var.
            mock_mode: If True, simulate API responses locally (for demos).
                      Falls back to FINTERNET_MOCK_MODE env var.
        """
        self.api_key = api_key or os.environ.get("FINTERNET_API_KEY")
        self.base_url = (
            base_url 
            or os.environ.get("FINTERNET_BASE_URL") 
            or self.DEFAULT_BASE_URL
        ).rstrip("/")  # Remove trailing slash if present
        
        # Check if mock mode is enabled
        if mock_mode is not None:
            self.mock_mode = mock_mode
        else:
            mock_env = os.environ.get("FINTERNET_MOCK_MODE", "false").lower()
            self.mock_mode = mock_env in ("true", "1", "yes")
        
        if not self.api_key and not self.mock_mode:
            raise ValueError("FINTERNET_API_KEY is required. Set it in environment or pass to constructor.")
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers with API key authentication."""
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an authenticated request to the Finternet API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request arguments
            
        Returns:
            Parsed JSON response
        """
        url = f"{self.base_url}{endpoint}"
        kwargs["headers"] = self._headers()
        
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Return error structure for graceful handling
            return {
                "error": {
                    "code": "request_failed",
                    "message": str(e),
                    "type": "api_error"
                }
            }
    
    # ==================== MOCK MODE HELPERS ====================
    
    def _generate_mock_intent_id(self) -> str:
        """Generate a realistic payment intent ID."""
        return f"intent_{uuid.uuid4().hex[:24]}"
    
    def _generate_mock_tx_hash(self) -> str:
        """Generate a realistic transaction hash."""
        return f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}"
    
    def _mock_create_payment_intent(
        self,
        amount: str,
        currency: str,
        payment_type: str,
        settlement_method: str,
        settlement_destination: str,
        description: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a mock payment intent for demo purposes."""
        intent_id = self._generate_mock_intent_id()
        created_at = int(time.time())
        
        # Generate EIP-712 typed data (simplified mock)
        typed_data = {
            "domain": {
                "name": "Finternet Payment",
                "version": "1",
                "chainId": 11155111,  # Sepolia
                "verifyingContract": "0x1234567890123456789012345678901234567890"
            },
            "types": {
                "Payment": [
                    {"name": "amount", "type": "uint256"},
                    {"name": "currency", "type": "string"},
                    {"name": "intentId", "type": "string"}
                ]
            },
            "primaryType": "Payment",
            "message": {
                "amount": amount,
                "currency": currency,
                "intentId": intent_id
            }
        }
        
        intent = {
            "id": intent_id,
            "object": "payment_intent",
            "amount": amount,
            "currency": currency,
            "type": payment_type,
            "status": self.STATUS_INITIATED,
            "settlementMethod": settlement_method,
            "settlementDestination": settlement_destination,
            "description": description,
            "metadata": metadata or {},
            "paymentUrl": f"http://localhost:5173/payment/confirm/{intent_id}",
            "typedData": typed_data,
            "createdAt": created_at,
            "updatedAt": created_at,
            "mock": True
        }
        
        # Store in mock storage
        _mock_intents[intent_id] = intent
        
        return {"data": intent}
    
    def _mock_get_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """Retrieve a mock payment intent."""
        if intent_id in _mock_intents:
            return {"data": _mock_intents[intent_id]}
        return {
            "error": {
                "code": "not_found",
                "message": f"Payment intent {intent_id} not found",
                "type": "invalid_request_error"
            }
        }
    
    def _mock_confirm_payment(
        self,
        intent_id: str,
        signature: str,
        payer_address: str
    ) -> Dict[str, Any]:
        """Confirm a mock payment intent."""
        if intent_id not in _mock_intents:
            return {
                "error": {
                    "code": "not_found",
                    "message": f"Payment intent {intent_id} not found",
                    "type": "invalid_request_error"
                }
            }
        
        intent = _mock_intents[intent_id]
        intent["status"] = self.STATUS_SUCCEEDED
        intent["payerAddress"] = payer_address
        intent["signature"] = signature
        intent["transactionHash"] = self._generate_mock_tx_hash()
        intent["updatedAt"] = int(time.time())
        intent["confirmedAt"] = int(time.time())
        
        return {"data": intent}
    
    def _mock_cancel_payment(self, intent_id: str) -> Dict[str, Any]:
        """Cancel a mock payment intent."""
        if intent_id not in _mock_intents:
            return {
                "error": {
                    "code": "not_found",
                    "message": f"Payment intent {intent_id} not found",
                    "type": "invalid_request_error"
                }
            }
        
        intent = _mock_intents[intent_id]
        if intent["status"] not in [self.STATUS_INITIATED, self.STATUS_REQUIRES_SIGNATURE]:
            return {
                "error": {
                    "code": "invalid_status",
                    "message": f"Cannot cancel payment in {intent['status']} status",
                    "type": "invalid_request_error"
                }
            }
        
        intent["status"] = self.STATUS_CANCELLED
        intent["updatedAt"] = int(time.time())
        intent["cancelledAt"] = int(time.time())
        
        return {"data": intent}
    
    # ==================== PAYMENT INTENTS ====================
    
    def create_payment_intent(
        self,
        amount: str,
        currency: str = "USDC",
        payment_type: str = "CONDITIONAL",
        settlement_method: str = "OFF_RAMP_MOCK",
        settlement_destination: str = "bank_account_default",
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new payment intent.
        
        This is the first step in collecting a payment. After creation,
        redirect the user to the paymentUrl in the response.
        
        Args:
            amount: Payment amount as string (e.g., "100.00")
            currency: Currency code (USDC, USDT, DAI)
            payment_type: Type of payment:
                - CONDITIONAL: Simple conditional payment
                - DELIVERY_VS_PAYMENT: Escrow-based delivery payment
            settlement_method: How to settle the payment:
                - OFF_RAMP_MOCK: For testing
                - BANK_TRANSFER: Real bank transfer
            settlement_destination: Destination account for settlement
            description: Optional payment description
            metadata: Optional metadata dict
            
        Returns:
            Payment intent object with:
            - id: Payment intent ID (intent_xxx)
            - status: Current status (INITIATED)
            - paymentUrl: URL to redirect user for payment
            - typedData: EIP-712 data for wallet signing
        """
        # Use mock mode if enabled
        if self.mock_mode:
            return self._mock_create_payment_intent(
                amount, currency, payment_type, settlement_method,
                settlement_destination, description, metadata
            )
        
        payload = {
            "amount": str(amount),
            "currency": currency,
            "type": payment_type,
            "settlementMethod": settlement_method,
            "settlementDestination": settlement_destination
        }
        
        if description:
            payload["description"] = description
        if metadata:
            payload["metadata"] = metadata
        
        return self._request("POST", "/payment-intents", json=payload)
    
    def get_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """
        Retrieve a payment intent by ID.
        
        Use this to check the current status of a payment.
        
        Args:
            intent_id: The payment intent ID (intent_xxx)
            
        Returns:
            Payment intent object with current status and details
        """
        if self.mock_mode:
            return self._mock_get_payment_intent(intent_id)
        
        return self._request("GET", f"/payment-intents/{intent_id}")
    
    def confirm_payment(
        self,
        intent_id: str,
        signature: str,
        payer_address: str
    ) -> Dict[str, Any]:
        """
        Confirm a payment intent after user signs the transaction.
        
        This should be called after the user has:
        1. Connected their wallet
        2. Signed the EIP-712 typed data
        
        Args:
            intent_id: The payment intent ID
            signature: EIP-712 signature from user's wallet (0x...)
            payer_address: User's Ethereum wallet address (0x...)
            
        Returns:
            Updated payment intent with:
            - status: PROCESSING
            - transactionHash: Blockchain transaction hash
        """
        if self.mock_mode:
            return self._mock_confirm_payment(intent_id, signature, payer_address)
        
        payload = {
            "signature": signature,
            "payerAddress": payer_address
        }
        
        return self._request("POST", f"/payment-intents/{intent_id}/confirm", json=payload)
    
    def cancel_payment(self, intent_id: str) -> Dict[str, Any]:
        """
        Cancel a payment intent.
        
        Can only cancel payments in INITIATED or REQUIRES_SIGNATURE status.
        
        Args:
            intent_id: The payment intent ID
            
        Returns:
            Cancelled payment intent object
        """
        if self.mock_mode:
            return self._mock_cancel_payment(intent_id)
        
        return self._request("POST", f"/payment-intents/{intent_id}/cancel")
    
    # ==================== CONDITIONAL PAYMENTS (ESCROW) ====================
    
    def get_conditional_payment(self, intent_id: str) -> Dict[str, Any]:
        """
        Get conditional payment (escrow) details for a payment intent.
        
        Only available for DELIVERY_VS_PAYMENT type payments.
        
        Args:
            intent_id: The payment intent ID
            
        Returns:
            Conditional payment object with:
            - orderStatus: PENDING, SHIPPED, DELIVERED, COMPLETED, etc.
            - settlementStatus: NONE, SCHEDULED, EXECUTED, etc.
            - deliveryDeadline, disputeWindow, etc.
        """
        return self._request("GET", f"/payment-intents/{intent_id}/escrow")
    
    def submit_delivery_proof(
        self,
        intent_id: str,
        proof_hash: str,
        submitted_by: str,
        proof_uri: Optional[str] = None,
        submit_tx_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit delivery proof for a conditional payment.
        
        This releases escrowed funds to the merchant if autoReleaseOnProof is enabled.
        
        Args:
            intent_id: The payment intent ID
            proof_hash: Keccak256 hash of delivery proof (bytes32 hex)
            submitted_by: Ethereum address of submitter
            proof_uri: Optional URI to proof document (IPFS, HTTP)
            submit_tx_hash: Optional on-chain transaction hash
            
        Returns:
            Delivery proof object
        """
        payload = {
            "proofHash": proof_hash,
            "submittedBy": submitted_by
        }
        
        if proof_uri:
            payload["proofURI"] = proof_uri
        if submit_tx_hash:
            payload["submitTxHash"] = submit_tx_hash
        
        return self._request("POST", f"/payment-intents/{intent_id}/escrow/delivery-proof", json=payload)
    
    def raise_dispute(
        self,
        intent_id: str,
        reason: str,
        raised_by: str,
        dispute_window: str = "604800"  # 7 days default
    ) -> Dict[str, Any]:
        """
        Raise a dispute for a conditional payment.
        
        This pauses fund release until dispute is resolved.
        
        Args:
            intent_id: The payment intent ID
            reason: Reason for the dispute
            raised_by: Ethereum address raising the dispute
            dispute_window: Dispute window in seconds (default: 7 days)
            
        Returns:
            Dispute status object
        """
        payload = {
            "reason": reason,
            "raisedBy": raised_by,
            "disputeWindow": dispute_window
        }
        
        return self._request("POST", f"/payment-intents/{intent_id}/escrow/dispute", json=payload)
    
    # ==================== UTILITY METHODS ====================
    
    def get_payment_url(self, intent_response: Dict[str, Any]) -> Optional[str]:
        """
        Extract payment URL from a payment intent response.
        
        Args:
            intent_response: Response from create_payment_intent
            
        Returns:
            Payment URL or None if not found
        """
        data = intent_response.get("data", intent_response)
        return data.get("paymentUrl")
    
    def get_typed_data(self, intent_response: Dict[str, Any]) -> Optional[Dict]:
        """
        Extract EIP-712 typed data from a payment intent response.
        
        This data is used by the frontend to request a wallet signature.
        
        Args:
            intent_response: Response from create_payment_intent or get_payment_intent
            
        Returns:
            Typed data object with domain, types, and message
        """
        data = intent_response.get("data", intent_response)
        return data.get("typedData")
    
    def is_payment_complete(self, status: str) -> bool:
        """Check if a payment status indicates completion."""
        return status in [self.STATUS_SUCCEEDED, self.STATUS_SETTLED, self.STATUS_FINAL]
    
    def is_payment_pending(self, status: str) -> bool:
        """Check if a payment is still pending action."""
        return status in [self.STATUS_INITIATED, self.STATUS_REQUIRES_SIGNATURE, self.STATUS_PROCESSING]


# ==================== LEGACY COMPATIBILITY ====================

def create_payment_intent(amount, currency="USDC", description=None):
    """Legacy function for backwards compatibility."""
    service = FinternetService()
    return service.create_payment_intent(
        amount=str(amount),
        currency=currency,
        description=description
    )


def fetch_intent(intent_id):
    """Legacy function for backwards compatibility."""
    service = FinternetService()
    return service.get_payment_intent(intent_id)
