# 🧠 Context Trust Layer (CTL) — Production Implementation Plan: Slack Connector (#23)

**Branch**: `feature/slack-connector`  
**Target Milestone**: Zero-Regression Live Connector Framework  
**Target Architecture**: 11-Layer Fail-Closed Enterprise AI Governance Framework  
**Scope**: Deliver a production-grade `SlackConnector` with zero database migrations, zero downstream engine modifications, and full offline testability.

---

## 1. Executive Summary & Architectural Guarantees

This plan integrates the **Slack Connector** into the **Context Trust Layer (CTL)** without modifying core downstream services or database schemas.

### 🛡️ Five Invariant & Safety Guarantees
1. **Zero Database / Schema Changes**: No edits to `backend/app/db/models/*` and no new Alembic migrations (`backend/alembic/*`). The existing `DataSource.connection_config` JSONB column and Fernet `_encrypted_credentials` store all connector parameters.
2. **Zero Downstream Core Changes**: No edits to Layer 5 (Candidate Extraction), Layer 6 (Validation Gate), Layer 8 (Trust Engine), Layer 9 (Conflict Engine), or Layer 11 (Decision Gate / MCP).
3. **Zero Third-Party Library Bloat**: Uses the existing asynchronous HTTP client (`httpx`) and data validation engine (`pydantic`). No external Slack SDK is installed.
4. **100% Offline Testability**: All unit test suites use `httpx.MockTransport` to simulate Slack Web APIs without making live network calls.
5. **Universal Blueprint**: Establishes a standardized 5-touchpoint pattern that will serve as the exact template for all subsequent enterprise connectors (Microsoft Teams, Discord, Zendesk).

---

## 2. End-to-End Architectural Flow (The 11 Layers)

Every piece of Slack data flows through the 11-layer architecture without requiring bespoke pipelines:

```
[ Slack Web API: conversations.list, conversations.history, conversations.replies, users.info ]
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 1: Data Source Governance & Ingestion Scoping                                     │
 │ • Classified as SourceFamily.CONVERSATION and SourceIntent.PROPOSALS_DISCUSSIONS        │
 │ • Default Authority Level: 50 (conversational consensus, strictly distinct from 80 policy)│
 │ • Bot token (xoxb-...) encrypted at rest using Fernet envelope encryption               │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 2: Native Connector Discovery & Fetching (THIS DELIVERABLE)                       │
 │ • test_connection(): Validates auth.test and checks x-oauth-scopes                      │
 │ • discover_assets() & discover_channels(): Paginates conversations.list (with is_member) │
 │ • fetch_native_assets(): Emits one RawSourceAsset per message (slack://{C}/{ts})       │
 │ • sync(): Bridges threads into Markdown documents for DocumentIngestionService         │
 │ • Central _call(): Exponential backoff on 5xx; handles HTTP 429 Retry-After (≤ 60s)    │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 3: Canonical Source Envelope & Tamper-Proof Dispatcher (Existing)                 │
 │ • Sealed with deterministic SHA-256 hash in CanonicalSourceEnvelope                     │
 │ • SourceTypeDetector identifies "slack://" & routes to CONVERSATIONS parser             │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 4: Specialized Source-Family Parsing into Evidence Units (Existing)               │
 │ • ConversationParser breaks thread into atomic chat_message units                       │
 │ • Binds exact speaker, ISO timestamp, channel (#incident-management), and thread_id     │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 5: Candidate Extraction, Deontic Classification & Completeness Ledger (Existing)  │
 │ • DeonticClassifier extracts modal operators: OBLIGATION ("must"), PROHIBITION, etc.   │
 │ • CompletenessLedger accounts for 100% of messages across 6 closed states               │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 6: Multi-Dimensional Validation Gate (Existing)                                   │
 │ • Evaluates 6 orthogonal dimensions (Completeness, Source Match, Meaning, Scope, Time) │
 │ • Emits APPROVE / REVIEW / REJECT; persists verified claims to PostgreSQL               │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 7: TEVV Enterprise Benchmark & Release Gate Engine (Existing)                     │
 │ • Compares extracted claims against ground truth benchmarks with >= 99% quote fidelity  │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 8: Multi-Factor Dynamic Trust Scoring & Decay Engine (Existing)                   │
 │ • Applies conversation authority weight (0.50) + 365-day half-life exponential decay   │
 │ • Immediately docks trust from 1.0 to 0.30 if an unresolved conflict is detected       │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 9: Cross-Corpus Semantic Conflict & Contradiction Detection (Existing)            │
 │ • Detects contradictions between chat decisions and formal enterprise policies         │
 │   (e.g., Slack: "Refunds up to $1000 approved", Policy: "Maximum refund limit is $500") │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 10: Human-in-the-Loop (HITL) Adjudication & Resolution Queue (Existing)           │
 │ • Routes contradictory chat-derived claims to human compliance reviewers                │
 │ • Re-evaluates winner; automatically triggers score rebound upon resolution             │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ Layer 11: Real-Time Decision Gate, Context Retrieval & Interception (Existing)          │
 │ • Intercepts autonomous agent tool calls (< 150ms) via Model Context Protocol (MCP)     │
 │ • Blocks actions driven by unverified conversational chat claims                        │
 │ • Quantifies financial loss avoided ($ ROI) and seals SHA-256 Merkle audit trail        │
 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Strict Modification Ledger

### 3.1 Strictly Frozen Modules (0 Lines Changed)
* `backend/app/db/models/*` (No changes to `data_source.py`, `document.py`, `claim.py`, etc.)
* `backend/alembic/*` (Zero database migrations required)
* `backend/app/extraction/*` (Layer 5 Candidate Extraction & Strategy Router untouched)
* `backend/app/validation_gate/*` (Layer 6 6-D Gate untouched)
* `backend/app/ingestion/parsers/*` (Layer 4 `ConversationParser` already supports Slack schema)
* `backend/app/ingestion/envelope.py` & `dispatcher.py` (Layer 3 already handles `"slack://"`)
* `backend/app/trust_engine/*`, `conflict_engine/*`, `retrieval/*`, `mcp/*` (Layers 8–11 untouched)

### 3.2 Exact Touchpoints (2 New Files, 7 Surgical Edits)

| # | Action | File Path | Scope & Impact |
|---|:---|:---|:---|
| 1 | **CREATE** | `backend/app/ingestion/connectors/slack_connector.py` | Complete production connector (~450 lines) |
| 2 | **CREATE** | `backend/tests/unit/test_slack_connector.py` | 9 isolated offline unit tests using `httpx.MockTransport` (~300 lines) |
| 3 | **MODIFY** | `backend/app/ingestion/connectors/slack.py` | Replace placeholder stub with re-export shim (3 lines) |
| 4 | **MODIFY** | `backend/app/ingestion/connectors/__init__.py` | Add `SlackConnector` to exports (2 lines) |
| 5 | **MODIFY** | `backend/app/ingestion/sync_engine.py` | Top-level import + `elif source_type in ("slack", ...):` dispatch (12 lines) |
| 6 | **MODIFY** | `backend/app/ingestion/connector_registry.py` | Add `ConnectorMetadata` to `CONNECTOR_CATALOG`, aliases in `get_by_id`, `resolve_source_family`, and `get_default_intent` (~20 lines) |
| 7 | **MODIFY** | `backend/app/api/v1/sources.py` | Unblock 5 rejection checks, add `"slack"` to `LIVE_SUPPORTED_PROVIDERS`, add 422 validation, secret encryption, `bot_token` redaction, `/test` and `/discover` branches (~35 lines) |
| 8 | **MODIFY** | `backend/tests/unit/test_live_connectors_workflow.py` | Update 2 assertion tests: verify Slack is live, encrypted, and validated (~20 lines) |
| 9 | **MODIFY** | `frontend/src/App.jsx` | Slack catalog card, configuration form (Token, Channels, Discover chips, Lookback, Replies), default `authority_level = 50`, copy polish (~70 lines) |

---

## 4. Component Technical Specifications

### 4.1 `SlackConnector` (`backend/app/ingestion/connectors/slack_connector.py`)

#### Class Inheritance & Constructor
```python
class SlackConnector(BaseConnector):
    """Production Layer 2 connector for Slack workspaces, channels, and conversation threads."""

    def __init__(
        self,
        session: AsyncSession = None,
        organization_id: uuid.UUID | None = None,
        source_id: uuid.UUID | None = None,
        bot_token: str | None = None,
        channels: list[str] | str | None = None,
        include_replies: bool = True,
        lookback_days: int = 30,
        connection_config: dict[str, Any] | None = None,
        owner_id: uuid.UUID | None = None,
        http_client: httpx.AsyncClient | None = None,
        **kwargs: Any,
    ):
```

#### A. Central HTTP Engine (`_call` & `_paginate`)
* **Endpoint Pattern**: `https://slack.com/api/{method}`
* **Authorization**: `Bearer xoxb-...`
* **HTTP 429 Handling**: Reads `Retry-After` response header, sleeps `min(float(header), 60.0)`, retries up to 5 times.
* **HTTP 5xx Handling**: Exponential backoff ($1\text{s}, 2\text{s}, 4\text{s}, 8\text{s}\dots$ capped at $30\text{s}$), retries up to 5 times.
* **Cursor Pagination**: Follows `response_metadata.next_cursor` until empty or null.
* **Testability**: Injected `http_client` allows `httpx.MockTransport` in unit tests.

#### B. `test_connection()` $\to$ `auth.test`
1. Verifies token begins with `xoxb-`.
2. Calls `POST https://slack.com/api/auth.test`.
3. Inspects `x-oauth-scopes` header:
   * **Required Scopes**: `channels:read`, `channels:history`
   * **Recommended Scopes**: `groups:read`, `groups:history`, `users:read`
4. Returns standard dictionary format matching Jira and Confluence:
   ```python
   {
       "success": True,
       "status": "ok",
       "message": "Connected to Slack workspace 'Acme Corp' as bot '@ContextTrustBot'.",
       "details": {
           "bot_user_id": "U01234567",
           "team_id": "T01234567",
           "team": "Acme Corp",
           "workspace_url": "https://acme.slack.com/",
           "granted_scopes": ["channels:read", "channels:history", "users:read"],
           "missing_required_scopes": []
       }
   }
   ```

#### C. `discover_assets()` & `discover_channels()` $\to$ `conversations.list`
* Paginates `conversations.list` with `types=public_channel,private_channel` and `exclude_archived=true`.
* Falls back to `public_channel` if `groups:read` scope is not granted.
* Emits `DiscoveredAsset`:
  ```python
  DiscoveredAsset(
      asset_id=f"slack://{channel['id']}",
      name=f"#{channel['name']}",
      asset_type="channel",
      source_family=SourceFamily.CONVERSATION,
      metadata={
          "channel_id": channel["id"],
          "is_private": channel.get("is_private", False),
          "topic": channel.get("topic", {}).get("value", ""),
          "num_members": channel.get("num_members", 0),
          "is_member": channel.get("is_member", False),
      }
  )
  ```
* Implements `@classmethod async def discover_channels(cls, bot_token: str)` to support the API resource discovery endpoint.

#### D. `fetch_native_assets()` $\to$ Layer 2 Native Assets
1. **Target Channel Resolution**: Matches configured channel names or IDs against cached workspace channels.
2. **Checkpoint & Watermark Strategy**:
   * Initial sync: `oldest = now - timedelta(days=lookback_days)`.
   * Delta sync: `oldest = max(lookback_floor, checkpoint["last_synced_at"] - 120s)`.
3. **Conversations History & Replies**:
   * Paginates `conversations.history(channel=id, oldest=oldest, limit=200)`.
   * For parent messages with `reply_count > 0` and `include_replies=True`, fetches full reply tree via `conversations.replies(channel=id, ts=thread_ts)`. Unfiltered by `oldest` to guarantee thread completeness.
4. **Noise Filtering**:
   * Filters out join/leave events (`channel_join`, `channel_leave`, `pin_added`, `channel_topic`).
   * Skips bot messages (unless `include_bot_messages=True`).
5. **Channel Fault Tolerance**:
   * Catches `not_in_channel`, `channel_not_found`, or `is_archived`.
   * Appends warning (`"Please run /invite @bot in #channel"`) and continues processing other channels without failing the sync.
6. **Emits One `RawSourceAsset` Per Message**:
   * `asset_id`: `"slack://{channel_id}/{message_ts}"`
   * `native_format`: `"slack_message"`
   * `source_family`: `SourceFamily.CONVERSATION`
   * `source_version`: `edited.ts or ts`
   * `raw_payload`: Native Slack message dictionary with parser aliases (`speaker`, `timestamp`, `id`, `parent_id`).
   * `evidence_locator`:
     ```python
     {
         "channel_id": channel_id,
         "channel_name": channel_name,
         "channel": f"#{channel_name}",
         "message_ts": ts,
         "thread_ts": thread_ts,
         "thread_id": thread_ts or ts,
         "permalink": f"{workspace_url}archives/{channel_id}/p{ts.replace('.', '')}"
     }
     ```

#### E. `sync()` $\to$ Markdown Bridge
* Translates message streams into Markdown threads:
  * Resolves `<@U12345>` mentions into `@DisplayName` using a cached `users.info` directory.
  * Formats channel tags (`<#C123|ops>` $\to$ `#ops`) and links (`<url|label>` $\to$ `[label](url)`).
* Formats content:
  ```markdown
  # Slack Thread: #incident-management
  **Channel**: `#incident-management` (`C01234`) | **Thread TS**: `1792918754.197087` | **Messages**: 2
  **Permalink**: https://acme.slack.com/archives/C01234/p1792918754197087

  ---
  ### Message by Alice at 2026-10-25 09:00:00 UTC
  Refunds above $500 must be approved by @FinanceDirector.

  ### Reply by Bob at 2026-10-25 09:15:00 UTC
  Confirmed. This policy is effective immediately.
  ```
* Calls `DocumentIngestionService.ingest_document_with_dedup(DocumentCreate(...))`.
* Returns 3-tuples: `list[tuple[Document, DocumentVersion, bool]]`.

---

### 4.2 API Layer Updates (`backend/app/api/v1/sources.py`)

1. **Provider Whitelist**:
   ```python
   LIVE_SUPPORTED_PROVIDERS = {
       "github",
       "mongodb",
       "mongodb_atlas",
       "jira",
       "confluence",
       "postgresql",
       "postgres",
       "slack",  # <-- Added
   }
   ```

2. **Validation & Secret Redaction (`_secure_and_validate_config`)**:
   * Remove the 400 rejection check for Slack.
   * Add validation rule:
     ```python
     elif stype in ("slack", "slack_channel", "slack_workspace"):
         token = clean_cfg.get("bot_token") or clean_cfg.get("token") or clean_cfg.get("access_token") or ""
         if not token or not token.startswith("xoxb-"):
             raise HTTPException(
                 status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                 detail="Slack Bot User OAuth Token is required and must start with 'xoxb-'."
             )
         secret_payload["bot_token"] = token
         secret_payload["token"] = token

         # Normalize channels
         raw_ch = clean_cfg.get("channels", [])
         if isinstance(raw_ch, str):
             clean_cfg["channels"] = [c.strip() for c in raw_ch.split(",") if c.strip()]
         clean_cfg["lookback_days"] = max(1, min(365, int(clean_cfg.get("lookback_days", 30))))
     ```
   * Add `"bot_token"` to the credential redaction tuple:
     ```python
     ("password", "token", "access_token", "api_token", "bot_token", "api_key", "secret", "client_secret")
     ```

3. **Catalog Filtering (`list_connectors_catalog`)**:
   Remove `filtered = [c for c in filtered if c.id not in ("slack", "slack_message")]`.

4. **Connection Test Dispatch (`test_connection`)**:
   Remove rejection check; add:
   ```python
   elif stype in ("slack", "slack_channel", "slack_workspace"):
       from app.ingestion.connectors.slack_connector import SlackConnector
       connector = SlackConnector(
           session=db,
           organization_id=dummy_org,
           source_id=dummy_src,
           connection_config=data.connection_config,
       )
       res = await connector.test_connection()
   ```

5. **Resource Discovery Dispatch (`discover_resources`)**:
   Remove rejection check; add:
   ```python
   elif stype in ("slack", "slack_channel", "slack_workspace"):
       from app.ingestion.connectors.slack_connector import SlackConnector
       token = cfg.get("bot_token") or cfg.get("token") or ""
       channels = await SlackConnector.discover_channels(bot_token=token)
       return ResourceDiscoveryResponse(source_type="slack", target_resource="channels", items=channels, total_count=len(channels))
   ```

6. **Source Listing Filter (`list_data_sources`)**:
   Remove `"slack"` from the exclusion tuple `("file", "upload", "local_file")`.

---

### 4.3 Catalog & Engine Registration

* **`backend/app/ingestion/connector_registry.py`**:
  * Add to `CONNECTOR_CATALOG`:
    ```python
    ConnectorMetadata(
        id="slack",
        name="Slack Workspace",
        category="enterprise_app",
        category_label="Collaboration & Chat",
        family="enterprise_app",
        description="Ingest operational decisions, approval threads, and policies from Slack channels.",
        default_port=None,
        default_auth="token",
        doc_type="policy_rule",
        monitored_scope="Channels & Conversation Threads",
    ),
    ```
  * In `get_by_id`: Map `"slack_channel"` and `"slack_workspace"` to `"slack"`.
  * In `resolve_source_family`: Add `"slack_channel"`, `"slack_workspace"` $\to$ `SourceFamily.CONVERSATION`.
  * In `get_default_intent`: Add `"slack_channel"`, `"slack_workspace"` $\to$ `SourceIntent.PROPOSALS_DISCUSSIONS`.

* **`backend/app/ingestion/sync_engine.py`**:
  * Add top-level import:
    ```python
    from app.ingestion.connectors.slack_connector import SlackConnector
    ```
  * In `get_connector_for_source()`:
    ```python
    elif source_type in ("slack", "slack_channel", "slack_workspace"):
        return SlackConnector(
            session=self.session,
            organization_id=source.organization_id,
            source_id=source.id,
            connection_config=raw_config,
            owner_id=effective_owner,
            **common_layer1,
        )
    ```

---

### 4.4 Frontend Studio Updates (`frontend/src/App.jsx`)

1. **Supported Catalog Card**:
   Add Slack to `supportedLiveCatalog` with `#4A154B` brand color, `MessageSquare`/`Hash` icon, and description.
2. **Configuration Form**:
   * **Bot Token Input**: Masked password field requiring `xoxb-...`.
   * **Channels Input & Discovery**: Text field with a **Discover Channels** button.
   * **Channel Chips**: Discovered channels render as selectable chips. Channels where `is_member == false` display with an amber warning badge: *"Bot must be invited via /invite @bot"*.
   * **Lookback Days**: Number input defaulting to `30`.
   * **Include Replies**: Checkbox toggle defaulting to `true`.
3. **Default Authority Rating**:
   Set `authority_level = 50` for Slack sources (reflecting conversational proposals/discussions rather than formal 80 policy documents).
4. **Copy Polish**:
   Remove the text *"Slack is explicitly excluded"* from all modals and help tooltips.

---

## 5. Offline Unit Test Matrix (`backend/tests/unit/test_slack_connector.py`)

All 9 test cases run offline using `httpx.MockTransport`:

| Test Name | Scenario Tested |
| :--- | :--- |
| `test_auth_test_success` | Valid `xoxb-` token and full scopes returns `status="ok"`. |
| `test_auth_test_missing_scope` | Detects missing `channels:history` and flags `missing_required_scopes`. |
| `test_auth_test_invalid_token` | Handles Slack `invalid_auth` response gracefully. |
| `test_rate_limit_backoff_429` | Verifies `Retry-After: 1` header triggers sleep and succeeds on retry. |
| `test_discover_channels` | Paginates public and private channels; sets `is_member` accurately. |
| `test_fetch_native_assets_filtering` | Filters out `channel_join` noise, retrieves threads, and produces `RawSourceAsset`. |
| `test_channel_not_in_channel_warning` | `not_in_channel` error appends warning and skips gracefully without failing run. |
| `test_sync_markdown_rendering` | Verifies mention substitution (`<@U123>` $\to$ `@Alice`) and Markdown thread headers. |
| `test_incremental_checkpoint` | Verifies delta fetch applies `last_synced_at - 120s` window. |

---

## 6. Step-by-Step Execution Protocol

```
Step 1: Write [slack_connector.py]
        └─ Implement test_connection, discover_assets, fetch_native_assets, sync
Step 2: Write [test_slack_connector.py]
        └─ Add 9 offline unit tests using httpx.MockTransport (0 network calls)
Step 3: Update Connector Exports & SyncEngine
        └─ Wire slack.py shim, __init__.py, sync_engine.py, connector_registry.py
Step 4: Update API Layer [sources.py]
        └─ Unblock Slack in test, discover, catalog, and secure_config
Step 5: Update Workflow Tests [test_live_connectors_workflow.py]
        └─ Verify Slack is registered, token encrypted, and invalid token rejected
Step 6: Update Frontend [App.jsx]
        └─ Slack card, config form, channel discovery chips, authority 50 default
Step 7: Run Regression Suites
        └─ Pytest unit tests and npm run build
```

### Verification Commands
```powershell
# 1. Run new Slack connector offline unit tests
.\backend\.venv\Scripts\pytest.exe backend/tests/unit/test_slack_connector.py -v

# 2. Run connector registry & security workflow tests
.\backend\.venv\Scripts\pytest.exe backend/tests/unit/test_live_connectors_workflow.py -v

# 3. Run full Layer 1 through Layer 6 pipeline regression suite
.\backend\.venv\Scripts\pytest.exe backend/tests/unit/test_11_layer_claim_architecture.py backend/tests/unit/test_layer_6_validation_gate.py -v

# 4. Verify frontend build
cd frontend; npm run build
```

---

## 7. Universal Connector Blueprint (For Future Connectors)

This pattern serves as the standard template for subsequent connectors (Microsoft Teams, Discord, Zendesk):

| Dimension | Rule & Contract |
| :--- | :--- |
| **1. Source Family & Intent** | Classified in `connector_registry.py` under `SourceFamily` (`DOCUMENT`, `STRUCTURED_DATA`, `CONVERSATION`, or `METADATA_OPERATIONAL`). |
| **2. Base Class** | Inherits `BaseConnector`, takes `(session, organization_id, source_id, connection_config)`. |
| **3. Four Core Methods** | Implements `test_connection()`, `discover_assets()`, `fetch_native_assets()`, and `sync()`. |
| **4. RawSourceAsset Bridge** | Formats `asset_id="{protocol}://{id}"` and sets `source_family`. Layer 3 automatically routes it to the corresponding Layer 4 parser. |
| **5. Engine Registration** | Adds a single `elif source_type == "..."` block in `SyncEngine.get_connector_for_source()`. |
| **6. Secret Encryption** | Registers secret keys in `_secure_and_validate_config()`. `EncryptionService` handles encryption and redaction automatically. |
| **7. Frontend & Testing** | Pairs with a UI form in `App.jsx` and an offline `httpx.MockTransport` test suite.
