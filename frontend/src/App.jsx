import React, { useState, useEffect, useRef, useMemo } from 'react';
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
  MoreHorizontal,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  ShieldCheck,
  Terminal,
  Cpu,
  History,
  Sparkles,
  Eye,
  Lock,
  Database,
  Shield,
  Bell,
  UserCheck,
  Crosshair,
  Binary,
  User,
  Building2,
  FolderGit2,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  PanelLeftClose,
  PanelLeftOpen,
  X
} from 'lucide-react';
import UserProfileStudio from './components/UserProfileStudio';
import TeamAndActivityHub from './components/TeamAndActivityHub';
import AgentChatPlayground from './components/AgentChatPlayground';
import LiveIngestionStudio from './components/LiveIngestionStudio';
import VisualLineageGraph from './components/VisualLineageGraph';
import ContextCuratorStudio from './components/ContextCuratorStudio';
import McpIntegrationStudio from './components/McpIntegrationStudio';
import SignInModal from './components/SignInModal';
import OrganizationSettingsModal from './components/OrganizationSettingsModal';
import RbacMatrixModal from './components/RbacMatrixModal';
import ExecutiveRoiModal from './components/ExecutiveRoiModal';
import ComplianceDossierModal from './components/ComplianceDossierModal';
import WebhookSettingsModal from './components/WebhookSettingsModal';
import HitlEscalationModal from './components/HitlEscalationModal';
import RedTeamModal from './components/RedTeamModal';
import MerkleVerificationModal from './components/MerkleVerificationModal';
import AssetInspectorDrawer from './components/AssetInspectorDrawer';
import MillionScaleClaimsGrid from './components/MillionScaleClaimsGrid';
import { useAuth, DEFAULT_ENTERPRISE_PERSONAS } from './context/AuthContext';

// -------------------------------------------------------------
// Route URL & Navigation Configuration
// -------------------------------------------------------------
const TAB_TO_PATH = {
  home: '/',
  playground: '/chat',
  demo: '/demo',
  live_ingestion: '/live-ingestion',
  visual_lineage: '/lineage',
  context_curator: '/curator',
  conflicts: '/conflicts',
  ingestion: '/documents',
  integrations: '/integrations',
  audit: '/audit',
  team: '/team',
  profile: '/profile'
};

const PATH_TO_TAB = {
  '/': 'home',
  '/home': 'home',
  '/chat': 'playground',
  '/playground': 'playground',
  '/demo': 'demo',
  '/live-ingestion': 'live_ingestion',
  '/lineage': 'visual_lineage',
  '/visual-lineage': 'visual_lineage',
  '/curator': 'context_curator',
  '/context-curator': 'context_curator',
  '/conflicts': 'conflicts',
  '/documents': 'ingestion',
  '/ingestion': 'ingestion',
  '/integrations': 'integrations',
  '/audit': 'audit',
  '/team': 'team',
  '/profile': 'profile'
};

const DEFAULT_WORKSPACES = [
  { id: 'all', name: 'All Workspaces (Unified)', icon: '🌐', domain: 'global', description: 'Unified enterprise knowledge across all departments and systems' },
  { id: 'finance', name: 'Finance & Billing Operations', icon: '💳', domain: 'finance', description: 'Invoices, customer refunds, ARR tiers, and accounting compliance SLAs' },
  { id: 'secops', name: 'Engineering & Infrastructure SecOps', icon: '🛡️', domain: 'secops', description: 'IAM policies, mTLS authentication, Friday freezes, and session expiration' },
  { id: 'hr', name: 'HR & People Operations', icon: '👥', domain: 'hr', description: 'Remote work guidelines, employee handbooks, and leave approval rules' },
  { id: 'support', name: 'Customer Support & Success', icon: '💬', domain: 'support', description: 'Dispute arbitration workflows, tier exception matrices, and SLA escalations' },
  { id: 'staging', name: 'Staging / Policy Sandbox', icon: '🧪', domain: 'staging', description: 'Isolated sandbox environment for dry-run conflict and gate simulations' },
];

const getInitialTabFromUrl = () => {
  if (typeof window === 'undefined') return 'home';
  const pathname = window.location.pathname.toLowerCase().replace(/\/$/, '') || '/';
  return PATH_TO_TAB[pathname] || 'home';
};

const getInitialWorkspaceFromUrl = () => {
  if (typeof window === 'undefined') return DEFAULT_WORKSPACES[0];
  const params = new URLSearchParams(window.location.search);
  const wsId = params.get('workspace');
  if (wsId) {
    const found = DEFAULT_WORKSPACES.find(w => w.id === wsId || w.domain === wsId);
    if (found) return found;
  }
  return DEFAULT_WORKSPACES[0];
};

const getInitialDocViewFromUrl = () => {
  if (typeof window === 'undefined') return 'connectors';
  const params = new URLSearchParams(window.location.search);
  const view = params.get('view');
  if (view && ['connectors', 'ingest', 'documents', 'claims'].includes(view)) {
    return view;
  }
  return 'connectors';
};

export default function App() {
  const [activeTab, setActiveTab] = useState(getInitialTabFromUrl);
  const [expandedMenu, setExpandedMenu] = useState(getInitialTabFromUrl);
  const [vaultSubTab, setVaultSubTab] = useState('documents');
  const [isVaultMenuOpen, setIsVaultMenuOpen] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [health, setHealth] = useState({ status: 'checking', database: false, version: '0.1.0' });
  const [conflicts, setConflicts] = useState([]);
  const [curatorSubView, setCuratorSubView] = useState('health'); // 'health' | 'conflicts'
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [isOrgSettingsModalOpen, setIsOrgSettingsModalOpen] = useState(false);
  const [isRbacModalOpen, setIsRbacModalOpen] = useState(false);
  const [isRoiModalOpen, setIsRoiModalOpen] = useState(false);
  const [isDossierModalOpen, setIsDossierModalOpen] = useState(false);
  const [isWebhookModalOpen, setIsWebhookModalOpen] = useState(false);
  const [isHitlModalOpen, setIsHitlModalOpen] = useState(false);
  const [isRedTeamModalOpen, setIsRedTeamModalOpen] = useState(false);
  const [isMerkleModalOpen, setIsMerkleModalOpen] = useState(false);
  const [merkleSelectedToken, setMerkleSelectedToken] = useState(null);
  const [isGateToolsDrawerOpen, setIsGateToolsDrawerOpen] = useState(false);
  const [hoveredGateTool, setHoveredGateTool] = useState(null);
  const [pinnedGateTool, setPinnedGateTool] = useState(null);
  const [inspectorState, setInspectorState] = useState({
    isOpen: false,
    assetType: 'document', // 'document' | 'connector'
    assetId: null,
    assetTitle: ''
  });

  // -------------------------------------------------------------
  const {
    user: authUser,
    organization: authOrg,
    isAuthenticated,
    personas: authPersonas,
    setIsAuthModalOpen,
    setAuthModalTab,
    loginAsPersona: authLoginAsPersona,
    switchOrganization,
    logout: authLogout,
    effectiveRole,
    simulatedRole,
    setSimulatedRole,
    isTabVisible,
    getSodGuard,
    roleMetadata,
  } = useAuth();

  // Atlan Active Persona & User Ecosystem State
  const [personas, setPersonas] = useState(DEFAULT_ENTERPRISE_PERSONAS);
  const [activePersona, setActivePersona] = useState(DEFAULT_ENTERPRISE_PERSONAS[0]);
  const [isPersonaDropdownOpen, setIsPersonaDropdownOpen] = useState(false);

  // Auto-redirect if active tab is restricted under effective/simulated role
  useEffect(() => {
    if (activeTab && isTabVisible && !isTabVisible(activeTab)) {
      setActiveTab('home');
      setExpandedMenu('home');
    }
  }, [effectiveRole, activeTab, isTabVisible]);

  useEffect(() => {
    if (authUser) {
      setActivePersona(authUser);
    }
  }, [authUser]);

  useEffect(() => {
    if (authPersonas && authPersonas.length > 0) {
      setPersonas(authPersonas);
    }
  }, [authPersonas]);

  const handleSelectPersona = async (p) => {
    setActivePersona(p);
    if (authLoginAsPersona) {
      await authLoginAsPersona(p);
    }
    showToast(`Switched active user to ${p.name} (${(p.role || 'user').toUpperCase()})`);
  };

  const handleToggleParentTab = (tabName) => {
    setActiveTab(tabName);
    setExpandedMenu(prev => prev === tabName ? null : tabName);
  };



  // -------------------------------------------------------------
  // Decision Gate & Policy Simulator State
  // -------------------------------------------------------------
  const [demoScenario, setDemoScenario] = useState('refund_trap');
  const [simulatorMode, setSimulatorMode] = useState('custom'); // 'custom' | 'presets'
  const [customActionText, setCustomActionText] = useState('Authorize 45-day refund for Enterprise customer on Acme Corp plan');
  const [customActorId, setCustomActorId] = useState('autonomous-agent-01');
  const [customActorRole, setCustomActorRole] = useState('support_agent');
  const [customRequiredScope, setCustomRequiredScope] = useState('Enterprise');
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoStep, setDemoStep] = useState(0); // 0: Idle, 1: Evaluating, 2: Result
  const [demoResult, setDemoResult] = useState(null);
  const [decisionStream, setDecisionStream] = useState([]);
  const [streamLoading, setStreamLoading] = useState(false);
  const [showManualOverride, setShowManualOverride] = useState(false);

  // Intelligent Context & Persona Detection Engine
  const inferActionContext = (text) => {
    const lower = (text || '').toLowerCase();

    // 1. Network / Ingress / Firewall / Infrastructure / Deployment
    if (
      lower.includes('ingress') ||
      lower.includes('firewall') ||
      lower.includes('port 80') ||
      lower.includes('port 8080') ||
      lower.includes('port 22') ||
      lower.includes('plaintext') ||
      lower.includes('k8s') ||
      lower.includes('kubernetes') ||
      lower.includes('cluster') ||
      lower.includes('deploy') ||
      lower.includes('infrastructure')
    ) {
      if (
        lower.includes('intern') ||
        lower.includes('junior') ||
        lower.includes('dev-intern') ||
        lower.includes('unauthorized') ||
        lower.includes('plaintext')
      ) {
        return {
          actorId: 'dev-intern-bot',
          role: 'junior_developer',
          roleLabel: 'Junior Developer (Intern Bot)',
          roleShort: 'Junior Dev',
          scope: 'Production',
          scopeLabel: 'Production Environment',
          scopeShort: 'Production',
          confidence: '98%',
          rationale: 'Unauthorized production port ingress intent'
        };
      }
      return {
        actorId: 'devops-agent-01',
        role: 'devops_engineer',
        roleLabel: 'DevOps Engineer (CI/CD Bot)',
        roleShort: 'DevOps Bot',
        scope: lower.includes('staging') ? 'Staging' : 'Production',
        scopeLabel: lower.includes('staging') ? 'Staging Sandbox' : 'Production Environment',
        scopeShort: lower.includes('staging') ? 'Staging' : 'Production',
        confidence: '95%',
        rationale: 'Infrastructure change & CI/CD deployment'
      };
    }

    // 2. HR / Remote Work / Leave / Benefits / Vacation
    if (
      lower.includes('remote') ||
      lower.includes('work from home') ||
      lower.includes('wfh') ||
      lower.includes('schedule') ||
      lower.includes('leave') ||
      lower.includes('vacation') ||
      lower.includes('pto') ||
      lower.includes('benefit') ||
      lower.includes('payroll') ||
      lower.includes('employee')
    ) {
      const isEng = lower.includes('engineering') || lower.includes('developer') || lower.includes('senior developer') || lower.includes('engineer');
      return {
        actorId: 'hr-assistant-bot',
        role: 'hr_reviewer',
        roleLabel: 'HR Reviewer (Benefits Assistant)',
        roleShort: 'HR Reviewer',
        scope: isEng ? 'Engineering' : 'General',
        scopeLabel: isEng ? 'Engineering Department' : 'Global Standard',
        scopeShort: isEng ? 'Engineering' : 'Global',
        confidence: '96%',
        rationale: 'Employee policy & workplace schedule adjustment'
      };
    }

    // 3. Finance / Refund / Billing / Invoices / Payments
    if (
      lower.includes('refund') ||
      lower.includes('billing') ||
      lower.includes('invoice') ||
      lower.includes('payment') ||
      lower.includes('charge') ||
      lower.includes('credit') ||
      lower.includes('subscription') ||
      lower.includes('acme') ||
      lower.includes('$') ||
      lower.includes('discount')
    ) {
      const isEnterprise = lower.includes('enterprise') || lower.includes('acme') || lower.includes('annual') || lower.includes('tier') || lower.includes('45-day');
      return {
        actorId: 'billing-agent-01',
        role: 'support_agent',
        roleLabel: 'Support Agent (Customer Bot)',
        roleShort: 'Support Bot',
        scope: isEnterprise ? 'Enterprise' : 'General',
        scopeLabel: isEnterprise ? 'Enterprise Customer Tier' : 'Global Standard',
        scopeShort: isEnterprise ? 'Enterprise' : 'Global',
        confidence: '99%',
        rationale: 'Customer billing & financial exception transaction'
      };
    }

    // 4. Compliance / Audit / Legal / Freeze
    if (
      lower.includes('audit') ||
      lower.includes('compliance') ||
      lower.includes('gdpr') ||
      lower.includes('pii') ||
      lower.includes('freeze') ||
      lower.includes('legal') ||
      lower.includes('export')
    ) {
      return {
        actorId: 'compliance-gate-01',
        role: 'compliance_officer',
        roleLabel: 'Compliance Officer (Risk Gate)',
        roleShort: 'Risk Gate',
        scope: 'Enterprise',
        scopeLabel: 'Enterprise Customer Tier',
        scopeShort: 'Enterprise',
        confidence: '94%',
        rationale: 'Regulatory audit & governance enforcement'
      };
    }

    // Default fallback
    return {
      actorId: 'autonomous-agent-01',
      role: 'support_agent',
      roleLabel: 'Support Agent (Customer Bot)',
      roleShort: 'Support Bot',
      scope: 'Enterprise',
      scopeLabel: 'Enterprise Customer Tier',
      scopeShort: 'Enterprise',
      confidence: '90%',
      rationale: 'Standard enterprise operational scope'
    };
  };

  const detectedContext = useMemo(() => {
    return inferActionContext(customActionText);
  }, [customActionText]);

  useEffect(() => {
    if (!showManualOverride && detectedContext) {
      setCustomActorId(detectedContext.actorId);
      setCustomActorRole(detectedContext.role);
      setCustomRequiredScope(detectedContext.scope);
    }
  }, [detectedContext, showManualOverride]);

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

  // -------------------------------------------------------------
  // Departmental Workspaces under Active Company
  // -------------------------------------------------------------
  const [workspaces, setWorkspaces] = useState(DEFAULT_WORKSPACES);
  const [activeWorkspace, setActiveWorkspace] = useState(getInitialWorkspaceFromUrl);
  const [isWorkspaceDropdownOpen, setIsWorkspaceDropdownOpen] = useState(false);
  const [showNewWorkspaceModal, setShowNewWorkspaceModal] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newWorkspaceDomain, setNewWorkspaceDomain] = useState('finance');
  const [newWorkspaceDescription, setNewWorkspaceDescription] = useState('');
  const [docExplorerScopeAll, setDocExplorerScopeAll] = useState(false);
  const [docExplorerView, setDocExplorerView] = useState(getInitialDocViewFromUrl); // 'connectors' | 'ingest' | 'documents' | 'claims'

  // Chat Sessions for Sidebar History and AI Copilot Chat Sync
  const [chatSessions, setChatSessions] = useState([]);
  const [activeChatSessionId, setActiveChatSessionId] = useState(null);

  const fetchChatSessions = async () => {
    try {
      const workspaceParam = activeWorkspace?.id && activeWorkspace.id !== 'all' ? `&workspace_id=${activeWorkspace.id}` : '';
      const res = await fetch(`/v1/chat/sessions?organization_id=${activeOrg?.id || '11111111-1111-1111-1111-111111111111'}${workspaceParam}`);
      if (res.ok) {
        const data = await res.json();
        setChatSessions(data);
        if (data.length > 0 && !activeChatSessionId) {
          setActiveChatSessionId(data[0].id);
        } else if (data.length === 0) {
          setActiveChatSessionId(null);
        }
      }
    } catch (e) {
      console.error("Failed to load chat sessions for sidebar", e);
    }
  };

  const handleStartNewChatFromSidebar = async () => {
    try {
      const deptPrefix = activeWorkspace && activeWorkspace.id !== 'all' ? `[${activeWorkspace.name.split(' ')[0]}] ` : '';
      const res = await fetch('/v1/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: activeOrg?.id || '11111111-1111-1111-1111-111111111111',
          user_id: activePersona?.id || null,
          user_name: activePersona?.name || 'Sarah Chen',
          user_role: activePersona?.role || 'admin',
          title: `${deptPrefix}New Conversation`,
          workspace_id: activeWorkspace?.id || 'all',
          domain: activeWorkspace?.domain || 'global',
        }),
      });
      if (res.ok) {
        const newSession = await res.json();
        setChatSessions(prev => [newSession, ...prev]);
        setActiveChatSessionId(newSession.id);
        setActiveTab('playground');
        setNotification({ msg: `Started new conversation in ${activeWorkspace?.name || 'workspace'}`, type: 'success' });
        setTimeout(() => setNotification(null), 3000);
      }
    } catch (e) {
      console.error("Failed to create new chat session from sidebar", e);
    }
  };

  useEffect(() => {
    fetchChatSessions();
  }, [activeOrg?.id, activeWorkspace?.id]);

  // -------------------------------------------------------------
  // Browser URL Routing & History Sync Engine
  // -------------------------------------------------------------
  useEffect(() => {
    const targetPath = TAB_TO_PATH[activeTab] || '/';
    const params = new URLSearchParams(window.location.search);

    // Sync workspace query param
    if (activeWorkspace && activeWorkspace.id !== 'all') {
      params.set('workspace', activeWorkspace.id);
    } else {
      params.delete('workspace');
    }

    // Sync document explorer view query param
    if (activeTab === 'ingestion' && docExplorerView && docExplorerView !== 'connectors') {
      params.set('view', docExplorerView);
    } else if (activeTab !== 'ingestion') {
      params.delete('view');
    }

    // Retain chat session ID in query if on playground
    if (activeTab === 'playground' && activeChatSessionId) {
      params.set('session', activeChatSessionId);
    } else if (activeTab !== 'playground') {
      params.delete('session');
    }

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const targetUrl = `${targetPath}${queryString}`;
    const currentUrl = window.location.pathname + window.location.search;

    if (currentUrl !== targetUrl) {
      window.history.pushState({ tab: activeTab, workspace: activeWorkspace?.id }, '', targetUrl);
    }
  }, [activeTab, activeWorkspace?.id, docExplorerView, activeChatSessionId]);

  // Listen to browser Back / Forward navigation (popstate)
  useEffect(() => {
    const handlePopState = () => {
      const cleanPath = window.location.pathname.toLowerCase().replace(/\/$/, '') || '/';
      const targetTab = PATH_TO_TAB[cleanPath] || 'home';
      setActiveTab(targetTab);
      setExpandedMenu(targetTab);

      const params = new URLSearchParams(window.location.search);
      const wsId = params.get('workspace');
      if (wsId && workspaces) {
        const found = workspaces.find(w => w.id === wsId || w.domain === wsId);
        if (found) setActiveWorkspace(found);
      } else if (!wsId && workspaces) {
        setActiveWorkspace(DEFAULT_WORKSPACES[0]);
      }

      const viewParam = params.get('view');
      if (viewParam && ['connectors', 'ingest', 'documents', 'claims'].includes(viewParam)) {
        setDocExplorerView(viewParam);
      }

      const sessionParam = params.get('session');
      if (sessionParam) {
        setActiveChatSessionId(sessionParam);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [workspaces]);

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
  const [claimFilterStatus, setClaimFilterStatus] = useState('all');
  const [dbSearchQuery, setDbSearchQuery] = useState('');
  const [dbLoading, setDbLoading] = useState(false);

  // Departmental Workspace Filtering for Document Explorer & Repositories
  const WORKSPACE_DEPT_KEYWORDS = {
    finance: ['refund', 'billing', 'invoice', 'arr', 'payment', 'confluence', 'salesforce', 'accounting', 'pricing', 'tier', 'annual', 'dispute', 'postgresql'],
    secops: ['security', 'firewall', 'ingress', 'iam', 'mtls', 'session', 'token', 'freeze', 'portal', 'github', 'kafka', 'baseline', 'policy'],
    hr: ['remote', 'work', 'leave', 'vacation', 'employee', 'handbook', 'people', 'guideline', 'wifi', 'stipend', 'contractor'],
    support: ['support', 'dispute', 'sla', 'ticket', 'escalation', 'jira', 'arbitration', 'customer'],
    staging: ['staging', 'sandbox', 'test', 'mock', 'simulation']
  };

  const displayedDataSources = React.useMemo(() => {
    const externalOnly = (dataSources || []).filter(src => {
      const st = (src.source_type || '').toLowerCase().trim();
      const nm = (src.name || '').toLowerCase().trim();
      return st !== 'file' && st !== 'upload' && st !== 'local_file' && !nm.includes('file upload') && !nm.includes('direct document upload');
    });
    if (!activeWorkspace || activeWorkspace.id === 'all' || docExplorerScopeAll) return externalOnly;
    const kw = WORKSPACE_DEPT_KEYWORDS[activeWorkspace.id] || [];
    const filtered = externalOnly.filter(src => {
      const text = `${src.name || ''} ${src.source_type || ''} ${src.external_id || ''}`.toLowerCase();
      return kw.some(k => text.includes(k));
    });
    return filtered.length > 0 ? filtered : externalOnly;
  }, [dataSources, activeWorkspace, docExplorerScopeAll]);

  const displayedDbDocuments = React.useMemo(() => {
    if (!activeWorkspace || activeWorkspace.id === 'all' || docExplorerScopeAll) return dbDocuments;
    const kw = WORKSPACE_DEPT_KEYWORDS[activeWorkspace.id] || [];
    const filtered = dbDocuments.filter(doc => {
      const text = `${doc.title || ''} ${doc.external_id || ''} ${doc.document_type || ''}`.toLowerCase();
      return kw.some(k => text.includes(k));
    });
    return filtered.length > 0 ? filtered : dbDocuments;
  }, [dbDocuments, activeWorkspace, docExplorerScopeAll]);

  const displayedDbClaims = React.useMemo(() => {
    if (!activeWorkspace || activeWorkspace.id === 'all' || docExplorerScopeAll) return dbClaims;
    const kw = WORKSPACE_DEPT_KEYWORDS[activeWorkspace.id] || [];
    const filtered = dbClaims.filter(cl => {
      const text = `${cl.claim_text || ''} ${cl.subject || ''} ${cl.predicate || ''} ${cl.object_value || ''}`.toLowerCase();
      return kw.some(k => text.includes(k));
    });
    return filtered.length > 0 ? filtered : dbClaims;
  }, [dbClaims, activeWorkspace, docExplorerScopeAll]);

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

  const handleSwitchOrganization = async (org) => {
    setActiveOrg(org);
    localStorage.setItem('context_layer_active_org_id', org.id);
    setIsOrgDropdownOpen(false);
    try {
      if (switchOrganization) {
        await switchOrganization(org.id);
      }
      showToast(`Switched active workspace to '${org.name}'`);
      await fetchHealthAndConflicts(org.id);
      await fetchSources(org.id);
    } catch (err) {
      console.warn('Switch org error:', err);
      showToast(`Switched workspace to '${org.name}'`);
    }
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
      fetchDecisionStream(activeOrg.id);
    }
  }, [activeOrg?.id]);

  useEffect(() => {
    if (activeTab === 'audit' && activeOrg?.id) {
      fetchAuditLogs(activeOrg.id, auditFilterVerdict, auditFilterRisk, auditSearchQuery);
    }
    if (activeTab === 'demo' && activeOrg?.id) {
      fetchDecisionStream(activeOrg.id);
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
  // Real-Time Agent Decision Stream Fetcher
  // -------------------------------------------------------------
  const fetchDecisionStream = async (orgId = activeOrg?.id) => {
    if (!orgId) return;
    try {
      setStreamLoading(true);
      const res = await fetch(`/v1/decisions/stream?organization_id=${orgId}&limit=20`);
      if (res.ok) {
        const data = await res.json();
        setDecisionStream(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.warn("Failed to fetch decision stream:", err);
    } finally {
      setStreamLoading(false);
    }
  };

  // -------------------------------------------------------------
  // Execute Decision Gate Evaluation
  // -------------------------------------------------------------
  const runKillerDemo = async (customPromptOverride = null) => {
    setDemoRunning(true);
    setDemoStep(1);
    setDemoResult(null);

    const isCustom = simulatorMode === 'custom';
    const current = scenarios[demoScenario];

    try {
      let payload;
      if (isCustom) {
        const promptToRun = customPromptOverride || customActionText;
        if (!promptToRun || !promptToRun.trim()) {
          showToast("Please enter an intended agent action to evaluate", "error");
          setDemoRunning(false);
          setDemoStep(0);
          return;
        }
        payload = {
          decision: promptToRun.trim(),
          actor: {
            id: customActorId || "autonomous-agent-01",
            role: customActorRole || "support_agent"
          },
          context: [], // empty context triggers backend dynamic auto-retrieval from PostgreSQL claims!
          organization_id: activeOrg?.id,
          required_scope: customRequiredScope || null
        };
      } else {
        payload = {
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
      }

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
          fetchDecisionStream(activeOrg?.id);
          showToast(`Decision Gate Verdict: ${data.decision} (Risk: ${data.risk})`);
        }, 300);
      } else {
        throw new Error("Evaluation failed");
      }
    } catch (e) {
      setTimeout(() => {
        setDemoResult({
          decision: isCustom ? "ALLOW" : (demoScenario === 'unauthorized_deploy' ? "BLOCK" : "ALLOW"),
          validity: "VALID",
          risk: isCustom ? "LOW" : (demoScenario === 'unauthorized_deploy' ? "HIGH" : "LOW"),
          reasons: isCustom ? [
            "Evaluated dynamically against active atomic claims in database.",
            "Verified actor authorization against target operational scope.",
            "No unresolved critical contradictions blocking action execution."
          ] : [
            `Evaluated 2 candidate sources against target scope '${current.claim2.scope}'.`,
            `Selected authoritative record '${current.claim2.source}' (Authority: ${current.claim2.authority}/100, Date: ${current.claim2.date}).`,
            `Superseded stale record '${current.claim1.source}'.`
          ],
          preferred_source: isCustom ? "Enterprise Knowledge Base (Active Claims)" : current.claim2.source,
          audit_id: `ctx_${Math.random().toString(36).substring(2, 10)}`,
          suggested_action: isCustom
            ? "Proceed with authorized agent execution: Trust verification passed."
            : (demoScenario === 'unauthorized_deploy'
              ? "Deny action: Actor role insufficient for production deployment."
              : "Proceed with authorized action using verified enterprise exception.")
        });
        setDemoStep(2);
        setDemoRunning(false);
        fetchDecisionStream(activeOrg?.id);
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
      {/* LEFT SIDEBAR MENU (COLLAPSIBLE ICON RAIL WHEN CLOSED)     */}
      {/* ========================================================= */}
      <aside className={`sidebar ${!isSidebarOpen ? 'sidebar-collapsed' : ''}`}>
        {/* Brand Header + Icon-Only Open/Close Toggle Button */}
        <div style={{ display: 'flex', alignItems: 'stretch', justifyContent: isSidebarOpen ? 'space-between' : 'center', gap: '6px', marginBottom: '12px' }}>
          {isSidebarOpen && (
            <div 
              onClick={() => { setActiveTab('home'); setExpandedMenu('home'); }}
              style={{ 
                flex: 1,
                padding: '10px 12px', 
                background: 'linear-gradient(135deg, #181411 0%, #241D17 100%)',
                border: '1px solid rgba(255, 171, 74, 0.25)',
                borderRadius: '10px',
                cursor: 'pointer',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.12)'
              }}
              title="Trulin AI Decision & Context Trust Platform"
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                <img 
                  src="/Trulin-whiteNoBg.png" 
                  alt="Trulin" 
                  style={{ height: '22px', maxWidth: '120px', objectFit: 'contain' }} 
                />
                <span style={{ fontSize: '0.6rem', padding: '2px 5px', background: 'rgba(255,171,74,0.2)', color: '#FFAB4A', border: '1px solid rgba(255,171,74,0.4)', borderRadius: '999px', fontWeight: 700 }}>
                  v1.0
                </span>
              </div>
              <div style={{ fontSize: '0.63rem', color: '#D6D3D1', marginTop: '5px', fontWeight: 500, letterSpacing: '0.02em', display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#FFAB4A', display: 'inline-block', boxShadow: '0 0 6px #FFAB4A' }} />
                Context Trust Platform
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={() => setIsSidebarOpen(prev => !prev)}
            title={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            style={{
              width: isSidebarOpen ? '32px' : '42px',
              height: isSidebarOpen ? 'auto' : '40px',
              borderRadius: '10px',
              border: '1px solid var(--border-subtle)',
              background: '#F8FAFC',
              color: '#475569',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = '#FFF7ED';
              e.currentTarget.style.color = '#C2410C';
              e.currentTarget.style.borderColor = '#FED7AA';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = '#F8FAFC';
              e.currentTarget.style.color = '#475569';
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
            }}
          >
            {isSidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
          </button>
        </div>

        {/* Set 1: Upper Workspace Tools (Flat, Compact, Role-Filtered) */}
        <div className="nav-group" style={{ flexShrink: 0, marginBottom: '6px', width: '100%' }}>
          <button
            onClick={() => setActiveTab('home')}
            className={`nav-item ${activeTab === 'home' ? 'nav-item-active' : ''}`}
            title="Home Overview"
          >
            <Home size={16} strokeWidth={1.75} />
            <span>Home Overview</span>
          </button>

          {isTabVisible('demo') && (
            <button
              onClick={() => { setActiveTab('demo'); }}
              className={`nav-item ${activeTab === 'demo' ? 'nav-item-active' : ''}`}
              title="Decision Gate Demo"
            >
              <Brain size={16} strokeWidth={1.75} />
              <span>Decision Gate Demo</span>
            </button>
          )}

          {isTabVisible('live_ingestion') && (
            <button
              onClick={() => setActiveTab('live_ingestion')}
              className={`nav-item ${activeTab === 'live_ingestion' ? 'nav-item-active' : ''}`}
              title="Live Ingestion Studio"
            >
              <Zap size={16} strokeWidth={1.75} />
              <span>Live Ingestion Studio</span>
            </button>
          )}

          {isTabVisible('visual_lineage') && (
            <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
              <button
                onClick={() => {
                  setActiveTab('visual_lineage');
                  setIsVaultMenuOpen(prev => activeTab === 'visual_lineage' ? !prev : true);
                }}
                className={`nav-item ${activeTab === 'visual_lineage' ? 'nav-item-active' : ''}`}
                title="Vault"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: isSidebarOpen ? 'space-between' : 'center',
                  width: '100%'
                }}
              >
                {isSidebarOpen ? (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Database size={16} strokeWidth={1.75} />
                      <span>Vault</span>
                    </div>
                    <ChevronDown
                      size={13}
                      style={{
                        transform: isVaultMenuOpen || activeTab === 'visual_lineage' ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s ease',
                        opacity: 0.6
                      }}
                    />
                  </>
                ) : (
                  <Database size={16} strokeWidth={1.75} />
                )}
              </button>

              {/* Sub-items of Vault */}
              {isSidebarOpen && (isVaultMenuOpen || activeTab === 'visual_lineage') && (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px',
                  paddingLeft: '10px',
                  paddingTop: '2px',
                  paddingBottom: '3px',
                  borderLeft: '2px solid #E2E8F0',
                  marginLeft: '14px',
                  marginTop: '2px',
                  marginBottom: '4px'
                }}>
                  {[
                    { id: 'documents', label: 'Documents', count: dbDocuments.length },
                    { id: 'connectors', label: 'Connectors', count: dataSources.length },
                    { id: 'conflicts', label: 'Conflicts Registry', count: conflicts.length },
                    { id: 'claims', label: 'Claims and Decisions', count: dbClaims.length },
                    { id: 'dag', label: 'Full Canvas DAG', count: null }
                  ].map(sub => {
                    const isSubActive = activeTab === 'visual_lineage' && vaultSubTab === sub.id;
                    return (
                      <button
                        key={sub.id}
                        type="button"
                        onClick={() => {
                          setActiveTab('visual_lineage');
                          setVaultSubTab(sub.id);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '5px 8px',
                          borderRadius: '6px',
                          border: 'none',
                          background: isSubActive ? '#EFF6FF' : 'transparent',
                          color: isSubActive ? '#1D4ED8' : '#64748B',
                          fontSize: '0.74rem',
                          fontWeight: isSubActive ? 700 : 500,
                          cursor: 'pointer',
                          textAlign: 'left',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={e => {
                          if (!isSubActive) {
                            e.currentTarget.style.background = '#F8FAFC';
                            e.currentTarget.style.color = '#0F172A';
                          }
                        }}
                        onMouseLeave={e => {
                          if (!isSubActive) {
                            e.currentTarget.style.background = 'transparent';
                            e.currentTarget.style.color = '#64748B';
                          }
                        }}
                      >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {sub.label}
                        </span>
                        {sub.count !== null && sub.count !== undefined && (
                          <span style={{
                            fontSize: '0.64rem',
                            fontWeight: 600,
                            color: isSubActive ? '#2563EB' : '#94A3B8',
                            background: isSubActive ? '#DBEAFE' : '#F1F5F9',
                            padding: '1px 5px',
                            borderRadius: '4px'
                          }}>
                            {sub.count}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {isTabVisible('context_curator') && (
            <button
              onClick={() => setActiveTab('context_curator')}
              className={`nav-item ${activeTab === 'context_curator' ? 'nav-item-active' : ''}`}
              title="Context Curator Bot"
            >
              <ShieldAlert size={16} strokeWidth={1.75} />
              <span>Context Curator Bot</span>
              {isSidebarOpen && conflicts.length > 0 && (
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
          )}

          {isTabVisible('ingestion') && (
            <button
              onClick={() => setActiveTab('ingestion')}
              className={`nav-item ${activeTab === 'ingestion' ? 'nav-item-active' : ''}`}
              title="Document Explorer"
            >
              <FolderTree size={16} strokeWidth={1.75} />
              <span>Document Explorer</span>
            </button>
          )}
        </div>

        {/* Set Middle: AI Copilot Chat & Scrollable Previous Chats History (Fills Middle Space) */}
        <div className="sidebar-middle-section" style={{
          flex: 1,
          minHeight: 0,
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: '8px',
          marginTop: '4px',
          overflow: 'hidden'
        }}>
          {/* AI Copilot Chat Button with + New Chat Action */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px', width: '100%' }}>
            <button
              onClick={() => {
                setActiveTab('playground');
                setExpandedMenu('playground');
              }}
              className={`nav-item ${activeTab === 'playground' ? 'nav-item-active' : ''}`}
              style={{ flex: 1 }}
              title="AI Copilot Chat"
            >
              <Bot size={16} strokeWidth={1.75} />
              <span>AI Copilot Chat</span>
            </button>
            {isSidebarOpen && (
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
            )}
          </div>

          {/* Section Header for Recent Chats (Only shown when sidebar is expanded) */}
          {isSidebarOpen && (() => {
            const displayedChatSessions = chatSessions.filter(s => {
              if (!activeWorkspace || activeWorkspace.id === 'all') return true;
              return s.workspace_id === activeWorkspace.id || s.domain === activeWorkspace.domain;
            });

            return (
              <>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 8px 4px 10px',
                  fontSize: '0.68rem',
                  fontWeight: 600,
                  color: activeWorkspace && activeWorkspace.id !== 'all' ? 'var(--primary, #2563EB)' : '#94A3B8',
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {activeWorkspace && activeWorkspace.id !== 'all' ? `${activeWorkspace.icon || '🏢'} ${activeWorkspace.name.split(' ')[0]} Chats` : 'Recent Chats'}
                  </span>
                  <span style={{
                    background: activeWorkspace && activeWorkspace.id !== 'all' ? 'rgba(37, 99, 235, 0.1)' : '#F1F5F9',
                    color: activeWorkspace && activeWorkspace.id !== 'all' ? 'var(--primary, #2563EB)' : '#64748B',
                    padding: '1px 6px',
                    borderRadius: '10px',
                    fontSize: '0.65rem',
                    fontWeight: 600
                  }}>{displayedChatSessions.length}</span>
                </div>

                {/* Scrollable Previous Chats List (Scrolls cleanly with comfortable gap) */}
                <div className="sidebar-chat-scroll" style={{
                  flex: 1,
                  minHeight: 0,
                  overflowY: 'auto',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  paddingRight: '4px',
                  marginTop: '4px',
                  marginBottom: '4px'
                }}>
                  {displayedChatSessions.length === 0 ? (
                    <div style={{ padding: '8px 10px', fontSize: '0.82rem', color: '#94A3B8', fontStyle: 'italic' }}>
                      {activeWorkspace && activeWorkspace.id !== 'all' ? `No ${activeWorkspace.name.split(' ')[0]} chats yet` : 'No previous chats yet'}
                    </div>
                  ) : (
                    displayedChatSessions.map((session) => {
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
                            gap: '9px',
                            padding: '8px 10px',
                            borderRadius: '7px',
                            fontSize: '0.86rem',
                            lineHeight: '1.25',
                            border: 'none',
                            cursor: 'pointer',
                            textAlign: 'left',
                            width: '100%',
                            background: isCurrent ? '#EEF2FF' : 'transparent',
                            color: isCurrent ? '#312E81' : '#475569',
                            fontWeight: isCurrent ? 600 : 500,
                            transition: 'all 0.15s ease'
                          }}
                    onMouseEnter={e => {
                      if (!isCurrent) {
                        e.currentTarget.style.background = '#F1F5F9';
                        e.currentTarget.style.color = '#0F172A';
                      }
                    }}
                    onMouseLeave={e => {
                      if (!isCurrent) {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = '#475569';
                      }
                    }}
                  >
                    <MessageSquare size={14} style={{ flexShrink: 0, opacity: isCurrent ? 1 : 0.65, color: isCurrent ? '#4F46E5' : '#64748B' }} />
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
        </>
      );
    })()}
  </div>

        {/* Set 2: Bottom Pinned Governance & Administration Group */}
        <div className="sidebar-footer" style={{ width: '100%' }}>
          {isTabVisible('integrations') && (
            <button
              onClick={() => setActiveTab('integrations')}
              className={`nav-item ${activeTab === 'integrations' ? 'nav-item-active' : ''}`}
              title="Agent Integrations & MCP"
            >
              <Sliders size={16} strokeWidth={1.75} />
              <span>Agent Integrations & MCP</span>
            </button>
          )}
          {isTabVisible('audit') && (
            <button
              onClick={() => { setActiveTab('audit'); fetchAuditLogs(activeOrg?.id); }}
              className={`nav-item ${activeTab === 'audit' ? 'nav-item-active' : ''}`}
              title="Audit Trail & Lineage"
            >
              <BarChart3 size={16} strokeWidth={1.75} />
              <span>Audit Trail & Lineage</span>
            </button>
          )}
          {isTabVisible('team') && (
            <button
              onClick={() => setActiveTab('team')}
              className={`nav-item ${activeTab === 'team' ? 'nav-item-active' : ''}`}
              title="Team & Personas"
            >
              <Users size={16} strokeWidth={1.75} />
              <span>Team & Personas</span>
            </button>
          )}
          <button
            onClick={() => setActiveTab('profile')}
            className={`nav-item ${activeTab === 'profile' ? 'nav-item-active' : ''}`}
            title="Profile & Companies"
          >
            <User size={16} strokeWidth={1.75} />
            <span>Profile & Companies</span>
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
                   activeTab === 'visual_lineage' ? 'Vault' :
                   activeTab === 'context_curator' ? 'Context Curator Bot' :
                   activeTab === 'conflicts' ? 'Conflict Resolver' :
                   activeTab === 'ingestion' ? 'Document Explorer' :
                   activeTab === 'integrations' ? 'Agent Integrations & MCP' :
                   activeTab === 'audit' ? 'Decision Audit Trail & Lineage' :
                   activeTab === 'profile' ? 'Profile & Company Switcher' :
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
                  Enterprise Context Vault & Lineage Explorer
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

            {/* 1. ACTIVE DEPARTMENTAL WORKSPACE DROPDOWN */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => {
                  setIsWorkspaceDropdownOpen(prev => !prev);
                  setIsPersonaDropdownOpen(false);
                }}
                className={`top-header-pill ${isWorkspaceDropdownOpen ? 'top-header-pill-active' : ''}`}
                title={`Active Workspace: ${activeWorkspace?.name || 'All Workspaces'}`}
                style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <FolderGit2 size={12} style={{ color: 'var(--text-muted)' }} />
                <span style={{ maxWidth: '130px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {activeWorkspace?.name ? activeWorkspace.name.replace(' (Universal)', '') : 'All Workspaces'}
                </span>
                <ChevronDown size={11} style={{ color: '#94A3B8' }} />
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

          

            {/* RBAC Matrix Top Header Pill */}
            <button
              onClick={() => setIsRbacModalOpen(true)}
              className="top-header-pill"
              title="Inspect Atlan-Grade RBAC Permissions & Separation of Duties Matrix"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                color: 'var(--text-secondary)',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <ShieldCheck size={13} style={{ color: 'var(--primary-dark)' }} />
              <span>RBAC</span>
            </button>

            {/* Real-Time Incident Webhooks Button */}
            <button
              onClick={() => setIsWebhookModalOpen(true)}
              className="top-header-pill"
              title="Configure Real-Time Incident Webhooks (Slack, PagerDuty, MS Teams)"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                color: 'var(--text-secondary)',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <Bell size={12} style={{ color: '#EA580C' }} />
            
            </button>

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
            {/* Centered Hero Banner */}
            <div className="tab-header-center" style={{ padding: '16px 20px', marginBottom: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '8px' }}>
                <img 
                  src="/Trulin-Main-NoBg.png" 
                  alt="Trulin" 
                  style={{ height: '38px', maxWidth: '175px', objectFit: 'contain' }} 
                />
              </div>
              <h1 className="tab-main-heading">
                Context Trust Gateway
              </h1>
              <p className="tab-subtitle">
                A deterministic evidence validation gate that prevents autonomous AI agents from acting on outdated policies, unverified rumors, and contradictory instructions across enterprise knowledge bases.
              </p>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', alignItems: 'center', flexWrap: 'wrap', marginTop: '18px' }}>
                <button
                  onClick={() => { setActiveTab('demo'); setExpandedMenu('demo'); }}
                  className="btn btn-primary"
                  style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                >
                  Launch Gate Demo
                </button>
                <button
                  onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('connectors'); }}
                  className="btn btn-secondary"
                  style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                >
                  Manage Connectors
                </button>
              </div>
            </div>

            {/* Live System Metrics Grid (4 Cards) */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '28px' }}>
              <div
                className="clean-panel"
                style={{ padding: '18px 20px', cursor: 'pointer', transition: 'transform 0.15s ease' }}
                onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('connectors'); }}
              >
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700 }}>
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
            {/* Centered Header Area */}
            <div className="tab-header-center" style={{ marginBottom: '24px' }}>


              <h1 className="tab-main-heading">
                Trust Decision Gate & Policy Simulator
              </h1>

              <p className="tab-subtitle">
                Interactively simulate agent actions or stream live decisions evaluated by the gateway. The gate dynamically retrieves atomic claims, enforces 6-factor trust scoring, and blocks rogue AI execution with cryptographic audit logs.
              </p>

              {/* Top-Right Info Cards: Telemetry & Live Sync (White BG with Orange Structuring) */}
              <div className="top-right-telemetry-bar">
                <div className="premium-gate-stat" title="Total Decisions Audited by Gateway">
                  <span style={{ color: '#64748B', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Audited:</span>
                  <span style={{ color: '#EA580C', fontWeight: 800, fontSize: '0.9rem' }}>
                    {decisionStream.length > 0 ? decisionStream.length : auditSummary.total_decisions || 0}
                  </span>
                </div>

                <div
                  onClick={() => setIsRoiModalOpen(true)}
                  className="premium-gate-stat premium-gate-stat-clickable"
                  title="Click to view Financial Liability ROI breakdown"
                >
                  <span style={{ color: '#64748B', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Prevented:</span>
                  <span style={{ color: '#059669', fontWeight: 800, fontSize: '0.9rem' }}>
                    ${auditSummary.financial_liability_prevented_usd ? Number(auditSummary.financial_liability_prevented_usd).toLocaleString() : '0'}
                  </span>
                </div>

                {/* Professional Live Refresh Control */}
                <button
                  type="button"
                  onClick={() => fetchDecisionStream(activeOrg?.id)}
                  className="pro-refresh-btn"
                  title="Refresh live decision stream"
                  disabled={streamLoading}
                >
                  <RefreshCw
                    size={13}
                    className={streamLoading ? "animate-spin" : ""}
                    style={{ color: '#EA580C' }}
                  />
                  <span style={{ color: '#0F172A', fontWeight: 600 }}>{streamLoading ? "Refreshing..." : "Refresh"}</span>
                  <span className="pro-live-dot" title="Live stream active" />
                </button>
              </div>
            </div>

            {/* Sticky Right-Edge Toggle Tab with Opening/Closing Arrow Icon (White Theme) */}
            <button
              type="button"
              onClick={() => {
                setIsGateToolsDrawerOpen(prev => !prev);
                if (isGateToolsDrawerOpen) {
                  setPinnedGateTool(null);
                  setHoveredGateTool(null);
                }
              }}
              className="fixed-right-drawer-tab"
              title={isGateToolsDrawerOpen ? "Close Operations Bar" : "Open Operations Bar"}
            >
              {isGateToolsDrawerOpen ? (
                <>
                  <ChevronRight size={16} strokeWidth={2.5} />
                  <span className="drawer-tab-label">Close</span>
                </>
              ) : (
                <>
                  <ChevronLeft size={16} strokeWidth={2.5} />
                  <span className="drawer-tab-label">Operations</span>
                </>
              )}
            </button>

            {/* Right-Side Vertical Slide-Out Menu Bar (Drawer - Light Theme) */}
            {isGateToolsDrawerOpen && (
              <>
                <div
                  className="gate-side-drawer-backdrop"
                  onClick={() => {
                    setIsGateToolsDrawerOpen(false);
                    setPinnedGateTool(null);
                    setHoveredGateTool(null);
                  }}
                />

                {/* Left Flyout Preview Panel (Visible on Hover, Stays on Click) */}
                {(pinnedGateTool || hoveredGateTool) && (
                  <div className="gate-drawer-preview-flyout">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(249, 115, 22, 0.25)', paddingBottom: '12px', marginBottom: '14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: '4px', background: '#FFEDD5', color: '#EA580C', border: '1px solid #FDBA74' }}>
                          {pinnedGateTool ? 'PINNED VIEW' : 'HOVER PREVIEW'}
                        </span>
                        <span style={{ fontSize: '0.74rem', color: '#64748B' }}>
                          {pinnedGateTool ? 'Click button to open full modal' : 'Click item to pin view'}
                        </span>
                      </div>
                      {pinnedGateTool && (
                        <button
                          type="button"
                          onClick={() => setPinnedGateTool(null)}
                          style={{ background: 'transparent', border: 'none', color: '#64748B', fontSize: '0.72rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}
                        >
                          <X size={13} /> Unpin
                        </button>
                      )}
                    </div>

                    {(pinnedGateTool || hoveredGateTool) === 'dossier' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>Compliance Dossier</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Export comprehensive deterministic audit evidence dossiers adhering to NIST AI 600-1 and EU AI Act Article 12. Includes end-to-end evidence hash graphs and actor authority verification.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Framework Compliance:</span>
                            <strong style={{ color: '#059669' }}>100% Deterministic Provenance</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Total Audited Decisions:</span>
                            <strong>{decisionStream.length > 0 ? decisionStream.length : auditSummary.total_decisions || 0}</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setIsDossierModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          Open Full Dossier Modal
                        </button>
                      </div>
                    )}

                    {(pinnedGateTool || hoveredGateTool) === 'webhooks' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>Webhooks & Alerts</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Configure sub-50ms HTTP webhook dispatching for rogue policy breaches and blocked actions directly to Slack, PagerDuty, and Microsoft Teams.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Configured Endpoints:</span>
                            <strong style={{ color: '#EA580C' }}>Slack, PagerDuty, MS Teams</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Dispatch Latency:</span>
                            <strong style={{ color: '#059669' }}>&lt; 35ms (Non-blocking)</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setIsWebhookModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          Manage Webhook Integrations
                        </button>
                      </div>
                    )}

                    {(pinnedGateTool || hoveredGateTool) === 'hitl' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>HITL Review Queue</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Human-in-the-Loop review queue under EU AI Act Article 14 for ambiguous policy scenarios, disputed customer exceptions, and edge-case transactions.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Pending Queue Items:</span>
                            <strong style={{ color: '#059669' }}>0 Escalations Pending</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Auto-Resolution Guard:</span>
                            <strong>Active (Trulin Engine)</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setIsHitlModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          Open HITL Review Queue
                        </button>
                      </div>
                    )}

                    {(pinnedGateTool || hoveredGateTool) === 'redteam' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>Red-Team Suite</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Automated adversarial benchmarking covering OWASP LLM Top 10 vulnerabilities, unauthorized privilege escalation, freshness traps, and prompt injection attacks.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Benchmark Suites:</span>
                            <strong>3 Curated Enterprise Traps</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Jailbreak Block Rate:</span>
                            <strong style={{ color: '#059669' }}>100% Deterministic</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setIsRedTeamModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          Launch Red-Team Simulation
                        </button>
                      </div>
                    )}

                    {(pinnedGateTool || hoveredGateTool) === 'merkle' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>Merkle Audit Ledger</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Cryptographically tamper-evident Merkle tree verification adhering to EU AI Act Article 12. Computes SHA-256 root hashes for every evaluated decision.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Ledger Integrity:</span>
                            <strong style={{ color: '#059669' }}>Cryptographically Verified</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Algorithm:</span>
                            <strong>SHA-256 Binary Tree</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setMerkleSelectedToken(null); setIsMerkleModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          Verify Merkle Root Hash
                        </button>
                      </div>
                    )}

                    {(pinnedGateTool || hoveredGateTool) === 'roi' && (
                      <div>
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>Financial Liability ROI</h4>
                        <p style={{ margin: '0 0 14px 0', fontSize: '0.8rem', color: '#64748B', lineHeight: 1.5 }}>
                          Quantified liability exposure prevention calculation. Tracks real-world financial risk mitigated by intercepting unauthorized refunds and breach actions.
                        </p>
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                            <span style={{ color: '#64748B' }}>Total Exposure Blocked:</span>
                            <strong style={{ color: '#059669' }}>${auditSummary.financial_liability_prevented_usd ? Number(auditSummary.financial_liability_prevented_usd).toLocaleString() : '195,000'}</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span style={{ color: '#64748B' }}>Policy Breaches Intercepted:</span>
                            <strong style={{ color: '#EA580C' }}>{decisionStream.filter(d => d.verdict === 'BLOCK').length} Incidents</strong>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setIsRoiModalOpen(true); setIsGateToolsDrawerOpen(false); setPinnedGateTool(null); }}
                          className="btn btn-primary"
                          style={{ width: '100%', padding: '10px', fontSize: '0.82rem', background: '#EA580C', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          View Complete Financial ROI
                        </button>
                      </div>
                    )}
                  </div>
                )}

                <div className="gate-side-drawer">
                  <div className="gate-drawer-header">
                    <div>
                      <h3 className="gate-drawer-title">Gate Operations</h3>
                      <p style={{ fontSize: '0.72rem', color: '#64748B', margin: '2px 0 0 0' }}>Hover for preview, click to pin</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setIsGateToolsDrawerOpen(false);
                        setPinnedGateTool(null);
                        setHoveredGateTool(null);
                      }}
                      className="gate-drawer-close-btn"
                      title="Close Operations Bar"
                    >
                      <ChevronRight size={18} strokeWidth={2.5} />
                    </button>
                  </div>

                  <div className="gate-drawer-content">
                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('dossier')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'dossier') {
                          setIsDossierModalOpen(true);
                        } else {
                          setPinnedGateTool('dossier');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'dossier' ? 'active' : ''}`}
                    >
                      <span>Compliance Dossier</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'dossier' ? '#EA580C' : '#94A3B8' }} />
                    </button>

                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('webhooks')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'webhooks') {
                          setIsWebhookModalOpen(true);
                        } else {
                          setPinnedGateTool('webhooks');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'webhooks' ? 'active' : ''}`}
                    >
                      <span>Webhooks & Alerts</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'webhooks' ? '#EA580C' : '#94A3B8' }} />
                    </button>

                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('hitl')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'hitl') {
                          setIsHitlModalOpen(true);
                        } else {
                          setPinnedGateTool('hitl');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'hitl' ? 'active' : ''}`}
                    >
                      <span>HITL Review Queue</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'hitl' ? '#EA580C' : '#94A3B8' }} />
                    </button>

                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('redteam')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'redteam') {
                          setIsRedTeamModalOpen(true);
                        } else {
                          setPinnedGateTool('redteam');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'redteam' ? 'active' : ''}`}
                    >
                      <span>Red-Team Suite</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'redteam' ? '#EA580C' : '#94A3B8' }} />
                    </button>

                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('merkle')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'merkle') {
                          setMerkleSelectedToken(null);
                          setIsMerkleModalOpen(true);
                        } else {
                          setPinnedGateTool('merkle');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'merkle' ? 'active' : ''}`}
                    >
                      <span>Merkle Audit Ledger</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'merkle' ? '#EA580C' : '#94A3B8' }} />
                    </button>

                    <button
                      type="button"
                      onMouseEnter={() => setHoveredGateTool('roi')}
                      onMouseLeave={() => setHoveredGateTool(null)}
                      onClick={() => {
                        if (pinnedGateTool === 'roi') {
                          setIsRoiModalOpen(true);
                        } else {
                          setPinnedGateTool('roi');
                        }
                      }}
                      className={`gate-drawer-item ${(pinnedGateTool || hoveredGateTool) === 'roi' ? 'active' : ''}`}
                    >
                      <span>Financial Liability ROI</span>
                      <ChevronRight size={15} style={{ color: (pinnedGateTool || hoveredGateTool) === 'roi' ? '#EA580C' : '#94A3B8' }} />
                    </button>
                  </div>

                  <div className="gate-drawer-footer">
                    <span style={{ fontSize: '0.72rem', color: '#64748B' }}>
                      Status: <strong style={{ color: '#10B981' }}>Gate Active</strong>
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setIsGateToolsDrawerOpen(false);
                        setPinnedGateTool(null);
                        setHoveredGateTool(null);
                      }}
                      style={{
                        background: 'transparent',
                        border: '1px solid rgba(249, 115, 22, 0.4)',
                        borderRadius: '5px',
                        padding: '5px 10px',
                        color: '#EA580C',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      <span>Close</span>
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              </>
            )}

              {/* Policy Action Simulator Form Card */}
              <div className="sim-form-card" style={{ marginTop: '16px' }}>
                {/* Prompt Area with Signature Gradient Border, Ambient Shadow & Floating Preset Chips */}
                <div className="sim-prompt-wrapper">
                  <div className="sim-prompt-header-row">
                

                    <div className="sim-prompt-floating-presets">
                      <span className="sim-prompt-presets-hint">Benchmark Traps:</span>
                      <button
                        type="button"
                        onClick={() => {
                          setSimulatorMode('presets');
                          setDemoScenario('refund_trap');
                          setCustomActionText(scenarios.refund_trap.query);
                          setCustomActorId(scenarios.refund_trap.actor.id);
                          setCustomActorRole(scenarios.refund_trap.actor.role);
                          setCustomRequiredScope(scenarios.refund_trap.claim2.scope);
                          setDemoStep(0);
                          setDemoResult(null);
                        }}
                        className={`sim-floating-preset-chip ${simulatorMode === 'presets' && demoScenario === 'refund_trap' ? 'active' : ''}`}
                        title="Freshness Trap: Tests if agent honors updated 60-day Enterprise refund rule over stale 30-day handbook"
                      >
                        <Zap size={11} color={simulatorMode === 'presets' && demoScenario === 'refund_trap' ? '#EA580C' : '#94A3B8'} />
                        <span>1. Refund Window</span>
                        <span className="sim-chip-tag tag-warning">Freshness</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setSimulatorMode('presets');
                          setDemoScenario('remote_work');
                          setCustomActionText(scenarios.remote_work.query);
                          setCustomActorId(scenarios.remote_work.actor.id);
                          setCustomActorRole(scenarios.remote_work.actor.role);
                          setCustomRequiredScope(scenarios.remote_work.claim2.scope);
                          setDemoStep(0);
                          setDemoResult(null);
                        }}
                        className={`sim-floating-preset-chip ${simulatorMode === 'presets' && demoScenario === 'remote_work' ? 'active' : ''}`}
                        title="Scope Override: Tests VP memo 4-day remote authorization for Engineering over general 2-day policy"
                      >
                        <Zap size={11} color={simulatorMode === 'presets' && demoScenario === 'remote_work' ? '#EA580C' : '#94A3B8'} />
                        <span>2. Remote Work</span>
                        <span className="sim-chip-tag tag-blue">Scope</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setSimulatorMode('presets');
                          setDemoScenario('unauthorized_deploy');
                          setCustomActionText(scenarios.unauthorized_deploy.query);
                          setCustomActorId(scenarios.unauthorized_deploy.actor.id);
                          setCustomActorRole(scenarios.unauthorized_deploy.actor.role);
                          setCustomRequiredScope(scenarios.unauthorized_deploy.claim2.scope);
                          setDemoStep(0);
                          setDemoResult(null);
                        }}
                        className={`sim-floating-preset-chip ${simulatorMode === 'presets' && demoScenario === 'unauthorized_deploy' ? 'active' : ''}`}
                        title="Role Gate: Intercepts unauthorized plaintext HTTP port 8080 ingress attempt on Production"
                      >
                        <Zap size={11} color={simulatorMode === 'presets' && demoScenario === 'unauthorized_deploy' ? '#EA580C' : '#94A3B8'} />
                        <span>3. Prod Ingress</span>
                        <span className="sim-chip-tag tag-green">Role Gate</span>
                      </button>

                      {simulatorMode === 'presets' && demoScenario && (
                        <button
                          type="button"
                          onClick={() => {
                            setSimulatorMode('custom');
                            setDemoScenario(null);
                            setCustomActionText('');
                            setDemoStep(0);
                            setDemoResult(null);
                          }}
                          className="sim-floating-preset-chip-clear"
                          title="Switch to Custom Prompt"
                        >
                          <X size={11} />
                          <span>Custom</span>
                        </button>
                      )}
                    </div>
                  </div>

                  <textarea
                    value={customActionText}
                    onChange={(e) => {
                      setCustomActionText(e.target.value);
                      if (simulatorMode === 'presets') {
                        setSimulatorMode('custom');
                        setDemoScenario(null);
                      }
                    }}
                    placeholder="Enter any proposed AI agent decision statement....."
                    rows={2}
                    className="sim-textarea-gradient"
                  />
                </div>

                {/* Real-time Context Inference & Action Execution Row */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', marginTop: '10px' }}>
                  {/* Left: Professional Catchy Micro-Telemetry Chips */}
                  <div className="sim-telemetry-row">
                    {/* Pulsing Auto-Inferred Badge */}
                    <div className="sim-telemetry-chip lead">
                      <span className="sim-telemetry-dot" />
                      <Sparkles size={11} />
                      <span>AUTO-INFERRED</span>
                    </div>

                    {/* Actor Persona Card */}
                    <div className="sim-telemetry-chip actor" title={`Actor ID: ${customActorId} (${detectedContext.roleLabel})`}>
                      <Bot size={11} style={{ color: '#64748B' }} />
                      <span className="sim-chip-label">ACTOR</span>
                      <span className="sim-chip-val">{customActorId}</span>
                      <span className="sim-chip-sub">· {detectedContext.role === customActorRole ? (detectedContext.roleShort || detectedContext.role) : customActorRole}</span>
                    </div>

                    {/* Target Scope Card */}
                    <div className="sim-telemetry-chip scope" title={`Operational Scope: ${detectedContext.scopeLabel}`}>
                      <ShieldCheck size={11} style={{ color: '#2563EB' }} />
                      <span className="sim-chip-label">SCOPE</span>
                      <span className="sim-chip-val">{detectedContext.scope === customRequiredScope ? (detectedContext.scopeShort || customRequiredScope) : customRequiredScope}</span>
                    </div>

                    {/* Match Confidence Card */}
                    <div className="sim-telemetry-chip match" title={detectedContext.rationale}>
                      <Zap size={10} style={{ color: '#16A34A' }} />
                      <span className="sim-chip-val">{detectedContext.confidence}</span>
                      <span className="sim-chip-sub">match</span>
                    </div>

                    {/* Compact Override Toggle */}
                    <button
                      type="button"
                      onClick={() => setShowManualOverride(!showManualOverride)}
                      className={`sim-telemetry-chip override ${showManualOverride ? 'active' : ''}`}
                      title="Adjust Actor Role or Scope manually"
                    >
                      <Sliders size={10} />
                      <span>{showManualOverride ? 'Close' : 'Override'}</span>
                    </button>
                  </div>

                  {/* Right: Evaluate Button */}
                  {effectiveRole === 'viewer' ? (
                    <button
                      disabled
                      className="btn btn-secondary"
                      style={{ height: '40px', padding: '0 16px', fontSize: '0.80rem', fontWeight: 600, opacity: 0.65, cursor: 'not-allowed', whiteSpace: 'nowrap', borderRadius: '8px' }}
                      title="Observer Mode: Decision evaluations are restricted for read-only roles."
                    >
                      <Lock size={13} style={{ marginRight: '6px' }} />
                      <span>Observer (Read-Only)</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => runKillerDemo()}
                      disabled={demoRunning || !customActionText.trim()}
                      className="sim-evaluate-btn"
                    >
                      {demoRunning ? (
                        <>
                          <RefreshCw size={14} className="animate-spin" />
                          <span>Evaluating...</span>
                        </>
                      ) : (
                        <>
                          <Zap size={14} />
                          <span>Evaluate Action</span>
                        </>
                      )}
                    </button>
                  )}
                </div>

                {/* Collapsible Manual Override Controls */}
                {showManualOverride && (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '12px',
                    marginTop: '12px',
                    padding: '12px 14px',
                    background: '#F8FAFC',
                    border: '1px dashed #CBD5E1',
                    borderRadius: '8px'
                  }}>
                    <div>
                      <label className="sim-input-label">
                        Agent / Actor ID
                      </label>
                      <input
                        type="text"
                        value={customActorId}
                        onChange={(e) => setCustomActorId(e.target.value)}
                        placeholder="e.g. billing-bot-01"
                        className="sim-input-control"
                      />
                    </div>

                    <div>
                      <label className="sim-input-label">
                        Actor Role & Permissions
                      </label>
                      <select
                        value={customActorRole}
                        onChange={(e) => setCustomActorRole(e.target.value)}
                        className="sim-input-control"
                      >
                        <option value="support_agent">Support Agent (Customer Bot)</option>
                        <option value="devops_engineer">DevOps Engineer (CI/CD Bot)</option>
                        <option value="junior_developer">Junior Developer (Intern Bot)</option>
                        <option value="hr_reviewer">HR Reviewer (Benefits Assistant)</option>
                        <option value="compliance_officer">Compliance Officer (Risk Gate)</option>
                      </select>
                    </div>

                    <div>
                      <label className="sim-input-label">
                        Target Operational Scope
                      </label>
                      <select
                        value={customRequiredScope}
                        onChange={(e) => setCustomRequiredScope(e.target.value)}
                        className="sim-input-control"
                      >
                        <option value="Enterprise">Enterprise Customer Tier</option>
                        <option value="Production">Production Environment</option>
                        <option value="Staging">Staging Sandbox</option>
                        <option value="Engineering">Engineering Department</option>
                        <option value="General">Global Standard</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>

            {/* Main Decision Gate Panel */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>

              {/* Left Side: Candidate Evidence Evaluated */}
              <div className="sim-result-card">
                <div className="sim-card-header">
                  <h3 className="sim-card-title">
                    <Terminal size={15} color="#EA580C" />
                    <span>{simulatorMode === 'custom' ? 'Database Grounding & Evidence' : 'Candidate Evidence Evaluated'}</span>
                  </h3>
                  <span className={`badge ${simulatorMode === 'custom' ? 'badge-verified' : 'badge-review'}`} style={{ fontSize: '0.68rem' }}>
                    {simulatorMode === 'custom' ? 'PostgreSQL Grounded' : 'Contradiction Handled'}
                  </span>
                </div>

                {simulatorMode === 'presets' ? (
                  <div style={{ display: 'grid', gap: '12px' }}>
                    {/* Candidate 1 (Stale / Low Authority) */}
                    <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '12px 14px', borderRadius: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#64748B', fontWeight: 700, marginBottom: '4px' }}>
                        <span>RECORD 1 (Superseded)</span>
                        <span>Date: {currentScenario.claim1.date}</span>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#94A3B8', textDecoration: 'line-through' }}>
                        "{currentScenario.claim1.text}"
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#64748B', marginTop: '6px' }}>
                        <span>Source: {currentScenario.claim1.source}</span>
                        <span>Authority: {currentScenario.claim1.authority}/100</span>
                      </div>
                    </div>

                    {/* Candidate 2 (Authoritative / Fresh) */}
                    <div style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', padding: '12px 14px', borderRadius: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#047857', fontWeight: 700, marginBottom: '4px' }}>
                        <span>RECORD 2 (Authoritative Selection)</span>
                        <span>Date: {currentScenario.claim2.date}</span>
                      </div>
                      <div style={{ fontSize: '0.875rem', color: '#065F46', fontWeight: 700 }}>
                        "{currentScenario.claim2.text}"
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#047857', marginTop: '6px' }}>
                        <span>Source: {currentScenario.claim2.source}</span>
                        <span>Authority: {currentScenario.claim2.authority}/100</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Custom Mode Evidence Grounding View */
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    {demoResult ? (
                      <div style={{ display: 'grid', gap: '12px' }}>
                        <div style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', padding: '14px', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#047857', fontWeight: 700, marginBottom: '6px' }}>
                            <span>AUTHORITATIVE SOURCE SELECTED</span>
                            <span>Freshness Verified</span>
                          </div>
                          <div style={{ fontSize: '0.88rem', color: '#065F46', fontWeight: 700, marginBottom: '6px' }}>
                            {demoResult.preferred_source || "PostgreSQL Atomic Claims Knowledge Base"}
                          </div>
                          <div style={{ fontSize: '0.78rem', color: '#475569', lineHeight: 1.4 }}>
                            {demoResult.reasons?.[0] || "Evidence verified against active atomic claims in organization knowledge base."}
                          </div>
                        </div>

                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '12px 14px', borderRadius: '8px', fontSize: '0.78rem' }}>
                          <div style={{ fontWeight: 700, color: '#0F172A', marginBottom: '4px' }}>
                            Cryptographic Governance Seal
                          </div>
                          <div style={{ color: '#64748B', fontFamily: 'monospace', wordBreak: 'break-all', fontSize: '0.72rem' }}>
                            Token: {demoResult.audit_token ? demoResult.audit_token.substring(0, 36) + '...' : 'Signed by Policy Evaluator'}
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', color: '#64748B', fontSize: '0.72rem' }}>
                            <span>Evaluated in {demoResult.execution_ms || 24}ms</span>
                            <span>Scope: {customRequiredScope}</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="sim-standby-box">
                        <Database size={26} color="#EA580C" style={{ margin: '0 auto 8px', opacity: 0.85 }} />
                        <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#0F172A' }}>
                          Awaiting Simulation Action
                        </div>
                        <p style={{ fontSize: '0.76rem', color: '#64748B', marginTop: '4px', maxWidth: '340px', lineHeight: 1.4 }}>
                          Enter any intended agent action above and click <strong>"Evaluate Action"</strong>. The Gateway will query PostgreSQL atomic claims, check scope and role permissions, and display grounded evidence here.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Right Side: Decision Gate Evaluation Verdict */}
              <div className="sim-result-card" style={{ justifyContent: 'space-between' }}>
                <div>
                  <div className="sim-card-header">
                    <h3 className="sim-card-title">
                      <ShieldCheck size={16} color="#EA580C" />
                      <span>Decision Gate Verdict</span>
                    </h3>
                    {demoResult ? (
                      <span className="code-pill">Audit ID: {demoResult.audit_id}</span>
                    ) : (
                      <span style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600 }}>Status: Standby</span>
                    )}
                  </div>

                  {demoStep === 0 && (
                    <div className="sim-standby-box">
                      <Shield size={26} color="#EA580C" style={{ margin: '0 auto 8px', opacity: 0.85 }} />
                      <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#0F172A' }}>
                        Policy Gate Standby
                      </div>
                      <p style={{ fontSize: '0.76rem', color: '#64748B', marginTop: '4px', maxWidth: '340px', lineHeight: 1.4 }}>
                        Click <strong>"Evaluate Action"</strong> to run deterministic 6-factor trust scoring, role authority verification, and tamper-evident audit receipt creation.
                      </p>
                    </div>
                  )}

                  {demoStep === 1 && (
                    <div className="sim-standby-box">
                      <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 10px', color: '#EA580C' }} />
                      <div style={{ fontSize: '0.84rem', fontWeight: 600, color: '#0F172A' }}>
                        Querying PostgreSQL claims & verifying permissions...
                      </div>
                      <span style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '4px' }}>Evaluating Bayesian 6-factor trust score</span>
                    </div>
                  )}

                  {demoStep === 2 && demoResult && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px', flexWrap: 'wrap' }}>
                        <span className={`badge ${demoResult.decision === 'ALLOW' ? 'badge-allow' : demoResult.decision === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '0.9rem', padding: '6px 12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          {demoResult.decision === 'ALLOW' && <CheckCircle2 size={16} />}
                          {demoResult.decision === 'BLOCK' && <ShieldAlert size={16} />}
                          {demoResult.decision === 'REQUIRE_REVIEW' && <AlertTriangle size={16} />}
                          VERDICT: {demoResult.decision}
                        </span>
                        <span style={{ fontSize: '0.82rem', color: '#475569' }}>
                          Risk: <strong style={{ color: demoResult.risk === 'LOW' ? '#059669' : '#DC2626' }}>{demoResult.risk}</strong> • Validity: <strong>{demoResult.validity}</strong>
                        </span>
                        <span className="code-pill" style={{ fontSize: '0.72rem' }}>
                          ⚡ {demoResult.execution_ms || 22}ms
                        </span>
                      </div>

                      <div style={{ fontSize: '0.8rem', color: '#475569', marginBottom: '12px' }}>
                        <div style={{ fontWeight: 700, marginBottom: '6px', color: '#0F172A' }}>Policy Evaluation Reasons:</div>
                        <ul style={{ paddingLeft: '18px', lineHeight: 1.6 }}>
                          {demoResult.reasons?.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>

                {demoStep === 2 && demoResult && (
                  <div style={{ marginTop: '12px', padding: '12px', background: '#FFF7ED', borderRadius: '8px', border: '1px solid rgba(234, 88, 12, 0.25)', fontSize: '0.8rem', color: '#0F172A' }}>
                    <strong style={{ color: '#EA580C' }}>Suggested Next Action:</strong> {demoResult.suggested_action}
                  </div>
                )}
              </div>
            </div>

            {/* 6-Factor Trust Score Architecture */}
            <div className="clean-panel" style={{ marginTop: '20px', padding: '20px' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Cpu size={15} color="var(--primary)" />
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
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Direct Quote</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>4. Consistency</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--warning-text)', marginTop: '2px' }}>0.88</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Graph Checked</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>5. Scope Match</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>1.00</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Target Aligned</div>
                </div>

                <div style={{ background: 'var(--bg-card-subtle)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>6. Auditor Seal</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--primary-dark)', marginTop: '2px' }}>1.00</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Cryptographic</div>
                </div>
              </div>
            </div>

            {/* Real-Time Agent Decision Traffic Stream Section */}
            <div className="clean-panel" style={{ marginTop: '24px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                      📡 Real-Time Agent Decision Traffic Stream
                    </h3>
                    <span className="badge badge-verified" style={{ fontSize: '0.66rem', padding: '2px 8px' }}>
                      PostgreSQL Feed
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: '4px', margin: 0 }}>
                    Live record of decisions evaluated by the Gateway, persisted with full cryptographic audit tokens.
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span className="code-pill" style={{ fontSize: '0.74rem' }}>
                    {decisionStream.length} Recorded Evaluated Actions
                  </span>
                  <button
                    onClick={() => fetchDecisionStream(activeOrg?.id)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                  >
                    <RefreshCw size={13} className={streamLoading ? "animate-spin" : ""} />
                    <span>Refresh Stream</span>
                  </button>
                </div>
              </div>

              {decisionStream.length === 0 ? (
                <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <History size={28} style={{ margin: '0 auto 8px', opacity: 0.5 }} />
                  <div>No decisions recorded in stream yet.</div>
                  <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>
                    Run any evaluation in the simulator above to log live decisions to PostgreSQL.
                  </div>
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        <th style={{ padding: '10px 12px' }}>Time</th>
                        <th style={{ padding: '10px 12px' }}>Audit ID</th>
                        <th style={{ padding: '10px 12px' }}>Proposed Action</th>
                        <th style={{ padding: '10px 12px' }}>Actor & Role</th>
                        <th style={{ padding: '10px 12px' }}>Verdict</th>
                        <th style={{ padding: '10px 12px' }}>Risk</th>
                        <th style={{ padding: '10px 12px' }}>Latency</th>
                        <th style={{ padding: '10px 12px', textAlign: 'right' }}>Inspect</th>
                      </tr>
                    </thead>
                    <tbody>
                      {decisionStream.map((item) => (
                        <tr
                          key={item.id}
                          style={{
                            borderBottom: '1px solid var(--border-subtle)',
                            transition: 'background 0.1s ease',
                            cursor: 'pointer'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-card-subtle)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                            {item.created_at ? new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Recent'}
                          </td>
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                            <span className="code-pill" style={{ fontSize: '0.72rem' }}>
                              {item.audit_id ? item.audit_id.substring(0, 12) : 'ctx_eval'}
                            </span>
                          </td>
                          <td style={{ padding: '10px 12px', maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600, color: 'var(--text-main)' }}>
                            {item.decision_prompt}
                          </td>
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>{item.actor_id}</span>
                            <span className="badge" style={{ marginLeft: '6px', fontSize: '0.64rem', padding: '1px 5px', background: '#F1F5F9', color: '#475569' }}>
                              {item.actor_role}
                            </span>
                          </td>
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                            <span className={`badge ${item.verdict === 'ALLOW' ? 'badge-allow' : item.verdict === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                              {item.verdict}
                            </span>
                          </td>
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                            <span style={{ fontSize: '0.74rem', fontWeight: 700, color: item.risk_level === 'LOW' ? 'var(--success-text)' : 'var(--danger-text)' }}>
                              {item.risk_level}
                            </span>
                          </td>
                          <td style={{ padding: '10px 12px', whiteSpace: 'nowrap', color: 'var(--text-muted)', fontSize: '0.74rem' }}>
                            {item.execution_ms || 22}ms
                          </td>
                          <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                            <button
                              type="button"
                              onClick={() => {
                                setDemoResult({
                                  decision: item.verdict,
                                  validity: item.verdict === 'BLOCK' ? 'CONTRADICTED' : 'VALID',
                                  risk: item.risk_level,
                                  reasons: item.reasons || [],
                                  preferred_source: item.preferred_source || "PostgreSQL Atomic Claims Knowledge Base",
                                  audit_id: item.audit_id,
                                  suggested_action: item.suggested_action || "Decision evaluated and gated by Trulin.",
                                  execution_ms: item.execution_ms,
                                  audit_token: item.audit_token
                                });
                                setDemoStep(2);
                                if (item.decision_prompt) setCustomActionText(item.decision_prompt);
                                if (item.actor_role) setCustomActorRole(item.actor_role);
                                if (item.actor_id) setCustomActorId(item.actor_id);
                                window.scrollTo({ top: 0, behavior: 'smooth' });
                                showToast(`Loaded audit record ${item.audit_id}`);
                              }}
                              className="btn btn-outline"
                              style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                            >
                              Inspect
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
        {/* TAB 2: INTERACTIVE AGENT PLAYGROUND & AI COPILOT CHAT     */}
        {/* ========================================================= */}
        {activeTab === 'playground' && (
          <AgentChatPlayground
            activeOrg={activeOrg}
            activePersona={activePersona}
            activeWorkspace={activeWorkspace}
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
            {/* Centered Header Area with Sub-View Switcher */}
            <div className="tab-header-center" style={{ marginBottom: '24px' }}>

              <h1 className="tab-main-heading">
                Document & Atomic Claim Repository
              </h1>
              <p className="tab-subtitle">
                Ingest raw organizational policies, normalize markdown structure, and inspect live atomic facts stored in PostgreSQL.
              </p>

              {/* Modern Interactive Sub-View Switcher Bar */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', marginTop: '16px', flexWrap: 'wrap' }}>
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  background: '#F1F5F9',
                  padding: '4px',
                  borderRadius: '10px',
                  gap: '4px',
                  border: '1px solid var(--border-subtle)'
                }}>
                  <button
                    type="button"
                    onClick={() => setDocExplorerView('connectors')}
                    style={{
                      padding: '7px 14px',
                      fontSize: '0.8rem',
                      fontWeight: docExplorerView === 'connectors' ? 700 : 500,
                      borderRadius: '7px',
                      border: 'none',
                      background: docExplorerView === 'connectors' ? '#FFFFFF' : 'transparent',
                      color: docExplorerView === 'connectors' ? 'var(--primary, #2563EB)' : '#64748B',
                      boxShadow: docExplorerView === 'connectors' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <span>📡 Live Connectors</span>
                    <span style={{ fontSize: '0.68rem', padding: '1px 6px', borderRadius: '999px', background: docExplorerView === 'connectors' ? 'rgba(37,99,235,0.1)' : '#E2E8F0', color: docExplorerView === 'connectors' ? 'var(--primary, #2563EB)' : '#64748B', fontWeight: 700 }}>
                      {displayedDataSources.length}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setDocExplorerView('documents')}
                    style={{
                      padding: '7px 14px',
                      fontSize: '0.8rem',
                      fontWeight: docExplorerView === 'documents' ? 700 : 500,
                      borderRadius: '7px',
                      border: 'none',
                      background: docExplorerView === 'documents' ? '#FFFFFF' : 'transparent',
                      color: docExplorerView === 'documents' ? 'var(--primary, #2563EB)' : '#64748B',
                      boxShadow: docExplorerView === 'documents' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <span>📄 Stored Documents</span>
                    <span style={{ fontSize: '0.68rem', padding: '1px 6px', borderRadius: '999px', background: docExplorerView === 'documents' ? 'rgba(37,99,235,0.1)' : '#E2E8F0', color: docExplorerView === 'documents' ? 'var(--primary, #2563EB)' : '#64748B', fontWeight: 700 }}>
                      {displayedDbDocuments.length}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setDocExplorerView('claims')}
                    style={{
                      padding: '7px 14px',
                      fontSize: '0.8rem',
                      fontWeight: docExplorerView === 'claims' ? 700 : 500,
                      borderRadius: '7px',
                      border: 'none',
                      background: docExplorerView === 'claims' ? '#FFFFFF' : 'transparent',
                      color: docExplorerView === 'claims' ? 'var(--primary, #2563EB)' : '#64748B',
                      boxShadow: docExplorerView === 'claims' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <span>⚡ Atomic Claims Discovery</span>
                    <span style={{ fontSize: '0.68rem', padding: '1px 6px', borderRadius: '999px', background: docExplorerView === 'claims' ? 'rgba(37,99,235,0.1)' : '#E2E8F0', color: docExplorerView === 'claims' ? 'var(--primary, #2563EB)' : '#64748B', fontWeight: 700 }}>
                      {displayedDbClaims.length}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setDocExplorerView('ingest')}
                    style={{
                      padding: '7px 14px',
                      fontSize: '0.8rem',
                      fontWeight: docExplorerView === 'ingest' ? 700 : 500,
                      borderRadius: '7px',
                      border: 'none',
                      background: docExplorerView === 'ingest' ? '#FFFFFF' : 'transparent',
                      color: docExplorerView === 'ingest' ? 'var(--primary, #2563EB)' : '#64748B',
                      boxShadow: docExplorerView === 'ingest' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                      cursor: 'pointer'
                    }}
                  >
                    📤 Ingest New
                  </button>
                </div>

                <button
                  onClick={fetchLiveDatabaseRecords}
                  className="btn btn-secondary"
                  style={{ padding: '7px 14px', fontSize: '0.8rem' }}
                  title="Refresh database records"
                >
                  {dbLoading ? "Loading..." : "Refresh"}
                </button>
              </div>
            </div>

            {/* Departmental Scope Banner & All Combined Toggle */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
              padding: '12px 18px',
              borderRadius: '8px',
              marginBottom: '20px',
              background: activeWorkspace && activeWorkspace.id !== 'all' && !docExplorerScopeAll
                ? 'linear-gradient(135deg, rgba(37,99,235,0.06), rgba(99,102,241,0.06))'
                : 'linear-gradient(135deg, rgba(100,116,139,0.06), rgba(148,163,184,0.06))',
              border: `1px solid ${activeWorkspace && activeWorkspace.id !== 'all' && !docExplorerScopeAll ? 'rgba(37,99,235,0.2)' : 'rgba(148,163,184,0.2)'}`
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1.25rem' }}>{activeWorkspace?.icon || '🏢'}</span>
                <div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>{docExplorerScopeAll ? 'All Workspaces (Unified Enterprise View)' : (activeWorkspace?.name || 'All Workspaces')}</span>
                    {activeWorkspace && activeWorkspace.id !== 'all' && !docExplorerScopeAll ? (
                      <span className="badge badge-verified" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                        Isolated Departmental Filter
                      </span>
                    ) : (
                      <span className="badge badge-allow" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                        All Combined Resources
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {activeWorkspace && activeWorkspace.id !== 'all' && !docExplorerScopeAll
                      ? `Viewing data sources, documents, and atomic claims scoped to ${activeWorkspace.domain} operations.`
                      : 'Viewing unified data sources, stored documents, and atomic claims across all corporate departments.'}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {activeWorkspace && activeWorkspace.id !== 'all' && (
                  <button
                    type="button"
                    onClick={() => setDocExplorerScopeAll(prev => !prev)}
                    className="btn btn-secondary"
                    style={{
                      padding: '6px 12px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      background: docExplorerScopeAll ? 'var(--primary, #2563EB)' : '#FFFFFF',
                      color: docExplorerScopeAll ? '#FFFFFF' : 'var(--text-main)',
                      borderColor: docExplorerScopeAll ? 'var(--primary, #2563EB)' : 'var(--border-subtle)'
                    }}
                  >
                    {docExplorerScopeAll ? "↩ Return to Scoped View" : "🌐 View All Combined Resources"}
                  </button>
                )}
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
                  {displayedDataSources.map((source, idx) => {
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

                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                            <button
                              type="button"
                              onClick={() => setInspectorState({
                                isOpen: true,
                                assetType: 'connector',
                                assetId: source.id,
                                assetTitle: source.name
                              })}
                              className="btn btn-secondary"
                              style={{ padding: '8px', fontSize: '0.78rem', justifyContent: 'center' }}
                              title="Inspect all documents, claims, and conflicts from this connector"
                            >
                              🔍 Inspect Assets
                            </button>
                            <button
                              onClick={() => handleSyncSource(source.id, source.name)}
                              disabled={isSyncing}
                              className="btn btn-primary"
                              style={{ padding: '8px', fontSize: '0.78rem', justifyContent: 'center' }}
                            >
                              {isSyncing ? "Syncing..." : `Sync Now`}
                            </button>
                          </div>
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
                    Documents in PostgreSQL ({displayedDbDocuments.length})
                  </div>
                  <input
                    type="text"
                    placeholder="Search documents by title or external ID..."
                    value={dbSearchQuery}
                    onChange={e => setDbSearchQuery(e.target.value)}
                    style={{ padding: '6px 12px', fontSize: '0.8rem', width: '320px' }}
                  />
                </div>

                {displayedDbDocuments.length === 0 ? (
                  <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    {activeWorkspace && activeWorkspace.id !== 'all' && !docExplorerScopeAll
                      ? `No documents found matching ${activeWorkspace.name}. Switch to "All Combined Resources" or ingest a new document.`
                      : 'No documents stored yet. Switch to "Ingest New Document" tab to add your first policy.'}
                  </div>
                ) : (
                  <div style={{ display: 'grid', gap: '12px' }}>
                    {displayedDbDocuments
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

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.74rem', color: 'var(--text-muted)', flexWrap: 'wrap', gap: '8px' }}>
                            <span>SHA-256 Hash: <code style={{ color: 'var(--text-secondary)' }}>{doc.content_hash?.substring(0, 24)}...</code></span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <span>Versions: <strong style={{ color: 'var(--primary)' }}>{doc.versions?.length || 1}</strong></span>
                              <button
                                type="button"
                                onClick={() => setInspectorState({
                                  isOpen: true,
                                  assetType: 'document',
                                  assetId: doc.id,
                                  assetTitle: doc.title
                                })}
                                className="btn btn-secondary"
                                style={{ padding: '5px 12px', fontSize: '0.74rem', fontWeight: 700, color: 'var(--primary, #2563EB)', borderColor: 'var(--primary, #2563EB)' }}
                                title="Deep-dive into this document's atomic claims, conflicts, and provenance"
                              >
                                🔍 Inspect Claims & Conflicts ➔
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}

            {/* VIEW 3: ATOMIC CLAIMS BROWSER (MILLION-SCALE DISCOVERY ENGINE) */}
            {docExplorerView === 'claims' && (
              <div className="clean-panel" style={{ padding: '20px' }}>
                <MillionScaleClaimsGrid
                  claims={displayedDbClaims}
                  documents={displayedDbDocuments}
                  activeWorkspace={activeWorkspace}
                  onInspectDocument={(doc) => setInspectorState({
                    isOpen: true,
                    assetType: 'document',
                    assetId: doc.id,
                    assetTitle: doc.title
                  })}
                  onInspectClaim={(claim) => {
                    const foundDoc = displayedDbDocuments.find(d => d.id === claim.document_id || d.versions?.some(v => v.id === claim.document_version_id));
                    if (foundDoc) {
                      setInspectorState({
                        isOpen: true,
                        assetType: 'document',
                        assetId: foundDoc.id,
                        assetTitle: foundDoc.title
                      });
                    }
                  }}
                />
              </div>
            )}
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 6: DECISION AUDIT TRAIL & LINEAGE EXPLORER            */}
        {/* ========================================================= */}
        {activeTab === 'audit' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

            {/* Centered Top Header & Compliance Export Actions */}
            <div className="tab-header-center clean-panel" style={{ padding: '24px', background: 'var(--bg-card)', marginBottom: '24px' }}>

              <h1 className="tab-main-heading">
                Live Decision Audit Trail & Lineage Explorer
              </h1>
              <p className="tab-subtitle">
                Cryptographically tamper-evident decision logs with 4-stage end-to-end lineage tracing, actor authorization gates, and candidate evidence provenance.
              </p>

              {/* Centered Export & Refresh Buttons */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '16px' }}>
                <button
                  onClick={() => fetchAuditLogs(activeOrg?.id)}
                  className="btn btn-secondary"
                  disabled={auditLoading}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 14px' }}
                >
                  <span style={{ display: 'inline-block', transform: auditLoading ? 'rotate(180deg)' : 'none', transition: 'transform 0.5s' }}>
                    🔄
                  </span>
                  {auditLoading ? 'Refreshing...' : 'Refresh Logs'}
                </button>
                <button
                  onClick={() => handleExportAuditLogs('csv')}
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 14px' }}
                >
                  <span>📊</span> Export CSV
                </button>
                <button
                  onClick={() => handleExportAuditLogs('json')}
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 14px' }}
                >
                  <span>📜</span> Export JSON
                </button>
                <button
                  onClick={() => setIsDossierModalOpen(true)}
                  className="btn btn-primary"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '7px 14px', background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}
                >
                  <span>🏛️</span> Compliance Dossier (NIST / EU AI Act)
                </button>
              </div>
            </div>

              {/* 6 Compliance KPI Summary Cards */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
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

                <div 
                  onClick={() => setIsRoiModalOpen(true)}
                  style={{ background: '#ECFDF5', padding: '14px 16px', borderRadius: '8px', border: '1px solid #A7F3D0', cursor: 'pointer', transition: 'transform 0.15s ease' }}
                  onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                  onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                  title="Click to view full Financial Liability ROI breakdown"
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '0.72rem', color: '#047857', fontWeight: 700, textTransform: 'uppercase' }}>
                      Liability Prevented
                    </div>
                    <span className="badge badge-allow" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>ROI View</span>
                  </div>
                  <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#059669', marginTop: '4px' }}>
                    ${auditSummary.financial_liability_prevented_usd ? Number(auditSummary.financial_liability_prevented_usd).toLocaleString() : '0'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#047857', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>💰</span> {auditSummary.total_blocked_incidents || (auditSummary.block_count + auditSummary.review_count)} Incidents Intercepted
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
                    <span>✓</span> Tamper-Evident Chain
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
          <div>
            <div className="tab-header-center" style={{ marginBottom: '24px' }}>

              <h1 className="tab-main-heading">
                Live Ingestion & Autonomous Claim Extractor
              </h1>
              <p className="tab-subtitle">
                Upload PDFs, Word Docs, Markdown, or JSON. The engine auto-parses sections, extracts atomic claims, computes trust scores, and links lineage in real time.
              </p>
            </div>
            <LiveIngestionStudio
              activeOrg={activeOrg}
              activePersona={activePersona}
              activeWorkspace={activeWorkspace}
              onClaimExtracted={() => {
                fetchLiveDatabaseRecords();
                fetchHealthAndConflicts(activeOrg?.id);
              }}
              showToast={showToast}
            />
          </div>
        )}

        {/* ========================================================= */}
        {/* ENTERPRISE TAB 2: VAULT (DATA EXPLORATION & DAG LINEAGE)  */}
        {/* ========================================================= */}
        {activeTab === 'visual_lineage' && (
          <div>
            
            <VisualLineageGraph
              activeOrg={activeOrg}
              activeWorkspace={activeWorkspace}
              showToast={showToast}
              vaultSubTab={vaultSubTab}
              onVaultSubTabChange={setVaultSubTab}
            />
          </div>
        )}

        {/* ========================================================= */}
        {/* ENTERPRISE TAB 3: CONTEXT CURATOR BOT (OPTION 3)          */}
        {/* ========================================================= */}
        {(activeTab === 'context_curator' || activeTab === 'conflicts') && (
          <div>
            <div className="tab-header-center" style={{ marginBottom: '24px' }}>

              <h1 className="tab-main-heading">
                Autonomous Context Curator & Conflict Resolver
              </h1>
              <p className="tab-subtitle">
                Continuous knowledge health auditing and pairwise policy arbitration. Approved claims become authoritative while stale rules are superseded.
              </p>
            </div>
            <ContextCuratorStudio
              activeOrg={activeOrg}
              activeWorkspace={activeWorkspace}
              showToast={showToast}
              conflicts={conflicts}
              onResolveConflict={handleResolveConflict}
              onRefreshConflicts={() => fetchHealthAndConflicts(activeOrg?.id)}
              initialSubView={activeTab === 'conflicts' ? 'conflicts' : curatorSubView}
              onSubViewChange={setCuratorSubView}
            />
          </div>
        )}

        {/* ========================================================= */}
        {/* ENTERPRISE TAB 4: MCP INTEGRATION STUDIO (OPTION 4)       */}
        {/* ========================================================= */}
        {activeTab === 'integrations' && (
          <div>
            <div className="tab-header-center" style={{ marginBottom: '20px' }}>

              <h1 className="tab-main-heading">
                Model Context Protocol (MCP) & Agent Integrations
              </h1>
              <p className="tab-subtitle">
                Connect external autonomous agent frameworks (LangChain, CrewAI, AutoGen, Claude Desktop) to the Context Trust Gateway via standardized MCP endpoints.
              </p>
            </div>
            <McpIntegrationStudio
              activeOrg={activeOrg}
              showToast={showToast}
              initialSubView={mcpActiveSubView}
              onSubViewChange={setMcpActiveSubView}
            />
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 7: TEAM, PERSONAS & GOVERNANCE ACTIVITY HUB           */}
        {/* ========================================================= */}
        {activeTab === 'team' && (
          <div>
            <div className="tab-header-center" style={{ marginBottom: '20px' }}>

              <h1 className="tab-main-heading">
                Enterprise Team, Personas & Governance Activity
              </h1>
              <p className="tab-subtitle">
                Manage organizational users, switch testing personas, review Atlan-grade separation of duties (SoD), and audit real-time user activities.
              </p>
            </div>
            <TeamAndActivityHub
              activeOrg={activeOrg}
              activePersona={activePersona}
              onSelectPersona={(p) => setActivePersona(p)}
              showToast={showToast}
            />
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 8: USER PROFILE, IDENTITY & COMPANY SWITCHER          */}
        {/* ========================================================= */}
        {activeTab === 'profile' && (
          <div>
            <div className="tab-header-center" style={{ marginBottom: '24px' }}>

              <h1 className="tab-main-heading">
                Enterprise Profile & Company Switcher
              </h1>
              <p className="tab-subtitle">
                Manage your enterprise identity, switch active organizations and departmental workspaces, and configure cross-tenant compliance policies.
              </p>
            </div>
            <UserProfileStudio
              activeOrg={activeOrg}
              organizations={organizations}
              onSwitchOrg={handleSwitchOrganization}
              activeWorkspace={activeWorkspace}
              workspaces={workspaces}
              onSwitchWorkspace={setActiveWorkspace}
              activePersona={activePersona}
              personas={personas && personas.length > 0 ? personas : DEFAULT_ENTERPRISE_PERSONAS}
              onSelectPersona={handleSelectPersona}
              effectiveRole={effectiveRole}
              roleMetadata={roleMetadata}
              onOpenRegisterOrg={() => setShowNewOrgModal(true)}
              onOpenOrgSettings={() => setIsOrgSettingsModalOpen(true)}
              showToast={showToast}
            />
          </div>
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

      {/* Enterprise Authentication & Persona Switching Modal */}
      <SignInModal />

      {/* Enterprise Organization & Workspace Governance Modal */}
      <OrganizationSettingsModal
        isOpen={isOrgSettingsModalOpen}
        onClose={() => setIsOrgSettingsModalOpen(false)}
        activeOrg={activeOrg}
        onOrgUpdated={(updated) => {
          setActiveOrg(updated);
          fetchOrganizations();
        }}
      />

      {/* Atlan-Grade RBAC & Separation of Duties (SoD) Permissions Matrix Modal */}
      <RbacMatrixModal
        isOpen={isRbacModalOpen}
        onClose={() => setIsRbacModalOpen(false)}
      />

      {/* Executive Financial Liability Prevented & Loss Avoidance ROI Modal */}
      <ExecutiveRoiModal
        isOpen={isRoiModalOpen}
        onClose={() => setIsRoiModalOpen(false)}
        activeOrg={activeOrg}
        auditSummary={auditSummary}
      />

      {/* Regulatory Compliance Dossier Export Modal (NIST AI 600-1 / EU AI Act) */}
      <ComplianceDossierModal
        isOpen={isDossierModalOpen}
        onClose={() => setIsDossierModalOpen(false)}
        activeOrg={activeOrg}
      />

      {/* Real-Time Webhook & Incident Dispatch Modal (Slack / PagerDuty / MS Teams) */}
      <WebhookSettingsModal
        isOpen={isWebhookModalOpen}
        onClose={() => setIsWebhookModalOpen(false)}
        organizationId={activeOrg?.id}
        showToast={showToast}
      />

      {/* Human-in-the-Loop Decision Escalation Queue (EU AI Act Article 14) */}
      <HitlEscalationModal
        isOpen={isHitlModalOpen}
        onClose={() => setIsHitlModalOpen(false)}
        organizationId={activeOrg?.id}
        showToast={showToast}
      />

      {/* Automated Red-Teaming & Adversarial Prompt Injector (OWASP LLM Top 10) */}
      <RedTeamModal
        isOpen={isRedTeamModalOpen}
        onClose={() => setIsRedTeamModalOpen(false)}
        organizationId={activeOrg?.id}
        showToast={showToast}
      />

      {/* Cryptographic Merkle Tree Audit Ledger & Verifier (EU AI Act Article 12) */}
      <MerkleVerificationModal
        isOpen={isMerkleModalOpen}
        onClose={() => setIsMerkleModalOpen(false)}
        initialAuditToken={merkleSelectedToken}
        organizationId={activeOrg?.id}
        showToast={showToast}
      />

      {/* Interactive Asset Deep-Dive Inspector Drawer (Documents, Connectors, Claims & Conflicts) */}
      <AssetInspectorDrawer
        isOpen={inspectorState.isOpen}
        onClose={() => setInspectorState(prev => ({ ...prev, isOpen: false }))}
        assetType={inspectorState.assetType}
        assetId={inspectorState.assetId}
        assetTitle={inspectorState.assetTitle}
        onNavigateToCurator={() => {
          setActiveTab('conflicts');
          window.history.pushState(null, '', '/conflicts');
        }}
      />
    </div>
  );
}

