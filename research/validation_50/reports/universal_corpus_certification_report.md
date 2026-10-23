# Corpus-Wide Universal Claim Certification Audit Report

**Audit Execution Timestamp**: 2026-10-22T12:32:03.482140+00:00  
**Target Directory**: `B:\Context_Layer_Ai\research\validation_50\raw_documents\Microsoft`  
**Architecture**: Universal 10-Gate Fail-Closed Evidence-First Engine  
**Total Documents Evaluated**: 40  
**Total Raw Candidates**: 2414  
**Execution Runtime**: 35.97 seconds  

---

## 1. Executive Summary & Core Invariant Metrics

All previous platform data was completely purged to guarantee a clean slate. Every document in the target directory was parsed directly into structured text, grounded with immutable SHA-256 evidence spans, and evaluated through the universal 10 gates without any hardcoded document assumptions or metadata synthesis.

| Certification Disposition | Count | Percentage | Operational Meaning |
|---|---|---|---|
| **Automated-Certified Canonical** | **104** | **4.3%** | Passed all 10 fail-closed gates; safe for autonomous agent retrieval |
| **Review Required** | **2114** | **87.6%** | Valid rules awaiting human confirmation or custom taxonomy binding |
| **Quarantined Compound** | **20** | **0.8%** | Multi-branch / mixed-polarity rules isolated from autonomous execution |
| **Non-Rule Reclassified** | **17** | **0.7%** | Definitions, descriptions, and references routed to citation-only tier |
| **Rejected Malformed** | **156** | **6.5%** | Page headers, postal addresses, or grammatical fragments rejected |
| **Collapsed Duplicates** | **3** | **0.1%** | Redundant propositions collapsed with `duplicate_of` back-pointer |

---

## 2. Performance Breakdown by Document Category

The universal architecture was tested across 6 distinct enterprise document archetypes:

| Document Type | Docs | Raw Candidates | Certified Canonical | Review Required | Quarantined | Non-Rules | Rejected | Duplicates |
|---|---|---|---|---|---|---|---|---|
| **Contract** | 12 | 1958 | 74 | 1729 | 20 | 13 | 120 | 2 |
| **Hr Policy** | 4 | 135 | 7 | 118 | 0 | 1 | 9 | 0 |
| **Invoice** | 9 | 112 | 3 | 104 | 0 | 0 | 5 | 0 |
| **Refund Policy** | 7 | 39 | 15 | 15 | 0 | 0 | 9 | 0 |
| **Regulatory Compliance** | 2 | 140 | 5 | 118 | 0 | 3 | 13 | 1 |
| **Technical Documentation** | 6 | 30 | 0 | 30 | 0 | 0 | 0 | 0 |

---

## 3. Universal 10-Gate Failure Pattern Analysis

Under the fail-closed policy, every candidate that does not strictly satisfy a gate is rejected or routed to review. The distribution of tripped gates across all candidates:

| Gate Evaluated | Tripped Count | Invariant Enforced |
|---|---|---|
| `predicate_valid` | **2272** | Controlled taxonomy vocabulary (fails closed on unapproved or banned catch-all generic predicates) |
| `text_integrity` | **156** | Authentic verbatim fidelity (blocks synthetic templates and injected slugs) |
| `clause_entails_claim` | **156** | Contextual entailment (rejects ungrounded assertions) |
| `atomicity_valid` | **20** | Atomic requirement (flags multi-branch disjunctions and mixed polarities) |
| `subject_valid` | **19** | Actor/entity resolution (rejects fragments, page numbers, postal lines) |
| `claim_type_allowed` | **17** | Operative rule requirement (reclassifies definitions, descriptions, references) |
| `evidence_located` | **10** | Exact byte/character offset alignment with source SHA-256 hash |
| `duplicate_valid` | **3** | Semantic uniqueness (collapses identical propositions to canonical) |
| `counterparty_resolved` | **2** | Obligor/obligee binding (rejects ungrounded dangling pronouns) |

---

## 4. Four-Tier Agent Retrieval Access Distribution

The risk policy service computes agent access permissions directly from certification state and predicate risk levels:

| Agent Access Tier | Count | Description |
|---|---|---|
| **HUMAN_CONFIRMATION_REQUIRED** | **2114** | High-risk actions (termination, indemnification) or unverified claims require human approval |
| **BLOCKED** | **179** | Quarantined, rejected, or duplicate claims strictly isolated from retrieval |
| **FULL_AUTONOMOUS** | **104** | Autonomous decision-making and constraint enforcement authorized |
| **CITATION_ONLY** | **17** | Available for background informational context and citations, not binding action |

---

## 5. Document-Level Certification Metrics (All 40 Documents)

| Document ID | Type | Pages | Raw Claims | Certified | Review | Quarantined | Non-Rules | Rej. | Dup. | Filename |
|---|---|---|---|---|---|---|---|---|---|---|
| `DOC-051` | contract | 6 | 53 | 2 | 41 | 4 | 0 | 6 | 0 | Agreement_for_leasing_or_renting_certain_Micr... |
| `DOC-052` | invoice | 6 | 9 | 0 | 9 | 0 | 0 | 0 | 0 | Checklist Microsoft Customer Agreement Billin... |
| `DOC-053` | contract | 5 | 46 | 2 | 42 | 0 | 1 | 1 | 0 | Enterprise Agreement.pdf |
| `DOC-054` | contract | 9 | 76 | 3 | 68 | 0 | 2 | 3 | 0 | Enterprise Subscription Enrollment (Indirect)... |
| `DOC-055` | contract | 294 | 1008 | 24 | 922 | 8 | 6 | 48 | 0 | mcaps-MSFT-GSA-Commercial-Supplier-Agreement-... |
| `DOC-056` | contract | 7 | 69 | 4 | 56 | 4 | 2 | 3 | 0 | Microsoft Business and Services Agreement.pdf |
| `DOC-057` | contract | 11 | 75 | 11 | 23 | 0 | 0 | 41 | 0 | Microsoft Customer Agreement.pdf |
| `DOC-058` | contract | 0 | 323 | 15 | 295 | 2 | 2 | 8 | 1 | Microsoft Partner Agreement (Direct).docx |
| `DOC-059` | contract | 0 | 264 | 13 | 241 | 2 | 0 | 7 | 1 | Microsoft Partner Agreement (Indirect).docx |
| `DOC-060` | contract | 11 | 10 | 0 | 9 | 0 | 0 | 1 | 0 | Migrate EA to Microsoft Customer Agreement AP... |
| `DOC-061` | contract | 11 | 12 | 0 | 11 | 0 | 0 | 1 | 0 | Modern-Work-Plan-Comparison-SMB.pdf |
| `DOC-062` | contract | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Services Provider License Agreement (Indirect... |
| `DOC-063` | invoice | 24 | 42 | 2 | 38 | 0 | 0 | 2 | 0 | Set up billing for Microsoft Customer Agreeme... |
| `DOC-064` | contract | 5 | 22 | 0 | 21 | 0 | 0 | 1 | 0 | Software Licensing Terms - English _ Microsof... |
| `DOC-065` | invoice | 17 | 21 | 0 | 20 | 0 | 0 | 1 | 0 | Transfer Azure product billing ownership to a... |
| `DOC-066` | regulatory_compliance | 0 | 127 | 5 | 106 | 0 | 3 | 12 | 1 | MicrosoftProductandServicesDPA(WW)(English)(M... |
| `DOC-067` | regulatory_compliance | 4 | 13 | 0 | 12 | 0 | 0 | 1 | 0 | Supplier Security and Privacy Assurance Progr... |
| `DOC-068` | hr_policy | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | How-Microsoft-is-reinventing-HR-with-Microsof... |
| `DOC-069` | hr_policy | 40 | 44 | 0 | 42 | 0 | 0 | 2 | 0 | Human-Rights-Transparency-Report-2025.pdf |
| `DOC-070` | hr_policy | 41 | 87 | 6 | 74 | 0 | 0 | 7 | 0 | Privacy in Microsoft Cloud Services.pdf |
| `DOC-071` | hr_policy | 2 | 3 | 1 | 1 | 0 | 1 | 0 | 0 | SupplierComm Refresh July 2024 WebVersion.pdf |
| `DOC-072` | invoice | 7 | 16 | 0 | 16 | 0 | 0 | 0 | 0 | Download Azure billing invoice - Microsoft Co... |
| `DOC-073` | invoice | 9 | 11 | 0 | 11 | 0 | 0 | 0 | 0 | Microsoft volume licensing invoices _ Microso... |
| `DOC-074` | invoice | 4 | 5 | 1 | 4 | 0 | 0 | 0 | 0 | Understand IRS tax forms issued by Microsoft ... |
| `DOC-075` | invoice | 8 | 4 | 0 | 3 | 0 | 0 | 1 | 0 | Understand your invoice for your Microsoft MO... |
| `DOC-076` | invoice | 3 | 4 | 0 | 3 | 0 | 0 | 1 | 0 | View or download your invoice in the Microsof... |
| `DOC-077` | invoice | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | View your Microsoft Store order history _ Mic... |
| `DOC-078` | refund_policy | 2 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | Can't get a refund on apps and games from Mic... |
| `DOC-079` | refund_policy | 4 | 8 | 1 | 5 | 0 | 0 | 2 | 0 | Cancel a Microsoft 365 subscription _ Microso... |
| `DOC-080` | refund_policy | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | Check the status of your Microsoft Store retu... |
| `DOC-081` | refund_policy | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | Get a refund for apps and games purchased fro... |
| `DOC-082` | refund_policy | 4 | 11 | 6 | 0 | 0 | 0 | 5 | 0 | Get an exchange or refund on devices bought f... |
| `DOC-083` | refund_policy | 5 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | How to get a refund on a Microsoft subscripti... |
| `DOC-084` | refund_policy | 4 | 8 | 2 | 4 | 0 | 0 | 2 | 0 | Microsoft subscription refund policy _ Micros... |
| `DOC-085` | technical_documentation | 5 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | Microsoft Entra deployment plans - Microsoft ... |
| `DOC-086` | technical_documentation | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | Microsoft Entra operations reference guide - ... |
| `DOC-087` | technical_documentation | 8 | 10 | 0 | 10 | 0 | 0 | 0 | 0 | Microsoft Entra security operations guide - M... |
| `DOC-088` | technical_documentation | 7 | 7 | 0 | 7 | 0 | 0 | 0 | 0 | Protect APIs by using Azure Application Gatew... |
| `DOC-089` | technical_documentation | 4 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | Security Copilot in Microsoft Entra _ Microso... |
| `DOC-090` | technical_documentation | 5 | 7 | 0 | 7 | 0 | 0 | 0 | 0 | What is Microsoft Entra_ - Microsoft Entra _ ... |

---

## 6. Verification and Audit Sign-Off

- **Clean Database State**: Verified all pre-existing platform data was cleanly wiped prior to ingestion.
- **Zero Document-Specific Hardcoding**: All 40 documents were processed through identical, document-agnostic gate pipelines.
- **Physical Evidence Grounding**: Every certified claim has verified `char_start`, `char_end`, and `source_hash`.
- **Relational Integrity**: `documents`, `document_versions`, `claims`, `claim_evidence`, `claim_trust_scores`, and `human_reviews` populated with referential integrity.

*Report automatically generated by Context Trust Layer Universal Certification Pipeline.*