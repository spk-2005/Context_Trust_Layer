# Context Layer AI - Sealed Holdout Evaluation Report (Sprint X)

**Evaluation Date:** 2026-10-17 11:13:32 UTC  
**Evaluation Standard:** Sealed Out-of-Distribution Single-Pass Assessment (Sprint X)  
**Corpus Scope:** 15 Unseen Enterprise Documents (200 Gold Canonical Rules across 5 Domains)  
**Harness Version at Evaluation:** `3.2.0` | **Commit:** `66183a8` | **Matches Current Harness:** `true`  
**No-Tuning Attestation:** Certified that the sealed holdout corpus was evaluated exactly once against the frozen Sprint X benchmark harness without hyperparameter adjustment, post-hoc threshold tuning, or gold-label inspection.  

---

## 1. Executive Summary & Dual-Gate Assessment

| Metric | Target Standard | Holdout Result | Gate Assessment |
| :--- | :---: | :---: | :---: |
| **Full-Match Recall** | Baseline Transfer | **69.00% (138/200)** | **Production Gate FAIL (< 90.0%)** |
| **Partial-Match Recall** | Diagnostic | **81.00% (162/200)** | **ROBUST DISCOVERY** |
| **Lower-Bound Precision** | Raw Denominator | **55.65% (138/248)** | **UNREVIEWED PENALTY** |
| **Adjudicated Validity Precision** | Human Review Standard | **86.29% (214/248)** | **Pilot Gate PASS (>= 80.0%)** |
| **Canonical Full-Match $F_1$** | Paired Harmonic Mean | **61.61%** | **SOLID BASELINE** |
| **Subject Accuracy** | $\ge 95.0\%$ | **98.50%** | **PASSED** |
| **Malformed Fragment Rate** | $\equiv 0.0\%$ | **0.00%** | **PASSED** |
| **Evidence Traceability** | $\equiv 100.0\%$ | **100.00%** | **PASSED** |

### Dual Gate Certification Verdict:
1. **Pilot-Readiness Gate: PASSED**. High semantic fidelity (86.29% adjudicated precision, 0.00% malformed fragments, 100% evidence traceability) confirms out-of-distribution safety for human-in-the-loop workflows.
2. **Production-Readiness Gate: NEEDS_WORK (BLOCKED)**. Holdout full-match recall (69.00% < 90.0%) confirms that general autonomous execution across unseen enterprise documents must remain strictly blocked.

---

## 2. Per-Domain Generalization Breakdown

| Business Domain | Documents | Gold Canonical | Full Matches | Full Recall | Lower Prec | Adjudicated Prec |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Financial Invoices** | 3 (`HOLD-001` - `003`) | 16 | 13 | **81.25%** | 68.42% | 94.74% |
| **HR & Separation Policies** | 3 (`HOLD-004` - `006`) | 36 | 28 | **77.78%** | 60.87% | 91.30% |
| **Commercial Procurement Contracts** | 3 (`HOLD-007` - `009`) | 58 | 38 | **65.52%** | 52.78% | 84.72% |
| **Regulatory Directives** | 3 (`HOLD-010` - `012`) | 26 | 20 | **76.92%** | 58.82% | 88.24% |
| **Warranty & Return Matrices** | 3 (`HOLD-013` - `015`) | 64 | 39 | **60.94%** | 49.37% | 81.01% |

---

## 3. Failure Mode Taxonomy Distribution

Missed rules across the holdout corpus partition as follows:
- **Table Structure Errors**: 18 misses (nested multi-column cells and span grouping)
- **Predicate Mapping Errors**: 14 misses (domain-specific contractual verbs)
- **Object Extraction Misses**: 12 misses (unit conversion and complex temporal spans)
- **Sentence Split Errors**: 10 misses (long compound conditional sentences)
- **Modality Contradictions**: 4 misses
- **Subject Resolution Errors**: 4 misses

---

## 4. Cryptographic Provenance Anchors
Anchored in holdout manifest SHA-256 `903135d7a1074b2db3fc77f7ff5b6c198eef39e8629f2ce1233f0f64f4a31112`.
