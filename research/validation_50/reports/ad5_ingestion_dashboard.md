# Sprint AD-6: Controlled Ingestion Dashboard & Full Reconciliation Report
**Execution Timestamp**: `2026-10-18T06:05:00Z`  
**Governance Posture**: `STAGED_DUAL_HUMAN_ADJUDICATION_ACTIVE`  

## 1. Full Data Reconciliation Invariant (1,026 Total Claims)

Every single candidate claim discovered across the 21 active English documents is accounted for with zero mathematical discrepancies:

$$\text{Total Extracted (1,026)} = \text{Tier 1 Provisional (750)} + \text{Tier 2 Wave 2 (120)} + \text{Tier 3 Blocked (56)} + \text{Rejected (100)}$$

| Claim Lifecycle State | Count | Usable by Agent? | Current Storage / Pipeline Location |
|---|:---:|:---:|---|
| **`EXTRACTED`** (Discovered candidates) | **1,026** | No | Ingestion parser candidate units |
| **`PROVISIONAL`** (Tier 1 valid, shadow mode) | **750** | Shadow mode only | `research/validation_50/staged_ingestion/staged_provisional_claims.json` |
| **`TIER_2_WAVE_2`** (Near-threshold valid) | **120** | No | Held for Wave 2 calibration (`DOC-052`, `DOC-065`) |
| **`BLOCKED_TIER_3`** (Below 85% precision) | **56** | No | Gated from staging; requires 100% manual adjudication |
| **`REJECTED`** (Automated gate failures) | **100** | No | Audit ledger artifact (`research/validation_50/reports/failure_patterns.json`) |
| **`CERTIFIED`** (Dual-human review approved) | **155** | **Yes** | Certified staging ledger (`research/validation_50/staged_ingestion/certified_claims.json`) |

---

## 2. Corrected Tiering Matrix (Explicit Non-Overlapping Rules)

- **Tier 1 (`Precision >= 90.0%`)**: 14 Documents (100% precision or above gate; eligible for provisional shadow staging)
- **Tier 2 (`Precision 85.0% - 89.9%`)**: 2 Documents (near threshold; held for Wave 2 calibration)
- **Tier 3 (`Precision < 85.0%`)**: 5 Documents (blocked from automated staging)

| Tier | Doc ID | Filename | Document Type | Precision | Recall | Valid | Candidate | Ingestion Status |
|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|:---|
| **Tier 1** | `DOC-053` | GxP Microsoft Compliance | regulatory_compliance | 100.0% | 100.0% | 3 | 3 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-054` | HDS France | regulatory_compliance | 100.0% | 100.0% | 3 | 3 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-055` | HITRUST CSF | regulatory_compliance | 100.0% | 100.0% | 3 | 3 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-070` | SOC 2 Type 2 | regulatory_compliance | 100.0% | 100.0% | 5 | 5 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-071` | SOC 3 | regulatory_compliance | 100.0% | 100.0% | 5 | 5 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-057` | Invoice Terms EN-CH | contract | 100.0% | 66.7% | 8 | 8 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-058` | manage-auto-claim-policies | general_policy | 95.0% | 100.0% | 19 | 20 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-061` | PO Terms en-AU | contract | 91.6% | 100.0% | 120 | 131 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-062` | PO Terms en-BD | contract | 91.3% | 100.0% | 116 | 127 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-063` | PO Terms en-BN | contract | 91.3% | 100.0% | 116 | 127 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-067` | PO Terms en-LK | contract | 91.3% | 100.0% | 116 | 127 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-051` | EPCS Azure Compliance | regulatory_compliance | 90.9% | 100.0% | 10 | 11 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-064` | PO Terms en-CN | contract | 90.8% | 100.0% | 118 | 130 | `PROVISIONAL` (Shadow Table) |
| **Tier 1** | `DOC-066` | PO Terms en-IN | contract | 90.0% | 95.6% | 108 | 120 | `PROVISIONAL` (Shadow Table) |
| **Tier 2** | `DOC-065` | PO Terms en-ID | contract | 89.8% | 95.8% | 114 | 127 | `WAVE_2_STAGING` |
| **Tier 2** | `DOC-052` | FDA CFR Title 21 Part 11 | regulatory_compliance | 85.7% | 75.0% | 6 | 7 | `WAVE_2_STAGING` |
| **Tier 3** | `DOC-072` | volume-licensing-invoices | invoice | 84.6% | 100.0% | 11 | 13 | `BLOCKED` (Below 85.0%) |
| **Tier 3** | `DOC-069` | SOC 1 Type 2 | regulatory_compliance | 83.3% | 100.0% | 5 | 6 | `BLOCKED` (Below 85.0%) |
| **Tier 3** | `DOC-059` | manage-user-roles-vl | general_policy | 81.2% | 100.0% | 26 | 32 | `BLOCKED` (Below 85.0%) |
| **Tier 3** | `DOC-056` | HIPAA & HITECH Act | regulatory_compliance | 75.0% | 100.0% | 3 | 4 | `BLOCKED` (Below 85.0%) |
| **Tier 3** | `DOC-060` | Microsoft Store Refund | refund_policy | 64.7% | 100.0% | 11 | 17 | `BLOCKED` (Below 85.0%) |

---

## 3. Dual-Human Adjudication Results (AD-6 Sample Audit)

- **Total Sample Audited**: `157` claims (150 stratified Tier 1 claims + 7 rescued entity claims)
- **Review Protocol**: Blinded dual review (`reviewer_alpha` and `reviewer_beta`) with third-adjudicator escalation
- **Inter-Annotator Agreement Rate**: **100.0%**
- **Observed Precision on Reviewed Sample**: **98.7%** (155 certified, 2 corrected/rejected)
- **Certified Claims Ledger**: Stored in `research/validation_50/staged_ingestion/certified_claims.json`

---

## 4. Governance & Safety Summary
- [x] Exact count reconciliation confirmed (1,026 extracted = 750 provisional + 120 wave 2 + 56 blocked + 100 rejected).
- [x] Standardized terminology: `AUTO_CLASSIFIED_PENDING_REVIEW` and `AUTO_AUDITED_VALID_CANDIDATE`.
- [x] Rescued claims audited across 5 dimensions and dual-review confirmed.
- [x] Tier 1 claims remain in provisional shadow table, with only reviewed sample promoted to certified.
- [x] Tier 3 documents remain strictly blocked.
- [x] Fast regression suite (35/35) passing in 4.14s.
- [x] Zero unrequested git commits or pushes.
