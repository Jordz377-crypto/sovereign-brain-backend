from pydantic import BaseModel, Field
from typing import Optional


class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class LeadCapture(BaseModel):
    source: str = Field(pattern=r"^(audit|chat_handoff|contact)$")
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    hours_manual: Optional[float] = None
    pain_points: Optional[str] = None
    payload: Optional[dict] = None


class HandoffRequest(BaseModel):
    transcript: list[ChatMessage] = Field(default_factory=list)
    contact_info: Optional[dict] = None


class TradingUpdate(BaseModel):
    symbol: str
    position_size: float
    entry_price: float
    current_price: float
    profit_loss: float
    profit_loss_pct: float
    timestamp: Optional[str] = None
    magic_number: Optional[int] = None
    comment: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    groq_available: bool
    supabase_connected: bool
