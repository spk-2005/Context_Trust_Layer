# Sprint AD-3: 21-Document English Corpus Precision Repair and Full Audit
**Corpus Version**: `validation_50_v2`  
**Active Documents**: `21` (English Validation Corpus)  
**Excluded Documents**: `1` (Quarantined pending dedicated validation)  
**Execution Timestamp**: `2026-10-19T05:00:53.278139+00:00`  
**Release Recommendation**: `FAIL_REQUIRES_REPAIR_SPRINT`  

## 1. Executive Summary & Quality Gates

| Metric | Target | Actual | Gate Status |
|---|---|---|---|
| Documents Passing Parsing | ≥ 90% | 100.0% | PASS |
| Claim Precision | ≥ 85.0% | 62.3% | FAIL |
| Claim Recall | ≥ 80.0% | 100.0% | PASS |
| Claim F1 Score | ≥ 83.0% | 76.8% | - |
| Evidence Grounding Rate | ≥ 95.0% | 93.7% | FAIL |
| Locator Accuracy Rate | ≥ 95.0% | 100.0% | PASS |

## 2. Document-by-Document Scorecard

| Doc ID | Filename | Type | Parsing Status | Extracted | Valid | Missed | Prec | Rec | F1 |
|---|---|---|---|---|---|---|---|---|---|
| `DOC-051` | Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 14 | 13 | 0 | 92.9% | 100.0% | 96.3% |
| `DOC-052` | Food and Drug Administration CFR Title 21 Part 11 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 7 | 6 | 0 | 85.7% | 100.0% | 92.3% |
| `DOC-053` | Good Clinical, Laboratory, and Manufacturing Practices (GxP) - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 3 | 2 | 0 | 66.7% | 100.0% | 66.7% |
| `DOC-054` | Health Data Hosting (HDS) France - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 7 | 3 | 0 | 42.9% | 100.0% | 42.9% |
| `DOC-055` | Health Information Trust Alliance (HITRUST) Common Security Framework (CSF) - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 6 | 2 | 0 | 33.3% | 100.0% | 33.3% |
| `DOC-056` | Health Insurance Portability and Accountability Act (HIPAA) & Health Information Technology for Economic and Clinical Health (HITECH) Act - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 7 | 6 | 0 | 85.7% | 100.0% | 92.3% |
| `DOC-057` | Invoice-Terms-and-Conditions_EN-CH.pdf | contract | `PASS` | 11 | 9 | 0 | 81.8% | 100.0% | 90.0% |
| `DOC-058` | manage-auto-claim-policies.md | general_policy | `PASS_WITH_MINOR_ISSUES` | 9 | 6 | 0 | 66.7% | 100.0% | 80.0% |
| `DOC-059` | manage-user-roles-vl.md | general_policy | `PASS_WITH_MINOR_ISSUES` | 36 | 24 | 0 | 66.7% | 100.0% | 66.7% |
| `DOC-060` | Microsoft Store Refund & Return Policy (Surface, Xbox, etc.).pdf | refund_policy | `PASS` | 8 | 6 | 0 | 75.0% | 100.0% | 85.7% |
| `DOC-061` | PO-Terms-and-Conditions_en-AU.pdf | contract | `PASS` | 99 | 71 | 0 | 71.7% | 100.0% | 71.7% |
| `DOC-062` | PO-Terms-and-Conditions_en-BD.pdf | contract | `PASS` | 100 | 69 | 0 | 69.0% | 100.0% | 69.0% |
| `DOC-063` | PO-Terms-and-Conditions_en-BN.pdf | contract | `PASS` | 100 | 69 | 0 | 69.0% | 100.0% | 69.0% |
| `DOC-064` | PO-Terms-and-Conditions_en-CN.pdf | contract | `PASS` | 98 | 71 | 0 | 72.5% | 100.0% | 72.5% |
| `DOC-065` | PO-Terms-and-Conditions_en-ID.pdf | contract | `PASS` | 95 | 67 | 0 | 70.5% | 100.0% | 70.5% |
| `DOC-066` | PO-Terms-and-Conditions_en-IN.pdf | contract | `PASS` | 94 | 64 | 0 | 68.1% | 100.0% | 68.1% |
| `DOC-067` | PO-Terms-and-Conditions_en-LK.pdf | contract | `PASS` | 100 | 69 | 0 | 69.0% | 100.0% | 69.0% |
| `DOC-069` | System and Organization Controls (SOC) 1 Type 2 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 8 | 3 | 0 | 37.5% | 100.0% | 37.5% |
| `DOC-070` | System and Organization Controls (SOC) 2 Type 2 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 8 | 3 | 0 | 37.5% | 100.0% | 37.5% |
| `DOC-071` | System and Organization Controls (SOC) 3 - Microsoft Compliance _ Microsoft Learn.pdf | regulatory_compliance | `PASS` | 8 | 2 | 0 | 25.0% | 100.0% | 25.0% |
| `DOC-072` | volume-licensing-invoices.md | invoice | `PASS_WITH_MINOR_ISSUES` | 58 | 12 | 0 | 20.7% | 100.0% | 20.7% |

## 3. Ranked Failure Patterns

| Rank | Failure Pattern | Total Occurrences | Affected Documents |
|---|---|---|---|
| 1 | **Spurious False Positive: no more users | claim** | 2 | DOC-058 |
| 2 | **Spurious False Positive: solutions for hard tokens | use** | 1 | DOC-051 |
| 3 | **Spurious False Positive: Customers | use** | 1 | DOC-052 |
| 4 | **Spurious False Positive: Company | operate** | 1 | DOC-056 |
| 5 | **Spurious False Positive: Vendor | bind** | 1 | DOC-057 |
| 6 | **Spurious False Positive: E-invoicing Provider | apply_such** | 1 | DOC-057 |
| 7 | **Spurious False Positive: no new users | receive** | 1 | DOC-058 |
| 8 | **Spurious False Positive: Microsoft Store | has_return_window** | 1 | DOC-060 |
| 9 | **Spurious False Positive: Both price adjustments | has_definition** | 1 | DOC-060 |

## 4. Actionable Repair Sprints
1. **Sprint AD-1**: Address highest frequency pattern from table above.
2. **Sprint AD-2**: Address conditional exception parser loss.
3. **Sprint AD-3**: English corpus precision repair and full claim audit.

## 5. Excluded Documents Ledger (Scope Control)

| Doc ID | Filename | Reason | Excluded At | Rejoin Criteria |
|---|---|---|---|---|
| `DOC-068` | `PO-Terms-and-Conditions_zh-CN.pdf` | Chinese-language extraction requires dedicated multilingual validation before inclusion | `2026-10-18` | Chinese regression suite and full claim audit pass |