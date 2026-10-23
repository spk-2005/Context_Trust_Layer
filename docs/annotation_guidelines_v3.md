# Enterprise Claim Quality Annotation & Certification Guidelines (v3.0)
## Standard Operating Procedure for Blinded Contract Claim Adjudication

**Version:** `v3.0-certified`  
**Target Audience:** Legal Counsel, Compliance Officers, Knowledge Graph Engineers  
**Scope:** Commercial Contracts, Master Service Agreements (MSAs), Data Protection Agreements (DPAs), and Enterprise Policy Handbooks  

---

## 1. Purpose & Guiding Principles

The objective of the Claim Quality Governance Layer is to transform unstructured legal contracts into a **canonical graph of atomic, grounded, deduplicated, and agent-executable policy rules**.

Downstream AI agents cannot reason reliably over run-on sentences, vague verbs, missing actors, or descriptive commentary disguised as obligations. Every claim submitted for human certification must be adjudicated against the six objective criteria defined herein.

### The Golden Rule of Claim Certification
> **"A claim is canonical if and only if an autonomous AI agent can take a binary compliance or execution decision based solely on the claim's subject, counterparty, action, and conditions, without needing to re-read the original document."**

---

## 2. The 6-Dimensional Evaluation Rubric

Every candidate claim is evaluated against six independent dimensions:

### Dimension 1: Actor Grounding & Counterparty Resolution (Subject & Counterparty)
* **Standard:** The subject must be a real, legally capable party, operational role, or operative artifact. It must never be a grammatical fragment, pronoun without antecedent, page heading, or physical postal address.
* **Canonical Subject Allowlist:**
  - `Customer`, `Microsoft`, `Partner`, `Affiliate`, `Either party`, `Each party`, `Neither party`, `Both parties`
  - `Supplier`, `Vendor`, `Employee`, `Employer`, `Company`, `Client`, `Contractor`, `Publisher`, `End User`
  - Operative Artifacts: `Product`, `Software`, `Subscription`, `Invoice`, `Account`, `Deliverable`, `Confidential Information`
* **Counterparty Requirement:** The affected party, obligee, or beneficiary must be resolved (e.g. if Customer has a duty to pay, the counterparty is Microsoft or Partner; if Microsoft grants a license, the counterparty is Customer). If the rule applies mutually, counterparty is `Other party`.
* **Disallowed:** `"the following"`, `"applicable terms"`, `"table of contents"`, `"123 Main St Reno NV"`, `"it"`, `"these"`.

### Dimension 2: Deontic Modality Fidelity
* **Standard:** The modality must accurately reflect the binding legal force of the underlying source text. Modality escalation (turning permissions into mandates) or dilution (turning prohibitions into suggestions) is strictly prohibited.
* **Modal Taxonomies:**
  1. `MUST` (Affirmative Obligation): Non-discretionary mandatory duty (*must*, *shall*, *is required to*, *will pay*).
  2. `MUST_NOT` (Prohibition): Explicit negative duty or restriction (*must not*, *may not*, *cannot*, *is prohibited from*).
  3. `MAY` (Discretionary Permission): Contractual right, option, or privilege (*may*, *is permitted to*, *has the option to*).
  4. `ENTITLED_TO` (Remedy / Entitlement): Affirmative financial or commercial remedy (*is entitled to credit/refund*).
  5. `ELIGIBLE_IF` (Threshold Requirement): Qualifying criterion (*is eligible if*, *meets academic criteria*).
  6. `DEFINES` / `DESCRIBES` (Non-Rule Content): Reserved exclusively for metadata partitions.

### Dimension 3: Controlled Action Taxonomy & Predicate Exactness
* **Standard:** The predicate must use an enterprise action verb from the controlled dictionary. Unconstrained generic verbs (*"in"*, *"become"*, *"order"*, *"customer"*, *"use"*, *"vary"*, *"approved"*) are strictly rejected.
* **Enterprise Action Taxonomies:**
  - `LICENSE`: `grants_product_license`, `may_transfer_perpetual_license`, `must_uninstall_upon_transfer`.
  - `RESTRICTION`: `prohibited_from_reverse_engineering`, `prohibited_from_commercial_hosting`.
  - `PAY`: `must_pay_within_30_days`, `may_assess_late_fee`, `must_pay_applicable_taxes`.
  - `TERMINATE`: `may_terminate_without_cause`, `may_terminate_for_material_breach`, `becomes_due_immediately`.
  - `NOTIFY`: `requires_written_notice`, `must_receive_60_days_modification_notice`.
  - `AUDIT`: `may_conduct_compliance_audit`, `must_provide_audit_access`, `must_acquire_unlicensed_usage`.
  - `INDEMNIFY`: `must_defend_ip_claims`, `must_provide_defense_cooperation`.
  - `CONFIDENTIALITY`: `must_maintain_confidentiality`, `prohibited_from_unauthorized_disclosure`.

### Dimension 4: Claim Atomicity (One Proposition = One Duty)
* **Standard:** A claim must represent exactly **one** legal duty, right, or restriction. If a sentence establishes multiple distinct duties, permissions with alternative paths, or obligations on multiple actors, it **must be split** into atomic child claims.
* **Decomposition Triggers:**
  - Enumeration subclauses: `(i)`, `(ii)` or `(1)`, `(2)` or `(a)`, `(b)`.
  - Semicolons separating clauses.
  - Conjunctions linking multiple modal verbs (*"... will control access ... and is responsible for ..."*).
  - Alternative conditions governing separate legal pathways.

### Dimension 5: Taxonomic Demarcation (Rules vs. Non-Rules)
* **Standard:** Only agent-executable normative rules may enter the active reasoning graph. Non-binding background commentary, term boundaries, external links, and role allocations must be partitioned into dedicated metadata sets:
  - `RULE`: Operative normative duty, right, or remedy.
  - `DEFINITION`: Term boundary or scope clarification (*"Software does not include Online Services"*).
  - `DESCRIPTION`: Informational capabilities, regional availability, or non-binding facts (*"Product availability may vary by region"*).
  - `REFERENCE`: External documentation pointers (*"Published on the Product Terms site at aka.ms/licensingdocs"*).
  - `RESPONSIBILITY`: Organizational delegation statements (*"Microsoft remains responsible for the performance of those services"*).
  - `EXAMPLE`: Non-binding illustrative scenario (*"For example, Customer may deploy on local servers"*).

### Dimension 6: Independent Evidence Grounding & Clause Entailment
* **Standard:** The evidence quote must exist verbatim in the original document text bytes (`span_exists = True`), match the cited page, and its enclosing clause must logically entail the claim without overstatement (`clause_entails_claim = True`).

---

## 3. Standardized Decision Codes & Adjudication Actions

Reviewers must select exactly one primary adjudication code for each candidate claim:

| Adjudication Code | Definition & Criteria | Action Taken |
| :--- | :--- | :--- |
| **`APPROVE`** | Claim passes all 6 dimensions: real actor, controlled predicate, atomic duty, valid modality, exact evidence match. | Promoted to `CANONICAL`. |
| **`REPAIR_PREDICATE`** | Claim captures a genuine obligation, but predicate is generic, ambiguous, or misnamed. | Rewritten to controlled vocabulary verb. |
| **`SPLIT_COMPOUND`** | Claim combines multiple distinct duties or permissions. | Decomposed into parent-child atomic claims (`:split:1`, `:split:2`). |
| **`RECLASSIFY_NON_RULE`** | Statement is informative, definitional, or cross-referential rather than an operative rule. | Routed to `DEFINITION`, `DESCRIPTION`, `REFERENCE`, or `RESPONSIBILITY`. |
| **`MARK_DUPLICATE`** | Claim expresses the identical normative proposition as an existing canonical claim under the same conditions. | Collapsed into canonical record; duplicate evidence linked. |
| **`REJECT_FRAGMENT`** | Subject is a heading/slug, quote is ungrounded, or text is unparsable OCR noise. | Permanently marked `REJECTED`. |

---

## 4. Benchmark Golden Case Studies

### Case Study A: Multi-Rule Compound Sentence (Section 1.g - License Transfers)
* **Raw Extracted Sentence:**
  > *"Customer may only transfer fully-paid, perpetual licenses to (1) an Affiliate or (2) a third party solely in connection with the transfer of hardware to which, or employees to whom, the licenses have been assigned as part of (a) a divestiture of all or part of an Affiliate or (b) a merger involving Customer or an Affiliate."*
* **Incorrect Action:** Approving as a single run-on claim.
* **Adjudication:** `SPLIT_COMPOUND` into 3 atomic child rules:
  1. `Customer` `may_transfer_perpetual_license` $\to$ to an Affiliate for fully-paid perpetual licenses.
  2. `Customer` `may_transfer_perpetual_license` $\to$ to a third party solely with permitted hardware/employee transfer.
  3. `Customer` `may_transfer_perpetual_license` $\to$ as part of corporate divestiture or merger.

### Case Study B: Termination Clauses Compatibility (Sections 7.b & 7.c)
* **Clause 1 (§7.b):** *"Either party may terminate this Agreement without cause on 60 days written notice."*
* **Clause 2 (§7.c):** *"Either party may terminate for material breach on 30 days notice if uncured within 30 days."*
* **Incorrect Action:** Flagging as a `CONFLICT` between 60 days vs 30 days.
* **Adjudication:** `APPROVE` both. Verified orthogonal triggers in `CompatibilityGate`:
  - Clause 1 activation trigger = `without_cause` (remedy: no breach needed, 60 days).
  - Clause 2 activation trigger = `material_breach` (remedy: uncured breach, 30 days).

### Case Study C: Rejection Recovery (Section 9.d - Modification Terms)
* **Source Text (§9.d):** *"If Customer does not agree to General Terms modifications, it must stop using Products and turn off recurring billing."*
* **Raw Extractor Output:** Discarded as an invalid fragment.
* **Adjudication:** Recovered under `APPROVE` with predicate `must_stop_use_and_disable_billing`, modality `MUST`, conditions: `["rejects General Terms modifications"]`. High-value protective rule.

### Case Study D: Invoice Ingestion Boundary (Invoice Track)
* **Raw Extracted Text:** *"Invoice total: $14,250.00 due within 30 days of invoice date."*
* **Incorrect Action:** Creating a policy rule `Customer` `must_pay` `$14,250.00`.
* **Adjudication:** `RECLASSIFY_NON_RULE` $\to$ routed to **Track B (Billing/Invoices)** as:
  - `LINE_ITEM` / `GRAND_TOTAL` = `$14,250.00`
  - `PAYMENT_TERM` = `net_30_days`

---

## 5. Blinded Reviewer Protocol & Adjudication Flow

1. **Reviewer Independence:**
   Reviewers evaluate items blindly through independent queue assignments without viewing:
   - Co-reviewer decisions
   - Automated heuristic trust scores
2. **Reviewer Perspective Roles:**
   - **Reviewer Alpha (Senior Enterprise Legal Auditor):** Evaluates legal enforceability, actor allowlist compliance, and deontic modality precision.
   - **Reviewer Beta (Regulatory & Compliance Officer):** Evaluates statutory scope, conditions preservation, and byte-level evidence grounding.
3. **Consensus & Arbitration Rules:**
   - If Alpha = `APPROVE` and Beta = `APPROVE` $\implies$ Final = `APPROVE`.
   - If Alpha = `SPLIT` and Beta = `SPLIT` $\implies$ Final = `SPLIT`.
   - If Divergence occurs (e.g. `APPROVE` vs `REPAIR_PREDICATE`) $\implies$ Escalated to **Lead Adjudicator** for binding resolution with logged legal rationale.
4. **Inter-Annotator Agreement Target:**
   - Cohen's Kappa $\kappa \ge 0.80$ (or Krippendorff's $\alpha \ge 0.80$).
