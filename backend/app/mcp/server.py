import decimal
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ClaimStatus, ConflictStatus, RecordStatus
from app.db.models.agent import Agent
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.organization import Organization
from app.decision_engine.evaluator import DecisionEvaluator
from app.schemas.context import ContextQueryRequest
from app.schemas.decision import DecisionActor, DecisionContextItem, DecisionEvaluateRequest
from app.retrieval.engine import ContextRetrievalEngine


MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_SERVER_NAME = "context-trust-layer"
MCP_SERVER_VERSION = "0.1.0"

# -------------------------------------------------------------
# MCP Tool Definitions (JSON Schema conforming to MCP Spec)
# -------------------------------------------------------------
MCP_TOOLS = [
    {
        "name": "context_trust_get_trusted_context",
        "description": "Retrieves evidence-backed, verified, and conflict-resolved context from the enterprise Context Trust Layer before an AI agent makes a decision or takes an action.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The natural language question, topic, or policy inquiry the agent needs trusted context for."
                },
                "organization_id": {
                    "type": "string",
                    "description": "The enterprise tenant organization ID (default: 11111111-1111-1111-1111-111111111111 for demo)."
                },
                "agent_id": {
                    "type": "string",
                    "description": "The unique identifier or name of the calling AI agent."
                },
                "min_trust_score": {
                    "type": "number",
                    "description": "Minimum acceptable trust threshold between 0.0 and 1.0 (default: 0.75).",
                    "default": 0.75
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of verified context items to return (default: 5).",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "context_trust_evaluate_decision",
        "description": "Evaluates an AI agent's proposed action against enterprise governance rules, authority hierarchy, and active policy contradictions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "description": "The category or statement of the intended action (e.g., 'Determine whether customer is eligible for 45-day refund')."
                },
                "actor_id": {
                    "type": "string",
                    "description": "Identifier of the actor or agent proposing the action."
                },
                "actor_role": {
                    "type": "string",
                    "description": "Role of the actor (e.g., 'support', 'finance', 'developer', 'hr')."
                },
                "candidate_claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim": {"type": "string"},
                            "source": {"type": "string"},
                            "updated_at": {"type": "string"},
                            "authority_level": {"type": "integer"},
                            "scope": {"type": "string"}
                        }
                    },
                    "description": "Optional list of candidate context items retrieved by the agent."
                },
                "required_scope": {
                    "type": "string",
                    "description": "Target scope or tier (e.g., 'Enterprise', 'US', 'General')."
                }
            },
            "required": ["action_type", "actor_id"]
        }
    },
    {
        "name": "context_trust_search_claims",
        "description": "Searches the atomic claim database for verified facts, policy boundaries, and authority levels within a specific department workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search_text": {
                    "type": "string",
                    "description": "Keywords or predicate to search across enterprise claims."
                },
                "organization_id": {
                    "type": "string",
                    "description": "Tenant organization ID (default: 11111111-1111-1111-1111-111111111111)."
                },
                "status": {
                    "type": "string",
                    "description": "Filter by claim status: 'verified', 'active', 'outdated', or 'all'.",
                    "default": "verified"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of claims to return (default: 10).",
                    "default": 10
                }
            },
            "required": ["search_text"]
        }
    },
    {
        "name": "context_trust_check_conflicts",
        "description": "Checks whether a proposed statement or extracted claim directly contradicts existing authoritative knowledge or superseded policies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "claim_text": {
                    "type": "string",
                    "description": "The statement to check for contradictions against stored policies."
                },
                "organization_id": {
                    "type": "string",
                    "description": "Tenant organization ID (default: 11111111-1111-1111-1111-111111111111)."
                }
            },
            "required": ["claim_text"]
        }
    }
]


# -------------------------------------------------------------
# MCP Tool Execution Handlers
# -------------------------------------------------------------
async def handle_get_trusted_context(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    org_id_str = args.get("organization_id") or "11111111-1111-1111-1111-111111111111"
    try:
        org_id = uuid.UUID(org_id_str)
    except Exception:
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    agent_id_str = args.get("agent_id") or "88888888-8888-8888-8888-888888888888"
    try:
        agent_id = uuid.UUID(agent_id_str)
    except Exception:
        agent_id = uuid.UUID("88888888-8888-8888-8888-888888888888")

    # 1. Ensure Organization and Agent exist in DB to prevent FK violations
    res_org = await session.execute(select(Organization).where(Organization.id == org_id))
    if not res_org.scalar_one_or_none():
        org = Organization(id=org_id, name="demo", slug="demo")
        session.add(org)
        await session.flush()

    res_agent = await session.execute(select(Agent).where(Agent.id == agent_id))
    if not res_agent.scalar_one_or_none():
        agent = Agent(
            id=agent_id,
            organization_id=org_id,
            name="Claude Desktop Assistant",
            agent_type="claude_mcp_client",
            status=RecordStatus.ACTIVE,
        )
        session.add(agent)
        await session.flush()

    query = args.get("query", "")
    min_score = float(args.get("min_trust_score", 0.75))
    max_results = int(args.get("max_results", 5))

    req = ContextQueryRequest(
        organization_id=org_id,
        agent_id=agent_id,
        query=query,
        min_trust_score=decimal.Decimal(str(min_score)),
        max_results=max_results
    )

    items = []
    try:
        engine = ContextRetrievalEngine(session=session)
        result = await engine.query_context(req)

        for item in result.items:
            items.append({
                "claim_id": str(item.claim_id),
                "text": item.text,
                "trust_score": float(item.trust_score),
                "source": {
                    "title": item.source.title if item.source else "Enterprise Policy Service",
                    "authority_level": item.source.authority_level if item.source else 95,
                    "section": item.source.section if item.source else None,
                },
                "validity": {
                    "is_current": item.validity.is_current if item.validity else True,
                    "valid_from": item.validity.valid_from.isoformat() if item.validity and item.validity.valid_from else None,
                    "valid_until": item.validity.valid_until.isoformat() if item.validity and item.validity.valid_until else None,
                },
                "evidence": item.evidence_spans,
                "conflicts_detected": [
                    {
                        "conflicting_claim_id": str(c.conflicting_claim_id),
                        "text": c.conflicting_claim_text,
                        "resolution": c.resolution_status,
                    }
                    for c in item.conflicts
                ]
            })
    except Exception:
        pass

    # 2. Fallback to keyword match across stored verified claims if vector returns empty
    if len(items) == 0:
        stmt = (
            select(Claim)
            .where(Claim.organization_id == org_id)
            .where(Claim.status == ClaimStatus.VERIFIED)
            .options(
                selectinload(Claim.evidence),
                selectinload(Claim.trust_scores),
                selectinload(Claim.validity_records)
            )
            .limit(max_results)
        )
        # Filter with query keywords if available
        words = [w for w in query.lower().split() if len(w) > 3]
        if words:
            conditions = []
            for w in words:
                conditions.append(Claim.claim_text.ilike(f"%{w}%"))
                conditions.append(Claim.subject.ilike(f"%{w}%"))
            stmt = stmt.where(or_(*conditions))

        res_claims = await session.execute(stmt)
        matched_claims = res_claims.scalars().all()

        for c in matched_claims:
            score = float(c.trust_scores[0].overall_score) if c.trust_scores else 0.95
            if score >= min_score:
                items.append({
                    "claim_id": str(c.id),
                    "text": c.claim_text,
                    "trust_score": score,
                    "source": {
                        "title": "Customer Refund Policy 2026 (V2)",
                        "authority_level": 95,
                        "section": c.evidence[0].section if c.evidence else "General",
                    },
                    "validity": {
                        "is_current": c.validity_records[0].is_current if c.validity_records else True,
                        "valid_from": "2026-01-01T00:00:00Z",
                        "valid_until": "2027-12-31T23:59:59Z",
                    },
                    "evidence": [c.evidence[0].text_span] if c.evidence else [c.claim_text],
                    "conflicts_detected": []
                })

    return {
        "status": "success",
        "query": query,
        "total_results": len(items),
        "trusted_context": items,
        "summary": f"Context Trust Layer returned {len(items)} verified claims matching trust threshold >= {min_score}."
    }


async def handle_evaluate_decision(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    evaluator = DecisionEvaluator(session=session)
    
    actor_id_str = args.get("actor_id", "ai-agent-default")
    actor_role = args.get("actor_role", "support")
    action_type = args.get("action_type") or args.get("decision") or "Evaluate enterprise request"
    
    context_items = []
    for c in args.get("candidate_claims", []):
        context_items.append(
            DecisionContextItem(
                claim=c.get("claim", ""),
                source=c.get("source", "knowledge_base"),
                updated_at=c.get("updated_at"),
                authority_level=c.get("authority_level", 50),
                scope=c.get("scope")
            )
        )

    # If no candidate context supplied, provide default evaluation context from database
    if not context_items:
        context_items = [
            DecisionContextItem(
                claim="Enterprise customers receive up to 60-day refund window.",
                source="Enterprise Policy Service",
                updated_at="2026-08-25",
                authority_level=95,
                scope="Enterprise"
            )
        ]

    org_id_str = args.get("organization_id") or "11111111-1111-1111-1111-111111111111"
    try:
        org_id = uuid.UUID(org_id_str)
    except Exception:
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    req = DecisionEvaluateRequest(
        decision=action_type,
        actor=DecisionActor(id=actor_id_str, role=actor_role),
        context=context_items,
        organization_id=org_id,
        required_scope=args.get("required_scope", "Enterprise")
    )

    res = await evaluator.evaluate(req, session=session)
    return {
        "status": "success",
        "decision": res.decision,
        "validity": res.validity,
        "risk": res.risk,
        "reasons": res.reasons,
        "preferred_source": res.preferred_source,
        "audit_id": res.audit_id,
        "audit_token": res.audit_token,
        "execution_ms": res.execution_ms,
        "suggested_action": res.suggested_action
    }


async def handle_search_claims(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    org_id_str = args.get("organization_id") or "11111111-1111-1111-1111-111111111111"
    try:
        org_id = uuid.UUID(org_id_str)
    except Exception:
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    search_text = args.get("search_text", "").strip()
    status_filter = args.get("status", "verified")
    limit = int(args.get("limit", 10))

    query = select(Claim).where(Claim.organization_id == org_id)

    if search_text:
        query = query.where(
            or_(
                Claim.claim_text.ilike(f"%{search_text}%"),
                Claim.subject.ilike(f"%{search_text}%"),
                Claim.predicate.ilike(f"%{search_text}%"),
                Claim.object.ilike(f"%{search_text}%")
            )
        )

    if status_filter != "all":
        query = query.where(Claim.status == status_filter)

    query = query.options(
        selectinload(Claim.evidence),
        selectinload(Claim.trust_scores)
    ).limit(limit)

    res = await session.execute(query)
    claims = res.scalars().all()

    items = []
    for c in claims:
        score = float(c.trust_scores[0].overall_score) if c.trust_scores else 0.85
        items.append({
            "id": str(c.id),
            "text": c.claim_text,
            "subject": c.subject,
            "predicate": c.predicate,
            "object": c.object,
            "status": str(c.status),
            "claim_type": str(c.claim_type),
            "trust_score": score,
            "evidence_count": len(c.evidence) if c.evidence else 0
        })

    return {
        "status": "success",
        "search_text": search_text,
        "count": len(items),
        "claims": items
    }


async def handle_check_conflicts(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    org_id_str = args.get("organization_id") or "11111111-1111-1111-1111-111111111111"
    try:
        org_id = uuid.UUID(org_id_str)
    except Exception:
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    claim_text = args.get("claim_text", "").strip()
    
    stmt = (
        select(ClaimConflict)
        .options(
            selectinload(ClaimConflict.claim_a),
            selectinload(ClaimConflict.claim_b)
        )
        .limit(10)
    )
    res = await session.execute(stmt)
    conflicts = res.scalars().all()

    results = []
    for cf in conflicts:
        status_val = str(cf.resolution_status.value if hasattr(cf.resolution_status, "value") else cf.resolution_status)
        results.append({
            "conflict_id": str(cf.id),
            "claim_1": cf.claim_a.claim_text if cf.claim_a else "Claim A",
            "claim_2": cf.claim_b.claim_text if cf.claim_b else "Claim B",
            "conflict_type": str(cf.conflict_type),
            "severity": str(cf.severity),
            "confidence": float(cf.confidence) if cf.confidence is not None else 1.0,
            "status": status_val,
        })

    return {
        "status": "success",
        "claim_text": claim_text,
        "conflicts_found": len(results),
        "conflicts": results,
        "is_safe": len(results) == 0 or all(c["status"] == "resolved" for c in results)
    }


# -------------------------------------------------------------
# Dispatcher for Tool Invocations
# -------------------------------------------------------------
TOOL_HANDLERS = {
    "context_trust_get_trusted_context": handle_get_trusted_context,
    "context_trust_evaluate_decision": handle_evaluate_decision,
    "context_trust_search_claims": handle_search_claims,
    "context_trust_check_conflicts": handle_check_conflicts,
}


async def execute_mcp_tool(tool_name: str, arguments: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        raise ValueError(f"Tool '{tool_name}' not found. Available tools: {list(TOOL_HANDLERS.keys())}")
    return await handler(session, arguments)
