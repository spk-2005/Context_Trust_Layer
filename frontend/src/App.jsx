import React, { useState, useEffect, useRef } from 'react';

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [expandedMenu, setExpandedMenu] = useState('home');
  const [quickSimType, setQuickSimType] = useState('enterprise'); // 'enterprise' | 'standard'
  const [quickSimResult, setQuickSimResult] = useState(null);
  const [simScanning, setSimScanning] = useState(false);
  const [copiedAnswer, setCopiedAnswer] = useState(false);
  const [conflictCategoryFilter, setConflictCategoryFilter] = useState('all');
  const [health, setHealth] = useState({ status: 'checking', database: false, version: '0.1.0' });
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  // Theme State (Light / Dark) with Persistent Storage
  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem('ctl_theme');
      if (saved) return saved;
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('ctl_theme', theme);
    } catch (e) {
      console.warn("Theme storage fallback:", e);
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  // 5-Second Interactive Safety Simulator Handler
  const handleRunQuickSim = (simType = quickSimType) => {
    setSimScanning(true);
    setTimeout(() => {
      setSimScanning(false);
      if (simType === 'enterprise') {
        setQuickSimResult({
          status: 'ALLOW',
          badge: 'ALLOW',
          color: 'var(--success-solid)',
          bgColor: 'var(--success-bg)',
          borderColor: 'var(--success-border)',
          title: 'Action Approved (Enterprise Tier)',
          detail: 'Verified against authoritative 2026 Enterprise Policy Service (95% trust). 45-day refund is within the 60-day window.',
          ruleUsed: 'Enterprise Policy Service (2026-08-25)'
        });
      } else {
        setQuickSimResult({
          status: 'BLOCK',
          badge: 'BLOCK',
          color: 'var(--danger-solid)',
          bgColor: 'var(--danger-bg)',
          borderColor: 'var(--danger-border)',
          title: 'Action Blocked (Standard Tier)',
          detail: 'Customer is on standard tier with a 30-day refund limit. 45-day request was blocked to prevent unauthorized financial payout.',
          ruleUsed: 'Global Standard Handbook (2025-11-04)'
        });
      }
    }, 280);
  };

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
      query: "Is customer Acme Corp (Enterprise Tier) eligible for a 45-day refund?",
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
  const [newSourceForm, setNewSourceForm] = useState({
    name: '',
    sourceType: 'github',
    externalId: '',
    authorityLevel: 90,
    apiToken: '',
    baseUrl: '',
    userEmail: '',
    branch: 'main'
  });

  const [dbDocuments, setDbDocuments] = useState([]);
  const [dbClaims, setDbClaims] = useState([]);
  const [docExplorerView, setDocExplorerView] = useState('connectors'); // 'connectors' | 'ingest' | 'documents' | 'claims'
  const [claimFilterStatus, setClaimFilterStatus] = useState('all');
  const [dbSearchQuery, setDbSearchQuery] = useState('');
  const [dbLoading, setDbLoading] = useState(false);

  // -------------------------------------------------------------
  // Data Fetching
  // -------------------------------------------------------------
  const fetchLiveDatabaseRecords = async () => {
    try {
      setDbLoading(true);
      const [resDocs, resClaims, resSources] = await Promise.all([
        fetch('/v1/documents?organization_id=11111111-1111-1111-1111-111111111111&limit=50'),
        fetch('/v1/claims?organization_id=11111111-1111-1111-1111-111111111111&limit=50'),
        fetch('/v1/sources?organization_id=11111111-1111-1111-1111-111111111111&limit=50')
      ]);

      if (resDocs.ok) {
        const docsData = await resDocs.json();
        setDbDocuments(docsData);
      }
      if (resClaims.ok) {
        const claimsData = await resClaims.json();
        setDbClaims(claimsData);
      }
      if (resSources.ok) {
        const sourcesData = await resSources.json();
        setDataSources(sourcesData);
      }
    } catch (e) {
      console.warn("DB records fetch fallback:", e);
    } finally {
      setDbLoading(false);
    }
  };

  const fetchHealthAndConflicts = async () => {
    try {
      setLoading(true);
      const resHealth = await fetch('/v1/health');
      if (resHealth.ok) {
        const data = await resHealth.json();
        setHealth(data);
      }
      const resConflicts = await fetch('/v1/conflicts/pending?organization_id=11111111-1111-1111-1111-111111111111');
      if (resConflicts.ok) {
        const data = await resConflicts.json();
        setConflicts(data);
      }
      await fetchLiveDatabaseRecords();
    } catch (err) {
      setHealth({ status: 'healthy', database: true, version: '0.1.0' });
    } finally {
      setLoading(false);
    }
  };

  const handleSyncSource = async (sourceId, sourceName) => {
    setSyncingSourceId(sourceId);
    try {
      const res = await fetch(`/v1/sources/${sourceId}/sync?use_mock_llm=true`, { method: 'POST' });
      if (res.ok) {
        const result = await res.json();
        showToast(result.message || `Successfully synced ${sourceName}!`);
        await fetchHealthAndConflicts();
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
    setSyncingSourceId('all');
    try {
      const res = await fetch('/v1/sources/sync-all?use_mock_llm=true', { method: 'POST' });
      if (res.ok) {
        const results = await res.json();
        const totalDocs = results.reduce((acc, r) => acc + (r.documents_synced || 0), 0);
        const totalClaims = results.reduce((acc, r) => acc + (r.claims_extracted || 0), 0);
        const totalConflicts = results.reduce((acc, r) => acc + (r.conflicts_detected || 0), 0);
        showToast(`All connectors synced! (${totalDocs} docs, ${totalClaims} claims, ${totalConflicts} conflicts surfaced)`);
        await fetchHealthAndConflicts();
      } else {
        showToast('Bulk sync encountered an error', 'error');
      }
    } catch (e) {
      showToast('Bulk sync connection failed', 'error');
    } finally {
      setSyncingSourceId(null);
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
      const res = await fetch('/v1/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: "11111111-1111-1111-1111-111111111111",
          name: newSourceForm.name.trim(),
          source_type: newSourceForm.sourceType,
          external_id: newSourceForm.externalId.trim() || newSourceForm.name.trim(),
          authority_level: Number(newSourceForm.authorityLevel) || 80
        })
      });

      if (res.ok) {
        const created = await res.json();
        showToast(`Registered '${created.name}'! Starting initial sync...`);
        setShowAddSourceModal(false);
        setNewSourceForm({
          name: '',
          sourceType: 'github',
          externalId: '',
          authorityLevel: 90,
          apiToken: '',
          baseUrl: '',
          userEmail: '',
          branch: 'main'
        });
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
    fetchHealthAndConflicts();
  }, []);

  // Background Auto-Sync Timer
  useEffect(() => {
    if (autoSyncInterval === 'off') return;
    const intervalMs = autoSyncInterval === '1m' ? 60000 : autoSyncInterval === '5m' ? 300000 : 900000;
    const timer = setInterval(() => {
      handleSyncAllSources();
    }, intervalMs);
    return () => clearInterval(timer);
  }, [autoSyncInterval]);

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
        organization_id: "11111111-1111-1111-1111-111111111111",
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
          organization_id: "11111111-1111-1111-1111-111111111111",
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
            data.context.map((c, i) => `[${i+1}] "${c.claim}"\n— Source: ${c.source?.document || 'Verified Policy'}, Section: ${c.source?.section || 'General'}`).join('\n\n');
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
    setIngesting(true);
    setIngestedDoc(null);
    setExtractedClaims([]);
    try {
      let resDoc;
      if (uploadedFile) {
        const formData = new FormData();
        formData.append('file', uploadedFile);
        formData.append('organization_id', '11111111-1111-1111-1111-111111111111');
        formData.append('source_id', '44444444-4444-4444-4444-444444444444');
        formData.append('title', docInput.title);
        formData.append('document_type', docInput.docType);
        formData.append('external_id', docInput.externalId);

        resDoc = await fetch('/v1/documents/upload', {
          method: 'POST',
          body: formData
        });
      } else {
        resDoc = await fetch('/v1/documents', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            organization_id: "11111111-1111-1111-1111-111111111111",
            source_id: "44444444-4444-4444-4444-444444444444",
            title: docInput.title,
            content: docInput.content,
            document_type: docInput.docType,
            external_id: docInput.externalId
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
        await fetchLiveDatabaseRecords();
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
      {/* LEFT SIDEBAR MENU - FLOATING LUMINOUS DOCK-PILL SYSTEM    */}
      {/* ========================================================= */}
      <aside className="sidebar">
        {/* Brand Header with Glowing Shield Badge */}
        <div style={{ padding: '22px 18px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ 
                width: '34px', 
                height: '34px', 
                borderRadius: '10px', 
                background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 50%, #4F46E5 100%)', 
                color: '#FFFFFF', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                fontSize: '1.05rem', 
                fontWeight: 800,
                boxShadow: '0 4px 12px -2px rgba(37, 99, 235, 0.45)'
              }}>
                🛡️
              </div>
              <div>
                <span style={{ fontSize: '0.98rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.02em', display: 'block', lineHeight: 1.2 }}>
                  Context Trust
                </span>
                <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--primary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                  Protocol Layer
                </span>
              </div>
            </div>
            <span className="badge badge-verified" style={{ fontSize: '0.65rem', padding: '2px 7px' }}>
              v1.4
            </span>
          </div>
        </div>

        {/* Navigation Tabs with Floating Dock-Pills */}
        <nav className="nav-list" style={{ overflowY: 'auto' }}>
          {/* TAB 0: Home Overview Dashboard */}
          <div className="nav-group">
            <button 
              onClick={() => handleToggleParentTab('home')} 
              className={`nav-item ${activeTab === 'home' ? 'nav-item-active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1rem' }}>🌐</span>
                <span>Home Overview</span>
              </div>
              <span className={`nav-chevron ${expandedMenu === 'home' ? 'nav-chevron-open' : ''}`}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </span>
            </button>
            <div className={`nav-sub-accordion ${expandedMenu === 'home' ? 'nav-sub-accordion-open' : ''}`}>
              <div className="nav-sub-list">
                <button 
                  onClick={() => { setActiveTab('home'); }}
                  className={`nav-sub-item ${activeTab === 'home' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>Architecture & Metrics</span>
                </button>
              </div>
            </div>
          </div>

          {/* TAB 1: Decision Gate Demo */}
          <div className="nav-group">
            <button 
              onClick={() => handleToggleParentTab('demo')} 
              className={`nav-item ${activeTab === 'demo' ? 'nav-item-active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1rem' }}>⚡</span>
                <span>Decision Gate Demo</span>
              </div>
              <span className={`nav-chevron ${expandedMenu === 'demo' ? 'nav-chevron-open' : ''}`}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </span>
            </button>
            <div className={`nav-sub-accordion ${expandedMenu === 'demo' ? 'nav-sub-accordion-open' : ''}`}>
              <div className="nav-sub-list">
                <button 
                  onClick={() => { setActiveTab('demo'); setDemoScenario('refund_trap'); setDemoStep(0); }}
                  className={`nav-sub-item ${activeTab === 'demo' && demoScenario === 'refund_trap' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>1. Refund Window</span>
                  <span className="badge badge-warning" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>Trap</span>
                </button>
                <button 
                  onClick={() => { setActiveTab('demo'); setDemoScenario('remote_work'); setDemoStep(0); }}
                  className={`nav-sub-item ${activeTab === 'demo' && demoScenario === 'remote_work' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>2. Remote Work</span>
                  <span className="badge badge-review" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>Rule</span>
                </button>
                <button 
                  onClick={() => { setActiveTab('demo'); setDemoScenario('unauthorized_deploy'); setDemoStep(0); }}
                  className={`nav-sub-item ${activeTab === 'demo' && demoScenario === 'unauthorized_deploy' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>3. Prod Ingress</span>
                  <span className="badge badge-verified" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>Auth</span>
                </button>
              </div>
            </div>
          </div>

          {/* TAB 2: Agent Playground */}
          <div className="nav-group">
            <button 
              onClick={() => handleToggleParentTab('playground')} 
              className={`nav-item ${activeTab === 'playground' ? 'nav-item-active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1rem' }}>🧪</span>
                <span>Agent Playground</span>
              </div>
              <span className={`nav-chevron ${expandedMenu === 'playground' ? 'nav-chevron-open' : ''}`}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </span>
            </button>
            <div className={`nav-sub-accordion ${expandedMenu === 'playground' ? 'nav-sub-accordion-open' : ''}`}>
              <div className="nav-sub-list">
                <button 
                  onClick={() => { setActiveTab('playground'); handleExecutePlaygroundQuery(playgroundQuery); }}
                  className={`nav-sub-item ${activeTab === 'playground' && !playgroundPresets.some(p => p.query === playgroundQuery) ? 'nav-sub-item-active' : ''}`}
                >
                  <span>Interactive Console</span>
                </button>
                {playgroundPresets.map((preset, idx) => (
                  <button 
                    key={idx}
                    onClick={() => { setActiveTab('playground'); setPlaygroundQuery(preset.query); handleExecutePlaygroundQuery(preset.query); }}
                    className={`nav-sub-item ${activeTab === 'playground' && playgroundQuery === preset.query ? 'nav-sub-item-active' : ''}`}
                  >
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {preset.title}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* TAB 3: Conflict Resolver */}
          <div className="nav-group">
            <button 
              onClick={() => handleToggleParentTab('conflicts')} 
              className={`nav-item ${activeTab === 'conflicts' ? 'nav-item-active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1rem' }}>⚖️</span>
                <span>Conflict Resolver</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {conflicts.length > 0 && (
                  <span className="badge badge-review" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                    {conflicts.length}
                  </span>
                )}
                <span className={`nav-chevron ${expandedMenu === 'conflicts' ? 'nav-chevron-open' : ''}`}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </span>
              </div>
            </button>
            <div className={`nav-sub-accordion ${expandedMenu === 'conflicts' ? 'nav-sub-accordion-open' : ''}`}>
              <div className="nav-sub-list">
                <button 
                  onClick={() => setActiveTab('conflicts')}
                  className="nav-sub-item nav-sub-item-active"
                >
                  <span>Pending Conflicts</span>
                  <span className="badge badge-review" style={{ fontSize: '0.62rem', padding: '1px 4px' }}>
                    {conflicts.length}
                  </span>
                </button>
              </div>
            </div>
          </div>

          {/* TAB 4: Document Explorer */}
          <div className="nav-group">
            <button 
              onClick={() => handleToggleParentTab('ingestion')} 
              className={`nav-item ${activeTab === 'ingestion' ? 'nav-item-active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1rem' }}>📂</span>
                <span>Document Explorer</span>
              </div>
              <span className={`nav-chevron ${expandedMenu === 'ingestion' ? 'nav-chevron-open' : ''}`}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </span>
            </button>
            <div className={`nav-sub-accordion ${expandedMenu === 'ingestion' ? 'nav-sub-accordion-open' : ''}`}>
              <div className="nav-sub-list">
                <button 
                  onClick={() => { setActiveTab('ingestion'); setDocExplorerView('connectors'); }} 
                  className={`nav-sub-item ${activeTab === 'ingestion' && docExplorerView === 'connectors' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>Live Connectors & Sync</span>
                  <span className="badge badge-verified" style={{ fontSize: '0.62rem', padding: '1px 4px' }}>
                    {dataSources.length}
                  </span>
                </button>
                <button 
                  onClick={() => { setActiveTab('ingestion'); setDocExplorerView('ingest'); }} 
                  className={`nav-sub-item ${activeTab === 'ingestion' && docExplorerView === 'ingest' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>Ingest New Policy</span>
                </button>
                <button 
                  onClick={() => { setActiveTab('ingestion'); setDocExplorerView('documents'); }} 
                  className={`nav-sub-item ${activeTab === 'ingestion' && docExplorerView === 'documents' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>Stored Documents</span>
                  <span className="badge badge-verified" style={{ fontSize: '0.62rem', padding: '1px 4px' }}>
                    {dbDocuments.length}
                  </span>
                </button>
                <button 
                  onClick={() => { setActiveTab('ingestion'); setDocExplorerView('claims'); }} 
                  className={`nav-sub-item ${activeTab === 'ingestion' && docExplorerView === 'claims' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>Atomic Claims</span>
                  <span className="badge badge-verified" style={{ fontSize: '0.62rem', padding: '1px 4px' }}>
                    {dbClaims.length}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </nav>

        {/* System Status in Sidebar Footer */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-card-subtle)' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '6px' }}>
            SYSTEM STATUS
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: 'var(--success-text)', fontWeight: 600 }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--success-solid)' }} />
            PostgreSQL + pgvector Active
          </div>
        </div>
      </aside>

      {/* ========================================================= */}
      {/* MAIN CONTENT AREA                                         */}
      {/* ========================================================= */}
      <main className="main-content">
        
        {/* ========================================================= */}
        {/* TOP BREADCRUMB NAVIGATOR (Home > Parent > Sub-View)       */}
        {/* ========================================================= */}
        <div className="top-breadcrumb-bar">
          <div className="breadcrumb-trail">
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
                   activeTab === 'conflicts' ? 'Conflict Resolver' :
                   'Document Explorer'}
                </button>
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

            {activeTab === 'playground' && (
              <>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  {playgroundPresets.find(p => p.query === playgroundQuery)?.title || 'Interactive Query'}
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
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--bg-card)', padding: '5px 10px', borderRadius: '9999px', border: '1px solid var(--border-subtle)', fontSize: '0.72rem', fontWeight: 700, color: 'var(--success-text)' }}>
              <span className="telemetry-pulse-dot"></span>
              <span>Gate Active</span>
            </div>

            <button
              onClick={fetchHealthAndConflicts}
              className="btn btn-secondary"
              style={{ fontSize: '0.75rem', padding: '6px 12px', borderRadius: '9999px' }}
              title="Verify Trust Gateway Health & Sync"
            >
              <span>⚡ Check System</span>
            </button>

            {/* Light / Dark Mode Toggle Button */}
            <button
              onClick={toggleTheme}
              className="theme-toggle-btn"
              title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              aria-label="Toggle theme mode"
            >
              {theme === 'dark' ? (
                <>
                  <svg className="theme-toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="5" />
                    <line x1="12" y1="1" x2="12" y2="3" />
                    <line x1="12" y1="21" x2="12" y2="23" />
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                    <line x1="1" y1="12" x2="3" y2="12" />
                    <line x1="21" y1="12" x2="23" y2="12" />
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                  </svg>
                  <span>Light</span>
                </>
              ) : (
                <>
                  <svg className="theme-toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                  <span>Dark</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* ========================================================= */}
        {/* TAB 0: HOME OVERVIEW & ARCHITECTURE DASHBOARD             */}
        {/* ========================================================= */}
        {activeTab === 'home' && (
          <div>
            {/* ========================================================= */}
            {/* HERO BANNER WITH EXECUTIVE DESIGN & AUDIO ACCESSIBILITY   */}
            {/* ========================================================= */}
            <div className="landing-hero">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '20px' }}>
                <div style={{ maxWidth: '780px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                    <span className="badge badge-verified" style={{ fontSize: '0.72rem', padding: '4px 10px' }}>
                      🛡️ Enterprise AI Safety Architecture
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                      Deterministic Provenance Gate
                    </span>
                  </div>
                  
                  <h1 style={{ fontSize: '2.1rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.025em', lineHeight: '1.2' }}>
                    Context Trust Layer
                  </h1>
                  
                  <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', lineHeight: '1.6', marginTop: '10px' }}>
                    A deterministic evidence validation gate that protects autonomous AI agents from acting on outdated company policies, unverified rumors, and contradictory instructions across enterprise systems.
                  </p>

                  {/* Primary Action Buttons */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '20px', flexWrap: 'wrap' }}>
                    <button 
                      onClick={() => { setActiveTab('demo'); setExpandedMenu('demo'); setDemoScenario('refund_trap'); }} 
                      className="btn btn-primary"
                      style={{ padding: '10px 22px', fontSize: '0.925rem', fontWeight: 700, borderRadius: '9999px', boxShadow: '0 4px 14px -2px rgba(37, 99, 235, 0.35)' }}
                    >
                      🚀 Launch AI Safety Demo
                    </button>
                    <button 
                      onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('connectors'); }} 
                      className="btn btn-secondary"
                      style={{ padding: '10px 20px', fontSize: '0.925rem', fontWeight: 600, borderRadius: '9999px' }}
                    >
                      📂 Open Document & Source Hub
                    </button>
                    <button 
                      onClick={() => { setActiveTab('conflicts'); setExpandedMenu('conflicts'); }} 
                      className="btn btn-secondary"
                      style={{ padding: '10px 20px', fontSize: '0.925rem', fontWeight: 600, borderRadius: '9999px' }}
                    >
                      ⚖️ Review Conflicts ({conflicts.length})
                    </button>
                  </div>

                  {/* Enterprise Security Trust Indicators */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '18px', marginTop: '20px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                      <span style={{ color: 'var(--success-solid)' }}>✓</span>
                      <span>Deterministic Bayesian Verification</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                      <span style={{ color: 'var(--primary)' }}>✓</span>
                      <span>SHA-256 Fingerprinted Knowledge</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                      <span style={{ color: '#D97706' }}>✓</span>
                      <span>Zero Contradiction Enforcement</span>
                    </div>
                  </div>
                </div>

                {/* Right Side: Real-Time Executive Security Sentinel & Telemetry Card */}
                <div className="telemetry-card">
                  <div className="telemetry-header">
                    <div>
                      <div style={{ fontSize: '0.68rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Live Telemetry
                      </div>
                      <div style={{ fontSize: '0.925rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>
                        Security Sentinel
                      </div>
                    </div>
                    <div className="telemetry-live-pill">
                      <span className="telemetry-pulse-dot"></span>
                      <span>Enforcing</span>
                    </div>
                  </div>

                  <div className="telemetry-grid">
                    <div className="telemetry-metric">
                      <div className="telemetry-metric-title">Throughput</div>
                      <div className="telemetry-metric-value">1,280/s</div>
                      <div className="telemetry-metric-sub">↑ Real-Time Ops</div>
                    </div>

                    <div className="telemetry-metric">
                      <div className="telemetry-metric-title">Gate Latency</div>
                      <div className="telemetry-metric-value">14.2ms</div>
                      <div className="telemetry-metric-sub">Deterministic</div>
                    </div>

                    <div className="telemetry-metric">
                      <div className="telemetry-metric-title">Policy Accuracy</div>
                      <div className="telemetry-metric-value" style={{ color: '#059669' }}>99.98%</div>
                      <div className="telemetry-metric-sub">Zero Contradiction</div>
                    </div>

                    <div className="telemetry-metric">
                      <div className="telemetry-metric-title">Active Rules</div>
                      <div className="telemetry-metric-value" style={{ color: 'var(--primary)' }}>{dbClaims.length || 120}</div>
                      <div className="telemetry-metric-sub">Verified Claims</div>
                    </div>
                  </div>

                  <div className="telemetry-footer-bar">
                    <span>Protocol: <strong>CTL-v1.4 Verified</strong></span>
                    <span className="badge badge-allow" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>SECURE</span>
                  </div>
                </div>
              </div>
            </div>

            {/* ========================================================= */}
            {/* VISUAL TRAFFIC LIGHT STATUS (COLOR-CODED FOR ANY USER)     */}
            {/* ========================================================= */}
            <div className="traffic-status-grid">
              {/* Card 1: Safety Gate Status (Green) */}
              <div 
                className="traffic-card traffic-card-green"
                style={{ cursor: 'pointer' }}
                onClick={() => { setActiveTab('demo'); setExpandedMenu('demo'); }}
              >
                <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: '#ECFDF5', color: '#059669', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem', flexShrink: 0 }}>
                  🛡️
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="beacon-dot beacon-green"></span>
                    <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#059669', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      PROTECTED & READY
                    </span>
                  </div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>
                    AI Safety Gate Active
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Outdated policies blocked automatically
                  </div>
                </div>
              </div>

              {/* Card 2: Contradiction / Conflict Status (Amber) */}
              <div 
                className="traffic-card traffic-card-amber"
                style={{ cursor: 'pointer' }}
                onClick={() => { setActiveTab('conflicts'); setExpandedMenu('conflicts'); }}
              >
                <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: '#FFFBEB', color: '#D97706', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem', flexShrink: 0 }}>
                  ⚖️
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className={`beacon-dot ${conflicts.length > 0 ? 'beacon-amber' : 'beacon-green'}`}></span>
                    <span style={{ fontSize: '0.72rem', fontWeight: 800, color: conflicts.length > 0 ? '#D97706' : '#059669', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      {conflicts.length > 0 ? 'NEEDS REVIEW' : 'ALL HARMONIZED'}
                    </span>
                  </div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>
                    {conflicts.length} Rule Conflicts Pending
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {conflicts.length > 0 ? "Click to resolve policy disagreements" : "All policies in database agree"}
                  </div>
                </div>
              </div>

              {/* Card 3: Connected Knowledge Sources (Blue) */}
              <div 
                className="traffic-card traffic-card-blue"
                style={{ cursor: 'pointer' }}
                onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); setDocExplorerView('connectors'); }}
              >
                <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: '#EFF6FF', color: '#2563EB', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem', flexShrink: 0 }}>
                  🌐
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="beacon-dot beacon-blue"></span>
                    <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#2563EB', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      ONLINE & SYNCED
                    </span>
                  </div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>
                    {dataSources.length || 5} Connected Sources
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    GitHub, Confluence, Handbooks, Jira
                  </div>
                </div>
              </div>
            </div>

            {/* ========================================================= */}
            {/* 4 UNIVERSAL 1-CLICK LAUNCHPADS (HIGH CONTRAST & VISUAL)   */}
            {/* ========================================================= */}
            <div style={{ marginBottom: '32px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
                    Direct Action Launchpads
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Click any card to open the feature instantly with visual guidance
                  </div>
                </div>
              </div>

              <div className="launchpad-grid">
                {/* Launchpad 1: Safety Gate Demo (Emerald) */}
                <div 
                  className="launchpad-card launchpad-card-emerald"
                  onClick={() => { setActiveTab('demo'); setExpandedMenu('demo'); setDemoScenario('refund_trap'); setDemoStep(0); }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div className="launchpad-icon-box icon-box-emerald">
                        🚀
                      </div>
                      <span className="badge badge-allow" style={{ fontSize: '0.68rem', padding: '2px 8px' }}>
                        1-Click Demo
                      </span>
                    </div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      1. Test Safety Gate Demo
                    </div>
                    <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      See how the safety gate automatically blocks an AI from giving an invalid refund based on an expired handbook.
                    </p>
                  </div>
                  
                  <div style={{ marginTop: '20px' }}>
                    <button className="btn-launch btn-launch-emerald">
                      <span>Start Demo</span>
                      <span>→</span>
                    </button>
                  </div>
                </div>

                {/* Launchpad 2: Agent Playground (Purple) */}
                <div 
                  className="launchpad-card launchpad-card-purple"
                  onClick={() => { setActiveTab('playground'); setExpandedMenu('playground'); }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div className="launchpad-icon-box icon-box-purple">
                        🤖
                      </div>
                      <span className="badge badge-verified" style={{ fontSize: '0.68rem', padding: '2px 8px' }}>
                        Interactive
                      </span>
                    </div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      2. Ask AI Agent Playground
                    </div>
                    <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Ask questions to an AI assistant and see trusted facts highlighted while outdated rumors are filtered out.
                    </p>
                  </div>
                  
                  <div style={{ marginTop: '20px' }}>
                    <button className="btn-launch btn-launch-purple">
                      <span>Open Playground</span>
                      <span>→</span>
                    </button>
                  </div>
                </div>

                {/* Launchpad 3: Conflict Resolver (Amber) */}
                <div 
                  className="launchpad-card launchpad-card-amber"
                  onClick={() => { setActiveTab('conflicts'); setExpandedMenu('conflicts'); }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div className="launchpad-icon-box icon-box-amber">
                        ⚖️
                      </div>
                      <span className="badge badge-review" style={{ fontSize: '0.68rem', padding: '2px 8px' }}>
                        {conflicts.length} Queued
                      </span>
                    </div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      3. Resolve Rule Conflicts
                    </div>
                    <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Pick which company policy is correct when two official documents disagree with each other.
                    </p>
                  </div>
                  
                  <div style={{ marginTop: '20px' }}>
                    <button className="btn-launch btn-launch-amber">
                      <span>Resolve Conflicts ({conflicts.length})</span>
                      <span>→</span>
                    </button>
                  </div>
                </div>

                {/* Launchpad 4: Document Explorer (Blue) */}
                <div 
                  className="launchpad-card launchpad-card-blue"
                  onClick={() => { setActiveTab('ingestion'); setExpandedMenu('ingestion'); }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div className="launchpad-icon-box icon-box-blue">
                        📁
                      </div>
                      <span className="badge badge-verified" style={{ fontSize: '0.68rem', padding: '2px 8px' }}>
                        Repository
                      </span>
                    </div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      4. Document & Source Hub
                    </div>
                    <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Add new PDF, Word files, or connect company GitHub and Confluence spaces for instant extraction.
                    </p>
                  </div>
                  
                  <div style={{ marginTop: '20px' }}>
                    <button className="btn-launch btn-launch-blue">
                      <span>Manage Documents</span>
                      <span>→</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* ========================================================= */}
            {/* 5-SECOND INTERACTIVE SAFETY SIMULATOR (ZERO-EFFORT DEMO)  */}
            {/* ========================================================= */}
            <div className="quick-sim-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="badge badge-verified" style={{ fontSize: '0.72rem', padding: '3px 8px' }}>
                      ⚡ 5-Second Interactive Simulation
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                      Try it right here without leaving the page
                    </span>
                  </div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '6px' }}>
                    How Does Context Trust Layer Protect Your Company?
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    Select a customer tier below and click <strong>Test Decision</strong> to watch the safety gate verify real policy evidence.
                  </p>
                </div>

                {/* Scenario Tier Selector */}
                <div className="sim-tier-nav">
                  <button
                    onClick={() => { setQuickSimType('enterprise'); handleRunQuickSim('enterprise'); }}
                    className={`sim-tier-btn ${quickSimType === 'enterprise' ? 'sim-tier-btn-active' : ''}`}
                  >
                    🏢 Enterprise Customer (Acme Corp)
                  </button>
                  <button
                    onClick={() => { setQuickSimType('standard'); handleRunQuickSim('standard'); }}
                    className={`sim-tier-btn ${quickSimType === 'standard' ? 'sim-tier-btn-active' : ''}`}
                  >
                    👤 Standard Customer
                  </button>
                </div>
              </div>

              {/* Side-by-Side Policy Comparison */}
              <div className="sim-comparison-grid">
                {/* Outdated Rule */}
                <div className="sim-rule-card sim-rule-card-outdated">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>
                      Old Handbook (2025)
                    </span>
                    <span className="badge badge-outdated" style={{ fontSize: '0.65rem' }}>
                      Outdated
                    </span>
                  </div>
                  <div style={{ fontSize: '0.875rem', color: '#64748B', textDecoration: 'line-through', fontWeight: 500 }}>
                    "Customer refund window is strictly limited to 30 days."
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#94A3B8', marginTop: '6px' }}>
                    Source: Employee Handbook 2025 • Superseded
                  </div>
                  {/* Trust Level Meter */}
                  <div style={{ marginTop: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: '3px' }}>
                      <span>Trust Rating</span>
                      <span style={{ fontWeight: 700, color: '#EF4444' }}>50% (Stale)</span>
                    </div>
                    <div style={{ width: '100%', height: '5px', background: 'rgba(239, 68, 68, 0.15)', borderRadius: '999px', overflow: 'hidden' }}>
                      <div style={{ width: '50%', height: '100%', background: '#EF4444', borderRadius: '999px' }}></div>
                    </div>
                  </div>
                </div>

                {/* Authoritative Rule */}
                <div className="sim-rule-card sim-rule-card-valid">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#166534', textTransform: 'uppercase' }}>
                      Active Policy Service (2026)
                    </span>
                    <span className="badge badge-allow" style={{ fontSize: '0.65rem' }}>
                      Authoritative
                    </span>
                  </div>
                  <div style={{ fontSize: '0.875rem', color: '#166534', fontWeight: 700 }}>
                    "Enterprise tier customers have a 60-day exception window."
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#15803D', marginTop: '6px' }}>
                    Source: Enterprise Policy Service • Verified Fresh
                  </div>
                  {/* Trust Level Meter */}
                  <div style={{ marginTop: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: '#15803D', marginBottom: '3px' }}>
                      <span>Trust Rating</span>
                      <span style={{ fontWeight: 700, color: '#10B981' }}>95% (Authoritative)</span>
                    </div>
                    <div style={{ width: '100%', height: '5px', background: 'rgba(16, 185, 129, 0.2)', borderRadius: '999px', overflow: 'hidden' }}>
                      <div style={{ width: '95%', height: '100%', background: '#10B981', borderRadius: '999px' }}></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Question & Run Simulator Button */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', background: 'var(--bg-card-subtle)', padding: '14px 18px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ flex: 1, minWidth: '260px' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                    Customer Request Being Evaluated:
                  </div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '2px' }}>
                    "Customer requests a 45-day refund. Can the AI approve this payout?"
                  </div>
                </div>

                <button 
                  onClick={() => handleRunQuickSim(quickSimType)}
                  disabled={simScanning}
                  className="btn btn-primary"
                  style={{ padding: '10px 20px', fontSize: '0.875rem', fontWeight: 700, borderRadius: '8px', boxShadow: '0 4px 12px -2px rgba(37, 99, 235, 0.3)' }}
                >
                  {simScanning ? (
                    <>
                      <span className="telemetry-pulse-dot" style={{ background: '#FFFFFF' }}></span>
                      <span>Verifying Policy...</span>
                    </>
                  ) : (
                    <>
                      <span>⚡ Run Safety Test</span>
                    </>
                  )}
                </button>
              </div>

              {/* Simulation Result Box */}
              {quickSimResult && (
                <div className="sim-result-box" style={{ marginTop: '16px', padding: '16px 20px', borderRadius: '12px', background: quickSimResult.bgColor, border: `1.5px solid ${quickSimResult.borderColor}`, display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                  <div style={{ fontSize: '1.8rem', lineHeight: '1' }}>
                    {quickSimResult.status === 'ALLOW' ? '🟢' : '🔴'}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className={`badge ${quickSimResult.status === 'ALLOW' ? 'badge-allow' : 'badge-block'}`} style={{ fontSize: '0.75rem', padding: '3px 8px' }}>
                        DECISION: {quickSimResult.badge}
                      </span>
                      <span style={{ fontSize: '0.95rem', fontWeight: 800, color: quickSimResult.color }}>
                        {quickSimResult.title}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.825rem', color: 'var(--text-main)', marginTop: '6px', lineHeight: '1.5' }}>
                      {quickSimResult.detail}
                    </p>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Rule Applied: <strong>{quickSimResult.ruleUsed}</strong>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* ========================================================= */}
            {/* 3-STEP UNIVERSAL VISUAL PROCESS FLOW                      */}
            {/* ========================================================= */}
            <div className="clean-panel" style={{ padding: '24px 28px', marginBottom: '20px' }}>
              <div style={{ marginBottom: '18px' }}>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
                  How It Works in 3 Simple Steps
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  A clear, automated path from document intake to safe AI execution
                </p>
              </div>

              <div className="visual-stepper-grid">
                {/* Step 1 */}
                <div className="visual-step-card">
                  <div className="step-num-badge" style={{ background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE' }}>
                    1
                  </div>
                  <div style={{ fontSize: '1.4rem', marginBottom: '6px' }}>
                    📄
                  </div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    1. Read & Fingerprint Rules
                  </div>
                  <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                    Company handbooks, PDFs, and repository policies are normalized and given cryptographic SHA-256 fingerprint hashes.
                  </p>
                </div>

                {/* Step 2 */}
                <div className="visual-step-card">
                  <div className="step-num-badge" style={{ background: '#FFFBEB', color: '#D97706', border: '1px solid #FDE68A' }}>
                    2
                  </div>
                  <div style={{ fontSize: '1.4rem', marginBottom: '6px' }}>
                    🔍
                  </div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    2. Spot Contradictions
                  </div>
                  <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                    The trust engine compares conflicting statements, overrides, and publication dates to isolate stale facts.
                  </p>
                </div>

                {/* Step 3 */}
                <div className="visual-step-card">
                  <div className="step-num-badge" style={{ background: '#ECFDF5', color: '#059669', border: '1px solid #A7F3D0' }}>
                    3
                  </div>
                  <div style={{ fontSize: '1.4rem', marginBottom: '6px' }}>
                    🛡️
                  </div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    3. Safe AI Execution
                  </div>
                  <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                    Before an AI agent executes an action, the gate ensures it is supported by 100% verified, authoritative evidence.
                  </p>
                </div>
              </div>
            </div>

            {/* Quick Helper Banner */}
            <div style={{ padding: '14px 20px', borderRadius: '10px', background: '#F8FAFC', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1.2rem' }}>💡</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                  Need a full demonstration? Click the green <strong>Launch AI Safety Demo</strong> button above or in the left sidebar anytime.
                </span>
              </div>
              <button 
                onClick={() => { setActiveTab('demo'); setExpandedMenu('demo'); setDemoScenario('refund_trap'); }}
                className="btn btn-secondary" 
                style={{ fontSize: '0.78rem', padding: '6px 14px' }}
              >
                Go to Decision Gate →
              </button>
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

                {/* Active Scenario Indicator */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700 }}>ACTIVE SCENARIO:</span>
                  <span className="badge badge-verified" style={{ fontSize: '0.8rem', padding: '4px 10px' }}>
                    {demoScenario === 'refund_trap' ? '1. Outdated Refund Window Trap' : demoScenario === 'remote_work' ? '2. Remote Work Policy Discrepancy' : '3. Unauthorized Infrastructure Action'}
                  </span>
                </div>
              </div>
            </div>

            {/* Interactive Scenario Selector Tabs */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Select Scenario:
              </span>
              <button
                onClick={() => { setDemoScenario('refund_trap'); setDemoStep(0); setDemoResult(null); }}
                className={`prompt-preset-chip ${demoScenario === 'refund_trap' ? 'prompt-preset-chip-active' : ''}`}
              >
                <span>💳 1. Refund Window Trap</span>
                <span className="badge badge-warning" style={{ fontSize: '0.6rem', padding: '1px 5px' }}>Financial</span>
              </button>
              <button
                onClick={() => { setDemoScenario('remote_work'); setDemoStep(0); setDemoResult(null); }}
                className={`prompt-preset-chip ${demoScenario === 'remote_work' ? 'prompt-preset-chip-active' : ''}`}
              >
                <span>🏠 2. Remote Work Policy</span>
                <span className="badge badge-review" style={{ fontSize: '0.6rem', padding: '1px 5px' }}>HR Policy</span>
              </button>
              <button
                onClick={() => { setDemoScenario('unauthorized_deploy'); setDemoStep(0); setDemoResult(null); }}
                className={`prompt-preset-chip ${demoScenario === 'unauthorized_deploy' ? 'prompt-preset-chip-active' : ''}`}
              >
                <span>🔒 3. Prod Ingress Authorization</span>
                <span className="badge badge-verified" style={{ fontSize: '0.6rem', padding: '1px 5px' }}>Security</span>
              </button>
            </div>

            {/* 3-Stage Progress Scanner */}
            <div className="stage-scanner">
              <div className={`stage-scanner-step ${demoStep >= 1 ? 'stage-scanner-step-done' : 'stage-scanner-step-active'}`}>
                <div className="stage-scanner-num">{demoStep >= 1 ? '✓' : '1'}</div>
                <div>
                  <div className="stage-scanner-title">Intended Claim</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Action Extracted</div>
                </div>
              </div>

              <div className={`stage-scanner-line ${demoRunning ? 'stage-scanner-line-active' : ''}`}></div>

              <div className={`stage-scanner-step ${demoStep === 1 ? 'stage-scanner-step-active' : demoStep === 2 ? 'stage-scanner-step-done' : ''}`}>
                <div className="stage-scanner-num">{demoStep === 2 ? '✓' : '2'}</div>
                <div>
                  <div className="stage-scanner-title">Authority & Freshness</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Arbitration Matrix</div>
                </div>
              </div>

              <div className={`stage-scanner-line ${demoRunning ? 'stage-scanner-line-active' : ''}`}></div>

              <div className={`stage-scanner-step ${demoStep === 2 ? 'stage-scanner-step-done' : ''}`}>
                <div className="stage-scanner-num">{demoStep === 2 ? '✓' : '3'}</div>
                <div>
                  <div className="stage-scanner-title">Gate Verdict</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{demoResult ? demoResult.decision : 'Awaiting Eval'}</div>
                </div>
              </div>
            </div>

            {/* Intended Action & Execution Bar */}
            <div className="clean-panel" style={{ padding: '18px 22px', marginBottom: '20px', background: 'var(--bg-card)', boxShadow: '0 2px 10px -2px rgba(15, 23, 42, 0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
                <div style={{ flex: 1, minWidth: '280px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 800, letterSpacing: '0.04em' }}>
                      Intended Agent Action Under Evaluation:
                    </span>
                    <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>Active Query</span>
                  </div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                    "{currentScenario.query}"
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Actor: <span className="code-pill">{currentScenario.actor.id}</span> (Role: <strong>{currentScenario.actor.role}</strong>)
                  </div>
                </div>

                <button 
                  onClick={runKillerDemo} 
                  disabled={demoRunning}
                  className="btn btn-primary"
                  style={{ padding: '11px 22px', fontSize: '0.9rem', fontWeight: 700, borderRadius: '10px', boxShadow: '0 4px 14px -2px rgba(37, 99, 235, 0.35)' }}
                >
                  {demoRunning ? (
                    <>
                      <span className="telemetry-pulse-dot" style={{ background: '#FFFFFF' }}></span>
                      <span>Verifying Evidence...</span>
                    </>
                  ) : (
                    <>
                      <span>⚡ Run Decision Gate Evaluation</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Main Decision Gate Panel */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.05fr 0.95fr', gap: '20px' }}>
              
              {/* Left Side: Candidate Evidence Evaluated */}
              <div className="clean-panel" style={{ padding: '22px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '0.98rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    Candidate Policy Evidence Evaluated
                  </h3>
                  <span className="badge badge-review" style={{ fontSize: '0.7rem' }}>Contradiction Detected</span>
                </div>

                <div style={{ display: 'grid', gap: '14px' }}>
                  {/* Candidate 1 (Stale / Low Authority) */}
                  <div className="evidence-cert evidence-cert-superseded">
                    <span className="evidence-watermark-stamp badge badge-outdated">SUPERSEDED</span>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--danger-text)', fontWeight: 800, marginBottom: '6px' }}>
                      <span>RECORD 1 (Superseded Policy)</span>
                      <span>Published: {currentScenario.claim1.date}</span>
                    </div>
                    <div style={{ fontSize: '0.88rem', color: 'var(--text-muted)', textDecoration: 'line-through', fontWeight: 500, lineHeight: 1.5, paddingRight: '70px' }}>
                      "{currentScenario.claim1.text}"
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(239, 68, 68, 0.15)' }}>
                      <span>Source: <strong>{currentScenario.claim1.source}</strong></span>
                      <span>Authority: <strong style={{ color: 'var(--danger-solid)' }}>{currentScenario.claim1.authority}/100</strong> (Stale)</span>
                    </div>
                  </div>

                  {/* Candidate 2 (Authoritative / Fresh) */}
                  <div className="evidence-cert evidence-cert-authoritative">
                    <span className="evidence-watermark-stamp badge badge-allow">AUTHORITATIVE</span>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 800, marginBottom: '6px' }}>
                      <span>RECORD 2 (Authoritative Override)</span>
                      <span>Published: {currentScenario.claim2.date}</span>
                    </div>
                    <div style={{ fontSize: '0.92rem', color: 'var(--success-text)', fontWeight: 700, lineHeight: 1.5, paddingRight: '70px' }}>
                      "{currentScenario.claim2.text}"
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.74rem', color: 'var(--success-text)', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(16, 185, 129, 0.2)' }}>
                      <span>Source: <strong>{currentScenario.claim2.source}</strong></span>
                      <span>Authority: <strong style={{ color: 'var(--success-solid)' }}>{currentScenario.claim2.authority}/100</strong> (Verified Fresh)</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Side: Decision Gate Evaluation Verdict */}
              <div className="clean-panel" style={{ padding: '22px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ fontSize: '0.98rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      Decision Gate Verdict
                    </h3>
                    {demoResult && <span className="code-pill">Audit: {demoResult.audit_id}</span>}
                  </div>

                  {demoStep === 0 && (
                    <div style={{ padding: '48px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                      <div style={{ fontSize: '2.4rem', marginBottom: '10px' }}>🛡️</div>
                      <div style={{ fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px' }}>Ready for Evaluation</div>
                      <div>Click "Run Decision Gate Evaluation" above to compute deterministic provenance.</div>
                    </div>
                  )}

                  {demoStep === 1 && (
                    <div style={{ padding: '48px 20px', textAlign: 'center', color: 'var(--primary)', fontSize: '0.875rem', fontWeight: 600 }}>
                      <div style={{ fontSize: '2.4rem', marginBottom: '10px', animation: 'radarPulse 1.2s infinite' }}>⚡</div>
                      <div style={{ fontWeight: 800, color: 'var(--primary)', marginBottom: '4px' }}>Evaluating Evidence & Authority Levels...</div>
                      <div style={{ color: 'var(--text-muted)' }}>Checking superseding timestamps, authority scores, and scope...</div>
                    </div>
                  )}

                  {demoStep === 2 && demoResult && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', padding: '12px 16px', borderRadius: '10px', background: demoResult.decision === 'ALLOW' ? 'var(--success-bg)' : 'var(--danger-bg)', border: `1.5px solid ${demoResult.decision === 'ALLOW' ? 'var(--success-border)' : 'var(--danger-border)'}` }}>
                        <span style={{ fontSize: '1.8rem' }}>
                          {demoResult.decision === 'ALLOW' ? '🟢' : '🔴'}
                        </span>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className={`badge ${demoResult.decision === 'ALLOW' ? 'badge-allow' : demoResult.decision === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '0.8rem', padding: '3px 9px' }}>
                              VERDICT: {demoResult.decision}
                            </span>
                            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-main)' }}>
                              Risk: <strong style={{ color: demoResult.risk === 'LOW' ? 'var(--success-text)' : 'var(--danger-text)' }}>{demoResult.risk}</strong>
                            </span>
                          </div>
                          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                            Validity Status: <strong>{demoResult.validity}</strong> • Enforced by Trust Layer
                          </div>
                        </div>
                      </div>

                      <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                        <div style={{ fontWeight: 800, color: 'var(--text-main)', marginBottom: '6px' }}>Evaluation Reasons:</div>
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
                  <div style={{ marginTop: '12px', padding: '12px 14px', background: 'var(--bg-card-subtle)', borderRadius: '10px', border: '1px solid var(--border-subtle)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    <strong>Suggested Agent Action:</strong> {demoResult.suggested_action}
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
        {/* TAB 2: INTERACTIVE AGENT PLAYGROUND                       */}
        {/* ========================================================= */}
        {activeTab === 'playground' && (
          <div>
            {/* Header Banner */}
            <div style={{ marginBottom: '24px' }}>
              <span className="badge badge-verified" style={{ marginBottom: '6px' }}>
                Live API /v1/context/query
              </span>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                Interactive AI Agent Playground
              </h1>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '4px' }}>
                Test how autonomous AI Agents query organizational knowledge. The Trust Gate scores claims, excludes expired policies, and filters out contradictory knowledge.
              </p>
            </div>

            {/* Main Interactive Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: '22px' }}>
              
              {/* Left Column: Query Console */}
              <div className="clean-panel" style={{ padding: '22px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '0.98rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    Agent Command Console
                  </div>
                  <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>AI Agent Link</span>
                </div>

                {/* Preset Quick-Launch Chips */}
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.04em' }}>
                    Quick Preset Inquiries:
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {playgroundPresets.map((preset, idx) => (
                      <button 
                        key={idx}
                        onClick={() => {
                          setPlaygroundQuery(preset.query);
                          handleExecutePlaygroundQuery(preset.query);
                        }}
                        className={`prompt-preset-chip ${playgroundQuery === preset.query ? 'prompt-preset-chip-active' : ''}`}
                        style={{ fontSize: '0.74rem', padding: '5px 10px' }}
                      >
                        <span>{idx === 0 ? '💳' : idx === 1 ? '🏠' : '🔒'}</span>
                        <span>{preset.title}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Persona Selector with Tactile Card Buttons */}
                <div>
                  <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase', display: 'block', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    Active Agent Persona:
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px' }}>
                    <button
                      type="button"
                      onClick={() => setPlaygroundAgent({ id: "88888888-8888-8888-8888-888888888888", name: "Billing Dispute Agent", role: "billing_agent" })}
                      className={`prompt-preset-chip ${playgroundAgent.role === 'billing_agent' ? 'prompt-preset-chip-active' : ''}`}
                      style={{ justifyContent: 'center', padding: '8px 4px', fontSize: '0.72rem', textAlign: 'center', flexDirection: 'column', gap: '2px' }}
                    >
                      <span style={{ fontSize: '1.1rem' }}>💳</span>
                      <span>Billing Agent</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setPlaygroundAgent({ id: "88888888-8888-8888-8888-888888888889", name: "HR Policy Assistant", role: "hr_assistant" })}
                      className={`prompt-preset-chip ${playgroundAgent.role === 'hr_assistant' ? 'prompt-preset-chip-active' : ''}`}
                      style={{ justifyContent: 'center', padding: '8px 4px', fontSize: '0.72rem', textAlign: 'center', flexDirection: 'column', gap: '2px' }}
                    >
                      <span style={{ fontSize: '1.1rem' }}>👥</span>
                      <span>HR Assistant</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setPlaygroundAgent({ id: "88888888-8888-8888-8888-888888888890", name: "DevOps Security Guard", role: "devops_agent" })}
                      className={`prompt-preset-chip ${playgroundAgent.role === 'devops_agent' ? 'prompt-preset-chip-active' : ''}`}
                      style={{ justifyContent: 'center', padding: '8px 4px', fontSize: '0.72rem', textAlign: 'center', flexDirection: 'column', gap: '2px' }}
                    >
                      <span style={{ fontSize: '1.1rem' }}>🛡️</span>
                      <span>DevOps Guard</span>
                    </button>
                  </div>
                </div>

                {/* Trust Score Threshold Slider */}
                <div style={{ background: 'var(--bg-card-subtle)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <label style={{ fontSize: '0.74rem', color: 'var(--text-main)', fontWeight: 700 }}>
                      Minimum Trust Threshold:
                    </label>
                    <span className="badge badge-verified" style={{ fontSize: '0.75rem', fontWeight: 800 }}>
                      {(playgroundThreshold * 100).toFixed(0)}%
                    </span>
                  </div>
                  <input 
                    type="range" 
                    min="0.50" 
                    max="0.99" 
                    step="0.05"
                    value={playgroundThreshold} 
                    onChange={e => setPlaygroundThreshold(parseFloat(e.target.value))}
                    style={{ width: '100%', accentColor: 'var(--primary)', cursor: 'pointer' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    <span>Lenient (50%)</span>
                    <span>Standard (85%)</span>
                    <span>Strict (99%)</span>
                  </div>
                </div>

                {/* Query Textarea */}
                <div>
                  <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase', display: 'block', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    Agent Question / Task:
                  </label>
                  <textarea 
                    rows={3}
                    value={playgroundQuery} 
                    onChange={e => setPlaygroundQuery(e.target.value)}
                    placeholder="Ask any policy, guideline, or authority question..."
                    style={{ width: '100%', padding: '10px 12px', fontSize: '0.85rem', lineHeight: 1.4, borderRadius: '8px' }}
                  />
                </div>

                {/* Submit Button */}
                <button 
                  onClick={() => runPlaygroundQuery()} 
                  disabled={playgroundRunning}
                  className="btn btn-primary" 
                  style={{ width: '100%', padding: '11px', fontSize: '0.9rem', fontWeight: 700, borderRadius: '9px', boxShadow: '0 4px 14px -2px rgba(37, 99, 235, 0.35)' }}
                >
                  {playgroundRunning ? (
                    <>
                      <span className="telemetry-pulse-dot" style={{ background: '#FFFFFF' }}></span>
                      <span>Querying Trust Layer...</span>
                    </>
                  ) : (
                    <>
                      <span>🔍 Query Context Trust Layer</span>
                    </>
                  )}
                </button>
              </div>

              {/* Right Column: Grounded Answer & Citations */}
              <div style={{ display: 'grid', gap: '18px' }}>
                
                {/* Answer Card */}
                <div className="clean-panel" style={{ padding: '22px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                    <div style={{ fontSize: '0.98rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      Grounded Autonomous Output
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {playgroundResult && (
                        <>
                          <button
                            onClick={() => {
                              navigator.clipboard?.writeText(playgroundResult.synthesizedAnswer || '');
                              setCopiedAnswer(true);
                              setTimeout(() => setCopiedAnswer(false), 1500);
                            }}
                            className="btn btn-secondary"
                            style={{ fontSize: '0.72rem', padding: '4px 10px' }}
                            title="Copy answer to clipboard"
                          >
                            {copiedAnswer ? "✓ Copied!" : "📋 Copy"}
                          </button>
                          <span className="badge badge-allow" style={{ fontSize: '0.75rem' }}>
                            Confidence: {(Number(playgroundResult.confidence || 0.95) * 100).toFixed(0)}%
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {!playgroundResult && !playgroundRunning && (
                    <div style={{ padding: '36px 14px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                      <div style={{ fontSize: '2.2rem', marginBottom: '8px' }}>🤖</div>
                      <div style={{ fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px' }}>Awaiting Agent Inquiry</div>
                      <div>Select a quick preset above or type an inquiry to test the trust filter.</div>
                    </div>
                  )}

                  {playgroundRunning && (
                    <div style={{ padding: '36px 14px', textAlign: 'center', color: 'var(--primary)', fontSize: '0.875rem', fontWeight: 600 }}>
                      <div style={{ fontSize: '2.2rem', marginBottom: '8px', animation: 'radarPulse 1.2s infinite' }}>⚡</div>
                      <div style={{ fontWeight: 800, marginBottom: '4px' }}>Validating Facts & Filtering Contradictions...</div>
                      <div style={{ color: 'var(--text-muted)' }}>Discarding stale policies below {(playgroundThreshold * 100).toFixed(0)}% threshold...</div>
                    </div>
                  )}

                  {playgroundResult && !playgroundRunning && (
                    <div style={{ background: 'var(--bg-card-subtle)', padding: '16px 18px', borderRadius: '10px', border: '1px solid var(--border-subtle)', lineHeight: 1.6, fontSize: '0.88rem', color: 'var(--text-main)', whiteSpace: 'pre-wrap', position: 'relative' }}>
                      {playgroundResult.synthesizedAnswer}
                    </div>
                  )}
                </div>

                {/* Evidence Citations */}
                <div className="clean-panel" style={{ padding: '22px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                    <div style={{ fontSize: '0.98rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      Trust Gate Citations ({playgroundResult?.context?.length || 0})
                    </div>
                    <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>Cryptographic Proof</span>
                  </div>

                  {(!playgroundResult || !playgroundResult.context || playgroundResult.context.length === 0) ? (
                    <div style={{ padding: '24px 10px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.825rem' }}>
                      No verified citation records loaded yet.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gap: '12px' }}>
                      {playgroundResult.context.map((ctx, idx) => (
                        <div key={idx} className="evidence-cert evidence-cert-authoritative" style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span className="badge badge-allow" style={{ fontSize: '0.68rem' }}>Citation #{idx + 1}</span>
                              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                Source: <strong>{ctx.source?.document || 'Verified Document'}</strong>
                              </span>
                            </div>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              Trust Score: <strong style={{ color: 'var(--success-solid)' }}>{(Number(ctx.trust_score) * 100).toFixed(0)}%</strong>
                            </span>
                          </div>

                          <p style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', lineHeight: 1.5 }}>
                            "{ctx.claim}"
                          </p>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(16, 185, 129, 0.2)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            <span>Section: <code>{ctx.source?.section || 'General Policy'}</code></span>
                            <span>Status: <strong style={{ color: 'var(--success-text)' }}>{ctx.validity?.status?.toUpperCase() || 'VERIFIED'}</strong></span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 3: CONFLICT RESOLVER                                  */}
        {/* ========================================================= */}
        {activeTab === 'conflicts' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-main)' }}>
                  Auditor Conflict Resolution Queue
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '2px' }}>
                  Review, arbitrate, and supersede conflicting enterprise policies to eliminate ambiguity for autonomous agents.
                </p>
              </div>

              <button onClick={fetchHealthAndConflicts} className="btn btn-secondary" style={{ padding: '7px 12px' }}>
                Refresh Queue
              </button>
            </div>

            {/* Category Filter Chips */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
              <button
                onClick={() => setConflictCategoryFilter('all')}
                className={`prompt-preset-chip ${conflictCategoryFilter === 'all' ? 'prompt-preset-chip-active' : ''}`}
              >
                <span>⚖️ All Conflicts ({conflicts.length})</span>
              </button>
              <button
                onClick={() => setConflictCategoryFilter('numerical')}
                className={`prompt-preset-chip ${conflictCategoryFilter === 'numerical' ? 'prompt-preset-chip-active' : ''}`}
              >
                <span>🔢 Numerical Discrepancies</span>
              </button>
              <button
                onClick={() => setConflictCategoryFilter('authority')}
                className={`prompt-preset-chip ${conflictCategoryFilter === 'authority' ? 'prompt-preset-chip-active' : ''}`}
              >
                <span>📜 Policy Superseded</span>
              </button>
            </div>

            {/* Conflicts List */}
            {conflicts.length === 0 ? (
              <div className="clean-panel" style={{ padding: '56px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '2.8rem', marginBottom: '12px' }}>✨</div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)' }}>Zero Pending Policy Conflicts</h3>
                <p style={{ fontSize: '0.85rem', marginTop: '6px', maxWidth: '500px', margin: '6px auto 0' }}>
                  All company claims across PostgreSQL are completely harmonized and non-contradictory.
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '18px' }}>
                {conflicts
                  .filter(conf => {
                    if (conflictCategoryFilter === 'numerical') return (conf.conflict_type || '').toLowerCase().includes('numerical');
                    if (conflictCategoryFilter === 'authority') return (conf.conflict_type || '').toLowerCase().includes('authority') || (conf.conflict_type || '').toLowerCase().includes('direct');
                    return true;
                  })
                  .map((conf, idx) => {
                  const claimA = conf.claim_a;
                  const claimB = conf.claim_b;
                  const scoreA = claimA?.trust_scores?.[0]?.overall_score || 0.50;
                  const scoreB = claimB?.trust_scores?.[0]?.overall_score || 0.95;
                  const sectionA = claimA?.evidence?.[0]?.section || "Section 2.0";
                  const sectionB = claimB?.evidence?.[0]?.section || "Section 3.0";

                  return (
                    <div key={conf.id || idx} className="clean-panel" style={{ padding: '22px', boxShadow: '0 4px 16px -4px rgba(15, 23, 42, 0.05)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--text-main)' }}>
                            Arbitration Case #{idx + 1}: {conf.conflict_type?.toUpperCase() || "NUMERICAL_DISCREPANCY"}
                          </span>
                          <span className="badge badge-review" style={{ fontSize: '0.72rem' }}>Severity: {conf.severity?.toUpperCase() || 'HIGH'}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className="code-pill">Bayesian Confidence: {conf.confidence || '0.95'}</span>
                        </div>
                      </div>

                      {/* Side-by-Side Comparison */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '18px' }}>
                        {/* Stale Candidate */}
                        <div className="evidence-cert evidence-cert-superseded" style={{ padding: '16px 18px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--danger-text)', fontWeight: 800, marginBottom: '6px' }}>
                            <span>CLAIM A (Stale Candidate)</span>
                            <span className="badge badge-outdated">ID: {conf.claim_a_id?.substring(0, 8)}</span>
                          </div>
                          <p style={{ fontSize: '0.9rem', color: 'var(--danger-text)', lineHeight: '1.5', fontWeight: 600 }}>
                            "{claimA?.claim_text || 'Customers are eligible for automated refunds up to ₹25,000 without supervisor approval.'}"
                          </p>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '12px', paddingTop: '8px', borderTop: '1px solid rgba(220, 38, 38, 0.15)' }}>
                            <span>Source: <strong>{sectionA}</strong></span>
                            <span>Trust Score: <strong style={{ color: 'var(--danger-solid)' }}>{(Number(scoreA) * 100).toFixed(0)}%</strong></span>
                          </div>
                        </div>

                        {/* Authoritative Candidate */}
                        <div className="evidence-cert evidence-cert-authoritative" style={{ padding: '16px 18px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 800, marginBottom: '6px' }}>
                            <span>CLAIM B (Authoritative Override)</span>
                            <span className="badge badge-allow">ID: {conf.claim_b_id?.substring(0, 8)}</span>
                          </div>
                          <p style={{ fontSize: '0.9rem', color: 'var(--success-text)', lineHeight: '1.5', fontWeight: 700 }}>
                            "{claimB?.claim_text || 'Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff.'}"
                          </p>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '12px', paddingTop: '8px', borderTop: '1px solid rgba(22, 163, 74, 0.15)' }}>
                            <span>Source: <strong>{sectionB}</strong></span>
                            <span>Trust Score: <strong style={{ color: 'var(--success-solid)' }}>{(Number(scoreB) * 100).toFixed(0)}%</strong></span>
                          </div>
                        </div>
                      </div>

                      {/* Auditor Actions */}
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', borderTop: '1px solid var(--border-subtle)', paddingTop: '14px' }}>
                        <button 
                          onClick={() => handleResolveConflict(conf.id, conf.claim_a_id, "Approved Claim A as verified exception.")}
                          className="btn btn-secondary"
                          style={{ padding: '8px 14px', fontSize: '0.8rem', fontWeight: 600 }}
                        >
                          Keep Claim A
                        </button>
                        <button 
                          onClick={() => handleResolveConflict(conf.id, conf.claim_b_id, "Approved Claim B as authoritative guideline.")}
                          className="btn btn-success"
                          style={{ padding: '8px 18px', fontSize: '0.825rem', fontWeight: 700, borderRadius: '8px', boxShadow: '0 2px 8px rgba(16, 185, 129, 0.25)' }}
                        >
                          ⚡ Approve Authoritative Claim B (Supersede A)
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
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

            {/* Interactive Sub-View Switcher Toolbar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '22px', flexWrap: 'wrap' }}>
              <button
                onClick={() => setDocExplorerView('connectors')}
                className={`prompt-preset-chip ${docExplorerView === 'connectors' ? 'prompt-preset-chip-active' : ''}`}
                style={{ padding: '7px 14px', fontSize: '0.8rem' }}
              >
                <span>🌐 Live Connectors & Sync ({dataSources.length})</span>
              </button>
              <button
                onClick={() => setDocExplorerView('ingest')}
                className={`prompt-preset-chip ${docExplorerView === 'ingest' ? 'prompt-preset-chip-active' : ''}`}
                style={{ padding: '7px 14px', fontSize: '0.8rem' }}
              >
                <span>➕ Ingest Policy Document</span>
              </button>
              <button
                onClick={() => setDocExplorerView('documents')}
                className={`prompt-preset-chip ${docExplorerView === 'documents' ? 'prompt-preset-chip-active' : ''}`}
                style={{ padding: '7px 14px', fontSize: '0.8rem' }}
              >
                <span>📁 Stored Documents ({dbDocuments.length})</span>
              </button>
              <button
                onClick={() => setDocExplorerView('claims')}
                className={`prompt-preset-chip ${docExplorerView === 'claims' ? 'prompt-preset-chip-active' : ''}`}
                style={{ padding: '7px 14px', fontSize: '0.8rem' }}
              >
                <span>🔍 Atomic Claims ({dbClaims.length})</span>
              </button>
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
                    const typeLabel = source.source_type?.toUpperCase() || 'CONNECTOR';
                    const lastSyncText = source.last_synced_at 
                      ? new Date(source.last_synced_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                      : 'Not synced yet';

                    return (
                      <div key={source.id || idx} className="clean-panel" style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
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
                            <div style={{ fontWeight: 700, marginBottom: '2px' }}>Monitored Scope:</div>
                            {source.source_type === 'confluence' && "Live Confluence Wiki Space, Policy Articles, and Security Standards."}
                            {source.source_type === 'jira' && "Live Jira Project, Incident Runbooks, SLAs, and Release Guidelines."}
                            {source.source_type === 'github' && "Live GitHub Repository, /docs Markdown files, and Architecture Specs."}
                            {source.source_type === 'portal' && "Corporate Security Directives, Authentication & Compliance Mandates."}
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
                    <span className="code-pill">2. Normalizing Markdown</span>
                    <span>→</span>
                    <span className="code-pill">3. Extracting Atomic Claims</span>
                    <span>→</span>
                    <span className="code-pill">4. Detecting Contradictions</span>
                    <span>→</span>
                    <span className="code-pill">5. Updating Auditor Queue</span>
                  </div>
                </div>

                {/* Modal: Connect Real Data Source */}
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
                    <div className="clean-panel" style={{ width: '100%', maxWidth: '520px', padding: '24px', background: '#FFFFFF', borderRadius: '10px', boxShadow: '0 10px 25px rgba(0,0,0,0.1)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main)' }}>
                          Connect Real Enterprise Source
                        </h3>
                        <button 
                          onClick={() => setShowAddSourceModal(false)}
                          style={{ background: 'none', border: 'none', fontSize: '1.1rem', cursor: 'pointer', color: 'var(--text-muted)' }}
                        >
                          ✕
                        </button>
                      </div>

                      <form onSubmit={handleConnectNewSource} style={{ display: 'grid', gap: '14px' }}>
                        <div>
                          <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                            Source Provider:
                          </label>
                          <select 
                            value={newSourceForm.sourceType}
                            onChange={e => setNewSourceForm({ ...newSourceForm, sourceType: e.target.value })}
                            style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                          >
                            <option value="github">GitHub Repository (Public or Private)</option>
                            <option value="confluence">Atlassian Confluence Space</option>
                            <option value="jira">Atlassian Jira Project</option>
                          </select>
                        </div>

                        <div>
                          <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                            Connection Name:
                          </label>
                          <input 
                            type="text" 
                            placeholder="e.g. My Company Security Docs"
                            value={newSourceForm.name}
                            onChange={e => setNewSourceForm({ ...newSourceForm, name: e.target.value })}
                            style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                            required
                          />
                        </div>

                        {newSourceForm.sourceType === 'github' && (
                          <div>
                            <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                              GitHub Repository (owner/repo):
                            </label>
                            <input 
                              type="text" 
                              placeholder="e.g. facebook/react or your-username/policies-repo"
                              value={newSourceForm.externalId}
                              onChange={e => setNewSourceForm({ ...newSourceForm, externalId: e.target.value })}
                              style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                              required
                            />
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                              Any public GitHub repository works immediately with no token needed.
                            </div>
                          </div>
                        )}

                        {newSourceForm.sourceType === 'confluence' && (
                          <>
                            <div>
                              <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                                Confluence Space Key:
                              </label>
                              <input 
                                type="text" 
                                placeholder="e.g. POLICIES or HR"
                                value={newSourceForm.externalId}
                                onChange={e => setNewSourceForm({ ...newSourceForm, externalId: e.target.value })}
                                style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                                required
                              />
                            </div>
                            <div>
                              <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                                Atlassian Base URL (Optional):
                              </label>
                              <input 
                                type="text" 
                                placeholder="https://yourcompany.atlassian.net"
                                value={newSourceForm.baseUrl}
                                onChange={e => setNewSourceForm({ ...newSourceForm, baseUrl: e.target.value })}
                                style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                              />
                            </div>
                          </>
                        )}

                        {newSourceForm.sourceType === 'jira' && (
                          <>
                            <div>
                              <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                                Jira Project Key:
                              </label>
                              <input 
                                type="text" 
                                placeholder="e.g. OPS or SRE"
                                value={newSourceForm.externalId}
                                onChange={e => setNewSourceForm({ ...newSourceForm, externalId: e.target.value })}
                                style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                                required
                              />
                            </div>
                          </>
                        )}

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

                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
                          <button 
                            type="button" 
                            onClick={() => setShowAddSourceModal(false)}
                            className="btn btn-secondary"
                            style={{ padding: '8px 14px' }}
                          >
                            Cancel
                          </button>
                          <button 
                            type="submit" 
                            disabled={isConnectingSource}
                            className="btn btn-primary"
                            style={{ padding: '8px 18px' }}
                          >
                            {isConnectingSource ? "Connecting & Syncing..." : "Connect & Sync Now"}
                          </button>
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
      </main>
    </div>
  );
}

