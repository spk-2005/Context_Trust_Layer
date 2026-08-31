# 🧠 Context Trust Layer

> **AI Agent Context Provenance, Validity, and Trust Engine**

The **Context Trust Layer** is an intelligent security and verification middleware sitting between organizational knowledge repositories (Confluence, Notion, Google Docs, PDFs) and AI Agents / LLMs.

It ensures that AI agents receive **only verified, fresh, non-conflicting, and high-trust factual context** with complete provenance citations (exact character offsets, section headers, and SHA-256 evidence hashes).

---

## 📖 Complete Documentation
For an in-depth, beginner-friendly explanation of the architecture, database schema, all 6 intelligence engines, and the test lifecycle, read the master guide:
👉 **[Master Project Guide & Test Deep-Dive (docs/PROJECT_GUIDE.md)](docs/PROJECT_GUIDE.md)**

---

## ⚡ Quick Start

### 1. Start Database Container (Postgres + pgvector)
```powershell
docker compose up -d
```

### 2. Run Database Migrations
```powershell
cd backend
.venv\Scripts\python.exe -m alembic upgrade head
```

### 3. Run the Automated End-to-End Pipeline Test
```powershell
.venv\Scripts\python.exe tests/integration/test_pipeline_e2e.py
```

### 4. Start the Interactive API Server
```powershell
.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```
Browse interactive API documentation at: **[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

## 🏗️ Architecture & Engines

```
[ Ingested Document ] ──► [ Claim Extraction ] ──► [ Trust Scoring ]
                                    │                     │
                                    ▼                     ▼
                         [ Conflict Detection ] ──► [ Context Retrieval ] ──► [ 🤖 AI Agent ]
                                    │
                                    ▼
                         [ Human Review Queue ]
```

1. **Document Ingestion & Normalizer:** SHA-256 hashing, multi-version management (`v1 -> v2`), Unicode cleaning, Markdown section parsing.
2. **Claim Extraction Engine:** Decomposes sections into structured `Subject-Predicate-Object` facts with exact text spans and offsets.
3. **Trust Scoring Engine:** Multi-factor composite rating ($0.0$ to $1.0$) with exponential freshness decay ($365$-day half-life).
4. **Conflict Detection Engine:** Detects numerical discrepancies and direct logical contradictions across documents.
5. **Human Review System:** Resolves disputes, approves winning claims, marks superseded claims outdated, and recalculates trust.
6. **Context Retrieval Engine:** Serves verified context to AI Agents filtered by trust threshold and validity windows.
