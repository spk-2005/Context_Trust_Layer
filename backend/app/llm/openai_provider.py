import json
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


class LLMClaimExtractionOutput(BaseModel):
    claims: list[ExtractedClaim]


class LLMContradictionOutput(BaseModel):
    is_contradiction: bool
    conflict_type: str
    severity: str
    confidence: float
    reasoning: str


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider using AsyncOpenAI for Claim Extraction, Embeddings, and Contradiction evaluation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
    ):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.embedding_model = embedding_model or settings.openai_embedding_model
        self.client = AsyncOpenAI(api_key=self.api_key)

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

    async def get_embedding(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return response.data[0].embedding

    async def get_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=list(texts),
        )
        return [item.embedding for item in response.data]

    async def evaluate_contradiction(
        self,
        claim_a_text: str,
        claim_b_text: str,
    ) -> ContradictionResult:
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

        return ContradictionResult(
            is_contradiction=False,
            conflict_type="compatible",
            severity="low",
            confidence=0.5,
            reasoning="Unable to parse contradiction output.",
        )
