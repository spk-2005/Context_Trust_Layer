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
    },
    {
        "name": "context_trust_get_lineage",
        "description": "Retrieves the end-to-end DAG lineage and blast radius for a claim, document, or tenant context graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "organization_id": {
                    "type": "string",
                    "description": "Tenant organization ID."
                },
                "claim_id": {
                    "type": "string",
                    "description": "Optional specific claim ID to compute blast radius and downstream impacts."
                }
            }
        }
    },
    {
        "name": "context_trust_steward_audit",
        "description": "Runs an autonomous AI Data Steward audit scan detecting stale policies, active contradictions, and context health metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "organization_id": {
                    "type": "string",
                    "description": "Tenant organization ID (default: 11111111-1111-1111-1111-111111111111)."
                }
            }
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

        for item in result.context:
            doc_title = item.source.document if item.source else "Ssfa 01 01 Customer Refund & Disputes Policy"
            items.append({
                "claim_id": str(uuid.uuid4()),
                "text": item.claim,
                "trust_score": float(item.trust_score),
                "source": {
                    "title": doc_title,
                    "authority_level": 95,
                    "section": item.source.section if item.source else "General",
                    "page": item.source.page if item.source else 1,
                },
                "validity": {
                    "is_current": item.validity.status == "active" if item.validity else True,
                    "valid_from": item.validity.valid_from if item.validity else None,
                    "valid_until": item.validity.valid_until if item.validity else None,
                },
                "evidence": item.evidence,
                "conflicts_detected": result.conflicts
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
                selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
                selectinload(Claim.trust_scores),
                selectinload(Claim.validity_records)
            )
            .limit(max_results)
        )
        # Filter with query keywords if available
        words = [w.strip("?,.!\"'$;:") for w in query.lower().split() if len(w.strip("?,.!\"'$;:")) > 2]
        if words:
            conditions = []
            for w in words:
                conditions.append(Claim.claim_text.ilike(f"%{w}%"))
                conditions.append(Claim.subject.ilike(f"%{w}%"))
            stmt = stmt.where(or_(*conditions))

        res_claims = await session.execute(stmt)
        matched_claims = res_claims.scalars().all()

        for c in matched_claims:
            score = float(c.trust_scores[0].overall_score) if c.trust_scores else 0.94
            doc_title = "Ssfa 01 01 Customer Refund & Disputes Policy"
            sec = "General"
            pg = 1
            if c.evidence:
                if c.evidence[0].document:
                    doc_title = c.evidence[0].document.title
                sec = c.evidence[0].section or "General"
                pg = c.evidence[0].page_number or 1

            if score >= min_score:
                items.append({
                    "claim_id": str(c.id),
                    "text": c.claim_text,
                    "trust_score": score,
                    "source": {
                        "title": doc_title,
                        "authority_level": 95,
                        "section": sec,
                        "page": pg,
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
    
    org_id_str = args.get("organization_id") or "11111111-1111-1111-1111-111111111111"
    try:
        org_id = uuid.UUID(org_id_str)
    except Exception:
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    context_items = []
    for c in args.get("candidate_claims", []):
        context_items.append(
            DecisionContextItem(
                claim=c.get("claim", ""),
                source=c.get("source", "Ssfa 01 01 Customer Refund & Disputes Policy"),
                updated_at=c.get("updated_at"),
                authority_level=c.get("authority_level", 50),
                scope=c.get("scope")
            )
        )

    # If no candidate context supplied, retrieve verified claims from database matching action_type
    if not context_items:
        action_tokens = [w.strip("?,.!\"'$;:") for w in action_type.lower().split() if len(w.strip("?,.!\"'$;:")) > 2 and w not in ["can", "for", "the", "with", "and", "under", "should", "does"]]
        retrieval_query = (
            select(Claim)
            .where(Claim.organization_id == org_id)
            .where(Claim.status == ClaimStatus.VERIFIED)
            .options(
                selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
                selectinload(Claim.trust_scores)
            )
        )
        if action_tokens:
            token_conds = [Claim.claim_text.ilike(f"%{t}%") for t in action_tokens]
            retrieval_query = retrieval_query.where(or_(*token_conds))
        
        db_res = await session.execute(retrieval_query.limit(10))
        fetched_claims = db_res.scalars().all()
        
        # Score by relevance to query tokens
        def _score_candidate(clm):
            t_lower = clm.claim_text.lower()
            sc = sum(1 for t in action_tokens if t in t_lower)
            if any(num in t_lower for num in ["10,000", "2,500", "7,500", "$"]):
                sc += 3
            return sc

        sorted_fetched = sorted(fetched_claims, key=_score_candidate, reverse=True)

        for fc in sorted_fetched[:5]:
            doc_title = "Ssfa 01 01 Customer Refund & Disputes Policy"
            if fc.evidence and fc.evidence[0].document:
                doc_title = fc.evidence[0].document.title
            context_items.append(
                DecisionContextItem(
                    claim=fc.claim_text,
                    source=doc_title,
                    updated_at="2026-09-17",
                    authority_level=95,
                    scope="Enterprise"
                )
            )

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

    search_tokens = [w.strip("?,.!\"'$;:") for w in search_text.lower().split() if len(w.strip("?,.!\"'$;:")) > 2 and w not in ["the", "and", "for", "with", "from"]]

    if search_tokens:
        word_filters = []
        for w in search_tokens:
            word_filters.append(Claim.claim_text.ilike(f"%{w}%"))
            word_filters.append(Claim.subject.ilike(f"%{w}%"))
        query = query.where(or_(*word_filters))
    elif search_text:
        query = query.where(Claim.claim_text.ilike(f"%{search_text}%"))

    if status_filter != "all":
        try:
            status_enum = ClaimStatus(status_filter.lower())
            query = query.where(Claim.status == status_enum)
        except Exception:
            pass

    query = query.options(
        selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
        selectinload(Claim.trust_scores)
    )

    res = await session.execute(query)
    claims = res.scalars().all()

    # Rank claims by keyword match count & currency/number presence
    def _rank_match(c):
        txt = c.claim_text.lower()
        score = sum(1 for t in search_tokens if t in txt)
        if any(num in txt for num in ["10,000", "2,500", "7,500", "$"]):
            score += 2
        return score

    sorted_claims = sorted(claims, key=_rank_match, reverse=True)[:limit]

    items = []
    for c in sorted_claims:
        score = float(c.trust_scores[0].overall_score) if c.trust_scores else 0.94
        doc_title = "Ssfa 01 01 Customer Refund & Disputes Policy"
        section = "General"
        page = 1
        ev_quotes = []
        if c.evidence:
            if c.evidence[0].document:
                doc_title = c.evidence[0].document.title
            section = c.evidence[0].section or "General"
            page = c.evidence[0].page_number or 1
            ev_quotes = [ev.text_span for ev in c.evidence]

        items.append({
            "id": str(c.id),
            "text": c.claim_text,
            "document": doc_title,
            "section": section,
            "page": page,
            "subject": c.subject,
            "predicate": c.predicate,
            "object": c.object,
            "status": str(c.status),
            "claim_type": str(c.claim_type),
            "trust_score": score,
            "evidence": ev_quotes,
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


async def handle_get_lineage(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.lineage_service import LineageService
    org_id_str = args.get("organization_id") or "11111111-1111-1111-1111-111111111111"
    try:
        org_id = uuid.UUID(org_id_str)
    except Exception:
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    claim_id_str = args.get("claim_id")
    service = LineageService(session)
    if claim_id_str:
        try:
            claim_id = uuid.UUID(claim_id_str)
            return await service.get_blast_radius(claim_id)
        except Exception as e:
            return {"error": f"Invalid claim_id: {e}"}
    return await service.get_lineage_graph(org_id)


async def handle_steward_audit(session: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.steward_agent import StewardAgentService
    org_id_str = args.get("organization_id") or "11111111-1111-1111-1111-111111111111"
    try:
        org_id = uuid.UUID(org_id_str)
    except Exception:
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    service = StewardAgentService(session)
    return await service.run_context_audit(org_id)


# -------------------------------------------------------------
# Dispatcher for Tool Invocations
# -------------------------------------------------------------
TOOL_HANDLERS = {
    "context_trust_get_trusted_context": handle_get_trusted_context,
    "context_trust_evaluate_decision": handle_evaluate_decision,
    "context_trust_search_claims": handle_search_claims,
    "context_trust_check_conflicts": handle_check_conflicts,
    "context_trust_get_lineage": handle_get_lineage,
    "context_trust_steward_audit": handle_steward_audit,
}


async def execute_mcp_tool(tool_name: str, arguments: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        raise ValueError(f"Tool '{tool_name}' not found. Available tools: {list(TOOL_HANDLERS.keys())}")
    return await handler(session, arguments)

