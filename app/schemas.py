from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=2, max_length=4000)
    conversation_id: Optional[str] = Field(default=None, max_length=128)


class Source(BaseModel):
    title: str
    section: Optional[str] = None
    page: Optional[int] = None
    score: Optional[float] = None


class QuestionResponse(BaseModel):
    request_id: str
    answer: str
    intent: str
    priority: str
    confidence: float
    sources: List[Source] = []
    need_human: bool
    reason: Optional[str] = None
    ticket_id: Optional[str] = None


class TicketResponse(BaseModel):
    id: str
    user_id: str
    user_message: str
    intent: str
    priority: str
    status: str
    ai_reply: Optional[str]
    sources: Optional[List[dict[str, Any]]]
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None


class FeedbackRequest(BaseModel):
    ticket_id: Optional[str] = None
    score: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class StatsResponse(BaseModel):
    total_tickets: int
    open_tickets: int
    human_handoff_rate: float
    average_response_seconds: float
