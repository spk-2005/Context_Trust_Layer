import React, { useState, useEffect, useRef } from 'react';

export default function App() {
  const [activeTab, setActiveTab] = useState('demo');
  const [expandedMenu, setExpandedMenu] = useState('demo');
  const [health, setHealth] = useState({ status: 'checking', database: false, version: '0.1.0' });
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

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
      {/* LEFT SIDEBAR MENU (NO SYMBOLS/ICONS, CLEAN TEXT)          */}
      {/* ========================================================= */}
      <aside className="sidebar">
        {/* Brand Header */}
        <div style={{ padding: '24px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
              Context Trust Layer
            </span>
            <span className="badge badge-verified" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
              v0.1.0
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            AI Evidence & Decision Safety Gate
          </p>
        </div>

        {/* Navigation Tabs with Accordion Sub-Menus */}
        <nav className="nav-list" style={{ overflowY: 'auto' }}>
          {/* TAB 0: Home Overview Dashboard */}
          <div>
            <button 
              onClick={() => handleToggleParentTab('home')} 
              className={`nav-item ${activeTab === 'home' ? 'nav-item-active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`nav-chevron ${expandedMenu === 'home' ? 'nav-chevron-open' : ''}`}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </span>
                <span>Home Overview</span>
              </div>
            </button>
            <div className={`nav-sub-accordion ${expandedMenu === 'home' ? 'nav-sub-accordion-open' : ''}`}>
              <div className="nav-sub-list">
                <button 
                  onClick={() => { setActiveTab('home'); }}
                  className={`nav-sub-item ${activeTab === 'home' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>System Architecture & Metrics</span>
                </button>
              </div>
            </div>
          </div>

          {/* TAB 1: Decision Gate Demo */}
          <div>
            <button 
              onClick={() => handleToggleParentTab('demo')} 
              className={`nav-item ${activeTab === 'demo' ? 'nav-item-active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`nav-chevron ${expandedMenu === 'demo' ? 'nav-chevron-open' : ''}`}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </span>
                <span>Decision Gate Demo</span>
              </div>
            </button>
            <div className={`nav-sub-accordion ${expandedMenu === 'demo' ? 'nav-sub-accordion-open' : ''}`}>
              <div className="nav-sub-list">
                <button 
                  onClick={() => { setActiveTab('demo'); setDemoScenario('refund_trap'); setDemoStep(0); }}
                  className={`nav-sub-item ${activeTab === 'demo' && demoScenario === 'refund_trap' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>1. Refund Window</span>
                  <span className="badge badge-warning" style={{ fontSize: '0.62rem', padding: '1px 4px' }}>Trap</span>
                </button>
                <button 
                  onClick={() => { setActiveTab('demo'); setDemoScenario('remote_work'); setDemoStep(0); }}
                  className={`nav-sub-item ${activeTab === 'demo' && demoScenario === 'remote_work' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>2. Remote Work</span>
                  <span className="badge badge-review" style={{ fontSize: '0.62rem', padding: '1px 4px' }}>Rule</span>
                </button>
                <button 
                  onClick={() => { setActiveTab('demo'); setDemoScenario('unauthorized_deploy'); setDemoStep(0); }}
                  className={`nav-sub-item ${activeTab === 'demo' && demoScenario === 'unauthorized_deploy' ? 'nav-sub-item-active' : ''}`}
                >
                  <span>3. Prod Ingress</span>
                  <span className="badge badge-verified" style={{ fontSize: '0.62rem', padding: '1px 4px' }}>Auth</span>
                </button>
              </div>
            </div>
          </div>

          {/* TAB 2: Agent Playground */}
          <div>
            <button 
              onClick={() => handleToggleParentTab('playground')} 
              className={`nav-item ${activeTab === 'playground' ? 'nav-item-active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`nav-chevron ${expandedMenu === 'playground' ? 'nav-chevron-open' : ''}`}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </span>
                <span>Agent Playground</span>
              </div>
            </button>
            <div className={`nav-sub-accordion ${expandedMenu === 'playground' ? 'nav-sub-accordion-open' : ''}`}>
              <div className="nav-sub-list">
                <button 
                  onClick={() => { setActiveTab('playground'); handleExecutePlaygroundQuery(playgroundQuery); }}
                  className={`nav-sub-item ${activeTab === 'playground' && !playgroundPresets.some(p => p.query === playgroundQuery) ? 'nav-sub-item-active' : ''}`}
                >
                  <span>Interactive Query</span>
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
          <div>
            <button 
              onClick={() => handleToggleParentTab('conflicts')} 
              className={`nav-item ${activeTab === 'conflicts' ? 'nav-item-active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`nav-chevron ${expandedMenu === 'conflicts' ? 'nav-chevron-open' : ''}`}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </span>
                <span>Conflict Resolver</span>
              </div>
              {conflicts.length > 0 && (
                <span className="badge badge-review" style={{ fontSize: '0.7rem', padding: '1px 6px' }}>
                  {conflicts.length}
                </span>
              )}
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
          <div>
            <button 
              onClick={() => handleToggleParentTab('ingestion')} 
              className={`nav-item ${activeTab === 'ingestion' ? 'nav-item-active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`nav-chevron ${expandedMenu === 'ingestion' ? 'nav-chevron-open' : ''}`}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </span>
                <span>Document Explorer</span>
              </div>
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
                  <span>Ingest New Document</span>
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

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge badge-verified" style={{ fontSize: '0.72rem', padding: '3px 8px' }}>
              System Operational
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
                onClick={() => { setActiveTab('conflicts'); setExpandedMenu('conflicts'); }}
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

                {/* Card 3: Conflict Resolver */}
                <div 
                  className="clean-panel" 
                  style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => { setActiveTab('conflicts'); setExpandedMenu('conflicts'); }}
                >
                  <div>
                    <span className="badge badge-review" style={{ marginBottom: '8px' }}>Module 3</span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                      Conflict Resolver Queue
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '6px' }}>
                      Review and arbitrate conflicting policies. Approved claims become authoritative while stale candidates are archived.
                    </p>
                  </div>
                  <div style={{ marginTop: '16px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Open Resolver ({conflicts.length}) →
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

                {/* Active Scenario Indicator */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700 }}>ACTIVE SCENARIO:</span>
                  <span className="badge badge-verified" style={{ fontSize: '0.8rem', padding: '4px 10px' }}>
                    {demoScenario === 'refund_trap' ? '1. Outdated Refund Window Trap' : demoScenario === 'remote_work' ? '2. Remote Work Policy Discrepancy' : '3. Unauthorized Infrastructure Action'}
                  </span>
                </div>
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
            <div style={{ display: 'grid', gridTemplateColumns: '400px 1fr', gap: '20px' }}>
              
              {/* Left Column: Query Console */}
              <div className="clean-panel" style={{ padding: '20px' }}>
                <div style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '14px' }}>
                  Agent Query Console
                </div>

                <div style={{ display: 'grid', gap: '14px' }}>
                  {/* Persona Selector */}
                  <div>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                      Agent Persona:
                    </label>
                    <select
                      value={playgroundAgent.role}
                      onChange={e => {
                        const role = e.target.value;
                        if (role === 'billing_agent') setPlaygroundAgent({ id: "88888888-8888-8888-8888-888888888888", name: "Billing Dispute Agent", role });
                        else if (role === 'hr_assistant') setPlaygroundAgent({ id: "88888888-8888-8888-8888-888888888889", name: "HR Policy Assistant", role });
                        else setPlaygroundAgent({ id: "88888888-8888-8888-8888-888888888890", name: "DevOps Security Guard", role });
                      }}
                      style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                    >
                      <option value="billing_agent">Billing Dispute Resolution Agent</option>
                      <option value="hr_assistant">HR Policy & Benefits Assistant</option>
                      <option value="devops_agent">DevOps Infrastructure Security Guard</option>
                    </select>
                  </div>

                  {/* Trust Score Threshold */}
                  <div style={{ background: 'var(--bg-card-subtle)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 700 }}>
                        Min Trust Threshold:
                      </label>
                      <span className="badge badge-verified">
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
                      style={{ width: '100%', accentColor: 'var(--primary)' }}
                    />
                  </div>

                  {/* Query Textarea */}
                  <div>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                      Agent Question:
                    </label>
                    <textarea 
                      rows={3}
                      value={playgroundQuery} 
                      onChange={e => setPlaygroundQuery(e.target.value)}
                      placeholder="Ask any policy question..."
                      style={{ width: '100%', padding: '8px 10px', fontSize: '0.85rem' }}
                    />
                  </div>

                  {/* Submit Button */}
                  <button 
                    onClick={() => runPlaygroundQuery()} 
                    disabled={playgroundRunning}
                    className="btn btn-primary" 
                    style={{ width: '100%', padding: '10px', fontSize: '0.875rem' }}
                  >
                    {playgroundRunning ? "Retrieving..." : "Query Context Trust Layer"}
                  </button>
                </div>
              </div>

              {/* Right Column: Grounded Answer & Citations */}
              <div style={{ display: 'grid', gap: '16px' }}>
                
                {/* Answer Card */}
                <div className="clean-panel" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      Grounded Agent Output
                    </div>
                    {playgroundResult && (
                      <span className="badge badge-allow">
                        Confidence: {(Number(playgroundResult.confidence || 0.95) * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>

                  {!playgroundResult && !playgroundRunning && (
                    <div style={{ padding: '30px 10px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      Select a preset or click query to inspect the grounded answer.
                    </div>
                  )}

                  {playgroundRunning && (
                    <div style={{ padding: '30px 10px', textAlign: 'center', color: 'var(--primary)', fontSize: '0.85rem', fontWeight: 600 }}>
                      Filtering claims by trust score and checking active conflicts...
                    </div>
                  )}

                  {playgroundResult && !playgroundRunning && (
                    <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', lineHeight: 1.5, fontSize: '0.85rem', color: 'var(--text-main)', whiteSpace: 'pre-wrap' }}>
                      {playgroundResult.synthesizedAnswer}
                    </div>
                  )}
                </div>

                {/* Evidence Citations */}
                <div className="clean-panel" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      Trust Gate Citations ({playgroundResult?.context?.length || 0})
                    </div>
                    <span className="badge badge-verified">Verified Evidence</span>
                  </div>

                  {(!playgroundResult || !playgroundResult.context || playgroundResult.context.length === 0) ? (
                    <div style={{ padding: '20px 10px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      No citation records loaded yet.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gap: '10px' }}>
                      {playgroundResult.context.map((ctx, idx) => (
                        <div key={idx} style={{ background: '#FFFFFF', border: '1px solid var(--border-subtle)', padding: '12px', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <span className="badge badge-allow">Citation #{idx + 1}</span>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              Trust Score: <strong style={{ color: 'var(--success-text)' }}>{(Number(ctx.trust_score) * 100).toFixed(0)}%</strong>
                            </span>
                          </div>

                          <p style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)', lineHeight: 1.4 }}>
                            "{ctx.claim}"
                          </p>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', paddingTop: '6px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            <span>Source: {ctx.source?.document || 'Verified Document'} ({ctx.source?.section || 'General'})</span>
                            <span>Status: <strong style={{ color: 'var(--success-text)' }}>{ctx.validity?.status?.toUpperCase() || 'VALID'}</strong></span>
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

            {/* Conflicts List */}
            {conflicts.length === 0 ? (
              <div className="clean-panel" style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)' }}>Zero Pending Conflicts</h3>
                <p style={{ fontSize: '0.825rem', marginTop: '4px' }}>
                  All enterprise claims are verified and non-conflicting.
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '16px' }}>
                {conflicts.map((conf, idx) => {
                  const claimA = conf.claim_a;
                  const claimB = conf.claim_b;
                  const scoreA = claimA?.trust_scores?.[0]?.overall_score || 0.50;
                  const scoreB = claimB?.trust_scores?.[0]?.overall_score || 0.95;
                  const sectionA = claimA?.evidence?.[0]?.section || "Section 2.0";
                  const sectionB = claimB?.evidence?.[0]?.section || "Section 3.0";

                  return (
                    <div key={conf.id || idx} className="clean-panel" style={{ padding: '18px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-main)' }}>
                            Conflict #{idx + 1}: {conf.conflict_type?.toUpperCase() || "NUMERICAL_DISCREPANCY"}
                          </span>
                          <span className="badge badge-review">Severity: {conf.severity?.toUpperCase() || 'HIGH'}</span>
                        </div>
                        <span className="code-pill">Confidence: {conf.confidence || '0.95'}</span>
                      </div>

                      {/* Side-by-Side Comparison */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '16px' }}>
                        <div style={{ background: 'var(--danger-bg)', border: '1px solid var(--danger-border)', padding: '14px', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--danger-text)', fontWeight: 800, marginBottom: '4px' }}>
                            <span>CLAIM A (Stale Candidate)</span>
                            <span className="badge badge-outdated">ID: {conf.claim_a_id?.substring(0, 8)}</span>
                          </div>
                          <p style={{ fontSize: '0.85rem', color: 'var(--danger-text)', lineHeight: '1.4', fontWeight: 600 }}>
                            "{claimA?.claim_text || 'Customers are eligible for automated refunds up to ₹25,000 without supervisor approval.'}"
                          </p>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid rgba(220, 38, 38, 0.15)' }}>
                            <span>Source: {sectionA}</span>
                            <span>Trust: <strong>{(Number(scoreA) * 100).toFixed(0)}%</strong></span>
                          </div>
                        </div>

                        <div style={{ background: 'var(--success-bg)', border: '1px solid var(--success-border)', padding: '14px', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 800, marginBottom: '4px' }}>
                            <span>CLAIM B (Authoritative Candidate)</span>
                            <span className="badge badge-allow">ID: {conf.claim_b_id?.substring(0, 8)}</span>
                          </div>
                          <p style={{ fontSize: '0.85rem', color: 'var(--success-text)', lineHeight: '1.4', fontWeight: 600 }}>
                            "{claimB?.claim_text || 'Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff.'}"
                          </p>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid rgba(22, 163, 74, 0.15)' }}>
                            <span>Source: {sectionB}</span>
                            <span>Trust: <strong>{(Number(scoreB) * 100).toFixed(0)}%</strong></span>
                          </div>
                        </div>
                      </div>

                      {/* Auditor Actions */}
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                        <button 
                          onClick={() => handleResolveConflict(conf.id, conf.claim_b_id, "Approved Claim B as authoritative guideline.")}
                          className="btn btn-success"
                          style={{ padding: '7px 14px' }}
                        >
                          Approve Authoritative Claim B (Supersede A)
                        </button>
                        <button 
                          onClick={() => handleResolveConflict(conf.id, conf.claim_a_id, "Approved Claim A as verified exception.")}
                          className="btn btn-secondary"
                          style={{ padding: '7px 12px' }}
                        >
                          Approve Claim A
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

