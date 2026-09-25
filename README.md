# 🧠 Context Trust Layer (CTL) — Enterprise v1.0.0

[![CI Unit Tests](https://img.shields.io/badge/Unit%20Tests-44%2F44%20Passing-brightgreen.svg)]()
[![Compliance](https://img.shields.io/badge/Compliance-NIST%20AI%20600--1%20%7C%20EU%20AI%20Act%20%7C%20ISO%2042001-blue.svg)]()
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20SQLAlchemy%20%7C%20Postgres-009688.svg)]()
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%20%7C%20Lucide-61DAFB.svg)]()
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

> **The Enterprise AI Governance, Real-Time Decision Gate & Context Provenance Platform**

The **Context Trust Layer (CTL)** is an enterprise-grade AI security and provenance middleware that intercepts autonomous AI agent actions in real time, validates inputs against a verified ground-truth knowledge store, enforces organizational policies, computes direct financial loss avoidance, and generates one-click auditor-ready regulatory compliance dossiers.

---

## 🏛️ System Architecture

```
                                 ORGANIZATIONAL SOURCES
                      [ Confluence ] [ Notion ] [ Google Docs ] [ PDFs ]
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    GROUND TRUTH & INGESTION LAYER     │
                      │  • Canonical Normalizer & Deduplication│
                      │  • Atomic Claim Extraction (S-P-O)    │
                      │  • Exponential Freshness Decay Engine │
                      │  • Automated Precedence & Conflicts   │
                      └───────────────────┬───────────────────┘
                                          │
                                          ▼
                               ┌─────────────────────┐
                               │ VERIFIED TRUTH STORE│
                               │  (Postgres/pgvector)│
                               └──────────┬──────────┘
                                          │
    AUTONOMOUS AGENTS                     ▼                     EXTERNAL SYSTEMS
 [ LangChain / CrewAI / ──► ┌───────────────────────────┐ ──► [ Production DBs /
   AutoGen / Claude ]       │   REAL-TIME DECISION GATE │       APIs / Firewalls /
                            │  • Context Retrieval      │       Financial Rails ]
                            │  • Hallucination Intercept│
                            │  • Policy & RBAC Guard    │
                            │  • Allow / Review / Block │
                            └─────────────┬─────────────┘
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │      GOVERNANCE & AUDIT PLATFORM      │
                      │  • Financial Liability ROI Calculator │
                      │  • 1-Click NIST/EU AI Act Dossier     │
                      │  • Tamper-Evident SHA-256 Audit Trail │
                      │  • Human-in-the-Loop Review Queue     │
                      └───────────────────────────────────────┘
```

---

## 🌟 Core Enterprise Capabilities

### 1. 🛡️ Real-Time Decision Gate & Live Agent Stream
* **Pre-Execution Interception**: Inspects agent tool calls, financial disbursements, and API requests before they execute.
* **Deterministic Policy Engine**: Enforces role constraints, spending ceilings, data leakage rules, and ground-truth consistency.
* **Interactive Live Simulator**: Real-time console featuring one-click benchmark scenarios (`Port 22 Firewall Drift`, `High-Volume Refund Request`, `PII Customer Data Export`, `Safe Knowledge Query`).

### 2. 💰 Financial Liability Prevented ($ ROI Loss Avoidance Metric)
* Quantifies the direct dollar ROI of AI governance by computing loss avoidance whenever a high-risk agent action is blocked.
* **Empirical Risk Benchmark Model** (Ponemon Institute / IBM Cost of Data Breach):
  * **Security Exploit Interception**: `$45,000` / incident (firewall openings, shell injections)
  * **Regulatory & PII Violations**: `$15,000` / incident (GDPR/HIPAA drift, unredacted exports)
  * **Financial Transaction Drift**: `$5,000+` / incident (unauthorized discounts, unapproved refunds)
  * **Operational Outages**: `$1,250` / incident (infinite agent loops, compute exhaustion)
* Real-time platform ROI multiplier (e.g. `2.5x` vs annual licensing baseline) surfaced in executive dashboards.

### 3. 📜 One-Click Regulatory Compliance Dossier
* Eliminates months of audit preparation by generating formal, cryptographically certified compliance packs with one click:
  * **NIST AI RMF 1.0 (AI 600-1)**: MAP 1.1, MEASURE 2.2, MANAGE 2.4
  * **EU AI Act (Regulation 2024/1689)**: Article 12 (Traceability & Logging) & Article 14 (Human Oversight)
  * **ISO/IEC 42001:2023**: AI Management System Controls A.6 & A.8
  * **SOC 2 Type II**: Trust Services Criteria CC6.1, CC6.6, CC7.2
* **Multi-Format Export**:
  * `HTML`: Standalone, print-ready executive presentation with dark-mode styling.
  * `Markdown`: Git-friendly engineering documentation.
  * `JSON`: Direct ingestion into enterprise SIEMs (Splunk, Datadog) and GRC platforms (OneTrust, Vanta).
* **SHA-256 Integrity Seal**: Signed off under Chief Compliance Officer provenance.

### 4. 👥 Enterprise RBAC & Multi-Tenant Governance
* Complete tenant isolation scoped by `organization_id`.
* Granular Role-Based Access Control:
  * **ADMIN**: Full policy control, tenant management, team provisioning.
  * **OPERATOR**: Document ingestion, truth store curation, rule simulation.
  * **AUDITOR**: Read-only compliance dossier review, audit log export.
  * **VIEWER**: Dashboard & metric observation.
* Secure team invitation workflows, password hashing (`bcrypt`), and enterprise SSO readiness.

---

## ⚡ Quick Start

### Prerequisites
* Python 3.11+
* Node.js 18+
* Docker Desktop (PostgreSQL + pgvector)

### 1. Launch the Database
```powershell
docker compose up -d
```

### 2. Configure & Start Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000
```
Browse interactive OpenAPI documentation at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### 3. Start Frontend Dashboard
```powershell
cd frontend
npm install
npm run dev
```
Open **[http://localhost:4000](http://localhost:4000)** in your browser.

---

## 🧪 Testing & Verification

The platform maintains full test coverage across normalization, claim extraction, conflict resolution, RBAC, and dossier generation:

```powershell
# Run backend test suite
.\backend\.venv\Scripts\pytest.exe backend/tests/unit -q
# Output: 44 passed in 4.51s

# Verify frontend production build
cd frontend
npm run build
# Output: ✓ built in 10.49s
```

---

## 📄 Key API Endpoints

| Category | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Decisions** | `POST` | `/v1/decisions/evaluate` | Intercept and evaluate agent actions in real time |
| **Audit & ROI** | `GET` | `/v1/audit/summary` | Organization audit metrics and loss avoidance total |
| **Audit & ROI** | `GET` | `/v1/audit/roi` | ROI breakdown, platform multiplier, and top prevented incidents |
| **Compliance** | `GET` | `/v1/audit/compliance-dossier` | Export certified audit dossier (`json`, `markdown`, `html`) |
| **Users** | `GET` | `/v1/users` | List tenant team members |
| **Users** | `POST` | `/v1/users` | Provision/invite new user with role assignment |
| **Claims** | `GET` | `/v1/claims` | Query verified truth store claims with trust ratings |
| **Conflicts** | `GET` | `/v1/conflicts` | List and resolve inter-document factual disputes |

---

## 🔐 Security & Compliance

Context Trust Layer enforces zero-trust context delivery. No sensitive credentials or raw prompts bypass local policy filters without cryptographic validation. For questions regarding enterprise deployment, contact your organization's compliance administrator.
