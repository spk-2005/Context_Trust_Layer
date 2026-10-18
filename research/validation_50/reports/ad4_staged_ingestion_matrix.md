# Sprint AD-4: Staged Ingestion Architecture & Tiering Matrix
**Corpus Version**: `validation_50_v2` (21 Active English Documents)  
**Current Governance Posture**: `PASS for Staged Ingestion` | `CONDITIONAL for Production Certification`  

## 1. Executive Policy & Ingestion Lifecycle

To guarantee zero hallucination and preserve production integrity, ingestion is decoupled into four explicit lifecycle states:

| Claim State | Definition | Gate Rule | Storage Destination |
|---|---|---|---|
| `CERTIFIED` | Independently audited claim with verified subject, predicate, object, modal operator, and exact character locator | Human review accepted + trust score $\ge 0.95$ | Active Queryable Knowledge Graph |
| `PROVISIONAL` | High-confidence automated extraction passing all 6 Layer 6 dimensions | Automated Gate PASS ($\ge 0.88$), awaiting human spot-check | Staged Shadow Table (`claims_provisional`) |
| `PENDING_REVIEW` | Borderline confidence, conflict-flagged, or low-contrast condition | Flagged by decision engine ($0.75 - 0.87$) | Blinded Adjudication Queue (`research/adjudication_queue/`) |
| `REJECTED` | Grounding failure, unnormalized pronoun, or synthetic phantom subject | Gate FAIL ($< 0.75$) | Audit Ledger Artifact (`failure_patterns.json`) |
| `FILTERED_DIFF` | Pre-extraction suppression by AD-3/AD-4 syntax hygiene filters | Never entered candidate pipeline | Claim Diff Ledger (`ad3_claim_diff_report.json`) |

## 2. Document Tiering Matrix

### Tier 1: Immediate Staged Ingestion Candidates (13 Documents)
Criteria: Precision $\ge 90.0\%$, Recall $\ge 90.0\%$, Locator Accuracy $= 100.0\%$.

| Doc ID | Filename | Document Type | Precision | Recall | Valid Claims | Initial Ingestion State |
|---|---|---|---|---|---|---|
| `DOC-051` | Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf | regulatory_compliance | 90.9% | 100.0% | 10 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-053` | Good Clinical, Laboratory, and Manufacturing Practices (GxP) - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | 100.0% | 100.0% | 3 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-054` | Health Data Hosting (HDS) France - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | 100.0% | 100.0% | 3 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-055` | Health Information Trust Alliance (HITRUST) Common Security Framework (CSF) - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | 100.0% | 100.0% | 3 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-058` | manage-auto-claim-policies.md | general_policy | 95.0% | 100.0% | 19 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-061` | PO-Terms-and-Conditions_en-AU.pdf | contract | 91.6% | 100.0% | 120 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-062` | PO-Terms-and-Conditions_en-BD.pdf | contract | 91.3% | 100.0% | 116 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-063` | PO-Terms-and-Conditions_en-BN.pdf | contract | 91.3% | 100.0% | 116 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-064` | PO-Terms-and-Conditions_en-CN.pdf | contract | 90.8% | 100.0% | 118 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-066` | PO-Terms-and-Conditions_en-IN.pdf | contract | 90.0% | 95.6% | 108 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-067` | PO-Terms-and-Conditions_en-LK.pdf | contract | 91.3% | 100.0% | 116 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-070` | System and Organization Controls (SOC) 2 Type 2 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | 100.0% | 100.0% | 5 | `PROVISIONAL` $\rightarrow$ Sample Audit |
| `DOC-071` | System and Organization Controls (SOC) 3 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | 100.0% | 100.0% | 5 | `PROVISIONAL` $\rightarrow$ Sample Audit |

### Tier 2: Secondary Wave Ingestion (3 Documents)
Criteria: Precision $85.0\% - 89.9\%$, Recall $\ge 75.0\%$.

| Doc ID | Filename | Document Type | Precision | Recall | Valid Claims | Initial Ingestion State |
|---|---|---|---|---|---|---|
| `DOC-052` | Food and Drug Administration CFR Title 21 Part 11 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | 85.7% | 75.0% | 6 | `PENDING_REVIEW` Wave 2 |
| `DOC-057` | Invoice-Terms-and-Conditions_EN-CH.pdf | contract | 100.0% | 66.7% | 8 | `PENDING_REVIEW` Wave 2 |
| `DOC-065` | PO-Terms-and-Conditions_en-ID.pdf | contract | 89.8% | 95.8% | 114 | `PENDING_REVIEW` Wave 2 |

### Tier 3: Review-Gated Documents (5 Documents)
Criteria: Precision $< 85.0\%$ or heavy reliance on overview context. Gated from automated ingestion until adjudication queue clearance.

| Doc ID | Filename | Document Type | Precision | Recall | Valid Claims | Action Required |
|---|---|---|---|---|---|---|
| `DOC-056` | Health Insurance Portability and Accountability Act (HIPAA) & Health Information Technology for Economic and Clinical Health (HITECH) Act - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | 75.0% | 100.0% | 3 | Manual Queue Clearance Required |
| `DOC-059` | manage-user-roles-vl.md | general_policy | 81.2% | 100.0% | 26 | Manual Queue Clearance Required |
| `DOC-060` | Microsoft Store Refund & Return Policy (Surface, Xbox, etc.).pdf | refund_policy | 64.7% | 100.0% | 11 | Manual Queue Clearance Required |
| `DOC-069` | System and Organization Controls (SOC) 1 Type 2 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | 83.3% | 100.0% | 5 | Manual Queue Clearance Required |
| `DOC-072` | volume-licensing-invoices.md | invoice | 84.6% | 100.0% | 11 | Manual Queue Clearance Required |

## 3. False-Negative Safety & Diff Verification Safeguard
- **Total Active English Claims**: `1,019`
- **Total Filtered Narrative Clauses**: `467`
- **Confirmed False Positives (Clean Noise Removal)**: `260`
- **Regulatory Entity Normalizations Rescued**: `207` (e.g. `Covered entities that create, receive, maintain, or transmit PHI` normalized to legal actor head-noun `Covered entities` with restrictive conditions preserved).

## 4. Acceptance Sign-Off
- [x] Scope quarantined: DOC-068 excluded and isolated
- [x] Multilingual feature flag enabled: false by default
- [x] 60-clause Chinese regression test suite passing (30 positive, 30 negative)
- [x] 7-test AD-4 permanent regression suite passing (fast lane)
- [x] Claim diff audit generated with reason codes
- [x] Staged ingestion architecture formalizing Tier 1 / Tier 2 / Tier 3 rollout
- [x] Zero unrequested git commits or pushes