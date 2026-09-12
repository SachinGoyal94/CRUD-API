from enum import Enum
from pydantic import BaseModel, Field


class CategoryEnum(str, Enum):
    BILLING = "billing"
    BUG = "bug"
    FEATURE = "feature"
    OTHER = "other"


class UrgencyEnum(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TriageRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Support or task message text to triage (1-2000 characters)"
    )


class TriageResponse(BaseModel):
    category: CategoryEnum = Field(..., description="Classified category")
    urgency: UrgencyEnum = Field(..., description="Urgency level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reason: str = Field(..., description="One short sentence explaining classification")
