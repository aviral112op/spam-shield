from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EmailRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50_000, description="Email content to classify")


class BatchEmailRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=100)


class PredictionResponse(BaseModel):
    label: str
    is_spam: bool
    confidence: float


class BatchPredictionResponse(BaseModel):
    predictions: List[PredictionResponse]


class EmlPrediction(BaseModel):
    filename: str
    subject: Optional[str] = None
    prediction: Optional[PredictionResponse] = None
    error: Optional[str] = None


class EmlPredictionResponse(BaseModel):
    results: List[EmlPrediction]


class Credentials(BaseModel):
    email: str = Field(..., max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    # bcrypt only uses the first 72 bytes of a password
    password: str = Field(..., min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    snippet: str
    label: str
    confidence: float
    created_at: datetime
