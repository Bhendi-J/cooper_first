"""Settlement calculation service - Splitwise-style debt minimization."""
from typing import List, Dict, Any, Tuple
from bson import ObjectId
from datetime import datetime
from app.extensions import db as mongo


class SettlementCalculator:
    """Calculate balances and minimize settlement transactions."""
    
    @staticmethod
    def get_balances(event_id: str) -> List[Dict[str, Any]]:
        """
        Get all participant balances for an event.
        
        Returns list of: {user_id, username, balance}
        - Positive balance = is owed money (others owe them)
        - Negative balance = owes money (they owe others)
        """
        participants = list(mongo.participants.find(
            {"event_id": ObjectId(event_id), "status": "active"}
        ))
        
        balances = []
        for p in participants:
            user = mongo.users.find_one({"_id": p["user_id"]})
            balances.append({
                "user_id": str(p["user_id"]),
                "username": user.get("username", "Unknown") if user else "Unknown",
                "email": user.get("email", "") if user else "",
                "balance": round(p.get("balance", 0), 2),
                "total_spent": round(p.get("total_spent", 0), 2)
            })
        
        return balances
    
    @staticmethod
    def calculate_debts(event_id: str) -> List[Dict[str, Any]]:
        """
        Calculate who owes whom using greedy algorithm to minimize transactions.
        
        Returns list of: {from_user, from_username, to_user, to_username, amount}
        """
        balances = SettlementCalculator.get_balances(event_id)
        
        # Separate creditors (positive balance) and debtors (negative balance)
        creditors = []  # People who are OWED money
        debtors = []    # People who OWE money
        
        for b in balances:
            if b["balance"] > 0.01:  # Small threshold to avoid floating point issues
                creditors.append({
                    "user_id": b["user_id"],
                    "username": b["username"],
                    "amount": b["balance"]
                })
            elif b["balance"] < -0.01:
                debtors.append({
                    "user_id": b["user_id"],
                    "username": b["username"],
                    "amount": -b["balance"]  # Make positive for easier calculation
                })
        
        # Sort by amount for more efficient matching
        creditors.sort(key=lambda x: -x["amount"])
        debtors.sort(key=lambda x: -x["amount"])
        
        settlements = []
        
        # Greedy matching to minimize transactions
        for debtor in debtors:
            debt = debtor["amount"]
            
            while debt > 0.01 and creditors:
                creditor = creditors[0]
                
                # Calculate how much this debtor can pay this creditor
                amount = min(debt, creditor["amount"])
                amount = round(amount, 2)
                
                if amount > 0.01:
                    settlements.append({
                        "from_user": debtor["user_id"],
                        "from_username": debtor["username"],
                        "to_user": creditor["user_id"],
                        "to_username": creditor["username"],
                        "amount": amount
                    })
                
                debt -= amount
                creditor["amount"] -= amount
                
                # Remove creditor if fully paid
                if creditor["amount"] < 0.01:
                    creditors.pop(0)
        
        return settlements
    
    @staticmethod
    def record_settlement(
        event_id: str,
        from_user_id: str,
        to_user_id: str,
        amount: float,
        payment_method: str = "finternet"
    ) -> Dict[str, Any]:
        """
        Record a settlement payment between two users.
        Updates their balances accordingly.
        """
        amount = round(amount, 2)
        
        # Create settlement record
        settlement = {
            "event_id": ObjectId(event_id),
            "from_user_id": ObjectId(from_user_id),
            "to_user_id": ObjectId(to_user_id),
            "amount": amount,
            "payment_method": payment_method,
            "status": "completed",
            "created_at": datetime.utcnow()
        }
        
        result = mongo.settlements.insert_one(settlement)
        
        # Update balances:
        # - from_user's balance increases (less debt)
        # - to_user's balance decreases (received payment)
        
        mongo.participants.update_one(
            {"event_id": ObjectId(event_id), "user_id": ObjectId(from_user_id)},
            {"$inc": {"balance": amount}}
        )
        
        mongo.participants.update_one(
            {"event_id": ObjectId(event_id), "user_id": ObjectId(to_user_id)},
            {"$inc": {"balance": -amount}}
        )
        
        settlement["_id"] = str(result.inserted_id)
        settlement["event_id"] = str(settlement["event_id"])
        settlement["from_user_id"] = str(settlement["from_user_id"])
        settlement["to_user_id"] = str(settlement["to_user_id"])
        settlement["created_at"] = settlement["created_at"].isoformat()
        
        return settlement
    
    @staticmethod
    def get_settlement_history(event_id: str) -> List[Dict[str, Any]]:
        """Get all settlements for an event."""
        settlements = list(mongo.settlements.find(
            {"event_id": ObjectId(event_id)}
        ).sort("created_at", -1))
        
        result = []
        for s in settlements:
            from_user = mongo.users.find_one({"_id": s["from_user_id"]})
            to_user = mongo.users.find_one({"_id": s["to_user_id"]})
            
            result.append({
                "_id": str(s["_id"]),
                "event_id": str(s["event_id"]),
                "from_user_id": str(s["from_user_id"]),
                "from_username": from_user.get("username", "Unknown") if from_user else "Unknown",
                "to_user_id": str(s["to_user_id"]),
                "to_username": to_user.get("username", "Unknown") if to_user else "Unknown",
                "amount": s["amount"],
                "payment_method": s.get("payment_method", "manual"),
                "status": s.get("status", "completed"),
                "created_at": s["created_at"].isoformat() if hasattr(s["created_at"], "isoformat") else str(s["created_at"])
            })
        
        return result
