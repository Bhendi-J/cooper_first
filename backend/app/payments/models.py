"""
Payment models for Finternet integration.

These models represent local records of payment intents,
synced with the Finternet API.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId
from app.extensions import db as mongo


# ==================== DATA CLASSES ====================

@dataclass
class PaymentIntent:
    """Local record of a Finternet payment intent."""
    id: str  # Finternet intent ID (intent_xxx)
    amount: float
    currency: str
    status: str
    
    # Related entities
    event_id: Optional[str] = None
    expense_id: Optional[str] = None
    user_id: Optional[str] = None  # Payer user ID
    
    # Finternet data
    payment_url: Optional[str] = None
    typed_data: Optional[Dict] = None
    transaction_hash: Optional[str] = None
    settlement_status: Optional[str] = None
    
    # Wallet info
    payer_address: Optional[str] = None
    signature: Optional[str] = None
    
    # Metadata
    description: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None


@dataclass
class ConditionalPayment:
    """Local record of a conditional payment (escrow)."""
    id: str  # Finternet conditional payment ID
    payment_intent_id: str
    
    # Contract details
    contract_address: Optional[str] = None
    order_id: Optional[str] = None
    
    # Parties
    buyer_address: Optional[str] = None
    merchant_id: Optional[str] = None
    
    # Payment details
    amount: float = 0.0
    token_address: Optional[str] = None
    
    # Delivery settings
    delivery_period: int = 2592000  # 30 days default
    delivery_deadline: Optional[str] = None
    auto_release_on_proof: bool = True
    release_type: str = "DELIVERY_PROOF"
    
    # Status
    order_status: str = "PENDING"  # PENDING, SHIPPED, DELIVERED, COMPLETED, CANCELLED, DISPUTED
    settlement_status: str = "NONE"  # NONE, SCHEDULED, EXECUTED, CONFIRMED, CANCELLED
    
    # Dispute info
    dispute_window: int = 604800  # 7 days default
    dispute_raised_at: Optional[datetime] = None
    dispute_reason: Optional[str] = None
    dispute_raised_by: Optional[str] = None
    
    # Proof info
    expected_delivery_hash: Optional[str] = None
    actual_delivery_hash: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    released_at: Optional[datetime] = None


# ==================== DATABASE OPERATIONS ====================

class PaymentIntentDB:
    """Database operations for payment intents."""
    
    COLLECTION = "payment_intents"
    
    @classmethod
    def create(cls, intent_data: Dict[str, Any]) -> str:
        """
        Create a new payment intent record.
        
        Args:
            intent_data: Payment intent data from Finternet API
            
        Returns:
            MongoDB document ID
        """
        doc = {
            "finternet_id": intent_data.get("id"),
            "amount": float(intent_data.get("data", {}).get("amount", 0)),
            "currency": intent_data.get("data", {}).get("currency", "USDC"),
            "status": intent_data.get("status", "INITIATED"),
            "payment_url": intent_data.get("data", {}).get("paymentUrl"),
            "typed_data": intent_data.get("data", {}).get("typedData"),
            "contract_address": intent_data.get("data", {}).get("contractAddress"),
            "chain_id": intent_data.get("data", {}).get("chainId"),
            "description": intent_data.get("data", {}).get("description"),
            "settlement_method": intent_data.get("data", {}).get("settlementMethod"),
            "settlement_destination": intent_data.get("data", {}).get("settlementDestination"),
            "settlement_status": intent_data.get("data", {}).get("settlementStatus"),
            "metadata": intent_data.get("data", {}).get("metadata", {}),
            "phases": intent_data.get("data", {}).get("phases", []),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = mongo.payment_intents.insert_one(doc)
        return str(result.inserted_id)
    
    @classmethod
    def find_by_finternet_id(cls, finternet_id: str) -> Optional[Dict]:
        """Find a payment intent by Finternet ID."""
        doc = mongo.payment_intents.find_one({"finternet_id": finternet_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
    
    @classmethod
    def find_by_id(cls, doc_id: str) -> Optional[Dict]:
        """Find a payment intent by MongoDB ID."""
        doc = mongo.payment_intents.find_one({"_id": ObjectId(doc_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
    
    @classmethod
    def update_status(cls, finternet_id: str, status: str, extra_data: Dict = None) -> bool:
        """
        Update payment intent status.
        
        Args:
            finternet_id: Finternet payment intent ID
            status: New status
            extra_data: Additional fields to update
            
        Returns:
            True if updated, False if not found
        """
        update = {
            "$set": {
                "status": status,
                "updated_at": datetime.utcnow()
            }
        }
        
        if extra_data:
            update["$set"].update(extra_data)
        
        result = mongo.payment_intents.update_one(
            {"finternet_id": finternet_id},
            update
        )
        return result.modified_count > 0
    
    @classmethod
    def confirm(cls, finternet_id: str, signature: str, payer_address: str, tx_hash: str = None) -> bool:
        """Record payment confirmation."""
        update = {
            "$set": {
                "status": "PROCESSING",
                "signature": signature,
                "payer_address": payer_address,
                "confirmed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
        
        if tx_hash:
            update["$set"]["transaction_hash"] = tx_hash
        
        result = mongo.payment_intents.update_one(
            {"finternet_id": finternet_id},
            update
        )
        return result.modified_count > 0
    
    @classmethod
    def find_by_user(cls, user_id: str, limit: int = 20) -> List[Dict]:
        """Find payment intents for a user."""
        cursor = mongo.payment_intents.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(limit)
        
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    
    @classmethod
    def find_by_event(cls, event_id: str) -> List[Dict]:
        """Find payment intents for an event."""
        cursor = mongo.payment_intents.find(
            {"event_id": event_id}
        ).sort("created_at", -1)
        
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    
    @classmethod
    def find_pending(cls) -> List[Dict]:
        """Find all pending payment intents for status sync."""
        cursor = mongo.payment_intents.find({
            "status": {"$in": ["INITIATED", "REQUIRES_SIGNATURE", "PROCESSING"]}
        })
        
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results


class SplitPaymentDB:
    """Database operations for expense split payments."""
    
    @classmethod
    def create_for_expense(cls, expense_id: str, splits: List[Dict], payment_intents: List[Dict]) -> List[str]:
        """
        Create split payment records linking expense splits to payment intents.
        
        Args:
            expense_id: The expense ID
            splits: List of split objects from expense
            payment_intents: List of created payment intents
            
        Returns:
            List of created document IDs
        """
        docs = []
        intent_map = {p["user_id"]: p["intent"] for p in payment_intents}
        
        for split in splits:
            user_id = split["user_id"]
            intent = intent_map.get(user_id)
            
            doc = {
                "expense_id": ObjectId(expense_id),
                "user_id": user_id,
                "amount": split["amount"],
                "status": split["status"],
                "finternet_intent_id": intent.get("id") if intent else None,
                "payment_url": intent.get("data", {}).get("paymentUrl") if intent else None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            docs.append(doc)
        
        if docs:
            result = mongo.split_payments.insert_many(docs)
            return [str(id) for id in result.inserted_ids]
        return []
    
    @classmethod
    def find_by_expense(cls, expense_id: str) -> List[Dict]:
        """Find all split payments for an expense."""
        cursor = mongo.split_payments.find({"expense_id": ObjectId(expense_id)})
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            doc["expense_id"] = str(doc["expense_id"])
            results.append(doc)
        return results
    
    @classmethod
    def find_pending_for_user(cls, user_id: str) -> List[Dict]:
        """Find pending payments a user needs to complete."""
        cursor = mongo.split_payments.find({
            "user_id": user_id,
            "status": "pending"
        }).sort("created_at", -1)
        
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            doc["expense_id"] = str(doc["expense_id"])
            results.append(doc)
        return results
    
    @classmethod
    def mark_paid(cls, expense_id: str, user_id: str, tx_hash: str = None) -> bool:
        """Mark a split payment as paid."""
        update = {
            "$set": {
                "status": "paid",
                "paid_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
        if tx_hash:
            update["$set"]["transaction_hash"] = tx_hash
        
        result = mongo.split_payments.update_one(
            {"expense_id": ObjectId(expense_id), "user_id": user_id},
            update
        )
        return result.modified_count > 0

    @classmethod
    def mark_paid_by_intent(cls, intent_id: str, tx_hash: str = None) -> bool:
        """Mark a split payment as paid using the intent ID."""
        update = {
            "$set": {
                "status": "paid",
                "paid_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
        if tx_hash:
            update["$set"]["transaction_hash"] = tx_hash
        
        result = mongo.split_payments.update_one(
            {"finternet_intent_id": intent_id},
            update
        )
        return result.modified_count > 0
