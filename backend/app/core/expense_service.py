"""
Expense Distribution Service - Split calculation and validation.

Responsibilities:
- Calculate equal splits
- Calculate weighted/margin-based splits
- Calculate actual amount spent per participant
- Support mixed split types
- Validate splits sum to total
- Validate only authorized participants
"""
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId
from decimal import Decimal, ROUND_HALF_UP

from app.extensions import db as mongo


class SplitType:
    """Split type constants."""
    EQUAL = "equal"
    WEIGHTED = "weighted"
    PERCENTAGE = "percentage"
    EXACT = "exact"
    ACTUAL = "actual"  # Actual amount spent per participant
    MARGIN = "margin"  # Creator-defined margin-based


class ExpenseDistributionService:
    """Service for expense split calculation and validation."""
    
    @classmethod
    def calculate_equal_split(
        cls,
        total_amount: float,
        participant_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Calculate equal split among participants.
        
        Handles remainder cents by adding to first participant.
        
        Args:
            total_amount: Total expense amount
            participant_ids: List of participant user IDs
            
        Returns:
            List of {user_id, amount, split_type} dicts
        """
        if not participant_ids:
            return []
        
        n = len(participant_ids)
        # Use Decimal for precision
        total = Decimal(str(total_amount))
        base_split = (total / n).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        splits = []
        running_total = Decimal('0')
        
        for i, user_id in enumerate(participant_ids):
            if i == n - 1:
                # Last person gets remainder to ensure exact total
                amount = total - running_total
            else:
                amount = base_split
                running_total += amount
            
            splits.append({
                "user_id": user_id,
                "amount": float(amount),
                "split_type": SplitType.EQUAL
            })
        
        return splits
    
    @classmethod
    def calculate_weighted_split(
        cls,
        total_amount: float,
        weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Calculate weighted split based on participant weights.
        
        Args:
            total_amount: Total expense amount
            weights: Dict of {user_id: weight}
            
        Returns:
            List of {user_id, amount, weight, split_type} dicts
        """
        if not weights:
            return []
        
        total_weight = sum(weights.values())
        if total_weight == 0:
            return []
        
        total = Decimal(str(total_amount))
        splits = []
        running_total = Decimal('0')
        weight_items = list(weights.items())
        
        for i, (user_id, weight) in enumerate(weight_items):
            if i == len(weight_items) - 1:
                amount = total - running_total
            else:
                ratio = Decimal(str(weight)) / Decimal(str(total_weight))
                amount = (total * ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                running_total += amount
            
            splits.append({
                "user_id": user_id,
                "amount": float(amount),
                "weight": weight,
                "split_type": SplitType.WEIGHTED
            })
        
        return splits
    
    @classmethod
    def calculate_percentage_split(
        cls,
        total_amount: float,
        percentages: Dict[str, float]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Calculate split based on percentages.
        
        Args:
            total_amount: Total expense amount
            percentages: Dict of {user_id: percentage} (should sum to 100)
            
        Returns:
            Tuple of (splits list, error message if invalid)
        """
        if not percentages:
            return [], "No percentages provided"
        
        total_pct = sum(percentages.values())
        if abs(total_pct - 100) > 0.01:
            return [], f"Percentages must sum to 100, got {total_pct}"
        
        total = Decimal(str(total_amount))
        splits = []
        running_total = Decimal('0')
        pct_items = list(percentages.items())
        
        for i, (user_id, pct) in enumerate(pct_items):
            if i == len(pct_items) - 1:
                amount = total - running_total
            else:
                amount = (total * Decimal(str(pct)) / 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                running_total += amount
            
            splits.append({
                "user_id": user_id,
                "amount": float(amount),
                "percentage": pct,
                "split_type": SplitType.PERCENTAGE
            })
        
        return splits, None
    
    @classmethod
    def calculate_exact_split(
        cls,
        total_amount: float,
        exact_amounts: Dict[str, float]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Validate and use exact amounts per participant.
        
        Args:
            total_amount: Total expense amount
            exact_amounts: Dict of {user_id: exact_amount}
            
        Returns:
            Tuple of (splits list, error message if invalid)
        """
        if not exact_amounts:
            return [], "No amounts provided"
        
        amounts_sum = sum(exact_amounts.values())
        if abs(amounts_sum - total_amount) > 0.01:
            return [], f"Amounts sum to {amounts_sum}, expected {total_amount}"
        
        splits = []
        for user_id, amount in exact_amounts.items():
            splits.append({
                "user_id": user_id,
                "amount": round(float(amount), 2),
                "split_type": SplitType.EXACT
            })
        
        return splits, None
    
    @classmethod
    def calculate_margin_split(
        cls,
        base_amount: float,
        participant_ids: List[str],
        margin_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Calculate split with creator-defined margin.
        
        Margin can be:
        - Fixed amount per person
        - Percentage on top of base
        - Different margins per participant
        
        Args:
            base_amount: Base expense amount
            participant_ids: List of participant user IDs
            margin_config: {
                "type": "fixed" | "percentage",
                "value": float,  # Amount or percentage
                "per_user": {user_id: margin}  # Optional per-user overrides
            }
            
        Returns:
            List of {user_id, base, margin, amount, split_type} dicts
        """
        if not participant_ids:
            return []
        
        n = len(participant_ids)
        base_per_person = base_amount / n
        margin_type = margin_config.get("type", "fixed")
        default_margin = margin_config.get("value", 0)
        per_user_margins = margin_config.get("per_user", {})
        
        splits = []
        for user_id in participant_ids:
            user_margin = per_user_margins.get(user_id, default_margin)
            
            if margin_type == "percentage":
                margin_amount = base_per_person * (user_margin / 100)
            else:  # fixed
                margin_amount = user_margin
            
            total = base_per_person + margin_amount
            
            splits.append({
                "user_id": user_id,
                "base": round(base_per_person, 2),
                "margin": round(margin_amount, 2),
                "amount": round(total, 2),
                "split_type": SplitType.MARGIN
            })
        
        return splits
    
    @classmethod
    def calculate_mixed_split(
        cls,
        total_amount: float,
        split_config: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Calculate mixed split with different types per participant.
        
        Args:
            total_amount: Total expense amount
            split_config: {
                "default_type": "equal",
                "participants": [
                    {"user_id": "...", "type": "exact", "value": 50},
                    {"user_id": "...", "type": "percentage", "value": 30},
                    {"user_id": "...", "type": "equal"},  # Will share remaining
                ]
            }
            
        Returns:
            Tuple of (splits list, error message if invalid)
        """
        participants = split_config.get("participants", [])
        if not participants:
            return [], "No participants provided"
        
        total = Decimal(str(total_amount))
        allocated = Decimal('0')
        splits = []
        equal_share_users = []
        
        # First pass: allocate exact and percentage amounts
        for p in participants:
            user_id = p["user_id"]
            split_type = p.get("type", split_config.get("default_type", "equal"))
            value = p.get("value", 0)
            
            if split_type == "exact":
                amount = Decimal(str(value)).quantize(Decimal('0.01'))
                allocated += amount
                splits.append({
                    "user_id": user_id,
                    "amount": float(amount),
                    "split_type": SplitType.EXACT
                })
            
            elif split_type == "percentage":
                amount = (total * Decimal(str(value)) / 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                allocated += amount
                splits.append({
                    "user_id": user_id,
                    "amount": float(amount),
                    "percentage": value,
                    "split_type": SplitType.PERCENTAGE
                })
            
            else:  # equal - will be calculated later
                equal_share_users.append(user_id)
        
        # Second pass: distribute remaining to equal share users
        if equal_share_users:
            remaining = total - allocated
            if remaining < 0:
                return [], f"Over-allocated by ${abs(float(remaining)):.2f}"
            
            per_person = remaining / len(equal_share_users)
            running = Decimal('0')
            
            for i, user_id in enumerate(equal_share_users):
                if i == len(equal_share_users) - 1:
                    amount = remaining - running
                else:
                    amount = per_person.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    running += amount
                
                splits.append({
                    "user_id": user_id,
                    "amount": float(amount),
                    "split_type": SplitType.EQUAL
                })
        else:
            # Validate exact allocation
            if abs(allocated - total) > Decimal('0.01'):
                return [], f"Total mismatch: allocated {float(allocated)}, expected {total_amount}"
        
        return splits, None
    
    @classmethod
    def validate_splits(
        cls,
        event_id: str,
        total_amount: float,
        splits: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that splits are correct.
        
        Checks:
        - Splits sum to total
        - All users are authorized participants
        - No duplicate users
        - No negative amounts
        
        Args:
            event_id: Event ID
            total_amount: Expected total
            splits: List of split dicts with user_id and amount
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not splits:
            return False, "No splits provided"
        
        # Check for negative amounts
        for s in splits:
            if s.get("amount", 0) < 0:
                return False, f"Negative amount for user {s['user_id']}"
        
        # Check for duplicates
        user_ids = [s["user_id"] for s in splits]
        if len(user_ids) != len(set(user_ids)):
            return False, "Duplicate users in splits"
        
        # Check sum
        splits_sum = sum(s.get("amount", 0) for s in splits)
        if abs(splits_sum - total_amount) > 0.01:
            return False, f"Splits sum to {splits_sum}, expected {total_amount}"
        
        # Check all users are authorized participants
        for user_id in user_ids:
            participant = mongo.participants.find_one({
                "event_id": ObjectId(event_id),
                "user_id": ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id,
                "status": {"$in": ["active", "approved"]}
            })
            
            if not participant:
                return False, f"User {user_id} is not an authorized participant"
        
        return True, None
    
    @classmethod
    def create_expense_with_splits(
        cls,
        event_id: str,
        payer_id: str,
        amount: float,
        description: str,
        split_type: str,
        split_config: Optional[Dict] = None,
        category_id: Optional[str] = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Create an expense with calculated splits.
        
        Args:
            event_id: Event ID
            payer_id: User who paid
            amount: Total amount
            description: Expense description
            split_type: Type of split (equal, weighted, etc.)
            split_config: Configuration for non-equal splits
            category_id: Optional category ID
            
        Returns:
            Tuple of (expense dict, error message)
        """
        # Get active participants
        participants = list(mongo.participants.find({
            "event_id": ObjectId(event_id),
            "status": {"$in": ["active", "approved"]}
        }))
        
        if not participants:
            return None, "No active participants"
        
        participant_ids = [str(p["user_id"]) for p in participants]
        
        # Calculate splits based on type
        error = None
        
        if split_type == SplitType.EQUAL:
            splits = cls.calculate_equal_split(amount, participant_ids)
        
        elif split_type == SplitType.WEIGHTED:
            weights = split_config.get("weights", {}) if split_config else {}
            if not weights:
                # Default equal weights
                weights = {uid: 1 for uid in participant_ids}
            splits = cls.calculate_weighted_split(amount, weights)
        
        elif split_type == SplitType.PERCENTAGE:
            percentages = split_config.get("percentages", {}) if split_config else {}
            splits, error = cls.calculate_percentage_split(amount, percentages)
        
        elif split_type == SplitType.EXACT:
            exact_amounts = split_config.get("amounts", {}) if split_config else {}
            splits, error = cls.calculate_exact_split(amount, exact_amounts)
        
        elif split_type == SplitType.MARGIN:
            margin_config = split_config or {}
            splits = cls.calculate_margin_split(amount, participant_ids, margin_config)
        
        elif split_type == "mixed":
            splits, error = cls.calculate_mixed_split(amount, split_config or {})
        
        else:
            # Default to equal
            splits = cls.calculate_equal_split(amount, participant_ids)
        
        if error:
            return None, error
        
        # Validate splits
        is_valid, validation_error = cls.validate_splits(event_id, amount, splits)
        if not is_valid:
            return None, validation_error
        
        # Mark payer's split as paid
        for s in splits:
            s["status"] = "paid" if s["user_id"] == payer_id else "pending"
        
        # Create expense document
        expense = {
            "event_id": ObjectId(event_id),
            "payer_id": ObjectId(payer_id),
            "amount": round(amount, 2),
            "description": description,
            "category_id": ObjectId(category_id) if category_id else None,
            "split_type": split_type,
            "splits": splits,
            "status": "pending",  # Will be updated by approval service
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        return expense, None
    
    @classmethod
    def get_user_expense_share(cls, expense: Dict, user_id: str) -> float:
        """Get a specific user's share in an expense."""
        for split in expense.get("splits", []):
            if split["user_id"] == user_id:
                return float(split.get("amount", 0))
        return 0.0
