import React, {
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    Search,
    Plus,
    RefreshCw,
    Database,
    CheckCircle2,
    AlertTriangle,
    Clock,
    Settings,
    Play,
    ChevronRight,
    X,
} from "lucide-react";

import {
    ENTERPRISE_CONNECTORS,
    CATALOG_CATEGORIES,
    getConnectorById,
} from "../utils/connectorsCatalog";

import ConnectorWizard from "./ConnectorWizard";


// ============================================================================
// CONFIGURATION
// ============================================================================

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "/api/v1";

const DEFAULT_ORGANIZATION_ID =
    "11111111-1111-1111-1111-111111111111";


// ============================================================================
// API HELPER
// ============================================================================

async function apiRequest(
    path,
    options = {}
) {
    const response =
        await fetch(
            `${API_BASE_URL}${path}`,
            {
                headers: {
                    Accept:
                        "application/json",
                    "Content-Type":
                        "application/json",
                    ...(options.headers || {}),
                },
                ...options,
            }
        );

    let data = null;

    try {
        data =
            await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {
        throw new Error(
            data?.detail ||
            data?.message ||
            `Request failed with status ${response.status}`
        );
    }

    return data;
}


// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function Connectors({
    organizationId =
    DEFAULT_ORGANIZATION_ID,
    onConnectorSelect,
    onViewConnection,
    onAddConnection,
    onEditConnection,
    showToast,
}) {
    // --------------------------------------------------------------------------
    // Connector catalog
    // --------------------------------------------------------------------------

    const [
        catalog,
        setCatalog,
    ] = useState(
        ENTERPRISE_CONNECTORS
    );

    // --------------------------------------------------------------------------
    // Configured sources
    // --------------------------------------------------------------------------

    const [
        sources,
        setSources,
    ] = useState([]);

    // --------------------------------------------------------------------------
    // UI state
    // --------------------------------------------------------------------------

    const [
        searchQuery,
        setSearchQuery,
    ] = useState("");

    const [
        selectedCategory,
        setSelectedCategory,
    ] = useState("all");

    const [
        selectedConnector,
        setSelectedConnector,
    ] = useState(null);

    const [
        showWizard,
        setShowWizard,
    ] = useState(false);

    const [
        loading,
        setLoading,
    ] = useState(false);

    const [
        syncingSourceId,
        setSyncingSourceId,
    ] = useState(null);

    const [
        error,
        setError,
    ] = useState(null);

    const [
        success,
        setSuccess,
    ] = useState(null);


    // --------------------------------------------------------------------------
    // Initial data load
    // --------------------------------------------------------------------------

    useEffect(() => {
        loadCatalog();
        loadSources();
    }, [
        organizationId,
    ]);


    // ==========================================================================
    // LOAD CATALOG
    // ==========================================================================

    async function loadCatalog() {
        try {
            const result =
                await apiRequest(
                    "/sources/catalog"
                );

            if (
                Array.isArray(
                    result?.connectors
                ) &&
                result.connectors.length
            ) {
                setCatalog(
                    result.connectors
                );
            }
        } catch {
            // Keep the local catalog as fallback.
            setCatalog(
                ENTERPRISE_CONNECTORS
            );
        }
    }


    // ==========================================================================
    // LOAD CONFIGURED SOURCES
    // ==========================================================================

    async function loadSources() {
        setLoading(true);
        setError(null);

        try {
            const result =
                await apiRequest(
                    `/sources?organization_id=${encodeURIComponent(
                        organizationId
                    )}`
                );

            setSources(
                Array.isArray(result)
                    ? result
                    : result?.sources || []
            );
        } catch (err) {
            setError(
                err.message ||
                "Unable to load configured connectors."
            );
        } finally {
            setLoading(false);
        }
    }


    // ==========================================================================
    // FILTERED CONNECTORS
    // ==========================================================================

    const filteredConnectors =
        useMemo(() => {
            const query =
                searchQuery
                    .trim()
                    .toLowerCase();

            return catalog.filter(
                (connector) => {
                    const categoryMatch =
                        selectedCategory ===
                        "all" ||
                        connector.category ===
                        selectedCategory;

                    if (!categoryMatch) {
                        return false;
                    }

                    if (!query) {
                        return true;
                    }

                    const searchable = [
                        connector.id,
                        connector.name,
                        connector.description,
                        connector.family,
                        connector.category_label,
                    ]
                        .filter(Boolean)
                        .join(" ")
                        .toLowerCase();

                    return searchable.includes(
                        query
                    );
                }
            );
        }, [
            catalog,
            searchQuery,
            selectedCategory,
        ]);


    // ==========================================================================
    // GROUP FILTERED CONNECTORS
    // ==========================================================================

    const groupedConnectors =
        useMemo(() => {
            const groups = {};

            filteredConnectors.forEach(
                (connector) => {
                    const category =
                        connector.category ||
                        "other";

                    if (!groups[category]) {
                        groups[category] = [];
                    }

                    groups[
                        category
                    ].push(connector);
                }
            );

            return Object.entries(
                groups
            ).map(
                ([
                    category,
                    connectors,
                ]) => {
                    const metadata =
                        CATALOG_CATEGORIES.find(
                            (item) =>
                                item.id ===
                                category
                        );

                    return {
                        id: category,
                        label:
                            metadata?.label ||
                            connectors[0]
                                ?.category_label ||
                            category,
                        connectors,
                    };
                }
            );
        }, [
            filteredConnectors,
        ]);


    // ==========================================================================
    // STATISTICS
    // ==========================================================================

    const statistics =
        useMemo(() => {
            const connected =
                sources.length;

            const active =
                sources.filter(
                    (source) =>
                        normalizeStatus(
                            source.status
                        ) === "active" ||
                        normalizeStatus(
                            source.status
                        ) === "connected" ||
                        normalizeStatus(
                            source.status
                        ) === "healthy"
                ).length;

            const errors =
                sources.filter(
                    (source) =>
                        normalizeStatus(
                            source.status
                        ) === "error" ||
                        normalizeStatus(
                            source.status
                        ) === "failed"
                ).length;

            return {
                supported:
                    catalog.length,
                connected,
                active,
                errors,
            };
        }, [
            catalog,
            sources,
        ]);


    // ==========================================================================
    // OPEN WIZARD
    // ==========================================================================

    function openWizard(
        connectorId = null
    ) {
        setSelectedConnector(
            connectorId
        );

        setShowWizard(
            true
        );

        setError(null);
        setSuccess(null);
    }


    // ==========================================================================
    // CLOSE WIZARD
    // ==========================================================================

    function closeWizard() {
        setShowWizard(
            false
        );

        setSelectedConnector(
            null
        );
    }


    // ==========================================================================
    // WIZARD COMPLETE
    // ==========================================================================

    function handleWizardComplete(
        result
    ) {
        setSuccess(
            "Connector synchronization completed successfully."
        );
        if (showToast) {
            showToast("Connector synchronized successfully!", "success");
        }

        closeWizard();

        loadSources();

        if (onViewConnection) {
            onViewConnection(result);
        } else if (onConnectorSelect) {
            onConnectorSelect(result);
        }
    }


    // ==========================================================================
    // SYNC SOURCE
    // ==========================================================================

    async function syncSource(
        source
    ) {
        if (!source?.id) {
            return;
        }

        setSyncingSourceId(
            source.id
        );

        setError(null);
        setSuccess(null);

        try {
            const result =
                await apiRequest(
                    `/sources/${source.id}/sync/continuous?use_mock_llm=true`,
                    {
                        method: "POST",
                    }
                );

            setSuccess(
                result?.message ||
                `Synchronization completed for ${source.name}.`
            );

            await loadSources();
        } catch (err) {
            setError(
                err.message ||
                `Synchronization failed for ${source.name}.`
            );
        } finally {
            setSyncingSourceId(
                null
            );
        }
    }


    // ==========================================================================
    // TEST SOURCE
    // ==========================================================================

    async function testSource(
        source
    ) {
        if (!source?.id) {
            return;
        }

        setError(null);
        setSuccess(null);

        try {
            const result =
                await apiRequest(
                    `/sources/${source.id}/test`,
                    {
                        method: "POST",
                    }
                );

            if (
                result?.success === false
            ) {
                throw new Error(
                    result.message ||
                    "Connection test failed."
                );
            }

            setSuccess(
                result?.message ||
                `${source.name} connection test passed.`
            );

            await loadSources();
        } catch (err) {
            setError(
                err.message ||
                "Connection test failed."
            );
        }
    }


    // ==========================================================================
    // REMOVE/EDIT
    // ==========================================================================
    //
    // We deliberately do not implement destructive deletion here because the
    // existing backend contract should remain the source of truth for lifecycle
    // management. The settings action can be connected in File 10/11.
    // ==========================================================================

    // ==========================================================================
    // WIZARD VIEW
    // ==========================================================================

    if (showWizard) {
        return (
            <ConnectorWizard
                organizationId={
                    organizationId
                }
                initialConnectorId={
                    selectedConnector
                }
                onComplete={
                    handleWizardComplete
                }
                onCancel={
                    closeWizard
                }
            />
        );
    }


    // ==========================================================================
    // MAIN CONNECTOR HUB
    // ==========================================================================

    return (
        <div
            style={
                styles.container
            }
        >

            {/* ================================================================= */}
            {/* HEADER                                                            */}
            {/* ================================================================= */}

            <div
                style={
                    styles.header
                }
            >
                <div>
                    <div
                        style={
                            styles.eyebrow
                        }
                    >
                        DATA CONNECTORS
                    </div>

                    <h1
                        style={
                            styles.title
                        }
                    >
                        Connector Hub
                    </h1>

                    <p
                        style={
                            styles.subtitle
                        }
                    >
                        Configure, authenticate, test, discover,
                        synchronize and monitor enterprise data
                        sources.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={() =>
                        openWizard()
                    }
                    style={
                        styles.primaryButton
                    }
                >
                    <Plus
                        size={16}
                    />

                    Add Connector
                </button>
            </div>


            {/* ================================================================= */}
            {/* ALERTS                                                            */}
            {/* ================================================================= */}

            {error && (
                <div
                    style={
                        styles.errorAlert
                    }
                >
                    <AlertTriangle
                        size={17}
                    />

                    <span>
                        {error}
                    </span>

                    <button
                        type="button"
                        onClick={() =>
                            setError(null)
                        }
                        style={
                            styles.closeAlertButton
                        }
                    >
                        <X
                            size={15}
                        />
                    </button>
                </div>
            )}

            {success && (
                <div
                    style={
                        styles.successAlert
                    }
                >
                    <CheckCircle2
                        size={17}
                    />

                    <span>
                        {success}
                    </span>

                    <button
                        type="button"
                        onClick={() =>
                            setSuccess(null)
                        }
                        style={
                            styles.closeAlertButton
                        }
                    >
                        <X
                            size={15}
                        />
                    </button>
                </div>
            )}


            {/* ================================================================= */}
            {/* STATISTICS                                                        */}
            {/* ================================================================= */}

            <div
                style={
                    styles.statsGrid
                }
            >
                <StatCard
                    icon={
                        <Database
                            size={19}
                        />
                    }
                    label="Supported Connectors"
                    value={
                        statistics.supported
                    }
                />

                <StatCard
                    icon={
                        <CheckCircle2
                            size={19}
                        />
                    }
                    label="Configured"
                    value={
                        statistics.connected
                    }
                />

                <StatCard
                    icon={
                        <Play
                            size={19}
                        />
                    }
                    label="Active"
                    value={
                        statistics.active
                    }
                />

                <StatCard
                    icon={
                        <AlertTriangle
                            size={19}
                        />
                    }
                    label="Needs Attention"
                    value={
                        statistics.errors
                    }
                />
            </div>


            {/* ================================================================= */}
            {/* CONFIGURED CONNECTIONS                                            */}
            {/* ================================================================= */}

            {sources.length >
                0 && (
                    <section
                        style={
                            styles.section
                        }
                    >
                        <div
                            style={
                                styles.sectionHeader
                            }
                        >
                            <div>
                                <h2
                                    style={
                                        styles.sectionTitle
                                    }
                                >
                                    Configured Connections
                                </h2>

                                <p
                                    style={
                                        styles.sectionDescription
                                    }
                                >
                                    Existing data source connections and
                                    their current synchronization state.
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={
                                    loadSources
                                }
                                disabled={
                                    loading
                                }
                                style={
                                    styles.iconButton
                                }
                                title="Refresh connections"
                            >
                                <RefreshCw
                                    size={16}
                                    style={
                                        loading
                                            ? styles.spin
                                            : undefined
                                    }
                                />
                            </button>
                        </div>

                        <div
                            style={
                                styles.connectionsList
                            }
                        >
                            {sources.map(
                                (source) => (
                                    <ConfiguredSourceCard
                                        key={
                                            source.id
                                        }
                                        source={
                                            source
                                        }
                                        connector={
                                            getConnectorById(
                                                source.source_type
                                            ) ||
                                            catalog.find(
                                                (item) =>
                                                    item.id ===
                                                    source.source_type
                                            )
                                        }
                                        syncing={
                                            syncingSourceId ===
                                            source.id
                                        }
                                        onTest={() =>
                                            testSource(
                                                source
                                            )
                                        }
                                        onSync={() =>
                                            syncSource(
                                                source
                                            )
                                        }
                                        onOpen={() => {
                                            if (onViewConnection) {
                                                onViewConnection(source);
                                            } else if (onConnectorSelect) {
                                                onConnectorSelect(source);
                                            }
                                        }}
                                    />
                                )
                            )}
                        </div>
                    </section>
                )}


            {/* ================================================================= */}
            {/* CATALOG                                                           */}
            {/* ================================================================= */}

            <section
                style={
                    styles.section
                }
            >
                <div
                    style={
                        styles.sectionHeader
                    }
                >
                    <div>
                        <h2
                            style={
                                styles.sectionTitle
                            }
                        >
                            Enterprise Connector Catalog
                        </h2>

                        <p
                            style={
                                styles.sectionDescription
                            }
                        >
                            Select any supported connector to begin
                            the Configure → Authenticate → Test →
                            Discover → Select → Sync lifecycle.
                        </p>
                    </div>

                    <span
                        style={
                            styles.catalogCount
                        }
                    >
                        {filteredConnectors.length}{" "}
                        available
                    </span>
                </div>


                {/* =============================================================== */}
                {/* SEARCH                                                           */}
                {/* =============================================================== */}

                <div
                    style={
                        styles.toolbar
                    }
                >
                    <div
                        style={
                            styles.searchWrapper
                        }
                    >
                        <Search
                            size={17}
                            style={
                                styles.searchIcon
                            }
                        />

                        <input
                            type="search"
                            value={
                                searchQuery
                            }
                            onChange={(event) =>
                                setSearchQuery(
                                    event.target.value
                                )
                            }
                            placeholder="Search connectors..."
                            style={
                                styles.searchInput
                            }
                        />

                        {searchQuery && (
                            <button
                                type="button"
                                onClick={() =>
                                    setSearchQuery(
                                        ""
                                    )
                                }
                                style={
                                    styles.clearSearch
                                }
                            >
                                <X
                                    size={15}
                                />
                            </button>
                        )}
                    </div>
                </div>


                {/* =============================================================== */}
                {/* CATEGORY FILTERS                                                 */}
                {/* =============================================================== */}

                <div
                    style={
                        styles.categoryTabs
                    }
                >
                    {CATALOG_CATEGORIES.map(
                        (category) => (
                            <button
                                key={
                                    category.id
                                }
                                type="button"
                                onClick={() =>
                                    setSelectedCategory(
                                        category.id
                                    )
                                }
                                style={{
                                    ...styles.categoryTab,
                                    ...(selectedCategory ===
                                        category.id
                                        ? styles.activeCategoryTab
                                        : {}),
                                }}
                            >
                                {
                                    category.label
                                }

                                <span
                                    style={{
                                        ...styles.categoryCount,
                                        ...(selectedCategory ===
                                            category.id
                                            ? styles.activeCategoryCount
                                            : {}),
                                    }}
                                >
                                    {
                                        category.count
                                    }
                                </span>
                            </button>
                        )
                    )}
                </div>


                {/* =============================================================== */}
                {/* CONNECTOR GROUPS                                                 */}
                {/* =============================================================== */}

                {groupedConnectors.length ===
                    0 && (
                        <div
                            style={
                                styles.emptyState
                            }
                        >
                            <Search
                                size={30}
                            />

                            <h3>
                                No connectors found
                            </h3>

                            <p>
                                Try a different search term or
                                category.
                            </p>

                            <button
                                type="button"
                                onClick={() => {
                                    setSearchQuery(
                                        ""
                                    );
                                    setSelectedCategory(
                                        "all"
                                    );
                                }}
                                style={
                                    styles.secondaryButton
                                }
                            >
                                Clear Filters
                            </button>
                        </div>
                    )}

                {groupedConnectors.map(
                    (group) => (
                        <div
                            key={
                                group.id
                            }
                            style={
                                styles.connectorGroup
                            }
                        >
                            <div
                                style={
                                    styles.groupHeader
                                }
                            >
                                <h3
                                    style={
                                        styles.groupTitle
                                    }
                                >
                                    {group.label}
                                </h3>

                                <span
                                    style={
                                        styles.groupCount
                                    }
                                >
                                    {
                                        group.connectors
                                            .length
                                    }{" "}
                                    connectors
                                </span>
                            </div>

                            <div
                                style={
                                    styles.connectorGrid
                                }
                            >
                                {group.connectors.map(
                                    (
                                        connector
                                    ) => (
                                        <ConnectorCard
                                            key={
                                                connector.id
                                            }
                                            connector={
                                                connector
                                            }
                                            onConnect={() =>
                                                openWizard(
                                                    connector.id
                                                )
                                            }
                                        />
                                    )
                                )}
                            </div>
                        </div>
                    )
                )}
            </section>
        </div>
    );
}


// ============================================================================
// STAT CARD
// ============================================================================

function StatCard({
    icon,
    label,
    value,
}) {
    return (
        <div
            style={
                styles.statCard
            }
        >
            <div
                style={
                    styles.statIcon
                }
            >
                {icon}
            </div>

            <div>
                <div
                    style={
                        styles.statValue
                    }
                >
                    {value}
                </div>

                <div
                    style={
                        styles.statLabel
                    }
                >
                    {label}
                </div>
            </div>
        </div>
    );
}


// ============================================================================
// CONNECTOR CARD
// ============================================================================

function ConnectorCard({
    connector,
    onConnect,
}) {
    return (
        <div
            style={
                styles.connectorCard
            }
        >
            <div
                style={
                    styles.connectorCardHeader
                }
            >
                <div
                    style={
                        styles.connectorIcon
                    }
                >
                    {connector.icon ||
                        "🔌"}
                </div>

                <div
                    style={
                        styles.connectorCardTitle
                    }
                >
                    <h4
                        style={
                            styles.connectorName
                        }
                    >
                        {connector.name}
                    </h4>

                    <span
                        style={
                            styles.familyBadge
                        }
                    >
                        {connector.family ||
                            connector.category}
                    </span>
                </div>
            </div>

            <p
                style={
                    styles.connectorDescription
                }
            >
                {connector.description}
            </p>

            {connector.monitored_scope && (
                <div
                    style={
                        styles.monitoredScope
                    }
                >
                    <span
                        style={
                            styles.scopeLabel
                        }
                    >
                        Monitored scope
                    </span>

                    <span>
                        {
                            connector.monitored_scope
                        }
                    </span>
                </div>
            )}

            <div
                style={
                    styles.connectorCardFooter
                }
            >
                <span
                    style={
                        styles.portInfo
                    }
                >
                    {connector.default_port
                        ? `Port ${connector.default_port}`
                        : "API"}
                </span>

                <button
                    type="button"
                    onClick={
                        onConnect
                    }
                    style={
                        styles.connectButton
                    }
                >
                    Connect

                    <ChevronRight
                        size={15}
                    />
                </button>
            </div>
        </div>
    );
}


// ============================================================================
// CONFIGURED SOURCE CARD
// ============================================================================

function ConfiguredSourceCard({
    source,
    connector,
    syncing,
    onTest,
    onSync,
    onOpen,
}) {
    const status =
        normalizeStatus(
            source.status
        );

    const statusMeta =
        getStatusMeta(
            status
        );

    return (
        <div
            style={
                styles.sourceCard
            }
        >
            <div
                style={
                    styles.sourceIdentity
                }
            >
                <div
                    style={
                        styles.sourceIcon
                    }
                >
                    {connector?.icon ||
                        "🔌"}
                </div>

                <div
                    style={
                        styles.sourceDetails
                    }
                >
                    <div
                        style={
                            styles.sourceName
                        }
                    >
                        {source.name ||
                            connector?.name ||
                            source.source_type}
                    </div>

                    <div
                        style={
                            styles.sourceType
                        }
                    >
                        {connector?.name ||
                            source.source_type}
                    </div>

                    {source.external_id && (
                        <div
                            style={
                                styles.externalId
                            }
                        >
                            {source.external_id}
                        </div>
                    )}
                </div>
            </div>


            <div
                style={
                    styles.sourceStatus
                }
            >
                <span
                    style={{
                        ...styles.statusBadge,
                        ...statusMeta.style,
                    }}
                >
                    {statusMeta.icon}

                    {statusMeta.label}
                </span>

                <div
                    style={
                        styles.lastSync
                    }
                >
                    <Clock
                        size={13}
                    />

                    {formatLastSync(
                        source.last_synced_at
                    )}
                </div>
            </div>


            <div
                style={
                    styles.sourceActions
                }
            >
                <button
                    type="button"
                    onClick={
                        onTest
                    }
                    style={
                        styles.smallButton
                    }
                    title="Test connection"
                >
                    <CheckCircle2
                        size={14}
                    />

                    Test
                </button>

                <button
                    type="button"
                    onClick={
                        onSync
                    }
                    disabled={
                        syncing
                    }
                    style={
                        styles.smallPrimaryButton
                    }
                >
                    <RefreshCw
                        size={14}
                        style={
                            syncing
                                ? styles.spin
                                : undefined
                        }
                    />

                    {syncing
                        ? "Syncing"
                        : "Sync"}
                </button>

                <button
                    type="button"
                    onClick={
                        onOpen
                    }
                    style={
                        styles.settingsButton
                    }
                    title="Open connector"
                >
                    <Settings
                        size={15}
                    />
                </button>
            </div>
        </div>
    );
}


// ============================================================================
// STATUS HELPERS
// ============================================================================

function normalizeStatus(
    status
) {
    return String(
        status ||
        "unknown"
    )
        .toLowerCase()
        .replace(
            /-/g,
            "_"
        )
        .trim();
}


function getStatusMeta(
    status
) {
    if (
        [
            "active",
            "connected",
            "healthy",
            "ready",
            "ok",
        ].includes(
            status
        )
    ) {
        return {
            label:
                "Connected",
            icon: (
                <CheckCircle2
                    size={12}
                />
            ),
            style:
                styles.connectedStatus,
        };
    }

    if (
        [
            "error",
            "failed",
            "failure",
        ].includes(
            status
        )
    ) {
        return {
            label:
                "Needs attention",
            icon: (
                <AlertTriangle
                    size={12}
                />
            ),
            style:
                styles.errorStatus,
        };
    }

    if (
        [
            "syncing",
            "running",
            "in_progress",
        ].includes(
            status
        )
    ) {
        return {
            label:
                "Syncing",
            icon: (
                <RefreshCw
                    size={12}
                />
            ),
            style:
                styles.syncingStatus,
        };
    }

    return {
        label:
            "Configured",
        icon: (
            <Clock
                size={12}
            />
        ),
        style:
            styles.configuredStatus,
    };
}


function formatLastSync(
    value
) {
    if (!value) {
        return "Never synced";
    }

    const date =
        new Date(
            value
        );

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return "Sync time unavailable";
    }

    const now =
        Date.now();

    const difference =
        Math.max(
            0,
            now -
            date.getTime()
        );

    const minutes =
        Math.floor(
            difference /
            60000
        );

    if (
        minutes < 1
    ) {
        return "Just now";
    }

    if (
        minutes < 60
    ) {
        return `${minutes}m ago`;
    }

    const hours =
        Math.floor(
            minutes / 60
        );

    if (
        hours < 24
    ) {
        return `${hours}h ago`;
    }

    const days =
        Math.floor(
            hours / 24
        );

    if (
        days < 30
    ) {
        return `${days}d ago`;
    }

    return date.toLocaleDateString();
}


// ============================================================================
// STYLES
// ============================================================================

const styles = {
    container: {
        width: "100%",
        maxWidth:
            "1400px",
        margin:
            "0 auto",
        padding:
            "28px",
        boxSizing:
            "border-box",
    },

    header: {
        display:
            "flex",
        justifyContent:
            "space-between",
        alignItems:
            "flex-start",
        gap:
            "24px",
        marginBottom:
            "24px",
    },

    eyebrow: {
        fontSize:
            "11px",
        fontWeight:
            700,
        letterSpacing:
            "0.12em",
        color:
            "#64748b",
        marginBottom:
            "6px",
    },

    title: {
        margin: 0,
        fontSize:
            "28px",
        fontWeight:
            750,
        color:
            "#0f172a",
    },

    subtitle: {
        margin:
            "7px 0 0",
        maxWidth:
            "720px",
        color:
            "#64748b",
        fontSize:
            "14px",
        lineHeight:
            1.55,
    },

    primaryButton: {
        display:
            "inline-flex",
        alignItems:
            "center",
        justifyContent:
            "center",
        gap:
            "7px",
        border:
            "1px solid var(--primary-hover, #F5982C)",
        borderRadius:
            "8px",
        padding:
            "10px 16px",
        background:
            "var(--primary, #FFAB4A)",
        color:
            "var(--text-main, #0F172A)",
        cursor:
            "pointer",
        fontSize:
            "13px",
        fontWeight:
            650,
        whiteSpace:
            "nowrap",
    },

    secondaryButton: {
        border:
            "1px solid #cbd5e1",
        borderRadius:
            "7px",
        padding:
            "9px 14px",
        background:
            "#ffffff",
        color:
            "#334155",
        cursor:
            "pointer",
        fontWeight:
            600,
    },

    statsGrid: {
        display:
            "grid",
        gridTemplateColumns:
            "repeat(4, minmax(0, 1fr))",
        gap:
            "12px",
        marginBottom:
            "32px",
    },

    statCard: {
        display:
            "flex",
        alignItems:
            "center",
        gap:
            "12px",
        padding:
            "17px",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "10px",
        background:
            "#ffffff",
    },

    statIcon: {
        width:
            "38px",
        height:
            "38px",
        display:
            "flex",
        alignItems:
            "center",
        justifyContent:
            "center",
        borderRadius:
            "8px",
        background:
            "var(--primary-50, #FFF9F2)",
        border:
            "1px solid var(--primary-200, #FFD8A8)",
        color:
            "var(--primary-dark, #C96E07)",
    },

    statValue: {
        fontSize:
            "21px",
        fontWeight:
            750,
        color:
            "#0f172a",
    },

    statLabel: {
        marginTop:
            "2px",
        fontSize:
            "11px",
        color:
            "#64748b",
    },

    section: {
        marginBottom:
            "34px",
    },

    sectionHeader: {
        display:
            "flex",
        alignItems:
            "flex-start",
        justifyContent:
            "space-between",
        gap:
            "20px",
        marginBottom:
            "17px",
    },

    sectionTitle: {
        margin: 0,
        fontSize:
            "18px",
        fontWeight:
            700,
        color:
            "#0f172a",
    },

    sectionDescription: {
        margin:
            "5px 0 0",
        fontSize:
            "13px",
        color:
            "#64748b",
        lineHeight:
            1.5,
    },

    catalogCount: {
        fontSize:
            "12px",
        color:
            "#64748b",
        whiteSpace:
            "nowrap",
    },

    toolbar: {
        marginBottom:
            "14px",
    },

    searchWrapper: {
        position:
            "relative",
        width:
            "100%",
        maxWidth:
            "520px",
    },

    searchIcon: {
        position:
            "absolute",
        left:
            "12px",
        top:
            "50%",
        transform:
            "translateY(-50%)",
        color:
            "#94a3b8",
    },

    searchInput: {
        width:
            "100%",
        boxSizing:
            "border-box",
        padding:
            "11px 38px",
        border:
            "1px solid #cbd5e1",
        borderRadius:
            "8px",
        outline:
            "none",
        fontSize:
            "13px",
        background:
            "#ffffff",
    },

    clearSearch: {
        position:
            "absolute",
        right:
            "9px",
        top:
            "50%",
        transform:
            "translateY(-50%)",
        border:
            "none",
        background:
            "transparent",
        cursor:
            "pointer",
        color:
            "#64748b",
    },

    categoryTabs: {
        display:
            "flex",
        gap:
            "7px",
        overflowX:
            "auto",
        paddingBottom:
            "8px",
        marginBottom:
            "24px",
    },

    categoryTab: {
        display:
            "inline-flex",
        alignItems:
            "center",
        gap:
            "7px",
        whiteSpace:
            "nowrap",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "20px",
        padding:
            "7px 11px",
        background:
            "#ffffff",
        color:
            "#475569",
        cursor:
            "pointer",
        fontSize:
            "11px",
        fontWeight:
            550,
    },

    activeCategoryTab: {
        background:
            "var(--primary, #FFAB4A)",
        color:
            "var(--text-main, #0F172A)",
        borderColor:
            "var(--primary-hover, #F5982C)",
    },

    categoryCount: {
        minWidth:
            "18px",
        padding:
            "2px 5px",
        borderRadius:
            "10px",
        background:
            "#f1f5f9",
        color:
            "#64748b",
        fontSize:
            "9px",
        textAlign:
            "center",
    },

    activeCategoryCount: {
        background:
            "rgba(255,255,255,0.22)",
        color:
            "#ffffff",
    },

    connectorGroup: {
        marginBottom:
            "28px",
    },

    groupHeader: {
        display:
            "flex",
        alignItems:
            "center",
        gap:
            "10px",
        marginBottom:
            "11px",
    },

    groupTitle: {
        margin: 0,
        fontSize:
            "14px",
        fontWeight:
            700,
        color:
            "#334155",
    },

    groupCount: {
        fontSize:
            "10px",
        color:
            "#94a3b8",
    },

    connectorGrid: {
        display:
            "grid",
        gridTemplateColumns:
            "repeat(auto-fill, minmax(280px, 1fr))",
        gap:
            "12px",
    },

    connectorCard: {
        display:
            "flex",
        flexDirection:
            "column",
        minHeight:
            "205px",
        padding:
            "15px",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "10px",
        background:
            "#ffffff",
        transition:
            "border-color 0.15s ease",
    },

    connectorCardHeader: {
        display:
            "flex",
        gap:
            "11px",
        alignItems:
            "flex-start",
    },

    connectorIcon: {
        width:
            "40px",
        height:
            "40px",
        minWidth:
            "40px",
        display:
            "flex",
        alignItems:
            "center",
        justifyContent:
            "center",
        borderRadius:
            "8px",
        background:
            "#f1f5f9",
        fontSize:
            "21px",
    },

    connectorCardTitle: {
        minWidth:
            0,
    },

    connectorName: {
        margin: 0,
        fontSize:
            "14px",
        fontWeight:
            700,
        color:
            "#0f172a",
        lineHeight:
            1.35,
    },

    familyBadge: {
        display:
            "inline-block",
        marginTop:
            "5px",
        padding:
            "3px 6px",
        borderRadius:
            "10px",
        background:
            "#f8fafc",
        color:
            "#64748b",
        fontSize:
            "9px",
    },

    connectorDescription: {
        margin:
            "12px 0",
        color:
            "#64748b",
        fontSize:
            "11px",
        lineHeight:
            1.5,
        flex: 1,
    },

    monitoredScope: {
        display:
            "flex",
        flexDirection:
            "column",
        gap:
            "3px",
        padding:
            "8px",
        marginBottom:
            "11px",
        borderRadius:
            "6px",
        background:
            "#f8fafc",
        color:
            "#64748b",
        fontSize:
            "9px",
        lineHeight:
            1.4,
    },

    scopeLabel: {
        fontWeight:
            700,
        color:
            "#475569",
    },

    connectorCardFooter: {
        display:
            "flex",
        alignItems:
            "center",
        justifyContent:
            "space-between",
        paddingTop:
            "10px",
        borderTop:
            "1px solid #f1f5f9",
    },

    portInfo: {
        color:
            "#94a3b8",
        fontSize:
            "10px",
    },

    connectButton: {
        display:
            "inline-flex",
        alignItems:
            "center",
        gap:
            "3px",
        border:
            "none",
        background:
            "transparent",
        color:
            "var(--primary-dark, #C96E07)",
        cursor:
            "pointer",
        fontSize:
            "11px",
        fontWeight:
            650,
    },

    connectionsList: {
        display:
            "flex",
        flexDirection:
            "column",
        gap:
            "8px",
    },

    sourceCard: {
        display:
            "grid",
        gridTemplateColumns:
            "minmax(250px, 1fr) minmax(160px, auto) auto",
        alignItems:
            "center",
        gap:
            "20px",
        padding:
            "13px 15px",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "9px",
        background:
            "#ffffff",
    },

    sourceIdentity: {
        display:
            "flex",
        alignItems:
            "center",
        gap:
            "11px",
        minWidth:
            0,
    },

    sourceIcon: {
        width:
            "38px",
        height:
            "38px",
        minWidth:
            "38px",
        display:
            "flex",
        alignItems:
            "center",
        justifyContent:
            "center",
        borderRadius:
            "8px",
        background:
            "#f1f5f9",
        fontSize:
            "19px",
    },

    sourceDetails: {
        minWidth:
            0,
    },

    sourceName: {
        fontSize:
            "13px",
        fontWeight:
            700,
        color:
            "#0f172a",
        overflow:
            "hidden",
        textOverflow:
            "ellipsis",
        whiteSpace:
            "nowrap",
    },

    sourceType: {
        marginTop:
            "2px",
        fontSize:
            "10px",
        color:
            "#64748b",
    },

    externalId: {
        marginTop:
            "2px",
        fontSize:
            "9px",
        color:
            "#94a3b8",
        overflow:
            "hidden",
        textOverflow:
            "ellipsis",
        whiteSpace:
            "nowrap",
    },

    sourceStatus: {
        display:
            "flex",
        flexDirection:
            "column",
        alignItems:
            "flex-start",
        gap:
            "5px",
    },

    statusBadge: {
        display:
            "inline-flex",
        alignItems:
            "center",
        gap:
            "4px",
        padding:
            "4px 7px",
        borderRadius:
            "12px",
        fontSize:
            "9px",
        fontWeight:
            650,
    },

    connectedStatus: {
        background:
            "#dcfce7",
        color:
            "#166534",
    },

    errorStatus: {
        background:
            "#fee2e2",
        color:
            "#991b1b",
    },

    syncingStatus: {
        background:
            "#dbeafe",
        color:
            "#1d4ed8",
    },

    configuredStatus: {
        background:
            "#f1f5f9",
        color:
            "#475569",
    },

    lastSync: {
        display:
            "inline-flex",
        alignItems:
            "center",
        gap:
            "4px",
        color:
            "#94a3b8",
        fontSize:
            "9px",
    },

    sourceActions: {
        display:
            "flex",
        alignItems:
            "center",
        gap:
            "5px",
    },

    smallButton: {
        display:
            "inline-flex",
        alignItems:
            "center",
        gap:
            "4px",
        padding:
            "7px 9px",
        border:
            "1px solid #cbd5e1",
        borderRadius:
            "6px",
        background:
            "#ffffff",
        color:
            "#475569",
        cursor:
            "pointer",
        fontSize:
            "10px",
        fontWeight:
            600,
    },

    smallPrimaryButton: {
        display:
            "inline-flex",
        alignItems:
            "center",
        gap:
            "4px",
        padding:
            "7px 10px",
        border:
            "none",
        borderRadius:
            "6px",
        background:
            "var(--primary, #FFAB4A)",
        color:
            "var(--text-main, #0F172A)",
        cursor:
            "pointer",
        fontSize:
            "10px",
        fontWeight:
            650,
    },

    settingsButton: {
        width:
            "30px",
        height:
            "30px",
        display:
            "flex",
        alignItems:
            "center",
        justifyContent:
            "center",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "6px",
        background:
            "#ffffff",
        color:
            "#64748b",
        cursor:
            "pointer",
    },

    iconButton: {
        width:
            "32px",
        height:
            "32px",
        display:
            "flex",
        alignItems:
            "center",
        justifyContent:
            "center",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "7px",
        background:
            "#ffffff",
        color:
            "#64748b",
        cursor:
            "pointer",
    },

    errorAlert: {
        display:
            "flex",
        alignItems:
            "center",
        gap:
            "8px",
        padding:
            "11px 13px",
        marginBottom:
            "16px",
        border:
            "1px solid #fecaca",
        borderRadius:
            "8px",
        background:
            "#fef2f2",
        color:
            "#991b1b",
        fontSize:
            "12px",
    },

    successAlert: {
        display:
            "flex",
        alignItems:
            "center",
        gap:
            "8px",
        padding:
            "11px 13px",
        marginBottom:
            "16px",
        border:
            "1px solid #bbf7d0",
        borderRadius:
            "8px",
        background:
            "#f0fdf4",
        color:
            "#166534",
        fontSize:
            "12px",
    },

    closeAlertButton: {
        marginLeft:
            "auto",
        border:
            "none",
        background:
            "transparent",
        color:
            "inherit",
        cursor:
            "pointer",
        display:
            "flex",
    },

    emptyState: {
        display:
            "flex",
        flexDirection:
            "column",
        alignItems:
            "center",
        justifyContent:
            "center",
        minHeight:
            "260px",
        border:
            "1px dashed #cbd5e1",
        borderRadius:
            "10px",
        color:
            "#64748b",
        textAlign:
            "center",
    },

    spin: {
        animation:
            "spin 1s linear infinite",
    },
};