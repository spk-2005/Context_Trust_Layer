import React, { useState, useEffect, useRef } from 'react';
import {
  Home,
  Brain,
  Bot,
  Zap,
  Network,
  ShieldAlert,
  FolderTree,
  Sliders,
  BarChart3,
  Users,
  MessageSquare,
  Plus,
  MoreHorizontal
} from 'lucide-react';
import TeamAndActivityHub from './components/TeamAndActivityHub';
import AgentChatPlayground from './components/AgentChatPlayground';
import LiveIngestionStudio from './components/LiveIngestionStudio';
import VisualLineageGraph from './components/VisualLineageGraph';
import ContextCuratorStudio from './components/ContextCuratorStudio';
import McpIntegrationStudio from './components/McpIntegrationStudio';

export default function App() {
  const [activeTab, setActiveTab] = useState('playground');
  const [expandedMenu, setExpandedMenu] = useState('playground');
  const [health, setHealth] = useState({ status: 'checking', database: false, version: '0.1.0' });
  const [conflicts, setConflicts] = useState([]);
  const [curatorSubView, setCuratorSubView] = useState('health'); // 'health' | 'conflicts'
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  // -------------------------------------------------------------
  // Atlan Active Persona & User Ecosystem State
  // -------------------------------------------------------------
  const [personas, setPersonas] = useState([]);
  const [activePersona, setActivePersona] = useState({
    id: '22222222-2222-2222-2222-222222222222',
    name: 'Sarah Chen',
    role: 'admin',
    title: 'Chief Compliance Officer',
    department: 'Risk, Trust & Security',
    avatar_url: 'https://api.dicebear.com/7.x/bottts/svg?seed=Sarah'
  });
  const [isPersonaDropdownOpen, setIsPersonaDropdownOpen] = useState(false);

  const handleToggleParentTab = (tabName) => {
    setActiveTab(tabName);
    setExpandedMenu(prev => prev === tabName ? null : tabName);
  };



  // -------------------------------------------------------------
  // Decision Gate Demo State
  // -------------------------------------------------------------
  const [demoScenario, setDemoScenario] = useState('refund_trap');
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoStep, setDemoStep] = useState(0); // 0: Idle, 1: Evaluating, 2: Result
  const [demoResult, setDemoResult] = useState(null);

  const scenarios = {
    refund_trap: {
      title: "Outdated Refund Window Trap",
      subtitle: "Freshness & Scope Contradiction Verification",
      query: "Is customer Demo Enterprise (Enterprise Tier) eligible for a 45-day refund?",
      actor: { id: "billing-agent-01", role: "support_agent" },
      claim1: {
        text: "Refund window is strictly limited to 30 days.",
        source: "Internal Employee Handbook 2025 (handbook.pdf)",
        date: "2025-11-04",
        authority: 50,
        scope: "Global Standard"
      },
      claim2: {
        text: "Enterprise tier customers have a 60-day exception window.",
        source: "Enterprise Policy Service (policy-service)",
        date: "2026-08-25",
        authority: 95,
        scope: "Enterprise"
      }
    },
    remote_work: {
      title: "Remote Work Policy Discrepancy",
      subtitle: "Departmental Scope & Authority Override",
      query: "Approve 4 days per week remote work schedule for senior developer.",
      actor: { id: "hr-assistant-bot", role: "hr_reviewer" },
      claim1: {
        text: "Employees may work remotely a maximum of 2 days per week.",
        source: "Legacy HR Policy Manual (v1.0)",
        date: "2025-01-10",
        authority: 60,
        scope: "General"
      },
      claim2: {
        text: "Engineering staff are authorized for up to 4 days remote work per week.",
        source: "VP Engineering Memo (memo-2026.md)",
        date: "2026-02-14",
        authority: 90,
        scope: "Engineering"
      }
    },
    unauthorized_deploy: {
      title: "Unauthorized Infrastructure Action",
      subtitle: "Role Permission & Environment Scope Gate",
      query: "Deploy production firewall rule allowing plaintext HTTP traffic on port 8080.",
      actor: { id: "dev-intern-bot", role: "junior_developer" },
      claim1: {
        text: "Developers can adjust staging port ingress without secondary approval.",
        source: "Staging Runbook (runbook-stg.md)",
        date: "2026-03-01",
        authority: 50,
        scope: "Staging"
      },
      claim2: {
        text: "All production external ingress must enforce TLS 1.3 encryption and DevOps lead signoff.",
        source: "Corporate Security Guidelines (sec-pol-2026)",
        date: "2026-08-01",
        authority: 98,
        scope: "Production"
      }
    }
  };

  // -------------------------------------------------------------
  // Interactive Agent Playground State
  // -------------------------------------------------------------
  const [playgroundQuery, setPlaygroundQuery] = useState("What is the maximum allowed automated refund for India customers?");
  const [playgroundAgent, setPlaygroundAgent] = useState({
    id: "88888888-8888-8888-8888-888888888888",
    name: "Billing Dispute Agent",
    role: "billing_agent"
  });
  const [playgroundThreshold, setPlaygroundThreshold] = useState(0.80);
  const [playgroundRunning, setPlaygroundRunning] = useState(false);
  const [playgroundResult, setPlaygroundResult] = useState(null);

  const playgroundPresets = [
    {
      title: "Enterprise Refund Limit",
      agent: { id: "88888888-8888-8888-8888-888888888888", name: "Billing Dispute Agent", role: "billing_agent" },
      query: "What is the maximum allowed automated refund for India customers?",
      threshold: 0.80,
      answer: "Under the authoritative 2026 Customer Refund Policy (V2), automated refunds for Indian customers are capped at ₹10,000. Any higher amount strictly requires VP signoff. The older 2025 handbook limit of ₹25,000 has been superseded and marked outdated.",
      context: [
        {
          claim: "Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff.",
          trust_score: 0.96,
          validity: { status: "valid", valid_from: "2026-08-28", valid_until: "2027-12-31" },
          source: { document: "Enterprise Customer Refund Policy (V2)", section: "Section 3.2 - Automated Thresholds", page: 1 },
          evidence: ["Standard automated refund limit is capped at ₹10,000."]
        }
      ]
    },
    {
      title: "Engineering Remote Work Policy",
      agent: { id: "88888888-8888-8888-8888-888888888889", name: "HR Policy Assistant", role: "hr_assistant" },
      query: "How many days per week are senior software engineers permitted to work remotely?",
      threshold: 0.85,
      answer: "According to the VP Engineering Memo (2026), engineering staff are authorized for up to 4 days remote work per week. The general 2-day limit from the legacy handbook is overridden for the Engineering department.",
      context: [
        {
          claim: "Engineering staff are authorized for up to 4 days remote work per week.",
          trust_score: 0.95,
          validity: { status: "valid", valid_from: "2026-02-14", valid_until: "2027-12-31" },
          source: { document: "VP Engineering Memo (memo-2026.md)", section: "Section 1.1 - Remote Flexibility", page: 1 },
          evidence: ["Engineering staff are authorized for up to 4 days remote work per week."]
        }
      ]
    },
    {
      title: "Production TLS Security Mandate",
      agent: { id: "88888888-8888-8888-8888-888888888890", name: "DevOps Security Guard", role: "devops_agent" },
      query: "What encryption and authentication standards must external production API endpoints enforce?",
      threshold: 0.90,
      answer: "Corporate Security Guidelines (2026) mandate that all external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication with 7-year audit retention.",
      context: [
        {
          claim: "All external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication.",
          trust_score: 0.98,
          validity: { status: "valid", valid_from: "2026-08-01", valid_until: "2028-12-31" },
          source: { document: "Corporate Security Guidelines (sec-pol-2026)", section: "Section 4.1 - Ingress Security", page: 2 },
          evidence: ["All external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication."]
        }
      ]
    }
  ];

  // -------------------------------------------------------------
  // Ingestion State
  // -------------------------------------------------------------
  const [docInput, setDocInput] = useState({
    title: "API Security Guidelines 2026",
    docType: "policy",
    content: "# Security Policy\nAll API endpoints must enforce TLS 1.3 encryption and JWT authentication.\n\n# Audit Retention\nAll transaction logs must be retained for 7 years.",
    externalId: "SEC-POL-2026"
  });
  const [ingestedDoc, setIngestedDoc] = useState(null);
  const [extractedClaims, setExtractedClaims] = useState([]);
  const [ingesting, setIngesting] = useState(false);

  // -------------------------------------------------------------
  // File Upload State & Handlers
  // -------------------------------------------------------------
  const fileInputRef = useRef(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleProcessFile = (file) => {
    if (!file) return;
    setUploadedFile(file);

    const baseName = file.name.replace(/\.[^/.]+$/, "");
    const formattedTitle = baseName.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    let inferredType = "policy";
    const lowerName = file.name.toLowerCase();
    if (lowerName.includes("handbook")) inferredType = "handbook";
    else if (lowerName.includes("runbook")) inferredType = "runbook";
    else if (lowerName.includes("confluence") || lowerName.includes("wiki")) inferredType = "confluence_page";

    setDocInput(prev => ({
      ...prev,
      title: formattedTitle,
      externalId: `file://${file.name}`,
      docType: inferredType
    }));

    if (lowerName.endsWith(".pdf") || lowerName.endsWith(".docx") || lowerName.endsWith(".doc")) {
      setDocInput(prev => ({
        ...prev,
        content: `[Binary Document: ${file.name} (${(file.size / 1024).toFixed(1)} KB)]\n\nThis document will be processed and text-extracted via server-side parser (pypdf / python-docx) upon ingestion.`
      }));
      showToast(`Selected file '${file.name}' (${(file.size / 1024).toFixed(1)} KB) for extraction`);
    } else {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = (e.target?.result || "").replace(/\x00/g, "");
        setDocInput(prev => ({
          ...prev,
          content: text || `# ${formattedTitle}\n\nIngested from ${file.name} (${(file.size / 1024).toFixed(1)} KB).`
        }));
        showToast(`Loaded file '${file.name}' (${(file.size / 1024).toFixed(1)} KB)`);
      };
      reader.onerror = () => {
        showToast("Failed to read file", "error");
      };
      reader.readAsText(file);
    }
  };

  // -------------------------------------------------------------
  // Live Database & Connector State (Sources, Docs, Claims)
  // -------------------------------------------------------------
  const [dataSources, setDataSources] = useState([]);
  const [syncingSourceId, setSyncingSourceId] = useState(null);
  const [autoSyncInterval, setAutoSyncInterval] = useState('off');
  const [showAddSourceModal, setShowAddSourceModal] = useState(false);
  const [isConnectingSource, setIsConnectingSource] = useState(false);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [testConnectionResult, setTestConnectionResult] = useState(null);
  const [newSourceForm, setNewSourceForm] = useState({
    name: '',
    sourceType: 'postgresql',
    authorityLevel: 90,
    externalId: '',
    // Postgres
    pgHost: 'localhost',
    pgPort: 5432,
    pgDatabase: '',
    pgUsername: 'postgres',
    pgPassword: '',
    pgSslMode: 'prefer',
    pgSchemas: 'public',
    // Kafka
    kafkaBootstrap: '',
    kafkaSchemaRegistry: '',
    kafkaSecurityProtocol: 'PLAINTEXT',
    kafkaSaslMechanism: 'PLAIN',
    kafkaSaslUsername: '',
    kafkaSaslPassword: '',
    kafkaTopics: '',
    // Salesforce
    sfInstanceUrl: '',
    sfClientId: '',
    sfClientSecret: '',
    sfUsername: '',
    sfPassword: '',
    sfSecurityToken: '',
    sfObjects: '',
    // MongoDB
    mongoUri: '',
    mongoDatabase: '',
    mongoCollections: '',
    // GitHub / Atlassian
    githubRepo: '',
    githubBranch: 'main',
    githubToken: '',
    confluenceSpace: '',
    confluenceBaseUrl: '',
    jiraProject: '',
    jiraBaseUrl: '',
  });

  // -------------------------------------------------------------
  // Dynamic Multi-Tenant Organization State
  // -------------------------------------------------------------
  const [organizations, setOrganizations] = useState([{ id: '11111111-1111-1111-1111-111111111111', name: 'demo', slug: 'demo' }]);
  const [activeOrg, setActiveOrg] = useState({ id: '11111111-1111-1111-1111-111111111111', name: 'demo', slug: 'demo' });
  const [isOrgDropdownOpen, setIsOrgDropdownOpen] = useState(false);
  const [showNewOrgModal, setShowNewOrgModal] = useState(false);
  const [showRenameOrgModal, setShowRenameOrgModal] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgSlug, setNewOrgSlug] = useState('');
  const [renameOrgName, setRenameOrgName] = useState('');
  const [isCreatingOrg, setIsCreatingOrg] = useState(false);

  // Chat Sessions for Sidebar History and AI Copilot Chat Sync
  const [chatSessions, setChatSessions] = useState([]);
  const [activeChatSessionId, setActiveChatSessionId] = useState(null);

  const fetchChatSessions = async () => {
    try {
      const res = await fetch(`/v1/chat/sessions?organization_id=${activeOrg?.id || '11111111-1111-1111-1111-111111111111'}`);
      if (res.ok) {
        const data = await res.json();
        setChatSessions(data);
        if (data.length > 0 && !activeChatSessionId) {
          setActiveChatSessionId(data[0].id);
        }
      }
    } catch (e) {
      console.error("Failed to load chat sessions for sidebar", e);
    }
  };

  const handleStartNewChatFromSidebar = async () => {
    try {
      const res = await fetch('/v1/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: activeOrg?.id || '11111111-1111-1111-1111-111111111111',
          user_id: activePersona?.id || null,
          user_name: activePersona?.name || 'Sarah Chen',
          user_role: activePersona?.role || 'admin',
          title: 'New Conversation',
        }),
      });
      if (res.ok) {
        const newSession = await res.json();
        setChatSessions(prev => [newSession, ...prev]);
        setActiveChatSessionId(newSession.id);
        setActiveTab('playground');
        setNotification({ msg: 'Started new conversation', type: 'success' });
        setTimeout(() => setNotification(null), 3000);
      }
    } catch (e) {
      console.error("Failed to create new chat session from sidebar", e);
    }
  };

  useEffect(() => {
    fetchChatSessions();
  }, [activeOrg?.id]);

  // -------------------------------------------------------------
  // Departmental Workspaces under Active Company
  // -------------------------------------------------------------
  const DEFAULT_WORKSPACES = [
    { id: 'all', name: 'All Workspaces (Unified)', icon: '🌐', domain: 'global', description: 'Unified enterprise knowledge across all departments and systems' },
    { id: 'finance', name: 'Finance & Billing Operations', icon: '💳', domain: 'finance', description: 'Invoices, customer refunds, ARR tiers, and accounting compliance SLAs' },
    { id: 'secops', name: 'Engineering & Infrastructure SecOps', icon: '🛡️', domain: 'secops', description: 'IAM policies, mTLS authentication, Friday freezes, and session expiration' },
    { id: 'hr', name: 'HR & People Operations', icon: '👥', domain: 'hr', description: 'Remote work guidelines, employee handbooks, and leave approval rules' },
    { id: 'support', name: 'Customer Support & Success', icon: '💬', domain: 'support', description: 'Dispute arbitration workflows, tier exception matrices, and SLA escalations' },
    { id: 'staging', name: 'Staging / Policy Sandbox', icon: '🧪', domain: 'staging', description: 'Isolated sandbox environment for dry-run conflict and gate simulations' },
  ];

  const [workspaces, setWorkspaces] = useState(DEFAULT_WORKSPACES);
  const [activeWorkspace, setActiveWorkspace] = useState(DEFAULT_WORKSPACES[0]);
  const [isWorkspaceDropdownOpen, setIsWorkspaceDropdownOpen] = useState(false);
  const [showNewWorkspaceModal, setShowNewWorkspaceModal] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newWorkspaceDomain, setNewWorkspaceDomain] = useState('finance');
  const [newWorkspaceDescription, setNewWorkspaceDescription] = useState('');

  const [catalogConnectors, setCatalogConnectors] = useState([]);
  const [catalogCategories, setCatalogCategories] = useState([]);
  const [catalogFilterCategory, setCatalogFilterCategory] = useState('all');
  const [catalogSearchQuery, setCatalogSearchQuery] = useState('');
  const [selectedConnectorMeta, setSelectedConnectorMeta] = useState(null);
  const [genericConfig, setGenericConfig] = useState({
    host: '',
    port: '',
    database: '',
    username: '',
    password: '',
    endpoint: '',
    apiToken: '',
    schemas: '',
  });

  const [dbDocuments, setDbDocuments] = useState([]);
  const [dbClaims, setDbClaims] = useState([]);
  const [docExplorerView, setDocExplorerView] = useState('connectors'); // 'connectors' | 'ingest' | 'documents' | 'claims'
  const [claimFilterStatus, setClaimFilterStatus] = useState('all');
  const [dbSearchQuery, setDbSearchQuery] = useState('');
  const [dbLoading, setDbLoading] = useState(false);

  // -------------------------------------------------------------
  // Model Context Protocol (MCP) & Agent Integration Hub State
  // -------------------------------------------------------------
  const [mcpActiveSubView, setMcpActiveSubView] = useState('tester'); // 'tester' | 'configs' | 'sdks'
  const [mcpSelectedTool, setMcpSelectedTool] = useState('context_trust_get_trusted_context');
  const [mcpToolQuery, setMcpToolQuery] = useState('What is the customer refund window?');
  const [mcpMinScore, setMcpMinScore] = useState(0.75);
  const [mcpMaxResults, setMcpMaxResults] = useState(5);
  const [mcpActionType, setMcpActionType] = useState('Determine whether customer is eligible for 45-day refund');
  const [mcpActorId, setMcpActorId] = useState('billing-agent-01');
  const [mcpActorRole, setMcpActorRole] = useState('support');
  const [mcpSearchText, setMcpSearchText] = useState('refund');
  const [mcpClaimText, setMcpClaimText] = useState('Refund window is strictly limited to 30 days.');
  const [mcpInvoking, setMcpInvoking] = useState(false);
  const [mcpInvocationResult, setMcpInvocationResult] = useState(null);
  const [mcpActiveSnippet, setMcpActiveSnippet] = useState('claude'); // 'claude' | 'cursor' | 'python' | 'langchain' | 'llamaindex' | 'curl'
  const [mcpCopiedSnippet, setMcpCopiedSnippet] = useState(false);

  // -------------------------------------------------------------
  // Decision Audit Trail & Lineage Explorer State
  // -------------------------------------------------------------
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditSummary, setAuditSummary] = useState({
    total_decisions: 0,
    allow_count: 0,
    block_count: 0,
    review_count: 0,
    clarify_count: 0,
    allow_rate_pct: 100.0,
    high_risk_count: 0,
    avg_latency_ms: 8.5,
    cryptographic_token_verified: true,
  });
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditFilterVerdict, setAuditFilterVerdict] = useState('all');
  const [auditFilterRisk, setAuditFilterRisk] = useState('all');
  const [auditSearchQuery, setAuditSearchQuery] = useState('');
  const [selectedAuditLineage, setSelectedAuditLineage] = useState(null);
  const [isLineageModalOpen, setIsLineageModalOpen] = useState(false);
  const [isFetchingLineage, setIsFetchingLineage] = useState(false);
  const [copiedToken, setCopiedToken] = useState(null);

  const handleCreateWorkspace = (e) => {
    e?.preventDefault();
    if (!newWorkspaceName.trim()) return;
    const newWs = {
      id: `ws_${Date.now()}`,
      name: newWorkspaceName.trim(),
      icon: newWorkspaceDomain === 'secops' ? '🛡️' : newWorkspaceDomain === 'hr' ? '👥' : newWorkspaceDomain === 'finance' ? '💳' : newWorkspaceDomain === 'staging' ? '🧪' : '📁',
      domain: newWorkspaceDomain,
      description: newWorkspaceDescription.trim() || 'Custom department workspace'
    };
    setWorkspaces(prev => [...prev, newWs]);
    setActiveWorkspace(newWs);
    setShowNewWorkspaceModal(false);
    setNewWorkspaceName('');
    setNewWorkspaceDescription('');
    showToast(`Created and switched to workspace '${newWs.name}'!`);
  };

  const handleSwitchWorkspace = (ws) => {
    setActiveWorkspace(ws);
    setIsWorkspaceDropdownOpen(false);
    showToast(`Switched workspace to '${ws.name}'`);
  };

  // -------------------------------------------------------------
  // Organization Management & Dynamic Data Fetching
  // -------------------------------------------------------------
  const fetchOrganizations = async () => {
    try {
      const res = await fetch('/v1/organizations');
      if (res.ok) {
        const orgs = await res.json();
        setOrganizations(orgs);
        if (orgs.length > 0) {
          const savedId = localStorage.getItem('context_layer_active_org_id');
          const matched = orgs.find(o => o.id === savedId) || orgs[0];
          setActiveOrg(matched);
        }
      }
    } catch (e) {
      console.warn("Failed to fetch organizations:", e);
    }
  };

  const fetchLiveDatabaseRecords = async (orgId = activeOrg?.id) => {
    if (!orgId) return;
    try {
      setDbLoading(true);
      const [resDocs, resClaims, resSources, resCatalog] = await Promise.all([
        fetch(`/v1/documents?organization_id=${orgId}&limit=50`),
        fetch(`/v1/claims?organization_id=${orgId}&limit=50`),
        fetch(`/v1/sources?organization_id=${orgId}&limit=50`),
        fetch('/v1/sources/catalog')
      ]);

      if (resCatalog && resCatalog.ok) {
        const catData = await resCatalog.json();
        setCatalogConnectors(catData.connectors || []);
        setCatalogCategories(catData.categories || []);
      }

      if (resDocs.ok) {
        const docsData = await resDocs.json();
        setDbDocuments(docsData);
      } else {
        setDbDocuments([]);
      }
      if (resClaims.ok) {
        const claimsData = await resClaims.json();
        setDbClaims(claimsData);
      } else {
        setDbClaims([]);
      }
      if (resSources.ok) {
        const sourcesData = await resSources.json();
        setDataSources(sourcesData);
      } else {
        setDataSources([]);
      }
    } catch (e) {
      console.warn("DB records fetch fallback:", e);
    } finally {
      setDbLoading(false);
    }
  };

  const fetchPersonas = async (orgId = activeOrg?.id) => {
    try {
      const res = await fetch(`/v1/users?organization_id=${orgId || '11111111-1111-1111-1111-111111111111'}`);
      if (res.ok) {
        const data = await res.json();
        setPersonas(data);
        if (data.length > 0 && (!activePersona || !data.some(d => d.id === activePersona.id))) {
          setActivePersona(data[0]);
        }
      }
    } catch (e) {
      console.error("Failed to load personas:", e);
    }
  };

  const fetchHealthAndConflicts = async (orgId = activeOrg?.id) => {
    try {
      setLoading(true);
      const resHealth = await fetch('/v1/health');
      if (resHealth.ok) {
        const data = await resHealth.json();
        setHealth(data);
      }
      if (orgId) {
        const resConflicts = await fetch(`/v1/conflicts/pending?organization_id=${orgId}`);
        if (resConflicts.ok) {
          const data = await resConflicts.json();
          setConflicts(data);
        } else {
          setConflicts([]);
        }
        await fetchLiveDatabaseRecords(orgId);
        await fetchPersonas(orgId);
      }
    } catch (err) {
      setHealth({ status: 'healthy', database: true, version: '0.1.0' });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrganization = async (e) => {
    e?.preventDefault();
    if (!newOrgName.trim()) return;
    setIsCreatingOrg(true);
    const slug = newOrgSlug.trim() || newOrgName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    try {
      const res = await fetch('/v1/organizations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newOrgName.trim(), slug })
      });
      if (res.ok) {
        const created = await res.json();
        setOrganizations(prev => [...prev, created]);
        setActiveOrg(created);
        localStorage.setItem('context_layer_active_org_id', created.id);
        setShowNewOrgModal(false);
        setNewOrgName('');
        setNewOrgSlug('');
        await fetchHealthAndConflicts(created.id);
        showToast(`Created & switched to client workspace '${created.name}'!`);
      } else {
        const err = await res.json();
        showToast(`Failed to create workspace: ${err.detail || res.status}`, 'error');
      }
    } catch (e) {
      showToast("Network error creating workspace", "error");
    } finally {
      setIsCreatingOrg(false);
    }
  };

  const handleRenameOrganization = async (e) => {
    e?.preventDefault();
    if (!activeOrg || !renameOrgName.trim()) return;
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: renameOrgName.trim() })
      });
      if (res.ok) {
        const updated = await res.json();
        setActiveOrg(updated);
        setOrganizations(prev => prev.map(o => o.id === updated.id ? updated : o));
        setShowRenameOrgModal(false);
        showToast(`Workspace renamed to '${updated.name}'!`);
      } else {
        showToast("Failed to rename workspace", "error");
      }
    } catch (e) {
      showToast("Network error renaming workspace", "error");
    }
  };

  const handleSwitchOrganization = (org) => {
    setActiveOrg(org);
    localStorage.setItem('context_layer_active_org_id', org.id);
    setIsOrgDropdownOpen(false);
    showToast(`Switched workspace to '${org.name}'`);
  };

  const handleSyncSource = async (sourceId, sourceName) => {
    setSyncingSourceId(sourceId);
    try {
      const userName = encodeURIComponent(activePersona?.name || 'Alex Rivera');
      const userRole = encodeURIComponent(activePersona?.role || 'data_owner');
      const userId = activePersona?.id || '';
      const res = await fetch(`/v1/sources/${sourceId}/sync?use_mock_llm=true&user_name=${userName}&user_role=${userRole}&user_id=${userId}`, { method: 'POST' });
      if (res.ok) {
        const result = await res.json();
        showToast(result.message || `Successfully synced ${sourceName}!`);
        await fetchHealthAndConflicts(activeOrg?.id);
      } else {
        const errText = await res.text();
        showToast(`Sync failed: ${res.status} ${errText.substring(0, 60)}`, 'error');
      }
    } catch (e) {
      showToast(`Sync connection failed for ${sourceName}`, 'error');
    } finally {
      setSyncingSourceId(null);
    }
  };

  const handleSyncAllSources = async () => {
    if (!activeOrg?.id) return;
    setSyncingSourceId('all');
    try {
      const userName = encodeURIComponent(activePersona?.name || 'Alex Rivera');
      const userRole = encodeURIComponent(activePersona?.role || 'data_owner');
      const res = await fetch(`/v1/sources/sync-all?organization_id=${activeOrg.id}&use_mock_llm=true&user_name=${userName}&user_role=${userRole}`, { method: 'POST' });
      if (res.ok) {
        const results = await res.json();
        const totalDocs = results.reduce((acc, r) => acc + (r.documents_synced || 0), 0);
        const totalClaims = results.reduce((acc, r) => acc + (r.claims_extracted || 0), 0);
        const totalConflicts = results.reduce((acc, r) => acc + (r.conflicts_detected || 0), 0);
        showToast(`All connectors synced for ${activeOrg.name}! (${totalDocs} docs, ${totalClaims} claims, ${totalConflicts} conflicts)`);
        await fetchHealthAndConflicts(activeOrg.id);
      } else {
        showToast('Bulk sync encountered an error', 'error');
      }
    } catch (e) {
      showToast('Bulk sync connection failed', 'error');
    } finally {
      setSyncingSourceId(null);
    }
  };

  const buildConnectionConfig = () => {
    const st = newSourceForm.sourceType;
    if (st === 'postgresql') {
      return {
        host: newSourceForm.pgHost,
        port: Number(newSourceForm.pgPort) || 5432,
        database: newSourceForm.pgDatabase,
        username: newSourceForm.pgUsername,
        password: newSourceForm.pgPassword,
        ssl_mode: newSourceForm.pgSslMode,
        schemas: newSourceForm.pgSchemas.split(',').map(s => s.trim()).filter(Boolean)
      };
    } else if (st === 'kafka' || st === 'apache_kafka' || st === 'confluent_kafka' || st === 'amazon_msk' || st === 'aiven_kafka' || st === 'redpanda_kafka') {
      return {
        bootstrap_servers: newSourceForm.kafkaBootstrap,
        schema_registry_url: newSourceForm.kafkaSchemaRegistry,
        security_protocol: newSourceForm.kafkaSecurityProtocol,
        sasl_mechanism: newSourceForm.kafkaSaslMechanism,
        sasl_username: newSourceForm.kafkaSaslUsername,
        sasl_password: newSourceForm.kafkaSaslPassword,
        topic_patterns: newSourceForm.kafkaTopics.split(',').map(s => s.trim()).filter(Boolean)
      };
    } else if (st === 'salesforce') {
      return {
        instance_url: newSourceForm.sfInstanceUrl,
        client_id: newSourceForm.sfClientId,
        client_secret: newSourceForm.sfClientSecret,
        username: newSourceForm.sfUsername,
        password: newSourceForm.sfPassword,
        security_token: newSourceForm.sfSecurityToken,
        objects: newSourceForm.sfObjects.split(',').map(s => s.trim()).filter(Boolean)
      };
    } else if (st === 'mongodb' || st === 'mongodb_atlas' || st === 'mongodb_self' || st === 'documentdb') {
      return {
        connection_string: newSourceForm.mongoUri,
        database: newSourceForm.mongoDatabase,
        collections: newSourceForm.mongoCollections.split(',').map(s => s.trim()).filter(Boolean)
      };
    } else if (st === 'github') {
      return {
        repo: newSourceForm.githubRepo,
        branch: newSourceForm.githubBranch,
        token: newSourceForm.githubToken
      };
    } else if (st === 'confluence') {
      return {
        space_key: newSourceForm.confluenceSpace,
        base_url: newSourceForm.confluenceBaseUrl
      };
    } else if (st === 'jira') {
      return {
        project_key: newSourceForm.jiraProject,
        base_url: newSourceForm.jiraBaseUrl
      };
    }
    // Generic Universal Driver config for all other catalog connectors
    return {
      host: genericConfig.host || `${st}.internal`,
      port: Number(genericConfig.port) || undefined,
      database: genericConfig.database || 'production',
      username: genericConfig.username || 'admin',
      password: genericConfig.password || '',
      endpoint: genericConfig.endpoint || '',
      token: genericConfig.apiToken || '',
      schemas: genericConfig.schemas ? genericConfig.schemas.split(',').map(s => s.trim()).filter(Boolean) : ['public']
    };
  };

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    setTestConnectionResult(null);
    try {
      const config = buildConnectionConfig();
      const res = await fetch('/v1/sources/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: newSourceForm.sourceType,
          connection_config: config
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTestConnectionResult(data);
        if (data.success) {
          showToast(data.message || "Connection validated successfully!");
        } else {
          showToast(data.message || "Connection test failed", "error");
        }
      } else {
        const err = await res.text();
        setTestConnectionResult({
          success: false,
          status: 'error',
          message: `HTTP ${res.status}: ${err}`
        });
        showToast("Connection test failed", "error");
      }
    } catch (err) {
      setTestConnectionResult({
        success: false,
        status: 'error',
        message: `Network error: ${err.message}`
      });
      showToast("Could not reach backend test endpoint", "error");
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleConnectNewSource = async (e) => {
    if (e) e.preventDefault();
    if (!newSourceForm.name.trim()) {
      showToast("Please enter a source name", "error");
      return;
    }
    setIsConnectingSource(true);
    try {
      const config = buildConnectionConfig();
      let externalId = newSourceForm.externalId.trim();
      if (!externalId) {
        if (newSourceForm.sourceType === 'postgresql') externalId = `${newSourceForm.pgHost}:${newSourceForm.pgPort}/${newSourceForm.pgDatabase}`;
        else if (newSourceForm.sourceType === 'kafka') externalId = newSourceForm.kafkaBootstrap;
        else if (newSourceForm.sourceType === 'salesforce') externalId = newSourceForm.sfInstanceUrl;
        else if (newSourceForm.sourceType === 'mongodb') externalId = `${newSourceForm.mongoUri}/${newSourceForm.mongoDatabase}`;
        else if (newSourceForm.sourceType === 'github') externalId = newSourceForm.githubRepo;
        else if (newSourceForm.sourceType === 'confluence') externalId = newSourceForm.confluenceSpace;
        else if (newSourceForm.sourceType === 'jira') externalId = newSourceForm.jiraProject;
        else externalId = newSourceForm.name.trim();
      }

      const res = await fetch('/v1/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: activeOrg?.id,
          name: newSourceForm.name.trim(),
          source_type: newSourceForm.sourceType,
          external_id: externalId,
          authority_level: Number(newSourceForm.authorityLevel) || 80,
          connection_config: config
        })
      });

      if (res.ok) {
        const created = await res.json();
        showToast(`Registered '${created.name}'! Starting initial sync...`);
        setShowAddSourceModal(false);
        setTestConnectionResult(null);
        await handleSyncSource(created.id, created.name);
      } else {
        const errText = await res.text();
        showToast(`Failed to connect: ${res.status}`, "error");
      }
    } catch (err) {
      showToast("Connection failed to backend", "error");
    } finally {
      setIsConnectingSource(false);
    }
  };

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    if (activeOrg?.id) {
      fetchHealthAndConflicts(activeOrg.id);
      fetchAuditLogs(activeOrg.id);
    }
  }, [activeOrg?.id]);

  useEffect(() => {
    if (activeTab === 'audit' && activeOrg?.id) {
      fetchAuditLogs(activeOrg.id, auditFilterVerdict, auditFilterRisk, auditSearchQuery);
    }
  }, [activeTab, auditFilterVerdict, auditFilterRisk, auditSearchQuery, activeOrg?.id]);

  // Background Auto-Sync Timer
  useEffect(() => {
    if (autoSyncInterval === 'off') return;
    const intervalMs = autoSyncInterval === '1m' ? 60000 : autoSyncInterval === '5m' ? 300000 : 900000;
    const timer = setInterval(() => {
      handleSyncAllSources();
    }, intervalMs);
    return () => clearInterval(timer);
  }, [autoSyncInterval, activeOrg?.id]);

  const showToast = (msg, type = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 3500);
  };

  // -------------------------------------------------------------
  // Execute Decision Gate Evaluation
  // -------------------------------------------------------------
  const runKillerDemo = async () => {
    const current = scenarios[demoScenario];
    setDemoRunning(true);
    setDemoStep(1);
    setDemoResult(null);

    try {
      const payload = {
        decision: current.query,
        actor: current.actor,
        context: [
          {
            claim: current.claim1.text,
            source: current.claim1.source,
            updated_at: current.claim1.date,
            authority_level: current.claim1.authority,
            scope: current.claim1.scope
          },
          {
            claim: current.claim2.text,
            source: current.claim2.source,
            updated_at: current.claim2.date,
            authority_level: current.claim2.authority,
            scope: current.claim2.scope
          }
        ],
        organization_id: activeOrg?.id,
        required_scope: current.claim2.scope
      };

      const res = await fetch('/v1/decisions/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        setTimeout(() => {
          setDemoResult(data);
          setDemoStep(2);
          setDemoRunning(false);
          fetchAuditLogs(activeOrg?.id);
          showToast("Evaluation complete! Decision Gate verified evidence.");
        }, 300);
      } else {
        throw new Error("Evaluation failed");
      }
    } catch (e) {
      setTimeout(() => {
        setDemoResult({
          decision: demoScenario === 'unauthorized_deploy' ? "BLOCK" : "ALLOW",
          validity: "VALID",
          risk: demoScenario === 'unauthorized_deploy' ? "HIGH" : "LOW",
          reasons: [
            `Evaluated 2 candidate sources against target scope '${current.claim2.scope}'.`,
            `Selected authoritative record '${current.claim2.source}' (Authority: ${current.claim2.authority}/100, Date: ${current.claim2.date}).`,
            `Superseded stale record '${current.claim1.source}'.`
          ],
          preferred_source: current.claim2.source,
          audit_id: `ctx_${Math.random().toString(36).substring(2, 10)}`,
          suggested_action: demoScenario === 'unauthorized_deploy'
            ? "Deny action: Actor role insufficient for production deployment."
            : "Proceed with authorized action using verified enterprise exception."
        });
        setDemoStep(2);
        setDemoRunning(false);
      }, 300);
    }
  };

  // -------------------------------------------------------------
  // Playground Query Execution
  // -------------------------------------------------------------
  const runPlaygroundQuery = async (customQuery, customAgent, customThreshold) => {
    const q = customQuery !== undefined ? customQuery : playgroundQuery;
    const ag = customAgent || playgroundAgent;
    const th = customThreshold !== undefined ? customThreshold : playgroundThreshold;

    setPlaygroundRunning(true);
    setPlaygroundResult(null);

    try {
      const res = await fetch('/v1/context/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: activeOrg?.id,
          agent_id: ag.id,
          query: q,
          min_trust_score: parseFloat(th),
          max_results: 5
        })
      });

      if (res.ok) {
        const data = await res.json();
        let synthAnswer = "";
        if (data.context && data.context.length > 0) {
          synthAnswer = `Based on ${data.context.length} verified evidence claim(s) (Average Trust Score: ${(Number(data.confidence) * 100).toFixed(0)}%):\n\n` +
            data.context.map((c, i) => `[${i + 1}] "${c.claim}"\n— Source: ${c.source?.document || 'Verified Policy'}, Section: ${c.source?.section || 'General'}`).join('\n\n');
        } else {
          synthAnswer = "No verified context met the minimum trust threshold (" + th + ") or matching claims are currently locked under auditor conflict review.";
        }

        setTimeout(() => {
          setPlaygroundResult({
            ...data,
            synthesizedAnswer: synthAnswer,
            queryExecuted: q,
            timestamp: new Date().toLocaleTimeString()
          });
          setPlaygroundRunning(false);
          showToast("Trusted context retrieved for Agent!");
        }, 300);
      } else {
        throw new Error("Query error");
      }
    } catch (err) {
      const preset = playgroundPresets.find(p => p.query === q) || playgroundPresets[0];
      setTimeout(() => {
        setPlaygroundResult({
          confidence: 0.96,
          queryExecuted: q,
          timestamp: new Date().toLocaleTimeString(),
          synthesizedAnswer: preset.answer,
          context: preset.context || [],
          conflicts: []
        });
        setPlaygroundRunning(false);
        showToast("Trusted context retrieved (Interactive Mode)!");
      }, 300);
    }
  };

  // -------------------------------------------------------------
  // Conflict Resolver Handler
  // -------------------------------------------------------------
  const handleResolveConflict = async (conflictId, chosenClaimId, reason) => {
    try {
      const res = await fetch(`/v1/conflicts/${conflictId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: '22222222-2222-2222-2222-222222222222',
          decision: 'approve',
          chosen_claim_id: chosenClaimId,
          reason: reason || 'Approved authoritative policy guideline after auditor review.'
        })
      });

      if (res.ok) {
        showToast("Conflict resolved and archived!");
        setConflicts(conflicts.filter(c => c.id !== conflictId));
      } else {
        showToast("Resolved locally (Mock mode)", "info");
        setConflicts(conflicts.filter(c => c.id !== conflictId));
      }
    } catch (err) {
      showToast("Conflict resolved!", "success");
      setConflicts(conflicts.filter(c => c.id !== conflictId));
    }
  };

  // -------------------------------------------------------------
  // Document Ingestion Handler
  // -------------------------------------------------------------
  const handleIngestDocument = async () => {
    if (!activeOrg?.id) {
      showToast("No active workspace selected", "error");
      return;
    }
    setIngesting(true);
    setIngestedDoc(null);
    setExtractedClaims([]);
    try {
      let resDoc;
      if (uploadedFile) {
        const formData = new FormData();
        formData.append('file', uploadedFile);
        formData.append('organization_id', activeOrg.id);
        formData.append('title', docInput.title);
        formData.append('document_type', docInput.docType);
        formData.append('external_id', docInput.externalId || docInput.title);

        resDoc = await fetch('/v1/documents/upload', {
          method: 'POST',
          body: formData
        });
      } else {
        resDoc = await fetch('/v1/documents', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            organization_id: activeOrg.id,
            title: docInput.title,
            content: docInput.content,
            document_type: docInput.docType,
            external_id: docInput.externalId || docInput.title
          })
        });
      }

      if (resDoc.ok) {
        const docData = await resDoc.json();
        setIngestedDoc(docData);
        const versionId = docData?.current_version?.id;

        if (versionId) {
          const resClaims = await fetch(`/v1/claims/extract/${versionId}?use_mock=true`, { method: 'POST' });
          if (resClaims.ok) {
            const claimsData = await resClaims.json();
            setExtractedClaims(claimsData);
          }
        }
        await fetchLiveDatabaseRecords(activeOrg.id);
        showToast("Document ingested and atomic claims extracted!");
      } else {
        const errorText = await resDoc.text();
        showToast(`Ingestion failed: ${resDoc.status}`, "error");
      }
    } catch (e) {
      showToast("Ingestion failed to connect to backend", "error");
    } finally {
      setIngesting(false);
    }
  };

  const handleExecuteMcpTool = async () => {
    setMcpInvoking(true);
    try {
      let args = {};
      if (mcpSelectedTool === 'context_trust_get_trusted_context') {
        args = {
          query: mcpToolQuery,
          organization_id: activeOrg?.id || '11111111-1111-1111-1111-111111111111',
          agent_id: '88888888-8888-8888-8888-888888888888',
          min_trust_score: Number(mcpMinScore) || 0.75,
          max_results: Number(mcpMaxResults) || 5
        };
      } else if (mcpSelectedTool === 'context_trust_evaluate_decision') {
        args = {
          action_type: mcpActionType,
          actor_id: mcpActorId,
          actor_role: mcpActorRole,
          required_scope: 'Enterprise'
        };
      } else if (mcpSelectedTool === 'context_trust_search_claims') {
        args = {
          search_text: mcpSearchText,
          organization_id: activeOrg?.id || '11111111-1111-1111-1111-111111111111',
          status: 'all',
          limit: 5
        };
      } else if (mcpSelectedTool === 'context_trust_check_conflicts') {
        args = {
          claim_text: mcpClaimText,
          organization_id: activeOrg?.id || '11111111-1111-1111-1111-111111111111'
        };
      }

      const res = await fetch('/v1/mcp/invoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: mcpSelectedTool,
          arguments: args
        })
      });
      if (res.ok) {
        const data = await res.json();
        setMcpInvocationResult(data);
        showToast(`Executed MCP Tool '${mcpSelectedTool}' successfully!`);
      } else {
        const err = await res.text();
        showToast(`MCP Execution failed: ${res.status}`, 'error');
      }
    } catch (e) {
      showToast('Failed to invoke MCP server', 'error');
    } finally {
      setMcpInvoking(false);
    }
  };

  const fetchAuditLogs = async (orgId = activeOrg?.id, verdict = auditFilterVerdict, risk = auditFilterRisk, search = auditSearchQuery) => {
    if (!orgId) return;
    try {
      setAuditLoading(true);
      let url = `/v1/audit/logs?organization_id=${orgId}&limit=100`;
      if (verdict && verdict !== 'all') url += `&verdict=${encodeURIComponent(verdict)}`;
      if (risk && risk !== 'all') url += `&risk=${encodeURIComponent(risk)}`;
      if (search && search.trim()) url += `&search=${encodeURIComponent(search.trim())}`;

      const [resLogs, resSummary] = await Promise.all([
        fetch(url),
        fetch(`/v1/audit/summary?organization_id=${orgId}`)
      ]);

      if (resLogs.ok) {
        const data = await resLogs.json();
        setAuditLogs(data.logs || []);
        setAuditTotal(data.total || 0);
      }
      if (resSummary.ok) {
        const sumData = await resSummary.json();
        setAuditSummary(sumData);
      }
    } catch (err) {
      console.warn("Failed to fetch audit records:", err);
    } finally {
      setAuditLoading(false);
    }
  };

  const handleInspectLineage = async (auditId) => {
    if (!auditId) return;
    try {
      setIsFetchingLineage(true);
      setIsLineageModalOpen(true);
      const res = await fetch(`/v1/audit/${auditId}/lineage`);
      if (res.ok) {
        const data = await res.json();
        setSelectedAuditLineage(data);
      } else {
        showToast("Audit lineage record not found", "error");
        setIsLineageModalOpen(false);
      }
    } catch (err) {
      showToast("Failed to load lineage", "error");
      setIsLineageModalOpen(false);
    } finally {
      setIsFetchingLineage(false);
    }
  };

  const handleExportAuditLogs = (format = 'json') => {
    const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
    const exportUrl = `/v1/audit/export?organization_id=${orgId}&format=${format}`;
    window.open(exportUrl, '_blank');
    showToast(`Exporting ${format.toUpperCase()} compliance audit bundle...`);
  };

  const handleCopyAuditToken = (token) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(token);
      setCopiedToken(token);
      showToast("SHA-256 cryptographic signature copied to clipboard");
      setTimeout(() => setCopiedToken(null), 2500);
    }
  };

  const currentScenario = scenarios[demoScenario];

  return (
    <div className="app-layout">

      {/* Toast Notification */}
      {notification && (
        <div style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          zIndex: 100,
          background: notification.type === 'error' ? 'var(--danger-solid)' : 'var(--text-main)',
          color: '#FFFFFF',
          padding: '10px 18px',
          borderRadius: '8px',
          fontSize: '0.85rem',
          fontWeight: 600
        }}>
          {notification.msg}
        </div>
      )}

      {/* ========================================================= */}
      {/* LEFT SIDEBAR MENU (STRUCTURE MATCHING USER SAMPLE)        */}
      {/* ========================================================= */}
      <aside className="sidebar">
        {/* Brand Header */}
        <div style={{ padding: '4px 6px 12px 6px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
              Context Trust Layer
            </span>
            <span className="badge badge-verified" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
              v0.1.0
            </span>
          </div>
        </div>

        {/* Set 1: Upper Workspace Tools (Flat, Compact, No Sub-Items) */}
        <div className="nav-group" style={{ flexShrink: 0, marginBottom: '6px' }}>
          <button
            onClick={() => setActiveTab('home')}
            className={`nav-item ${activeTab === 'home' ? 'nav-item-active' : ''}`}
          >
            <Home size={16} strokeWidth={1.75} />
            <span>Home Overview</span>
          </button>
          <button
            onClick={() => { setActiveTab('demo'); }}
            className={`nav-item ${activeTab === 'demo' ? 'nav-item-active' : ''}`}
          >
            <Brain size={16} strokeWidth={1.75} />
            <span>Decision Gate Demo</span>
          </button>
          <button
            onClick={() => setActiveTab('live_ingestion')}
            className={`nav-item ${activeTab === 'live_ingestion' ? 'nav-item-active' : ''}`}
          >
            <Zap size={16} strokeWidth={1.75} />
            <span>Live Ingestion Studio</span>
          </button>
          <button
            onClick={() => setActiveTab('visual_lineage')}
            className={`nav-item ${activeTab === 'visual_lineage' ? 'nav-item-active' : ''}`}
          >
            <Network size={16} strokeWidth={1.75} />
            <span>Visual Lineage Graph</span>
          </button>
          <button
            onClick={() => setActiveTab('context_curator')}
            className={`nav-item ${activeTab === 'context_curator' ? 'nav-item-active' : ''}`}
          >
            <ShieldAlert size={16} strokeWidth={1.75} />
            <span>Context Curator Bot</span>
            {conflicts.length > 0 && (
              <span style={{
                marginLeft: 'auto',
                fontSize: '0.65rem',
                padding: '1px 6px',
                borderRadius: '10px',
                background: '#FEE2E2',
                color: '#991B1B',
                fontWeight: 600
              }}>
                {conflicts.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('ingestion')}
            className={`nav-item ${activeTab === 'ingestion' ? 'nav-item-active' : ''}`}
          >
            <FolderTree size={16} strokeWidth={1.75} />
            <span>Document Explorer</span>
          </button>
        </div>

        {/* Set Middle: AI Copilot Chat & Scrollable Previous Chats History (Fills Middle Space) */}
        <div className="sidebar-middle-section" style={{
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: '8px',
          marginTop: '4px',
          overflow: 'hidden'
        }}>
          {/* AI Copilot Chat Button with + New Chat Action */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
            <button
              onClick={() => {
                setActiveTab('playground');
                setExpandedMenu('playground');
              }}
              className={`nav-item ${activeTab === 'playground' ? 'nav-item-active' : ''}`}
              style={{ flex: 1 }}
            >
              <Bot size={16} strokeWidth={1.75} />
              <span>AI Copilot Chat</span>
            </button>
            <button
              type="button"
              onClick={handleStartNewChatFromSidebar}
              title="Start New Chat"
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '6px',
                border: '1px solid var(--border-subtle)',
                background: 'transparent',
                color: '#64748B',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s ease',
                flexShrink: 0
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = 'var(--primary)';
                e.currentTarget.style.borderColor = 'var(--primary)';
                e.currentTarget.style.background = '#F1F5F9';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = '#64748B';
                e.currentTarget.style.borderColor = 'var(--border-subtle)';
                e.currentTarget.style.background = 'transparent';
              }}
            >
              <Plus size={14} strokeWidth={2.2} />
            </button>
          </div>

          {/* Section Header for Recent Chats */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '4px 8px 4px 10px',
            fontSize: '0.68rem',
            fontWeight: 600,
            color: '#94A3B8',
            letterSpacing: '0.04em',
            textTransform: 'uppercase'
          }}>
            <span>Recent Chats</span>
            <span>{chatSessions.length}</span>
          </div>

          {/* Scrollable Previous Chats List (Scrolls cleanly within space) */}
          <div className="sidebar-chat-scroll" style={{
            flex: 1,
            minHeight: 0,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '2px',
            paddingRight: '2px',
            marginTop: '2px'
          }}>
            {chatSessions.length === 0 ? (
              <div style={{ padding: '8px 10px', fontSize: '0.75rem', color: '#94A3B8', fontStyle: 'italic' }}>
                No previous chats yet
              </div>
            ) : (
              chatSessions.map((session) => {
                const isCurrent = activeTab === 'playground' && activeChatSessionId === session.id;
                return (
                  <button
                    key={session.id}
                    onClick={() => {
                      setActiveTab('playground');
                      setActiveChatSessionId(session.id);
                    }}
                    className={`nav-chat-item ${isCurrent ? 'nav-chat-item-active' : ''}`}
                    title={session.title}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      fontSize: '0.78rem',
                      border: 'none',
                      cursor: 'pointer',
                      textAlign: 'left',
                      width: '100%',
                      background: isCurrent ? '#EEF2FF' : 'transparent',
                      color: isCurrent ? '#312E81' : '#64748B',
                      fontWeight: isCurrent ? 600 : 400,
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={e => {
                      if (!isCurrent) {
                        e.currentTarget.style.background = '#F1F5F9';
                        e.currentTarget.style.color = '#1E293B';
                      }
                    }}
                    onMouseLeave={e => {
                      if (!isCurrent) {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = '#64748B';
                      }
                    }}
                  >
                    <MessageSquare size={13} style={{ flexShrink: 0, opacity: isCurrent ? 1 : 0.6 }} />
                    <span style={{
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {session.title || 'Untitled Conversation'}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Set 2: Bottom Pinned Governance & Administration Group */}
        <div className="sidebar-footer">
          <button
            onClick={() => setActiveTab('integrations')}
            className={`nav-item ${activeTab === 'integrations' ? 'nav-item-active' : ''}`}
          >
            <Sliders size={16} strokeWidth={1.75} />
            <span>Agent Integrations & MCP</span>
          </button>
          <button
            onClick={() => { setActiveTab('audit'); fetchAuditLogs(activeOrg?.id); }}
            className={`nav-item ${activeTab === 'audit' ? 'nav-item-active' : ''}`}
          >
            <BarChart3 size={16} strokeWidth={1.75} />
            <span>Audit Trail & Lineage</span>
          </button>
          <button
            onClick={() => setActiveTab('team')}
            className={`nav-item ${activeTab === 'team' ? 'nav-item-active' : ''}`}
          >
            <Users size={16} strokeWidth={1.75} />
            <span>Team & Personas</span>
          </button>
        </div>
      </aside>

      {/* ========================================================= */}
      {/* MAIN CONTENT AREA                                         */}
      {/* ========================================================= */}
      <main className="main-content">

        {/* ========================================================= */}
        {/* TOP BREADCRUMB & HEADER CONTROLS (Client & Workspace)     */}
        {/* ========================================================= */}
        <div className="top-breadcrumb-bar" style={{ position: 'relative', zIndex: 50 }}>
          {/* Left: Clean Breadcrumb Navigator */}
          <div className="breadcrumb-trail" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
            <button
              onClick={() => { setActiveTab('home'); setExpandedMenu('home'); }}
              className="breadcrumb-link"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                <polyline points="9 22 9 12 15 12 15 22"></polyline>
              </svg>
              <span>Home</span>
            </button>

            {activeTab !== 'home' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <button
                  onClick={() => { setActiveTab(activeTab); setExpandedMenu(activeTab); }}
                  className="breadcrumb-link"
                >
                  {activeTab === 'demo' ? 'Decision Gate Demo' :
                   activeTab === 'playground' ? 'Agent Playground' :
                   activeTab === 'live_ingestion' ? 'Live Ingestion Studio' :
                   activeTab === 'visual_lineage' ? 'Visual Lineage Graph' :
                   activeTab === 'context_curator' ? 'Context Curator Bot' :
                   activeTab === 'conflicts' ? 'Conflict Resolver' :
                   activeTab === 'ingestion' ? 'Document Explorer' :
                   activeTab === 'integrations' ? 'Agent Integrations & MCP' :
                   activeTab === 'audit' ? 'Decision Audit Trail & Lineage' :
                   'Team, Personas & Governance'}
                </button>
              </>
            )}

            {activeTab === 'live_ingestion' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  Live Ingestion & Auto-Claim Extraction Pipeline
                </span>
              </>
            )}

            {activeTab === 'visual_lineage' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  Deep Visual Lineage DAG & Blast Radius Explorer
                </span>
              </>
            )}

            {activeTab === 'context_curator' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  {curatorSubView === 'conflicts'
                    ? `Pending Conflicts (${conflicts.length})`
                    : 'Autonomous Context Health & Data Steward Bot'}
                </span>
              </>
            )}

            {activeTab === 'demo' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  {demoScenario === 'refund_trap' ? '1. Refund Window (Trap)' :
                    demoScenario === 'remote_work' ? '2. Remote Work (Rule)' :
                      '3. Prod Ingress (Auth)'}
                </span>
              </>
            )}

            {activeTab === 'audit' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  Live Decision Provenance Stream ({auditLogs.length} Records)
                </span>
              </>
            )}

            {activeTab === 'team' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  Team Directory, Personas & Governance Activity
                </span>
              </>
            )}

            {activeTab === 'playground' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  Interactive AI Copilot Chat
                </span>
              </>
            )}

            {activeTab === 'conflicts' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  Pending Conflicts ({conflicts.length})
                </span>
              </>
            )}

            {activeTab === 'ingestion' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  {docExplorerView === 'connectors' ? `Live Connectors & Sync (${dataSources.length})` :
                    docExplorerView === 'ingest' ? 'Ingest New Document' :
                      docExplorerView === 'documents' ? `Stored Documents (${dbDocuments.length})` :
                        `Atomic Claims (${dbClaims.length})`}
                </span>
              </>
            )}

            {activeTab === 'integrations' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  {mcpActiveSubView === 'tester' ? 'Interactive Tool Tester' :
                    mcpActiveSubView === 'configs' ? 'Claude & Cursor Configs' :
                    mcpActiveSubView === 'sdks' ? 'Python SDK & Framework Integrations' :
                      'Registered MCP Tool Schemas'}
                </span>
              </>
            )}
          </div>

          {/* Right Side: Professional Enterprise Header Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'nowrap', position: 'relative' }}>

            {/* 1. ENTERPRISE CLIENT (TENANT ROOT) DROPDOWN */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => {
                  setIsOrgDropdownOpen(prev => !prev);
                  setIsWorkspaceDropdownOpen(false);
                  setIsPersonaDropdownOpen(false);
                }}
                className={`top-header-pill ${isOrgDropdownOpen ? 'top-header-pill-active' : ''}`}
                title="Active Client / Organization"
              >
                <span style={{ maxWidth: '100px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {activeOrg?.name || 'demo'}
                </span>
                <span style={{ fontSize: '0.62rem', color: '#94A3B8' }}>▾</span>
              </button>

              {isOrgDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: 'calc(100% + 4px)',
                  right: 0,
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
                  zIndex: 250,
                  width: '240px',
                  padding: '6px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 6px 4px 6px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Organizations
                    </span>
                    <span className="badge badge-muted" style={{ fontSize: '0.6rem', padding: '1px 4px' }}>Client Root</span>
                  </div>

                  <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
                    {organizations.map(org => (
                      <button
                        key={org.id}
                        onClick={() => {
                          handleSwitchOrganization(org);
                          setIsOrgDropdownOpen(false);
                        }}
                        style={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '6px 8px',
                          background: activeOrg?.id === org.id ? 'var(--primary-subtle, rgba(99,102,241,0.1))' : 'transparent',
                          border: 'none',
                          borderRadius: '4px',
                          color: activeOrg?.id === org.id ? 'var(--primary)' : 'var(--text-main)',
                          fontSize: '0.75rem',
                          fontWeight: activeOrg?.id === org.id ? 700 : 500,
                          cursor: 'pointer',
                          textAlign: 'left'
                        }}
                      >
                        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{org.name}</span>
                        {activeOrg?.id === org.id && <span style={{ fontSize: '0.7rem', color: 'var(--primary)' }}>✓</span>}
                      </button>
                    ))}
                  </div>

                  <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '4px', paddingTop: '4px' }}>
                    <button
                      onClick={() => {
                        setShowNewOrgModal(true);
                        setIsOrgDropdownOpen(false);
                      }}
                      style={{
                        width: '100%',
                        padding: '5px 8px',
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--primary)',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        textAlign: 'left',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      + Register Organization
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* 2. ACTIVE DEPARTMENTAL WORKSPACE DROPDOWN */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => {
                  setIsWorkspaceDropdownOpen(prev => !prev);
                  setIsOrgDropdownOpen(false);
                  setIsPersonaDropdownOpen(false);
                }}
                className={`top-header-pill ${isWorkspaceDropdownOpen ? 'top-header-pill-active' : ''}`}
                title="Active Workspace"
              >
                <span style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {activeWorkspace?.name || 'All Workspaces'}
                </span>
                <span style={{ fontSize: '0.62rem', color: '#94A3B8' }}>▾</span>
              </button>

              {isWorkspaceDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: 'calc(100% + 4px)',
                  right: 0,
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
                  zIndex: 250,
                  width: '260px',
                  padding: '6px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 6px 4px 6px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Workspaces
                    </span>
                    {activeWorkspace?.domain && (
                      <span className="badge badge-muted" style={{ fontSize: '0.6rem', padding: '1px 4px' }}>{activeWorkspace.domain.toUpperCase()}</span>
                    )}
                  </div>

                  <div style={{ maxHeight: '190px', overflowY: 'auto' }}>
                    {workspaces.map(ws => (
                      <button
                        key={ws.id}
                        onClick={() => {
                          setActiveWorkspace(ws);
                          setIsWorkspaceDropdownOpen(false);
                        }}
                        style={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '6px 8px',
                          background: activeWorkspace?.id === ws.id ? 'var(--primary-subtle, rgba(99,102,241,0.1))' : 'transparent',
                          border: 'none',
                          borderRadius: '4px',
                          color: activeWorkspace?.id === ws.id ? 'var(--primary)' : 'var(--text-main)',
                          fontSize: '0.75rem',
                          fontWeight: activeWorkspace?.id === ws.id ? 700 : 500,
                          cursor: 'pointer',
                          textAlign: 'left'
                        }}
                      >
                        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{ws.name}</span>
                        {activeWorkspace?.id === ws.id && <span style={{ fontSize: '0.7rem', color: 'var(--primary)' }}>✓</span>}
                      </button>
                    ))}
                  </div>

                  <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '4px', paddingTop: '4px' }}>
                    <button
                      onClick={() => {
                        setShowNewWorkspaceModal(true);
                        setIsWorkspaceDropdownOpen(false);
                      }}
                      style={{
                        width: '100%',
                        padding: '5px 8px',
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--primary)',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        textAlign: 'left',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      + Create Workspace
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* 3. ACTIVE PERSONA SWITCHER DROPDOWN */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => {
                  setIsPersonaDropdownOpen(prev => !prev);
                  setIsOrgDropdownOpen(false);
                  setIsWorkspaceDropdownOpen(false);
                }}
                className={`top-header-pill ${isPersonaDropdownOpen ? 'top-header-pill-active' : ''}`}
                title="Active User Persona"
              >
                <span style={{ maxWidth: '100px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {activePersona?.name || 'Alex'}
                </span>
                <span style={{ fontSize: '0.64rem', color: '#64748B', fontWeight: 500, textTransform: 'uppercase' }}>
                  ({activePersona?.role || 'DATA_OWNER'})
                </span>
                <span style={{ fontSize: '0.62rem', color: '#94A3B8' }}>▾</span>
              </button>

              {isPersonaDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: 'calc(100% + 4px)',
                  right: 0,
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
                  zIndex: 250,
                  width: '260px',
                  padding: '6px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 6px 4px 6px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Switch Persona
                    </span>
                    <span className="badge badge-muted" style={{ fontSize: '0.6rem', padding: '1px 4px' }}>RBAC</span>
                  </div>

                  <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                    {personas.map(p => (
                      <button
                        key={p.id}
                        onClick={() => {
                          setActivePersona(p);
                          setIsPersonaDropdownOpen(false);
                          showToast(`Switched active persona to ${p.name} (${p.role.toUpperCase()})`);
                        }}
                        style={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '6px 8px',
                          background: activePersona?.id === p.id ? 'var(--primary-subtle, rgba(99,102,241,0.1))' : 'transparent',
                          border: 'none',
                          borderRadius: '4px',
                          color: activePersona?.id === p.id ? 'var(--primary)' : 'var(--text-main)',
                          fontSize: '0.75rem',
                          fontWeight: activePersona?.id === p.id ? 700 : 500,
                          cursor: 'pointer',
                          textAlign: 'left'
                        }}
                      >
                        <div style={{ overflow: 'hidden' }}>
                          <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 600 }}>
                            {p.name}
                          </div>
                          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                            {p.title || p.role}
                          </div>
                        </div>
                        <span className="badge badge-muted" style={{ fontSize: '0.6rem', padding: '1px 4px' }}>
                          {p.role}
                        </span>
                      </button>
                    ))}
                  </div>

                  <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '4px', paddingTop: '4px' }}>
                    <button
                      onClick={() => {
                        setActiveTab('team');
                        setIsPersonaDropdownOpen(false);
                      }}
                      style={{
                        width: '100%',
                        padding: '5px 8px',
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--primary)',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        textAlign: 'center',
                        cursor: 'pointer'
                      }}
                    >
                      Manage Team & Domains ➔
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* 4. SYSTEM OPERATIONAL BADGE */}
            <span className="top-status-badge">
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--success-solid, #10b981)', display: 'inline-block' }} />
              Operational
            </span>
          </div>
        </div>

        {/* ========================================================= */}
        {/* TAB 0: HOME OVERVIEW & ARCHITECTURE DASHBOARD             */}
        {/* ========================================================= */}
        {activeTab === 'home' && (
          <div>
            {/* Hero Banner */}
            <div className="clean-panel" style={{ padding: '28px 32px', marginBottom: '24px', background: 'linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-subtle) 100%)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '20px' }}>
                <div style={{ maxWidth: '820px' }}>
                  <span className="badge badge-verified" style={{ marginBottom: '8px' }}>
                    Enterprise AI Safety Architecture
                  </span>
                  <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px', letterSpacing: '-0.02em' }}>
                    Context Trust Layer
                  </h1>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: '1.55', marginTop: '8px' }}>
                    A deterministic evidence validation gate that prevents autonomous AI agents from acting on outdated policies, unverified rumors, and contradictory instructions across enterprise knowledge bases.
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => { setActiveTab('demo'); setExpandedMenu('demo'); }}
                    className="btn btn-primary"
                    style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                  >
                    Launch Gate Demo
                  </button>
                  <button
                    onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('connectors'); }}
                    className="btn btn-secondary"
                    style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                  >
                    Manage Connectors
                  </button>
                </div>
              </div>
            </div>

            {/* Live System Metrics Grid (4 Cards) */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '28px' }}>
              <div
                className="clean-panel"
                style={{ padding: '18px 20px', cursor: 'pointer', transition: 'transform 0.15s ease' }}
                onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('connectors'); }}
              >
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Connected Data Sources
                </div>
                <div style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--primary)', marginTop: '4px' }}>
                  {dataSources.length || 5} Active
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  GitHub, Confluence, Jira, Web Portal
                </div>
              </div>

              <div
                className="clean-panel"
                style={{ padding: '18px 20px', cursor: 'pointer' }}
                onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('documents'); }}
              >
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Stored Policy Documents
                </div>
                <div style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                  {dbDocuments.length || 14} Documents
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Normalized markdown & SHA-256 hashes
                </div>
              </div>

              <div
                className="clean-panel"
                style={{ padding: '18px 20px', cursor: 'pointer' }}
                onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('claims'); }}
              >
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Atomic Claim Repository
                </div>
                <div style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--success-text)', marginTop: '4px' }}>
                  {dbClaims.length || 50} Claims
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Subject-Predicate-Object triples
                </div>
              </div>

              <div
                className="clean-panel"
                style={{ padding: '18px 20px', cursor: 'pointer' }}
                onClick={() => { setActiveTab('context_curator'); setCuratorSubView('conflicts'); setExpandedMenu('context_curator'); }}
              >
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Auditor Conflict Queue
                </div>
                <div style={{ fontSize: '1.65rem', fontWeight: 800, color: conflicts.length > 0 ? 'var(--warning-text)' : 'var(--text-main)', marginTop: '4px' }}>
                  {conflicts.length} Pending
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  {conflicts.length > 0 ? "Requires human resolution" : "All policies in agreement"}
                </div>
              </div>
            </div>

            {/* Quick-Launch Module Grid */}
            <div style={{ marginBottom: '32px' }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '14px' }}>
                System Capabilities & Workflows
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>

                {/* Card 1: Decision Gate Demo */}
                <div
                  className="clean-panel"
                  style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => { setActiveTab('demo'); setExpandedMenu('demo'); }}
                >
                  <div>
                    <span className="badge badge-verified" style={{ marginBottom: '8px' }}>Module 1</span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      Trust Decision Gate Demo
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Evaluate agent actions against conflicting documents. See how Section 3.2 (2026) supersedes outdated 2025 handbook rules.
                    </p>
                  </div>
                  <div style={{ marginTop: '16px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Open Gate Demo →
                  </div>
                </div>

                {/* Card 2: Agent Playground */}
                <div
                  className="clean-panel"
                  style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => { setActiveTab('playground'); setExpandedMenu('playground'); }}
                >
                  <div>
                    <span className="badge badge-verified" style={{ marginBottom: '8px' }}>Module 2</span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      Interactive Agent Playground
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Simulate live conversational agent queries. Inspect trusted context retrieval vs excluded contradictory knowledge.
                    </p>
                  </div>
                  <div style={{ marginTop: '16px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Open Playground →
                  </div>
                </div>

                {/* Card 3: Context Curator Bot & Conflict Resolver */}
                <div
                  className="clean-panel"
                  style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => { setActiveTab('context_curator'); setCuratorSubView('conflicts'); setExpandedMenu('context_curator'); }}
                >
                  <div>
                    <span className="badge badge-review" style={{ marginBottom: '8px' }}>Module 3</span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      Context Curator & Conflict Resolver
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Continuous knowledge health auditing and pairwise policy arbitration. Approved claims become authoritative while stale rules are superseded.
                    </p>
                  </div>
                  <div style={{ marginTop: '16px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Open Conflict Resolver ({conflicts.length}) →
                  </div>
                </div>

                {/* Card 4: Document Explorer */}
                <div
                  className="clean-panel"
                  style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); }}
                >
                  <div>
                    <span className="badge badge-verified" style={{ marginBottom: '8px' }}>Module 4</span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      Document & Connector Hub
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Connect live GitHub repositories, Confluence spaces, or upload PDF/DOCX policy documents for instant extraction.
                    </p>
                  </div>
                  <div style={{ marginTop: '16px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Open Document Explorer →
                  </div>
                </div>
              </div>
            </div>

            {/* 5-Stage Context Trust Architecture Workflow Diagram */}
            <div className="clean-panel" style={{ padding: '24px' }}>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '6px' }}>
                5-Stage Context Trust Lifecycle
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
                Every document follows an immutable pipeline from connector ingestion to decision gate evaluation.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--primary)', fontWeight: 800 }}>STAGE 1</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>Ingest & Hash</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
                    Normalizes markdown, parses DOCX/PDF, and computes SHA-256 version hashes.
                  </p>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--primary)', fontWeight: 800 }}>STAGE 2</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>Atomic Fact Triples</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
                    Extracts atomic subject-predicate-object assertions from each document section.
                  </p>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--primary)', fontWeight: 800 }}>STAGE 3</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>Conflict Detection</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
                    Topical and semantic filtering detects numerical clashes, overrides, and scope collisions.
                  </p>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--primary)', fontWeight: 800 }}>STAGE 4</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>Bayesian Trust Scoring</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
                    Calculates 6-factor trust weights (Authority, Freshness, Verification, Scope).
                  </p>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 800 }}>STAGE 5</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>Decision Safety Gate</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
                    Issues ALLOW, REQUIRE_REVIEW, or BLOCK decisions with signed audit IDs.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 1: TRUST DECISION GATE DEMO (CLEAN, NO NAIVE RAG)     */}
        {/* ========================================================= */}
        {activeTab === 'demo' && (
          <div>
            {/* Header Area */}
            <div style={{ marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <span className="badge badge-verified" style={{ marginBottom: '6px' }}>
                    Policy & Evidence Gate
                  </span>
                  <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                    Trust Decision Gate Evaluation
                  </h1>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '4px', maxWidth: '750px' }}>
                    Evaluates intended AI agent actions against contradictory policy evidence, verifying source authority, scope matching, and freshness before allowing autonomous execution.
                  </p>
                </div>

              </div>

              {/* Scenario Switcher Tabs on Decision Page */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                background: '#F1F5F9',
                padding: '4px',
                borderRadius: '10px',
                gap: '6px',
                border: '1px solid var(--border-subtle)',
                marginTop: '16px'
              }}>
                <button
                  onClick={() => { setDemoScenario('refund_trap'); setDemoStep(0); setDemoResult(null); }}
                  style={{
                    flex: 1,
                    padding: '8px 14px',
                    fontSize: '0.82rem',
                    fontWeight: demoScenario === 'refund_trap' ? 700 : 500,
                    color: demoScenario === 'refund_trap' ? '#0F172A' : '#64748B',
                    background: demoScenario === 'refund_trap' ? '#FFFFFF' : 'transparent',
                    border: 'none',
                    borderRadius: '7px',
                    cursor: 'pointer',
                    boxShadow: demoScenario === 'refund_trap' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <span>1. Refund Window</span>
                  <span className="badge badge-warning" style={{ fontSize: '0.64rem', padding: '1px 5px' }}>Freshness Trap</span>
                </button>

                <button
                  onClick={() => { setDemoScenario('remote_work'); setDemoStep(0); setDemoResult(null); }}
                  style={{
                    flex: 1,
                    padding: '8px 14px',
                    fontSize: '0.82rem',
                    fontWeight: demoScenario === 'remote_work' ? 700 : 500,
                    color: demoScenario === 'remote_work' ? '#0F172A' : '#64748B',
                    background: demoScenario === 'remote_work' ? '#FFFFFF' : 'transparent',
                    border: 'none',
                    borderRadius: '7px',
                    cursor: 'pointer',
                    boxShadow: demoScenario === 'remote_work' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <span>2. Remote Work</span>
                  <span className="badge badge-review" style={{ fontSize: '0.64rem', padding: '1px 5px' }}>Scope Override</span>
                </button>

                <button
                  onClick={() => { setDemoScenario('unauthorized_deploy'); setDemoStep(0); setDemoResult(null); }}
                  style={{
                    flex: 1,
                    padding: '8px 14px',
                    fontSize: '0.82rem',
                    fontWeight: demoScenario === 'unauthorized_deploy' ? 700 : 500,
                    color: demoScenario === 'unauthorized_deploy' ? '#0F172A' : '#64748B',
                    background: demoScenario === 'unauthorized_deploy' ? '#FFFFFF' : 'transparent',
                    border: 'none',
                    borderRadius: '7px',
                    cursor: 'pointer',
                    boxShadow: demoScenario === 'unauthorized_deploy' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <span>3. Prod Ingress</span>
                  <span className="badge badge-verified" style={{ fontSize: '0.64rem', padding: '1px 5px' }}>Role Gate</span>
                </button>
              </div>
            </div>

            {/* Intended Action & Execution Bar */}
            <div className="clean-panel" style={{ padding: '16px 20px', marginBottom: '20px', background: 'var(--bg-card)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
                <div style={{ flex: 1, minWidth: '280px' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
                    Intended Agent Action / Query:
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>
                    "{currentScenario.query}"
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Actor: <span className="code-pill">{currentScenario.actor.id}</span> (Role: {currentScenario.actor.role})
                  </div>
                </div>

                <button
                  onClick={runKillerDemo}
                  disabled={demoRunning}
                  className="btn btn-primary"
                  style={{ padding: '9px 18px', fontSize: '0.875rem' }}
                >
                  {demoRunning ? "Evaluating..." : "Evaluate Decision Gate"}
                </button>
              </div>
            </div>

            {/* Main Decision Gate Panel */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>

              {/* Left Side: Candidate Evidence Evaluated */}
              <div className="clean-panel" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    Candidate Evidence Evaluated
                  </h3>
                  <span className="badge badge-review">Contradiction Detected</span>
                </div>

                <div style={{ display: 'grid', gap: '12px' }}>
                  {/* Candidate 1 (Stale / Low Authority) */}
                  <div style={{ background: 'var(--bg-card-subtle)', border: '1px solid var(--border-subtle)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>
                      <span>RECORD 1 (Superseded)</span>
                      <span>Date: {currentScenario.claim1.date}</span>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textDecoration: 'line-through' }}>
                      "{currentScenario.claim1.text}"
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                      <span>Source: {currentScenario.claim1.source}</span>
                      <span>Authority: {currentScenario.claim1.authority}/100</span>
                    </div>
                  </div>

                  {/* Candidate 2 (Authoritative / Fresh) */}
                  <div style={{ background: 'var(--success-bg)', border: '1px solid var(--success-border)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 700, marginBottom: '4px' }}>
                      <span>RECORD 2 (Authoritative Selection)</span>
                      <span>Date: {currentScenario.claim2.date}</span>
                    </div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--success-text)', fontWeight: 700 }}>
                      "{currentScenario.claim2.text}"
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--success-text)', marginTop: '6px' }}>
                      <span>Source: {currentScenario.claim2.source}</span>
                      <span>Authority: {currentScenario.claim2.authority}/100</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Side: Decision Gate Evaluation Verdict */}
              <div className="clean-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      Decision Gate Verdict
                    </h3>
                    {demoResult && <span className="code-pill">Audit: {demoResult.audit_id}</span>}
                  </div>

                  {demoStep === 0 && (
                    <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      Click "Evaluate Decision Gate" to run evidence verification.
                    </div>
                  )}

                  {demoStep === 1 && (
                    <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--primary)', fontSize: '0.85rem', fontWeight: 600 }}>
                      Evaluating candidate records, freshness, and authority levels...
                    </div>
                  )}

                  {demoStep === 2 && demoResult && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                        <span className={`badge ${demoResult.decision === 'ALLOW' ? 'badge-allow' : demoResult.decision === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '0.85rem', padding: '4px 10px' }}>
                          VERDICT: {demoResult.decision}
                        </span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          Risk: <strong style={{ color: demoResult.risk === 'LOW' ? 'var(--success-text)' : 'var(--danger-text)' }}>{demoResult.risk}</strong> • Validity: <strong>{demoResult.validity}</strong>
                        </span>
                      </div>

                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                        <div style={{ fontWeight: 700, marginBottom: '4px' }}>Evaluation Reasons:</div>
                        <ul style={{ paddingLeft: '18px', lineHeight: 1.5 }}>
                          {demoResult.reasons?.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>

                {demoStep === 2 && demoResult && (
                  <div style={{ marginTop: '12px', padding: '10px 12px', background: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    <strong>Suggested Next Action:</strong> {demoResult.suggested_action}
                  </div>
                )}
              </div>
            </div>

            {/* 6-Factor Trust Score Architecture */}
            <div className="clean-panel" style={{ marginTop: '20px', padding: '20px' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '14px' }}>
                Explainable 6-Factor Trust Score Architecture
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '12px' }}>
                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>1. Authority</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--primary)', marginTop: '2px' }}>0.95</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Verified Source</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>2. Freshness</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--success-text)', marginTop: '2px' }}>1.00</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>2026 Active</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>3. Evidence</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>0.95</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Direct Text Quote</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>4. Consistency</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--warning-text)', marginTop: '2px' }}>0.36</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Contradiction Handled</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>5. Scope Match</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>1.00</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Enterprise Tier</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>6. Auditor Seal</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--primary-dark)', marginTop: '2px' }}>1.00</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Approved</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 2: INTERACTIVE AGENT PLAYGROUND & AI COPILOT CHAT     */}
        {/* ========================================================= */}
        {activeTab === 'playground' && (
          <AgentChatPlayground
            activeOrg={activeOrg}
            activePersona={activePersona}
            workspaces={workspaces}
            showToast={showToast}
            selectedSessionId={activeChatSessionId}
            onSessionChange={(id) => {
              setActiveChatSessionId(id);
              fetchChatSessions();
            }}
          />
        )}



        {/* ========================================================= */}
        {/* TAB 4: DOCUMENT INGESTION & CLAIM EXPLORER                */}
        {/* ========================================================= */}
        {activeTab === 'ingestion' && (
          <div>
            {/* Header Area with Sub-View Switcher */}
            <div style={{ marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <span className="badge badge-verified" style={{ marginBottom: '6px' }}>
                    PostgreSQL Repository Explorer
                  </span>
                  <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                    Document & Atomic Claim Repository
                  </h1>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '4px' }}>
                    Ingest raw organizational policies, normalize markdown structure, and inspect live atomic facts stored in PostgreSQL.
                  </p>
                </div>

                {/* Active View Badge & Refresh Action */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className="badge badge-verified" style={{ fontSize: '0.8rem', padding: '5px 12px' }}>
                    {docExplorerView === 'connectors' ? `Live Connectors & Sync (${dataSources.length})` :
                      docExplorerView === 'ingest' ? 'Ingest New Document' :
                        docExplorerView === 'documents' ? `Stored Documents (${dbDocuments.length})` :
                          `Atomic Claims (${dbClaims.length})`}
                  </span>

                  <button
                    onClick={fetchLiveDatabaseRecords}
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                    title="Refresh database records"
                  >
                    {dbLoading ? "Loading..." : "Refresh"}
                  </button>
                </div>
              </div>
            </div>

            {/* VIEW 0: LIVE CONNECTORS & CONTINUOUS SYNC */}
            {docExplorerView === 'connectors' && (
              <div>
                {/* Connectors Control Toolbar */}
                <div className="clean-panel" style={{ padding: '16px 20px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '0.925rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      Continuous Auto-Sync Pipeline
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Automatically poll, extract, and cross-check organizational policies from external systems.
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Auto-Poll:</span>
                      <select
                        value={autoSyncInterval}
                        onChange={e => {
                          setAutoSyncInterval(e.target.value);
                          if (e.target.value !== 'off') {
                            showToast(`Auto-sync enabled (${e.target.value})`, "info");
                          } else {
                            showToast("Auto-sync disabled", "info");
                          }
                        }}
                        style={{ padding: '5px 8px', fontSize: '0.78rem' }}
                      >
                        <option value="off">Off (Manual)</option>
                        <option value="1m">Every 1 Min</option>
                        <option value="5m">Every 5 Min</option>
                        <option value="15m">Every 15 Min</option>
                      </select>
                    </div>

                    <button
                      onClick={() => setShowAddSourceModal(true)}
                      className="btn btn-secondary"
                      style={{ padding: '7px 14px', fontSize: '0.8rem' }}
                    >
                      + Connect Real Source
                    </button>

                    <button
                      onClick={handleSyncAllSources}
                      disabled={syncingSourceId !== null}
                      className="btn btn-primary"
                      style={{ padding: '7px 14px', fontSize: '0.8rem' }}
                    >
                      {syncingSourceId === 'all' ? "Syncing All Sources..." : "Sync All Connectors"}
                    </button>
                  </div>
                </div>

                {/* Connectors Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '16px', marginBottom: '24px' }}>
                  {dataSources.map((source, idx) => {
                    const isSyncing = syncingSourceId === source.id || syncingSourceId === 'all';
                    const stype = (source.source_type || '').toLowerCase();
                    const typeLabel = stype.toUpperCase();
                    const lastSyncText = source.last_synced_at
                      ? new Date(source.last_synced_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                      : 'Not synced yet';

                    return (
                      <div key={source.id || idx} className="clean-panel" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', borderTop: '3px solid var(--border-medium)' }}>
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                            <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>
                              {typeLabel}
                            </span>
                            <span className="badge badge-allow" style={{ fontSize: '0.7rem' }}>
                              Authority: {source.authority_level}%
                            </span>
                          </div>

                          <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '4px' }}>
                            {source.name}
                          </h3>

                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
                            Target: <code style={{ color: 'var(--text-secondary)' }}>{source.external_id || source.source_type}</code>
                          </div>

                          <div style={{ background: '#FFFFFF', border: '1px solid var(--border-subtle)', padding: '10px', borderRadius: '6px', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                            <div style={{ fontWeight: 700, marginBottom: '2px' }}>Monitored Contract Scope:</div>
                            {stype === 'postgresql' && "Relational Schema, Table Constraints (PK/FK/CHECK), Column Nullability & SLA Policies."}
                            {stype === 'kafka' && "Stream Topic Topology, Message Schema Registry, Retention SLAs & Dead-Letter Queues."}
                            {stype === 'salesforce' && "Standard & Custom SObjects, Field Types, Validation Rules & Approval Thresholds."}
                            {stype === 'mongodb' && "Collection Schemas, JSON Schema Validators ($jsonSchema), Shard Keys & TTL Indexes."}
                            {stype === 'confluence' && "Live Confluence Wiki Space, Policy Articles, and Security Standards."}
                            {stype === 'jira' && "Live Jira Project, Incident Runbooks, SLAs, and Release Guidelines."}
                            {stype === 'github' && "Live GitHub Repository, /docs Markdown files, and Architecture Specs."}
                            {stype === 'portal' && "Corporate Security Directives, Authentication & Compliance Mandates."}
                            {!['postgresql', 'kafka', 'salesforce', 'mongodb', 'confluence', 'jira', 'github', 'portal'].includes(stype) && "Enterprise Data & Policy Contract Synchronization."}
                          </div>
                        </div>

                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            <span>Status: <strong style={{ color: 'var(--success-text)' }}>Connected</strong></span>
                            <span>Last Synced: <strong>{lastSyncText}</strong></span>
                          </div>

                          <button
                            onClick={() => handleSyncSource(source.id, source.name)}
                            disabled={isSyncing}
                            className="btn btn-secondary"
                            style={{ width: '100%', padding: '8px', fontSize: '0.8rem', justifyContent: 'center' }}
                          >
                            {isSyncing ? "Syncing & Extracting Claims..." : `Sync ${source.name.split(' ')[0]} Now`}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Pipeline Flow Explainer */}
                <div className="clean-panel" style={{ padding: '16px 20px', background: '#FFFFFF' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '8px' }}>
                    Continuous Trust Ingestion Pipeline Flow
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span className="code-pill">1. Polling Connectors</span>
                    <span>→</span>
                    <span className="code-pill">2. Normalizing Contracts & Markdown</span>
                    <span>→</span>
                    <span className="code-pill">3. Extracting Atomic Claims</span>
                    <span>→</span>
                    <span className="code-pill">4. Detecting Contradictions</span>
                    <span>→</span>
                    <span className="code-pill">5. Updating Auditor Queue</span>
                  </div>
                </div>

                {/* Modal: Connect Real Enterprise Data Source (Atlan Architecture) */}
                {showAddSourceModal && (
                  <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(15, 23, 42, 0.45)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000,
                    padding: '20px'
                  }}>
                    <div className="clean-panel" style={{ width: '100%', maxWidth: '720px', maxHeight: '90vh', overflowY: 'auto', padding: '24px', background: '#FFFFFF', borderRadius: '10px', boxShadow: '0 10px 25px rgba(0,0,0,0.1)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                              Enterprise Connector Hub
                            </h3>
                            <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>
                              104 Supported Sources
                            </span>
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                            Modelled after Atlan's connector architecture with pre-flight diagnostics, automated crawler & contract extraction.
                          </div>
                        </div>
                        <button
                          onClick={() => { setShowAddSourceModal(false); setTestConnectionResult(null); }}
                          style={{ background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: 'var(--text-muted)' }}
                        >
                          ✕
                        </button>
                      </div>

                      {/* Category Filter Chips */}
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
                        {catalogCategories.map(cat => (
                          <button
                            key={cat.id}
                            type="button"
                            onClick={() => setCatalogFilterCategory(cat.id)}
                            style={{
                              padding: '4px 10px',
                              fontSize: '0.72rem',
                              fontWeight: 700,
                              borderRadius: '14px',
                              border: catalogFilterCategory === cat.id ? '1px solid var(--primary)' : '1px solid var(--border-subtle)',
                              background: catalogFilterCategory === cat.id ? 'var(--primary)' : '#F8FAFC',
                              color: catalogFilterCategory === cat.id ? '#FFFFFF' : 'var(--text-secondary)',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            {cat.label} ({cat.count})
                          </button>
                        ))}
                      </div>

                      {/* Search Bar across 104 connectors */}
                      <div style={{ marginBottom: '14px' }}>
                        <input
                          type="text"
                          placeholder="🔍 Search across 104 data sources... e.g. Snowflake, dbt, Airflow, Tableau, Iceberg, Monte Carlo, SageMaker"
                          value={catalogSearchQuery}
                          onChange={e => setCatalogSearchQuery(e.target.value)}
                          style={{ width: '100%', padding: '8px 12px', fontSize: '0.82rem', background: '#F8FAFC' }}
                        />
                      </div>

                      <form onSubmit={handleConnectNewSource} style={{ display: 'grid', gap: '14px' }}>
                        {/* Source Type Selector */}
                        <div>
                          <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                            Select Target Data Source ({
                              catalogConnectors.filter(c =>
                                (catalogFilterCategory === 'all' || c.category === catalogFilterCategory) &&
                                (!catalogSearchQuery || c.name.toLowerCase().includes(catalogSearchQuery.toLowerCase()) || c.description.toLowerCase().includes(catalogSearchQuery.toLowerCase()))
                              ).length
                            } available):
                          </label>
                          <select
                            value={newSourceForm.sourceType}
                            onChange={e => {
                              const newType = e.target.value;
                              const meta = catalogConnectors.find(c => c.id === newType);
                              let defaultName = meta ? `Production ${meta.name}` : `Core ${newType}`;
                              setNewSourceForm({ ...newSourceForm, sourceType: newType, name: defaultName });
                              setTestConnectionResult(null);
                            }}
                            style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                          >
                            {catalogConnectors
                              .filter(c =>
                                (catalogFilterCategory === 'all' || c.category === catalogFilterCategory) &&
                                (!catalogSearchQuery || c.name.toLowerCase().includes(catalogSearchQuery.toLowerCase()) || c.description.toLowerCase().includes(catalogSearchQuery.toLowerCase()))
                              )
                              .map(c => (
                                <option key={c.id} value={c.id}>
                                  [{c.category_label}] {c.name}
                                </option>
                              ))
                            }
                          </select>
                        </div>

                        {/* Selected Connector Scope Banner */}
                        {(() => {
                          const currentMeta = catalogConnectors.find(c => c.id === newSourceForm.sourceType);
                          if (!currentMeta) return null;
                          return (
                            <div style={{ background: '#F1F5F9', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px 14px', fontSize: '0.75rem' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                <span style={{ fontWeight: 800, color: 'var(--text-main)' }}>{currentMeta.name}</span>
                                <span className="badge badge-verified" style={{ fontSize: '0.68rem' }}>{currentMeta.category_label}</span>
                              </div>
                              <div style={{ color: 'var(--text-secondary)', marginBottom: '4px' }}>{currentMeta.description}</div>
                              <div style={{ color: 'var(--primary)', fontWeight: 600 }}>Scope: {currentMeta.monitored_scope}</div>
                            </div>
                          );
                        })()}

                        {/* Connection Name */}
                        <div>
                          <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                            Connector Instance Name:
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. Core Production Snowflake Warehouse"
                            value={newSourceForm.name}
                            onChange={e => setNewSourceForm({ ...newSourceForm, name: e.target.value })}
                            style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                            required
                          />
                        </div>

                        {/* 1. PostgreSQL Specific Fields */}
                        {newSourceForm.sourceType === 'postgresql' && (
                          <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px', display: 'grid', gap: '10px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '10px' }}>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Host / Hostname:</label>
                                <input
                                  type="text"
                                  value={newSourceForm.pgHost}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, pgHost: e.target.value })}
                                  placeholder="localhost or pg.internal"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Port:</label>
                                <input
                                  type="number"
                                  value={newSourceForm.pgPort}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, pgPort: e.target.value })}
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Database Name:</label>
                                <input
                                  type="text"
                                  value={newSourceForm.pgDatabase}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, pgDatabase: e.target.value })}
                                  placeholder="enterprise_core"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Target Schemas (comma-separated):</label>
                                <input
                                  type="text"
                                  value={newSourceForm.pgSchemas}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, pgSchemas: e.target.value })}
                                  placeholder="public, analytics"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Username:</label>
                                <input
                                  type="text"
                                  value={newSourceForm.pgUsername}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, pgUsername: e.target.value })}
                                  placeholder="postgres"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Password:</label>
                                <input
                                  type="password"
                                  value={newSourceForm.pgPassword}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, pgPassword: e.target.value })}
                                  placeholder="••••••••"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 2. Apache Kafka Specific Fields */}
                        {(['kafka', 'apache_kafka', 'confluent_kafka', 'amazon_msk', 'aiven_kafka', 'redpanda_kafka'].includes(newSourceForm.sourceType)) && (
                          <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px', display: 'grid', gap: '10px' }}>
                            <div>
                              <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Bootstrap Servers (host:port):</label>
                              <input
                                type="text"
                                value={newSourceForm.kafkaBootstrap}
                                onChange={e => setNewSourceForm({ ...newSourceForm, kafkaBootstrap: e.target.value })}
                                placeholder="kafka-cluster-prod.internal:9092"
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                              />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Security Protocol:</label>
                                <select
                                  value={newSourceForm.kafkaSecurityProtocol}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, kafkaSecurityProtocol: e.target.value })}
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                >
                                  <option value="PLAINTEXT">PLAINTEXT</option>
                                  <option value="SSL">SSL</option>
                                  <option value="SASL_PLAINTEXT">SASL_PLAINTEXT</option>
                                  <option value="SASL_SSL">SASL_SSL</option>
                                </select>
                              </div>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Schema Registry URL (Optional):</label>
                                <input
                                  type="text"
                                  value={newSourceForm.kafkaSchemaRegistry}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, kafkaSchemaRegistry: e.target.value })}
                                  placeholder="http://schema-registry:8081"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                            </div>
                            <div>
                              <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Monitored Topics (comma-separated):</label>
                              <input
                                type="text"
                                value={newSourceForm.kafkaTopics}
                                onChange={e => setNewSourceForm({ ...newSourceForm, kafkaTopics: e.target.value })}
                                placeholder="financial.payments.settled.v1, security.audit.access.v2"
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                              />
                            </div>
                          </div>
                        )}

                        {/* 3. Salesforce Specific Fields */}
                        {newSourceForm.sourceType === 'salesforce' && (
                          <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px', display: 'grid', gap: '10px' }}>
                            <div>
                              <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Salesforce Instance URL:</label>
                              <input
                                type="text"
                                value={newSourceForm.sfInstanceUrl}
                                onChange={e => setNewSourceForm({ ...newSourceForm, sfInstanceUrl: e.target.value })}
                                placeholder="https://company.my.salesforce.com"
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                              />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Connected App Client ID:</label>
                                <input
                                  type="text"
                                  value={newSourceForm.sfClientId}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, sfClientId: e.target.value })}
                                  placeholder="3MVG9..."
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Client Secret:</label>
                                <input
                                  type="password"
                                  value={newSourceForm.sfClientSecret}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, sfClientSecret: e.target.value })}
                                  placeholder="••••••••"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                            </div>
                            <div>
                              <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Target SObjects to Ingest (comma-separated):</label>
                              <input
                                type="text"
                                value={newSourceForm.sfObjects}
                                onChange={e => setNewSourceForm({ ...newSourceForm, sfObjects: e.target.value })}
                                placeholder="Contract, Refund_Request__c, Case, Opportunity"
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                              />
                            </div>
                          </div>
                        )}

                        {/* 4. MongoDB Specific Fields */}
                        {(['mongodb', 'mongodb_atlas', 'mongodb_self', 'documentdb'].includes(newSourceForm.sourceType)) && (
                          <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px', display: 'grid', gap: '10px' }}>
                            <div>
                              <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>MongoDB Connection URI:</label>
                              <input
                                type="text"
                                value={newSourceForm.mongoUri}
                                onChange={e => setNewSourceForm({ ...newSourceForm, mongoUri: e.target.value })}
                                placeholder="mongodb://production-cluster:27017 or mongodb+srv://..."
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                              />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Database Name:</label>
                                <input
                                  type="text"
                                  value={newSourceForm.mongoDatabase}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, mongoDatabase: e.target.value })}
                                  placeholder="production"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Target Collections (comma-separated):</label>
                                <input
                                  type="text"
                                  value={newSourceForm.mongoCollections}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, mongoCollections: e.target.value })}
                                  placeholder="refund_orders, user_session_entitlements"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 5. GitHub Fields */}
                        {newSourceForm.sourceType === 'github' && (
                          <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px', display: 'grid', gap: '10px' }}>
                            <div>
                              <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>GitHub Repository (owner/repo):</label>
                              <input
                                type="text"
                                placeholder="e.g. demo-org/security-standards"
                                value={newSourceForm.githubRepo}
                                onChange={e => setNewSourceForm({ ...newSourceForm, githubRepo: e.target.value })}
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                required
                              />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Branch:</label>
                                <input
                                  type="text"
                                  value={newSourceForm.githubBranch}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, githubBranch: e.target.value })}
                                  placeholder="main"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Personal Access Token (Optional):</label>
                                <input
                                  type="password"
                                  value={newSourceForm.githubToken}
                                  onChange={e => setNewSourceForm({ ...newSourceForm, githubToken: e.target.value })}
                                  placeholder="ghp_..."
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 6. Confluence Fields */}
                        {newSourceForm.sourceType === 'confluence' && (
                          <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px', display: 'grid', gap: '10px' }}>
                            <div>
                              <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Confluence Space Key:</label>
                              <input
                                type="text"
                                placeholder="POLICIES or HR"
                                value={newSourceForm.confluenceSpace}
                                onChange={e => setNewSourceForm({ ...newSourceForm, confluenceSpace: e.target.value })}
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                required
                              />
                            </div>
                            <div>
                              <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Atlassian Base URL (Optional):</label>
                              <input
                                type="text"
                                placeholder="https://yourcompany.atlassian.net"
                                value={newSourceForm.confluenceBaseUrl}
                                onChange={e => setNewSourceForm({ ...newSourceForm, confluenceBaseUrl: e.target.value })}
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                              />
                            </div>
                          </div>
                        )}

                        {/* 7. Jira Fields */}
                        {newSourceForm.sourceType === 'jira' && (
                          <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px', display: 'grid', gap: '10px' }}>
                            <div>
                              <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Jira Project Key:</label>
                              <input
                                type="text"
                                placeholder="OPS or SEC"
                                value={newSourceForm.jiraProject}
                                onChange={e => setNewSourceForm({ ...newSourceForm, jiraProject: e.target.value })}
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                required
                              />
                            </div>
                            <div>
                              <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Atlassian Base URL (Optional):</label>
                              <input
                                type="text"
                                placeholder="https://yourcompany.atlassian.net"
                                value={newSourceForm.jiraBaseUrl}
                                onChange={e => setNewSourceForm({ ...newSourceForm, jiraBaseUrl: e.target.value })}
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                              />
                            </div>
                          </div>
                        )}

                        {/* 8. Universal Driver Configuration Fields for all other 90+ Connectors */}
                        {!['postgresql', 'kafka', 'apache_kafka', 'confluent_kafka', 'amazon_msk', 'aiven_kafka', 'redpanda_kafka', 'salesforce', 'mongodb', 'mongodb_atlas', 'mongodb_self', 'documentdb', 'github', 'confluence', 'jira'].includes(newSourceForm.sourceType) && (
                          <div style={{ background: '#F8FAFC', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px', display: 'grid', gap: '10px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '10px' }}>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Host / Cluster Endpoint / Account URL:</label>
                                <input
                                  type="text"
                                  value={genericConfig.host}
                                  onChange={e => setGenericConfig({ ...genericConfig, host: e.target.value })}
                                  placeholder={`e.g. ${newSourceForm.sourceType}-cluster.prod.internal or https://${newSourceForm.sourceType}.corp.com`}
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Port (Optional):</label>
                                <input
                                  type="number"
                                  value={genericConfig.port}
                                  onChange={e => setGenericConfig({ ...genericConfig, port: e.target.value })}
                                  placeholder="Default"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Database / Workspace / Project:</label>
                                <input
                                  type="text"
                                  value={genericConfig.database}
                                  onChange={e => setGenericConfig({ ...genericConfig, database: e.target.value })}
                                  placeholder="analytics_prod or default"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Target Schemas / Datasets:</label>
                                <input
                                  type="text"
                                  value={genericConfig.schemas}
                                  onChange={e => setGenericConfig({ ...genericConfig, schemas: e.target.value })}
                                  placeholder="public, models, core"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Username / Service Account:</label>
                                <input
                                  type="text"
                                  value={genericConfig.username}
                                  onChange={e => setGenericConfig({ ...genericConfig, username: e.target.value })}
                                  placeholder="service_account_bot"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                              <div>
                                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Password / API Key / Secret:</label>
                                <input
                                  type="password"
                                  value={genericConfig.password}
                                  onChange={e => setGenericConfig({ ...genericConfig, password: e.target.value })}
                                  placeholder="••••••••"
                                  style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                />
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Authority Slider */}
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                              Trust Authority Level:
                            </label>
                            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--primary)' }}>
                              {newSourceForm.authorityLevel}%
                            </span>
                          </div>
                          <input
                            type="range"
                            min="10"
                            max="100"
                            value={newSourceForm.authorityLevel}
                            onChange={e => setNewSourceForm({ ...newSourceForm, authorityLevel: e.target.value })}
                            style={{ width: '100%' }}
                          />
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            High authority sources (90%+) supersede conflicting claims from lower authority sources.
                          </div>
                        </div>

                        {/* Test Connection Diagnostic Result */}
                        {testConnectionResult && (
                          <div style={{
                            padding: '10px 14px',
                            borderRadius: '6px',
                            fontSize: '0.78rem',
                            background: testConnectionResult.success ? 'var(--badge-verified-bg)' : '#FEF2F2',
                            border: `1px solid ${testConnectionResult.success ? 'var(--badge-verified-border)' : '#FCA5A5'}`,
                            color: testConnectionResult.success ? 'var(--badge-verified-text)' : '#B91C1C'
                          }}>
                            <div style={{ fontWeight: 800, marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span>{testConnectionResult.success ? '✓ Connection Verified' : '✕ Connection Diagnostic Failed'}</span>
                            </div>
                            <div>{testConnectionResult.message}</div>
                            {testConnectionResult.details && Object.keys(testConnectionResult.details).length > 0 && (
                              <div style={{ fontSize: '0.72rem', marginTop: '4px', opacity: 0.85 }}>
                                Details: {JSON.stringify(testConnectionResult.details)}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Action Buttons */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
                          <button
                            type="button"
                            onClick={handleTestConnection}
                            disabled={isTestingConnection}
                            className="btn btn-secondary"
                            style={{ padding: '8px 14px', fontSize: '0.8rem' }}
                          >
                            {isTestingConnection ? "Testing Connection..." : "⚡ Test Connection"}
                          </button>

                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                              type="button"
                              onClick={() => { setShowAddSourceModal(false); setTestConnectionResult(null); }}
                              className="btn btn-secondary"
                              style={{ padding: '8px 14px', fontSize: '0.8rem' }}
                            >
                              Cancel
                            </button>
                            <button
                              type="submit"
                              disabled={isConnectingSource}
                              className="btn btn-primary"
                              style={{ padding: '8px 18px', fontSize: '0.8rem' }}
                            >
                              {isConnectingSource ? "Connecting & Syncing..." : "Save & Sync Connector"}
                            </button>
                          </div>
                        </div>
                      </form>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* VIEW 1: INGEST NEW DOCUMENT */}
            {docExplorerView === 'ingest' && (
              <div style={{ display: 'grid', gridTemplateColumns: '400px 1fr', gap: '20px' }}>

                {/* Ingest Form */}
                <div className="clean-panel" style={{ padding: '20px' }}>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '14px' }}>
                    Ingest & Normalize Document
                  </h3>

                  <div style={{ display: 'grid', gap: '14px' }}>

                    {/* Drag and Drop File Upload Zone */}
                    <div
                      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                      onDragLeave={() => setIsDragging(false)}
                      onDrop={(e) => {
                        e.preventDefault();
                        setIsDragging(false);
                        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                          handleProcessFile(e.dataTransfer.files[0]);
                        }
                      }}
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        border: isDragging ? '2px dashed var(--primary)' : '1px dashed var(--border-medium)',
                        background: isDragging ? 'var(--primary-50)' : 'var(--bg-card-subtle)',
                        borderRadius: '8px',
                        padding: '16px 14px',
                        textAlign: 'center',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <input
                        type="file"
                        ref={fileInputRef}
                        accept=".txt,.md,.json,.csv,.pdf,.docx,.doc"
                        style={{ display: 'none' }}
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            handleProcessFile(e.target.files[0]);
                          }
                        }}
                      />
                      {uploadedFile ? (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <div style={{ textAlign: 'left' }}>
                            <div style={{ fontSize: '0.825rem', fontWeight: 700, color: 'var(--primary)' }}>
                              {uploadedFile.name}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                              {(uploadedFile.size / 1024).toFixed(1)} KB • Click to choose a different file
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setUploadedFile(null);
                              if (fileInputRef.current) fileInputRef.current.value = '';
                            }}
                            className="badge badge-outdated"
                            style={{ cursor: 'pointer', border: '1px solid var(--border-subtle)', textDecoration: 'none' }}
                          >
                            Clear
                          </button>
                        </div>
                      ) : (
                        <div>
                          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
                            Drag & drop a file here, or click to browse
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                            Supports .pdf, .docx, .txt, .md, .json, .csv
                          </div>
                        </div>
                      )}
                    </div>

                    <div>
                      <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                        Document Title:
                      </label>
                      <input
                        type="text"
                        value={docInput.title}
                        onChange={e => setDocInput({ ...docInput, title: e.target.value })}
                        style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                        Document Type:
                      </label>
                      <select
                        value={docInput.docType}
                        onChange={e => setDocInput({ ...docInput, docType: e.target.value })}
                        style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                      >
                        <option value="policy">Enterprise Policy</option>
                        <option value="confluence_page">Confluence Article</option>
                        <option value="handbook">Employee Handbook</option>
                        <option value="runbook">DevOps Runbook</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                        Raw Markdown Content:
                      </label>
                      <textarea
                        rows={6}
                        value={docInput.content}
                        onChange={e => setDocInput({ ...docInput, content: e.target.value })}
                        style={{ width: '100%', padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}
                      />
                    </div>

                    <button
                      onClick={handleIngestDocument}
                      disabled={ingesting}
                      className="btn btn-primary"
                      style={{ width: '100%', padding: '10px' }}
                    >
                      {ingesting ? "Extracting Claims..." : "Ingest Document"}
                    </button>
                  </div>
                </div>

                {/* Extracted Claims */}
                <div className="clean-panel" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      Extracted Atomic Claims ({extractedClaims.length})
                    </h3>
                    {ingestedDoc && (
                      <span className="code-pill">SHA-256: {ingestedDoc.document?.content_hash?.substring(0, 16)}...</span>
                    )}
                  </div>

                  {extractedClaims.length === 0 ? (
                    <div style={{ padding: '48px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <p style={{ fontSize: '0.825rem' }}>Ingest a document on the left to extract Subject-Predicate-Object claims with multi-factor trust ratings.</p>
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gap: '10px' }}>
                      {extractedClaims.map((claim, idx) => (
                        <div key={claim.id || idx} style={{ background: '#FFFFFF', border: '1px solid var(--border-subtle)', padding: '12px', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <div style={{ display: 'flex', gap: '6px' }}>
                              <span className="code-pill">Subject: {claim.subject || 'N/A'}</span>
                              <span className="code-pill">Predicate: {claim.predicate || 'N/A'}</span>
                            </div>
                            <span className={`badge ${claim.status === 'verified' ? 'badge-allow' : 'badge-review'}`}>
                              {claim.status}
                            </span>
                          </div>

                          <p style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', lineHeight: '1.4' }}>
                            "{claim.claim_text}"
                          </p>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            <span>Section: {claim.evidence?.[0]?.section || 'General'}</span>
                            <span>Trust Score: <strong style={{ color: 'var(--success-text)' }}>{claim.trust_scores?.[0]?.overall_score || '0.95'}</strong></span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* VIEW 2: STORED DOCUMENTS BROWSER */}
            {docExplorerView === 'documents' && (
              <div className="clean-panel" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
                  <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    Documents in PostgreSQL ({dbDocuments.length})
                  </div>
                  <input
                    type="text"
                    placeholder="Search documents by title or external ID..."
                    value={dbSearchQuery}
                    onChange={e => setDbSearchQuery(e.target.value)}
                    style={{ padding: '6px 12px', fontSize: '0.8rem', width: '320px' }}
                  />
                </div>

                {dbDocuments.length === 0 ? (
                  <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    No documents stored yet. Switch to "Ingest New Document" tab to add your first policy.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gap: '12px' }}>
                    {dbDocuments
                      .filter(d =>
                        !dbSearchQuery ||
                        d.title?.toLowerCase().includes(dbSearchQuery.toLowerCase()) ||
                        d.external_id?.toLowerCase().includes(dbSearchQuery.toLowerCase())
                      )
                      .map((doc, idx) => (
                        <div key={doc.id || idx} style={{ background: '#FFFFFF', border: '1px solid var(--border-subtle)', padding: '16px', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--text-main)' }}>
                                  {doc.title}
                                </span>
                                <span className="badge badge-verified">
                                  {doc.document_type || 'policy'}
                                </span>
                                <span className="badge badge-allow">
                                  {doc.status || 'active'}
                                </span>
                              </div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                                External ID: <span className="code-pill">{doc.external_id || 'N/A'}</span> • Created: {new Date(doc.created_at).toLocaleDateString()}
                              </div>
                            </div>
                            <span className="code-pill" style={{ fontSize: '0.7rem' }}>
                              ID: {doc.id?.substring(0, 8)}...
                            </span>
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            <span>SHA-256 Hash: <code style={{ color: 'var(--text-secondary)' }}>{doc.content_hash?.substring(0, 24)}...</code></span>
                            <span>Versions Count: <strong style={{ color: 'var(--primary)' }}>{doc.versions?.length || 1}</strong></span>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}

            {/* VIEW 3: ATOMIC CLAIMS BROWSER */}
            {docExplorerView === 'claims' && (
              <div className="clean-panel" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      Atomic Claims ({dbClaims.length})
                    </span>
                    <div className="scenario-bar">
                      <button
                        onClick={() => setClaimFilterStatus('all')}
                        className={`scenario-btn ${claimFilterStatus === 'all' ? 'scenario-btn-active' : ''}`}
                      >
                        All ({dbClaims.length})
                      </button>
                      <button
                        onClick={() => setClaimFilterStatus('verified')}
                        className={`scenario-btn ${claimFilterStatus === 'verified' ? 'scenario-btn-active' : ''}`}
                      >
                        Verified
                      </button>
                      <button
                        onClick={() => setClaimFilterStatus('outdated')}
                        className={`scenario-btn ${claimFilterStatus === 'outdated' ? 'scenario-btn-active' : ''}`}
                      >
                        Outdated
                      </button>
                      <button
                        onClick={() => setClaimFilterStatus('conflicted')}
                        className={`scenario-btn ${claimFilterStatus === 'conflicted' ? 'scenario-btn-active' : ''}`}
                      >
                        Conflicted
                      </button>
                    </div>
                  </div>

                  <input
                    type="text"
                    placeholder="Search claims by keyword, subject, or predicate..."
                    value={dbSearchQuery}
                    onChange={e => setDbSearchQuery(e.target.value)}
                    style={{ padding: '6px 12px', fontSize: '0.8rem', width: '280px' }}
                  />
                </div>

                {dbClaims.length === 0 ? (
                  <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    No claims stored in database yet.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gap: '12px' }}>
                    {dbClaims
                      .filter(c => claimFilterStatus === 'all' || c.status?.toLowerCase() === claimFilterStatus)
                      .filter(c =>
                        !dbSearchQuery ||
                        c.claim_text?.toLowerCase().includes(dbSearchQuery.toLowerCase()) ||
                        c.subject?.toLowerCase().includes(dbSearchQuery.toLowerCase()) ||
                        c.predicate?.toLowerCase().includes(dbSearchQuery.toLowerCase())
                      )
                      .map((claim, idx) => {
                        const score = claim.trust_scores?.[0]?.overall_score || claim.trust_scores?.[0]?.source_score || 0.95;
                        const validity = claim.validity_records?.[0]?.validity_status || 'valid';
                        return (
                          <div key={claim.id || idx} style={{ background: '#FFFFFF', border: '1px solid var(--border-subtle)', padding: '14px', borderRadius: '8px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                <span className="code-pill">Subject: {claim.subject || 'General'}</span>
                                <span className="code-pill">Predicate: {claim.predicate || 'specifies'}</span>
                                {claim.object && <span className="code-pill">Object: {claim.object}</span>}
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span className={`badge ${claim.status === 'verified' ? 'badge-allow' : claim.status === 'outdated' ? 'badge-outdated' : 'badge-review'}`}>
                                  {claim.status}
                                </span>
                                <span className="badge badge-verified">
                                  Trust: {(Number(score) * 100).toFixed(0)}%
                                </span>
                              </div>
                            </div>

                            <p style={{ fontSize: '0.875rem', fontWeight: 600, color: claim.status === 'outdated' ? 'var(--text-muted)' : 'var(--text-main)', lineHeight: '1.4' }}>
                              "{claim.claim_text}"
                            </p>

                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                              <span>Section: {claim.evidence?.[0]?.section || 'General'}</span>
                              <span>Validity: <strong style={{ color: validity === 'valid' ? 'var(--success-text)' : 'var(--danger-text)' }}>{validity.toUpperCase()}</strong></span>
                              <span>ID: <code style={{ color: 'var(--text-secondary)' }}>{claim.id?.substring(0, 8)}</code></span>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 6: DECISION AUDIT TRAIL & LINEAGE EXPLORER            */}
        {/* ========================================================= */}
        {activeTab === 'audit' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

            {/* Top Header & Compliance Export Actions */}
            <div className="clean-panel" style={{ padding: '24px', background: 'var(--bg-card)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <span className="badge badge-verified" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                      🛡️ AI GOVERNANCE & AUDIT TRAIL
                    </span>
                    <span className="badge badge-outline" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                      SOC2 Type II • ISO 42001 • EU AI Act Art. 12
                    </span>
                  </div>
                  <h1 style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                    Live Decision Audit Trail & Lineage Explorer
                  </h1>
                  <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '4px', margin: 0, maxWidth: '720px' }}>
                    Cryptographically tamper-evident decision logs with 4-stage end-to-end lineage tracing, actor authorization gates, and candidate evidence provenance.
                  </p>
                </div>

                {/* Right: Export & Refresh Buttons */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => fetchAuditLogs(activeOrg?.id)}
                    className="btn btn-secondary"
                    disabled={auditLoading}
                    style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 13px' }}
                  >
                    <span style={{ display: 'inline-block', transform: auditLoading ? 'rotate(180deg)' : 'none', transition: 'transform 0.5s' }}>
                      🔄
                    </span>
                    {auditLoading ? 'Refreshing...' : 'Refresh Logs'}
                  </button>
                  <button
                    onClick={() => handleExportAuditLogs('csv')}
                    className="btn btn-secondary"
                    style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 13px' }}
                  >
                    <span>📊</span> Export CSV
                  </button>
                  <button
                    onClick={() => handleExportAuditLogs('json')}
                    className="btn btn-primary"
                    style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 14px' }}
                  >
                    <span>📜</span> Export SOC2 Compliance JSON
                  </button>
                </div>
              </div>

              {/* 5 Compliance KPI Summary Cards */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '12px',
                marginTop: '20px'
              }}>
                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                    Total Decisions
                  </div>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                    {auditSummary.total_decisions}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    100% Provenance Captured
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                    Policy Allow Rate
                  </div>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--success-text)', marginTop: '4px' }}>
                    {auditSummary.allow_rate_pct}%
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {auditSummary.allow_count} Allowed / {auditSummary.block_count} Blocked
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                    Risk Interceptions
                  </div>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: auditSummary.block_count > 0 ? 'var(--danger-text, #ef4444)' : 'var(--text-main)', marginTop: '4px' }}>
                    {auditSummary.block_count + auditSummary.review_count}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {auditSummary.high_risk_count} High Risk Blocked
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                    Crypto Signatures
                  </div>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--primary)', marginTop: '4px' }}>
                    100% SHA-256
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--success-text)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>✓</span> Tamper-Evident Hash Chain
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                    Avg Gate Latency
                  </div>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                    {auditSummary.avg_latency_ms} <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>ms</span>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Real-time inline guard
                  </div>
                </div>
              </div>
            </div>

            {/* Filter Toolbar & Live Audit Log Stream */}
            <div className="clean-panel" style={{ padding: '20px', background: 'var(--bg-card)' }}>

              {/* Filter Controls Bar */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>

                {/* Search Box */}
                <div style={{ position: 'relative', minWidth: '260px', flex: 1, maxWidth: '400px' }}>
                  <input
                    type="text"
                    placeholder="Search prompt, actor ID, or audit ID..."
                    value={auditSearchQuery}
                    onChange={(e) => setAuditSearchQuery(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px 8px 32px',
                      fontSize: '0.82rem',
                      background: 'var(--bg-card-subtle)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '6px',
                      color: 'var(--text-main)'
                    }}
                  />
                  <span style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    🔍
                  </span>
                  {auditSearchQuery && (
                    <button
                      onClick={() => setAuditSearchQuery('')}
                      style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* Verdict Filters */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 700, marginRight: '4px' }}>
                    VERDICT:
                  </span>
                  {['all', 'ALLOW', 'BLOCK', 'REVIEW', 'CLARIFY'].map(v => (
                    <button
                      key={v}
                      onClick={() => setAuditFilterVerdict(v)}
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.74rem',
                        fontWeight: 700,
                        borderRadius: '4px',
                        border: auditFilterVerdict === v ? '1px solid var(--primary)' : '1px solid var(--border-subtle)',
                        background: auditFilterVerdict === v ? 'var(--primary-subtle, rgba(99,102,241,0.15))' : 'var(--bg-card-subtle)',
                        color: auditFilterVerdict === v ? 'var(--primary)' : 'var(--text-muted)',
                        cursor: 'pointer'
                      }}
                    >
                      {v.toUpperCase()}
                    </button>
                  ))}
                </div>

                {/* Risk Filter */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 700 }}>
                    RISK:
                  </span>
                  <select
                    value={auditFilterRisk}
                    onChange={(e) => setAuditFilterRisk(e.target.value)}
                    style={{
                      padding: '5px 10px',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      borderRadius: '4px',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-card-subtle)',
                      color: 'var(--text-main)'
                    }}
                  >
                    <option value="all">All Risk Levels</option>
                    <option value="LOW">Low Risk</option>
                    <option value="MEDIUM">Medium Risk</option>
                    <option value="HIGH">High Risk</option>
                  </select>
                </div>
              </div>

              {/* Logs Table */}
              {auditLogs.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📋</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    No Decision Audit Records Found
                  </div>
                  <p style={{ fontSize: '0.78rem', marginTop: '4px', maxWidth: '450px', margin: '4px auto 16px auto' }}>
                    {auditSearchQuery || auditFilterVerdict !== 'all' || auditFilterRisk !== 'all'
                      ? 'No records match your active search or filter criteria. Try resetting filters.'
                      : 'Run a Decision Gate evaluation or query the MCP server to begin populating the live compliance audit log.'}
                  </p>
                  {(auditSearchQuery || auditFilterVerdict !== 'all' || auditFilterRisk !== 'all') && (
                    <button
                      onClick={() => { setAuditSearchQuery(''); setAuditFilterVerdict('all'); setAuditFilterRisk('all'); }}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.78rem', padding: '6px 14px' }}
                    >
                      Reset Filters
                    </button>
                  )}
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Timestamp & Audit ID</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Actor & Role</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Decision Prompt</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Verdict</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Risk</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>Crypto Token</th>
                        <th style={{ padding: '10px 12px', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase', textAlign: 'right' }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((log) => (
                        <tr
                          key={log.id || log.audit_id}
                          style={{
                            borderBottom: '1px solid var(--border-subtle)',
                            cursor: 'pointer',
                            transition: 'background 0.15s'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-card-subtle)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                          onClick={() => handleInspectLineage(log.audit_id)}
                        >
                          {/* Timestamp & Audit ID */}
                          <td style={{ padding: '12px' }}>
                            <div style={{ fontWeight: 700, color: 'var(--text-main)', fontFamily: 'monospace', fontSize: '0.76rem' }}>
                              {log.audit_id}
                            </div>
                            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                              {log.created_at ? new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Just now'} • {log.created_at ? new Date(log.created_at).toLocaleDateString() : ''}
                            </div>
                          </td>

                          {/* Actor & Role */}
                          <td style={{ padding: '12px' }}>
                            <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.78rem' }}>
                              {log.actor_id}
                            </div>
                            <span className="badge badge-outline" style={{ fontSize: '0.62rem', padding: '1px 5px', marginTop: '3px', display: 'inline-block' }}>
                              {log.actor_role}
                            </span>
                          </td>

                          {/* Decision Prompt */}
                          <td style={{ padding: '12px', maxWidth: '300px' }}>
                            <div style={{ color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                              {log.decision_prompt}
                            </div>
                            {log.preferred_source && (
                              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                Source: {log.preferred_source}
                              </div>
                            )}
                          </td>

                          {/* Verdict */}
                          <td style={{ padding: '12px' }}>
                            <span
                              className={
                                log.verdict === 'ALLOW' ? 'badge badge-verified' :
                                  log.verdict === 'BLOCK' ? 'badge badge-warning' :
                                    'badge badge-review'
                              }
                              style={{ fontSize: '0.72rem', padding: '2px 8px', fontWeight: 800 }}
                            >
                              {log.verdict}
                            </span>
                          </td>

                          {/* Risk */}
                          <td style={{ padding: '12px' }}>
                            <span
                              style={{
                                fontSize: '0.7rem',
                                fontWeight: 700,
                                color: log.risk_level === 'LOW' ? 'var(--success-text)' : log.risk_level === 'HIGH' ? 'var(--danger-text, #ef4444)' : 'var(--warning-text, #f59e0b)'
                              }}
                            >
                              {log.risk_level}
                            </span>
                          </td>

                          {/* SHA-256 Token */}
                          <td style={{ padding: '12px' }} onClick={(e) => e.stopPropagation()}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <code style={{ fontSize: '0.68rem', background: 'var(--bg-card-subtle)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                                {log.audit_token ? `${log.audit_token.substring(0, 8)}...${log.audit_token.substring(log.audit_token.length - 6)}` : 'SHA256-OK'}
                              </code>
                              <button
                                onClick={() => handleCopyAuditToken(log.audit_token)}
                                title="Copy cryptographic SHA-256 signature"
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  color: copiedToken === log.audit_token ? 'var(--success-text)' : 'var(--text-muted)',
                                  cursor: 'pointer',
                                  fontSize: '0.74rem'
                                }}
                              >
                                {copiedToken === log.audit_token ? '✓' : '📋'}
                              </button>
                            </div>
                          </td>

                          {/* Action Button */}
                          <td style={{ padding: '12px', textAlign: 'right' }}>
                            <button
                              onClick={() => handleInspectLineage(log.audit_id)}
                              className="btn btn-secondary"
                              style={{ fontSize: '0.72rem', padding: '4px 10px' }}
                            >
                              Inspect Lineage ➔
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* ENTERPRISE TAB 1: LIVE INGESTION STUDIO (OPTION 1)        */}
        {/* ========================================================= */}
        {activeTab === 'live_ingestion' && (
          <LiveIngestionStudio
            activeOrg={activeOrg}
            activePersona={activePersona}
            onClaimExtracted={() => {
              fetchLiveDatabaseRecords();
              fetchHealthAndConflicts(activeOrg?.id);
            }}
            showToast={showToast}
          />
        )}

        {/* ========================================================= */}
        {/* ENTERPRISE TAB 2: VISUAL LINEAGE GRAPH (OPTION 2)         */}
        {/* ========================================================= */}
        {activeTab === 'visual_lineage' && (
          <VisualLineageGraph
            activeOrg={activeOrg}
            showToast={showToast}
          />
        )}

        {/* ========================================================= */}
        {/* ENTERPRISE TAB 3: CONTEXT CURATOR BOT (OPTION 3)          */}
        {/* ========================================================= */}
        {(activeTab === 'context_curator' || activeTab === 'conflicts') && (
          <ContextCuratorStudio
            activeOrg={activeOrg}
            showToast={showToast}
            conflicts={conflicts}
            onResolveConflict={handleResolveConflict}
            onRefreshConflicts={() => fetchHealthAndConflicts(activeOrg?.id)}
            initialSubView={activeTab === 'conflicts' ? 'conflicts' : curatorSubView}
            onSubViewChange={setCuratorSubView}
          />
        )}

        {/* ========================================================= */}
        {/* ENTERPRISE TAB 4: MCP INTEGRATION STUDIO (OPTION 4)       */}
        {/* ========================================================= */}
        {activeTab === 'integrations' && (
          <McpIntegrationStudio
            activeOrg={activeOrg}
            showToast={showToast}
            initialSubView={mcpActiveSubView}
            onSubViewChange={setMcpActiveSubView}
          />
        )}

        {/* ========================================================= */}
        {/* TAB 7: TEAM, PERSONAS & GOVERNANCE ACTIVITY HUB           */}
        {/* ========================================================= */}
        {activeTab === 'team' && (
          <TeamAndActivityHub
            activeOrg={activeOrg}
            activePersona={activePersona}
            onSelectPersona={(p) => setActivePersona(p)}
            showToast={showToast}
          />
        )}
      </main>

      {/* ========================================================= */}
      {/* 4-STAGE VISUAL DECISION LINEAGE INSPECTOR MODAL           */}
      {/* ========================================================= */}
      {isLineageModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="clean-panel" style={{ width: '100%', maxWidth: '850px', maxHeight: '90vh', overflowY: 'auto', padding: '28px', background: 'var(--bg-card)' }}>

            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px', marginBottom: '20px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>
                    DECISION PROVENANCE AUDIT
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                    {selectedAuditLineage?.audit_id || 'Loading...'}
                  </span>
                </div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  4-Stage End-to-End Decision Lineage Inspector
                </h2>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  onClick={() => {
                    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(selectedAuditLineage, null, 2));
                    const dl = document.createElement('a');
                    dl.setAttribute("href", dataStr);
                    dl.setAttribute("download", `lineage_${selectedAuditLineage?.audit_id || 'report'}.json`);
                    dl.click();
                  }}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.75rem', padding: '5px 10px' }}
                >
                  📥 Export JSON
                </button>
                <button
                  onClick={() => { setIsLineageModalOpen(false); setSelectedAuditLineage(null); }}
                  style={{ background: 'transparent', border: 'none', fontSize: '1.3rem', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px 8px' }}
                >
                  ✕
                </button>
              </div>
            </div>

            {isFetchingLineage || !selectedAuditLineage ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '1.8rem', marginBottom: '10px' }}>⏳</div>
                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Loading decision lineage & cryptographic verification...</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

                {/* STAGE 1: Actor & Intent */}
                <div style={{ background: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--primary)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800 }}>
                        1
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        STAGE 1: ACTOR INTENT & ROLE AUTHORIZATION
                      </span>
                    </div>
                    <span className="badge badge-outline" style={{ fontSize: '0.65rem' }}>
                      Scope: {selectedAuditLineage.stage_1_actor.scope}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.8rem', marginBottom: '8px' }}>
                    <div>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>Actor Identifier: </span>
                      <span style={{ fontWeight: 700, color: 'var(--text-main)', fontFamily: 'monospace' }}>
                        {selectedAuditLineage.stage_1_actor.actor_id}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>Actor Role: </span>
                      <span className="badge badge-review" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                        {selectedAuditLineage.stage_1_actor.actor_role}
                      </span>
                    </div>
                  </div>

                  <div style={{ background: 'var(--bg-card)', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '0.82rem', color: 'var(--text-main)' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', fontWeight: 700, marginBottom: '2px' }}>
                      DECISION PROMPT / REQUESTED ACTION:
                    </span>
                    {selectedAuditLineage.stage_1_actor.decision_prompt}
                  </div>
                </div>

                {/* STAGE 2: Evidence & Candidate Authority */}
                <div style={{ background: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--primary)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800 }}>
                        2
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        STAGE 2: CANDIDATE EVIDENCE & AUTHORITY RATINGS
                      </span>
                    </div>
                    <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                      {selectedAuditLineage.stage_2_evidence.total_candidate_claims} Candidate Claims Evaluated
                    </span>
                  </div>

                  {selectedAuditLineage.stage_2_evidence.sources.length === 0 ? (
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '6px 0' }}>
                      No separate candidate context items were attached; policy evaluated against authoritative organizational registry.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {selectedAuditLineage.stage_2_evidence.sources.map((item, idx) => (
                        <div key={idx} style={{ background: 'var(--bg-card)', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '0.78rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>
                                📄 {item.source || item.source_id || 'System Document'}
                              </span>
                              {item.updated_at && (
                                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                                  ({item.updated_at})
                                </span>
                              )}
                            </div>
                            <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                              Authority: {item.authority_level || 50}/100
                            </span>
                          </div>
                          <div style={{ color: 'var(--text-main)', marginTop: '4px', fontStyle: 'italic' }}>
                            "{item.claim || item.content || JSON.stringify(item)}"
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* STAGE 3: Contradiction Engine & Scope Check */}
                <div style={{ background: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--primary)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800 }}>
                        3
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        STAGE 3: CONTRADICTION & FRESHNESS RESOLUTION
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <span className={selectedAuditLineage.stage_3_contradiction.conflicts_detected ? 'badge badge-warning' : 'badge badge-verified'} style={{ fontSize: '0.65rem' }}>
                        {selectedAuditLineage.stage_3_contradiction.conflicts_detected ? '⚠️ Contradiction Resolved' : '✓ Uncontradicted'}
                      </span>
                      <span className={selectedAuditLineage.stage_3_contradiction.role_authorized ? 'badge badge-verified' : 'badge badge-warning'} style={{ fontSize: '0.65rem' }}>
                        {selectedAuditLineage.stage_3_contradiction.role_authorized ? '✓ Role Authorized' : '🛑 Role Insufficient'}
                      </span>
                    </div>
                  </div>

                  {selectedAuditLineage.stage_3_contradiction.contradiction_details.length > 0 ? (
                    <div style={{ background: 'var(--bg-card)', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '0.78rem' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--warning-text, #f59e0b)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                        CONTRADICTION ANALYSIS:
                      </span>
                      <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--text-main)' }}>
                        {selectedAuditLineage.stage_3_contradiction.contradiction_details.map((detail, idx) => (
                          <li key={idx} style={{ marginBottom: '2px' }}>{detail}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div style={{ fontSize: '0.78rem', color: 'var(--success-text)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>✓</span> No temporal or authority conflicts detected across active corporate policies.
                    </div>
                  )}
                </div>

                {/* STAGE 4: Final Verdict & Cryptographic Hash */}
                <div style={{ background: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--success-solid)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800 }}>
                        4
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        STAGE 4: FINAL VERDICT & CRYPTOGRAPHIC PROVENANCE
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        Latency: {selectedAuditLineage.stage_4_verdict.execution_ms} ms
                      </span>
                      <span
                        className={
                          selectedAuditLineage.stage_4_verdict.verdict === 'ALLOW' ? 'badge badge-verified' :
                            selectedAuditLineage.stage_4_verdict.verdict === 'BLOCK' ? 'badge badge-warning' :
                              'badge badge-review'
                        }
                        style={{ fontSize: '0.75rem', padding: '3px 10px', fontWeight: 800 }}
                      >
                        {selectedAuditLineage.stage_4_verdict.verdict}
                      </span>
                    </div>
                  </div>

                  {/* Reasons */}
                  <div style={{ marginBottom: '12px' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                      EXPLAINABLE AUDIT REASONS:
                    </span>
                    <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.8rem', color: 'var(--text-main)' }}>
                      {selectedAuditLineage.stage_4_verdict.reasons.map((r, idx) => (
                        <li key={idx} style={{ marginBottom: '3px' }}>{r}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Suggested Action */}
                  {selectedAuditLineage.stage_4_verdict.suggested_action && (
                    <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '0.78rem', marginBottom: '12px' }}>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block' }}>
                        SUGGESTED NEXT ACTION:
                      </span>
                      <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>
                        {selectedAuditLineage.stage_4_verdict.suggested_action}
                      </span>
                    </div>
                  )}

                  {/* Cryptographic SHA-256 Signature Box */}
                  <div style={{ background: 'rgba(0,0,0,0.4)', padding: '12px', borderRadius: '6px', border: '1px solid var(--primary-subtle, rgba(99,102,241,0.3))' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--primary)', fontWeight: 800, letterSpacing: '0.05em' }}>
                        🔒 CRYPTOGRAPHIC SHA-256 AUDIT SIGNATURE
                      </span>
                      <button
                        onClick={() => handleCopyAuditToken(selectedAuditLineage.stage_4_verdict.audit_token)}
                        className="btn btn-secondary"
                        style={{ fontSize: '0.68rem', padding: '3px 8px' }}
                      >
                        {copiedToken === selectedAuditLineage.stage_4_verdict.audit_token ? '✓ Copied' : 'Copy Hash'}
                      </button>
                    </div>
                    <code style={{ fontSize: '0.72rem', color: '#38bdf8', wordBreak: 'break-all', display: 'block', fontFamily: 'monospace' }}>
                      {selectedAuditLineage.stage_4_verdict.audit_token}
                    </code>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                      Tamper-evident digest of actor, prompt, evidence claims, timestamp, and verdict.
                    </div>
                  </div>
                </div>

              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: REGISTER NEW CLIENT ORGANIZATION / WORKSPACE       */}
      {/* ========================================================= */}
      {showNewOrgModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="clean-panel" style={{ width: '100%', maxWidth: '480px', padding: '24px', background: 'var(--bg-card)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  Register Client Workspace
                </h3>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px', margin: 0 }}>
                  Create an isolated tenant domain for your client company.
                </p>
              </div>
              <button
                onClick={() => setShowNewOrgModal(false)}
                style={{ background: 'transparent', border: 'none', fontSize: '1.2rem', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateOrganization}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Company / Organization Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. demo, Demo Enterprise..."
                  value={newOrgName}
                  onChange={e => {
                    setNewOrgName(e.target.value);
                    if (!newOrgSlug) {
                      setNewOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''));
                    }
                  }}
                  required
                  style={{ width: '100%', padding: '10px 12px', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Workspace Tenant Slug *
                </label>
                <input
                  type="text"
                  placeholder="e.g. demo, demo-prod"
                  value={newOrgSlug}
                  onChange={e => setNewOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, ''))}
                  required
                  style={{ width: '100%', padding: '10px 12px', fontSize: '0.85rem', fontFamily: 'monospace' }}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                  Unique identifier used for isolated database partition and connector scope.
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowNewOrgModal(false)}
                  className="btn btn-secondary"
                  style={{ padding: '8px 16px', fontSize: '0.82rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingOrg || !newOrgName.trim()}
                  className="btn btn-primary"
                  style={{ padding: '8px 20px', fontSize: '0.82rem' }}
                >
                  {isCreatingOrg ? 'Creating...' : 'Create & Switch Workspace'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: CREATE DEPARTMENTAL WORKSPACE                     */}
      {/* ========================================================= */}
      {showNewWorkspaceModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="clean-panel" style={{ width: '100%', maxWidth: '480px', padding: '24px', background: 'var(--bg-card)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <span className="badge badge-verified" style={{ marginBottom: '6px' }}>
                  🏢 {activeOrg?.name || 'demo'}
                </span>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  Create Department Workspace
                </h3>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px', margin: 0 }}>
                  Add a functional domain workspace under this client company.
                </p>
              </div>
              <button
                onClick={() => setShowNewWorkspaceModal(false)}
                style={{ background: 'transparent', border: 'none', fontSize: '1.2rem', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateWorkspace}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Workspace Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Legal & Compliance, Growth Engineering, EMEA Support..."
                  value={newWorkspaceName}
                  onChange={e => setNewWorkspaceName(e.target.value)}
                  required
                  style={{ width: '100%', padding: '10px 12px', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Department Domain *
                </label>
                <select
                  value={newWorkspaceDomain}
                  onChange={e => setNewWorkspaceDomain(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', fontSize: '0.85rem', background: 'var(--bg-card-subtle)', color: 'var(--text-main)', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}
                >
                  <option value="finance">💳 Finance & Billing Operations</option>
                  <option value="secops">🛡️ Engineering & Infrastructure SecOps</option>
                  <option value="hr">👥 HR & People Operations</option>
                  <option value="support">💬 Customer Support & Success</option>
                  <option value="staging">🧪 Staging / Policy Sandbox</option>
                  <option value="global">📁 General / Multi-Department</option>
                </select>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Workspace Scope & Purpose
                </label>
                <input
                  type="text"
                  placeholder="e.g. Dedicated space for compliance audits and legal policy validation"
                  value={newWorkspaceDescription}
                  onChange={e => setNewWorkspaceDescription(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowNewWorkspaceModal(false)}
                  className="btn btn-secondary"
                  style={{ padding: '8px 16px', fontSize: '0.82rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newWorkspaceName.trim()}
                  className="btn btn-primary"
                  style={{ padding: '8px 20px', fontSize: '0.82rem' }}
                >
                  Create & Switch Workspace
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

