import hashlib, json, logging, math, re
from typing import Sequence
import httpx
from app.llm.base import BaseLLMProvider
from app.llm.schemas import ClaimExtractionResult, ContradictionResult, ExtractedClaim

logger = logging.getLogger(__name__)

_CLAIM_PROMPT = (
    'Extract atomic claims from the text below as JSON: {{"claims": [...]}}. '
    "Each claim must have: claim_text, subject, predicate, object, "
    "claim_type (policy|technical|financial|metric|compliance), "
    "confidence (0.0-1.0), evidence_text_span.\n"
    "Rules: one fact per claim, preserve exact numbers, NO extra text, ONLY valid JSON.\n\n"
    "Title: {document_title} | Section: {section_title}\n"
    "Text: {section_content}\n"
)

_CONTRA_PROMPT = (
    "Do these two claims contradict? Reply ONLY with JSON:\n"
    '{{"is_contradiction":bool,"conflict_type":"direct_contradiction|numerical_discrepancy|temporal_outdated|complementary|compatible",'
    '"severity":"high|medium|low","confidence":float,"reasoning":"one sentence"}}\n\n'
    "A: {claim_a}\nB: {claim_b}\n"
)


def _hash_emb(text: str, dim: int = 1536) -> list[float]:
    vec = [0.0] * dim
    words = re.findall(r"\w+", text.lower())
    if not words:
        vec[0] = 1.0
        return vec
    for w in words:
        h = int(hashlib.md5(w.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm > 0 else vec


def _sf(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def _ss(v, d=""):
    return str(v) if v is not None else d


class OllamaProvider(BaseLLMProvider):
    """Real LLM provider backed by a local Ollama server."""

    def __init__(self):
        from app.core.config import settings
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.emb_model = settings.ollama_embedding_model
        self.timeout = settings.ollama_timeout
        self.embedding_dim = 1536
        logger.info("OllamaProvider ready  model=%s  url=%s", self.model, self.base_url)

    async def _chat(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Output valid JSON only. Do not output thinking or markdown formatting."},
                        {"role": "user", "content": prompt}
                    ],
                    "format": "json",
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_ctx": 2048,
                        "num_predict": 512,
                    },
                },
            )
            r.raise_for_status()
        return r.json()["message"]["content"].strip()

    @staticmethod
    def _clean(raw: str) -> str:
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
        return raw.strip()

    async def extract_claims(
        self, document_title: str, section_title: str, section_content: str
    ) -> ClaimExtractionResult:
        empty = ClaimExtractionResult(
            claims=[], extraction_model=self.model, extraction_method="ollama_json_extraction"
        )
        if not (section_content or "").strip():
            return empty
        prompt = _CLAIM_PROMPT.format(
            document_title=document_title,
            section_title=section_title or "General",
            section_content=section_content,
        )
        raw = ""
        try:
            raw = self._clean(await self._chat(prompt))
            data = json.loads(raw)
            if isinstance(data, dict):
                rows = data.get("claims") or data.get("data") or [data]
            elif isinstance(data, list):
                rows = data
            else:
                rows = []
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning("Ollama extract_claims network error: %s", e)
            return empty
        except json.JSONDecodeError:
            logger.warning("Ollama extract_claims non-JSON (model=%s): %s", self.model, raw[:400])
            return empty

        claims = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            ct = _ss(item.get("claim_text") or item.get("claim") or item.get("statement") or item.get("text")).strip()
            if not ct:
                continue
            claims.append(
                ExtractedClaim(
                    claim_text=ct,
                    subject=_ss(item.get("subject") or "Unknown")[:250],
                    predicate=_ss(item.get("predicate") or "specifies")[:250],
                    object=_ss(item.get("object") or ct),
                    claim_type=_ss(item.get("claim_type") or "policy"),
                    confidence=_sf(item.get("confidence"), 0.90),
                    evidence_text_span=_ss(item.get("evidence_text_span") or ct),
                )
            )
        logger.info("OllamaProvider extracted %d claims from section '%s'", len(claims), section_title)
        return ClaimExtractionResult(
            claims=claims, extraction_model=self.model, extraction_method="ollama_json_extraction"
        )

    async def get_embedding(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.emb_model, "prompt": text},
                )
            if r.status_code == 200:
                emb = r.json().get("embedding", [])
                if emb:
                    return emb
        except (httpx.RequestError, httpx.HTTPStatusError):
            pass
        return _hash_emb(text, self.embedding_dim)

    async def get_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        return [await self.get_embedding(t) for t in texts]

    async def evaluate_contradiction(
        self, claim_a_text: str, claim_b_text: str
    ) -> ContradictionResult:
        prompt = _CONTRA_PROMPT.format(claim_a=claim_a_text, claim_b=claim_b_text)
        raw = ""
        try:
            raw = self._clean(await self._chat(prompt))
            data = json.loads(raw)
            return ContradictionResult(
                is_contradiction=bool(data.get("is_contradiction", False)),
                conflict_type=_ss(data.get("conflict_type", "compatible")),
                severity=_ss(data.get("severity", "low")),
                confidence=_sf(data.get("confidence"), 0.85),
                reasoning=_ss(data.get("reasoning", "No reasoning.")),
            )
        except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError) as e:
            logger.debug("Ollama contradiction eval fallback due to: %s", e)
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().evaluate_contradiction(claim_a_text, claim_b_text)

    async def generate_grounded_answer(
        self,
        query: str,
        citations: list[dict],
        has_conflicts: bool = False,
        warnings: list[str] | None = None,
    ) -> str:
        if not citations:
            return (
                f'No verified claims or policies matching "{query}" were found in the current organization knowledge base. '
                "Please ingest the relevant documentation or connect enterprise data sources."
            )
        claims_text = "\n".join(f"- {c.get('claim_text', '')} (Source: {c.get('source_title', 'Doc')})" for c in citations[:5])
        prompt = (
            f"You are Context Trust Layer AI Copilot. Answer the user's question using ONLY the provided verified claims.\n"
            f"User Question: {query}\n\n"
            f"Verified Claims:\n{claims_text}\n\n"
            f"Conflicts present: {has_conflicts}\n"
            "Provide a concise, direct, authoritative answer citing the sources."
        )
        try:
            ans = await self._chat(prompt)
            if ans and len(ans.strip()) > 10:
                return ans.strip()
        except Exception as e:
            logger.debug("Ollama chat completion fallback due to: %s", e)
        from app.llm.mock_provider import MockLLMProvider
        return await MockLLMProvider().generate_grounded_answer(query, citations, has_conflicts, warnings)

