import hashlib
import json
import logging
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.slack_security import (
    decode_oauth_state,
    decode_slack_link_token,
    decrypt_slack_bot_token,
    encrypt_slack_bot_token,
    generate_oauth_state,
    generate_slack_link_token,
    resolve_slack_backend_url,
    verify_slack_signature,
)
from app.db.database import get_db
from app.db.models.hitl_escalation import HitlEscalation
from app.db.models.organization import Organization
from app.db.models.slack import (
    SlackFeedback,
    SlackInboundRequest,
    SlackInstallation,
    SlackJob,
    SlackUserIdentity,
)
from app.db.models.user import User
from app.services.slack_block_kit import SlackBlockKitRenderer
from app.services.slack_worker import slack_worker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])


class AccountLinkRequest(BaseModel):
    token: str = Field(..., description="Signed account linking JWT from Slack card")


@router.post("/commands")
async def handle_slash_command(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_slack_request_timestamp: Optional[str] = Header(None, alias="X-Slack-Request-Timestamp"),
    x_slack_signature: Optional[str] = Header(None, alias="X-Slack-Signature"),
):
    """
    Ingress receiver for Slack slash commands (/trulin ask <question>, /trulin help, etc.).
    Adheres strictly to Slack's 3-second SLA by verifying signatures, recording durable jobs,
    and acknowledging immediately with a private ephemeral response.
    """
    # 1. Read raw body bytes for signature verification
    raw_body = await request.body()

    # 2. Verify signature & timestamp freshness (< 5 minutes)
    if settings.slack_signing_secret or not settings.app_env.startswith("dev"):
        is_valid = verify_slack_signature(
            raw_body=raw_body,
            timestamp_header=x_slack_request_timestamp,
            signature_header=x_slack_signature,
        )
        if not is_valid:
            req_app_id = "unknown"
            try:
                parsed_dbg = urllib.parse.parse_qs(raw_body.decode("utf-8", errors="replace"))
                req_app_id = parsed_dbg.get("api_app_id", ["unknown"])[0]
            except Exception:
                pass
            logger.warning(
                f"Slack slash command rejected: invalid signature or expired timestamp. "
                f"(Request api_app_id='{req_app_id}', Configured SLACK_APP_ID='{settings.slack_app_id}')"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Slack request signature or timestamp freshness check failed.",
            )

    # 3. Parse application/x-www-form-urlencoded body
    form_data = urllib.parse.parse_qs(raw_body.decode("utf-8", errors="replace"))
    
    command = form_data.get("command", ["/trulin"])[0].strip()
    text = form_data.get("text", [""])[0].strip()
    team_id = form_data.get("team_id", [""])[0].strip()
    user_id = form_data.get("user_id", [""])[0].strip()
    channel_id = form_data.get("channel_id", [""])[0].strip()
    response_url = form_data.get("response_url", [""])[0].strip()
    trigger_id = form_data.get("trigger_id", [""])[0].strip() if "trigger_id" in form_data else None

    if not team_id or not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing team_id or user_id.")

    # 4. Resolve workspace installation
    inst_stmt = select(SlackInstallation).where(
        SlackInstallation.slack_team_id == team_id,
        SlackInstallation.is_active == True,
    )
    installation = (await db.execute(inst_stmt)).scalar_one_or_none()
    if not installation:
        return {
            "response_type": "ephemeral",
            "text": "⚠️ Trulin is not currently installed or active in this Slack workspace. Please ask an administrator to install the Trulin app.",
        }

    # 5. Handle immediate subcommands (/trulin help, /trulin link, /trulin status)
    lower_text = text.lower()
    if lower_text in ("help", "--help", "-h") or not text:
        return SlackBlockKitRenderer.render_help_card()

    if lower_text in ("link", "connect", "auth"):
        link_token = generate_slack_link_token(
            slack_team_id=team_id,
            slack_user_id=user_id,
            organization_id=str(installation.organization_id),
        )
        proto = request.headers.get("x-forwarded-proto", "https")
        host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
        base_url = resolve_slack_backend_url(request_host=host, request_proto=proto)
        link_url = f"{base_url}/v1/slack/link-ui?token={link_token}"
        return SlackBlockKitRenderer.render_account_linking_card(link_url)

    if lower_text in ("status", "health"):
        ident_stmt = select(SlackUserIdentity).where(
            SlackUserIdentity.slack_team_id == team_id,
            SlackUserIdentity.slack_user_id == user_id,
            SlackUserIdentity.is_active == True,
        )
        identity = (await db.execute(ident_stmt)).scalar_one_or_none()
        link_status = "Linked ✅" if identity else "Unlinked ⚠️ (use `/trulin link`)"
        return {
            "response_type": "ephemeral",
            "text": f"🛡️ *Trulin Integration Status:*\n• Workspace: `{installation.slack_team_name or team_id}`\n• Identity: {link_status}\n• Assistant Mode: Read-Only Policy Q&A",
        }

    # Clean question text if user typed '/trulin ask <question>'
    question_clean = text
    if lower_text.startswith("ask "):
        question_clean = text[4:].strip()

    # 6. Compute query fingerprint for idempotency
    now = datetime.now(timezone.utc)
    fingerprint_raw = f"{team_id}:{user_id}:{trigger_id or 'notrig'}:{command}:{question_clean}"
    fingerprint = hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()
    trace_id = f"trc-{uuid.uuid4().hex[:8]}"

    # Slack response_url is valid for 30 minutes; configure 25-minute guard
    expires_at = now + timedelta(minutes=25)

    # 7. Check for duplicate inbound request
    existing_req = (await db.execute(
        select(SlackInboundRequest).where(SlackInboundRequest.query_fingerprint == fingerprint)
    )).scalar_one_or_none()

    if existing_req:
        # Idempotent response: return immediate acknowledgment without re-enqueuing duplicate job
        return {
            "response_type": "ephemeral",
            "text": "Checking your permitted Trulin sources…",
        }

    # 8. Atomically persist inbound request and queue background job
    inbound_req = SlackInboundRequest(
        id=uuid.uuid4(),
        organization_id=installation.organization_id,
        slack_team_id=team_id,
        slack_user_id=user_id,
        slack_channel_id=channel_id,
        command=command,
        query_fingerprint=fingerprint,
        response_url=response_url,
        response_url_expires_at=expires_at,
        trigger_id=trigger_id,
        trace_id=trace_id,
        raw_text=question_clean,
        status="QUEUED",
        created_at=now,
    )
    db.add(inbound_req)
    await db.flush()

    job = SlackJob(
        id=uuid.uuid4(),
        inbound_request_id=inbound_req.id,
        status="QUEUED",
        attempts=0,
        max_attempts=3,
        next_run_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    await db.commit()

    # Proactively notify worker to process pending job
    slack_worker.start()

    # 9. Return fast acknowledgment (< 200ms) within Slack's 3-second SLA
    return {
        "response_type": "ephemeral",
        "text": "Checking your permitted Trulin sources…",
    }


@router.post("/interactions")
async def handle_interactions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_slack_request_timestamp: Optional[str] = Header(None, alias="X-Slack-Request-Timestamp"),
    x_slack_signature: Optional[str] = Header(None, alias="X-Slack-Signature"),
):
    """
    Handles Block Kit interactive button actions (Report Issue, Request Review).
    """
    raw_body = await request.body()

    if settings.slack_signing_secret or not settings.app_env.startswith("dev"):
        is_valid = verify_slack_signature(
            raw_body=raw_body,
            timestamp_header=x_slack_request_timestamp,
            signature_header=x_slack_signature,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Slack request signature or expired timestamp.",
            )

    form_data = urllib.parse.parse_qs(raw_body.decode("utf-8", errors="replace"))
    payload_raw = form_data.get("payload", ["{}"])[0]
    payload = json.loads(payload_raw)

    team_id = payload.get("team", {}).get("id")
    user_id = payload.get("user", {}).get("id")
    actions = payload.get("actions", [])
    if not actions:
        return Response(status_code=200)

    action = actions[0]
    action_id = action.get("action_id")
    trace_id = action.get("value") or "unknown_trace"

    # Resolve organization from installation
    inst = (await db.execute(
        select(SlackInstallation).where(SlackInstallation.slack_team_id == team_id)
    )).scalar_one_or_none()
    org_id = inst.organization_id if inst else uuid.UUID("11111111-1111-1111-1111-111111111111")

    # Resolve linked user if any
    ident = (await db.execute(
        select(SlackUserIdentity).where(
            SlackUserIdentity.slack_team_id == team_id,
            SlackUserIdentity.slack_user_id == user_id,
        )
    )).scalar_one_or_none()
    trulin_user_id = ident.trulin_user_id if ident else None

    if action_id == "slack_report_issue":
        feedback = SlackFeedback(
            trace_id=trace_id,
            organization_id=org_id,
            trulin_user_id=trulin_user_id,
            feedback_type="REPORT_ISSUE",
            reviewer_notes=f"User @{user_id} reported an issue from Slack for trace {trace_id}.",
        )
        db.add(feedback)
        await db.commit()
        return {
            "response_type": "ephemeral",
            "replace_original": False,
            "text": f"✅ Thank you! An issue report has been logged with compliance stewards (Trace ID: `{trace_id}`).",
        }

    elif action_id == "slack_request_review":
        feedback = SlackFeedback(
            trace_id=trace_id,
            organization_id=org_id,
            trulin_user_id=trulin_user_id,
            feedback_type="REQUEST_REVIEW",
            reviewer_notes=f"Human review requested from Slack for trace {trace_id}.",
        )
        db.add(feedback)

        escalation = HitlEscalation(
            organization_id=org_id,
            audit_id=trace_id,
            actor_id=str(trulin_user_id or user_id),
            actor_role="Slack Requester",
            action_prompt=f"Human policy review requested for Slack interaction (Trace: {trace_id})",
            reasons=["Requester flagged ambiguity or requested certified human steward verification."],
            category="Operational Triage",
            liability_prevented_usd=0.0,
            status="PENDING",
        )
        db.add(escalation)
        await db.commit()
        return {
            "response_type": "ephemeral",
            "replace_original": False,
            "text": f"🛡️ A review request has been routed to your authorized organization compliance reviewers (Trace ID: `{trace_id}`).",
        }

    return Response(status_code=200)


@router.get("/oauth/install")
async def initiate_slack_oauth(
    organization_id: uuid.UUID = Query(..., description="Target Trulin organization ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiates administrator OAuth v2 flow to install the Trulin app into a Slack workspace.
    Binds the installation to the initiating administrator and organization.
    """
    if current_user.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot install for another organization.")

    user_role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if user_role_str not in ("admin", "steward"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator privileges required to install Slack integration.")

    state_token = generate_oauth_state(
        organization_id=str(organization_id),
        admin_user_id=str(current_user.id),
    )

    client_id = settings.slack_client_id or "test_client_id"
    redirect_uri = settings.slack_redirect_uri
    scopes = "commands,chat:write"
    
    slack_auth_url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={urllib.parse.quote(client_id)}"
        f"&scope={urllib.parse.quote(scopes)}"
        f"&state={urllib.parse.quote(state_token)}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
    )

    return {"auth_url": slack_auth_url}


@router.api_route("/oauth/callback", methods=["GET", "POST"])
async def handle_oauth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    x_slack_request_timestamp: Optional[str] = Header(None, alias="X-Slack-Request-Timestamp"),
    x_slack_signature: Optional[str] = Header(None, alias="X-Slack-Signature"),
):
    """
    Handles Slack OAuth v2 callback: verifies one-time state, exchanges code for bot token,
    encrypts credentials at rest, and binds the workspace to the Trulin organization.
    Also handles POST requests gracefully if Slash Commands or URL challenges hit this URL.
    """
    # Gracefully intercept POST requests if misrouted by Slack settings
    if request.method == "POST":
        raw_body = await request.body()
        content_type = request.headers.get("content-type", "")

        # 1. Handle URL verification challenge
        if "application/json" in content_type:
            try:
                body_json = json.loads(raw_body)
                if body_json.get("type") == "url_verification":
                    return {"challenge": body_json.get("challenge")}
            except Exception:
                pass

        # 2. Handle misrouted slash command
        if b"command=" in raw_body:
            return await handle_slash_command(
                request=request,
                db=db,
                x_slack_request_timestamp=x_slack_request_timestamp,
                x_slack_signature=x_slack_signature,
            )

        # 3. Handle misrouted interaction
        if b"payload=" in raw_body:
            return await handle_interactions(
                request=request,
                db=db,
                x_slack_request_timestamp=x_slack_request_timestamp,
                x_slack_signature=x_slack_signature,
            )

    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slack authorization error: {error}")

    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code or state token.")

    # 1. Validate state token (nonce, expiration, bound organization)
    state_data = decode_oauth_state(state)
    target_org_id = uuid.UUID(state_data["organization_id"])
    admin_user_id = uuid.UUID(state_data["admin_user_id"])

    # 2. Determine exact redirect_uri to match what was passed in authorization link
    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
    inferred_uri = f"{proto}://{host}/v1/slack/oauth/callback" if host else None
    
    redirect_uri = settings.slack_redirect_uri
    if not redirect_uri or "localhost" in redirect_uri:
        redirect_uri = inferred_uri

    # 3. Exchange code for tokens via Slack API
    token_url = "https://slack.com/api/oauth.v2.access"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(
            token_url,
            data={
                "client_id": settings.slack_client_id,
                "client_secret": settings.slack_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        data = res.json()

    if not data.get("ok"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slack OAuth token exchange failed: {data.get('error')}")

    # Check for Enterprise Grid installation
    is_enterprise = data.get("is_enterprise_install", False)
    if is_enterprise:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enterprise Grid org-wide installation is not supported in the read-only pilot. Please install to a specific workspace.",
        )

    team_info = data.get("team", {})
    team_id = team_info.get("id")
    team_name = team_info.get("name", "Slack Workspace")
    bot_user_id = data.get("bot_user_id", "")
    bot_token = data.get("access_token", "")
    granted_scopes = data.get("scope", "commands,chat:write").split(",")

    if not team_id or not bot_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token response from Slack.")

    # 3. Encrypt bot token at rest using Fernet envelope encryption
    encrypted_token = encrypt_slack_bot_token(bot_token)

    # 4. Upsert SlackInstallation record
    existing_stmt = select(SlackInstallation).where(SlackInstallation.slack_team_id == team_id)
    installation = (await db.execute(existing_stmt)).scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if installation:
        installation.organization_id = target_org_id
        installation.slack_team_name = team_name
        installation.bot_user_id = bot_user_id
        installation.encrypted_bot_token = encrypted_token
        installation.installed_by_user_id = admin_user_id
        installation.is_active = True
        installation.scopes = granted_scopes
        installation.updated_at = now
    else:
        installation = SlackInstallation(
            id=uuid.uuid4(),
            organization_id=target_org_id,
            slack_team_id=team_id,
            slack_team_name=team_name,
            bot_user_id=bot_user_id,
            encrypted_bot_token=encrypted_token,
            installed_by_user_id=admin_user_id,
            is_active=True,
            scopes=granted_scopes,
            created_at=now,
            updated_at=now,
        )
        db.add(installation)

    await db.commit()

    # Return clean HTML success card
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Trulin Slack Installation Successful</title>
            <style>
                body {{ background: #0B0F19; color: #F8FAFC; font-family: -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                .card {{ background: #161F30; border: 1px solid #2A3854; border-radius: 16px; padding: 2.5rem; max-width: 480px; text-align: center; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
                .badge {{ background: #064E3B; color: #34D399; font-size: 0.85rem; font-weight: 600; padding: 6px 12px; border-radius: 9999px; margin-bottom: 1.25rem; display: inline-block; }}
                h1 {{ font-size: 1.5rem; margin-bottom: 0.75rem; }}
                p {{ color: #94A3B8; font-size: 0.95rem; line-height: 1.5; }}
                .code-box {{ background: #0F172A; border: 1px solid #222F46; border-radius: 8px; padding: 0.75rem; margin: 1.25rem 0; font-family: monospace; color: #38BDF8; font-size: 1.1rem; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="badge">✅ Connected to Slack</div>
                <h1>Installation Successful!</h1>
                <p>Workspace <strong>{team_name}</strong> is now securely bound to your Trulin organization.</p>
                <div class="code-box">/trulin ask &lt;question&gt;</div>
                <p>You can now return to Slack and ask your first policy or agreement question!</p>
            </div>
        </body>
        </html>
        """
    )


@router.post("/auth/link")
async def link_slack_user_account(
    req: AccountLinkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticated web endpoint to complete user identity linking.
    Binds the logged-in Trulin user to the Slack (team_id, user_id) tuple.
    """
    token_data = decode_slack_link_token(req.token)
    slack_team_id = token_data["slack_team_id"]
    slack_user_id = token_data["slack_user_id"]
    org_id = uuid.UUID(token_data["organization_id"])

    # Ensure user belongs to the same organization bound to this Slack installation
    if current_user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your Trulin user does not belong to the organization bound to this Slack workspace.",
        )

    # Upsert SlackUserIdentity mapping
    stmt = select(SlackUserIdentity).where(
        SlackUserIdentity.slack_team_id == slack_team_id,
        SlackUserIdentity.slack_user_id == slack_user_id,
    )
    identity = (await db.execute(stmt)).scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if identity:
        identity.trulin_user_id = current_user.id
        identity.organization_id = org_id
        identity.is_active = True
        identity.linked_at = now
    else:
        identity = SlackUserIdentity(
            id=uuid.uuid4(),
            organization_id=org_id,
            slack_team_id=slack_team_id,
            slack_user_id=slack_user_id,
            trulin_user_id=current_user.id,
            is_active=True,
            linked_at=now,
        )
        db.add(identity)

    await db.commit()

    return {
        "status": "linked",
        "slack_team_id": slack_team_id,
        "slack_user_id": slack_user_id,
        "trulin_user_id": str(current_user.id),
        "message": "Slack profile successfully linked to your Trulin account. You can now use /trulin ask.",
    }


@router.get("/link-ui", response_class=HTMLResponse)
async def serve_slack_link_ui(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Renders an interactive HTML confirmation page for linking a Slack user profile to Trulin.
    """
    try:
        token_data = decode_slack_link_token(token)
    except Exception as e:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Link Expired - Trulin</title>
            <style>body {{ background: #0f172a; color: #f8fafc; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .card {{ background: #1e293b; padding: 2rem; border-radius: 12px; max-width: 450px; text-align: center; border: 1px solid #334155; }}
            .btn {{ background: #ea580c; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; display: inline-block; margin-top: 15px; }}</style>
            </head>
            <body>
            <div class="card">
                <h2 style="color: #ef4444;">⚠️ Link Expired or Invalid</h2>
                <p>{str(e)}</p>
                <p>Please return to Slack and type <code>/trulin link</code> to generate a fresh link.</p>
            </div>
            </body>
            </html>
            """,
            status_code=400,
        )

    slack_user_id = token_data["slack_user_id"]
    slack_team_id = token_data["slack_team_id"]
    org_id = token_data["organization_id"]

    # Look up org name
    org = (await db.execute(select(Organization).where(Organization.id == uuid.UUID(org_id)))).scalar_one_or_none()
    org_name = org.name if org else "Enterprise Tenant"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Connect Trulin to Slack</title>
        <style>
            body {{
                background-color: #0B0F19;
                color: #F8FAFC;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
            }}
            .card {{
                background-color: #161F30;
                border: 1px solid #2A3854;
                border-radius: 16px;
                padding: 2.5rem;
                max-width: 480px;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
                text-align: center;
            }}
            .badge {{
                display: inline-block;
                background-color: #1E293B;
                color: #38BDF8;
                font-size: 0.85rem;
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 9999px;
                margin-bottom: 1.25rem;
                border: 1px solid #334155;
            }}
            h1 {{ font-size: 1.5rem; margin-bottom: 0.75rem; color: #FFFFFF; }}
            p {{ color: #94A3B8; font-size: 0.95rem; line-height: 1.5; margin-bottom: 1.5rem; }}
            .details {{
                background: #0F172A;
                border: 1px solid #222F46;
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 1.5rem;
                text-align: left;
                font-size: 0.9rem;
            }}
            .details-row {{ display: flex; justify-content: space-between; margin-bottom: 0.5rem; }}
            .details-row:last-child {{ margin-bottom: 0; }}
            .details-label {{ color: #64748B; }}
            .details-val {{ color: #E2E8F0; font-family: monospace; }}
            .btn {{
                display: block;
                width: 100%;
                background: linear-gradient(135deg, #2563EB, #1D4ED8);
                color: white;
                font-weight: 600;
                padding: 12px 0;
                border-radius: 8px;
                border: none;
                cursor: pointer;
                font-size: 1rem;
                transition: opacity 0.2s;
            }}
            .btn:hover {{ opacity: 0.9; }}
            .success {{ color: #10B981; margin-top: 1rem; display: none; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">🛡️ Trulin Integration</div>
            <h1>Connect Your Account</h1>
            <p>Authorize Trulin Assistant in Slack to query verified policies on your behalf.</p>
            
            <div class="details">
                <div class="details-row">
                    <span class="details-label">Organization:</span>
                    <span class="details-val">{org_name}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">Slack User ID:</span>
                    <span class="details-val">{slack_user_id}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">Workspace:</span>
                    <span class="details-val">{slack_team_id}</span>
                </div>
            </div>

            <div id="authStatus" style="font-size: 0.85rem; color: #94A3B8; margin-bottom: 1rem;"></div>

            <div id="oneClickSection" style="display: none;">
                <button class="btn" id="confirmBtn" onclick="confirmLink()">Confirm & Link Profile</button>
            </div>

            <div id="loginSection" style="display: none; text-align: left;">
                <a href="/v1/auth/sso/authorize?provider=google" class="btn" style="background: #FFFFFF; color: #1E293B; display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 1rem; text-decoration: none; font-weight: 600; padding: 10px 0;">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>
                    Continue with Google
                </a>
                <div style="text-align: center; color: #64748B; font-size: 0.78rem; margin-bottom: 1rem;">— OR SIGN IN WITH EMAIL —</div>
                <div style="margin-bottom: 0.75rem;">
                    <label style="display: block; font-size: 0.8rem; color: #94A3B8; margin-bottom: 4px;">Trulin Corporate Email</label>
                    <input type="email" id="emailInput" placeholder="name@company.com" style="width: 100%; box-sizing: border-box; background: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 9px 12px; color: #F8FAFC; font-size: 0.9rem;" />
                </div>
                <div style="margin-bottom: 1rem;">
                    <label style="display: block; font-size: 0.8rem; color: #94A3B8; margin-bottom: 4px;">Password</label>
                    <input type="password" id="passwordInput" placeholder="••••••••" style="width: 100%; box-sizing: border-box; background: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 9px 12px; color: #F8FAFC; font-size: 0.9rem;" />
                </div>
                <button class="btn" id="loginBtn" onclick="loginAndLink()">Sign In & Link Profile</button>
            </div>

            <div id="statusMsg" style="margin-top: 1rem; font-size: 0.9rem; display: none;"></div>
        </div>

        <script>
            const linkToken = '{token}';
            const localToken = localStorage.getItem('context_trust_token');
            const authStatus = document.getElementById('authStatus');
            const oneClick = document.getElementById('oneClickSection');
            const loginSec = document.getElementById('loginSection');
            const statusMsg = document.getElementById('statusMsg');

            if (localToken) {{
                authStatus.innerText = '✅ Authenticated session detected in browser.';
                oneClick.style.display = 'block';
            }} else {{
                authStatus.innerText = 'Sign in with your Trulin account to link your Slack identity:';
                loginSec.style.display = 'block';
            }}

            async function submitLink(bearerToken) {{
                const res = await fetch('/v1/slack/auth/link', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + bearerToken
                    }},
                    body: JSON.stringify({{ token: linkToken }})
                }});
                if (!res.ok) {{
                    const err = await res.json();
                    throw new Error(err.detail || 'Identity linking rejected.');
                }}
                return await res.json();
            }}

            async function confirmLink() {{
                const btn = document.getElementById('confirmBtn');
                btn.disabled = true;
                btn.innerText = 'Connecting...';
                try {{
                    await submitLink(localToken);
                    oneClick.style.display = 'none';
                    authStatus.style.display = 'none';
                    statusMsg.style.display = 'block';
                    statusMsg.style.color = '#10B981';
                    statusMsg.innerHTML = '✅ <b>Profile successfully linked!</b><br>You can now return to Slack and use <code>/trulin ask</code>.';
                }} catch (e) {{
                    btn.disabled = false;
                    btn.innerText = 'Confirm & Link Profile';
                    authStatus.innerText = 'Session expired or invalid. Please sign in:';
                    oneClick.style.display = 'none';
                    loginSec.style.display = 'block';
                }}
            }}

            async function loginAndLink() {{
                const email = document.getElementById('emailInput').value.trim();
                const password = document.getElementById('passwordInput').value;
                const btn = document.getElementById('loginBtn');

                if (!email || !password) {{
                    alert('Please enter your Trulin email and password.');
                    return;
                }}

                btn.disabled = true;
                btn.innerText = 'Authenticating...';

                try {{
                    const loginRes = await fetch('/v1/auth/login', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ email: email, password: password }})
                    }});
                    if (!loginRes.ok) {{
                        const err = await loginRes.json();
                        throw new Error(err.detail || 'Invalid email or password.');
                    }}
                    const loginData = await loginRes.json();
                    const newBearer = loginData.access_token;
                    localStorage.setItem('context_trust_token', newBearer);

                    btn.innerText = 'Linking Profile...';
                    await submitLink(newBearer);

                    loginSec.style.display = 'none';
                    authStatus.style.display = 'none';
                    statusMsg.style.display = 'block';
                    statusMsg.style.color = '#10B981';
                    statusMsg.innerHTML = '✅ <b>Profile successfully linked!</b><br>You can now return to Slack and use <code>/trulin ask</code>.';
                }} catch (e) {{
                    alert(e.message);
                    btn.disabled = false;
                    btn.innerText = 'Sign In & Link Profile';
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/events")
async def handle_slack_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_slack_request_timestamp: Optional[str] = Header(None, alias="X-Slack-Request-Timestamp"),
    x_slack_signature: Optional[str] = Header(None, alias="X-Slack-Signature"),
):
    """
    Handles Slack Events API payloads (URL verification challenge, app_uninstalled, tokens_revoked).
    """
    raw_body = await request.body()
    try:
        data = json.loads(raw_body.decode("utf-8", errors="replace"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    # 1. URL verification challenge during Slack portal setup
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}

    # 2. Verify signature for real events
    if settings.slack_signing_secret or not settings.app_env.startswith("dev"):
        is_valid = verify_slack_signature(
            raw_body=raw_body,
            timestamp_header=x_slack_request_timestamp,
            signature_header=x_slack_signature,
        )
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid signature.")

    # 3. Handle app uninstalled or token revoked
    event = data.get("event", {})
    event_type = event.get("type")
    team_id = data.get("team_id")

    if event_type in ("app_uninstalled", "tokens_revoked"):
        now = datetime.now(timezone.utc)
        inst_stmt = select(SlackInstallation).where(SlackInstallation.slack_team_id == team_id)
        installation = (await db.execute(inst_stmt)).scalar_one_or_none()
        if installation:
            installation.is_active = False
            installation.revoked_at = now
            await db.commit()
            logger.info(f"Slack workspace {team_id} deactivated via {event_type} event.")

    return Response(status_code=200)


@router.get("/installations")
async def list_installations(
    organization_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists active Slack installations for an organization."""
    if current_user.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    stmt = select(SlackInstallation).where(SlackInstallation.organization_id == organization_id)
    res = await db.execute(stmt)
    records = res.scalars().all()
    return [
        {
            "id": str(r.id),
            "slack_team_id": r.slack_team_id,
            "slack_team_name": r.slack_team_name,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
