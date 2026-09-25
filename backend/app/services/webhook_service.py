import hashlib
import hmac
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models.webhook import WebhookDispatchLog, WebhookSubscription
from app.schemas.decision import DecisionEvaluateRequest, DecisionEvaluateResponse

logger = logging.getLogger(__name__)


def compute_single_incident_liability(prompt: str, role: str, verdict: str) -> Tuple[float, str]:
    """Computes dollar loss avoidance and risk category for a blocked or reviewed decision."""
    prompt_lower = (prompt or "").lower()
    role_lower = (role or "").lower()

    # Search for explicit currency strings like $45,000, €12,500, £250
    dollar_match = re.search(r'[\$£€](\d[\d,]*(\.\d+)?)', prompt_lower)
    numeric_val = None
    if dollar_match:
        try:
            numeric_val = float(dollar_match.group(1).replace(',', ''))
        except ValueError:
            numeric_val = None

    if any(k in prompt_lower for k in ["firewall", "ingress", "port 8080", "plaintext", "http", "staging to prod", "deploy", "root", "ssh", "security", "unauthorized"]) or "devops" in role_lower or "developer" in role_lower:
        category = "Security & Cloud Infrastructure"
        val = numeric_val if numeric_val else 45000.0
    elif any(k in prompt_lower for k in ["refund", "billing", "credit", "discount", "payout", "payment", "invoice", "price", "chargeback", "wire"]) or "billing" in role_lower:
        category = "Financial & Rogue Transactions"
        val = numeric_val if numeric_val else 5000.0
    elif any(k in prompt_lower for k in ["sla", "compliance", "gdpr", "hipaa", "remote work", "policy", "contract", "legal", "hr", "benefits", "pii"]) or "hr" in role_lower or "compliance" in role_lower:
        category = "Regulatory & Contractual SLA"
        val = numeric_val if numeric_val else 15000.0
    else:
        category = "Operational Triage"
        val = 1250.0

    return val, category


def build_slack_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    """Formats incident alert using Slack Block Kit."""
    verdict = event.get("verdict", "BLOCK")
    liability = event.get("liability_prevented_usd", 0.0)
    category = event.get("category", "Security & Cloud Infrastructure")
    actor_id = event.get("actor_id", "autonomous-agent")
    actor_role = event.get("actor_role", "operator")
    prompt = event.get("decision_prompt", "N/A")
    reasons = event.get("reasons", ["Out-of-policy agent action intercepted."])
    reason_text = "\n> ".join(reasons) if reasons else "Violated deterministic safety policy."

    color_emoji = "🚨" if verdict == "BLOCK" else "⚠️"
    headline = f"{color_emoji} [Context Trust Layer] {verdict} - ${liability:,.2f} Loss Avoided"

    return {
        "text": headline,
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{color_emoji} Rogue Agent Action Intercepted ({verdict})",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Verdict:*\n`{verdict}`"},
                    {"type": "mrkdwn", "text": f"*Liability Prevented:*\n*${liability:,.2f}*"},
                    {"type": "mrkdwn", "text": f"*Risk Category:*\n{category}"},
                    {"type": "mrkdwn", "text": f"*Actor / Agent:*\n`{actor_id}` ({actor_role})"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Target Action:*\n```{prompt}```\n*Policy Interception Rationale:*\n> {reason_text}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🛡️ *Context Trust Layer Gate* • NIST AI 600-1 / EU AI Act Art. 14 • Timestamp: {event.get('timestamp')}",
                    }
                ],
            },
        ],
    }


def build_pagerduty_payload(event: Dict[str, Any], routing_key: Optional[str] = None) -> Dict[str, Any]:
    """Formats incident alert for PagerDuty Events API v2."""
    verdict = event.get("verdict", "BLOCK")
    liability = event.get("liability_prevented_usd", 0.0)
    severity = "critical" if verdict == "BLOCK" else "warning"

    return {
        "routing_key": routing_key or "context-trust-layer-key",
        "event_action": "trigger",
        "dedup_key": f"ctl-{event.get('audit_id', str(uuid.uuid4()))}",
        "payload": {
            "summary": f"🚨 [{verdict}] Rogue Agent Action Intercepted: ${liability:,.2f} Loss Avoided",
            "source": "Context Trust Layer Gate",
            "severity": severity,
            "component": "DecisionGate",
            "group": event.get("category", "Governance"),
            "custom_details": event,
        },
    }


def build_teams_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    """Formats incident alert as a Microsoft Teams MessageCard."""
    verdict = event.get("verdict", "BLOCK")
    liability = event.get("liability_prevented_usd", 0.0)
    theme_color = "DC2626" if verdict == "BLOCK" else "D97706"

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": theme_color,
        "summary": f"[{verdict}] Rogue Agent Action Intercepted",
        "sections": [
            {
                "activityTitle": f"🚨 [{verdict}] Rogue Agent Action Intercepted",
                "activitySubtitle": f"**${liability:,.2f}** Financial Loss Prevented",
                "facts": [
                    {"name": "Actor / Agent", "value": f"{event.get('actor_id')} ({event.get('actor_role')})"},
                    {"name": "Risk Category", "value": event.get("category", "General")},
                    {"name": "Action Prompt", "value": event.get("decision_prompt", "N/A")},
                    {"name": "Interception Reasons", "value": "; ".join(event.get("reasons", []))},
                ],
                "markdown": True,
            }
        ],
    }


def build_generic_payload(event: Dict[str, Any], secret_token: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Formats standard JSON payload with optional HMAC-SHA256 signature header."""
    headers = {"Content-Type": "application/json", "User-Agent": "Context-Trust-Layer-Webhook/1.0"}
    body_str = json.dumps(event, default=str)
    if secret_token:
        signature = hmac.new(secret_token.encode("utf-8"), body_str.encode("utf-8"), hashlib.sha256).hexdigest()
        headers["X-CTL-Signature"] = f"sha256={signature}"
    return event, headers


async def dispatch_single_webhook(
    webhook: WebhookSubscription,
    event_data: Dict[str, Any],
    db: AsyncSession,
) -> Tuple[bool, int, str]:
    """Sends HTTP request to webhook destination and writes dispatch log."""
    channel_type = (webhook.channel_type or "slack").lower()
    headers = {"Content-Type": "application/json"}
    payload: Dict[str, Any]

    if channel_type == "slack":
        payload = build_slack_payload(event_data)
    elif channel_type == "pagerduty":
        payload = build_pagerduty_payload(event_data, routing_key=webhook.secret_token)
    elif channel_type == "teams":
        payload = build_teams_payload(event_data)
    else:
        payload, custom_headers = build_generic_payload(event_data, secret_token=webhook.secret_token)
        headers.update(custom_headers)

    status_code = None
    resp_text = None
    success = False

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook.url, json=payload, headers=headers)
            status_code = resp.status_code
            resp_text = resp.text[:500]
            success = 200 <= status_code < 300
    except Exception as e:
        status_code = 0
        resp_text = f"Connection error: {str(e)}"
        logger.warning(f"Webhook dispatch failed to {webhook.url}: {e}")

    # Record log
    webhook.last_triggered_at = datetime.now(timezone.utc)
    webhook.last_status_code = status_code
    webhook.last_error = None if success else resp_text

    log_entry = WebhookDispatchLog(
        webhook_id=webhook.id,
        organization_id=webhook.organization_id,
        event_type=f"incident.{event_data.get('verdict', 'block').lower()}",
        liability_prevented_usd=event_data.get("liability_prevented_usd", 0.0),
        actor_id=event_data.get("actor_id", "system"),
        verdict=event_data.get("verdict", "BLOCK"),
        response_status=status_code,
        response_body=resp_text,
    )
    db.add(log_entry)
    await db.commit()

    return success, status_code or 0, resp_text or ""


async def dispatch_decision_event(
    req: DecisionEvaluateRequest,
    decision: DecisionEvaluateResponse,
    organization_id: uuid.UUID,
) -> None:
    """Background task executed when a decision is evaluated as BLOCK or REVIEW."""
    verdict = decision.verdict.upper()
    if verdict not in ("BLOCK", "REQUIRE_REVIEW", "REVIEW"):
        return

    # 1. Compute loss avoidance and risk category
    liability_prevented, category = compute_single_incident_liability(
        prompt=req.decision_prompt,
        role=req.actor.role,
        verdict=verdict,
    )

    event_data = {
        "event": "agent.decision.intercepted",
        "audit_id": decision.audit_id,
        "audit_token": decision.audit_token,
        "organization_id": str(organization_id),
        "actor_id": req.actor.id,
        "actor_role": req.actor.role,
        "verdict": verdict,
        "risk_level": decision.risk_level,
        "category": category,
        "liability_prevented_usd": liability_prevented,
        "decision_prompt": req.decision_prompt,
        "reasons": decision.reasons,
        "suggested_action": decision.suggested_action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with AsyncSessionLocal() as session:
        stmt = (
            select(WebhookSubscription)
            .where(
                WebhookSubscription.organization_id == organization_id,
                WebhookSubscription.is_active == True,
            )
        )
        res = await session.execute(stmt)
        webhooks = res.scalars().all()

        for wh in webhooks:
            # Check verdict filters
            if verdict == "BLOCK" and not wh.trigger_on_block:
                continue
            if verdict in ("REVIEW", "REQUIRE_REVIEW") and not wh.trigger_on_review:
                continue

            # Check liability threshold
            if liability_prevented < wh.min_liability_threshold_usd:
                continue

            # Dispatch
            await dispatch_single_webhook(wh, event_data, session)


async def test_webhook_delivery(
    webhook: WebhookSubscription,
    db: AsyncSession,
) -> Tuple[bool, int, str, Dict[str, Any]]:
    """Sends a benchmark test incident payload to verify destination webhook connectivity."""
    test_event = {
        "event": "test.ping",
        "audit_id": f"test-{uuid.uuid4().hex[:8]}",
        "audit_token": hashlib.sha256(b"test-token").hexdigest(),
        "organization_id": str(webhook.organization_id),
        "actor_id": "test-devops-agent",
        "actor_role": "devops_engineer",
        "verdict": "BLOCK",
        "risk_level": "CRITICAL",
        "category": "Security & Cloud Infrastructure",
        "liability_prevented_usd": 45000.0,
        "decision_prompt": "curl -X POST http://api.production.internal/open-ports --data 'port=22&allow_all=true'",
        "reasons": [
            "Deterministic Security Policy Violation: Direct ingress port 22 modification blocked without CISO approval."
        ],
        "suggested_action": "Route request to SecOps review queue.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    success, status_code, resp_body = await dispatch_single_webhook(webhook, test_event, db)
    return success, status_code, resp_body, test_event
