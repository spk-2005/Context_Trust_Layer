# Trulin 9-Document Enterprise Benchmark Evaluation Report (Version 3.2)

**Evaluation Date:** 2026-10-17 04:21:00 UTC  
**Frozen Code Commit:** `d32d1b3`  
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
| `DOC-002` | Guidelines for Engagement of Employees on Contract Basis | Government of Mizoram (DP&AR) | 90.0% (9/10) | 100.0% (10/10) | 25.7% | 40.0% | 44.4% | 100.0% | **`NEEDS_WORK`** |
| `DOC-003` | Termination of Employment Policy | University of St. Thomas | 70.0% (7/10) | 70.0% (7/10) | 18.4% | 29.2% | 29.2% | 100.0% | **`NEEDS_WORK`** |
| `DOC-004` | Sample Return and Refund Policy Template | TermsFeed E-Commerce Standard | 33.3% (2/6) | 33.3% (2/6) | 16.7% | 22.2% | 22.2% | 100.0% | **`NEEDS_WORK`** |
| `DOC-005` | Commercial Vendor Agreement Template | Tarion Warranty Corporation | 6.2% (2/32) | 6.2% (2/32) | 8.0% | 7.0% | 7.0% | 100.0% | **`NEEDS_WORK`** |
| `DOC-006` | WordPress PDF Invoice Plugin Sample | DEMO - Sliced Invoices | 0.0% (0/5) | 0.0% (0/5) | 0.0% | 0.0% | 0.0% | 90.0% | **`NEEDS_WORK`** |
| `DOC-007` | EPA Lead and Copper Rule Implementation Letter | U.S. EPA (Office of Water) | 100.0% (3/3) | 100.0% (3/3) | 23.1% | 37.5% | 37.5% | 100.0% | **`NEEDS_WORK`** |
| `DOC-008` | Employee Notice Period Policy | Wingify Software Private Limited | 94.4% (17/18) | 94.4% (17/18) | 56.7% | 70.8% | 70.8% | 100.0% | **`CONDITIONAL_PASS`** |
| `DOC-009` | Northwind Refund Policy Handbook | Northwind Traders | 15.4% (12/78) | 15.4% (12/78) | 6.9% | 9.5% | 9.5% | 100.0% | **`NEEDS_WORK`** |

---

## 2. Auditable Closed Candidate Accounting Ledger

Every canonical approved candidate is accounted for under a closed partition equation:  
$$\text{Canonical Approved} = \text{Correct Full Matches} + \text{Accepted Partial Matches} + \text{Unjudged Spans} + \text{Incorrect / Malformed}$$

| Document | Total Extracted | Approved (L6) | Rejected (L6) | Review (L6) | Canonical Approved | Full Matches | Partial Matches | Unjudged Spans | Incorrect / Malformed | Gold Captured (Full/Part/Total) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `DOC-001` | 19 | 11 | 8 | 0 | **11** | 3 | 0 | 8 | 0 | 3 / 3 / 8 |
| `DOC-002` | 37 | 36 | 1 | 0 | **35** | 9 | 1 | 25 | 0 | 9 / 10 / 10 |
| `DOC-003` | 55 | 39 | 16 | 0 | **38** | 7 | 0 | 31 | 0 | 7 / 7 / 10 |
| `DOC-004` | 18 | 12 | 6 | 0 | **12** | 2 | 0 | 10 | 0 | 2 / 2 / 6 |
| `DOC-005` | 129 | 25 | 100 | 0 | **25** | 2 | 0 | 23 | 0 | 2 / 2 / 32 |
| `DOC-006` | 10 | 8 | 2 | 0 | **8** | 0 | 0 | 7 | 1 | 0 / 0 / 5 |
| `DOC-007` | 19 | 13 | 6 | 0 | **13** | 3 | 0 | 10 | 0 | 3 / 3 / 3 |
| `DOC-008` | 40 | 33 | 7 | 0 | **30** | 17 | 0 | 13 | 0 | 17 / 17 / 18 |
| `DOC-009` | 250 | 176 | 72 | 0 | **175** | 12 | 0 | 163 | 0 | 12 / 12 / 78 |

---

## 3. Layer 6 Approved to Canonical Approved Reconciliation Ledger

Every Layer 6 approved candidate is strictly reconciled against canonical approved candidates:  
$$\text{Approved L6 Total} = \text{Canonical Approved} + \text{Duplicate Evidence Links} + \text{Excluded Boilerplate} + \text{Excluded Non-Canonical}$$

| Document | Approved L6 Total | Canonical Approved | Excluded Duplicates | Excluded Boilerplate | Excluded Non-Canonical | Reconciliation Difference | Reconciliation Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `DOC-001` | 11 | 11 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-002` | 36 | 35 | 1 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-003` | 39 | 38 | 0 | 1 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-004` | 12 | 12 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-005` | 25 | 25 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-006` | 8 | 8 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-007` | 13 | 13 | 0 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-008` | 33 | 30 | 0 | 3 | 0 | **0** | **`RECONCILED (0 DIFF)`** |
| `DOC-009` | 176 | 175 | 1 | 0 | 0 | **0** | **`RECONCILED (0 DIFF)`** |

---

## 4. Explicitly Paired Named Metric Suites & Adjudication Status

| Document | Full Recall | Lower-Bound Precision | Full-Match $F_1$ | Partial Recall | Partial Precision | Partial-Match $F_1$ | Adjudicated Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `DOC-001` | 37.5% | 27.3% | 31.6% | 37.5% | 27.3% | 31.6% | Audited baseline |
| `DOC-002` | 90.0% | 25.7% | 40.0% | 100.0% | 28.6% | 44.4% | Lower bound (25 unjudged spans pending) |
| `DOC-003` | 70.0% | 18.4% | 29.2% | 70.0% | 18.4% | 29.2% | Adjudicated baseline (31 claims reviewed; 81.6% adj. precision) |
| `DOC-004` | 33.3% | 16.7% | 22.2% | 33.3% | 16.7% | 22.2% | Audited baseline |
| `DOC-005` | 6.2% | 8.0% | 7.0% | 6.2% | 8.0% | 7.0% | Lower bound (23 unjudged spans pending) |
| `DOC-006` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | Audited baseline |
| `DOC-007` | 100.0% | 23.1% | 37.5% | 100.0% | 23.1% | 37.5% | Audited baseline |
| `DOC-008` | 94.4% | 56.7% | 70.8% | 94.4% | 56.7% | 70.8% | **Adjudicated conditional pass** (13 claims reviewed; 96.7% adj. precision) |
| `DOC-009` | 15.4% | 6.9% | 9.5% | 15.4% | 6.9% | 9.5% | Lower bound (163 unjudged spans pending) |