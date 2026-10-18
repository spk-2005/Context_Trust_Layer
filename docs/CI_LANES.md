# Continuous Integration & Layered Testing Lanes

Context Layer AI utilizes a 4-tier layered testing pyramid to deliver sub-second feedback for developers while maintaining certification-grade rigor for enterprise compliance.

---

## Testing Lane Matrix

| Lane | Time Budget | Frequency & Trigger | Scope | Executed Command |
|---|---|---|---|---|
| **1. Fast Developer Lane** | **< 15 seconds** (Typical: < 2s) | On save, pre-commit, interactive shell | Isolated Golden Micro-Fixtures (indemnity clauses, table rows, fused headings, merged cells) | `pytest -m fast` |
| **2. PR / Integration Lane** | **< 5 minutes** (Typical: < 45s) | Pull Request creation and updates | Smart Test Router diff check, all backend unit tests, active benchmark slice (DOC-005, DOC-009) | `python scripts/test_runner.py` |
| **3. Nightly Lane** | **< 30 minutes** (Typical: ~5m) | Nightly schedule on `main` | All 9 evaluation documents (DOC-001 through DOC-009), 400+ backend tests, pipeline cache regression audit | `python research/evaluation/benchmark_harness.py --profile full` |
| **4. Certification Lane** | **Release Gating** | Release Candidate (RC) tag, production deployment gate | Full corpus evaluation, cryptographic manifest integrity, 8-stage lifecycle provenance guard, sealed holdout evaluation | `python research/evaluation/benchmark_harness.py --profile certify` |

---

## 1. Fast Developer Lane

- **Purpose**: Immediate regression detection on extractor regexes, deontic classifiers, subject normalizers, and table cell parsers without re-running full PDF parsing or OCR.
- **Fixtures Directory**: `backend/tests/fixtures/golden_micro/`
  - `contracts/indemnity_covenant.json`
  - `contracts/interest_rate_clause.json`
  - `policies/refund_matrix_row.json`
  - `policies/inline_fused_heading.json`
  - `policies/photo_id_requirement.json`
  - `policies/gift_receipt_rule.json`
  - `policies/ambiguous_table_merged_cell.json`
  - `invoices/line_item_subtotal.json`
- **Execution**:
  ```bash
  pytest -m fast
  ```

---

## 2. Content-Addressed Pipeline Caching

- **Mechanism**: `PipelineStageCache` (in `backend/app/caching/pipeline_cache.py`) uses a 4-factor cryptographic SHA-256 key:
  $$\text{Key} = \text{SHA256}(\text{source\_sha256} + \text{parser\_version} + \text{parser\_config\_hash} + \text{normalizer\_version})$$
- **Cache Location**: `.pipeline_cache/` (git-ignored)
- **Invalidation Invariants**:
  - Changing source document bytes $\to$ automatic miss.
  - Incrementing parser code version $\to$ automatic miss.
  - Toggling OCR or table extraction flags $\to$ automatic miss.
  - Incrementing normalizer code version $\to$ automatic miss.
  - Corrupted cache payloads safely evict and recompute without crashing.
- **Bypass / Force Refresh**:
  ```bash
  export CONTEXT_LAYER_NO_CACHE=1
  # or pass --no-cache to benchmark_harness.py
  ```

---

## 3. Asynchronous Blinded Dual-Human Adjudication

- **Protocol**: Disassociates human adjudication from CI and pre-commit hooks to eliminate developer lag.
- **Independence & Anti-Bias Guarantees**:
  - Zero automated reviewer IDs allowed in `reviewer_1` or `reviewer_2`.
  - Reviewer B is strictly blinded to Reviewer A's disposition.
  - If Reviewer A and Reviewer B agree $\to$ status advances to `READY_FOR_CERTIFICATION`.
  - If Reviewer A and Reviewer B disagree $\to$ status escalates to an independent third-party `Adjudicator`.
  - Dedicated governance officer action (`scripts/review_queue.py certify`) is required to promote into `adjudications.json`.
- **Authoritative 8-State Taxonomy** (`AdjudicationDisposition`):
  1. `CORRECT_FULL_MATCH`
  2. `ACCEPTED_PARTIAL_MATCH`
  3. `INCORRECT`
  4. `MALFORMED`
  5. `DUPLICATE`
  6. `NON_CANONICAL`
  7. `GOLD_LABEL_GAP`
  8. `AMBIGUOUS_NEEDS_REVIEW`
- **CLI Commands**:
  ```bash
  # View queue (blinded)
  python scripts/review_queue.py list --reviewer annotator_b

  # Submit review
  python scripts/review_queue.py review --id QUEUE-DOC-005-xxxx --reviewer annotator_a --disposition GOLD_LABEL_GAP --rationale "..."

  # Adjudicate disagreement
  python scripts/review_queue.py adjudicate --id QUEUE-DOC-005-xxxx --adjudicator lead_specialist --disposition ACCEPTED_PARTIAL_MATCH --rationale "..."

  # Promote to certified record
  python scripts/review_queue.py certify --id QUEUE-DOC-005-xxxx --officer governance_lead
  ```

---

## 4. Operational Governance Rule

**Zero Unrequested Git Writes**: Automation agents must never run `git commit` or `git push` without an explicit, current-turn user instruction.