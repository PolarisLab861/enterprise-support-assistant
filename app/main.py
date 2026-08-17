from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import Base, engine, get_db
from .dify import DifyWorkflowClient
from .models import Feedback, Ticket, TicketStatus, WorkflowRun
from .schemas import FeedbackRequest, QuestionRequest, QuestionResponse, StatsResponse, TicketResponse, TicketUpdate

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


def ticket_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse.model_validate(ticket, from_attributes=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "environment": settings.environment, "mock_ai": settings.mock_ai}


@app.post("/api/v1/questions", response_model=QuestionResponse)
def ask_question(payload: QuestionRequest, db: Session = Depends(get_db)) -> QuestionResponse:
    request_id = f"req_{uuid4().hex[:12]}"
    started = time.perf_counter()
    try:
        result = DifyWorkflowClient(settings).run(payload.message, payload.user_id, payload.conversation_id)
        ticket_id = None
        if result.need_human:
            ticket = Ticket(
                user_id=payload.user_id,
                user_message=payload.message,
                intent=result.intent,
                priority=result.priority,
                ai_reply=result.answer,
                sources=result.sources,
            )
            db.add(ticket)
            db.flush()
            ticket_id = ticket.id
        elapsed = time.perf_counter() - started
        db.add(WorkflowRun(request_id=request_id, status="succeeded", elapsed_time=elapsed, total_tokens=result.total_tokens))
        db.commit()
        return QuestionResponse(
            request_id=request_id,
            answer=result.answer,
            intent=result.intent,
            priority=result.priority,
            confidence=result.confidence,
            sources=result.sources,
            need_human=result.need_human,
            reason=result.reason,
            ticket_id=ticket_id,
        )
    except Exception as exc:
        db.add(WorkflowRun(request_id=request_id, status="failed", elapsed_time=time.perf_counter() - started, error=str(exc)))
        db.commit()
        raise HTTPException(status_code=502, detail="AI 工作流暂时不可用，请稍后重试或联系人工客服") from exc


@app.get("/api/v1/tickets", response_model=list[TicketResponse])
def list_tickets(status: Optional[str] = Query(default=None), db: Session = Depends(get_db)) -> List[TicketResponse]:
    query = select(Ticket).order_by(Ticket.created_at.desc())
    if status:
        query = query.where(Ticket.status == status)
    return [ticket_response(ticket) for ticket in db.scalars(query).all()]


@app.get("/api/v1/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> TicketResponse:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ticket_response(ticket)


@app.patch("/api/v1/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: str, payload: TicketUpdate, db: Session = Depends(get_db)) -> TicketResponse:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if payload.status and payload.status not in {item.value for item in TicketStatus}:
        raise HTTPException(status_code=400, detail="不支持的工单状态")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(ticket, field, value)
    db.commit()
    db.refresh(ticket)
    return ticket_response(ticket)


@app.post("/api/v1/feedbacks")
def create_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)) -> dict:
    if payload.ticket_id and not db.get(Ticket, payload.ticket_id):
        raise HTTPException(status_code=404, detail="关联工单不存在")
    feedback = Feedback(**payload.model_dump())
    db.add(feedback)
    db.commit()
    return {"id": feedback.id, "status": "created"}


@app.get("/api/v1/stats", response_model=StatsResponse)
def stats(db: Session = Depends(get_db)) -> StatsResponse:
    total = db.scalar(select(func.count(Ticket.id))) or 0
    open_count = db.scalar(select(func.count(Ticket.id)).where(Ticket.status.in_(["open", "in_progress", "reopened"]))) or 0
    runs = list(db.scalars(select(WorkflowRun)).all())
    average = sum(run.elapsed_time for run in runs) / len(runs) if runs else 0
    human_handoff_rate = total / len(runs) if runs else 0
    return StatsResponse(total_tickets=total, open_tickets=open_count, human_handoff_rate=round(human_handoff_rate, 4), average_response_seconds=round(average, 4))


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent.parent / "web" / "index.html")
