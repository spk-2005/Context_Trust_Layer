# Context Layer AI - All Documents Ground-Truth Evaluation Matrix (Sprint X)

**Evaluation Standard:** Antigravity Evaluation Contract v1.0.0  
**Milestone:** Sprint X: Independent Human IAA, Sealed Holdout Execution & Generic Recall Restoration  
**Evaluated At:** 2026-10-17 11:02:40 UTC  
**Corpus Status:** 9 Development Documents (Frozen Baseline, Immutable Manifest Barrier Active)  

---

## 1. Corpus Identity & Evaluation Metrics Table

| Document ID | Official Title | Organization | Domain | Full Recall | Low Prec | Adj Prec | F1 (Full) | Verdict | Pilot Gate |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `DOC-001` | Resignation and Voluntary Termination Policy | Central Ohio Technical College | `hr_policy` | **37.5%** | 27.3% | None (Unreviewed) | 31.6% | `NEEDS_WORK` | NO-GO |
| `DOC-002` | Guidelines for Engagement of Employees on Contract Basis | Government of Mizoram (DP&AR) | `contract_employment_guidelines` | **90.0%** | 25.7% | 97.1% | 40.0% | `NEEDS_WORK` | **CONDITIONAL_GO** |
| `DOC-003` | Termination of Employment Policy | University of St. Thomas | `termination_policy` | **70.0%** | 18.4% | None (Unreviewed) | 29.2% | `NEEDS_WORK` | NO-GO |
| `DOC-004` | Sample Return and Refund Policy Template | TermsFeed E-Commerce Standard | `refund_policy` | **33.3%** | 16.7% | None (Unreviewed) | 22.2% | `NEEDS_WORK` | NO-GO |
| `DOC-005` | Commercial Vendor Agreement Template | Tarion Warranty Corporation | `commercial_vendor_agreement` | **6.2%** | 8.0% | None (Unreviewed) | 7.0% | `NEEDS_WORK` | NO-GO |
| `DOC-006` | WordPress PDF Invoice Plugin Sample | DEMO - Sliced Invoices | `invoice` | **100.0%** | 100.0% | 100.0% | 100.0% | `TECHNICAL_PASS_PENDING_GOVERNANCE` | **CONDITIONAL_GO_LIMITED_SCOPE** |
| `DOC-007` | EPA Lead and Copper Rule Implementation Letter | U.S. EPA (Office of Water) | `regulatory_directive_letter` | **100.0%** | 23.1% | 100.0% | 37.5% | `NEEDS_WORK` | **CONDITIONAL_GO** |
| `DOC-008` | Employee Notice Period Policy | Wingify Software Private Limited | `hr_policy` | **94.4%** | 56.7% | 96.7% | 70.8% | `CONDITIONAL_PASS` | **CONDITIONAL_GO** |
| `DOC-009` | Northwind Refund Policy Handbook | Northwind Traders | `refund_handbook` | **19.2%** | 8.6% | None (Unreviewed) | 11.9% | `NEEDS_WORK` | NO-GO |

---

## 2. Pilot Eligibility & Certified Dual-Review IAA Assessment

| Document ID | Scope / Use Case | Cohen's Kappa | Sample N | Adj Precision | Pilot Status | Decision Rationale |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `DOC-002` | Contract Employment Guidelines | **0.9355** | 35 | 97.1% | **CONDITIONAL GO** | High recall (90.0%) and near-perfect dual IAA. Reconciled in doc002_adjudication_reconciliation.json. |
| `DOC-006` | Financial Invoice Plugin | **1.0000** | 5 | 100.0% | **CONDITIONAL_GO_LIMITED_SCOPE** | Independent dual human review completed (Kappa 1.0000, N=5). Downgraded to provisional pending expanded invoice validation. |
| `DOC-007` | EPA Regulatory Directive Letter | **1.0000** | 13 | 100.0% | **CONDITIONAL GO** | Perfect dual IAA and 100% full recall. Certified for regulatory letter pilot. |
| `DOC-008` | Wingify Notice Period Policy | **0.9341** | 30 | 96.7% | **CONDITIONAL GO** | Certified in Sprint T; 94.4% full recall with zero synthetic markers. |
| `DOC-001` | Resignation & Voluntary Termination | N/A | 19 | None | **NO-GO** | Blocked on 37.5% full recall (unadjudicated pool: 19). |
| `DOC-003` | Termination of Employment Policy | N/A | 55 | None | **NO-GO** | Blocked on 70.0% full recall (unadjudicated pool: 55). |
| `DOC-004` | Return & Refund Policy Template | N/A | 18 | None | **NO-GO** | Blocked on 33.3% full recall (unadjudicated pool: 18). |
| `DOC-005` | Commercial Vendor Agreement | N/A | 129 | None | **NO-GO** | Authentic baseline recall is 6.25% (2/32 full matches, 129 unadjudicated pool); covenant pipeline repair required. |
| `DOC-009` | Northwind Refund Policy Handbook | N/A | 250 | None | **NO-GO** | Authentic baseline recall is 19.23% (15/78 full matches, 250 unadjudicated pool); refund condition table repair required. |

---

## 3. Engineering Priorities & Production Gate Posture
1. **Autonomous Production Gate: NO-GO**. General unattended production remains strictly blocked corpus-wide.
2. **Staged Supervised Pilot Gate: CONDITIONAL GO**. Certified strictly for `DOC-002`, `DOC-007`, and `DOC-008`; `DOC-006` certified for supervised pilot under limited operational scope (CONDITIONAL_GO_LIMITED_SCOPE, N=5).
3. **DOC-006 Governance Alignment**: Independent dual human review completed (`doc006_inter_annotator_agreement.json`, Kappa = 1.0000); harness verdict accurately reflects `TECHNICAL_PASS_PENDING_GOVERNANCE` with `CONDITIONAL_GO_LIMITED_SCOPE`.
4. **DOC-002 Adjudication Reconciled**: Published `doc002_adjudication_reconciliation.json` confirming 97.14% adjudicated precision (34 valid / 35 reviewed) and clarifying earlier Sprint U narrative typo.
5. **Holdout Status Formally Rerun**: Sealed holdout re-evaluated under frozen harness 3.2.0 (commit 66183a8); Pilot Gate PASSED (86.29% precision), Production Gate BLOCKED (69.00% recall); no-tuning attestation verified.