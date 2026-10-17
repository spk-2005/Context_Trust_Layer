# Context Layer AI - Evaluation Contract (Version 1.0.0)

**Effective Date:** 2026-10-17  
**Scope:** Universal Document Intelligence Ground Truth Benchmark & Production Quality Gates  
**Status:** FROZEN & IMMUTABLE  

---

## 1. Core Principles & Antigravity Invariants

1. **Root-Cause Discipline**: No evaluation defect may be resolved by hardcoding document IDs, matching specific gold quotes, or injecting synthetic claims into test fixtures.
2. **Universality**: Every parser, extraction, and validation rule must operate on structural layout geometry, document types, and semantic schema contracts.
3. **Immutable Reference Standard**: Gold label sets, once certified, may only be updated via documented version diffs with dual-annotator consensus.
4. **Closed Candidate Accounting**: Every candidate approved by Layer 6 must be strictly partitioned with zero arithmetic drift:
   \\text{Approved L6} = \\text{Canonical Approved} + \\text{Duplicate Evidence Links} + \\text{Boilerplate} + \\text{Non-Canonical}
   \\text{Canonical Approved} = \\text{Correct Full Matches} + \\text{Partial Matches} + \\text{Unjudged Spans} + \\text{Incorrect / Malformed}

---

## 2. Match Tiers Definition

Every candidate claim evaluated against gold canonical ground truth must be deterministically classified into one of the following mutually exclusive tiers:

| Match Tier | Code | Definition | Admissibility to Production Gate |
| :--- | :--- | :--- | :---: |
| **Full Match** | FULL_MATCH | Exact semantic alignment on Subject, Predicate, Object (including numeric thresholds & units), Modality, and Evidence Grounding. | **YES** |
| **Partial Object Capture (Pending Review)** | PARTIAL_OBJECT_CAPTURE_PENDING_REVIEW | Matcher-derived partial capture where predicate/action aligns but parameter/unit requires human review. | **NO** (Pending Human Review) |
| **Accepted Partial Match** | ACCEPTED_PARTIAL_MATCH | Formally adjudicated partial match where human reviewer accepted parameter variance. | **CONDITIONAL** |
| **Wrong Predicate** | WRONG_PREDICATE | Subject and evidence span align, but predicate belongs to an incompatible semantic family. | **NO** |
| **Wrong Object / Contradiction** | WRONG_OBJECT | Predicate aligns, but numeric threshold or entity object contradicts ground truth. | **NO** |
| **Wrong Subject** | WRONG_SUBJECT | Predicate and object align, but subject was resolved to generic text, section number, or wrong entity. | **NO** |
| **Wrong Modality** | WRONG_MODALITY | Extracted deontic modality contradicts gold standard (e.g., extracted MAY for a gold MUST_NOT). | **NO** |
| **Missing Rule** | MISSING | Gold canonical rule was not extracted or not admitted into canonical approved claims. | **NO** |

---

## 3. Named Paired Metric Formulas

All metrics must use explicitly defined, paired populations to prevent denominator confusion:

\\text{Gold-Match Precision} = \\frac{\\text{Correct Full Matches}}{\\text{Canonical Approved Claims}}

\\text{Adjudicated Validity Precision} = \\frac{\\text{Adjudicated Valid Policy Claims}}{\\text{Canonical Approved Claims}}

\\text{Gold-Covered Precision} = \\frac{\\text{Correct Full Matches}}{\\text{Adjudicated Valid Claims}}

\\text{Execution-Ready Precision} = \\frac{\\text{Claims Certified for Autonomous Execution}}{\\text{Canonical Approved Claims}}

\\text{Full-Match Recall} = \\frac{\\text{Correct Full Matches}}{\\text{Total Gold Canonical Rules}}

\\text{Full-Match } F_1 = \\frac{2 \\cdot \\text{Gold-Match Precision} \\cdot \\text{Full-Match Recall}}{\\text{Gold-Match Precision} + \\text{Full-Match Recall}}

---

## 4. Two-Tier Systemic Quality Gates

To prevent confusion between pilot deployment under human review and fully autonomous execution, the evaluation standard strictly defines two separate, named gates:

### Gate 1: Pilot-Readiness Gate (Staged Deployment with Human Review)
*Standard for admitting a document or domain into supervised pilot deployment.*
1. **Adjudicated Validity Precision >= 80.0%**
2. **Malformed Fragment Rate == 0.0%**
3. **Evidence Span Traceability == 100.0%**

*Verdict under Pilot Gate*:
- **PASSED**: System exhibits robust semantic fidelity and zero structural corruption; safe for human-in-the-loop assisted workflow.
- **NEEDS_WORK**: System produces ungrounded or corrupt fragments; unsafe for pilot deployment.

### Gate 2: Production-Readiness Gate (Autonomous Unconditional Execution)
*Standard for admitting a document or domain into autonomous, unattended execution.*
1. **Full-Match Recall >= 90.0%**
2. **Adjudicated Validity Precision >= 90.0%**
3. **Canonical Full-Match F1 >= 90.0%**
4. **Subject Accuracy >= 95.0%**
5. **False Approval Rate <= 2.0%**
6. **False Conflict Rate <= 2.0%**
7. **Malformed Fragment Rate == 0.0%**
8. **Evidence Span Traceability == 100.0%**

*Document Verdicts under Production Gate*:
- **PASS (Unconditional Production Gate)**: Meets all 8 production thresholds.
- **CONDITIONAL_PASS (Staged Deployment Gate)**: Achieves Full-Match Recall >= 90.0%, Adjudicated Precision >= 85.0%, and Dual-Annotator Cohen's Kappa >= 0.85 with documented residual risk management.
- **NEEDS_WORK**: Fails to meet PASS or CONDITIONAL_PASS thresholds. Autonomous execution is blocked.

---

## 5. Sealed Holdout Evaluation Protocol & Gate Verdicts

1. The holdout corpus consists of **15 unseen enterprise documents** (200 gold canonical rules across 5 business domains) sealed in `research/holdout/`.
2. The holdout evaluation is executed **exactly once** on a frozen pipeline; zero post-hoc tuning is permitted.
3. **Dual Gate Assessment for Sealed Holdout**:
   - **Pilot-Readiness Gate**: **PASSED** (Adjudicated Precision = 86.29%, Malformed Rate = 0.00%, Traceability = 100.00%).
   - **Production-Readiness Gate**: **NEEDS_WORK (BLOCKED)** (Full-Match Recall = 69.00% < 90.0%, Adjudicated Precision = 86.29% < 90.0%). Autonomous execution across unseen enterprise documents is strictly blocked.
