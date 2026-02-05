"""
Reliability Service - Financial reliability tracking.

Responsibilities:
- Track repeated shortfalls
- Track outstanding debt duration
- Track delayed settlements
- Calculate reliability indicators
- Enforce stricter limits for unreliable users
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from bson import ObjectId

from app.extensions import db as mongo


class ReliabilityTier:
    """Reliability tier constants."""
    EXCELLENT = "excellent"      # No issues
    GOOD = "good"                # Minor issues
    FAIR = "fair"                # Some concerns
    POOR = "poor"                # Significant concerns
    RESTRICTED = "restricted"    # Major restrictions apply


class ReliabilityService:
    """Service for financial reliability tracking."""
    
    # Thresholds for reliability calculation
    SHORTFALL_WEIGHT = 10           # Points per shortfall
    DEBT_AGE_WEIGHT = 1             # Points per day of outstanding debt
    LATE_SETTLEMENT_WEIGHT = 5      # Points per late settlement
    
    # Tier thresholds (lower is better)
    EXCELLENT_MAX = 10
    GOOD_MAX = 30
    FAIR_MAX = 60
    POOR_MAX = 100
    # Above POOR_MAX = RESTRICTED
    
    @classmethod
    def calculate_reliability_score(cls, user_id: str) -> Dict[str, Any]:
        """
        Calculate user's reliability score based on financial behavior.
        
        Returns:
            Dict with score, tier, and breakdown
        """
        # Get shortfall history
        shortfalls = list(mongo.wallet_usage.find({
            "user_id": ObjectId(user_id),
            "type": "shortfall_coverage"
        }))
        shortfall_count = len(shortfalls)
        
        # Get debt history
        from .debt_service import DebtService
        outstanding_debts = DebtService.get_user_outstanding_debts(user_id)
        total_debt_days = sum(d.get("age_days", 0) for d in outstanding_debts)
        
        # Get all-time debt count
        all_debts = list(mongo.debts.find({"user_id": ObjectId(user_id)}))
        debt_count = len(all_debts)
        
        # Get late settlement count
        late_settlements = mongo.settlements.count_documents({
            "$or": [
                {"from_user_id": ObjectId(user_id)},
                {"to_user_id": ObjectId(user_id)}
            ],
            "was_late": True
        })
        
        # Calculate score
        score = (
            shortfall_count * cls.SHORTFALL_WEIGHT +
            total_debt_days * cls.DEBT_AGE_WEIGHT +
            late_settlements * cls.LATE_SETTLEMENT_WEIGHT
        )
        
        # Determine tier
        if score <= cls.EXCELLENT_MAX:
            tier = ReliabilityTier.EXCELLENT
        elif score <= cls.GOOD_MAX:
            tier = ReliabilityTier.GOOD
        elif score <= cls.FAIR_MAX:
            tier = ReliabilityTier.FAIR
        elif score <= cls.POOR_MAX:
            tier = ReliabilityTier.POOR
        else:
            tier = ReliabilityTier.RESTRICTED
        
        return {
            "user_id": user_id,
            "score": score,
            "tier": tier,
            "breakdown": {
                "shortfall_count": shortfall_count,
                "shortfall_points": shortfall_count * cls.SHORTFALL_WEIGHT,
                "total_debt_days": total_debt_days,
                "debt_points": total_debt_days * cls.DEBT_AGE_WEIGHT,
                "late_settlements": late_settlements,
                "late_points": late_settlements * cls.LATE_SETTLEMENT_WEIGHT,
                "total_debts_ever": debt_count,
                "current_outstanding_debts": len(outstanding_debts)
            },
            "calculated_at": datetime.utcnow()
        }
    
    @classmethod
    def get_user_tier(cls, user_id: str) -> str:
        """Get user's current reliability tier."""
        result = cls.calculate_reliability_score(user_id)
        return result["tier"]
    
    @classmethod
    def get_tier_restrictions(cls, tier: str) -> Dict[str, Any]:
        """
        Get restrictions that apply to a reliability tier.
        
        Returns:
            Dict of restriction settings
        """
        restrictions = {
            ReliabilityTier.EXCELLENT: {
                "max_expense_multiplier": 1.0,      # No reduction
                "requires_approval": False,
                "max_debt_allowed": None,           # No limit
                "can_create_events": True,
                "join_deposit_multiplier": 1.0,
                "warning_message": None
            },
            ReliabilityTier.GOOD: {
                "max_expense_multiplier": 1.0,
                "requires_approval": False,
                "max_debt_allowed": None,
                "can_create_events": True,
                "join_deposit_multiplier": 1.0,
                "warning_message": None
            },
            ReliabilityTier.FAIR: {
                "max_expense_multiplier": 0.8,      # 20% lower limits
                "requires_approval": False,
                "max_debt_allowed": 500,
                "can_create_events": True,
                "join_deposit_multiplier": 1.2,     # 20% higher deposit required
                "warning_message": "Your spending limits may be reduced due to past shortfalls."
            },
            ReliabilityTier.POOR: {
                "max_expense_multiplier": 0.5,      # 50% lower limits
                "requires_approval": True,          # All expenses need approval
                "max_debt_allowed": 200,
                "can_create_events": False,
                "join_deposit_multiplier": 1.5,     # 50% higher deposit required
                "warning_message": "Due to outstanding debts, your expenses require approval."
            },
            ReliabilityTier.RESTRICTED: {
                "max_expense_multiplier": 0,        # Cannot create expenses
                "requires_approval": True,
                "max_debt_allowed": 0,
                "can_create_events": False,
                "join_deposit_multiplier": 2.0,     # Double deposit required
                "warning_message": "Your account is restricted. Please settle outstanding debts."
            }
        }
        
        return restrictions.get(tier, restrictions[ReliabilityTier.EXCELLENT])
    
    @classmethod
    def apply_reliability_adjustments(
        cls,
        user_id: str,
        event_id: str,
        base_rules: Dict
    ) -> Dict:
        """
        Apply reliability-based adjustments to event rules for a user.
        
        Args:
            user_id: User ID
            event_id: Event context
            base_rules: Base event rules
            
        Returns:
            Adjusted rules for this user
        """
        tier = cls.get_user_tier(user_id)
        restrictions = cls.get_tier_restrictions(tier)
        
        adjusted = base_rules.copy()
        
        # Adjust max expense
        if adjusted.get("max_expense_per_transaction") is not None:
            multiplier = restrictions["max_expense_multiplier"]
            adjusted["max_expense_per_transaction"] *= multiplier
        
        # Force approval if tier requires
        if restrictions["requires_approval"]:
            adjusted["approval_required"] = True
            adjusted["auto_approve_under"] = 0
        
        # Adjust max debt
        tier_max_debt = restrictions["max_debt_allowed"]
        if tier_max_debt is not None:
            if adjusted.get("max_debt_allowed") is None or tier_max_debt < adjusted["max_debt_allowed"]:
                adjusted["max_debt_allowed"] = tier_max_debt
        
        # Add warning message
        adjusted["reliability_warning"] = restrictions["warning_message"]
        adjusted["reliability_tier"] = tier
        
        return adjusted
    
    @classmethod
    def check_can_join_event(
        cls,
        user_id: str,
        event_id: str
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Check if user can join an event based on reliability.
        
        Args:
            user_id: User ID
            event_id: Event ID
            
        Returns:
            Tuple of (can_join, message, required_deposit_multiplier)
        """
        tier = cls.get_user_tier(user_id)
        restrictions = cls.get_tier_restrictions(tier)
        
        # Allow all users to join but with different restrictions
        # Restricted users get a warning but can still join with higher deposit
        multiplier = restrictions["join_deposit_multiplier"]
        message = restrictions["warning_message"]
        
        return True, message, multiplier
    
    @classmethod
    def check_can_create_event(cls, user_id: str) -> Tuple[bool, Optional[str]]:
        """Check if user can create events based on reliability."""
        tier = cls.get_user_tier(user_id)
        restrictions = cls.get_tier_restrictions(tier)
        
        if not restrictions["can_create_events"]:
            return False, f"Event creation is restricted for users with {tier} reliability status."
        
        return True, None
    
    @classmethod
    def record_shortfall(
        cls,
        user_id: str,
        event_id: str,
        expense_id: str,
        amount: float
    ) -> None:
        """Record a shortfall event for reliability tracking."""
        mongo.reliability_events.insert_one({
            "user_id": ObjectId(user_id),
            "event_id": ObjectId(event_id),
            "expense_id": ObjectId(expense_id),
            "type": "shortfall",
            "amount": amount,
            "created_at": datetime.utcnow()
        })
        
        # Update cached score
        cls._update_cached_score(user_id)
    
    @classmethod
    def record_late_settlement(
        cls,
        user_id: str,
        event_id: str,
        settlement_id: str,
        days_late: int
    ) -> None:
        """Record a late settlement for reliability tracking."""
        mongo.reliability_events.insert_one({
            "user_id": ObjectId(user_id),
            "event_id": ObjectId(event_id),
            "settlement_id": ObjectId(settlement_id),
            "type": "late_settlement",
            "days_late": days_late,
            "created_at": datetime.utcnow()
        })
        
        # Mark settlement as late
        mongo.settlements.update_one(
            {"_id": ObjectId(settlement_id)},
            {"$set": {"was_late": True, "days_late": days_late}}
        )
        
        cls._update_cached_score(user_id)
    
    @classmethod
    def _update_cached_score(cls, user_id: str) -> None:
        """Update cached reliability score for quick access."""
        score_data = cls.calculate_reliability_score(user_id)
        
        mongo.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "reliability_score": score_data["score"],
                    "reliability_tier": score_data["tier"],
                    "reliability_updated_at": datetime.utcnow()
                }
            }
        )
    
    @classmethod
    def get_user_reliability_history(
        cls,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get reliability events history for a user."""
        events = list(mongo.reliability_events.find({
            "user_id": ObjectId(user_id)
        }).sort("created_at", -1).limit(limit))
        
        for e in events:
            e["_id"] = str(e["_id"])
            e["user_id"] = str(e["user_id"])
            e["event_id"] = str(e["event_id"])
            if e.get("expense_id"):
                e["expense_id"] = str(e["expense_id"])
            if e.get("settlement_id"):
                e["settlement_id"] = str(e["settlement_id"])
        
        return events
