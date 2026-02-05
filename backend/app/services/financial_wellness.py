"""
Financial Wellness Service - A gentle, supportive approach to financial tracking.

This service focuses on empowerment rather than restriction. It provides:
- Spending insights without judgment
- Helpful suggestions framed positively  
- Private, personalized financial health metrics
- Encouraging reminders that respect user dignity
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from bson import ObjectId
from flask import current_app


class FinancialWellnessService:
    """
    A supportive financial wellness companion.
    
    Design Philosophy:
    - No shaming or stigmatizing language
    - Frame everything as opportunities, not problems
    - Private metrics visible only to the user
    - Celebrate positive actions
    - Gentle, optional reminders
    """
    
    def __init__(self, mongo_db):
        self.db = mongo_db

    def get_user_wellness_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a holistic financial wellness summary for the user.
        Returns encouraging insights, not judgmental metrics.
        """
        user_oid = ObjectId(user_id)
        
        # Get recent spending patterns (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Get expenses where user paid
        recent_expenses = list(self.db.expenses.find({
            "paid_by": user_oid,
            "created_at": {"$gte": thirty_days_ago}
        }))
        
        # Get pending debts (what user owes)
        pending_debts = list(self.db.participants.find({
            "user_id": user_oid,
            "status": {"$ne": "settled"}
        }))
        
        # Calculate totals
        total_spent = sum(exp.get("amount", 0) for exp in recent_expenses)
        total_pending = sum(debt.get("share", 0) for debt in pending_debts if debt.get("share", 0) > 0)
        
        # Get recent payments made (positive actions)
        recent_payments = list(self.db.payments.find({
            "from_user": user_oid,
            "status": "completed",
            "created_at": {"$gte": thirty_days_ago}
        }))
        total_payments_made = sum(p.get("amount", 0) for p in recent_payments)
        
        # Calculate wellness score (0-100) - focuses on positive behaviors
        wellness_score = self._calculate_wellness_score(
            recent_expenses, pending_debts, recent_payments
        )
        
        # Generate encouraging insights
        insights = self._generate_insights(
            total_spent, total_pending, total_payments_made, len(recent_expenses)
        )
        
        # Category breakdown with friendly descriptions
        spending_by_category = self._get_spending_breakdown(recent_expenses)
        
        return {
            "wellness_score": wellness_score,
            "wellness_status": self._get_wellness_status(wellness_score),
            "spending_summary": {
                "last_30_days": round(total_spent, 2),
                "transaction_count": len(recent_expenses),
                "average_transaction": round(total_spent / max(len(recent_expenses), 1), 2)
            },
            "pending_summary": {
                "total_pending": round(total_pending, 2),
                "pending_count": len([d for d in pending_debts if d.get("share", 0) > 0]),
                "message": self._get_pending_message(total_pending, len(pending_debts))
            },
            "positive_actions": {
                "payments_made": round(total_payments_made, 2),
                "payments_count": len(recent_payments),
                "message": self._get_positive_message(len(recent_payments))
            },
            "spending_breakdown": spending_by_category,
            "insights": insights,
            "encouragement": self._get_encouragement(wellness_score)
        }

    def _calculate_wellness_score(
        self, 
        expenses: List[Dict], 
        debts: List[Dict], 
        payments: List[Dict]
    ) -> int:
        """
        Calculate a supportive wellness score (0-100).
        Higher scores indicate good financial habits.
        
        Scoring factors:
        - Settling debts on time (positive)
        - Making regular payments (positive)
        - Participating in group activities (positive)
        - Large pending amounts (slight reduction, not punitive)
        """
        base_score = 70  # Everyone starts with a good score
        
        # Positive: Making payments
        if len(payments) > 0:
            base_score += min(15, len(payments) * 3)  # Up to +15
        
        # Positive: Participating in group expenses (social engagement)
        if len(expenses) > 0:
            base_score += min(10, len(expenses) * 1)  # Up to +10
        
        # Slight adjustment for pending debts (not punitive)
        pending_amount = sum(d.get("share", 0) for d in debts if d.get("share", 0) > 0)
        if pending_amount > 1000:
            base_score -= 5  # Small gentle reminder
        elif pending_amount > 5000:
            base_score -= 10
        
        # Keep score between 30-100 (never too low - everyone deserves dignity)
        return max(30, min(100, base_score))

    def _get_wellness_status(self, score: int) -> Dict[str, str]:
        """Get a friendly wellness status based on score."""
        if score >= 85:
            return {
                "label": "Thriving",
                "emoji": "🌟",
                "color": "green",
                "description": "You're doing amazing! Your financial habits are excellent."
            }
        elif score >= 70:
            return {
                "label": "Doing Well",
                "emoji": "✨",
                "color": "blue",
                "description": "You're on track! Keep up the good work."
            }
        elif score >= 50:
            return {
                "label": "Growing",
                "emoji": "🌱",
                "color": "yellow",
                "description": "You're making progress! Small steps lead to big changes."
            }
        else:
            return {
                "label": "Building Momentum",
                "emoji": "💪",
                "color": "orange",
                "description": "Every journey starts somewhere. You've got this!"
            }

    def _generate_insights(
        self, 
        total_spent: float, 
        total_pending: float, 
        payments_made: float,
        transaction_count: int
    ) -> List[Dict[str, str]]:
        """Generate helpful, non-judgmental insights."""
        insights = []
        
        # Spending insight
        if transaction_count > 0:
            avg_transaction = total_spent / transaction_count
            if avg_transaction < 500:
                insights.append({
                    "type": "positive",
                    "icon": "💡",
                    "message": "Your average transaction size is modest - great for staying mindful!"
                })
            else:
                insights.append({
                    "type": "neutral",
                    "icon": "📊",
                    "message": f"Your average expense is ₹{avg_transaction:.0f}. Want to see a breakdown by category?"
                })
        
        # Pending insight
        if total_pending > 0:
            insights.append({
                "type": "info",
                "icon": "📝",
                "message": f"You have ₹{total_pending:.0f} in pending settlements. No rush - settle when convenient!"
            })
        elif payments_made > 0:
            insights.append({
                "type": "positive",
                "icon": "🎉",
                "message": "All caught up! No pending settlements at the moment."
            })
        
        # Activity insight
        if transaction_count == 0:
            insights.append({
                "type": "info",
                "icon": "👋",
                "message": "No group expenses this month. Join or create an event to split costs with friends!"
            })
        elif transaction_count >= 10:
            insights.append({
                "type": "positive",
                "icon": "🎊",
                "message": f"Active month! You've participated in {transaction_count} group expenses."
            })
        
        return insights

    def _get_spending_breakdown(self, expenses: List[Dict]) -> List[Dict[str, Any]]:
        """Get spending breakdown by category with friendly labels."""
        category_totals = {}
        for exp in expenses:
            category = exp.get("category", "other")
            amount = exp.get("amount", 0)
            category_totals[category] = category_totals.get(category, 0) + amount
        
        category_emoji = {
            "food": "🍕",
            "transport": "🚗",
            "entertainment": "🎬",
            "shopping": "🛍️",
            "utilities": "💡",
            "health": "💊",
            "travel": "✈️",
            "other": "📦"
        }
        
        breakdown = []
        total = sum(category_totals.values())
        for category, amount in sorted(category_totals.items(), key=lambda x: -x[1]):
            percentage = (amount / total * 100) if total > 0 else 0
            breakdown.append({
                "category": category,
                "emoji": category_emoji.get(category, "📦"),
                "amount": round(amount, 2),
                "percentage": round(percentage, 1)
            })
        
        return breakdown

    def _get_pending_message(self, total: float, count: int) -> str:
        """Get a friendly message about pending amounts."""
        if total == 0:
            return "All clear! No pending settlements. 🎉"
        elif total < 500:
            return f"Just ₹{total:.0f} pending - settle anytime that works for you."
        elif total < 2000:
            return f"₹{total:.0f} pending across {count} items. Take your time!"
        else:
            return f"₹{total:.0f} pending. Consider settling a few when convenient."

    def _get_positive_message(self, payment_count: int) -> str:
        """Generate an encouraging message about payments made."""
        if payment_count == 0:
            return "Ready to settle up? It's easy and friends appreciate it!"
        elif payment_count < 3:
            return f"Great job making {payment_count} payment(s) this month!"
        else:
            return f"Amazing! You've made {payment_count} payments. You're a great group member! 🌟"

    def _get_encouragement(self, score: int) -> str:
        """Get a personalized encouragement message."""
        messages = {
            90: "You're absolutely crushing it! Your financial discipline is inspiring. 🏆",
            80: "Wonderful habits! You're setting yourself up for success. ⭐",
            70: "You're doing really well! Keep that momentum going. 🚀",
            60: "Good progress! Every positive choice adds up. 💪",
            50: "You're on the right path. Celebrate the small wins! 🌟",
            40: "Building good habits takes time. You're doing great by being here! 🌱",
            30: "Remember: where you are today doesn't define your tomorrow. Keep going! 💫"
        }
        
        for threshold, message in sorted(messages.items(), reverse=True):
            if score >= threshold:
                return message
        return messages[30]

    def get_gentle_reminders(self, user_id: str, max_reminders: int = 3) -> List[Dict[str, Any]]:
        """
        Get gentle, non-intrusive reminders for the user.
        These are ALWAYS optional and framed positively.
        """
        user_oid = ObjectId(user_id)
        reminders = []
        
        # Check for old pending debts (gentle nudge, not demand)
        week_ago = datetime.utcnow() - timedelta(days=7)
        old_debts = list(self.db.participants.find({
            "user_id": user_oid,
            "status": {"$ne": "settled"},
            "created_at": {"$lt": week_ago}
        }).limit(3))
        
        for debt in old_debts:
            if debt.get("share", 0) > 0:
                event = self.db.events.find_one({"_id": debt.get("event_id")})
                event_name = event.get("name", "an event") if event else "an event"
                reminders.append({
                    "type": "settlement",
                    "priority": "low",  # Never "urgent" or "high" - no pressure
                    "icon": "💰",
                    "title": "Settlement Available",
                    "message": f"Ready to settle ₹{debt.get('share', 0):.0f} for {event_name}? No rush!",
                    "action": "settle",
                    "event_id": str(debt.get("event_id")),
                    "dismissible": True
                })
                if len(reminders) >= max_reminders:
                    break
        
        return reminders

    def record_positive_action(self, user_id: str, action_type: str, details: Dict = None):
        """
        Record a positive financial action for encouragement tracking.
        Used to celebrate user achievements, not for scoring negatively.
        """
        self.db.wellness_actions.insert_one({
            "user_id": ObjectId(user_id),
            "action_type": action_type,  # "payment_made", "expense_settled", "on_time_payment"
            "details": details or {},
            "created_at": datetime.utcnow()
        })


# Singleton instance
_wellness_service = None

def get_wellness_service(mongo_db=None) -> FinancialWellnessService:
    """Get or create the singleton wellness service instance."""
    global _wellness_service
    if _wellness_service is None:
        if mongo_db is None:
            from app.extensions import mongo
            mongo_db = mongo.db
        _wellness_service = FinancialWellnessService(mongo_db)
    return _wellness_service
