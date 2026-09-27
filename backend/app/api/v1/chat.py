import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    organization_id: uuid.UUID
    user_id: uuid.UUID | None = None
    user_name: str = "Anonymous"
    user_role: str = "developer"
    title: str = "New Conversation"
    workspace_id: str | None = "all"
    domain: str | None = "global"


class SendMessageRequest(BaseModel):
    organization_id: uuid.UUID
    content: str = Field(..., min_length=1)
    user_id: uuid.UUID | None = None
    user_name: str = "User"
    user_role: str = "developer"
    workspace_id: str | None = None
    domain: str | None = None


@router.get("/sessions")
async def list_chat_sessions(
    organization_id: uuid.UUID = Query(...),
    user_id: uuid.UUID | None = Query(None),
    workspace_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List chat sessions for a specific organization, user/persona, and departmental workspace."""
    service = ChatService(db)
    return await service.list_sessions(organization_id, user_id, workspace_id, limit)


@router.post("/sessions")
async def create_chat_session(
    req: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversational session tagged with active departmental workspace."""
    service = ChatService(db)
    return await service.create_session(
        organization_id=req.organization_id,
        user_id=req.user_id,
        user_name=req.user_name,
        user_role=req.user_role,
        title=req.title,
        workspace_id=req.workspace_id,
        domain=req.domain,
    )


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get conversation details with complete message history."""
    service = ChatService(db)
    session_data = await service.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session_data


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation session and all its messages."""
    service = ChatService(db)
    success = await service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"status": "deleted", "session_id": str(session_id)}


@router.post("/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Post a user message, run context trust retrieval, and generate grounded assistant response."""
    service = ChatService(db)
    # Ensure session exists
    session_data = await service.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Chat session not found")

    result = await service.process_user_message(
        session_id=session_id,
        organization_id=req.organization_id,
        content=req.content,
        user_id=req.user_id,
        user_name=req.user_name,
        user_role=req.user_role,
        workspace_id=req.workspace_id,
        domain=req.domain,
    )
    return result
