import React, {
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    CONNECTOR_LIFECYCLE,
    fetchConnector,
    fetchConnectorCatalog,
    getConnectorFields,
    getDefaultConnectorConfig,
    getGroupedConnectorCatalog,
    getLifecycleStages,
    supportsLifecycleStage,
} from "../utils/connectorsCatalog";


// ============================================================================
// CONSTANTS
// ============================================================================

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "/api/v1";

const WIZARD_STEPS = [
    {
        id: "configure",
        label: "Configure",
        description:
            "Configure the connector connection.",
    },
    {
        id: "authenticate",
        label: "Authenticate",
        description:
            "Provide authentication details.",
    },
    {
        id: "test",
        label: "Test",
        description:
            "Verify the connection.",
    },
    {
        id: "discover",
        label: "Discover",
        description:
            "Discover available resources.",
    },
    {
        id: "select",
        label: "Select",
        description:
            "Select resources to synchronize.",
    },
    {
        id: "initial_sync",
        label: "Initial Sync",
        description:
            "Import the selected resources.",
    },
];


// ============================================================================
// HELPERS
// ============================================================================

function normalizeFieldType(field) {
    const type =
        field?.type ||
        field?.field_type ||
        "text";

    if (
        [
            "password",
            "secret",
        ].includes(type)
    ) {
        return "password";
    }

    if (
        [
            "number",
            "integer",
        ].includes(type)
    ) {
        return "number";
    }

    if (
        [
            "boolean",
            "checkbox",
        ].includes(type)
    ) {
        return "checkbox";
    }

    if (
        [
            "select",
            "dropdown",
        ].includes(type)
    ) {
        return "select";
    }

    if (
        [
            "textarea",
            "longtext",
        ].includes(type)
    ) {
        return "textarea";
    }

    return "text";
}


function getFieldName(field) {
    return (
        field?.name ||
        field?.key ||
        field?.id ||
        ""
    );
}


function getFieldLabel(field) {
    return (
        field?.label ||
        field?.name ||
        field?.key ||
        "Configuration"
    );
}


function getFieldPlaceholder(field) {
    return (
        field?.placeholder ||
        ""
    );
}


function getFieldOptions(field) {
    return (
        field?.options ||
        field?.values ||
        []
    );
}


function getFieldRequired(field) {
    return (
        field?.required === true
    );
}


function isSecretField(field) {
    const name =
        getFieldName(field)
            .toLowerCase();

    return (
        normalizeFieldType(
            field
        ) === "password" ||
        name.includes("token") ||
        name.includes("secret") ||
        name.includes("password") ||
        name.includes("api_key") ||
        name.includes("apikey")
    );
}


function buildInitialConfig(
    connector
) {
    const defaults =
        getDefaultConnectorConfig(
            connector
        );

    const fields =
        getConnectorFields(
            connector
        );

    const config = {
        ...defaults,
    };

    fields.forEach(
        (field) => {
            const name =
                getFieldName(field);

            if (!name) {
                return;
            }

            if (
                field.default !==
                undefined
            ) {
                config[name] =
                    field.default;
            } else if (
                field.default_value !==
                undefined
            ) {
                config[name] =
                    field.default_value;
            } else if (
                field.type ===
                "boolean"
            ) {
                config[name] =
                    false;
            } else if (
                config[name] ===
                undefined
            ) {
                config[name] = "";
            }
        }
    );

    return config;
}


function getApiErrorMessage(
    error,
    fallback
) {
    if (
        error?.response?.detail
    ) {
        return error.response.detail;
    }

    if (
        error?.detail
    ) {
        return error.detail;
    }

    if (
        error?.message
    ) {
        return error.message;
    }

    return fallback;
}


async function apiRequest(
    path,
    options = {}
) {
    const response =
        await fetch(
            `${API_BASE_URL}${path}`,
            {
                headers: {
                    "Content-Type":
                        "application/json",
                    Accept:
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
        const error =
            new Error(
                data?.detail ||
                data?.message ||
                `Request failed with status ${response.status}`
            );

        error.status =
            response.status;

        error.detail =
            data?.detail ||
            data?.message;

        throw error;
    }

    return data;
}


// ============================================================================
// COMPONENT
// ============================================================================

export default function ConnectorWizard({
    organizationId,
    initialConnectorId = null,
    onComplete,
    onCancel,
}) {
    // --------------------------------------------------------------------------
    // Catalog state
    // --------------------------------------------------------------------------

    const [
        connectors,
        setConnectors,
    ] = useState([]);

    const [
        catalogLoading,
        setCatalogLoading,
    ] = useState(true);

    const [
        catalogError,
        setCatalogError,
    ] = useState(null);


    // --------------------------------------------------------------------------
    // Wizard state
    // --------------------------------------------------------------------------

    const [
        currentStep,
        setCurrentStep,
    ] = useState(0);

    const [
        selectedConnectorId,
        setSelectedConnectorId,
    ] = useState(
        initialConnectorId
    );

    const [
        connector,
        setConnector,
    ] = useState(null);

    const [
        source,
        setSource,
    ] = useState(null);

    const [
        connectionConfig,
        setConnectionConfig,
    ] = useState({});

    const [
        sourceName,
        setSourceName,
    ] = useState("");

    const [
        externalId,
        setExternalId,
    ] = useState("");

    const [
        discoveredResources,
        setDiscoveredResources,
    ] = useState([]);

    const [
        selectedResourceIds,
        setSelectedResourceIds,
    ] = useState([]);

    const [
        discoveryResult,
        setDiscoveryResult,
    ] = useState(null);

    const [
        testResult,
        setTestResult,
    ] = useState(null);

    const [
        syncResult,
        setSyncResult,
    ] = useState(null);


    // --------------------------------------------------------------------------
    // Request state
    // --------------------------------------------------------------------------

    const [
        loading,
        setLoading,
    ] = useState(false);

    const [
        error,
        setError,
    ] = useState(null);

    const [
        success,
        setSuccess,
    ] = useState(null);


    // --------------------------------------------------------------------------
    // Load connector catalog
    // --------------------------------------------------------------------------

    useEffect(() => {
        let mounted = true;

        async function loadCatalog() {
            setCatalogLoading(true);
            setCatalogError(null);

            try {
                const data =
                    await fetchConnectorCatalog();

                if (!mounted) {
                    return;
                }

                setConnectors(data);

                if (
                    initialConnectorId
                ) {
                    const selected =
                        data.find(
                            (item) =>
                                item.id ===
                                initialConnectorId
                        );

                    if (selected) {
                        setConnector(
                            selected
                        );
                        setConnectionConfig(
                            buildInitialConfig(
                                selected
                            )
                        );
                    }
                }
            } catch (err) {
                if (!mounted) {
                    return;
                }

                setCatalogError(
                    getApiErrorMessage(
                        err,
                        "Unable to load connector catalog."
                    )
                );
            } finally {
                if (mounted) {
                    setCatalogLoading(
                        false
                    );
                }
            }
        }

        loadCatalog();

        return () => {
            mounted = false;
        };
    }, [
        initialConnectorId,
    ]);


    // --------------------------------------------------------------------------
    // Connector selection
    // --------------------------------------------------------------------------

    function handleConnectorSelect(
        connectorId
    ) {
        const selected =
            connectors.find(
                (item) =>
                    item.id ===
                    connectorId
            );

        if (!selected) {
            return;
        }

        setSelectedConnectorId(
            connectorId
        );

        setConnector(
            selected
        );

        setConnectionConfig(
            buildInitialConfig(
                selected
            )
        );

        setSourceName(
            `${selected.name} Connection`
        );

        setExternalId("");

        setSource(null);

        setDiscoveredResources(
            []
        );

        setSelectedResourceIds(
            []
        );

        setDiscoveryResult(
            null
        );

        setTestResult(
            null
        );

        setSyncResult(
            null
        );

        setCurrentStep(
            0
        );

        setError(null);
        setSuccess(null);
    }


    // --------------------------------------------------------------------------
    // Grouped catalog
    // --------------------------------------------------------------------------

    const groupedConnectors =
        useMemo(
            () =>
                getGroupedConnectorCatalog(
                    connectors
                ),
            [connectors]
        );


    // --------------------------------------------------------------------------
    // Connector lifecycle
    // --------------------------------------------------------------------------

    const lifecycle =
        useMemo(
            () =>
                getLifecycleStages(
                    connector
                ),
            [connector]
        );


    // --------------------------------------------------------------------------
    // Dynamic connector fields
    // --------------------------------------------------------------------------

    const connectorFields =
        useMemo(
            () =>
                getConnectorFields(
                    connector
                ),
            [connector]
        );


    // --------------------------------------------------------------------------
    // Configuration field update
    // --------------------------------------------------------------------------

    function updateConfig(
        fieldName,
        value
    ) {
        setConnectionConfig(
            (previous) => ({
                ...previous,
                [fieldName]:
                    value,
            })
        );
    }


    // --------------------------------------------------------------------------
    // Create source
    // --------------------------------------------------------------------------

    async function createSource() {
        if (!connector) {
            throw new Error(
                "Please select a connector."
            );
        }

        if (!organizationId) {
            throw new Error(
                "Organization ID is required."
            );
        }

        if (!sourceName.trim()) {
            throw new Error(
                "Please enter a connection name."
            );
        }

        const data =
            await apiRequest(
                "/sources",
                {
                    method: "POST",
                    body: JSON.stringify({
                        name:
                            sourceName.trim(),

                        source_type:
                            connector.id,

                        organization_id:
                            organizationId,

                        external_id:
                            externalId.trim() ||
                            null,

                        connection_config:
                            connectionConfig,

                        enabled: true,
                    }),
                }
            );

        setSource(data);

        return data;
    }


    // --------------------------------------------------------------------------
    // Configure step
    // --------------------------------------------------------------------------

    async function handleConfigure() {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            if (!connector) {
                throw new Error(
                    "Please select a connector."
                );
            }

            if (!source) {
                await createSource();
            }

            setSuccess(
                "Connector configuration saved."
            );

            setCurrentStep(
                getNextStepIndex(
                    "authenticate"
                )
            );
        } catch (err) {
            setError(
                getApiErrorMessage(
                    err,
                    "Unable to configure connector."
                )
            );
        } finally {
            setLoading(false);
        }
    }


    // --------------------------------------------------------------------------
    // Authenticate step
    // --------------------------------------------------------------------------

    async function handleAuthenticate() {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            if (!source) {
                await createSource();
            }

            setSuccess(
                "Authentication configuration is ready."
            );

            setCurrentStep(
                getNextStepIndex(
                    "test"
                )
            );
        } catch (err) {
            setError(
                getApiErrorMessage(
                    err,
                    "Unable to save authentication configuration."
                )
            );
        } finally {
            setLoading(false);
        }
    }


    // --------------------------------------------------------------------------
    // Test step
    // --------------------------------------------------------------------------

    async function handleTest() {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            let activeSource =
                source;

            if (!activeSource) {
                activeSource =
                    await createSource();
            }

            const result =
                await apiRequest(
                    `/sources/${activeSource.id}/test`,
                    {
                        method: "POST",
                    }
                );

            setTestResult(
                result
            );

            setSuccess(
                "Connection test completed successfully."
            );

            setCurrentStep(
                getNextStepIndex(
                    "discover"
                )
            );
        } catch (err) {
            setTestResult(null);

            setError(
                getApiErrorMessage(
                    err,
                    "Connection test failed."
                )
            );
        } finally {
            setLoading(false);
        }
    }


    // --------------------------------------------------------------------------
    // Discover step
    // --------------------------------------------------------------------------

    async function handleDiscover() {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            if (!source) {
                throw new Error(
                    "No configured source is available."
                );
            }

            const result =
                await apiRequest(
                    `/sources/${source.id}/discover`,
                    {
                        method: "POST",
                    }
                );

            setDiscoveryResult(
                result
            );

            const resources =
                extractResources(
                    result
                );

            setDiscoveredResources(
                resources
            );

            setSelectedResourceIds(
                resources
                    .filter(
                        (resource) =>
                            resource.selected ===
                            true
                    )
                    .map(
                        getResourceId
                    )
                    .filter(Boolean)
            );

            setSuccess(
                `Discovered ${resources.length} resource(s).`
            );

            setCurrentStep(
                getNextStepIndex(
                    "select"
                )
            );
        } catch (err) {
            setError(
                getApiErrorMessage(
                    err,
                    "Resource discovery failed."
                )
            );
        } finally {
            setLoading(false);
        }
    }


    // --------------------------------------------------------------------------
    // Select step
    // --------------------------------------------------------------------------

    async function handleSelect() {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            if (!source) {
                throw new Error(
                    "No configured source is available."
                );
            }

            const selectedResources =
                discoveredResources.filter(
                    (resource) =>
                        selectedResourceIds.includes(
                            getResourceId(
                                resource
                            )
                        )
                );

            const result =
                await apiRequest(
                    `/sources/${source.id}/select`,
                    {
                        method: "POST",
                        body: JSON.stringify({
                            resources:
                                selectedResources,

                            resource_ids:
                                selectedResourceIds,

                            selection: {
                                selected:
                                    selectedResourceIds,
                            },
                        }),
                    }
                );

            setSuccess(
                `${selectedResourceIds.length} resource(s) selected.`
            );

            if (
                supportsLifecycleStage(
                    connector,
                    "initial_sync"
                )
            ) {
                setCurrentStep(
                    getNextStepIndex(
                        "initial_sync"
                    )
                );
            } else {
                await handleInitialSync();
            }

            return result;
        } catch (err) {
            setError(
                getApiErrorMessage(
                    err,
                    "Unable to save resource selection."
                )
            );
        } finally {
            setLoading(false);
        }
    }


    // --------------------------------------------------------------------------
    // Initial sync
    // --------------------------------------------------------------------------

    async function handleInitialSync() {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            if (!source) {
                throw new Error(
                    "No configured source is available."
                );
            }

            const result =
                await apiRequest(
                    `/sources/${source.id}/sync/initial?use_mock_llm=true`,
                    {
                        method: "POST",
                    }
                );

            setSyncResult(
                result
            );

            setSuccess(
                "Initial synchronization completed."
            );

            if (
                onComplete
            ) {
                onComplete(
                    result
                );
            }
        } catch (err) {
            setError(
                getApiErrorMessage(
                    err,
                    "Initial synchronization failed."
                )
            );
        } finally {
            setLoading(false);
        }
    }


    // --------------------------------------------------------------------------
    // Continuous sync
    // --------------------------------------------------------------------------

    async function handleContinuousSync() {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            if (!source) {
                throw new Error(
                    "No configured source is available."
                );
            }

            const result =
                await apiRequest(
                    `/sources/${source.id}/sync/continuous?use_mock_llm=true`,
                    {
                        method: "POST",
                    }
                );

            setSyncResult(
                result
            );

            setSuccess(
                "Continuous synchronization completed."
            );

            if (
                onComplete
            ) {
                onComplete(
                    result
                );
            }
        } catch (err) {
            setError(
                getApiErrorMessage(
                    err,
                    "Continuous synchronization failed."
                )
            );
        } finally {
            setLoading(false);
        }
    }


    // --------------------------------------------------------------------------
    // Determine next lifecycle step
    // --------------------------------------------------------------------------

    function getNextStepIndex(
        stage
    ) {
        const index =
            WIZARD_STEPS.findIndex(
                (step) =>
                    step.id ===
                    stage
            );

        if (index < 0) {
            return currentStep;
        }

        return index;
    }


    // --------------------------------------------------------------------------
    // Back
    // --------------------------------------------------------------------------

    function handleBack() {
        if (
            currentStep <= 0
        ) {
            return;
        }

        setError(null);
        setSuccess(null);

        setCurrentStep(
            currentStep - 1
        );
    }


    // --------------------------------------------------------------------------
    // Resource selection
    // --------------------------------------------------------------------------

    function toggleResource(
        resource
    ) {
        const id =
            getResourceId(
                resource
            );

        if (!id) {
            return;
        }

        setSelectedResourceIds(
            (previous) => {
                if (
                    previous.includes(
                        id
                    )
                ) {
                    return previous.filter(
                        (item) =>
                            item !== id
                    );
                }

                return [
                    ...previous,
                    id,
                ];
            }
        );
    }


    function selectAllResources() {
        setSelectedResourceIds(
            discoveredResources
                .map(
                    getResourceId
                )
                .filter(Boolean)
        );
    }


    function clearAllResources() {
        setSelectedResourceIds(
            []
        );
    }


    // --------------------------------------------------------------------------
    // Render
    // --------------------------------------------------------------------------

    return (
        <div
            style={styles.container}
        >
            <div
                style={styles.header}
            >
                <div>
                    <h2
                        style={styles.title}
                    >
                        Add Data Connector
                    </h2>

                    <p
                        style={styles.subtitle}
                    >
                        Connect a trusted data source to the
                        Context Trust Layer.
                    </p>
                </div>

                {onCancel && (
                    <button
                        type="button"
                        onClick={onCancel}
                        style={styles.secondaryButton}
                    >
                        Cancel
                    </button>
                )}
            </div>


            {/* ------------------------------------------------------------------ */}
            {/* STEP INDICATOR                                                     */}
            {/* ------------------------------------------------------------------ */}

            <div
                style={styles.stepContainer}
            >
                {WIZARD_STEPS.map(
                    (step, index) => {
                        const completed =
                            index <
                            currentStep;

                        const active =
                            index ===
                            currentStep;

                        return (
                            <React.Fragment
                                key={step.id}
                            >
                                <div
                                    style={{
                                        ...styles.step,
                                        ...(active
                                            ? styles.activeStep
                                            : {}),
                                        ...(completed
                                            ? styles.completedStep
                                            : {}),
                                    }}
                                >
                                    <div
                                        style={
                                            styles.stepNumber
                                        }
                                    >
                                        {completed
                                            ? "✓"
                                            : index + 1}
                                    </div>

                                    <div>
                                        <div
                                            style={
                                                styles.stepLabel
                                            }
                                        >
                                            {
                                                step.label
                                            }
                                        </div>

                                        <div
                                            style={
                                                styles.stepDescription
                                            }
                                        >
                                            {
                                                step.description
                                            }
                                        </div>
                                    </div>
                                </div>

                                {index <
                                    WIZARD_STEPS.length -
                                    1 && (
                                        <div
                                            style={
                                                styles.stepLine
                                            }
                                        />
                                    )}
                            </React.Fragment>
                        );
                    }
                )}
            </div>


            {/* ------------------------------------------------------------------ */}
            {/* ALERTS                                                             */}
            {/* ------------------------------------------------------------------ */}

            {error && (
                <div
                    style={
                        styles.errorMessage
                    }
                >
                    <strong>
                        Error
                    </strong>

                    <span>
                        {error}
                    </span>
                </div>
            )}

            {success && (
                <div
                    style={
                        styles.successMessage
                    }
                >
                    {success}
                </div>
            )}


            {/* ------------------------------------------------------------------ */}
            {/* CONTENT                                                            */}
            {/* ------------------------------------------------------------------ */}

            <div
                style={styles.content}
            >

                {/* -------------------------------------------------------------- */}
                {/* CONNECTOR SELECTION                                            */}
                {/* -------------------------------------------------------------- */}

                {!connector && (
                    <ConnectorSelection
                        groupedConnectors={
                            groupedConnectors
                        }
                        loading={
                            catalogLoading
                        }
                        error={
                            catalogError
                        }
                        selectedConnectorId={
                            selectedConnectorId
                        }
                        onSelect={
                            handleConnectorSelect
                        }
                    />
                )}


                {/* -------------------------------------------------------------- */}
                {/* CONFIGURE                                                       */}
                {/* -------------------------------------------------------------- */}

                {connector &&
                    currentStep === 0 && (
                        <ConfigureStep
                            connector={
                                connector
                            }
                            sourceName={
                                sourceName
                            }
                            setSourceName={
                                setSourceName
                            }
                            externalId={
                                externalId
                            }
                            setExternalId={
                                setExternalId
                            }
                            fields={
                                connectorFields
                            }
                            config={
                                connectionConfig
                            }
                            updateConfig={
                                updateConfig
                            }
                        />
                    )}


                {/* -------------------------------------------------------------- */}
                {/* AUTHENTICATE                                                    */}
                {/* -------------------------------------------------------------- */}

                {connector &&
                    currentStep === 1 && (
                        <AuthenticateStep
                            connector={
                                connector
                            }
                            fields={
                                connectorFields
                            }
                            config={
                                connectionConfig
                            }
                            updateConfig={
                                updateConfig
                            }
                        />
                    )}


                {/* -------------------------------------------------------------- */}
                {/* TEST                                                            */}
                {/* -------------------------------------------------------------- */}

                {connector &&
                    currentStep === 2 && (
                        <TestStep
                            connector={
                                connector
                            }
                            result={
                                testResult
                            }
                            loading={
                                loading
                            }
                        />
                    )}


                {/* -------------------------------------------------------------- */}
                {/* DISCOVER                                                        */}
                {/* -------------------------------------------------------------- */}

                {connector &&
                    currentStep === 3 && (
                        <DiscoverStep
                            connector={
                                connector
                            }
                            result={
                                discoveryResult
                            }
                            resources={
                                discoveredResources
                            }
                            loading={
                                loading
                            }
                        />
                    )}


                {/* -------------------------------------------------------------- */}
                {/* SELECT                                                          */}
                {/* -------------------------------------------------------------- */}

                {connector &&
                    currentStep === 4 && (
                        <SelectStep
                            resources={
                                discoveredResources
                            }
                            selectedIds={
                                selectedResourceIds
                            }
                            onToggle={
                                toggleResource
                            }
                            onSelectAll={
                                selectAllResources
                            }
                            onClearAll={
                                clearAllResources
                            }
                        />
                    )}


                {/* -------------------------------------------------------------- */}
                {/* INITIAL SYNC                                                    */}
                {/* -------------------------------------------------------------- */}

                {connector &&
                    currentStep === 5 && (
                        <InitialSyncStep
                            connector={
                                connector
                            }
                            result={
                                syncResult
                            }
                            loading={
                                loading
                            }
                            onContinuousSync={
                                handleContinuousSync
                            }
                        />
                    )}

            </div>


            {/* ------------------------------------------------------------------ */}
            {/* FOOTER                                                             */}
            {/* ------------------------------------------------------------------ */}

            {connector && (
                <div
                    style={styles.footer}
                >
                    <button
                        type="button"
                        onClick={
                            currentStep === 0
                                ? () => {
                                    setConnector(
                                        null
                                    );
                                    setSelectedConnectorId(
                                        null
                                    );
                                }
                                : handleBack
                        }
                        disabled={
                            loading
                        }
                        style={
                            styles.secondaryButton
                        }
                    >
                        {currentStep === 0
                            ? "Change Connector"
                            : "Back"}
                    </button>


                    <div
                        style={
                            styles.footerRight
                        }
                    >

                        {currentStep ===
                            0 && (
                                <button
                                    type="button"
                                    onClick={
                                        handleConfigure
                                    }
                                    disabled={
                                        loading
                                    }
                                    style={
                                        styles.primaryButton
                                    }
                                >
                                    {loading
                                        ? "Saving..."
                                        : "Continue"}
                                </button>
                            )}


                        {currentStep ===
                            1 && (
                                <button
                                    type="button"
                                    onClick={
                                        handleAuthenticate
                                    }
                                    disabled={
                                        loading
                                    }
                                    style={
                                        styles.primaryButton
                                    }
                                >
                                    {loading
                                        ? "Saving..."
                                        : "Continue"}
                                </button>
                            )}


                        {currentStep ===
                            2 && (
                                <button
                                    type="button"
                                    onClick={
                                        handleTest
                                    }
                                    disabled={
                                        loading
                                    }
                                    style={
                                        styles.primaryButton
                                    }
                                >
                                    {loading
                                        ? "Testing..."
                                        : "Test Connection"}
                                </button>
                            )}


                        {currentStep ===
                            3 && (
                                <button
                                    type="button"
                                    onClick={
                                        handleDiscover
                                    }
                                    disabled={
                                        loading
                                    }
                                    style={
                                        styles.primaryButton
                                    }
                                >
                                    {loading
                                        ? "Discovering..."
                                        : "Discover Resources"}
                                </button>
                            )}


                        {currentStep ===
                            4 && (
                                <button
                                    type="button"
                                    onClick={
                                        handleSelect
                                    }
                                    disabled={
                                        loading ||
                                        selectedResourceIds.length ===
                                        0
                                    }
                                    style={
                                        styles.primaryButton
                                    }
                                >
                                    {loading
                                        ? "Saving..."
                                        : `Select ${selectedResourceIds.length} Resource${selectedResourceIds.length ===
                                            1
                                            ? ""
                                            : "s"
                                        }`}
                                </button>
                            )}


                        {currentStep ===
                            5 && (
                                <>
                                    {!syncResult && (
                                        <button
                                            type="button"
                                            onClick={
                                                handleInitialSync
                                            }
                                            disabled={
                                                loading
                                            }
                                            style={
                                                styles.primaryButton
                                            }
                                        >
                                            {loading
                                                ? "Synchronizing..."
                                                : "Start Initial Sync"}
                                        </button>
                                    )}

                                    {syncResult && (
                                        <button
                                            type="button"
                                            onClick={
                                                handleContinuousSync
                                            }
                                            disabled={
                                                loading
                                            }
                                            style={
                                                styles.primaryButton
                                            }
                                        >
                                            {loading
                                                ? "Synchronizing..."
                                                : "Run Continuous Sync"}
                                        </button>
                                    )}
                                </>
                            )}
                    </div>
                </div>
            )}
        </div>
    );
}


// ============================================================================
// CONNECTOR SELECTION
// ============================================================================

function ConnectorSelection({
    groupedConnectors,
    loading,
    error,
    selectedConnectorId,
    onSelect,
}) {
    const [
        search,
        setSearch,
    ] = useState("");

    const filteredGroups =
        useMemo(() => {
            const query =
                search
                    .trim()
                    .toLowerCase();

            if (!query) {
                return groupedConnectors;
            }

            return groupedConnectors
                .map(
                    (group) => ({
                        ...group,

                        connectors:
                            group.connectors.filter(
                                (connector) => {
                                    const value = [
                                        connector.id,
                                        connector.name,
                                        connector.family,
                                        connector.description,
                                    ]
                                        .filter(Boolean)
                                        .join(" ")
                                        .toLowerCase();

                                    return value.includes(
                                        query
                                    );
                                }
                            ),
                    })
                )
                .filter(
                    (group) =>
                        group.connectors.length >
                        0
                );
        }, [
            groupedConnectors,
            search,
        ]);

    if (loading) {
        return (
            <div
                style={
                    styles.emptyState
                }
            >
                Loading connectors...
            </div>
        );
    }

    if (error) {
        return (
            <div
                style={
                    styles.errorMessage
                }
            >
                {error}
            </div>
        );
    }

    return (
        <div>
            <div
                style={
                    styles.sectionHeader
                }
            >
                <div>
                    <h3
                        style={
                            styles.sectionTitle
                        }
                    >
                        Select a connector
                    </h3>

                    <p
                        style={
                            styles.sectionDescription
                        }
                    >
                        Choose the source you want to
                        connect to the Context Trust Layer.
                    </p>
                </div>

                <span
                    style={
                        styles.connectorCount
                    }
                >
                    {groupedConnectors.reduce(
                        (
                            total,
                            group
                        ) =>
                            total +
                            group.connectors
                                .length,
                        0
                    )}{" "}
                    connectors
                </span>
            </div>

            <input
                type="search"
                value={search}
                onChange={(event) =>
                    setSearch(
                        event.target.value
                    )
                }
                placeholder="Search connectors..."
                style={
                    styles.searchInput
                }
            />

            {filteredGroups.map(
                (group) => (
                    <div
                        key={group.id}
                        style={
                            styles.category
                        }
                    >
                        <h4
                            style={
                                styles.categoryTitle
                            }
                        >
                            {group.label}
                        </h4>

                        <div
                            style={
                                styles.connectorGrid
                            }
                        >
                            {group.connectors.map(
                                (item) => {
                                    const selected =
                                        selectedConnectorId ===
                                        item.id;

                                    return (
                                        <button
                                            key={
                                                item.id
                                            }
                                            type="button"
                                            onClick={() =>
                                                onSelect(
                                                    item.id
                                                )
                                            }
                                            style={{
                                                ...styles.connectorCard,
                                                ...(selected
                                                    ? styles.selectedConnectorCard
                                                    : {}),
                                            }}
                                        >
                                            <div
                                                style={
                                                    styles.connectorIcon
                                                }
                                            >
                                                {getInitials(
                                                    item.name
                                                )}
                                            </div>

                                            <div
                                                style={
                                                    styles.connectorCardContent
                                                }
                                            >
                                                <div
                                                    style={
                                                        styles.connectorName
                                                    }
                                                >
                                                    {
                                                        item.name
                                                    }
                                                </div>

                                                <div
                                                    style={
                                                        styles.connectorDescription
                                                    }
                                                >
                                                    {
                                                        item.description
                                                    }
                                                </div>

                                                <div
                                                    style={
                                                        styles.connectorMeta
                                                    }
                                                >
                                                    <span>
                                                        {item.driver ===
                                                            "native"
                                                            ? "Native"
                                                            : "Universal"}
                                                    </span>

                                                    {item.family && (
                                                        <span>
                                                            {
                                                                item.family
                                                            }
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </button>
                                    );
                                }
                            )}
                        </div>
                    </div>
                )
            )}
        </div>
    );
}


// ============================================================================
// CONFIGURE STEP
// ============================================================================

function ConfigureStep({
    connector,
    sourceName,
    setSourceName,
    externalId,
    setExternalId,
    fields,
    config,
    updateConfig,
}) {
    return (
        <div>
            <StepHeader
                title="Configure connector"
                description={`Configure ${connector.name} before authentication.`}
            />

            <div
                style={
                    styles.form
                }
            >
                <div
                    style={
                        styles.formGroup
                    }
                >
                    <label
                        style={
                            styles.label
                        }
                    >
                        Connection name
                    </label>

                    <input
                        type="text"
                        value={sourceName}
                        onChange={(event) =>
                            setSourceName(
                                event.target.value
                            )
                        }
                        placeholder={`${connector.name} Connection`}
                        style={
                            styles.input
                        }
                    />
                </div>

                <div
                    style={
                        styles.formGroup
                    }
                >
                    <label
                        style={
                            styles.label
                        }
                    >
                        External ID
                        <span
                            style={
                                styles.optional
                            }
                        >
                            Optional
                        </span>
                    </label>

                    <input
                        type="text"
                        value={externalId}
                        onChange={(event) =>
                            setExternalId(
                                event.target.value
                            )
                        }
                        placeholder="External source identifier"
                        style={
                            styles.input
                        }
                    />
                </div>

                {fields
                    .filter(
                        (field) =>
                            !isAuthenticationField(
                                field
                            )
                    )
                    .map(
                        (field) => (
                            <DynamicField
                                key={
                                    getFieldName(
                                        field
                                    )
                                }
                                field={
                                    field
                                }
                                value={
                                    config[
                                    getFieldName(
                                        field
                                    )
                                    ]
                                }
                                onChange={
                                    updateConfig
                                }
                            />
                        )
                    )}
            </div>
        </div>
    );
}


// ============================================================================
// AUTHENTICATE STEP
// ============================================================================

function AuthenticateStep({
    connector,
    fields,
    config,
    updateConfig,
}) {
    const authFields =
        fields.filter(
            isAuthenticationField
        );

    return (
        <div>
            <StepHeader
                title="Authenticate"
                description={`Provide the authentication information required by ${connector.name}.`}
            />

            <div
                style={
                    styles.securityNotice
                }
            >
                <strong>
                    Secure credentials
                </strong>

                <span>
                    Credentials are sent to the backend
                    connector layer and should never be
                    stored in frontend code.
                </span>
            </div>

            <div
                style={
                    styles.form
                }
            >
                {authFields.length ===
                    0 && (
                        <div
                            style={
                                styles.infoMessage
                            }
                        >
                            This connector does not expose
                            additional authentication fields.
                            Authentication will be handled by
                            the configured connector driver.
                        </div>
                    )}

                {authFields.map(
                    (field) => (
                        <DynamicField
                            key={
                                getFieldName(
                                    field
                                )
                            }
                            field={
                                field
                            }
                            value={
                                config[
                                getFieldName(
                                    field
                                )
                                ]
                            }
                            onChange={
                                updateConfig
                            }
                        />
                    )
                )}
            </div>
        </div>
    );
}


// ============================================================================
// TEST STEP
// ============================================================================

function TestStep({
    connector,
    result,
    loading,
}) {
    return (
        <div>
            <StepHeader
                title="Test connection"
                description={`Verify that the Context Trust Layer can connect to ${connector.name}.`}
            />

            {!result && !loading && (
                <div
                    style={
                        styles.actionPanel
                    }
                >
                    <div
                        style={
                            styles.actionIcon
                        }
                    >
                        ✓
                    </div>

                    <h3>
                        Ready to test
                    </h3>

                    <p>
                        Click "Test Connection" to verify
                        authentication and connectivity.
                    </p>
                </div>
            )}

            {loading && (
                <div
                    style={
                        styles.actionPanel
                    }
                >
                    <div
                        style={
                            styles.spinner
                        }
                    >
                        ...
                    </div>

                    <h3>
                        Testing connection
                    </h3>

                    <p>
                        Verifying credentials and connector
                        availability.
                    </p>
                </div>
            )}

            {result && (
                <ResultPanel
                    result={
                        result
                    }
                    success
                />
            )}
        </div>
    );
}


// ============================================================================
// DISCOVER STEP
// ============================================================================

function DiscoverStep({
    connector,
    result,
    resources,
    loading,
}) {
    return (
        <div>
            <StepHeader
                title="Discover resources"
                description={`Discover the tables, projects, repositories, topics, dashboards, files or other resources exposed by ${connector.name}.`}
            />

            {loading && (
                <div
                    style={
                        styles.actionPanel
                    }
                >
                    Discovering resources...
                </div>
            )}

            {!loading &&
                !result && (
                    <div
                        style={
                            styles.actionPanel
                        }
                    >
                        <h3>
                            Ready to discover
                        </h3>

                        <p>
                            The connector will inspect the
                            configured source and return resources
                            that can be selected for synchronization.
                        </p>
                    </div>
                )}

            {result && (
                <div>
                    <ResultPanel
                        result={
                            result
                        }
                        success
                    />

                    <div
                        style={
                            styles.resourceSummary
                        }
                    >
                        <strong>
                            {resources.length}
                        </strong>

                        <span>
                            resources discovered
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
}


// ============================================================================
// SELECT STEP
// ============================================================================

function SelectStep({
    resources,
    selectedIds,
    onToggle,
    onSelectAll,
    onClearAll,
}) {
    return (
        <div>
            <StepHeader
                title="Select resources"
                description="Choose which discovered resources should enter the Context Trust Layer."
            />

            <div
                style={
                    styles.selectionToolbar
                }
            >
                <span>
                    {selectedIds.length} of{" "}
                    {resources.length} selected
                </span>

                <div
                    style={
                        styles.toolbarButtons
                    }
                >
                    <button
                        type="button"
                        onClick={
                            onSelectAll
                        }
                        style={
                            styles.linkButton
                        }
                    >
                        Select all
                    </button>

                    <button
                        type="button"
                        onClick={
                            onClearAll
                        }
                        style={
                            styles.linkButton
                        }
                    >
                        Clear all
                    </button>
                </div>
            </div>

            {resources.length ===
                0 && (
                    <div
                        style={
                            styles.emptyState
                        }
                    >
                        No resources were discovered.
                    </div>
                )}

            <div
                style={
                    styles.resourceList
                }
            >
                {resources.map(
                    (resource) => {
                        const id =
                            getResourceId(
                                resource
                            );

                        const selected =
                            selectedIds.includes(
                                id
                            );

                        return (
                            <label
                                key={
                                    id ||
                                    JSON.stringify(
                                        resource
                                    )
                                }
                                style={{
                                    ...styles.resourceRow,
                                    ...(selected
                                        ? styles.selectedResourceRow
                                        : {}),
                                }}
                            >
                                <input
                                    type="checkbox"
                                    checked={
                                        selected
                                    }
                                    onChange={() =>
                                        onToggle(
                                            resource
                                        )
                                    }
                                />

                                <div
                                    style={
                                        styles.resourceContent
                                    }
                                >
                                    <strong>
                                        {
                                            getResourceName(
                                                resource
                                            )
                                        }
                                    </strong>

                                    <span>
                                        {
                                            getResourceType(
                                                resource
                                            )
                                        }
                                    </span>
                                </div>
                            </label>
                        );
                    }
                )}
            </div>
        </div>
    );
}


// ============================================================================
// INITIAL SYNC STEP
// ============================================================================

function InitialSyncStep({
    connector,
    result,
    loading,
    onContinuousSync,
}) {
    return (
        <div>
            <StepHeader
                title="Initial synchronization"
                description={`Import the selected ${connector.name} resources into the Context Trust Layer.`}
            />

            {!result && (
                <div
                    style={
                        styles.actionPanel
                    }
                >
                    <h3>
                        Ready for initial sync
                    </h3>

                    <p>
                        The synchronization pipeline will
                        ingest, normalize, establish provenance,
                        detect conflicts and create lineage.
                    </p>

                    <div
                        style={
                            styles.pipeline
                        }
                    >
                        {[
                            "Initial Sync",
                            "Normalize",
                            "Provenance",
                            "Conflict Detection",
                            "Lineage",
                            "Monitoring",
                        ].map(
                            (stage) => (
                                <span
                                    key={stage}
                                    style={
                                        styles.pipelineStage
                                    }
                                >
                                    {stage}
                                </span>
                            )
                        )}
                    </div>
                </div>
            )}

            {loading && (
                <div
                    style={
                        styles.actionPanel
                    }
                >
                    Synchronizing...
                </div>
            )}

            {result && (
                <>
                    <ResultPanel
                        result={
                            result
                        }
                        success
                    />

                    <div
                        style={
                            styles.actionPanel
                        }
                    >
                        <h3>
                            Initial sync complete
                        </h3>

                        <p>
                            You can now run continuous
                            synchronization whenever required.
                        </p>

                        <button
                            type="button"
                            onClick={
                                onContinuousSync
                            }
                            disabled={
                                loading
                            }
                            style={
                                styles.primaryButton
                            }
                        >
                            Run Continuous Sync
                        </button>
                    </div>
                </>
            )}
        </div>
    );
}


// ============================================================================
// DYNAMIC FIELD
// ============================================================================

function DynamicField({
    field,
    value,
    onChange,
}) {
    const name =
        getFieldName(
            field
        );

    const type =
        normalizeFieldType(
            field
        );

    const label =
        getFieldLabel(
            field
        );

    const required =
        getFieldRequired(
            field
        );

    if (!name) {
        return null;
    }

    return (
        <div
            style={
                styles.formGroup
            }
        >
            <label
                style={
                    styles.label
                }
            >
                {label}

                {required && (
                    <span
                        style={
                            styles.required
                        }
                    >
                        *
                    </span>
                )}

                {!required && (
                    <span
                        style={
                            styles.optional
                        }
                    >
                        Optional
                    </span>
                )}
            </label>

            {type ===
                "textarea" && (
                    <textarea
                        value={
                            value ?? ""
                        }
                        required={
                            required
                        }
                        placeholder={
                            getFieldPlaceholder(
                                field
                            )
                        }
                        onChange={(event) =>
                            onChange(
                                name,
                                event.target.value
                            )
                        }
                        style={
                            styles.textarea
                        }
                    />
                )}

            {type ===
                "select" && (
                    <select
                        value={
                            value ?? ""
                        }
                        required={
                            required
                        }
                        onChange={(event) =>
                            onChange(
                                name,
                                event.target.value
                            )
                        }
                        style={
                            styles.input
                        }
                    >
                        <option value="">
                            Select...
                        </option>

                        {getFieldOptions(
                            field
                        ).map(
                            (option) => {
                                const optionValue =
                                    typeof option ===
                                        "object"
                                        ? option.value
                                        : option;

                                const optionLabel =
                                    typeof option ===
                                        "object"
                                        ? option.label ||
                                        option.name ||
                                        option.value
                                        : option;

                                return (
                                    <option
                                        key={
                                            optionValue
                                        }
                                        value={
                                            optionValue
                                        }
                                    >
                                        {
                                            optionLabel
                                        }
                                    </option>
                                );
                            }
                        )}
                    </select>
                )}

            {type ===
                "checkbox" && (
                    <input
                        type="checkbox"
                        checked={
                            Boolean(value)
                        }
                        onChange={(event) =>
                            onChange(
                                name,
                                event.target.checked
                            )
                        }
                    />
                )}

            {type !==
                "textarea" &&
                type !==
                "select" &&
                type !==
                "checkbox" && (
                    <input
                        type={
                            isSecretField(
                                field
                            )
                                ? "password"
                                : type
                        }
                        value={
                            value ?? ""
                        }
                        required={
                            required
                        }
                        placeholder={
                            getFieldPlaceholder(
                                field
                            )
                        }
                        onChange={(event) =>
                            onChange(
                                name,
                                event.target.value
                            )
                        }
                        style={
                            styles.input
                        }
                    />
                )}

            {field.description && (
                <span
                    style={
                        styles.fieldHelp
                    }
                >
                    {
                        field.description
                    }
                </span>
            )}
        </div>
    );
}


// ============================================================================
// STEP HEADER
// ============================================================================

function StepHeader({
    title,
    description,
}) {
    return (
        <div
            style={
                styles.sectionHeader
            }
        >
            <div>
                <h3
                    style={
                        styles.sectionTitle
                    }
                >
                    {title}
                </h3>

                <p
                    style={
                        styles.sectionDescription
                    }
                >
                    {description}
                </p>
            </div>
        </div>
    );
}


// ============================================================================
// RESULT PANEL
// ============================================================================

function ResultPanel({
    result,
    success = false,
}) {
    return (
        <div
            style={{
                ...styles.resultPanel,
                ...(success
                    ? styles.successResultPanel
                    : {}),
            }}
        >
            <div
                style={
                    styles.resultStatus
                }
            >
                {success
                    ? "✓"
                    : "!"}
            </div>

            <div
                style={
                    styles.resultContent
                }
            >
                <strong>
                    {result?.message ||
                        result?.status ||
                        "Operation completed"}
                </strong>

                {result?.documents_synced !==
                    undefined && (
                        <div>
                            Documents synced:{" "}
                            {
                                result.documents_synced
                            }
                        </div>
                    )}

                {result?.documents_created !==
                    undefined && (
                        <div>
                            Documents created:{" "}
                            {
                                result.documents_created
                            }
                        </div>
                    )}

                {result?.claims_extracted !==
                    undefined && (
                        <div>
                            Claims extracted:{" "}
                            {
                                result.claims_extracted
                            }
                        </div>
                    )}

                {result?.conflicts_detected !==
                    undefined && (
                        <div>
                            Conflicts detected:{" "}
                            {
                                result.conflicts_detected
                            }
                        </div>
                    )}
            </div>
        </div>
    );
}


// ============================================================================
// RESOURCE HELPERS
// ============================================================================

function extractResources(
    result
) {
    if (!result) {
        return [];
    }

    const candidates = [
        result.resources,
        result.items,
        result.data?.resources,
        result.data?.items,
        result.discovered_resources,
        result.records,
    ];

    for (
        const candidate of candidates
    ) {
        if (
            Array.isArray(
                candidate
            )
        ) {
            return candidate;
        }
    }

    return [];
}


function getResourceId(
    resource
) {
    if (
        resource ===
        null
    ) {
        return null;
    }

    if (
        typeof resource ===
        "string"
    ) {
        return resource;
    }

    return (
        resource.id ||
        resource.resource_id ||
        resource.external_id ||
        resource.name ||
        resource.path ||
        resource.key ||
        null
    );
}


function getResourceName(
    resource
) {
    if (
        typeof resource ===
        "string"
    ) {
        return resource;
    }

    return (
        resource.name ||
        resource.display_name ||
        resource.title ||
        resource.id ||
        resource.resource_id ||
        "Unnamed resource"
    );
}


function getResourceType(
    resource
) {
    if (
        typeof resource ===
        "string"
    ) {
        return "resource";
    }

    return (
        resource.type ||
        resource.resource_type ||
        resource.kind ||
        resource.category ||
        "resource"
    );
}


// ============================================================================
// AUTH FIELD HELPER
// ============================================================================

function isAuthenticationField(
    field
) {
    const name =
        getFieldName(
            field
        ).toLowerCase();

    const authKeywords = [
        "token",
        "password",
        "secret",
        "api_key",
        "apikey",
        "client_id",
        "client_secret",
        "username",
        "email",
        "credential",
        "private_key",
        "access_key",
        "access_token",
        "refresh_token",
    ];

    return authKeywords.some(
        (keyword) =>
            name.includes(
                keyword
            )
    );
}


// ============================================================================
// DISPLAY HELPERS
// ============================================================================

function getInitials(
    name
) {
    if (!name) {
        return "?";
    }

    const parts =
        name
            .trim()
            .split(
                /\s+/
            );

    if (
        parts.length ===
        1
    ) {
        return parts[0]
            .slice(
                0,
                2
            )
            .toUpperCase();
    }

    return (
        parts[0][0] +
        parts[
        parts.length - 1
        ][0]
    ).toUpperCase();
}


// ============================================================================
// STYLES
// ============================================================================

const styles = {
    container: {
        width: "100%",
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "24px",
        boxSizing: "border-box",
        background:
            "#ffffff",
        borderRadius:
            "12px",
    },

    header: {
        display: "flex",
        justifyContent:
            "space-between",
        alignItems:
            "flex-start",
        gap: "20px",
        marginBottom:
            "28px",
    },

    title: {
        margin: 0,
        fontSize: "24px",
        fontWeight: 700,
    },

    subtitle: {
        margin:
            "8px 0 0",
        color:
            "#64748b",
        fontSize: "14px",
    },

    stepContainer: {
        display: "flex",
        alignItems: "center",
        marginBottom:
            "28px",
        overflowX: "auto",
        paddingBottom:
            "8px",
    },

    step: {
        display: "flex",
        alignItems: "center",
        gap: "8px",
        minWidth: "130px",
        color:
            "#64748b",
    },

    activeStep: {
        color:
            "#0f172a",
        fontWeight: 600,
    },

    completedStep: {
        color:
            "#166534",
    },

    stepNumber: {
        width: "28px",
        height: "28px",
        minWidth: "28px",
        borderRadius:
            "50%",
        display: "flex",
        alignItems: "center",
        justifyContent:
            "center",
        border:
            "1px solid #cbd5e1",
        fontSize: "12px",
    },

    stepLabel: {
        fontSize: "12px",
    },

    stepDescription: {
        fontSize: "10px",
        marginTop:
            "2px",
        whiteSpace:
            "nowrap",
    },

    stepLine: {
        width: "28px",
        minWidth: "28px",
        height: "1px",
        background:
            "#cbd5e1",
        margin:
            "0 8px",
    },

    content: {
        minHeight:
            "400px",
    },

    sectionHeader: {
        display: "flex",
        justifyContent:
            "space-between",
        gap: "20px",
        marginBottom:
            "20px",
    },

    sectionTitle: {
        margin: 0,
        fontSize: "20px",
        fontWeight: 700,
    },

    sectionDescription: {
        margin:
            "7px 0 0",
        color:
            "#64748b",
        fontSize: "14px",
        lineHeight: 1.5,
    },

    connectorCount: {
        whiteSpace:
            "nowrap",
        color:
            "#64748b",
        fontSize: "13px",
    },

    searchInput: {
        width: "100%",
        boxSizing:
            "border-box",
        padding:
            "12px 14px",
        border:
            "1px solid #cbd5e1",
        borderRadius:
            "8px",
        marginBottom:
            "24px",
        fontSize: "14px",
    },

    category: {
        marginBottom:
            "28px",
    },

    categoryTitle: {
        margin:
            "0 0 12px",
        fontSize: "15px",
        fontWeight: 700,
    },

    connectorGrid: {
        display: "grid",
        gridTemplateColumns:
            "repeat(auto-fill, minmax(260px, 1fr))",
        gap: "12px",
    },

    connectorCard: {
        display: "flex",
        textAlign: "left",
        gap: "12px",
        padding: "14px",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "10px",
        background:
            "#ffffff",
        cursor: "pointer",
    },

    selectedConnectorCard: {
        border:
            "2px solid var(--primary, #FFAB4A)",
        background:
            "var(--primary-50, #FFF9F2)",
    },

    connectorIcon: {
        width: "40px",
        height: "40px",
        minWidth: "40px",
        borderRadius:
            "8px",
        display: "flex",
        alignItems: "center",
        justifyContent:
            "center",
        background:
            "#e2e8f0",
        fontSize: "12px",
        fontWeight: 700,
    },

    connectorCardContent: {
        minWidth: 0,
    },

    connectorName: {
        fontWeight: 700,
        fontSize: "14px",
    },

    connectorDescription: {
        marginTop:
            "4px",
        color:
            "#64748b",
        fontSize: "12px",
        lineHeight: 1.4,
    },

    connectorMeta: {
        display: "flex",
        gap: "8px",
        marginTop:
            "8px",
        fontSize: "10px",
        color:
            "#64748b",
    },

    form: {
        maxWidth:
            "720px",
        display: "flex",
        flexDirection:
            "column",
        gap: "18px",
    },

    formGroup: {
        display: "flex",
        flexDirection:
            "column",
        gap: "7px",
    },

    label: {
        fontSize: "13px",
        fontWeight: 600,
    },

    required: {
        marginLeft:
            "4px",
        color:
            "#dc2626",
    },

    optional: {
        marginLeft:
            "7px",
        color:
            "#94a3b8",
        fontSize: "11px",
        fontWeight: 400,
    },

    input: {
        width: "100%",
        boxSizing:
            "border-box",
        padding:
            "11px 12px",
        border:
            "1px solid #cbd5e1",
        borderRadius:
            "7px",
        fontSize: "14px",
        background:
            "#ffffff",
    },

    textarea: {
        width: "100%",
        minHeight:
            "110px",
        boxSizing:
            "border-box",
        padding:
            "11px 12px",
        border:
            "1px solid #cbd5e1",
        borderRadius:
            "7px",
        fontSize: "14px",
        resize: "vertical",
    },

    fieldHelp: {
        fontSize: "11px",
        color:
            "#64748b",
    },

    securityNotice: {
        display: "flex",
        flexDirection:
            "column",
        gap: "4px",
        padding:
            "14px",
        borderRadius:
            "8px",
        background:
            "#f8fafc",
        border:
            "1px solid #e2e8f0",
        marginBottom:
            "20px",
        fontSize: "13px",
    },

    actionPanel: {
        padding:
            "48px 24px",
        textAlign:
            "center",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "10px",
        background:
            "#f8fafc",
    },

    actionIcon: {
        width: "48px",
        height: "48px",
        margin:
            "0 auto 16px",
        borderRadius:
            "50%",
        display: "flex",
        alignItems:
            "center",
        justifyContent:
            "center",
        background:
            "#dcfce7",
        color:
            "#166534",
        fontWeight: 700,
    },

    spinner: {
        fontSize:
            "20px",
        marginBottom:
            "12px",
    },

    resourceSummary: {
        display: "flex",
        gap: "8px",
        alignItems:
            "baseline",
        padding:
            "16px",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "8px",
        marginTop:
            "16px",
    },

    selectionToolbar: {
        display: "flex",
        justifyContent:
            "space-between",
        alignItems:
            "center",
        padding:
            "12px 0",
        marginBottom:
            "10px",
        fontSize: "13px",
    },

    toolbarButtons: {
        display: "flex",
        gap: "12px",
    },

    linkButton: {
        border: "none",
        background:
            "transparent",
        cursor: "pointer",
        fontSize: "12px",
        fontWeight: 600,
        color:
            "var(--primary-dark, #C96E07)",
    },

    resourceList: {
        display: "flex",
        flexDirection:
            "column",
        gap: "8px",
    },

    resourceRow: {
        display: "flex",
        alignItems:
            "center",
        gap: "12px",
        padding:
            "13px",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "8px",
        cursor: "pointer",
    },

    selectedResourceRow: {
        background:
            "#eff6ff",
        borderColor:
            "#93c5fd",
    },

    resourceContent: {
        display: "flex",
        flexDirection:
            "column",
        gap: "3px",
    },

    pipeline: {
        display: "flex",
        flexWrap:
            "wrap",
        justifyContent:
            "center",
        gap: "8px",
        marginTop:
            "20px",
    },

    pipelineStage: {
        padding:
            "7px 10px",
        borderRadius:
            "20px",
        background:
            "#e2e8f0",
        fontSize: "11px",
    },

    resultPanel: {
        display: "flex",
        gap: "12px",
        padding:
            "16px",
        borderRadius:
            "9px",
        background:
            "#f8fafc",
        border:
            "1px solid #e2e8f0",
        marginBottom:
            "20px",
    },

    successResultPanel: {
        background:
            "#f0fdf4",
        borderColor:
            "#bbf7d0",
    },

    resultStatus: {
        fontSize:
            "20px",
        fontWeight: 700,
    },

    resultContent: {
        display: "flex",
        flexDirection:
            "column",
        gap: "4px",
        fontSize: "13px",
    },

    infoMessage: {
        padding:
            "14px",
        background:
            "#f8fafc",
        border:
            "1px solid #e2e8f0",
        borderRadius:
            "8px",
        color:
            "#475569",
        fontSize: "13px",
    },

    errorMessage: {
        display: "flex",
        gap: "8px",
        padding:
            "12px 14px",
        marginBottom:
            "16px",
        borderRadius:
            "8px",
        background:
            "#fef2f2",
        border:
            "1px solid #fecaca",
        color:
            "#991b1b",
        fontSize: "13px",
    },

    successMessage: {
        padding:
            "12px 14px",
        marginBottom:
            "16px",
        borderRadius:
            "8px",
        background:
            "#f0fdf4",
        border:
            "1px solid #bbf7d0",
        color:
            "#166534",
        fontSize: "13px",
    },

    emptyState: {
        padding:
            "48px 20px",
        textAlign:
            "center",
        color:
            "#64748b",
        border:
            "1px dashed #cbd5e1",
        borderRadius:
            "10px",
    },

    footer: {
        display: "flex",
        justifyContent:
            "space-between",
        alignItems:
            "center",
        marginTop:
            "28px",
        paddingTop:
            "18px",
        borderTop:
            "1px solid #e2e8f0",
    },

    footerRight: {
        display: "flex",
        gap: "10px",
    },

    primaryButton: {
        border: "1px solid var(--primary-hover, #F5982C)",
        borderRadius:
            "7px",
        padding:
            "10px 18px",
        background:
            "var(--primary, #FFAB4A)",
        color:
            "var(--text-main, #0F172A)",
        cursor: "pointer",
        fontWeight: 650,
        fontSize: "13px",
    },

    secondaryButton: {
        border:
            "1px solid #cbd5e1",
        borderRadius:
            "7px",
        padding:
            "10px 18px",
        background:
            "#ffffff",
        color:
            "#334155",
        cursor: "pointer",
        fontWeight: 600,
        fontSize: "13px",
    },
};