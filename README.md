# 🧠 Context Trust Layer (CTL) — Enterprise AI Governance & Decision Gate

[![CI Unit Tests](https://img.shields.io/badge/Unit%20Tests-331%2F331%20Passing%20(100%25)-brightgreen.svg)]()
[![Compliance](https://img.shields.io/badge/Compliance-NIST%20AI%20600--1%20%7C%20EU%20AI%20Act%20%7C%20ISO%2042001-blue.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-Dual--Engine%20(Rules%20%2B%20LLMs)-blueviolet.svg)]()
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20PostgreSQL%20%2B%20pgvector-009688.svg)]()
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%20%7C%20Lucide-61DAFB.svg)]()
[![License](https://img.shields.io/badge/License-MIT%20%2F%20Enterprise%20Ready-green.svg)]()

> **Zero-Trust Real-Time Governance, Autonomous Agent Decision Interception & Ground-Truth Provenance Platform**

The **Context Trust Layer (CTL)** is an enterprise-grade AI governance and security middleware that intercepts autonomous AI agent tool calls and actions in real time. It deterministically validates agent requests against a verified ground-truth knowledge store, blocks policy-violating hallucinations, calculates dollar financial liability prevented ($ ROI Loss Avoidance), and generates cryptographically signed (SHA-256 Merkle root) compliance dossiers ready for regulatory auditors.

---

## 💡 Why Context Trust Layer?

As organizations deploy autonomous AI agents (LangChain, CrewAI, AutoGen, Claude MCP) with real-world tool execution privileges—such as executing database mutations, triggering financial disbursements, or altering network firewalls—uncontrolled model hallucinations present direct operational and regulatory liabilities.

Traditional LLM safety solutions rely on superficial prompt filtering or post-hoc observability logs. **CTL solves this at the architectural execution boundary**:
1. **In-Line Interception (<150ms)**: Intercepts actions *before* execution, issuing deterministic `ALLOW`, `REVIEW`, or `BLOCK` verdicts.
2. **Ground-Truth Knowledge Store**: Decomposes enterprise documents (PDFs, DOCX, Markdown) into atomic Subject-Predicate-Object (SPO) claims with exact character-level evidence spans and exponential freshness decay.
3. **Loss Avoidance Metrics**: Translates blocked security and compliance violations into concrete dollar ROI metrics based on Ponemon Institute / IBM Cost of a Data Breach benchmarks.
4. **Regulatory Audit Dossiers**: One-click generation of certified compliance dossiers for **NIST AI RMF 1.0 (AI 600-1)**, **EU AI Act (2024/1689)**, and **ISO/IEC 42001**.

---

## 🏛️ System Architecture

```
                                 ORGANIZATIONAL SOURCES
                      [ Confluence ] [ Notion ] [ Google Docs ] [ Enterprise PDFs ]
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │     GROUND TRUTH & INGESTION LAYER      │
                      │  • Universal Parser (PDF, DOCX, MD, TXT)│
                      │  • Atomic Claim Extraction (S-P-O)      │
                      │  • Byte-Level Exact Evidence Anchors    │
                      │  • Exponential Freshness Decay Engine   │
                      │  • Automated Precedence & Deduplication │
                      └────────────────────┬────────────────────┘
                                           │
                                           ▼
                                ┌───────────────────────┐
                                │  VERIFIED TRUTH STORE │
                                │ (PostgreSQL + pgvector)│
                                └──────────┬────────────┘
                                           │
     AUTONOMOUS AGENTS                     ▼                      EXTERNAL SYSTEMS
  [ LangChain / CrewAI /  ──► ┌───────────────────────────┐ ──► [ Production DBs /
    AutoGen / Claude MCP ]     │  REAL-TIME DECISION GATE  │       Cloud APIs / Firewalls /
                              │  • Sub-150ms Interception │       Financial Rails ]
                              │  • Policy & RBAC Guard    │
                              │  • Allow / Review / Block │
                              └─────────────┬─────────────┘
                                            │
                                            ▼
                      ┌─────────────────────────────────────────┐
                      │       GOVERNANCE & AUDIT PLATFORM       │
                      │  • Financial Loss Avoidance Calculator  │
                      │  • 1-Click NIST / EU AI Act Dossier     │
                      │  • SHA-256 Merkle Tree Audit Ledger     │
                      │  • Human-in-the-Loop Review Workspace   │
                      └─────────────────────────────────────────┘
```

---

## 🧩 Architectural Transparency: Dual-Engine Design

Context Trust Layer is engineered with an explicit **Dual-Engine Architecture** to ensure robust performance across both automated CI/CD pipelines and live production environments:

| Engine | Characteristics | Target Environment |
| :--- | :--- | :--- |
| **Deterministic Rule Engine** | • Zero external API cost<br>• Fully offline & sub-millisecond execution<br>• 100% reproducible AST, regex, and canonical SPO normalizer<br>• Powers the entire unit test suite (331 tests passing in ~20s) | • CI/CD Automated Gates<br>• Air-gapped / Local Testing<br>• High-throughput deterministic rule enforcement |
| **Pluggable LLM Reasoning Engine** | • Pluggable provider factory (`OpenAI`, `OpenRouter`, `Ollama`)<br>• Natural language semantic extraction & dispute resolution<br>• Supports `gpt-4o-mini`, `z-ai/glm-5.3-flash`, and local `qwen3:1.7b`<br>• Automated fallback to deterministic rules if offline | • Production Deployments<br>• Complex contract ambiguity resolution<br>• Conversational Agent Copilot |

---

## 📊 Feature Readiness & Roadmap

To maintain engineering transparency, platform capabilities are categorized by implementation status:

| Capability | Status | Implementation Details |
| :--- | :---: | :--- |
| **Real-Time Decision Gate** | 🟢 Production | Sub-150ms agent tool-call interception, Allow/Review/Block policy enforcement. |
| **Atomic Claim Normalizer** | 🟢 Production | Subject-Predicate-Object decomposition, controlled enterprise vocabulary. |
| **Evidence Span Locator** | 🟢 Production | Byte-level quote matching, bounding verification, and hallucination rejection. |
| **Financial Loss Avoidance** | 🟢 Production | Ponemon benchmark risk modeling ($45k security exploit, $15k PII breach). |
| **Regulatory Dossiers** | 🟢 Production | Multi-format export (`JSON`, `Markdown`, `HTML`) with SHA-256 integrity seal. |
| **Merkle Audit Ledger** | 🟢 Production | Cryptographic leaf hashing, audit proof generation, and verification tests. |
| **Multi-Tenant RBAC** | 🟢 Production | Role hierarchy (`admin`, `operator`, `reviewer`, `auditor`, `viewer`). |
| **Local Ollama & OpenRouter** | 🟢 Production | Configurable provider factory via `.env` settings. |
| **Real-Time Live Connectors** | 🟡 Beta | Database and document sync drivers with encrypted credential storage. |
| **Cross-Cloud Merkle Anchor** | ⚪ Roadmap | Planned anchoring to public distributed ledgers for external audit notarization. |

---

## ⚡ Quick Start (60 Seconds)

### Prerequisites
* **Docker Desktop** (PostgreSQL 16 + pgvector)
* **Python 3.10+**
* **Node.js 18+**

### 1. Launch Vector Database
```powershell
docker compose up -d postgres
```
*PostgreSQL with pgvector will be available at `localhost:5433` (`context_user:context_password`).*

### 2. Configure & Start Backend API
```powershell
# Navigate to backend directory
cd backend

# Create virtual environment & install dependencies
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Seed canonical organizations, policies, and test data
python ..\database\reset_and_seed.py

# Start API server
uvicorn app.main:app --reload --port 8000
```
* OpenAPI Interactive Swagger UI: **[http://localhost:8000/docs](http://localhost:8000/docs)**
* API Health Check: **[http://localhost:8000/v1/health](http://localhost:8000/v1/health)**

### 3. Launch Frontend Governance Studio
```powershell
cd frontend
npm install
npm run dev
```
* Open **[http://localhost:4000](http://localhost:4000)** to view the interactive real-time dashboard.

---

## 🧪 Testing & Verification

The repository enforces 100% test pass rates across all core governance layers:

```powershell
# Run the entire backend unit test suite (331 tests)
.\backend\.venv\Scripts\pytest.exe backend/tests/unit -q
# Output: 331 passed in 20.81s (100% PASS)

# Verify frontend production build
cd frontend
npm run build
# Output: ✓ 1859 modules transformed, built in ~8s
```

### Modular Verification of Core Flows

You can verify each pipeline stage independently:

```powershell
# 1. Document Ingestion & Specialized Parsers (15 tests)
.\backend\.venv\Scripts\pytest.exe backend/tests/unit/test_universal_file_parser.py backend/tests/unit/test_layer_4_specialized_parsers.py backend/tests/unit/test_normalization.py -q

# 2. Atomic Claim Extraction & SPO Normalizer (31 tests)
.\backend\.venv\Scripts\pytest.exe backend/tests/unit/test_claim_quality_normalizer.py backend/tests/unit/test_enhanced_claim_extraction.py backend/tests/unit/test_11_layer_claim_architecture.py -q

# 3. Byte-Level Evidence References & Anti-Hallucination (10 tests)
.\backend\.venv\Scripts\pytest.exe backend/tests/unit/test_independent_evidence_verifier.py backend/tests/unit/test_grounding_verifier.py -q

# 4. Decision Gate, Freshness Decay & Compliance Dossier (15 tests)
.\backend\.venv\Scripts\pytest.exe backend/tests/unit/test_decision_engine.py backend/tests/unit/test_trust_engine.py backend/tests/unit/test_policy_agent_access_gate_v3.py backend/tests/unit/test_roi_and_dossier.py -q

# 5. Cryptographic Merkle Audit Ledger (13 tests)
.\backend\.venv\Scripts\pytest.exe backend/tests/unit/test_merkle_ledger.py backend/tests/unit/test_release_certification_ledger.py -q
```

---

## 🎬 1-Command Live Pipeline Demonstration

To witness the entire backend lifecycle execute end-to-end (document ingestion, claim extraction, trust scoring, context retrieval, conflict resolution, and decision gate interception), run the included automated demonstrator:

```powershell
python scripts/demo_backend_api.py
```

**Demonstration Workflow Output**:
```
======================================================================
 Context Trust Layer - Full Backend API Execution Demonstration
======================================================================

[1] Root Endpoint GET /:
    -> Application: Context Trust Layer | Status: operational

[2] Health Endpoint GET /v1/health:
    -> Status: healthy | DB Connected: True | Extensions: ['uuid-ossp', 'vector', 'pgcrypto']

[3] Ingest Document POST /v1/documents:
    -> Document ID: 7c5e2d1a-...
    -> Version ID:  9f3b1a8c-...
    -> Status:      Document uploaded and version created successfully

[4] Extract & Score Claims POST /v1/claims/extract/{version_id}:
    -> Extracted 2 claim(s)
    -> Claim #1 Text: 'All API endpoints must enforce TLS 1.3 encryption...'

[5] Evaluate Decision POST /v1/decisions/evaluate:
    -> Agent Action: 'Allow plaintext HTTP traffic on external endpoints'
    -> Decision Outcome: BLOCK
    -> Validity:         INVALID
    -> Risk Rating:      CRITICAL
    -> Prevented Loss:   +$45,000 (Security Exploit Avoidance)
    -> Reasons:          ['Violates Enterprise TLS 1.3 encryption policy']

======================================================================
 SUCCESS! ALL 11 BACKEND ENDPOINTS EXECUTED AND VERIFIED CLEANLY!
======================================================================
```

---

## 📄 Key API Endpoints

| Category | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **System** | `GET` | `/v1/health` | Service health, PostgreSQL connection, and pgvector extension status |
| **Documents** | `POST` | `/v1/documents` | Ingest raw documents (PDF, DOCX, Markdown, plain text) |
| **Documents** | `GET` | `/v1/documents/{id}` | Retrieve document metadata, revision lineage, and active versions |
| **Claims** | `POST` | `/v1/claims/extract/{version_id}` | Extract atomic SPO claims and compute Bayesian trust scores |
| **Claims** | `GET` | `/v1/claims` | Query verified truth store claims with filters and trust thresholds |
| **Conflicts** | `GET` | `/v1/conflicts/pending` | Detect and list factual contradictions between documents |
| **Conflicts** | `POST` | `/v1/conflicts/{id}/resolve` | Human-in-the-loop dispute resolution and claim superseding |
| **Context Query** | `POST` | `/v1/context/query` | Retrieve verified high-trust context grounding for AI agents |
| **Decisions** | `POST` | `/v1/decisions/evaluate` | Intercept and evaluate agent actions in real time (`ALLOW`/`REVIEW`/`BLOCK`) |
| **Audit & ROI** | `GET` | `/v1/audit/summary` | Organization-level loss avoidance totals and audit logs |
| **Compliance** | `GET` | `/v1/audit/compliance-dossier` | Export certified compliance dossier (`json`, `markdown`, `html`) |
| **Merkle Ledger** | `GET` | `/v1/merkle/status` | Current cryptographic Merkle root hash and ledger depth |

---

## 🔐 Security & Data Privacy

* **Zero Leaked Secrets**: All local environment files (`.env`, `.env.*`) are strictly git-ignored. The repository provides an annotated [.env.example](.env.example) with placeholder configurations.
* **Deterministic Sandboxing**: The test suite runs in full isolation without transmitting external API requests or persisting confidential telemetry.
* **Tamper-Evident Provenance**: Every decision and claim verification is cryptographically anchored to a SHA-256 Merkle root.
