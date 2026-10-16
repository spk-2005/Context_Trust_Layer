# Trulin 9-Document Enterprise Benchmark Evaluation Report (Version 3.2)

**Evaluation Date:** 2026-10-16 15:09:23 UTC  
**Frozen Code Commit:** `4ee140ef169da0b4f7d6420a95586e1d2f628fcb`  
**Evaluation Architecture:** Strict Dual-Tier Ground Truth Benchmark  
- **Full-Match Tier (Strict Production Gate)**: Evaluates claims where Subject, Predicate, Object (including numerical thresholds), Modality, and Evidence Grounding strictly align, and the candidate is admitted into `canonical_approved_claims`.  
- **Partial-Match Tier**: Evaluates claims admitted into `canonical_approved_claims` that exhibit minor parameter discrepancies (e.g., extracted action verb without numeric threshold). Raw unapproved candidate discoveries are isolated into `raw_metrics`.  
- **Dual-Gate Standards**:  
  - `PASS`: Full-Match Recall $\ge 90\%$, Lower-Bound Precision $\ge 90\%$, Full-Match $F_1 \ge 90\%$, Subject Acc $\ge 95\%$.  
  - `CONDITIONAL_PASS`: Partial-Match Recall $\ge 75\%$, Lower-Bound Precision $\ge 35\%$, Partial-Match $F_1 \ge 50\%$, Subject Acc $\ge 85\%$.  
  - `NEEDS_WORK`: Any document failing the above criteria.  

---

## 1. Executive Summary & Verdict Matrix

| Document ID | Official Title | Organization | Full-Match Recall | Partial-Match Recall | Lower-Bound Precision | Full-Match $F_1$ | Partial-Match $F_1$ | Subj Acc | Verdict |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `DOC-001` | Resignation and Voluntary Termination Policy | Central Ohio Technical College | 37.5% (3/8) | 37.5% (3/8) | 27.3% | 31.6% | 31.6% | 100.0% | **`NEEDS_WORK`** |
| `DOC-002` | Guidelines for Engagement of Employees on Contract Basis | Government of Mizoram (DP&AR) | 90.0% (9/10) | 100.0% (10/10) | 25.0% | 39.1% | 43.5% | 100.0% | **`NEEDS_WORK`** |
| `DOC-003` | Termination of Employment Policy | University of St. Thomas | 50.0% (5/10) | 50.0% (5/10) | 13.2% | 20.8% | 20.8% | 100.0% | **`NEEDS_WORK`** |
| `DOC-004` | Sample Return and Refund Policy Template | TermsFeed E-Commerce Standard | 33.3% (2/6) | 33.3% (2/6) | 16.7% | 22.2% | 22.2% | 100.0% | **`NEEDS_WORK`** |
| `DOC-005` | Commercial Vendor Agreement Template | Tarion Warranty Corporation | 20.0% (1/5) | 20.0% (1/5) | 4.0% | 6.7% | 6.7% | 100.0% | **`NEEDS_WORK`** |
| `DOC-006` | WordPress PDF Invoice Plugin Sample | DEMO - Sliced Invoices | 0.0% (0/5) | 0.0% (0/5) | 0.0% | 0.0% | 0.0% | 90.0% | **`NEEDS_WORK`** |
| `DOC-007` | EPA Lead and Copper Rule Implementation Letter | U.S. EPA (Office of Water) | 100.0% (3/3) | 100.0% (3/3) | 23.1% | 37.5% | 37.5% | 100.0% | **`NEEDS_WORK`** |
| `DOC-008` | Employee Notice Period Policy | Wingify Software Private Limited | 61.1% (11/18) | 61.1% (11/18) | 36.7% | 45.8% | 45.8% | 100.0% | **`NEEDS_WORK`** |
| `DOC-009` | Northwind Refund Policy Handbook | Northwind Traders | 41.4% (12/29) | 41.4% (12/29) | 6.8% | 11.7% | 11.7% | 100.0% | **`NEEDS_WORK`** |

---

## 2. Auditable Closed Candidate Accounting Ledger

Every canonical approved candidate is accounted for under a closed partition equation:  
$$\text{Canonical Approved} = \text{Correct Full Matches} + \text{Accepted Partial Matches} + \text{Unjudged Spans} + \text{Duplicates} + \text{Incorrect / Malformed}$$

| Document | Total Extracted | Approved (L6) | Rejected (L6) | Review (L6) | Canonical Approved | Full Matches | Partial Matches | Unjudged Spans | Duplicates | Incorrect / Malformed | Gold Captured (Full/Part/Total) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `DOC-001` | 19 | 11 | 8 | 0 | **11** | 3 | 0 | 8 | 0 | 0 | 3 / 3 / 8 |
| `DOC-002` | 37 | 36 | 1 | 0 | **36** | 9 | 1 | 25 | 1 | 0 | 9 / 10 / 10 |
| `DOC-003` | 55 | 39 | 16 | 0 | **38** | 5 | 0 | 33 | 0 | 0 | 5 / 5 / 10 |
| `DOC-004` | 18 | 12 | 6 | 0 | **12** | 2 | 0 | 10 | 0 | 0 | 2 / 2 / 6 |
| `DOC-005` | 129 | 25 | 100 | 0 | **25** | 1 | 0 | 24 | 0 | 0 | 1 / 1 / 5 |
| `DOC-006` | 10 | 8 | 2 | 0 | **8** | 0 | 0 | 7 | 0 | 1 | 0 / 0 / 5 |
| `DOC-007` | 19 | 13 | 6 | 0 | **13** | 3 | 0 | 10 | 0 | 0 | 3 / 3 / 3 |
| `DOC-008` | 40 | 33 | 7 | 0 | **30** | 11 | 0 | 19 | 0 | 0 | 11 / 11 / 18 |
| `DOC-009` | 250 | 176 | 72 | 0 | **176** | 12 | 0 | 163 | 1 | 0 | 12 / 12 / 29 |

---

## 3. Layer 6 Approved to Canonical Approved Reconciliation Ledger

Every Layer 6 approved candidate is strictly reconciled against canonical approved candidates:  
$$\text{Approved L6 Total} = \text{Canonical Approved} + \text{Excluded Non-Canonical} + \text{Excluded Metadata/Boilerplate} + \text{Excluded Duplicates}$$

| Document | Approved L6 Total | Canonical Approved | Excluded Non-Canonical | Excluded Boilerplate | Excluded Duplicates | Reconciliation Difference | Reconciliation Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `DOC-001` | 11 | 11 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-002` | 36 | 36 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-003` | 39 | 38 | 0 | 1 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-004` | 12 | 12 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-005` | 25 | 25 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-006` | 8 | 8 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-007` | 13 | 13 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-008` | 33 | 30 | 0 | 3 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-009` | 176 | 176 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |

---

## 4. Explicitly Paired Named Metric Suites

To ensure mathematical integrity and avoid mixing populations, separate metric suites are reported:
- **Full-Match Canonical Suite**: Strictly pairs `full_match_recall` with `lower_bound_precision` to compute `canonical_f1_full_match`.
- **Partial-Match Suite**: Strictly pairs `partial_match_recall` with `partial_precision` to compute `canonical_f1_partial_match` (both derived strictly from canonical approved claims).
- **Adjudication Tier**: Distinguishes lower-bound precision from measured precision for documents with large unannotated spans (e.g. DOC-009).

| Document | Full Recall | Lower-Bound Precision | Full-Match $F_1$ | Partial Recall | Partial Precision | Partial-Match $F_1$ | Adjudicated Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `DOC-001` | 37.5% | 27.3% | 31.6% | 37.5% | 27.3% | 31.6% | Audited baseline |
| `DOC-002` | 90.0% | 25.0% | 39.1% | 100.0% | 27.8% | 43.5% | Lower bound (25 unjudged spans pending) |
| `DOC-003` | 50.0% | 13.2% | 20.8% | 50.0% | 13.2% | 20.8% | Lower bound (33 unjudged spans pending) |
| `DOC-004` | 33.3% | 16.7% | 22.2% | 33.3% | 16.7% | 22.2% | Audited baseline |
| `DOC-005` | 20.0% | 4.0% | 6.7% | 20.0% | 4.0% | 6.7% | Lower bound (24 unjudged spans pending) |
| `DOC-006` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | Audited baseline |
| `DOC-007` | 100.0% | 23.1% | 37.5% | 100.0% | 23.1% | 37.5% | Audited baseline |
| `DOC-008` | 61.1% | 36.7% | 45.8% | 61.1% | 36.7% | 45.8% | Lower bound (19 unjudged spans pending) |
| `DOC-009` | 41.4% | 6.8% | 11.7% | 41.4% | 6.8% | 11.7% | Lower bound (163 unjudged spans pending) |

---

## 5. DOC-002 In-Depth Audit & Reconciliation

### Audit Ledger Verification (Zero Manual Overrides)
The evaluation of DOC-002 was fully re-executed through the deterministic benchmark matcher. The classification results are:
1. **Labeled Rule Coverage**: 9 out of 10 gold rules are verified as **`FULL_MATCH`** in `canonical_approved_claims` (90.0% Full-Match Recall).
2. **Partial Match (`DOC002-C09`)**: Rule `DOC002-C09` (Earned leave encashment) is classified deterministically as **`ACCEPTED_PARTIAL_MATCH`** (100.0% Partial-Match Recall). The candidate captured subject `Earned leave`, predicate `has_encashment_limit`, and the verified source evidence span, but extracted object `be encashed` omitted the numeric threshold `150 days`.
3. **Precision Framing**: With 36 canonical approved claims and 9 full matches, Lower-Bound Precision is **25.0%** (or 27.8% partial precision). DOC-002 is **NOT production ready** and remains in **`NEEDS_WORK`** with 25 unjudged spans pending human adjudication.

### DOC-002 Per-Gold-Rule Audit Ledger

| Gold Claim ID | Gold Subject | Predicate | Object Value | Match Tier | Candidate ID | Candidate Status | Match Rationale |
|:---|:---|:---|:---|:---:|:---:|:---:|:---|
| `DOC002-C01` | All Administrative Departments and Heads of Departments | `scrupulously` | follow the following terms and | **`FULL_MATCH`** | `e5db8cbe...` | `verified` | Candidate admitted into canonical approved claims with 100% semantic and evidence alignment. |
| `DOC002-C02` | engagement on contract basis | `has_validity_rule` | be made except with prior appr | **`FULL_MATCH`** | `77bca732...` | `verified` | Candidate admitted into canonical approved claims with 100% semantic and evidence alignment. |
| `DOC002-C03` | Period of engagement on contract basis | `has_duration_limit` | one year at the initial stage | **`FULL_MATCH`** | `5a774d21...` | `verified` | Candidate admitted into canonical approved claims with 100% semantic and evidence alignment. |
| `DOC002-C04` | Retired Officers | `has_age_restriction` | 63 years of age | **`FULL_MATCH`** | `be7c596c...` | `verified` | Candidate admitted into canonical approved claims with 100% semantic and evidence alignment. |
| `DOC002-C05` | contract employee | `has_financial_power_restriction` | neither be delegated with fina | **`FULL_MATCH`** | `91591f71...` | `verified` | Candidate admitted into canonical approved claims with 100% semantic and evidence alignment. |
| `DOC002-C06` | rate of monthly remuneration of contract employee | `has_compensation_rate` | minimum scale of pay attached  | **`FULL_MATCH`** | `95a6451a...` | `verified` | Candidate admitted into canonical approved claims with 100% semantic and evidence alignment. |
| `DOC002-C07` | Contract employees | `has_medical_reimbursement` | at par with other regular gove | **`FULL_MATCH`** | `12c87ac6...` | `verified` | Candidate admitted into canonical approved claims with 100% semantic and evidence alignment. |
| `DOC002-C08` | gratuity | `has_validity_rule` | be permissible if he had compl | **`FULL_MATCH`** | `0a4b310b...` | `verified` | Candidate admitted into canonical approved claims with 100% semantic and evidence alignment. |
| `DOC002-C09` | Earned leave | `has_encashment_limit` | subject to a maximum of 150 da | **`ACCEPTED_PARTIAL_MATCH`** | `47f7188f...` | `verified` | Candidate admitted into canonical approved claims; partial discrepancy in object: extracted 'be encashed' without numerical limit parameter '150 days'. |
| `DOC002-C10` | Service book | `has_governing_rule` | shall be maintained for each c | **`FULL_MATCH`** | `8de7d7f6...` | `verified` | Candidate admitted into canonical approved claims with 100% semantic and evidence alignment. |

---

## 6. Detailed Document Diagnostics & Blocking Reasons

### DOC-001: Resignation and Voluntary Termination Policy
- **Organization**: Central Ohio Technical College (hr_policy)
- **Source File**: `Resignation and Voluntary Termination.pdf` (SHA-256: `b804fa0fef939113...`)
- **Final Verdict**: **`NEEDS_WORK`** (Verdict Basis: `full_match_canonical_metrics`)
- **Full-Match Metrics**: Recall = 37.5%, Lower-Bound Precision = 27.3%, Full $F_1$ = 31.6%, Subject Accuracy = 100.0%
- **Partial-Match Metrics**: Recall = 37.5%, Partial Precision = 27.3%, Partial $F_1$ = 31.6%
- **Ledger Breakdown**: Canonical Approved = 11, Full Matches = 3, Partial Matches = 0, Unjudged Spans = 8, Duplicates = 0, Defective = 0
- **Safety Rates**: False Approval = 0.0%, False Conflict = 0.0%, Malformed = 0.0%
- **Blocking Reasons**:
  - `full_match_recall_below_threshold (37.5% < 90.0%)`
  - `canonical_policy_precision_below_threshold (27.3% < 90.0%)`
  - `material_claim_precision_below_threshold (27.3% < 90.0%)`
  - `f1_score_below_threshold (31.6% < 90.0%)`
  - `WRONG_PREDICATE: DOC001-C01 [PREDICATE_MAPPING_ERROR] - College staff: "College staff may resign their employment at any time provid"`
  - `WRONG_PREDICATE: DOC001-C04 [PREDICATE_MAPPING_ERROR] - Staff: "Staff may not use vacation or compensatory time to extend th"`
  - *(+3 additional itemized diagnostics)*

### DOC-002: Guidelines for Engagement of Employees on Contract Basis
- **Organization**: Government of Mizoram (DP&AR) (contract_employment_guidelines)
- **Source File**: `guidelines-for-engagement-of-employees-on-contract-basis.pdf` (SHA-256: `abf5f0de01415f5f...`)
- **Final Verdict**: **`NEEDS_WORK`** (Verdict Basis: `full_match_canonical_metrics`)
- **Full-Match Metrics**: Recall = 90.0%, Lower-Bound Precision = 25.0%, Full $F_1$ = 39.1%, Subject Accuracy = 100.0%
- **Partial-Match Metrics**: Recall = 100.0%, Partial Precision = 27.8%, Partial $F_1$ = 43.5%
- **Ledger Breakdown**: Canonical Approved = 36, Full Matches = 9, Partial Matches = 1, Unjudged Spans = 25, Duplicates = 1, Defective = 0
- **Safety Rates**: False Approval = 0.0%, False Conflict = 0.0%, Malformed = 0.0%
- **Blocking Reasons**:
  - `canonical_policy_precision_below_threshold (25.0% < 90.0%)`
  - `material_claim_precision_below_threshold (25.0% < 90.0%)`
  - `f1_score_below_threshold (39.1% < 90.0%)`

### DOC-003: Termination of Employment Policy
- **Organization**: University of St. Thomas (termination_policy)
- **Source File**: `terminationofemploymentpolicy.pdf` (SHA-256: `2a2ccbbdcf0597d6...`)
- **Final Verdict**: **`NEEDS_WORK`** (Verdict Basis: `full_match_canonical_metrics`)
- **Full-Match Metrics**: Recall = 50.0%, Lower-Bound Precision = 13.2%, Full $F_1$ = 20.8%, Subject Accuracy = 100.0%
- **Partial-Match Metrics**: Recall = 50.0%, Partial Precision = 13.2%, Partial $F_1$ = 20.8%
- **Ledger Breakdown**: Canonical Approved = 38, Full Matches = 5, Partial Matches = 0, Unjudged Spans = 33, Duplicates = 0, Defective = 0
- **Safety Rates**: False Approval = 0.0%, False Conflict = 0.0%, Malformed = 0.0%
- **Blocking Reasons**:
  - `full_match_recall_below_threshold (50.0% < 90.0%)`
  - `canonical_policy_precision_below_threshold (13.2% < 90.0%)`
  - `material_claim_precision_below_threshold (13.2% < 90.0%)`
  - `f1_score_below_threshold (20.8% < 90.0%)`
  - `WRONG_PREDICATE: DOC003-C03 [PREDICATE_MAPPING_ERROR] - Termination for serious misconduct: "Termination for serious misconduct may occur without prior n"`
  - `MISSING: DOC003-C05 [SENTENCE_SPLIT_ERROR] - position elimination: "A position elimination occurs when a position is eliminate d"`
  - *(+3 additional itemized diagnostics)*

### DOC-004: Sample Return and Refund Policy Template
- **Organization**: TermsFeed E-Commerce Standard (refund_policy)
- **Source File**: `sample-return-refund-policy-template.pdf` (SHA-256: `9e8349c1a3b3bc02...`)
- **Final Verdict**: **`NEEDS_WORK`** (Verdict Basis: `full_match_canonical_metrics`)
- **Full-Match Metrics**: Recall = 33.3%, Lower-Bound Precision = 16.7%, Full $F_1$ = 22.2%, Subject Accuracy = 100.0%
- **Partial-Match Metrics**: Recall = 33.3%, Partial Precision = 16.7%, Partial $F_1$ = 22.2%
- **Ledger Breakdown**: Canonical Approved = 12, Full Matches = 2, Partial Matches = 0, Unjudged Spans = 10, Duplicates = 0, Defective = 0
- **Safety Rates**: False Approval = 0.0%, False Conflict = 0.0%, Malformed = 0.0%
- **Blocking Reasons**:
  - `full_match_recall_below_threshold (33.3% < 90.0%)`
  - `canonical_policy_precision_below_threshold (16.7% < 90.0%)`
  - `material_claim_precision_below_threshold (16.7% < 90.0%)`
  - `f1_score_below_threshold (22.2% < 90.0%)`
  - `MISSING: DOC004-C01 [SENTENCE_SPLIT_ERROR] - Your Order Cancellation Rights: "You are entitled to cancel Your Order within 14 days without"`
  - `MISSING: DOC004-C02 [SENTENCE_SPLIT_ERROR] - deadline for cancelling an Order: "The deadline for cancelling an Order is 14 days from the dat"`
  - *(+2 additional itemized diagnostics)*

### DOC-005: Commercial Vendor Agreement Template
- **Organization**: Tarion Warranty Corporation (commercial_vendor_agreement)
- **Source File**: `Vendor Agreement Template-02.2021_2.pdf` (SHA-256: `53c8cc27edc86823...`)
- **Final Verdict**: **`NEEDS_WORK`** (Verdict Basis: `full_match_canonical_metrics`)
- **Full-Match Metrics**: Recall = 20.0%, Lower-Bound Precision = 4.0%, Full $F_1$ = 6.7%, Subject Accuracy = 100.0%
- **Partial-Match Metrics**: Recall = 20.0%, Partial Precision = 4.0%, Partial $F_1$ = 6.7%
- **Ledger Breakdown**: Canonical Approved = 25, Full Matches = 1, Partial Matches = 0, Unjudged Spans = 24, Duplicates = 0, Defective = 0
- **Safety Rates**: False Approval = 0.0%, False Conflict = 0.0%, Malformed = 0.0%
- **Blocking Reasons**:
  - `full_match_recall_below_threshold (20.0% < 90.0%)`
  - `canonical_policy_precision_below_threshold (4.0% < 90.0%)`
  - `material_claim_precision_below_threshold (4.0% < 90.0%)`
  - `f1_score_below_threshold (6.7% < 90.0%)`
  - `MISSING: DOC005-C01 [SENTENCE_SPLIT_ERROR] - Tarion Warranty Corporation: "Tarion is a private, not-for-profit corporation designated b"`
  - `WRONG_PREDICATE: DOC005-C02 [PREDICATE_MAPPING_ERROR] - Vendor: "be licensed under the New Home Construction Licensing Act, 2"`
  - *(+2 additional itemized diagnostics)*

### DOC-006: WordPress PDF Invoice Plugin Sample
- **Organization**: DEMO - Sliced Invoices (invoice)
- **Source File**: `wordpress-pdf-invoice-plugin-sample.pdf` (SHA-256: `c2de358a0974f9b0...`)
- **Final Verdict**: **`NEEDS_WORK`** (Verdict Basis: `full_match_canonical_metrics`)
- **Full-Match Metrics**: Recall = 0.0%, Lower-Bound Precision = 0.0%, Full $F_1$ = 0.0%, Subject Accuracy = 90.0%
- **Partial-Match Metrics**: Recall = 0.0%, Partial Precision = 0.0%, Partial $F_1$ = 0.0%
- **Ledger Breakdown**: Canonical Approved = 8, Full Matches = 0, Partial Matches = 0, Unjudged Spans = 7, Duplicates = 0, Defective = 1
- **Safety Rates**: False Approval = 0.0%, False Conflict = 0.0%, Malformed = 0.0%
- **Blocking Reasons**:
  - `full_match_recall_below_threshold (0.0% < 90.0%)`
  - `canonical_policy_precision_below_threshold (0.0% < 90.0%)`
  - `material_claim_precision_below_threshold (0.0% < 90.0%)`
  - `f1_score_below_threshold (0.0% < 90.0%)`
  - `subject_accuracy_below_threshold (90.0% < 95.0%)`
  - `MISSING: DOC006-C01 [TABLE_STRUCTURE_ERROR] - Total: "Total $85.00"`
  - *(+4 additional itemized diagnostics)*

### DOC-007: EPA Lead and Copper Rule Implementation Letter
- **Organization**: U.S. EPA (Office of Water) (regulatory_directive_letter)
- **Source File**: `SAMPLE LETTER.pdf` (SHA-256: `56dbc38ad88037db...`)
- **Final Verdict**: **`NEEDS_WORK`** (Verdict Basis: `full_match_canonical_metrics`)
- **Full-Match Metrics**: Recall = 100.0%, Lower-Bound Precision = 23.1%, Full $F_1$ = 37.5%, Subject Accuracy = 100.0%
- **Partial-Match Metrics**: Recall = 100.0%, Partial Precision = 23.1%, Partial $F_1$ = 37.5%
- **Ledger Breakdown**: Canonical Approved = 13, Full Matches = 3, Partial Matches = 0, Unjudged Spans = 10, Duplicates = 0, Defective = 0
- **Safety Rates**: False Approval = 0.0%, False Conflict = 0.0%, Malformed = 0.0%
- **Blocking Reasons**:
  - `canonical_policy_precision_below_threshold (23.1% < 90.0%)`
  - `material_claim_precision_below_threshold (23.1% < 90.0%)`
  - `f1_score_below_threshold (37.5% < 90.0%)`

### DOC-008: Employee Notice Period Policy
- **Organization**: Wingify Software Private Limited (hr_policy)
- **Source File**: `Employees Notice Period Policy- V 1.5 (1).pdf` (SHA-256: `45dfae85a80a6985...`)
- **Final Verdict**: **`NEEDS_WORK`** (Verdict Basis: `full_match_canonical_metrics`)
- **Full-Match Metrics**: Recall = 61.1%, Lower-Bound Precision = 36.7%, Full $F_1$ = 45.8%, Subject Accuracy = 100.0%
- **Partial-Match Metrics**: Recall = 61.1%, Partial Precision = 36.7%, Partial $F_1$ = 45.8%
- **Ledger Breakdown**: Canonical Approved = 30, Full Matches = 11, Partial Matches = 0, Unjudged Spans = 19, Duplicates = 0, Defective = 0
- **Safety Rates**: False Approval = 0.0%, False Conflict = 0.0%, Malformed = 0.0%
- **Blocking Reasons**:
  - `full_match_recall_below_threshold (61.1% < 90.0%)`
  - `canonical_policy_precision_below_threshold (36.7% < 90.0%)`
  - `material_claim_precision_below_threshold (36.7% < 90.0%)`
  - `f1_score_below_threshold (45.8% < 90.0%)`
  - `MISSING: DOC008-C01 [TABLE_STRUCTURE_ERROR] - Wingify Notice Period Policy: "Effective April 1, 2021, this policy outlines various aspect"`
  - `WRONG_PREDICATE: DOC008-C02 [PREDICATE_MAPPING_ERROR] - Grade A (A1 & A2) confirmed employees: "A (A1 & A2) CXO 90 Days"`
  - *(+5 additional itemized diagnostics)*

### DOC-009: Northwind Refund Policy Handbook
- **Organization**: Northwind Traders (refund_handbook)
- **Source File**: `Northwind_Refund_Policy_Handbook.pdf` (SHA-256: `a0a5ae7bffabede3...`)
- **Final Verdict**: **`NEEDS_WORK`** (Verdict Basis: `full_match_canonical_metrics`)
- **Full-Match Metrics**: Recall = 41.4%, Lower-Bound Precision = 6.8%, Full $F_1$ = 11.7%, Subject Accuracy = 100.0%
- **Partial-Match Metrics**: Recall = 41.4%, Partial Precision = 6.8%, Partial $F_1$ = 11.7%
- **Ledger Breakdown**: Canonical Approved = 176, Full Matches = 12, Partial Matches = 0, Unjudged Spans = 163, Duplicates = 1, Defective = 0
- **Safety Rates**: False Approval = 0.0%, False Conflict = 0.0%, Malformed = 0.0%
- **Blocking Reasons**:
  - `full_match_recall_below_threshold (41.4% < 90.0%)`
  - `canonical_policy_precision_below_threshold (6.8% < 90.0%)`
  - `material_claim_precision_below_threshold (6.8% < 90.0%)`
  - `f1_score_below_threshold (11.7% < 90.0%)`
  - `MISSING: DOC009-C05 [SENTENCE_SPLIT_ERROR] - Exchange: "Exchange return shipping rule is N/A."`
  - `MISSING: DOC009-C08 [SENTENCE_SPLIT_ERROR] - Return window: "Return window specifies Summary as 30 days from delivery (60"`
  - *(+15 additional itemized diagnostics)*
