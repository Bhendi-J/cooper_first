"""
Rule Enforcement Service - Creator-defined rules enforcement.

Responsibilities:
- Enforce minimum/maximum deposit limits
- Enforce deposit margin ranges
- Enforce maximum expense per transaction
- Enforce maximum cumulative spend per user
- Enforce warning and approval thresholds
- Enforce category-based spending restrictions
"""
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId

from app.extensions import db as mongo


class RuleViolationType:
    """Rule violation type constants."""
    MIN_DEPOSIT = "min_deposit"
    MAX_DEPOSIT = "max_deposit"
    DEPOSIT_MARGIN = "deposit_margin"
    MAX_EXPENSE = "max_expense"
    MAX_CUMULATIVE_SPEND = "max_cumulative_spend"
    APPROVAL_REQUIRED = "approval_required"
    WARNING_THRESHOLD = "warning_threshold"
    CATEGORY_RESTRICTED = "category_restricted"
    INSUFFICIENT_POOL = "insufficient_pool"


class RuleEnforcementService:
    """Service for enforcing creator-defined rules."""
    
    @classmethod
    def get_event_rules(cls, event_id: str) -> Dict[str, Any]:
        """
        Get all rules for an event.
        
        Returns default rules if none set.
        """
        event = mongo.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            return {}
        
        default_rules = {
            # Deposit rules
            "min_deposit": None,
            "max_deposit": None,
            "deposit_margin_min": None,
            "deposit_margin_max": None,
            
            # Expense rules
            "max_expense_per_transaction": None,
            "max_cumulative_spend_per_user": None,
            
            # Threshold rules
            "warning_threshold": None,  # Amount that triggers warning
            "approval_required_threshold": None,  # Amount that requires approval
            "auto_approve_under": 100,  # Auto-approve expenses under this amount
            
            # Category rules
            "restricted_categories": [],  # Categories that need approval
            "blocked_categories": [],  # Categories that are not allowed
            
            # General
            "approval_required": False,  # All expenses need approval
            "allow_wallet_fallback": True,  # Allow personal wallet for shortfall
            "max_debt_allowed": None,  # Maximum debt per user
        }
        
        event_rules = event.get("rules", {})
        
        # Merge with defaults
        for key, default in default_rules.items():
            if key not in event_rules or event_rules[key] is None:
                event_rules[key] = default
        
        return event_rules
    
    @classmethod
    def validate_deposit(
        cls,
        event_id: str,
        user_id: str,
        amount: float
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate a deposit against event rules.
        
        Args:
            event_id: Event ID
            user_id: User making deposit
            amount: Deposit amount
            
        Returns:
            Tuple of (is_valid, error_message, violation_type)
        """
        rules = cls.get_event_rules(event_id)
        
        if not rules:
            return True, None, None
        
        # Check minimum deposit
        min_deposit = rules.get("min_deposit")
        if min_deposit is not None and amount < min_deposit:
            return False, f"Minimum deposit is ${min_deposit:.2f}", RuleViolationType.MIN_DEPOSIT
        
        # Check maximum deposit
        max_deposit = rules.get("max_deposit")
        if max_deposit is not None and amount > max_deposit:
            return False, f"Maximum deposit is ${max_deposit:.2f}", RuleViolationType.MAX_DEPOSIT
        
        # Check deposit margin range
        margin_min = rules.get("deposit_margin_min")
        margin_max = rules.get("deposit_margin_max")
        
        if margin_min is not None or margin_max is not None:
            # Get average deposit
            participants = list(mongo.participants.find({
                "event_id": ObjectId(event_id),
                "status": {"$in": ["active", "approved"]}
            }))
            
            if participants:
                total_deposits = sum(p.get("deposit_amount", 0) for p in participants)
                avg_deposit = total_deposits / len(participants) if participants else 0
                
                if avg_deposit > 0:
                    margin = ((amount - avg_deposit) / avg_deposit) * 100
                    
                    if margin_min is not None and margin < margin_min:
                        return False, f"Deposit is {abs(margin):.1f}% below average (min margin: {margin_min}%)", RuleViolationType.DEPOSIT_MARGIN
                    
                    if margin_max is not None and margin > margin_max:
                        return False, f"Deposit is {margin:.1f}% above average (max margin: {margin_max}%)", RuleViolationType.DEPOSIT_MARGIN
        
        return True, None, None
    
    @classmethod
    def validate_expense(
        cls,
        event_id: str,
        payer_id: str,
        amount: float,
        category_id: Optional[str] = None,
        splits: Optional[List[Dict]] = None
    ) -> Tuple[bool, Optional[str], Optional[str], bool]:
        """
        Validate an expense against event rules.
        
        Args:
            event_id: Event ID
            payer_id: User creating expense
            amount: Expense amount
            category_id: Category of expense
            splits: Expense splits
            
        Returns:
            Tuple of (is_valid, error_message, violation_type, requires_approval)
        """
        rules = cls.get_event_rules(event_id)
        requires_approval = False
        
        if not rules:
            return True, None, None, False
        
        # Check if category is blocked
        blocked_categories = rules.get("blocked_categories", [])
        if category_id and category_id in blocked_categories:
            category = mongo.categories.find_one({"_id": ObjectId(category_id)})
            cat_name = category.get("name", "This category") if category else "This category"
            return False, f"{cat_name} expenses are not allowed", RuleViolationType.CATEGORY_RESTRICTED, False
        
        # Check minimum expense per transaction
        min_expense = rules.get("min_expense_per_transaction")
        if min_expense is not None and amount < min_expense:
            return False, f"Minimum expense per transaction is ${min_expense:.2f}", "min_expense", False
        
        # Check maximum expense per transaction
        max_expense = rules.get("max_expense_per_transaction")
        if max_expense is not None and amount > max_expense:
            return False, f"Maximum expense per transaction is ${max_expense:.2f}", RuleViolationType.MAX_EXPENSE, False
        
        # Check cumulative spend per user if splits provided
        if splits:
            max_cumulative = rules.get("max_cumulative_spend_per_user")
            if max_cumulative is not None:
                for split in splits:
                    user_id = split["user_id"]
                    split_amount = split["amount"]
                    
                    # Get user's current total spent
                    participant = mongo.participants.find_one({
                        "event_id": ObjectId(event_id),
                        "user_id": ObjectId(user_id)
                    })
                    
                    current_spent = participant.get("total_spent", 0) if participant else 0
                    new_total = current_spent + split_amount
                    
                    if new_total > max_cumulative:
                        user = mongo.users.find_one({"_id": ObjectId(user_id)})
                        user_name = user.get("name", "User") if user else "User"
                        return False, f"{user_name}'s cumulative spend would exceed limit (${max_cumulative:.2f})", RuleViolationType.MAX_CUMULATIVE_SPEND, False
        
        # Check pool availability
        event = mongo.events.find_one({"_id": ObjectId(event_id)})
        if event:
            available = event.get("total_pool", 0) - event.get("total_spent", 0)
            if amount > available:
                return False, f"Insufficient pool balance. Available: ${available:.2f}", RuleViolationType.INSUFFICIENT_POOL, False
        
        # Check if approval required (always or by threshold)
        if rules.get("approval_required", False):
            requires_approval = True
        
        approval_threshold = rules.get("approval_required_threshold")
        if approval_threshold is not None and amount >= approval_threshold:
            requires_approval = True
        
        # Check if category requires approval
        restricted_categories = rules.get("restricted_categories", [])
        if category_id and category_id in restricted_categories:
            requires_approval = True
        
        # Check auto-approve threshold
        auto_approve = rules.get("auto_approve_under")
        if auto_approve is not None and amount < auto_approve:
            requires_approval = False
        
        return True, None, None, requires_approval
    
    @classmethod
    def check_warning_threshold(
        cls,
        event_id: str,
        amount: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if expense triggers a warning.
        
        Args:
            event_id: Event ID
            amount: Expense amount
            
        Returns:
            Tuple of (triggers_warning, warning_message)
        """
        rules = cls.get_event_rules(event_id)
        
        warning_threshold = rules.get("warning_threshold")
        if warning_threshold is not None and amount >= warning_threshold:
            return True, f"Expense of ${amount:.2f} exceeds warning threshold (${warning_threshold:.2f})"
        
        return False, None
    
    @classmethod
    def validate_join(
        cls,
        event_id: str,
        user_id: str,
        deposit_amount: Optional[float] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate a join request against event rules.
        
        Args:
            event_id: Event ID
            user_id: User trying to join
            deposit_amount: Initial deposit amount (if required)
            
        Returns:
            Tuple of (is_valid, error_message, violation_type)
        """
        rules = cls.get_event_rules(event_id)
        
        if not rules:
            return True, None, None
        
        # Check if minimum deposit is required to join
        min_deposit = rules.get("min_deposit")
        if min_deposit is not None:
            if deposit_amount is None:
                return False, f"Initial deposit of at least ${min_deposit:.2f} is required to join", RuleViolationType.MIN_DEPOSIT
            if deposit_amount < min_deposit:
                return False, f"Minimum deposit is ${min_deposit:.2f}", RuleViolationType.MIN_DEPOSIT
        
        return True, None, None
    
    @classmethod
    def record_rule_violation(
        cls,
        event_id: str,
        user_id: str,
        violation_type: str,
        details: str,
        amount: Optional[float] = None,
        expense_id: Optional[str] = None
    ) -> str:
        """
        Record a rule violation for audit.
        
        Returns:
            Violation record ID
        """
        record = {
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id),
            "violation_type": violation_type,
            "details": details,
            "amount": amount,
            "expense_id": ObjectId(expense_id) if expense_id else None,
            "created_at": datetime.utcnow()
        }
        
        result = mongo.rule_violations.insert_one(record)
        return str(result.inserted_id)
    
    @classmethod
    def get_user_violations(
        cls,
        event_id: str,
        user_id: str
    ) -> List[Dict]:
        """Get all violations for a user in an event."""
        violations = list(mongo.rule_violations.find({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id)
        }).sort("created_at", -1))
        
        for v in violations:
            v["_id"] = str(v["_id"])
            v["event_id"] = str(v["event_id"])
            v["user_id"] = str(v["user_id"])
            if v.get("expense_id"):
                v["expense_id"] = str(v["expense_id"])
        
        return violations
    
    @classmethod
    def update_rules(
        cls,
        event_id: str,
        creator_id: str,
        new_rules: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Update event rules (creator only).
        
        Args:
            event_id: Event ID
            creator_id: User attempting update
            new_rules: New rules to set
            
        Returns:
            Tuple of (success, error_message)
        """
        event = mongo.events.find_one({"_id": ObjectId(event_id)})
        
        if not event:
            return False, "Event not found"
        
        if str(event["creator_id"]) != creator_id:
            return False, "Only the event creator can update rules"
        
        # Merge with existing rules
        current_rules = event.get("rules", {})
        current_rules.update(new_rules)
        
        mongo.events.update_one(
            {"_id": ObjectId(event_id)},
            {
                "$set": {
                    "rules": current_rules,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Record rule change activity
        mongo.activities.insert_one({
            "type": "rules_updated",
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(creator_id),
            "changes": new_rules,
            "created_at": datetime.utcnow()
        })
        
        return True, None
