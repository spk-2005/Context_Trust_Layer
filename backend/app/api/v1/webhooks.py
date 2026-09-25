import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.webhook import WebhookDispatchLog, WebhookSubscription
from app.schemas.webhook import (
    WebhookCreateRequest,
    WebhookDispatchLogResponse,
    WebhookResponse,
    WebhookTestResponse,
    WebhookUpdateRequest,
)
from app.services.webhook_service import test_webhook_delivery

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all configured webhook endpoints for the specified organization."""
    stmt = (
        select(WebhookSubscription)
        .where(WebhookSubscription.organization_id == organization_id)
        .order_by(WebhookSubscription.created_at.desc())
    )
    res = await db.execute(stmt)
    records = res.scalars().all()
    return records


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    req: WebhookCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new incident notification webhook (Slack, PagerDuty, Teams, Generic)."""
    wh = WebhookSubscription(
        organization_id=req.organization_id,
        name=req.name.strip(),
        url=req.url.strip(),
        channel_type=req.channel_type.lower(),
        min_liability_threshold_usd=req.min_liability_threshold_usd,
        trigger_on_block=req.trigger_on_block,
        trigger_on_review=req.trigger_on_review,
        secret_token=req.secret_token,
        is_active=True,
    )
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: uuid.UUID,
    req: WebhookUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update webhook properties, active status, or notification thresholds."""
    stmt = select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
    res = await db.execute(stmt)
    wh = res.scalars().first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")

    if req.name is not None:
        wh.name = req.name.strip()
    if req.url is not None:
        wh.url = req.url.strip()
    if req.channel_type is not None:
        wh.channel_type = req.channel_type.lower()
    if req.min_liability_threshold_usd is not None:
        wh.min_liability_threshold_usd = req.min_liability_threshold_usd
    if req.trigger_on_block is not None:
        wh.trigger_on_block = req.trigger_on_block
    if req.trigger_on_review is not None:
        wh.trigger_on_review = req.trigger_on_review
    if req.is_active is not None:
        wh.is_active = req.is_active
    if req.secret_token is not None:
        wh.secret_token = req.secret_token

    await db.commit()
    await db.refresh(wh)
    return wh


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a webhook subscription."""
    stmt = select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
    res = await db.execute(stmt)
    wh = res.scalars().first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")

    await db.delete(wh)
    await db.commit()
    return None


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def trigger_test_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Send an immediate test alert to verify the webhook receiver's configuration."""
    stmt = select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
    res = await db.execute(stmt)
    wh = res.scalars().first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")

    success, code, body, payload = await test_webhook_delivery(wh, db)
    return WebhookTestResponse(
        success=success,
        status_code=code,
        message=f"Test alert delivered with status {code}" if success else f"Delivery failed: {body}",
        delivered_payload=payload,
    )


@router.get("/logs", response_model=List[WebhookDispatchLogResponse])
async def list_dispatch_logs(
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Fetch recent incident notification dispatch history for compliance auditing."""
    stmt = (
        select(WebhookDispatchLog)
        .where(WebhookDispatchLog.organization_id == organization_id)
        .order_by(WebhookDispatchLog.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()
    return records
