from enum import Enum

class EventStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ParticipantStatus(str, Enum):
    INVITED = "invited"
    ACTIVE = "active"
    LEFT = "left"

class ExpenseType(str, Enum):
    EQUAL_SPLIT = "equal_split"
    PERCENTAGE = "percentage"
    CUSTOM = "custom"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


