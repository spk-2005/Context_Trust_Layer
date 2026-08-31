# 🧠 Context Trust Layer: Complete Project Guide & Test Deep-Dive

Welcome to the **Context Trust Layer** master guide. This document explains the entire project from scratch, including its architecture, database design, intelligence engines, and a step-by-step deep dive into how the end-to-end integration test works.

---

## 📑 Table of Contents
1. [The Core Problem & Mission](#1-the-core-problem--mission)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [The Complete Database Design (14 Tables)](#3-the-complete-database-design-14-tables)
4. [Deep Dive into the Intelligence Engines](#4-deep-dive-into-the-intelligence-engines)
   * [Engine 1: Ingestion & Normalization](#engine-1-ingestion--normalization)
   * [Engine 2: Claim Extraction Engine](#engine-2-claim-extraction-engine)
   * [Engine 3: Multi-Factor Trust Scoring Engine](#engine-3-multi-factor-trust-scoring-engine)
   * [Engine 4: Conflict Detection Engine](#engine-4-conflict-detection-engine)
   * [Engine 5: Human Review & Conflict Resolution](#engine-5-human-review--conflict-resolution)
   * [Engine 6: Context Retrieval Engine (AI Agent API)](#engine-6-context-retrieval-engine-ai-agent-api)
5. [Deep Dive: How the End-to-End Test Works (`test_pipeline_e2e.py`)](#5-deep-dive-how-the-end-to-end-test-works)
   * [The Real-World Test Scenario](#the-real-world-test-scenario)
   * [Step-by-Step Test Breakdown](#step-by-step-test-breakdown)
6. [How to Run and Test the Project](#6-how-to-run-and-test-the-project)

---

## 1. The Core Problem & Mission

### Why AI Agents Fail in Organizations
Traditional AI pipelines (such as standard RAG — Retrieval-Augmented Generation) pull raw text chunks from documents and feed them to an LLM. This leads to three critical failure modes:
1. **Outdated Information:** A 2024 policy document states *"Employees work 2 days remote"*, while a 2026 update states *"Employees work 4 days remote"*. The AI often pulls both and provides hallucinated or conflicting answers.
2. **Untracked Provenance:** Traditional chunking cannot prove *which specific sentence* on *which page* justified a claim.
3. **No Validity Windows or Authority Weighting:** Casual Slack messages are treated with the same weight as signed legal contracts.

### The Solution
The **Context Trust Layer** is an intelligent security and verification middleware sitting between organizational data sources and AI agents. It:
* Deconstructs documents into **atomic facts (Claims)** structured as `Subject-Predicate-Object`.
* Maintains **100% provenance** (exact character offsets, section titles, SHA-256 evidence hashes).
* Calculates a dynamic **Trust Score** ($0.0$ to $1.0$) based on source authority, freshness decay, and evidence.
* Automatically detects **Contradictions & Conflicts** across documents.
* Provides a **Human-in-the-Loop** resolution queue.
* Exposes a **Context Retrieval API** that ensures AI agents only receive fresh, verified, conflict-free context with citations.

---

## 2. System Architecture Overview

```
 [ Data Sources: Confluence, Google Docs, Notion, PDFs ]
                          │
                          ▼
 ┌──────────────────────────────────────────────────────────┐
 │ 1. INGESTION & NORMALIZATION                             │
 │    • Computes SHA-256 hash & manages document versioning │
 │    • Unicode cleaning & Markdown section segmentation    │
 └────────────────────────┬─────────────────────────────────┘
                          │
                          ▼
 ┌──────────────────────────────────────────────────────────┐
 │ 2. CLAIM EXTRACTION ENGINE (LLM / Mock Provider)         │
 │    • Extracts atomic Subject-Predicate-Object triplets   │
 │    • Locates exact text spans & evidence character offsets│
 │    • Records initial validity timeframes                 │
 └────────────────────────┬─────────────────────────────────┘
                          │
                          ▼
 ┌──────────────────────────────────────────────────────────┐
 │ 3. CONFLICT DETECTION ENGINE                             │
 │    • Semantic & vector comparison across all claims      │
 │    • Identifies numerical & direct contradictions        │
 │    • Flags conflicting claims for Human Review           │
 └────────────┬─────────────────────────────┬───────────────┘
              │                             │
    [ Conflict Detected ]         [ No Conflict ]
              │                             │
              ▼                             ▼
 ┌──────────────────────────┐  ┌────────────────────────────┐
 │ 4. HUMAN REVIEW QUEUE    │  │ 5. TRUST SCORING ENGINE    │
 │    • Reviewer resolves   │  │    • Source Authority      │
 │    • Approves winner     │  │    • Exponential Freshness │
 │    • Marks loser outdated│─►│    • Evidence & Consistency│
 └──────────────────────────┘  │    • Computes 0.0 - 1.0    │
                               └────────────┬───────────────┘
                                            │
                                            ▼
                               ┌────────────────────────────┐
                               │ 6. CONTEXT RETRIEVAL ENGINE│
                               │    • Filters by Trust Score│
                               │    • Excludes Conflicts    │
                               │    • Assembles Citations   │
                               └────────────┬───────────────┘
                                            │
                                            ▼
                               [ 🤖 AI Agent / LLM App ]
```

---

## 3. The Complete Database Design (14 Tables)

Implemented in PostgreSQL 16 using SQLAlchemy 2.0 and Alembic:

| # | Table Name | Purpose | Key Columns |
|---|:---|:---|:---|
| 1 | `organizations` | Multi-tenant company isolation | `id`, `name`, `slug`, `status` |
| 2 | `users` | User accounts & permissions | `id`, `organization_id`, `email`, `role` (`admin`, `reviewer`, `viewer`) |
| 3 | `data_sources` | Systems where files originate | `id`, `source_type` (`confluence`), `authority_level` (0–100) |
| 4 | `documents` | Master document records | `id`, `title`, `document_type`, `content_hash`, `status` |
| 5 | `document_versions` | Version history (`v1`, `v2`, `v3`) | `id`, `document_id`, `version_number`, `is_current`, `content_hash` |
| 6 | `claims` | Atomic factual statements | `id`, `claim_text`, `subject`, `predicate`, `object`, `status` |
| 7 | `claim_evidence` | Proof & citations for claims | `id`, `claim_id`, `document_id`, `text_span`, `start_offset`, `end_offset`, `evidence_hash` |
| 8 | `claim_validity` | Temporal validity windows | `id`, `claim_id`, `valid_from`, `valid_until`, `is_current`, `validity_status` |
| 9 | `claim_trust_scores` | Multi-factor trust evaluation | `id`, `claim_id`, `source_score`, `freshness_score`, `evidence_score`, `overall_score` |
| 10 | `claim_conflicts` | Contradiction pairings | `id`, `claim_a_id`, `claim_b_id`, `conflict_type`, `severity`, `confidence`, `resolution_status` |
| 11 | `human_reviews` | Audit trail of human actions | `id`, `reviewer_id`, `target_type`, `target_id`, `decision` (`approve`, `reject`, `override`) |
| 12 | `agents` | Registered AI agents | `id`, `organization_id`, `name`, `agent_type`, `status` |
| 13 | `agent_requests` | Audit log of context lookups | `id`, `agent_id`, `query`, `trust_threshold`, `status` |
| 14 | `agent_context_items` | Ranked context served to agent | `id`, `request_id`, `claim_id`, `rank`, `trust_score`, `included`, `exclusion_reason` |

---

## 4. Deep Dive into the Intelligence Engines

### Engine 1: Ingestion & Normalization
* **File:** `app/ingestion/document_ingestion.py` & `app/normalization/normalizer.py`
* **What it does:**
  1. Calculates SHA-256 hash of incoming text.
  2. If the document already exists, increments version number (`v1 -> v2`) and sets `is_current = True` on the new version while archiving the old.
  3. Cleans Unicode (NFKC), normalizes line endings (`\r\n -> \n`), and strips extra whitespace.
  4. Parses Markdown headers (`#`, `##`, `###`) into structured sections with character offsets.

---

### Engine 2: Claim Extraction Engine
* **Files:** `app/llm/` & `app/services/claim_extraction_service.py`
* **What it does:**
  1. Takes each normalized section and queries the LLM (or Mock Provider).
  2. Deconstructs the text into atomic facts with semantic structure:
     * **Subject:** *"Employees"*
     * **Predicate:** *"can work"*
     * **Object:** *"remotely up to 4 days per week"*
  3. Pinpoints the exact substring inside the raw document to generate `start_offset` and `end_offset`.
  4. Calculates SHA-256 hash of the evidence text to ensure tamper resistance.
  5. Saves records to `claims`, `claim_evidence`, and `claim_validity`.

---

### Engine 3: Multi-Factor Trust Scoring Engine
* **Files:** `app/trust_engine/calculator.py` & `app/services/trust_service.py`
* **Formula:**
  $$S_{\text{overall}} = 0.30 \cdot S_{\text{source}} + 0.25 \cdot S_{\text{freshness}} + 0.20 \cdot S_{\text{evidence}} + 0.15 \cdot S_{\text{consistency}} + 0.10 \cdot S_{\text{authority}} + S_{\text{human}}$$
* **Factors:**
  * **$S_{\text{source}}$ (0.0 to 1.0):** Scaled from `data_source.authority_level` (e.g. 90/100 = 0.90).
  * **$S_{\text{freshness}}$ (0.0 to 1.0):** Exponential decay with 365-day half-life: $e^{-\lambda \cdot \text{days}}$ where $\lambda = \frac{\ln(2)}{365}$.
  * **$S_{\text{evidence}}$ (0.0 to 1.0):** High (0.95) if verified text quote with exact offsets; 0.40 otherwise.
  * **$S_{\text{consistency}}$ (0.0 to 1.0):** 1.00 by default; penalized down to 0.30 if active unresolved conflicts exist.
  * **$S_{\text{human}}$:** Additive human adjustment.

---

### Engine 4: Conflict Detection Engine
* **Files:** `app/conflict_engine/detector.py` & `app/services/conflict_service.py`
* **What it does:**
  1. Compares newly extracted claims against all other active claims in the organization.
  2. Runs contradiction analysis to detect:
     * **Numerical Discrepancies:** e.g. *"2 days"* vs *"4 days"*, *"$300"* vs *"$500"*.
     * **Direct Oppositions:** e.g. *"allowed"* vs *"prohibited"*, *"mandatory"* vs *"optional"*.
  3. Creates a `ClaimConflict` record with `resolution_status = human_review_required` and sets both claims' statuses to `conflicted`.

---

### Engine 5: Human Review & Conflict Resolution
* **Files:** `app/services/conflict_service.py` & `app/api/v1/conflicts.py`
* **What it does:**
  1. Exposes `GET /v1/conflicts/pending` for human reviewers.
  2. When a reviewer resolves the conflict via `POST /v1/conflicts/{id}/resolve`:
     * Marks the winner as `ClaimStatus.VERIFIED`.
     * Marks the superseded claim as `ClaimStatus.OUTDATED`.
     * Logs the decision, reviewer ID, and reasoning in `human_reviews`.
     * **Automatically recalculates trust scores** so the winner's score rebounds to high trust ($0.95$).

---

### Engine 6: Context Retrieval Engine (AI Agent API)
* **Files:** `app/retrieval/engine.py` & `app/api/v1/context.py`
* **What it does:**
  1. Accepts an agent query (e.g. *"work remotely"*, `min_trust_score = 0.75`).
  2. Queries active claims and filters through 4 security checks:
     * **Validity Check:** Ensures `valid_until` has not expired.
     * **Trust Threshold Check:** Ensures `overall_score >= min_trust_score`.
     * **Conflict Safety Check:** **Excludes claims with unresolved conflicts** to protect the agent.
     * **Relevance Check:** Matches query keywords.
  3. Assembles the response with full provenance: document title, section name, page number, and evidence text quote.
  4. Records the query and ranked inclusions/exclusions in `agent_requests` and `agent_context_items`.

---

## 5. Deep Dive: How the End-to-End Test Works

The test in [`backend/tests/integration/test_pipeline_e2e.py`](file:///b:/Context_Layer_Ai/backend/tests/integration/test_pipeline_e2e.py) validates the entire 10-step lifecycle against PostgreSQL in an automated flow.

### The Real-World Test Scenario
* **Company:** Trust Corp
* **Data Source:** Confluence Wiki (Authority: 90/100)
* **Document 1 (2025 Policy):** *"Employees can work remotely up to 2 days per week."*
* **Document 2 (2026 Policy):** *"Employees can work remotely up to 4 days per week."*
* **The Conflict:** 2 days vs 4 days.
* **The Agent:** HR Assistant Bot querying remote work rules.

---

### Step-by-Step Test Breakdown

```
[ Step 1: Health Check ] ──► [ Step 2: Seed Org, DataSource, Agent, Reviewer ]
                                                  │
                                                  ▼
[ Step 4: Extract Doc 1 Claims (Score: 0.95) ] ◄── [ Step 3: Ingest 2025 Policy (2 days) ]
          │
          ▼
[ Step 5: Ingest 2026 Policy (4 days) ]
          │
          ▼
[ Step 6: Extract Doc 2 Claims & Run Conflict Detector ]
          │
          ▼
[ Step 7: Conflict Detected (Numerical Discrepancy, 92% Conf) ]
          │
          ▼
[ Step 8: Agent Context Query (DURING Conflict) ]
          └── Result: Conflicted claims SAFELY EXCLUDED (Agent gets 0 wrong answers)
          │
          ▼
[ Step 9: Human Reviewer Resolves Conflict ]
          └── Decision: APPROVE 2026 (4 days), Mark 2025 OUTDATED
          │
          ▼
[ Step 10: Agent Context Query (AFTER Resolution) ]
          └── Result: Verified 2026 Policy (4 days) SERVED with full citations & 0.95 Trust
```

#### Detailed Explanation of Each Step:

1. **Step 1 — Health Verification:**
   * Calls `GET /v1/health`.
   * Asserts PostgreSQL connection is healthy and `pgcrypto` + `vector` extensions are active.
2. **Step 2 — Database Seeding:**
   * Seeds an Organization (`Trust Corp`), a DataSource (`Confluence Wiki`, authority 90), a Reviewer (`Alice`), and an AI Agent (`HR Assistant`).
3. **Step 3 — Ingesting 2025 Policy:**
   * Posts document with text: *"Employees can work remotely up to 2 days per week."*
   * Database creates `Document` and `DocumentVersion(version_number=1, is_current=True)`.
4. **Step 4 — Claim Extraction & Scoring for 2025 Policy:**
   * Calls `POST /v1/claims/extract/{version_1_id}`.
   * Extracts claim: *"Employees can work remotely up to 2 days per week."*
   * Finds evidence text span and computes initial trust score: **`0.9500`**.
5. **Step 5 — Ingesting 2026 Policy:**
   * Posts updated document: *"Employees can work remotely up to 4 days per week."*
   * Database creates `DocumentVersion(version_number=2, is_current=True)` and archives version 1.
6. **Step 6 & 7 — Conflict Detection Triggered:**
   * Calls `POST /v1/claims/extract/{version_2_id}`.
   * Conflict detector compares 2026 claim against 2025 claim.
   * Evaluator flags `numerical_discrepancy` (*2 days* vs *4 days*) with $92\%$ confidence.
   * Both claims' statuses change to `CONFLICTED`.
7. **Step 8 — Agent Query During Conflict State:**
   * Agent queries `POST /v1/context/query` for *"work remotely"*.
   * Because both claims are currently in conflict, the retrieval engine **excludes both** with reason `"Claim has unresolved conflict pending human review"`.
   * **Why this matters:** The AI agent is prevented from giving inaccurate or contradictory answers to employees.
8. **Step 9 — Human Review & Resolution:**
   * Reviewer Alice calls `POST /v1/conflicts/{id}/resolve`.
   * Decision: `APPROVE` with chosen claim = 2026 Policy (*4 days*).
   * 2026 claim becomes `ClaimStatus.VERIFIED`.
   * 2025 claim becomes `ClaimStatus.OUTDATED`.
   * Trust scores automatically refresh; 2026 claim consistency score returns to 1.0 ($0.9500$ overall).
9. **Step 10 — Agent Query After Resolution:**
   * Agent queries `POST /v1/context/query` for *"work remotely"*.
   * Retrieval engine returns the verified 2026 policy:
     * **Claim:** *"Employees can work remotely up to 4 days per week."*
     * **Trust Score:** `0.9500`
     * **Document:** `Remote Work Policy 2026`
     * **Section:** `Remote Work Rules`
     * **Evidence Quote:** `"Employees can work remotely up to 4 days per week."`

---

## 6. How to Run and Test the Project

### 1. Start Database Container
```powershell
docker compose up -d
```

### 2. Run Database Migrations
```powershell
cd backend
.venv\Scripts\python.exe -m alembic upgrade head
```

### 3. Run All Unit Tests (Instant, In-Memory)
```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
```

### 4. Run the Full End-to-End Pipeline Integration Test
```powershell
.venv\Scripts\python.exe tests/integration/test_pipeline_e2e.py
```

### 5. Start the Live FastAPI Dev Server
```powershell
.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```
Open your browser at **[http://localhost:8000/docs](http://localhost:8000/docs)** to test the interactive Swagger UI.
