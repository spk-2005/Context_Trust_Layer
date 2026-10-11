"""
Layer 5: Candidate Extraction & Source-Aware Verification Package.
"""

from app.extraction.models import (
    CandidateClaim,
    CompletenessLedgerRecord,
    ExtractionStrategyType,
    Layer5ExtractionResult,
)
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.strategy_router import StrategyRouter
from app.extraction.completeness_ledger import CompletenessLedger
from app.extraction.pipeline import Layer5ExtractionPipeline, global_extraction_pipeline

__all__ = [
    "CandidateClaim",
    "CompletenessLedgerRecord",
    "ExtractionStrategyType",
    "Layer5ExtractionResult",
    "CandidateDiscoveryEngine",
    "StrategyRouter",
    "CompletenessLedger",
    "Layer5ExtractionPipeline",
    "global_extraction_pipeline",
]
