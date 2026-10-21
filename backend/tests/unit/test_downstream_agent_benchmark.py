"""
Unit tests for Downstream Agent Benchmark Engine (Sprint AF-12).
Validates:
1. Benchmark suite size and distribution (175 total: 75 Contracts, 50 Policies, 50 Billing).
2. Question types coverage (factual, conditional, synthesis, negative, adversarial).
3. 3-way comparative evaluation (Raw Claims vs Clause-Only vs Canonical Claims v3.0).
4. McNemar's paired statistical significance computation (p < 0.01).
"""

import pytest
from app.evaluation.downstream_agent_benchmark import (
    DownstreamAgentBenchmark,
    DocumentFamily,
    QuestionType,
    RetrievalBaseline,
    BaselineMetrics,
)


def test_benchmark_suite_size_and_distribution():
    questions = DownstreamAgentBenchmark.generate_benchmark_suite()
    assert len(questions) == 175

    contracts = [q for q in questions if q.family == DocumentFamily.CONTRACTS]
    policies = [q for q in questions if q.family == DocumentFamily.POLICIES_COMPLIANCE]
    billing = [q for q in questions if q.family == DocumentFamily.BILLING_INVOICES]

    assert len(contracts) == 75
    assert len(policies) == 50
    assert len(billing) == 50


def test_question_types_coverage():
    questions = DownstreamAgentBenchmark.generate_benchmark_suite()
    types_found = {q.question_type for q in questions}

    assert QuestionType.FACTUAL_LOOKUP in types_found
    assert QuestionType.CONDITIONAL_RULE in types_found
    assert QuestionType.MULTI_CLAUSE_SYNTHESIS in types_found
    assert QuestionType.NEGATIVE_UNSTATED in types_found
    assert QuestionType.ADVERSARIAL_TRAP in types_found


def test_run_benchmark_and_comparative_superiority():
    metrics, questions, all_results = DownstreamAgentBenchmark.run_benchmark()

    raw_m = metrics[RetrievalBaseline.RAW_CLAIMS]
    clause_m = metrics[RetrievalBaseline.CLAUSE_ONLY]
    v3_m = metrics[RetrievalBaseline.CANONICAL_CLAIMS_V3]

    # Verify 175 evaluated in all baselines
    assert raw_m.total_questions == 175
    assert clause_m.total_questions == 175
    assert v3_m.total_questions == 175

    # Target release standards for v3.0
    assert v3_m.correctness_rate_pct >= 90.0
    assert v3_m.citation_accuracy_pct >= 95.0
    assert v3_m.hallucination_rate_pct <= 5.0
    assert v3_m.contradiction_rate_pct == 0.0
    assert v3_m.refusal_accuracy_pct >= 95.0

    # Verify superiority over baselines
    assert v3_m.correctness_rate_pct > clause_m.correctness_rate_pct
    assert v3_m.correctness_rate_pct > raw_m.correctness_rate_pct
    assert v3_m.hallucination_rate_pct < clause_m.hallucination_rate_pct
    assert v3_m.hallucination_rate_pct < raw_m.hallucination_rate_pct

    # Statistical significance vs Clause-Only baseline
    assert v3_m.p_value_vs_clause_only is not None
    assert v3_m.p_value_vs_clause_only < 0.01


def test_mcnemar_statistical_test():
    from app.evaluation.downstream_agent_benchmark import AgentEvaluationResult

    # Perfect agreement -> p = 1.0
    res_a = [
        AgentEvaluationResult(
            question_id=f"Q{i}",
            baseline=RetrievalBaseline.CANONICAL_CLAIMS_V3,
            family=DocumentFamily.CONTRACTS,
            question_type=QuestionType.FACTUAL_LOOKUP,
            retrieved_context_summary="ctx",
            generated_answer="ans",
            is_correct=True,
            citation_correct=True,
            is_hallucination=False,
            is_contradiction=False,
            refusal_correct=True,
        )
        for i in range(50)
    ]
    p_identical = DownstreamAgentBenchmark.compute_mcnemar_p_value(res_a, res_a)
    assert p_identical == 1.0

    # Significant discordance -> p < 0.01
    res_discordant = [
        AgentEvaluationResult(
            question_id=f"Q{i}",
            baseline=RetrievalBaseline.CLAUSE_ONLY,
            family=DocumentFamily.CONTRACTS,
            question_type=QuestionType.FACTUAL_LOOKUP,
            retrieved_context_summary="ctx",
            generated_answer="ans",
            is_correct=(i >= 30),  # Wrong on first 30
            citation_correct=(i >= 30),
            is_hallucination=(i < 30),
            is_contradiction=False,
            refusal_correct=True,
        )
        for i in range(50)
    ]
    p_sig = DownstreamAgentBenchmark.compute_mcnemar_p_value(res_a, res_discordant)
    assert p_sig < 0.001
