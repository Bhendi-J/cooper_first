"""
Notification Service - Notification triggers for all events.

Responsibilities:
- Notify on payment confirmations
- Notify on expense approvals/rejections
- Notify on rule violations
- Notify on debt creation and reminders
- Notify creators on join requests
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId

from app.extensions import db as mongo


class NotificationType:
    """Notification type constants."""
    # Payment notifications
    PAYMENT_CONFIRMED = "payment_confirmed"
    PAYMENT_FAILED = "payment_failed"
    
    # Expense notifications
    EXPENSE_CREATED = "expense_created"
    EXPENSE_PENDING_APPROVAL = "expense_pending_approval"
    EXPENSE_APPROVED = "expense_approved"
    EXPENSE_REJECTED = "expense_rejected"
    
    # Join notifications
    JOIN_REQUEST = "join_request"
    JOIN_APPROVED = "join_approved"
    JOIN_REJECTED = "join_rejected"
    
    # Rule notifications
    RULE_VIOLATION = "rule_violation"
    RULE_WARNING = "rule_warning"
    
    # Debt notifications
    DEBT_CREATED = "debt_created"
    DEBT_REMINDER = "debt_reminder"
    DEBT_SETTLED = "debt_settled"
    
    # Event notifications
    EVENT_SETTLED = "event_settled"
    DEPOSIT_CONFIRMED = "deposit_confirmed"


class NotificationService:
    """Service for managing notifications."""
    
    @classmethod
    def create_notification(
        cls,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict] = None,
        priority: str = "normal"
    ) -> str:
        """
        Create a notification for a user.
        
        Args:
            user_id: User to notify
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional data (event_id, expense_id, etc.)
            priority: Priority level (low, normal, high, urgent)
            
        Returns:
            Notification ID
        """
        notification = {
            "user_id": ObjectId(user_id),
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "priority": priority,
            "read": False,
            "created_at": datetime.utcnow()
        }
        
        result = mongo.notifications.insert_one(notification)
        
        # Also push to real-time queue if available
        cls._push_realtime(user_id, notification)
        
        return str(result.inserted_id)
    
    @classmethod
    def _push_realtime(cls, user_id: str, notification: Dict) -> None:
        """Push notification to real-time channel (WebSocket/SSE)."""
        # This would integrate with a real-time service like Socket.IO or Redis pub/sub
        # For now, we store in a queue collection that can be polled
        notification_copy = notification.copy()
        notification_copy["user_id"] = str(notification_copy["user_id"])
        
        mongo.notification_queue.insert_one({
            "user_id": user_id,
            "notification": notification_copy,
            "delivered": False,
            "created_at": datetime.utcnow()
        })
    
    # ==================== PAYMENT NOTIFICATIONS ====================
    
    @classmethod
    def notify_payment_confirmed(
        cls,
        user_id: str,
        amount: float,
        purpose: str,
        payment_id: Optional[str] = None
    ) -> str:
        """Notify user that payment was confirmed."""
        return cls.create_notification(
            user_id=user_id,
            notification_type=NotificationType.PAYMENT_CONFIRMED,
            title="Payment Confirmed",
            message=f"Your {purpose.lower()} of ${amount:.2f} has been confirmed.",
            data={"amount": amount, "purpose": purpose, "payment_id": payment_id}
        )
    
    @classmethod
    def notify_payment_failed(
        cls,
        user_id: str,
        amount: float,
        purpose: str,
        error: Optional[str] = None
    ) -> str:
        """Notify user that payment failed."""
        return cls.create_notification(
            user_id=user_id,
            notification_type=NotificationType.PAYMENT_FAILED,
            title="Payment Failed",
            message=f"Your {purpose.lower()} of ${amount:.2f} failed. {error or 'Please try again.'}",
            data={"amount": amount, "purpose": purpose, "error": error},
            priority="high"
        )
    
    # ==================== EXPENSE NOTIFICATIONS ====================
    
    @classmethod
    def notify_expense_pending_approval(
        cls,
        creator_id: str,
        event_id: str,
        event_name: str,
        expense_id: str,
        amount: float,
        reason: Optional[str] = None
    ) -> str:
        """Notify creator that an expense needs approval."""
        message = f"An expense of ${amount:.2f} in {event_name} requires your approval."
        if reason:
            message += f" Reason: {reason}"
        
        return cls.create_notification(
            user_id=creator_id,
            notification_type=NotificationType.EXPENSE_PENDING_APPROVAL,
            title="Expense Needs Approval",
            message=message,
            data={
                "event_id": event_id,
                "event_name": event_name,
                "expense_id": expense_id,
                "amount": amount,
                "reason": reason
            },
            priority="high"
        )
    
    @classmethod
    def notify_expense_approved(
        cls,
        user_id: str,
        expense_id: str,
        amount: float,
        event_name: str
    ) -> str:
        """Notify user that their expense was approved."""
        return cls.create_notification(
            user_id=user_id,
            notification_type=NotificationType.EXPENSE_APPROVED,
            title="Expense Approved",
            message=f"Your expense of ${amount:.2f} in {event_name} has been approved.",
            data={
                "expense_id": expense_id,
                "amount": amount,
                "event_name": event_name
            }
        )
    
    @classmethod
    def notify_expense_rejected(
        cls,
        user_id: str,
        expense_id: str,
        amount: float,
        event_name: str,
        reason: Optional[str] = None
    ) -> str:
        """Notify user that their expense was rejected."""
        message = f"Your expense of ${amount:.2f} in {event_name} was rejected."
        if reason:
            message += f" Reason: {reason}"
        
        return cls.create_notification(
            user_id=user_id,
            notification_type=NotificationType.EXPENSE_REJECTED,
            title="Expense Rejected",
            message=message,
            data={
                "expense_id": expense_id,
                "amount": amount,
                "event_name": event_name,
                "reason": reason
            },
            priority="high"
        )
    
    # ==================== JOIN NOTIFICATIONS ====================
    
    @classmethod
    def notify_join_request(
        cls,
        creator_id: str,
        event_id: str,
        event_name: str,
        user_id: str,
        requires_approval: bool = True
    ) -> str:
        """Notify creator of a join request."""
        user = mongo.users.find_one({"_id": ObjectId(user_id)})
        user_name = user.get("name", "Someone") if user else "Someone"
        
        if requires_approval:
            title = "Join Request Pending"
            message = f"{user_name} wants to join {event_name}. Approval required."
            priority = "high"
        else:
            title = "New Participant Joined"
            message = f"{user_name} has joined {event_name}."
            priority = "normal"
        
        return cls.create_notification(
            user_id=creator_id,
            notification_type=NotificationType.JOIN_REQUEST,
            title=title,
            message=message,
            data={
                "event_id": event_id,
                "event_name": event_name,
                "requester_id": user_id,
                "requester_name": user_name,
                "requires_approval": requires_approval
            },
            priority=priority
        )
    
    @classmethod
    def notify_join_approved(
        cls,
        user_id: str,
        event_id: str,
        event_name: str
    ) -> str:
        """Notify user their join request was approved."""
        return cls.create_notification(
            user_id=user_id,
            notification_type=NotificationType.JOIN_APPROVED,
            title="Join Request Approved",
            message=f"You've been approved to join {event_name}!",
            data={"event_id": event_id, "event_name": event_name}
        )
    
    @classmethod
    def notify_join_rejected(
        cls,
        user_id: str,
        event_id: str,
        event_name: str,
        reason: Optional[str] = None
    ) -> str:
        """Notify user their join request was rejected."""
        message = f"Your request to join {event_name} was not approved."
        if reason:
            message += f" Reason: {reason}"
        
        return cls.create_notification(
            user_id=user_id,
            notification_type=NotificationType.JOIN_REJECTED,
            title="Join Request Declined",
            message=message,
            data={
                "event_id": event_id,
                "event_name": event_name,
                "reason": reason
            }
        )
    
    # ==================== RULE NOTIFICATIONS ====================
    
    @classmethod
    def notify_rule_violation(
        cls,
        user_id: str,
        event_id: str,
        event_name: str,
        violation_type: str,
        details: str,
        notify_creator: bool = True
    ) -> List[str]:
        """Notify about a rule violation."""
        notification_ids = []
        
        # Notify user
        notification_ids.append(cls.create_notification(
            user_id=user_id,
            notification_type=NotificationType.RULE_VIOLATION,
            title="Rule Violation",
            message=f"Your action in {event_name} violated a rule: {details}",
            data={
                "event_id": event_id,
                "event_name": event_name,
                "violation_type": violation_type,
                "details": details
            },
            priority="high"
        ))
        
        # Notify creator
        if notify_creator:
            event = mongo.events.find_one({"_id": ObjectId(event_id)})
            if event and str(event["creator_id"]) != user_id:
                user = mongo.users.find_one({"_id": ObjectId(user_id)})
                user_name = user.get("name", "A participant") if user else "A participant"
                
                notification_ids.append(cls.create_notification(
                    user_id=str(event["creator_id"]),
                    notification_type=NotificationType.RULE_VIOLATION,
                    title="Rule Violation in Your Event",
                    message=f"{user_name} violated a rule in {event_name}: {details}",
                    data={
                        "event_id": event_id,
                        "event_name": event_name,
                        "violator_id": user_id,
                        "violator_name": user_name,
                        "violation_type": violation_type,
                        "details": details
                    },
                    priority="high"
                ))
        
        return notification_ids
    
    # ==================== DEBT NOTIFICATIONS ====================
    
    @classmethod
    def notify_debt_created(
        cls,
        user_id: str,
        amount: float,
        event_id: str,
        expense_id: str
    ) -> str:
        """Notify user that a debt was created."""
        event = mongo.events.find_one({"_id": ObjectId(event_id)})
        event_name = event.get("name", "an event") if event else "an event"
        
        return cls.create_notification(
            user_id=user_id,
            notification_type=NotificationType.DEBT_CREATED,
            title="Outstanding Balance",
            message=f"You have an outstanding balance of ${amount:.2f} for {event_name}. Please settle when possible.",
            data={
                "amount": amount,
                "event_id": event_id,
                "event_name": event_name,
                "expense_id": expense_id
            },
            priority="high"
        )
    
    @classmethod
    def notify_debt_reminder(
        cls,
        user_id: str,
        amount: float,
        event_id: str,
        days_overdue: int
    ) -> str:
        """Send a debt reminder notification."""
        event = mongo.events.find_one({"_id": ObjectId(event_id)})
        event_name = event.get("name", "an event") if event else "an event"
        
        if days_overdue > 14:
            priority = "urgent"
            title = "Urgent: Outstanding Balance"
        else:
            priority = "high"
            title = "Reminder: Outstanding Balance"
        
        return cls.create_notification(
            user_id=user_id,
            notification_type=NotificationType.DEBT_REMINDER,
            title=title,
            message=f"You have ${amount:.2f} outstanding for {event_name} ({days_overdue} days overdue). Please settle soon.",
            data={
                "amount": amount,
                "event_id": event_id,
                "event_name": event_name,
                "days_overdue": days_overdue
            },
            priority=priority
        )
    
    @classmethod
    def notify_debt_settled(
        cls,
        user_id: str,
        amount: float,
        event_id: str
    ) -> str:
        """Notify user that their debt was settled."""
        event = mongo.events.find_one({"_id": ObjectId(event_id)})
        event_name = event.get("name", "an event") if event else "an event"
        
        return cls.create_notification(
            user_id=user_id,
            notification_type=NotificationType.DEBT_SETTLED,
            title="Debt Settled",
            message=f"Your outstanding balance of ${amount:.2f} for {event_name} has been settled.",
            data={
                "amount": amount,
                "event_id": event_id,
                "event_name": event_name
            }
        )
    
    # ==================== NOTIFICATION MANAGEMENT ====================
    
    @classmethod
    def get_user_notifications(
        cls,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict]:
        """Get notifications for a user."""
        query = {"user_id": ObjectId(user_id)}
        
        if unread_only:
            query["read"] = False
        
        notifications = list(
            mongo.notifications.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        
        for n in notifications:
            n["_id"] = str(n["_id"])
            n["user_id"] = str(n["user_id"])
        
        return notifications
    
    @classmethod
    def mark_as_read(cls, notification_id: str) -> bool:
        """Mark a notification as read."""
        result = mongo.notifications.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"read": True, "read_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    @classmethod
    def mark_all_as_read(cls, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        result = mongo.notifications.update_many(
            {"user_id": ObjectId(user_id), "read": False},
            {"$set": {"read": True, "read_at": datetime.utcnow()}}
        )
        return result.modified_count
    
    @classmethod
    def get_unread_count(cls, user_id: str) -> int:
        """Get count of unread notifications."""
        return mongo.notifications.count_documents({
            "user_id": ObjectId(user_id),
            "read": False
        })
