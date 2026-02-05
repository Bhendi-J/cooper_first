"""
Join Request Service - Join flow with approval.

Responsibilities:
- Handle join requests with rule acceptance
- Validate initial deposits within limits
- Notify creator of join requests
- Handle approval/rejection flow
- Only approved users participate in expenses
"""
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from bson import ObjectId

from app.extensions import db as mongo


class JoinStatus:
    """Join request status constants."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"  # After approval + deposit confirmed


class JoinRequestService:
    """Service for join request and approval flow."""
    
    @classmethod
    def create_join_request(
        cls,
        event_id: str,
        user_id: str,
        deposit_amount: Optional[float] = None,
        accepted_rules: bool = False
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Create a join request for an event.
        
        Args:
            event_id: Event to join
            user_id: User requesting to join
            deposit_amount: Intended deposit amount
            accepted_rules: Whether user accepted event rules
            
        Returns:
            Tuple of (join_request, error_message)
        """
        from .rules_service import RuleEnforcementService
        from .notification_service import NotificationService
        
        # Check event exists and is active
        event = mongo.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            return None, "Event not found"
        
        if event["status"] != "active":
            return None, "Event is not active"
        
        # Check if already a participant
        existing = mongo.participants.find_one({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id)
        })
        
        if existing:
            if existing["status"] == JoinStatus.PENDING:
                return None, "Join request already pending"
            elif existing["status"] in [JoinStatus.APPROVED, JoinStatus.ACTIVE]:
                return None, "Already a participant"
            elif existing["status"] == JoinStatus.REJECTED:
                # Allow re-request after rejection
                mongo.participants.delete_one({"_id": existing["_id"]})
        
        # Get event rules
        rules = RuleEnforcementService.get_event_rules(event_id)
        
        # Check if rules acceptance is required
        if rules and not accepted_rules:
            return None, "You must accept the event rules to join"
        
        # Validate deposit against rules
        if deposit_amount is not None:
            is_valid, error, _ = RuleEnforcementService.validate_deposit(
                event_id, user_id, deposit_amount
            )
            if not is_valid:
                return None, error
        
        # Check if min deposit is required
        min_deposit = rules.get("min_deposit") if rules else None
        if min_deposit and (deposit_amount is None or deposit_amount < min_deposit):
            return None, f"Minimum deposit of ${min_deposit:.2f} is required to join"
        
        # Determine if approval is required
        requires_approval = rules.get("require_join_approval", False) if rules else False
        
        # Create participant record
        participant = {
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id),
            "deposit_amount": 0,
            "intended_deposit": deposit_amount,
            "total_spent": 0,
            "balance": 0,
            "available_contribution": 0,
            "status": JoinStatus.PENDING if requires_approval else JoinStatus.APPROVED,
            "rules_accepted": accepted_rules,
            "rules_accepted_at": datetime.utcnow() if accepted_rules else None,
            "joined_via": "request",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = mongo.participants.insert_one(participant)
        participant["_id"] = str(result.inserted_id)
        participant["event_id"] = str(participant["event_id"])
        participant["user_id"] = str(participant["user_id"])
        
        # Record join request
        mongo.join_requests.insert_one({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id),
            "participant_id": result.inserted_id,
            "intended_deposit": deposit_amount,
            "status": JoinStatus.PENDING if requires_approval else JoinStatus.APPROVED,
            "rules_accepted": accepted_rules,
            "created_at": datetime.utcnow()
        })
        
        # Notify creator
        NotificationService.notify_join_request(
            creator_id=str(event["creator_id"]),
            event_id=event_id,
            event_name=event["name"],
            user_id=user_id,
            requires_approval=requires_approval
        )
        
        return participant, None
    
    @classmethod
    def approve_join_request(
        cls,
        event_id: str,
        user_id: str,
        approver_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Approve a pending join request.
        
        Args:
            event_id: Event ID
            user_id: User to approve
            approver_id: User approving (must be creator)
            
        Returns:
            Tuple of (success, error_message)
        """
        from .notification_service import NotificationService
        
        # Verify approver is creator
        event = mongo.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            return False, "Event not found"
        
        if str(event["creator_id"]) != approver_id:
            return False, "Only the event creator can approve join requests"
        
        # Find pending participant
        participant = mongo.participants.find_one({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id),
            "status": JoinStatus.PENDING
        })
        
        if not participant:
            return False, "No pending join request found"
        
        # Update status
        mongo.participants.update_one(
            {"_id": participant["_id"]},
            {
                "$set": {
                    "status": JoinStatus.APPROVED,
                    "approved_by": ObjectId(approver_id),
                    "approved_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update join request record
        mongo.join_requests.update_one(
            {
                "event_id": ObjectId(event_id),
                "user_id": ObjectId(user_id),
                "status": JoinStatus.PENDING
            },
            {
                "$set": {
                    "status": JoinStatus.APPROVED,
                    "approved_by": ObjectId(approver_id),
                    "approved_at": datetime.utcnow()
                }
            }
        )
        
        # Record activity
        mongo.activities.insert_one({
            "type": "join_approved",
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id),
            "approved_by": ObjectId(approver_id),
            "created_at": datetime.utcnow()
        })
        
        # Notify user
        NotificationService.notify_join_approved(
            user_id=user_id,
            event_id=event_id,
            event_name=event["name"]
        )
        
        return True, None
    
    @classmethod
    def reject_join_request(
        cls,
        event_id: str,
        user_id: str,
        rejector_id: str,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Reject a pending join request.
        
        Args:
            event_id: Event ID
            user_id: User to reject
            rejector_id: User rejecting (must be creator)
            reason: Optional rejection reason
            
        Returns:
            Tuple of (success, error_message)
        """
        from .notification_service import NotificationService
        
        # Verify rejector is creator
        event = mongo.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            return False, "Event not found"
        
        if str(event["creator_id"]) != rejector_id:
            return False, "Only the event creator can reject join requests"
        
        # Find pending participant
        participant = mongo.participants.find_one({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id),
            "status": JoinStatus.PENDING
        })
        
        if not participant:
            return False, "No pending join request found"
        
        # Update status
        mongo.participants.update_one(
            {"_id": participant["_id"]},
            {
                "$set": {
                    "status": JoinStatus.REJECTED,
                    "rejected_by": ObjectId(rejector_id),
                    "rejected_at": datetime.utcnow(),
                    "rejection_reason": reason,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update join request record
        mongo.join_requests.update_one(
            {
                "event_id": ObjectId(event_id),
                "user_id": ObjectId(user_id),
                "status": JoinStatus.PENDING
            },
            {
                "$set": {
                    "status": JoinStatus.REJECTED,
                    "rejected_by": ObjectId(rejector_id),
                    "rejected_at": datetime.utcnow(),
                    "rejection_reason": reason
                }
            }
        )
        
        # Notify user
        NotificationService.notify_join_rejected(
            user_id=user_id,
            event_id=event_id,
            event_name=event["name"],
            reason=reason
        )
        
        return True, None
    
    @classmethod
    def confirm_join_payment(
        cls,
        event_id: str,
        user_id: str,
        amount: float,
        payment_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Confirm join payment and activate participant.
        
        Called after payment webhook confirms the initial deposit.
        
        Args:
            event_id: Event ID
            user_id: User ID
            amount: Confirmed payment amount
            payment_id: Payment reference
            
        Returns:
            Tuple of (success, error_message)
        """
        from .pool_service import PoolService
        
        # Find participant
        participant = mongo.participants.find_one({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id),
            "status": {"$in": [JoinStatus.APPROVED, JoinStatus.PENDING]}
        })
        
        if not participant:
            return False, "Participant not found or not in approved state"
        
        # Confirm the deposit
        success, message = PoolService.confirm_deposit(
            event_id=event_id,
            user_id=user_id,
            amount=amount,
            payment_id=payment_id
        )
        
        if not success:
            return False, message
        
        # Activate participant
        mongo.participants.update_one(
            {"_id": participant["_id"]},
            {
                "$set": {
                    "status": JoinStatus.ACTIVE,
                    "activated_at": datetime.utcnow(),
                    "join_payment_id": payment_id,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Record activity
        mongo.activities.insert_one({
            "type": "participant_activated",
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id),
            "amount": amount,
            "payment_id": payment_id,
            "created_at": datetime.utcnow()
        })
        
        return True, None
    
    @classmethod
    def get_pending_requests(cls, event_id: str) -> List[Dict]:
        """Get all pending join requests for an event."""
        requests = list(mongo.join_requests.find({
            "event_id": ObjectId(event_id),
            "status": JoinStatus.PENDING
        }).sort("created_at", 1))
        
        for r in requests:
            r["_id"] = str(r["_id"])
            r["event_id"] = str(r["event_id"])
            r["user_id"] = str(r["user_id"])
            
            # Get user info
            user = mongo.users.find_one({"_id": ObjectId(r["user_id"])})
            if user:
                r["user_name"] = user.get("name", "Unknown")
                r["user_email"] = user.get("email", "")
        
        return requests
    
    @classmethod
    def is_authorized_participant(cls, event_id: str, user_id: str) -> bool:
        """Check if user is an authorized (approved/active) participant."""
        participant = mongo.participants.find_one({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id),
            "status": {"$in": [JoinStatus.APPROVED, JoinStatus.ACTIVE, "active"]}
        })
        return participant is not None
    
    @classmethod
    def accept_rules(
        cls,
        event_id: str,
        user_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Record user's acceptance of event rules.
        
        Args:
            event_id: Event ID
            user_id: User accepting rules
            
        Returns:
            Tuple of (success, error_message)
        """
        participant = mongo.participants.find_one({
            "event_id": ObjectId(event_id),
            "user_id": ObjectId(user_id)
        })
        
        if not participant:
            return False, "Participant not found"
        
        mongo.participants.update_one(
            {"_id": participant["_id"]},
            {
                "$set": {
                    "rules_accepted": True,
                    "rules_accepted_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return True, None
