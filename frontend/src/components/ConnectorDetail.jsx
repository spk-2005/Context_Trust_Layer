// frontend/src/components/ConnectorDetail.jsx

import React, { useEffect, useMemo, useState } from "react";
import {
    ArrowLeft,
    CheckCircle2,
    CircleAlert,
    Clock3,
    Database,
    GitBranch,
    History,
    Loader2,
    RefreshCw,
    Search,
    ShieldCheck,
    Activity,
    ChevronDown,
    ChevronRight,
    FileText,
    Layers3,
    Network,
    AlertTriangle,
    Check,
    X,
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
/* Lifecycle                                                                  */
/* -------------------------------------------------------------------------- */

const LIFECYCLE_STAGES = [
    {
        key: "configure",
        label: "Configure",
        description: "Connector configuration",
        icon: Database,
    },
    {
        key: "authenticate",
        label: "Authenticate",
        description: "Validate credentials",
        icon: ShieldCheck,
    },
    {
        key: "test",
        label: "Test",
        description: "Test source connectivity",
        icon: CheckCircle2,
    },
    {
        key: "discover",
        label: "Discover",
        description: "Discover available resources",
        icon: Search,
    },
    {
        key: "select",
        label: "Select",
        description: "Select resources to ingest",
        icon: Layers3,
    },
    {
        key: "initial_sync",
        label: "Initial Sync",
        description: "First synchronization",
        icon: RefreshCw,
    },
    {
        key: "continuous_sync",
        label: "Continuous Sync",
        description: "Ongoing synchronization",
        icon: Activity,
    },
    {
        key: "normalize",
        label: "Normalize",
        description: "Normalize source data",
        icon: FileText,
    },
    {
        key: "provenance",
        label: "Provenance",
        description: "Track source provenance",
        icon: History,
    },
    {
        key: "conflict_detection",
        label: "Conflict Detection",
        description: "Detect conflicting information",
        icon: AlertTriangle,
    },
    {
        key: "lineage",
        label: "Lineage",
        description: "Track data lineage",
        icon: GitBranch,
    },
    {
        key: "monitoring",
        label: "Monitoring",
        description: "Monitor connector health",
        icon: Network,
    },
];

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

function normalizeStatus(value) {
    if (!value) return "unknown";

    const status = String(value).toLowerCase();

    if (
        [
            "success",
            "successful",
            "connected",
            "active",
            "healthy",
            "completed",
            "complete",
            "ok",
        ].includes(status)
    ) {
        return "success";
    }

    if (
        [
            "running",
            "processing",
            "syncing",
            "in_progress",
            "pending",
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
    if (value === null || value === undefined) return "0";

    return Number(value).toLocaleString();
}

function getLifecycleValue(lifecycle, key) {
    if (!lifecycle) return null;

    return (
        lifecycle[key] ||
        lifecycle?.stages?.[key] ||
        lifecycle?.[`${key}_stage`] ||
        null
    );
}

function getStageStatus(lifecycle, key, currentStage) {
    const stage = getLifecycleValue(lifecycle, key);

    if (stage?.status) {
        return normalizeStatus(stage.status);
    }

    const currentIndex = LIFECYCLE_STAGES.findIndex(
        (item) => item.key === currentStage
    );

    const stageIndex = LIFECYCLE_STAGES.findIndex(
        (item) => item.key === key
    );

    if (currentIndex >= 0 && stageIndex >= 0) {
        if (stageIndex < currentIndex) return "success";
        if (stageIndex === currentIndex) return "running";
    }

    return "unknown";
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

/* -------------------------------------------------------------------------- */
/* Status Badge                                                               */
/* -------------------------------------------------------------------------- */

function StatusBadge({ status }) {
    const normalized = normalizeStatus(status);

    const config = {
        success: {
            label: "Healthy",
            icon: CheckCircle2,
            className: "status-success",
        },
        running: {
            label: "Running",
            icon: Loader2,
            className: "status-running",
        },
        failed: {
            label: "Failed",
            icon: CircleAlert,
            className: "status-failed",
        },
        unknown: {
            label: "Unknown",
            icon: Clock3,
            className: "status-unknown",
        },
    };

    const item = config[normalized];
    const Icon = item.icon;

    return (
        <span className={`status-badge ${item.className}`}>
            <Icon
                size={14}
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
/* Lifecycle Step                                                             */
/* -------------------------------------------------------------------------- */

function LifecycleStep({
    stage,
    status,
    isExpanded,
    onToggle,
    details,
}) {
    const Icon = stage.icon;

    return (
        <div className="lifecycle-step">
            <button
                type="button"
                className="lifecycle-step-button"
                onClick={onToggle}
            >
                <div className={`lifecycle-icon ${status}`}>
                    {status === "success" ? (
                        <Check size={16} />
                    ) : status === "failed" ? (
                        <X size={16} />
                    ) : status === "running" ? (
                        <Loader2 size={16} className="status-spin" />
                    ) : (
                        <Icon size={16} />
                    )}
                </div>

                <div className="lifecycle-step-content">
                    <div className="lifecycle-step-title">
                        {stage.label}
                    </div>

                    <div className="lifecycle-step-description">
                        {stage.description}
                    </div>
                </div>

                <div className="lifecycle-step-status">
                    {status === "success" && (
                        <span className="stage-status-text success">
                            Complete
                        </span>
                    )}

                    {status === "running" && (
                        <span className="stage-status-text running">
                            Running
                        </span>
                    )}

                    {status === "failed" && (
                        <span className="stage-status-text failed">
                            Failed
                        </span>
                    )}

                    {status === "unknown" && (
                        <span className="stage-status-text">
                            Not run
                        </span>
                    )}

                    {isExpanded ? (
                        <ChevronDown size={16} />
                    ) : (
                        <ChevronRight size={16} />
                    )}
                </div>
            </button>

            {isExpanded && (
                <div className="lifecycle-details">
                    {details ? (
                        <>
                            {details.message && (
                                <div className="detail-message">
                                    {details.message}
                                </div>
                            )}

                            <div className="detail-grid">
                                {details.started_at && (
                                    <DetailItem
                                        label="Started"
                                        value={formatDate(details.started_at)}
                                    />
                                )}

                                {details.completed_at && (
                                    <DetailItem
                                        label="Completed"
                                        value={formatDate(details.completed_at)}
                                    />
                                )}

                                {details.execution_time_ms !== undefined && (
                                    <DetailItem
                                        label="Execution Time"
                                        value={`${formatNumber(
                                            details.execution_time_ms
                                        )} ms`}
                                    />
                                )}

                                {details.records !== undefined && (
                                    <DetailItem
                                        label="Records"
                                        value={formatNumber(details.records)}
                                    />
                                )}

                                {details.documents !== undefined && (
                                    <DetailItem
                                        label="Documents"
                                        value={formatNumber(details.documents)}
                                    />
                                )}

                                {details.claims !== undefined && (
                                    <DetailItem
                                        label="Claims"
                                        value={formatNumber(details.claims)}
                                    />
                                )}

                                {details.conflicts !== undefined && (
                                    <DetailItem
                                        label="Conflicts"
                                        value={formatNumber(details.conflicts)}
                                    />
                                )}
                            </div>

                            {details.error && (
                                <div className="stage-error">
                                    <CircleAlert size={15} />
                                    {details.error}
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="empty-stage-detail">
                            No lifecycle execution information is available yet.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

/* -------------------------------------------------------------------------- */
/* Detail Item                                                                */
/* -------------------------------------------------------------------------- */

function DetailItem({ label, value }) {
    return (
        <div className="detail-item">
            <span>{label}</span>
            <strong>{value}</strong>
        </div>
    );
}

/* -------------------------------------------------------------------------- */
/* Metric Card                                                                */
/* -------------------------------------------------------------------------- */

function MetricCard({ label, value, icon: Icon }) {
    return (
        <div className="metric-card">
            <div className="metric-card-icon">
                <Icon size={17} />
            </div>

            <div>
                <div className="metric-card-label">
                    {label}
                </div>

                <div className="metric-card-value">
                    {value}
                </div>
            </div>
        </div>
    );
}

/* -------------------------------------------------------------------------- */
/* Main Component                                                             */
/* -------------------------------------------------------------------------- */

export default function ConnectorDetail({
    sourceId,
    organizationId = DEFAULT_ORGANIZATION_ID,
    onBack,
    onEdit,
    showToast,
}) {
    const [source, setSource] = useState(null);
    const [lifecycle, setLifecycle] = useState(null);
    const [monitoring, setMonitoring] = useState(null);

    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [testing, setTesting] = useState(false);

    const [error, setError] = useState(null);
    const [actionMessage, setActionMessage] =
        useState(null);

    const [expandedStage, setExpandedStage] =
        useState("configure");

    const connectorMetadata = useMemo(
        () => getConnectorMetadata(source),
        [source]
    );

    /* ---------------------------------------------------------------------- */
    /* Load Source                                                            */
    /* ---------------------------------------------------------------------- */

    async function loadSource(showLoader = true) {
        if (!sourceId) return;

        if (showLoader) {
            setLoading(true);
        } else {
            setRefreshing(true);
        }

        setError(null);

        try {
            const response = await apiRequest(
                `/sources/${sourceId}`
            );

            const sourceData =
                response?.source ||
                response?.data ||
                response;

            setSource(sourceData);

            if (
                response?.lifecycle ||
                sourceData?.lifecycle
            ) {
                setLifecycle(
                    response?.lifecycle ||
                    sourceData?.lifecycle
                );
            }

            if (
                response?.monitoring ||
                sourceData?.monitoring
            ) {
                setMonitoring(
                    response?.monitoring ||
                    sourceData?.monitoring
                );
            }
        } catch (requestError) {
            /*
             * Some deployments expose the configured sources
             * collection but not the single-source endpoint.
             * Fall back to the collection endpoint.
             */
            try {
                const response = await apiRequest(
                    `/sources?organization_id=${organizationId}`
                );

                const sources =
                    response?.sources ||
                    response?.data ||
                    [];

                const matchingSource = sources.find(
                    (item) =>
                        String(item.id) === String(sourceId)
                );

                if (!matchingSource) {
                    throw requestError;
                }

                setSource(matchingSource);
                setLifecycle(
                    matchingSource.lifecycle || null
                );
                setMonitoring(
                    matchingSource.monitoring || null
                );
            } catch (fallbackError) {
                setError(
                    fallbackError?.message ||
                    requestError?.message ||
                    "Unable to load connector."
                );
            }
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }

    useEffect(() => {
        loadSource(true);
    }, [sourceId]);

    /* ---------------------------------------------------------------------- */
    /* Test                                                                    */
    /* ---------------------------------------------------------------------- */

    async function handleTestConnection() {
        if (!sourceId) return;

        setTesting(true);
        setActionMessage(null);
        setError(null);

        try {
            const response = await apiRequest(
                `/sources/${sourceId}/test`,
                {
                    method: "POST",
                }
            );

            setActionMessage(
                response?.message ||
                "Connection test completed successfully."
            );
            if (showToast) {
                showToast(response?.message || "Connection test completed successfully.", "success");
            }

            await loadSource(false);
        } catch (requestError) {
            setError(
                requestError?.message ||
                "Connection test failed."
            );
            if (showToast) {
                showToast(requestError?.message || "Connection test failed.", "error");
            }
        } finally {
            setTesting(false);
        }
    }

    /* ---------------------------------------------------------------------- */
    /* Sync                                                                     */
    /* ---------------------------------------------------------------------- */

    async function handleSync() {
        if (!sourceId) return;

        setSyncing(true);
        setActionMessage(null);
        setError(null);

        try {
            const response = await apiRequest(
                `/sources/${sourceId}/sync/continuous?use_mock_llm=true`,
                {
                    method: "POST",
                }
            );

            setActionMessage(
                response?.message ||
                "Synchronization started successfully."
            );
            if (showToast) {
                showToast(response?.message || "Synchronization started successfully.", "success");
            }

            if (response?.lifecycle) {
                setLifecycle(response.lifecycle);
            }

            if (response?.monitoring) {
                setMonitoring(response.monitoring);
            }

            await loadSource(false);
        } catch (requestError) {
            setError(
                requestError?.message ||
                "Synchronization failed."
            );
            if (showToast) {
                showToast(requestError?.message || "Synchronization failed.", "error");
            }
        } finally {
            setSyncing(false);
        }
    }

    /* ---------------------------------------------------------------------- */
    /* Render Loading                                                          */
    /* ---------------------------------------------------------------------- */

    if (loading) {
        return (
            <div className="connector-detail-loading">
                <Loader2
                    size={28}
                    className="status-spin"
                />
                <span>Loading connector...</span>
            </div>
        );
    }

    /* ---------------------------------------------------------------------- */
    /* Render Error                                                             */
    /* ---------------------------------------------------------------------- */

    if (!source) {
        return (
            <div className="connector-detail-error">
                <CircleAlert size={24} />

                <h3>Connector not found</h3>

                <p>
                    {error ||
                        "The requested connector could not be loaded."}
                </p>

                <button
                    type="button"
                    onClick={onBack}
                    className="secondary-button"
                >
                    <ArrowLeft size={16} />
                    Back to Connectors
                </button>
            </div>
        );
    }

    const sourceType = getSourceType(source);

    const currentStage =
        lifecycle?.current_stage ||
        lifecycle?.currentStage ||
        source?.current_stage ||
        source?.lifecycle_stage ||
        null;

    const overallStatus =
        monitoring?.status ||
        lifecycle?.status ||
        source?.status ||
        "unknown";

    const connectionConfig =
        source.connection_config ||
        source.connectionConfig ||
        {};

    const selectedResources =
        source.selected_resources ||
        source.selectedResources ||
        lifecycle?.selected_resources ||
        [];

    const discoveredResources =
        source.discovered_resources ||
        source.discoveredResources ||
        lifecycle?.discovered_resources ||
        [];

    const metrics = {
        documents:
            monitoring?.documents_synced ??
            lifecycle?.documents_synced ??
            source?.documents_synced ??
            0,

        claims:
            monitoring?.claims_extracted ??
            lifecycle?.claims_extracted ??
            source?.claims_extracted ??
            0,

        conflicts:
            monitoring?.conflicts_detected ??
            lifecycle?.conflicts_detected ??
            source?.conflicts_detected ??
            0,

        lastSync:
            source?.last_synced_at ||
            monitoring?.last_sync_at ||
            lifecycle?.synced_at ||
            null,
    };

    return (
        <div className="connector-detail-page">
            <style>{`
        .connector-detail-page {
          width: 100%;
          min-height: 100%;
          padding: 24px;
          box-sizing: border-box;
          background: #f8fafc;
          color: #0f172a;
        }

        .connector-detail-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 20px;
          margin-bottom: 22px;
        }

        .connector-detail-title-area {
          display: flex;
          align-items: flex-start;
          gap: 14px;
        }

        .back-button {
          width: 38px;
          height: 38px;
          border: 1px solid #e2e8f0;
          border-radius: 9px;
          background: white;
          color: #475569;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .back-button:hover {
          background: #f1f5f9;
          color: #0f172a;
        }

        .connector-detail-icon {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          background: var(--primary-50, #fff9f2);
          border: 1px solid var(--primary-200, #ffd8a8);
          color: var(--primary-dark, #c96e07);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 17px;
          overflow: hidden;
        }

        .connector-detail-icon img {
          width: 32px;
          height: 32px;
          object-fit: contain;
        }

        .connector-detail-title {
          margin: 0;
          font-size: 23px;
          font-weight: 700;
          letter-spacing: -0.02em;
        }

        .connector-detail-subtitle {
          margin: 5px 0 0;
          color: #64748b;
          font-size: 13px;
        }

        .connector-detail-actions {
          display: flex;
          align-items: center;
          gap: 9px;
        }

        .primary-button,
        .secondary-button,
        .danger-button {
          border-radius: 8px;
          padding: 9px 13px;
          display: inline-flex;
          align-items: center;
          gap: 7px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
          transition: all 0.15s ease;
        }

        .primary-button {
          background: var(--primary, #ffab4a);
          border: 1px solid var(--primary-hover, #f5982c);
          color: #0f172a;
        }

        .primary-button:hover {
          background: var(--primary-hover, #f5982c);
        }

        .secondary-button {
          background: white;
          border: 1px solid #e2e8f0;
          color: #334155;
        }

        .secondary-button:hover {
          background: #f8fafc;
        }

        .primary-button:disabled,
        .secondary-button:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .connector-summary {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 18px;
          margin-bottom: 18px;
        }

        .summary-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 15px;
          margin-bottom: 18px;
        }

        .summary-status {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .status-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          border-radius: 999px;
          padding: 5px 9px;
          font-size: 12px;
          font-weight: 600;
        }

        .status-success {
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
          animation: connector-spin 1s linear infinite;
        }

        @keyframes connector-spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        .summary-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
        }

        .metric-card {
          border: 1px solid #e2e8f0;
          border-radius: 9px;
          padding: 12px;
          display: flex;
          gap: 10px;
          align-items: center;
        }

        .metric-card-icon {
          width: 32px;
          height: 32px;
          border-radius: 8px;
          background: #f1f5f9;
          color: #475569;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .metric-card-label {
          color: #64748b;
          font-size: 11px;
          margin-bottom: 3px;
        }

        .metric-card-value {
          font-size: 15px;
          font-weight: 700;
        }

        .connector-detail-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.5fr) minmax(300px, 0.8fr);
          gap: 18px;
          align-items: start;
        }

        .detail-panel {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          overflow: hidden;
        }

        .detail-panel-header {
          padding: 15px 17px;
          border-bottom: 1px solid #e2e8f0;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .detail-panel-title {
          font-size: 14px;
          font-weight: 700;
          margin: 0;
        }

        .detail-panel-subtitle {
          color: #64748b;
          font-size: 11px;
          margin-top: 3px;
        }

        .lifecycle {
          padding: 7px 17px 17px;
        }

        .lifecycle-step {
          border-bottom: 1px solid #f1f5f9;
        }

        .lifecycle-step:last-child {
          border-bottom: none;
        }

        .lifecycle-step-button {
          width: 100%;
          border: none;
          background: transparent;
          display: flex;
          align-items: center;
          text-align: left;
          padding: 11px 0;
          cursor: pointer;
          gap: 11px;
        }

        .lifecycle-icon {
          flex: 0 0 auto;
          width: 31px;
          height: 31px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f1f5f9;
          color: #64748b;
        }

        .lifecycle-icon.success {
          background: #dcfce7;
          color: #15803d;
        }

        .lifecycle-icon.running {
          background: #dbeafe;
          color: #2563eb;
        }

        .lifecycle-icon.failed {
          background: #fee2e2;
          color: #dc2626;
        }

        .lifecycle-step-content {
          flex: 1;
          min-width: 0;
        }

        .lifecycle-step-title {
          font-size: 13px;
          font-weight: 650;
          color: #1e293b;
        }

        .lifecycle-step-description {
          margin-top: 2px;
          font-size: 11px;
          color: #94a3b8;
        }

        .lifecycle-step-status {
          display: flex;
          align-items: center;
          gap: 7px;
          color: #94a3b8;
          font-size: 11px;
        }

        .stage-status-text.success {
          color: #15803d;
        }

        .stage-status-text.running {
          color: #2563eb;
        }

        .stage-status-text.failed {
          color: #dc2626;
        }

        .lifecycle-details {
          margin: 0 0 10px 42px;
          padding: 10px;
          background: #f8fafc;
          border-radius: 8px;
        }

        .detail-message {
          color: #475569;
          font-size: 12px;
          margin-bottom: 9px;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }

        .detail-item {
          display: flex;
          flex-direction: column;
          gap: 3px;
        }

        .detail-item span {
          font-size: 10px;
          color: #94a3b8;
        }

        .detail-item strong {
          font-size: 11px;
          color: #334155;
        }

        .stage-error {
          margin-top: 9px;
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px;
          border-radius: 7px;
          background: #fef2f2;
          color: #b91c1c;
          font-size: 11px;
        }

        .empty-stage-detail {
          color: #94a3b8;
          font-size: 11px;
        }

        .side-section {
          padding: 16px;
          border-bottom: 1px solid #e2e8f0;
        }

        .side-section:last-child {
          border-bottom: none;
        }

        .side-section-title {
          font-size: 12px;
          font-weight: 700;
          margin-bottom: 10px;
          color: #334155;
        }

        .info-row {
          display: flex;
          justify-content: space-between;
          gap: 15px;
          padding: 7px 0;
          font-size: 11px;
        }

        .info-row span:first-child {
          color: #94a3b8;
        }

        .info-row span:last-child {
          color: #334155;
          text-align: right;
          word-break: break-word;
        }

        .resource-list {
          display: flex;
          flex-direction: column;
          gap: 5px;
          max-height: 240px;
          overflow-y: auto;
        }

        .resource-item {
          display: flex;
          align-items: center;
          gap: 7px;
          padding: 7px 8px;
          border-radius: 6px;
          background: #f8fafc;
          color: #475569;
          font-size: 11px;
        }

        .resource-item svg {
          color: #94a3b8;
          flex: 0 0 auto;
        }

        .message-banner {
          margin-bottom: 16px;
          border-radius: 9px;
          padding: 10px 12px;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
        }

        .message-success {
          background: #ecfdf5;
          color: #047857;
          border: 1px solid #bbf7d0;
        }

        .message-error {
          background: #fef2f2;
          color: #b91c1c;
          border: 1px solid #fecaca;
        }

        .connector-detail-loading,
        .connector-detail-error {
          min-height: 360px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 10px;
          color: #64748b;
          padding: 30px;
          text-align: center;
        }

        .connector-detail-error h3 {
          margin: 0;
          color: #1e293b;
        }

        .connector-detail-error p {
          margin: 0 0 8px;
          max-width: 500px;
          font-size: 13px;
        }

        .refreshing {
          animation: connector-spin 1s linear infinite;
        }

        @media (max-width: 1000px) {
          .summary-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .connector-detail-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 700px) {
          .connector-detail-page {
            padding: 15px;
          }

          .connector-detail-header,
          .summary-top {
            flex-direction: column;
            align-items: stretch;
          }

          .connector-detail-actions {
            justify-content: flex-start;
            flex-wrap: wrap;
          }

          .summary-grid {
            grid-template-columns: 1fr;
          }

          .detail-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>

            {/* ---------------------------------------------------------------- */}
            {/* Header                                                            */}
            {/* ---------------------------------------------------------------- */}

            <div className="connector-detail-header">
                <div className="connector-detail-title-area">
                    <button
                        type="button"
                        className="back-button"
                        onClick={onBack}
                        title="Back"
                    >
                        <ArrowLeft size={18} />
                    </button>

                    <div className="connector-detail-icon">
                        {connectorMetadata?.icon ? (
                            <img
                                src={connectorMetadata.icon}
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

                    <div>
                        <h1 className="connector-detail-title">
                            {source.name ||
                                connectorMetadata?.name ||
                                sourceType}
                        </h1>

                        <p className="connector-detail-subtitle">
                            {connectorMetadata?.description ||
                                `Configured ${sourceType} connector`}
                        </p>
                    </div>
                </div>

                <div className="connector-detail-actions">
                    <button
                        type="button"
                        className="secondary-button"
                        onClick={() => loadSource(false)}
                        disabled={refreshing}
                    >
                        <RefreshCw
                            size={15}
                            className={
                                refreshing
                                    ? "refreshing"
                                    : ""
                            }
                        />
                        Refresh
                    </button>

                    <button
                        type="button"
                        className="secondary-button"
                        onClick={handleTestConnection}
                        disabled={testing}
                    >
                        {testing ? (
                            <Loader2
                                size={15}
                                className="status-spin"
                            />
                        ) : (
                            <CheckCircle2 size={15} />
                        )}
                        Test
                    </button>

                    <button
                        type="button"
                        className="primary-button"
                        onClick={handleSync}
                        disabled={syncing}
                    >
                        {syncing ? (
                            <Loader2
                                size={15}
                                className="status-spin"
                            />
                        ) : (
                            <RefreshCw size={15} />
                        )}
                        Sync Now
                    </button>

                    {onEdit && (
                        <button
                            type="button"
                            className="secondary-button"
                            onClick={() => onEdit(source)}
                        >
                            Edit
                        </button>
                    )}
                </div>
            </div>

            {/* ---------------------------------------------------------------- */}
            {/* Messages                                                          */}
            {/* ---------------------------------------------------------------- */}

            {actionMessage && (
                <div className="message-banner message-success">
                    <CheckCircle2 size={15} />
                    {actionMessage}
                </div>
            )}

            {error && (
                <div className="message-banner message-error">
                    <CircleAlert size={15} />
                    {error}
                </div>
            )}

            {/* ---------------------------------------------------------------- */}
            {/* Summary                                                           */}
            {/* ---------------------------------------------------------------- */}

            <section className="connector-summary">
                <div className="summary-top">
                    <div className="summary-status">
                        <StatusBadge status={overallStatus} />

                        <span
                            style={{
                                color: "#64748b",
                                fontSize: "12px",
                            }}
                        >
                            Last sync:{" "}
                            {formatDate(metrics.lastSync)}
                        </span>
                    </div>

                    {currentStage && (
                        <span
                            style={{
                                fontSize: "11px",
                                color: "#64748b",
                            }}
                        >
                            Current stage:{" "}
                            <strong style={{ color: "#334155" }}>
                                {String(currentStage)
                                    .replaceAll("_", " ")
                                    .replace(/\b\w/g, (char) =>
                                        char.toUpperCase()
                                    )}
                            </strong>
                        </span>
                    )}
                </div>

                <div className="summary-grid">
                    <MetricCard
                        label="Documents Synced"
                        value={formatNumber(metrics.documents)}
                        icon={FileText}
                    />

                    <MetricCard
                        label="Claims Extracted"
                        value={formatNumber(metrics.claims)}
                        icon={Layers3}
                    />

                    <MetricCard
                        label="Conflicts Detected"
                        value={formatNumber(metrics.conflicts)}
                        icon={AlertTriangle}
                    />

                    <MetricCard
                        label="Selected Resources"
                        value={formatNumber(
                            Array.isArray(selectedResources)
                                ? selectedResources.length
                                : selectedResources
                        )}
                        icon={Database}
                    />
                </div>
            </section>

            {/* ---------------------------------------------------------------- */}
            {/* Main Content                                                      */}
            {/* ---------------------------------------------------------------- */}

            <div className="connector-detail-grid">
                {/* Lifecycle */}
                <section className="detail-panel">
                    <div className="detail-panel-header">
                        <div>
                            <h2 className="detail-panel-title">
                                Connector Lifecycle
                            </h2>

                            <div className="detail-panel-subtitle">
                                Configure → Authenticate → Test →
                                Discover → Select → Sync → Trust
                            </div>
                        </div>

                        <StatusBadge status={overallStatus} />
                    </div>

                    <div className="lifecycle">
                        {LIFECYCLE_STAGES.map((stage) => {
                            const status = getStageStatus(
                                lifecycle,
                                stage.key,
                                currentStage
                            );

                            const details =
                                getLifecycleValue(
                                    lifecycle,
                                    stage.key
                                );

                            return (
                                <LifecycleStep
                                    key={stage.key}
                                    stage={stage}
                                    status={status}
                                    details={details}
                                    isExpanded={
                                        expandedStage === stage.key
                                    }
                                    onToggle={() =>
                                        setExpandedStage(
                                            expandedStage === stage.key
                                                ? null
                                                : stage.key
                                        )
                                    }
                                />
                            );
                        })}
                    </div>
                </section>

                {/* Sidebar */}
                <div className="detail-panel">
                    {/* Connection */}
                    <div className="side-section">
                        <div className="side-section-title">
                            Connection
                        </div>

                        <div className="info-row">
                            <span>Connector</span>
                            <span>
                                {connectorMetadata?.name ||
                                    sourceType}
                            </span>
                        </div>

                        <div className="info-row">
                            <span>Source ID</span>
                            <span>{source.id}</span>
                        </div>

                        <div className="info-row">
                            <span>External ID</span>
                            <span>
                                {source.external_id || "—"}
                            </span>
                        </div>

                        <div className="info-row">
                            <span>Domain</span>
                            <span>
                                {source.domain || "—"}
                            </span>
                        </div>

                        <div className="info-row">
                            <span>Authority</span>
                            <span>
                                {source.authority_level || "—"}
                            </span>
                        </div>
                    </div>

                    {/* Resources */}
                    <div className="side-section">
                        <div className="side-section-title">
                            Discovered Resources
                        </div>

                        {Array.isArray(
                            discoveredResources
                        ) &&
                            discoveredResources.length > 0 ? (
                            <div className="resource-list">
                                {discoveredResources.map(
                                    (resource, index) => {
                                        const name =
                                            typeof resource ===
                                                "string"
                                                ? resource
                                                : resource?.name ||
                                                resource?.id ||
                                                resource?.resource_name ||
                                                `Resource ${index + 1}`;

                                        return (
                                            <div
                                                className="resource-item"
                                                key={`${name}-${index}`}
                                            >
                                                <Database size={13} />
                                                <span>{name}</span>
                                            </div>
                                        );
                                    }
                                )}
                            </div>
                        ) : (
                            <div className="empty-stage-detail">
                                No discovered resources yet.
                            </div>
                        )}
                    </div>

                    {/* Selected Resources */}
                    <div className="side-section">
                        <div className="side-section-title">
                            Selected Resources
                        </div>

                        {Array.isArray(
                            selectedResources
                        ) &&
                            selectedResources.length > 0 ? (
                            <div className="resource-list">
                                {selectedResources.map(
                                    (resource, index) => {
                                        const name =
                                            typeof resource ===
                                                "string"
                                                ? resource
                                                : resource?.name ||
                                                resource?.id ||
                                                resource?.resource_name ||
                                                `Resource ${index + 1}`;

                                        return (
                                            <div
                                                className="resource-item"
                                                key={`${name}-${index}`}
                                            >
                                                <Check size={13} />
                                                <span>{name}</span>
                                            </div>
                                        );
                                    }
                                )}
                            </div>
                        ) : (
                            <div className="empty-stage-detail">
                                No resources selected yet.
                            </div>
                        )}
                    </div>

                    {/* Monitoring */}
                    <div className="side-section">
                        <div className="side-section-title">
                            Monitoring
                        </div>

                        <div className="info-row">
                            <span>Status</span>
                            <span>
                                {monitoring?.status ||
                                    overallStatus ||
                                    "Unknown"}
                            </span>
                        </div>

                        <div className="info-row">
                            <span>Last Successful Sync</span>
                            <span>
                                {formatDate(
                                    monitoring?.last_successful_sync
                                )}
                            </span>
                        </div>

                        <div className="info-row">
                            <span>Last Error</span>
                            <span>
                                {monitoring?.last_error ||
                                    "None"}
                            </span>
                        </div>

                        <div className="info-row">
                            <span>Updated</span>
                            <span>
                                {formatDate(
                                    source.updated_at
                                )}
                            </span>
                        </div>
                    </div>

                    {/* Configuration */}
                    <div className="side-section">
                        <div className="side-section-title">
                            Configuration
                        </div>

                        {Object.keys(connectionConfig).length >
                            0 ? (
                            Object.entries(
                                connectionConfig
                            ).map(([key, value]) => {
                                /*
                                 * Never expose credentials or secrets
                                 * directly in the connector detail UI.
                                 */
                                const sensitive =
                                    /token|secret|password|key|credential|authorization/i.test(
                                        key
                                    );

                                let displayValue = value;

                                if (sensitive) {
                                    displayValue = "••••••••";
                                } else if (
                                    typeof value === "object"
                                ) {
                                    displayValue =
                                        JSON.stringify(value);
                                }

                                return (
                                    <div
                                        className="info-row"
                                        key={key}
                                    >
                                        <span>
                                            {String(key)
                                                .replaceAll("_", " ")
                                                .replace(
                                                    /\b\w/g,
                                                    (char) =>
                                                        char.toUpperCase()
                                                )}
                                        </span>

                                        <span>
                                            {String(
                                                displayValue ?? "—"
                                            )}
                                        </span>
                                    </div>
                                );
                            })
                        ) : (
                            <div className="empty-stage-detail">
                                No connection configuration
                                available.
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}