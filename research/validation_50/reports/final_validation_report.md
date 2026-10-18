# Sprint AD-3: 21-Document English Corpus Precision Repair and Full Audit
**Corpus Version**: `validation_50_v2`  
**Active Documents**: `21` (English Validation Corpus)  
**Excluded Documents**: `1` (Quarantined pending dedicated validation)  
**Execution Timestamp**: `2026-10-18T05:52:08.220666+00:00`  
**Release Recommendation**: `PASS_FOR_STAGED_INGESTION (CONDITIONAL_FOR_PRODUCTION_CERTIFICATION)`  

## 1. Executive Summary & Quality Gates

| Metric | Target | Actual | Gate Status |
|---|---|---|---|
| Documents Passing Parsing | ≥ 90% | 100.0% | PASS |
| Claim Precision | ≥ 85.0% | 90.3% | PASS |
| Claim Recall | ≥ 80.0% | 96.8% | PASS |
| Claim F1 Score | ≥ 83.0% | 93.5% | - |
| Evidence Grounding Rate | ≥ 95.0% | 86.3% | FAIL |
| Locator Accuracy Rate | ≥ 95.0% | 100.0% | PASS |

## 2. Document-by-Document Scorecard

| Doc ID | Filename | Type | Parsing Status | Extracted | Valid | Missed | Prec | Rec | F1 |
|---|---|---|---|---|---|---|---|---|---|
| `DOC-051` | Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 11 | 10 | 0 | 90.9% | 100.0% | 95.2% |
| `DOC-052` | Food and Drug Administration CFR Title 21 Part 11 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 7 | 6 | 2 | 85.7% | 75.0% | 80.0% |
| `DOC-053` | Good Clinical, Laboratory, and Manufacturing Practices (GxP) - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 3 | 3 | 0 | 100.0% | 100.0% | 100.0% |
| `DOC-054` | Health Data Hosting (HDS) France - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 3 | 3 | 0 | 100.0% | 100.0% | 100.0% |
| `DOC-055` | Health Information Trust Alliance (HITRUST) Common Security Framework (CSF) - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 3 | 3 | 0 | 100.0% | 100.0% | 100.0% |
| `DOC-056` | Health Insurance Portability and Accountability Act (HIPAA) & Health Information Technology for Economic and Clinical Health (HITECH) Act - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 4 | 3 | 0 | 75.0% | 100.0% | 85.7% |
| `DOC-057` | Invoice-Terms-and-Conditions_EN-CH.pdf | contract | `PASS` | 8 | 8 | 4 | 100.0% | 66.7% | 80.0% |
| `DOC-058` | manage-auto-claim-policies.md | general_policy | `PASS_WITH_MINOR_ISSUES` | 20 | 19 | 0 | 95.0% | 100.0% | 97.4% |
| `DOC-059` | manage-user-roles-vl.md | general_policy | `PASS_WITH_MINOR_ISSUES` | 32 | 26 | 0 | 81.2% | 100.0% | 89.7% |
| `DOC-060` | Microsoft Store Refund & Return Policy (Surface, Xbox, etc.).pdf | refund_policy | `PASS` | 17 | 11 | 0 | 64.7% | 100.0% | 78.6% |
| `DOC-061` | PO-Terms-and-Conditions_en-AU.pdf | contract | `PASS` | 131 | 120 | 0 | 91.6% | 100.0% | 95.6% |
| `DOC-062` | PO-Terms-and-Conditions_en-BD.pdf | contract | `PASS` | 127 | 116 | 0 | 91.3% | 100.0% | 95.5% |
| `DOC-063` | PO-Terms-and-Conditions_en-BN.pdf | contract | `PASS` | 127 | 116 | 0 | 91.3% | 100.0% | 95.5% |
| `DOC-064` | PO-Terms-and-Conditions_en-CN.pdf | contract | `PASS` | 130 | 118 | 0 | 90.8% | 100.0% | 95.2% |
| `DOC-065` | PO-Terms-and-Conditions_en-ID.pdf | contract | `PASS` | 127 | 114 | 5 | 89.8% | 95.8% | 92.7% |
| `DOC-066` | PO-Terms-and-Conditions_en-IN.pdf | contract | `PASS` | 120 | 108 | 5 | 90.0% | 95.6% | 92.7% |
| `DOC-067` | PO-Terms-and-Conditions_en-LK.pdf | contract | `PASS` | 127 | 116 | 0 | 91.3% | 100.0% | 95.5% |
| `DOC-069` | System and Organization Controls (SOC) 1 Type 2 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 6 | 5 | 0 | 83.3% | 100.0% | 90.9% |
| `DOC-070` | System and Organization Controls (SOC) 2 Type 2 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 5 | 5 | 0 | 100.0% | 100.0% | 100.0% |
| `DOC-071` | System and Organization Controls (SOC) 3 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 5 | 5 | 0 | 100.0% | 100.0% | 100.0% |
| `DOC-072` | volume-licensing-invoices.md | invoice | `PASS_WITH_MINOR_ISSUES` | 13 | 11 | 0 | 84.6% | 100.0% | 91.7% |

## 3. Ranked Failure Patterns

| Rank | Failure Pattern | Total Occurrences | Affected Documents |
|---|---|---|---|
| 1 | **Conditional exceptions missed** | 4 | DOC-052, DOC-057, DOC-065, DOC-066 |

## 4. Actionable Repair Sprints
1. **Sprint AD-1**: Address highest frequency pattern from table above.
2. **Sprint AD-2**: Address conditional exception parser loss.
3. **Sprint AD-3**: English corpus precision repair and full claim audit.

## 5. Excluded Documents Ledger (Scope Control)

| Doc ID | Filename | Reason | Excluded At | Rejoin Criteria |
|---|---|---|---|---|
| `DOC-068` | `PO-Terms-and-Conditions_zh-CN.pdf` | Chinese-language extraction requires dedicated multilingual validation before inclusion | `2026-10-18` | Chinese regression suite and full claim audit pass |