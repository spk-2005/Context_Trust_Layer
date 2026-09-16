import json
import logging
from typing import Sequence

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.schemas import (
    ClaimExtractionResult,
    ContradictionResult,
    ExtractedClaim,
)

logger = logging.getLogger(__name__)


class LLMClaimExtractionOutput(BaseModel):
    claims: list[ExtractedClaim]


class LLMContradictionOutput(BaseModel):
    is_contradiction: bool
    conflict_type: str
    severity: str
    confidence: float
    reasoning: str


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API & OpenAI-Compatible Gateway Provider (OpenRouter, Ox Alpha, Groq, etc.)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        default_headers: dict[str, str] | None = None,
    ):
        self.api_key = api_key or settings.openai_api_key or settings.openrouter_api_key or "sk-dummy"
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model
        self.embedding_model = embedding_model or settings.openai_embedding_model
        
        client_kwargs: dict = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        if default_headers:
            client_kwargs["default_headers"] = default_headers

        self.client = AsyncOpenAI(**client_kwargs)

    async def extract_claims(
        self,
        document_title: str,
        section_title: str,
        section_content: str,
    ) -> ClaimExtractionResult:
        system_prompt = (
            "You are a knowledge provenance and claim extraction specialist. "
            "Extract all atomic, verifiable factual statements and policy rules from the text into "
            "Subject-Predicate-Object triplets. Include the EXACT substring span from the text as evidence."
        )

        user_prompt = (
            f"Document Title: {document_title}\n"
            f"Section Header: {section_title}\n\n"
            f"Content:\n{section_content}"
        )

        # 1. Attempt OpenAI structured output parsing
        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=LLMClaimExtractionOutput,
                temperature=0.0,
            )
            parsed = response.choices[0].message.parsed
            claims = parsed.claims if parsed else []
            return ClaimExtractionResult(
                claims=claims,
                extraction_model=self.model,
                extraction_method="openai_structured_outputs",
            )
        except Exception as parse_err:
            logger.debug("Structured parse unsupported or failed (%s); trying standard JSON mode", parse_err)

        # 2. Fallback to standard chat completion with JSON mode (compatible with OpenRouter / Ox Alpha)
        try:
            json_system_prompt = (
                f"{system_prompt}\n\n"
                "Return ONLY a valid JSON object with key 'claims': "
                '[{"subject": "...", "predicate": "...", "object": "...", '
                '"claim_text": "...", "claim_type": "policy|technical|financial|metric|compliance", '
                '"confidence": 0.95, "exact_span": "exact substring"}]'
            )
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": json_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            raw_claims = data.get("claims", [])
            claims = [ExtractedClaim(**c) for c in raw_claims]
            return ClaimExtractionResult(
                claims=claims,
                extraction_model=self.model,
                extraction_method="openai_json_mode",
            )
        except Exception as json_err:
            logger.warning("JSON mode extraction failed (%s); falling back to rule extractor", json_err)
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().extract_claims(document_title, section_title, section_content)

    async def get_embedding(self, text: str) -> list[float]:
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as emb_err:
            logger.debug("Embedding endpoint unavailable (%s); using deterministic vector", emb_err)
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().get_embedding(text)

    async def get_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=list(texts),
            )
            return [item.embedding for item in response.data]
        except Exception as emb_err:
            logger.debug("Embeddings batch endpoint unavailable (%s); using deterministic vectors", emb_err)
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().get_embeddings(texts)

    async def evaluate_contradiction(
        self,
        claim_a_text: str,
        claim_b_text: str,
    ) -> ContradictionResult:
        # Fast local evaluation for illustrative examples, metadata headers, and temporal updates
        from app.llm.mock_provider import MockLLMProvider
        mock_eval = await MockLLMProvider().evaluate_contradiction(claim_a_text, claim_b_text)
        if not mock_eval.is_contradiction or mock_eval.conflict_type in ("illustrative_example", "temporal_outdated"):
            return mock_eval

        system_prompt = (
            "You are a logic and contradiction analysis engine. "
            "Evaluate whether Claim A and Claim B contradict each other, state conflicting requirements, "
            "or represent numerical discrepancies on the same topic."
        )

        user_prompt = (
            f"Claim A: {claim_a_text}\n"
            f"Claim B: {claim_b_text}\n\n"
            "Analyze if they contradict or disagree."
        )

        # 1. Attempt OpenAI structured output parsing
        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=LLMContradictionOutput,
                temperature=0.0,
            )
            parsed = response.choices[0].message.parsed
            if parsed:
                return ContradictionResult(
                    is_contradiction=parsed.is_contradiction,
                    conflict_type=parsed.conflict_type,
                    severity=parsed.severity,
                    confidence=parsed.confidence,
                    reasoning=parsed.reasoning,
                )
        except Exception as parse_err:
            logger.debug("Contradiction structured parse failed (%s); trying standard JSON mode", parse_err)

        # 2. Fallback to standard chat completion with JSON mode
        try:
            json_system_prompt = (
                f"{system_prompt}\n\n"
                "Return ONLY a valid JSON object matching: "
                '{"is_contradiction": bool, "conflict_type": "direct_contradiction|numerical_discrepancy|temporal_outdated|compatible", '
                '"severity": "high|medium|low", "confidence": 0.90, "reasoning": "one sentence explanation"}'
            )
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": json_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return ContradictionResult(
                is_contradiction=bool(data.get("is_contradiction", False)),
                conflict_type=str(data.get("conflict_type", "compatible")),
                severity=str(data.get("severity", "low")),
                confidence=float(data.get("confidence", 0.85)),
                reasoning=str(data.get("reasoning", "Evaluated via JSON mode.")),
            )
        except Exception as json_err:
            logger.debug("JSON mode contradiction eval failed (%s); using rule evaluator", json_err)
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().evaluate_contradiction(claim_a_text, claim_b_text)

    async def generate_grounded_answer(
        self,
        query: str,
        citations: list[dict],
        has_conflicts: bool = False,
        warnings: list[str] | None = None,
    ) -> str:
        """Synthesize a natural language, factual answer using the model."""
        if not citations:
            return (
                f'No verified claims or policies matching "{query}" were found in the current organization knowledge base. '
                "Please ingest the relevant documentation or connect enterprise data sources."
            )

        # Sanitize and format verified citations
        sanitized_citations = []
        for idx, c in enumerate(citations[:5]):
            text = c.get('claim_text', '').strip()
            if text.startswith("{") or '"connectors":' in text or "synthetic" in text.lower():
                continue
            if len(text) > 300:
                text = text[:300].rsplit(" ", 1)[0] + "..."
            sanitized_citations.append(
                f"[{idx + 1}] {text} (Source: {c.get('source_title', 'Knowledge Base')} > {c.get('section', 'General')}, Trust Score: {int(float(c.get('trust_score', 0.8))*100)}%)"
            )

        citations_context = "\n".join(sanitized_citations) if sanitized_citations else "No specific text excerpts available."

        warning_context = ""
        if warnings:
            warning_context = "\n⚠️ Potential Policy Discrepancies / Conflicts:\n" + "\n".join(f"- {w}" for w in warnings)

        system_prompt = (
            "You are Context Trust Layer Copilot, an enterprise governance intelligence assistant. "
            "Formulate a direct, authoritative, and concise answer (2 to 4 sentences maximum) directly answering the user's inquiry. "
            "Use ONLY the provided verified citations. "
            "State specific numbers, dollar thresholds, windows, or conditions clearly. "
            "Explicitly reference whether the cited policy is an active current rule or if there are conflicts. "
            "DO NOT output raw JSON, code blocks, or repeat whole file schemas. Be crisp, professional, and concise."
        )

        user_prompt = (
            f"User Question: {query}\n\n"
            f"Verified Enterprise Claims:\n{citations_context}\n"
            f"{warning_context}\n\n"
            "Please provide a concise, authoritative answer for the user."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            content = response.choices[0].message.content
            if content and len(content.strip()) > 10:
                return content.strip()
        except Exception as chat_err:
            logger.warning("LLM answer synthesis failed (%s); using template synthesis", chat_err)

        from app.llm.mock_provider import MockLLMProvider
        return await MockLLMProvider().generate_grounded_answer(query, citations, has_conflicts, warnings)

