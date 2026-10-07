// frontend/src/components/Connections.jsx

import React, { useEffect, useMemo, useState } from "react";
import {
    Activity,
    AlertCircle,
    CheckCircle2,
    ChevronRight,
    Database,
    Eye,
    FileText,
    Loader2,
    Plus,
    RefreshCw,
    Search,
    Settings2,
    ShieldCheck,
    Wifi,
    XCircle,
} from "lucide-react";

import {
    ENTERPRISE_CONNECTORS,
    getConnectorById,
} from "../utils/connectorsCatalog";

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "/api/v1";

const DEFAULT_ORGANIZATION_ID =
    "11111111-1111-1111-1111-111111111111";

/* -------------------------------------------------------------------------- */
/* API                                                                        */
/* -------------------------------------------------------------------------- */

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    let payload = null;

    try {
        payload = await response.json();
    } catch {
        payload = null;
    }

    if (!response.ok) {
        throw new Error(
            payload?.detail ||
            payload?.message ||
            `Request failed with status ${response.status}`
        );
    }

    return payload;
}

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

function normalizeStatus(value) {
    if (!value) return "unknown";

    const status = String(value).toLowerCase();

    if (
        [
            "connected",
            "active",
            "healthy",
            "success",
            "successful",
            "completed",
            "complete",
            "ok",
        ].includes(status)
    ) {
        return "healthy";
    }

    if (
        [
            "running",
            "syncing",
            "processing",
            "pending",
            "in_progress",
        ].includes(status)
    ) {
        return "running";
    }

    if (
        [
            "failed",
            "error",
            "disconnected",
            "unhealthy",
        ].includes(status)
    ) {
        return "failed";
    }

    return "unknown";
}

function formatDate(value) {
    if (!value) return "Never";

    try {
        return new Date(value).toLocaleString();
    } catch {
        return String(value);
    }
}

function formatNumber(value) {
    if (value === undefined || value === null) {
        return "0";
    }

    return Number(value).toLocaleString();
}

function formatStage(value) {
    if (!value) return "Not started";

    return String(value)
        .replaceAll("_", " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getSourceType(source) {
    return (
        source?.source_type ||
        source?.connector_type ||
        source?.type ||
        "unknown"
    );
}

function getConnectorMetadata(source) {
    const sourceType = getSourceType(source);

    return (
        getConnectorById(sourceType) ||
        ENTERPRISE_CONNECTORS.find(
            (connector) =>
                connector.id === sourceType ||
                connector.name?.toLowerCase() ===
                String(source?.name || "").toLowerCase()
        ) ||
        null
    );
}

function getSourceStatus(source) {
    return normalizeStatus(
        source?.monitoring?.status ||
        source?.lifecycle?.status ||
        source?.status
    );
}

function getCurrentStage(source) {
    return (
        source?.lifecycle?.current_stage ||
        source?.lifecycle?.currentStage ||
        source?.current_stage ||
        source?.lifecycle_stage ||
        null
    );
}

/* -------------------------------------------------------------------------- */
/* Status Badge                                                               */
/* -------------------------------------------------------------------------- */

function StatusBadge({ status }) {
    const normalized = normalizeStatus(status);

    const config = {
        healthy: {
            label: "Healthy",
            icon: CheckCircle2,
            className: "status-healthy",
        },
        running: {
            label: "Syncing",
            icon: Loader2,
            className: "status-running",
        },
        failed: {
            label: "Failed",
            icon: XCircle,
            className: "status-failed",
        },
        unknown: {
            label: "Unknown",
            icon: AlertCircle,
            className: "status-unknown",
        },
    };

    const item = config[normalized] || config.unknown;
    const Icon = item.icon;

    return (
        <span className={`status-badge ${item.className}`}>
            <Icon
                size={13}
                className={
                    normalized === "running"
                        ? "status-spin"
                        : ""
                }
            />
            {item.label}
        </span>
    );
}

/* -------------------------------------------------------------------------- */
/* Connection Card                                                            */
/* -------------------------------------------------------------------------- */

function ConnectionCard({
    source,
    onView,
    onTest,
    onSync,
    testing,
    syncing,
}) {
    const metadata = getConnectorMetadata(source);

    const status = getSourceStatus(source);
    const stage = getCurrentStage(source);

    const documents =
        source?.monitoring?.documents_synced ??
        source?.documents_synced ??
        source?.lifecycle?.documents_synced ??
        0;

    const claims =
        source?.monitoring?.claims_extracted ??
        source?.claims_extracted ??
        source?.lifecycle?.claims_extracted ??
        0;

    const conflicts =
        source?.monitoring?.conflicts_detected ??
        source?.conflicts_detected ??
        source?.lifecycle?.conflicts_detected ??
        0;

    const resources =
        source?.selected_resources ||
        source?.selectedResources ||
        [];

    const lastSynced =
        source?.last_synced_at ||
        source?.monitoring?.last_sync_at ||
        source?.lifecycle?.synced_at;

    return (
        <div className="connection-card">
            <div className="connection-card-main">
                <div className="connection-icon">
                    {metadata?.icon ? (
                        <img
                            src={metadata.icon}
                            alt=""
                            onError={(event) => {
                                event.currentTarget.style.display =
                                    "none";
                            }}
                        />
                    ) : (
                        <Database size={22} />
                    )}
                </div>

                <div className="connection-info">
                    <div className="connection-title-row">
                        <h3>
                            {source?.name ||
                                metadata?.name ||
                                getSourceType(source)}
                        </h3>

                        <StatusBadge status={status} />
                    </div>

                    <div className="connection-type">
                        {metadata?.name ||
                            getSourceType(source)}
                    </div>

                    {metadata?.description && (
                        <p className="connection-description">
                            {metadata.description}
                        </p>
                    )}

                    <div className="connection-meta">
                        <span>
                            <Activity size={12} />
                            {formatStage(stage)}
                        </span>

                        <span>
                            <RefreshCw size={12} />
                            {formatDate(lastSynced)}
                        </span>

                        {source?.domain && (
                            <span>
                                <ShieldCheck size={12} />
                                {source.domain}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            <div className="connection-metrics">
                <div className="connection-metric">
                    <span>Documents</span>
                    <strong>{formatNumber(documents)}</strong>
                </div>

                <div className="connection-metric">
                    <span>Claims</span>
                    <strong>{formatNumber(claims)}</strong>
                </div>

                <div className="connection-metric">
                    <span>Conflicts</span>
                    <strong>{formatNumber(conflicts)}</strong>
                </div>

                <div className="connection-metric">
                    <span>Resources</span>
                    <strong>
                        {Array.isArray(resources)
                            ? resources.length
                            : formatNumber(resources)}
                    </strong>
                </div>
            </div>

            <div className="connection-actions">
                <button
                    type="button"
                    className="connection-action secondary"
                    onClick={() => onTest(source)}
                    disabled={testing}
                >
                    {testing ? (
                        <Loader2
                            size={14}
                            className="status-spin"
                        />
                    ) : (
                        <Wifi size={14} />
                    )}
                    Test
                </button>

                <button
                    type="button"
                    className="connection-action secondary"
                    onClick={() => onSync(source)}
                    disabled={syncing}
                >
                    {syncing ? (
                        <Loader2
                            size={14}
                            className="status-spin"
                        />
                    ) : (
                        <RefreshCw size={14} />
                    )}
                    Sync
                </button>

                <button
                    type="button"
                    className="connection-action secondary"
                    onClick={() => onView(source)}
                >
                    <Eye size={14} />
                    Details
                    <ChevronRight size={14} />
                </button>
            </div>
        </div>
    );
}

/* -------------------------------------------------------------------------- */
/* Main Component                                                             */
/* -------------------------------------------------------------------------- */

export default function Connections({
    organizationId = DEFAULT_ORGANIZATION_ID,
    onAddConnection,
    onViewConnection,
    onEditConnection,
    showToast,
}) {
    const [connections, setConnections] =
        useState([]);

    const [loading, setLoading] =
        useState(true);

    const [refreshing, setRefreshing] =
        useState(false);

    const [search, setSearch] =
        useState("");

    const [statusFilter, setStatusFilter] =
        useState("all");

    const [categoryFilter, setCategoryFilter] =
        useState("all");

    const [testingId, setTestingId] =
        useState(null);

    const [syncingId, setSyncingId] =
        useState(null);

    const [error, setError] =
        useState(null);

    const [message, setMessage] =
        useState(null);

    /* ---------------------------------------------------------------------- */
    /* Load Connections                                                        */
    /* ---------------------------------------------------------------------- */

    async function loadConnections(showLoader = true) {
        if (showLoader) {
            setLoading(true);
        } else {
            setRefreshing(true);
        }

        setError(null);

        try {
            const response = await apiRequest(
                `/sources?organization_id=${organizationId}`
            );

            const sources =
                response?.sources ||
                response?.data ||
                [];

            setConnections(
                Array.isArray(sources)
                    ? sources
                    : []
            );
        } catch (requestError) {
            setError(
                requestError?.message ||
                "Unable to load configured connections."
            );
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }

    useEffect(() => {
        loadConnections(true);
    }, [organizationId]);

    /* ---------------------------------------------------------------------- */
    /* Filters                                                                 */
    /* ---------------------------------------------------------------------- */

    const categories = useMemo(() => {
        const values = new Set();

        connections.forEach((source) => {
            const metadata =
                getConnectorMetadata(source);

            if (metadata?.category) {
                values.add(metadata.category);
            }
        });

        return Array.from(values);
    }, [connections]);

    const filteredConnections = useMemo(() => {
        const query = search.trim().toLowerCase();

        return connections.filter((source) => {
            const metadata =
                getConnectorMetadata(source);

            const status =
                getSourceStatus(source);

            const matchesSearch =
                !query ||
                String(
                    source?.name || ""
                )
                    .toLowerCase()
                    .includes(query) ||
                String(
                    source?.source_type || ""
                )
                    .toLowerCase()
                    .includes(query) ||
                String(
                    metadata?.name || ""
                )
                    .toLowerCase()
                    .includes(query) ||
                String(
                    metadata?.category_label || ""
                )
                    .toLowerCase()
                    .includes(query);

            const matchesStatus =
                statusFilter === "all" ||
                status === statusFilter;

            const matchesCategory =
                categoryFilter === "all" ||
                metadata?.category ===
                categoryFilter;

            return (
                matchesSearch &&
                matchesStatus &&
                matchesCategory
            );
        });
    }, [
        connections,
        search,
        statusFilter,
        categoryFilter,
    ]);

    /* ---------------------------------------------------------------------- */
    /* Test Connection                                                         */
    /* ---------------------------------------------------------------------- */

    async function handleTest(source) {
        if (!source?.id) return;

        setTestingId(source.id);
        setMessage(null);
        setError(null);

        try {
            const response = await apiRequest(
                `/sources/${source.id}/test`,
                {
                    method: "POST",
                }
            );

            setMessage(
                response?.message ||
                `${source.name || "Connection"} test completed.`
            );
            if (showToast) {
                showToast(response?.message || `${source.name || "Connection"} test completed.`, "success");
            }

            await loadConnections(false);
        } catch (requestError) {
            setError(
                requestError?.message ||
                "Connection test failed."
            );
            if (showToast) {
                showToast(requestError?.message || "Connection test failed.", "error");
            }
        } finally {
            setTestingId(null);
        }
    }

    /* ---------------------------------------------------------------------- */
    /* Sync Connection                                                         */
    /* ---------------------------------------------------------------------- */

    async function handleSync(source) {
        if (!source?.id) return;

        setSyncingId(source.id);
        setMessage(null);
        setError(null);

        try {
            const response = await apiRequest(
                `/sources/${source.id}/sync/continuous?use_mock_llm=true`,
                {
                    method: "POST",
                }
            );

            setMessage(
                response?.message ||
                `${source.name || "Connection"} synchronization completed.`
            );
            if (showToast) {
                showToast(response?.message || `${source.name || "Connection"} synchronization completed.`, "success");
            }

            await loadConnections(false);
        } catch (requestError) {
            setError(
                requestError?.message ||
                "Synchronization failed."
            );
            if (showToast) {
                showToast(requestError?.message || "Synchronization failed.", "error");
            }
        } finally {
            setSyncingId(null);
        }
    }

    /* ---------------------------------------------------------------------- */
    /* Sync All                                                                 */
    /* ---------------------------------------------------------------------- */

    async function handleSyncAll() {
        if (!connections.length) return;

        setMessage(null);
        setError(null);

        try {
            /*
             * Keep execution sequential.
             * This avoids overwhelming source systems and
             * preserves predictable connector lifecycle execution.
             */
            for (const source of connections) {
                if (!source?.id) continue;

                setSyncingId(source.id);

                try {
                    await apiRequest(
                        `/sources/${source.id}/sync/continuous?use_mock_llm=true`,
                        {
                            method: "POST",
                        }
                    );
                } catch (syncError) {
                    console.error(
                        `Sync failed for source ${source.id}`,
                        syncError
                    );
                }
            }

            setMessage(
                "Connector synchronization completed."
            );

            await loadConnections(false);
        } catch (requestError) {
            setError(
                requestError?.message ||
                "Unable to synchronize connectors."
            );
        } finally {
            setSyncingId(null);
        }
    }

    /* ---------------------------------------------------------------------- */
    /* Statistics                                                              */
    /* ---------------------------------------------------------------------- */

    const statistics = useMemo(() => {
        let healthy = 0;
        let running = 0;
        let failed = 0;

        connections.forEach((source) => {
            const status =
                getSourceStatus(source);

            if (status === "healthy") healthy += 1;
            if (status === "running") running += 1;
            if (status === "failed") failed += 1;
        });

        return {
            total: connections.length,
            healthy,
            running,
            failed,
        };
    }, [connections]);

    /* ---------------------------------------------------------------------- */
    /* Loading                                                                 */
    /* ---------------------------------------------------------------------- */

    if (loading) {
        return (
            <div className="connections-loading">
                <style>{`
          .connections-loading {
            min-height: 320px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 9px;
            color: #64748b;
            font-size: 13px;
          }

          .status-spin {
            animation: connections-spin 1s linear infinite;
          }

          @keyframes connections-spin {
            from {
              transform: rotate(0deg);
            }

            to {
              transform: rotate(360deg);
            }
          }
        `}</style>

                <Loader2
                    size={24}
                    className="status-spin"
                />

                Loading connections...
            </div>
        );
    }

    /* ---------------------------------------------------------------------- */
    /* Render                                                                  */
    /* ---------------------------------------------------------------------- */

    return (
        <div className="connections-page">
            <style>{`
        .connections-page {
          width: 100%;
          min-height: 100%;
          box-sizing: border-box;
          padding: 24px;
          background: #f8fafc;
          color: #0f172a;
        }

        .connections-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 20px;
          margin-bottom: 20px;
        }

        .connections-title {
          margin: 0;
          font-size: 23px;
          font-weight: 700;
          letter-spacing: -0.02em;
        }

        .connections-subtitle {
          margin: 5px 0 0;
          color: #64748b;
          font-size: 13px;
        }

        .connections-header-actions {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .connection-button {
          border-radius: 8px;
          padding: 9px 13px;
          display: inline-flex;
          align-items: center;
          gap: 7px;
          cursor: pointer;
          font-size: 12px;
          font-weight: 600;
          border: 1px solid #e2e8f0;
          background: white;
          color: #334155;
        }

        .connection-button:hover {
          background: #f8fafc;
        }

        .connection-button.primary {
          color: #0f172a;
          background: var(--primary, #ffab4a);
          border-color: var(--primary-hover, #f5982c);
        }

        .connection-button.primary:hover {
          background: var(--primary-hover, #f5982c);
        }

        .connection-button:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .connection-stats {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
          margin-bottom: 18px;
        }

        .connection-stat {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          padding: 13px;
        }

        .connection-stat-label {
          color: #64748b;
          font-size: 11px;
          margin-bottom: 4px;
        }

        .connection-stat-value {
          font-size: 20px;
          font-weight: 700;
        }

        .connection-stat-value.healthy {
          color: #15803d;
        }

        .connection-stat-value.running {
          color: #2563eb;
        }

        .connection-stat-value.failed {
          color: #dc2626;
        }

        .connections-toolbar {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          padding: 10px;
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 14px;
        }

        .search-box {
          position: relative;
          flex: 1;
          min-width: 220px;
        }

        .search-box svg {
          position: absolute;
          left: 10px;
          top: 50%;
          transform: translateY(-50%);
          color: #94a3b8;
        }

        .search-box input {
          width: 100%;
          box-sizing: border-box;
          height: 34px;
          padding: 0 10px 0 31px;
          border-radius: 7px;
          border: 1px solid #e2e8f0;
          outline: none;
          font-size: 12px;
          color: #334155;
        }

        .search-box input:focus {
          border-color: #a5b4fc;
          box-shadow: 0 0 0 2px #eef2ff;
        }

        .filter-select {
          height: 34px;
          border-radius: 7px;
          border: 1px solid #e2e8f0;
          background: white;
          color: #475569;
          padding: 0 9px;
          font-size: 12px;
          outline: none;
        }

        .connections-results {
          color: #64748b;
          font-size: 11px;
          margin: 0 0 9px 2px;
        }

        .connection-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .connection-card {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 11px;
          padding: 15px;
          display: grid;
          grid-template-columns: minmax(0, 1.4fr) minmax(330px, 0.9fr) auto;
          align-items: center;
          gap: 15px;
        }

        .connection-card:hover {
          border-color: #cbd5e1;
        }

        .connection-card-main {
          min-width: 0;
          display: flex;
          align-items: flex-start;
          gap: 11px;
        }

        .connection-icon {
          flex: 0 0 auto;
          width: 42px;
          height: 42px;
          border-radius: 10px;
          background: var(--primary-50, #fff9f2);
          border: 1px solid var(--primary-200, #ffd8a8);
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--primary-dark, #c96e07);
          overflow: hidden;
        }

        .connection-icon img {
          width: 29px;
          height: 29px;
          object-fit: contain;
        }

        .connection-info {
          min-width: 0;
        }

        .connection-title-row {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .connection-title-row h3 {
          margin: 0;
          font-size: 14px;
          font-weight: 700;
        }

        .status-badge {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 4px 8px;
          border-radius: 999px;
          font-size: 10px;
          font-weight: 600;
        }

        .status-healthy {
          background: #ecfdf5;
          color: #047857;
        }

        .status-running {
          background: #eff6ff;
          color: #2563eb;
        }

        .status-failed {
          background: #fef2f2;
          color: #dc2626;
        }

        .status-unknown {
          background: #f1f5f9;
          color: #64748b;
        }

        .status-spin {
          animation: connections-spin 1s linear infinite;
        }

        @keyframes connections-spin {
          from {
            transform: rotate(0deg);
          }

          to {
            transform: rotate(360deg);
          }
        }

        .connection-type {
          margin-top: 3px;
          color: #64748b;
          font-size: 11px;
        }

        .connection-description {
          margin: 5px 0 0;
          color: #94a3b8;
          font-size: 11px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 480px;
        }

        .connection-meta {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 9px;
          margin-top: 8px;
          color: #64748b;
          font-size: 10px;
        }

        .connection-meta span {
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }

        .connection-metrics {
          display: grid;
          grid-template-columns: repeat(4, minmax(65px, 1fr));
          gap: 7px;
        }

        .connection-metric {
          padding: 8px;
          border-radius: 7px;
          background: #f8fafc;
          text-align: center;
        }

        .connection-metric span {
          display: block;
          color: #94a3b8;
          font-size: 9px;
          margin-bottom: 3px;
        }

        .connection-metric strong {
          font-size: 13px;
          color: #334155;
        }

        .connection-actions {
          display: flex;
          align-items: center;
          gap: 5px;
        }

        .connection-action {
          height: 31px;
          padding: 0 9px;
          border-radius: 7px;
          display: inline-flex;
          align-items: center;
          gap: 5px;
          cursor: pointer;
          font-size: 10px;
          font-weight: 600;
          white-space: nowrap;
        }

        .connection-action.secondary {
          background: white;
          border: 1px solid #e2e8f0;
          color: #475569;
        }

        .connection-action.secondary:hover {
          background: #f8fafc;
        }

        .connection-action:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .message-banner {
          margin-bottom: 13px;
          padding: 9px 11px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          gap: 7px;
          font-size: 11px;
        }

        .message-success {
          color: #047857;
          background: #ecfdf5;
          border: 1px solid #bbf7d0;
        }

        .message-error {
          color: #b91c1c;
          background: #fef2f2;
          border: 1px solid #fecaca;
        }

        .connections-empty {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 11px;
          min-height: 260px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 30px;
          color: #64748b;
        }

        .connections-empty-icon {
          width: 44px;
          height: 44px;
          border-radius: 10px;
          background: #f1f5f9;
          color: #94a3b8;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 10px;
        }

        .connections-empty h3 {
          margin: 0;
          color: #334155;
          font-size: 14px;
        }

        .connections-empty p {
          max-width: 400px;
          margin: 6px 0 14px;
          font-size: 11px;
          line-height: 1.5;
        }

        @media (max-width: 1150px) {
          .connection-card {
            grid-template-columns: 1fr;
          }

          .connection-actions {
            justify-content: flex-end;
          }
        }

        @media (max-width: 800px) {
          .connections-page {
            padding: 15px;
          }

          .connections-header {
            flex-direction: column;
          }

          .connections-header-actions {
            width: 100%;
            flex-wrap: wrap;
          }

          .connection-stats {
            grid-template-columns: repeat(2, 1fr);
          }

          .connections-toolbar {
            flex-wrap: wrap;
          }

          .search-box {
            min-width: 100%;
          }
        }

        @media (max-width: 500px) {
          .connection-stats {
            grid-template-columns: 1fr;
          }

          .connection-metrics {
            grid-template-columns: repeat(2, 1fr);
          }

          .connection-actions {
            justify-content: flex-start;
            flex-wrap: wrap;
          }
        }
      `}</style>

            {/* ---------------------------------------------------------------- */}
            {/* Header                                                            */}
            {/* ---------------------------------------------------------------- */}

            <div className="connections-header">
                <div>
                    <h1 className="connections-title">
                        Connections
                    </h1>

                    <p className="connections-subtitle">
                        Manage configured data sources and
                        monitor their connector lifecycle.
                    </p>
                </div>

                <div className="connections-header-actions">
                    <button
                        type="button"
                        className="connection-button"
                        onClick={() =>
                            loadConnections(false)
                        }
                        disabled={refreshing}
                    >
                        <RefreshCw
                            size={14}
                            className={
                                refreshing
                                    ? "status-spin"
                                    : ""
                            }
                        />
                        Refresh
                    </button>

                    <button
                        type="button"
                        className="connection-button"
                        onClick={handleSyncAll}
                        disabled={
                            !connections.length ||
                            Boolean(syncingId)
                        }
                    >
                        {syncingId ? (
                            <Loader2
                                size={14}
                                className="status-spin"
                            />
                        ) : (
                            <RefreshCw size={14} />
                        )}
                        Sync All
                    </button>

                    {onAddConnection && (
                        <button
                            type="button"
                            className="connection-button primary"
                            onClick={onAddConnection}
                        >
                            <Plus size={14} />
                            Add Connection
                        </button>
                    )}
                </div>
            </div>

            {/* ---------------------------------------------------------------- */}
            {/* Messages                                                          */}
            {/* ---------------------------------------------------------------- */}

            {message && (
                <div className="message-banner message-success">
                    <CheckCircle2 size={14} />
                    {message}
                </div>
            )}

            {error && (
                <div className="message-banner message-error">
                    <AlertCircle size={14} />
                    {error}
                </div>
            )}

            {/* ---------------------------------------------------------------- */}
            {/* Statistics                                                        */}
            {/* ---------------------------------------------------------------- */}

            <div className="connection-stats">
                <div className="connection-stat">
                    <div className="connection-stat-label">
                        Total Connections
                    </div>
                    <div className="connection-stat-value">
                        {formatNumber(statistics.total)}
                    </div>
                </div>

                <div className="connection-stat">
                    <div className="connection-stat-label">
                        Healthy
                    </div>
                    <div className="connection-stat-value healthy">
                        {formatNumber(statistics.healthy)}
                    </div>
                </div>

                <div className="connection-stat">
                    <div className="connection-stat-label">
                        Syncing
                    </div>
                    <div className="connection-stat-value running">
                        {formatNumber(statistics.running)}
                    </div>
                </div>

                <div className="connection-stat">
                    <div className="connection-stat-label">
                        Failed
                    </div>
                    <div className="connection-stat-value failed">
                        {formatNumber(statistics.failed)}
                    </div>
                </div>
            </div>

            {/* ---------------------------------------------------------------- */}
            {/* Toolbar                                                           */}
            {/* ---------------------------------------------------------------- */}

            <div className="connections-toolbar">
                <div className="search-box">
                    <Search size={15} />

                    <input
                        type="text"
                        placeholder="Search connections..."
                        value={search}
                        onChange={(event) =>
                            setSearch(event.target.value)
                        }
                    />
                </div>

                <select
                    className="filter-select"
                    value={statusFilter}
                    onChange={(event) =>
                        setStatusFilter(event.target.value)
                    }
                >
                    <option value="all">
                        All Statuses
                    </option>
                    <option value="healthy">
                        Healthy
                    </option>
                    <option value="running">
                        Syncing
                    </option>
                    <option value="failed">
                        Failed
                    </option>
                    <option value="unknown">
                        Unknown
                    </option>
                </select>

                <select
                    className="filter-select"
                    value={categoryFilter}
                    onChange={(event) =>
                        setCategoryFilter(event.target.value)
                    }
                >
                    <option value="all">
                        All Categories
                    </option>

                    {categories.map((category) => {
                        const categoryConnector =
                            ENTERPRISE_CONNECTORS.find(
                                (item) =>
                                    item.category ===
                                    category
                            );

                        return (
                            <option
                                key={category}
                                value={category}
                            >
                                {categoryConnector?.category_label ||
                                    category}
                            </option>
                        );
                    })}
                </select>
            </div>

            <div className="connections-results">
                Showing{" "}
                <strong>
                    {filteredConnections.length}
                </strong>{" "}
                of{" "}
                <strong>
                    {connections.length}
                </strong>{" "}
                configured connections
            </div>

            {/* ---------------------------------------------------------------- */}
            {/* Connections                                                       */}
            {/* ---------------------------------------------------------------- */}

            {filteredConnections.length > 0 ? (
                <div className="connection-list">
                    {filteredConnections.map(
                        (source) => (
                            <ConnectionCard
                                key={source.id}
                                source={source}
                                onView={
                                    onViewConnection ||
                                    (() => { })
                                }
                                onTest={handleTest}
                                onSync={handleSync}
                                testing={
                                    testingId === source.id
                                }
                                syncing={
                                    syncingId === source.id
                                }
                            />
                        )
                    )}
                </div>
            ) : (
                <div className="connections-empty">
                    <div className="connections-empty-icon">
                        <Settings2 size={20} />
                    </div>

                    <h3>
                        {connections.length
                            ? "No matching connections"
                            : "No connections configured"}
                    </h3>

                    <p>
                        {connections.length
                            ? "Try changing the search or filters."
                            : "Configure a data connector to begin discovering and synchronizing trusted source data."}
                    </p>

                    {!connections.length &&
                        onAddConnection && (
                            <button
                                type="button"
                                className="connection-button primary"
                                onClick={onAddConnection}
                            >
                                <Plus size={14} />
                                Add Connection
                            </button>
                        )}
                </div>
            )}
        </div>
    );
}