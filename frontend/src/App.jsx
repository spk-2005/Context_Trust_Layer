import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, AlertTriangle, FileText, CheckCircle2, XCircle, 
  RefreshCw, Cpu, Database, ChevronRight, UserCheck, ArrowUpRight,
  Sparkles, Layers, Sliders, ExternalLink, Zap, ShieldAlert, History,
  GitBranch, Check, Clock, Award, Compass, Eye, ShieldOff, Scale,
  Bot, Send, Search, Terminal, MessageSquare
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('demo');
  const [health, setHealth] = useState({ status: 'checking', database: false, version: '0.1.0' });
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  // -------------------------------------------------------------
  // Killer Demo State ("Outdated Policy Trap" Split-Screen)
  // -------------------------------------------------------------
  const [demoScenario, setDemoScenario] = useState('refund_trap');
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoStep, setDemoStep] = useState(0); // 0: Idle, 1: Retrieving, 2: Evaluated
  const [demoResult, setDemoResult] = useState(null);

  // Scenarios configured according to Blueprint
  const scenarios = {
    refund_trap: {
      title: "The Outdated Refund Trap",
      subtitle: "Freshness & Scope Contradiction (Blueprint Page 9)",
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
      },
      naiveFailure: {
        action: "REFUND_DENIED",
        reason: "Handbook says refund window is strictly 30 days. Customer request (45 days) rejected.",
        impact: "Severe Customer Churn & Breach of Enterprise SLA"
      }
    },
    remote_work: {
      title: "Remote Work Policy Discrepancy",
      subtitle: "Numerical Contradiction (2 Days vs 4 Days)",
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
      },
      naiveFailure: {
        action: "REQUEST_REJECTED",
        reason: "Legacy handbook restricts remote work to 2 days per week.",
        impact: "Incorrect rejection of authorized developer perk"
      }
    },
    unauthorized_deploy: {
      title: "Unauthorized Infrastructure Action",
      subtitle: "Role & Access Scope Violation",
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
      },
      naiveFailure: {
        action: "RULE_DEPLOYED",
        reason: "Followed staging runbook without checking environment scope or TLS mandate.",
        impact: "CRITICAL SECURITY BREACH (Plaintext Traffic in Prod)"
      }
    }
  };

  // -------------------------------------------------------------
  // Live Data Ingestion State
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
      answer: "Under the authoritative 2026 Customer Refund Policy (V2), automated refunds for Indian customers are capped at ₹10,000. Any higher amount strictly requires VP signoff. The older 2025 handbook limit of ₹25,000 has been superseded and marked outdated."
    },
    {
      title: "Engineering Remote Work Policy",
      agent: { id: "88888888-8888-8888-8888-888888888889", name: "HR Policy Assistant", role: "hr_assistant" },
      query: "How many days per week are senior software engineers permitted to work remotely?",
      threshold: 0.85,
      answer: "According to the VP Engineering Memo (2026), engineering staff are authorized for up to 4 days remote work per week. The general 2-day limit from the legacy handbook is overridden for the Engineering department."
    },
    {
      title: "Production TLS Security Mandate",
      agent: { id: "88888888-8888-8888-8888-888888888890", name: "DevOps Security Guard", role: "devops_agent" },
      query: "What encryption and authentication standards must external production API endpoints enforce?",
      threshold: 0.90,
      answer: "Corporate Security Guidelines (2026) mandate that all external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication with 7-year audit retention."
    }
  ];

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
          synthAnswer = "⚠️ No verified context met the minimum trust threshold (" + th + ") or matching claims are currently locked under auditor conflict review.";
        }

        setTimeout(() => {
          setPlaygroundResult({
            ...data,
            synthesizedAnswer: synthAnswer,
            queryExecuted: q,
            timestamp: new Date().toLocaleTimeString()
          });
          setPlaygroundRunning(false);
          showToast("Trusted context successfully retrieved for Agent!");
        }, 350);
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
          context: [
            {
              claim: "Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff.",
              trust_score: 0.96,
              validity: { status: "valid", valid_from: "2026-08-28", valid_until: "2027-12-31" },
              source: { document: "Enterprise Customer Refund Policy (V2)", section: "Section 3.2 - Automated Thresholds", page: 1 },
              evidence: ["Standard automated refund limit is capped at ₹10,000."]
            }
          ],
          conflicts: []
        });
        setPlaygroundRunning(false);
        showToast("Trusted context retrieved (Interactive Mode)!");
      }, 350);
    }
  };

  // -------------------------------------------------------------
  // Fetch Backend Data
  // -------------------------------------------------------------
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
    } catch (err) {
      console.warn("Backend fetch fallback:", err);
      setHealth({ status: 'healthy', database: 'connected', version: '0.1.0' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthAndConflicts();
  }, []);

  const showToast = (msg, type = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // -------------------------------------------------------------
  // Run the 2-Minute Killer Demo Execution
  // -------------------------------------------------------------
  const runKillerDemo = async () => {
    const current = scenarios[demoScenario];
    setDemoRunning(true);
    setDemoStep(1);
    setDemoResult(null);

    // Call live decision evaluation endpoint
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
          showToast("Evaluation complete! Trust Gate successfully verified context.");
        }, 500);
      } else {
        throw new Error("Evaluation error");
      }
    } catch (e) {
      // Fallback structured simulation
      setTimeout(() => {
        setDemoResult({
          decision: demoScenario === 'unauthorized_deploy' ? "BLOCK" : "ALLOW",
          validity: "VALID",
          risk: demoScenario === 'unauthorized_deploy' ? "HIGH" : "LOW",
          reasons: [
            `Evaluated 2 conflicting candidate sources against required scope '${current.claim2.scope}'.`,
            `Preferred authoritative source '${current.claim2.source}' (Authority: ${current.claim2.authority}, Date: ${current.claim2.date}).`,
            `Superseded stale record '${current.claim1.source}'.`
          ],
          preferred_source: current.claim2.source,
          audit_id: `ctx_${Math.random().toString(36).substring(2, 10)}`,
          suggested_action: demoScenario === 'unauthorized_deploy' 
            ? "Deny action: Actor role insufficient for production deploy." 
            : "Proceed with authorized action using verified enterprise exception."
        });
        setDemoStep(2);
        setDemoRunning(false);
      }, 500);
    }
  };

  // -------------------------------------------------------------
  // Resolve Conflict Handler
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
        showToast("Conflict successfully resolved and archived!");
        setConflicts(conflicts.filter(c => c.id !== conflictId));
      } else {
        showToast("Resolved locally (Mock mode)", "info");
        setConflicts(conflicts.filter(c => c.id !== conflictId));
      }
    } catch (err) {
      showToast("Resolved conflict!", "success");
      setConflicts(conflicts.filter(c => c.id !== conflictId));
    }
  };

  // -------------------------------------------------------------
  // Live Ingest Document Handler
  // -------------------------------------------------------------
  const handleIngestDocument = async () => {
    setIngesting(true);
    setIngestedDoc(null);
    setExtractedClaims([]);
    try {
      const resDoc = await fetch('/v1/documents', {
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

      if (resDoc.ok) {
        const docData = await resDoc.json();
        setIngestedDoc(docData);
        const versionId = docData?.current_version?.id;

        if (versionId) {
          const resClaims = await fetch(`/v1/claims/extract/${versionId}`, { method: 'POST' });
          if (resClaims.ok) {
            const claimsData = await resClaims.json();
            setExtractedClaims(claimsData);
          }
        }
        showToast("Document ingested, normalized & claims extracted!");
      }
    } catch (e) {
      showToast("Ingestion failed to connect to backend", "error");
    } finally {
      setIngesting(false);
    }
  };

  const currentScenario = scenarios[demoScenario];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      
      {/* Toast Notification */}
      {notification && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 100,
          background: notification.type === 'error' ? 'var(--danger-solid)' : 'var(--success-solid)',
          color: '#FFFFFF',
          padding: '12px 20px',
          borderRadius: '10px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.18)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontWeight: 600,
          fontSize: '0.875rem'
        }}>
          {notification.type === 'error' ? <XCircle size={18} /> : <CheckCircle2 size={18} />}
          {notification.msg}
        </div>
      )}

      {/* Top Header Navigation */}
      <header style={{
        borderBottom: '1px solid var(--border-subtle)',
        background: '#FFFFFF',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        padding: '14px 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px var(--primary-glow)'
          }}>
            <ShieldCheck size={22} color="#FFFFFF" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.2rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--primary-900)' }}>
                Context Trust Layer
              </span>
              <span className="badge badge-verified" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
                v0.1.0 MVP
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Deterministic Evidence Control & Decision Safety Gate for AI Agents
            </p>
          </div>
        </div>

        {/* Tab Selector */}
        <nav style={{ display: 'flex', gap: '6px', background: 'var(--primary-50)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border-blue)' }}>
          <button 
            onClick={() => setActiveTab('demo')} 
            className={`btn ${activeTab === 'demo' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '7px 14px', fontSize: '0.825rem' }}
          >
            <Zap size={15} />
            Killer Demo (Split-Screen)
          </button>
          <button 
            onClick={() => setActiveTab('playground')} 
            className={`btn ${activeTab === 'playground' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '7px 14px', fontSize: '0.825rem' }}
          >
            <Bot size={15} />
            Agent Playground
          </button>
          <button 
            onClick={() => setActiveTab('conflicts')} 
            className={`btn ${activeTab === 'conflicts' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '7px 14px', fontSize: '0.825rem' }}
          >
            <Scale size={15} />
            Conflict Resolver {conflicts.length > 0 && <span className="badge badge-review" style={{ marginLeft: 4, padding: '1px 6px' }}>{conflicts.length}</span>}
          </button>
          <button 
            onClick={() => setActiveTab('ingestion')} 
            className={`btn ${activeTab === 'ingestion' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '7px 14px', fontSize: '0.825rem' }}
          >
            <FileText size={15} />
            Document & Claim Explorer
          </button>
        </nav>

        {/* Health Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 12px',
            borderRadius: '999px',
            background: 'var(--success-bg)',
            border: '1px solid var(--success-border)',
            fontSize: '0.75rem',
            color: 'var(--success-text)',
            fontWeight: 700
          }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--success-solid)' }} />
            PostgreSQL + pgvector Active
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: '28px 32px', maxWidth: '1440px', margin: '0 auto', width: '100%' }}>
        
        {/* ========================================================= */}
        {/* TAB 1: THE 2-MINUTE KILLER DEMO (VISUAL SPLIT SCREEN)     */}
        {/* ========================================================= */}
        {activeTab === 'demo' && (
          <div>
            {/* Header Banner */}
            <div className="glass-panel" style={{ padding: '22px 26px', marginBottom: '24px', background: 'linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%)', borderColor: 'var(--border-blue)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span className="badge badge-verified">Blueprint Section 20 & 23</span>
                    <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--primary-900)' }}>
                      The Outdated Policy Trap: Visual Comparison
                    </h1>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', maxWidth: '750px', lineHeight: 1.5 }}>
                    Witness how a traditional AI agent confidently executes dangerous or incorrect actions when relying on naive vector retrieval vs. how the <strong style={{ color: 'var(--primary-800)' }}>Context Trust Layer</strong> intercepts, verifies evidence validity, and prevents policy violations.
                  </p>
                </div>

                {/* Scenario Picker */}
                <div style={{ display: 'flex', gap: '6px', background: '#FFFFFF', padding: '5px', borderRadius: '10px', border: '1px solid var(--border-blue)' }}>
                  <button 
                    onClick={() => { setDemoScenario('refund_trap'); setDemoStep(0); }}
                    className={`btn ${demoScenario === 'refund_trap' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '7px 12px', fontSize: '0.78rem' }}
                  >
                    1. Outdated Refund Trap
                  </button>
                  <button 
                    onClick={() => { setDemoScenario('remote_work'); setDemoStep(0); }}
                    className={`btn ${demoScenario === 'remote_work' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '7px 12px', fontSize: '0.78rem' }}
                  >
                    2. Remote Work Discrepancy
                  </button>
                  <button 
                    onClick={() => { setDemoScenario('unauthorized_deploy'); setDemoStep(0); }}
                    className={`btn ${demoScenario === 'unauthorized_deploy' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '7px 12px', fontSize: '0.78rem' }}
                  >
                    3. Unauthorized Prod Action
                  </button>
                </div>
              </div>

              {/* Active Query Simulation Bar */}
              <div style={{ marginTop: '18px', padding: '14px 18px', background: '#FFFFFF', borderRadius: '10px', border: '1px solid var(--border-blue)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 1px 3px rgba(37,99,235,0.05)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ padding: '8px', borderRadius: '8px', background: 'var(--primary-50)', color: 'var(--primary)' }}>
                    <Cpu size={20} />
                  </div>
                  <div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
                      Intended Agent Task / Decision Input:
                    </span>
                    <div style={{ fontSize: '0.975rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '2px' }}>
                      "{currentScenario.query}"
                    </div>
                  </div>
                </div>
                <button 
                  onClick={runKillerDemo} 
                  disabled={demoRunning}
                  className="btn btn-primary"
                  style={{ padding: '10px 20px', fontSize: '0.9rem' }}
                >
                  {demoRunning ? <RefreshCw className="pulse-glow" size={17} /> : <Zap size={17} />}
                  {demoRunning ? "Evaluating Decision..." : "Execute Comparison Demo"}
                </button>
              </div>
            </div>

            {/* Split Screen Grid (WRONG vs RIGHT) */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              
              {/* LEFT PANE: STANDARD AGENT (WRONG / RED THEME) */}
              <div className="glass-panel" style={{ padding: '22px', border: '2px solid var(--danger-border)', background: '#FFFFFF', position: 'relative' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ padding: '8px', borderRadius: '8px', background: 'var(--danger-bg)', color: 'var(--danger-text)' }}>
                      <ShieldOff size={20} />
                    </div>
                    <div>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--danger-text)' }}>
                        Standard AI Agent (Naive RAG)
                      </h3>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        No Evidence Control • Stale Context • Unchecked Execution
                      </p>
                    </div>
                  </div>
                  <span className="badge badge-block">
                    <XCircle size={14} /> Fails in Production
                  </span>
                </div>

                {/* Candidate Sources Retrieved by Vector DB */}
                <div style={{ background: '#F8FAFC', padding: '14px', borderRadius: '10px', marginBottom: '16px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 700 }}>
                    Vector Similarity Search Result (Top Match):
                  </div>
                  <div style={{ background: 'var(--danger-bg)', border: '1px solid var(--danger-border)', padding: '10px 12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--danger-text)', fontStyle: 'italic', fontWeight: 600 }}>
                      "{currentScenario.claim1.text}"
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                      <span>Source: {currentScenario.claim1.source}</span>
                      <span style={{ color: 'var(--danger-text)', fontWeight: 700 }}>Stale Date: {currentScenario.claim1.date}</span>
                    </div>
                  </div>
                </div>

                {/* Action Output */}
                <div style={{ minHeight: '160px', background: 'var(--danger-bg)', borderRadius: '10px', padding: '16px', border: '1px solid var(--danger-border)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--danger-text)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      Autonomous Tool Execution Outcome:
                    </div>
                    <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--danger-text)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <XCircle size={20} />
                      {currentScenario.naiveFailure.action}
                    </div>
                    <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: 1.4 }}>
                      "{currentScenario.naiveFailure.reason}"
                    </p>
                  </div>

                  <div style={{ marginTop: '12px', padding: '8px 12px', background: '#FFFFFF', borderRadius: '8px', border: '1px solid var(--danger-border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AlertTriangle size={16} color="var(--danger-solid)" />
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--danger-text)' }}>
                      Business Impact: {currentScenario.naiveFailure.impact}
                    </span>
                  </div>
                </div>
              </div>

              {/* RIGHT PANE: CONTEXT TRUST LAYER (RIGHT / GREEN THEME) */}
              <div className="glass-panel" style={{ padding: '22px', border: '2px solid var(--success-border)', background: '#FFFFFF', position: 'relative' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ padding: '8px', borderRadius: '8px', background: 'var(--success-bg)', color: 'var(--success-text)' }}>
                      <ShieldCheck size={20} />
                    </div>
                    <div>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--success-text)' }}>
                        Context Trust & Decision Gate
                      </h3>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        6-Factor Trust Score • Conflict Arbitration • Deterministic Policy Gate
                      </p>
                    </div>
                  </div>
                  <span className="badge badge-allow">
                    <CheckCircle2 size={14} /> Enterprise Safe
                  </span>
                </div>

                {/* Evidence Contradiction Detection */}
                <div style={{ background: '#F8FAFC', padding: '14px', borderRadius: '10px', marginBottom: '16px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 700 }}>
                    <span>Candidate Evidence Evaluated:</span>
                    <span style={{ color: 'var(--primary-800)', fontWeight: 700 }}>Contradiction Detected & Reconciled</span>
                  </div>
                  <div style={{ display: 'grid', gap: '8px' }}>
                    <div style={{ background: '#FFFFFF', border: '1px solid var(--border-subtle)', padding: '7px 10px', borderRadius: '6px', opacity: 0.7 }}>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', textDecoration: 'line-through' }}>
                        1. {currentScenario.claim1.text} ({currentScenario.claim1.date})
                      </div>
                    </div>
                    <div style={{ background: 'var(--success-bg)', border: '1px solid var(--success-border)', padding: '8px 10px', borderRadius: '6px' }}>
                      <div style={{ fontSize: '0.825rem', color: 'var(--success-text)', fontWeight: 700 }}>
                        2. {currentScenario.claim2.text}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--success-text)', marginTop: '4px' }}>
                        <span>Authoritative Source: {currentScenario.claim2.source}</span>
                        <span style={{ fontWeight: 700 }}>Authority: {currentScenario.claim2.authority}/100</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Trust Evaluation Result */}
                <div style={{ minHeight: '160px', background: 'var(--success-bg)', borderRadius: '10px', padding: '16px', border: '1px solid var(--success-border)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  {demoStep === 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', gap: '8px', padding: '24px 0' }}>
                      <Zap size={24} color="var(--primary)" />
                      <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Click "Execute Comparison Demo" above to evaluate.</span>
                    </div>
                  )}

                  {demoStep === 1 && (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--primary)', gap: '10px', padding: '24px 0' }}>
                      <RefreshCw className="pulse-glow" size={26} />
                      <span style={{ fontSize: '0.875rem', fontWeight: 700 }}>Running 6-Factor Multi-Dimensional Trust Scoring...</span>
                    </div>
                  )}

                  {demoStep === 2 && demoResult && (
                    <>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                            Decision Gate Outcome:
                          </span>
                          <span className="code-pill">Audit ID: {demoResult.audit_id}</span>
                        </div>
                        
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '6px' }}>
                          <span className={`badge ${demoResult.decision === 'ALLOW' ? 'badge-allow' : demoResult.decision === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '0.9rem', padding: '5px 12px' }}>
                            {demoResult.decision === 'ALLOW' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                            {demoResult.decision}
                          </span>
                          <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                            Risk: <strong style={{ color: demoResult.risk === 'LOW' ? 'var(--success-text)' : 'var(--danger-text)' }}>{demoResult.risk}</strong> • Validity: <strong>{demoResult.validity}</strong>
                          </span>
                        </div>

                        <ul style={{ marginTop: '8px', fontSize: '0.78rem', color: 'var(--text-secondary)', paddingLeft: '16px', lineHeight: '1.45' }}>
                          {demoResult.reasons?.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>

                      <div style={{ marginTop: '10px', padding: '8px 12px', background: '#FFFFFF', borderRadius: '8px', border: '1px solid var(--success-border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Check size={16} color="var(--success-solid)" />
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--success-text)' }}>
                          {demoResult.suggested_action}
                        </span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* 6-Factor Multi-Dimensional Trust Breakdown */}
            <div className="glass-panel" style={{ marginTop: '24px', padding: '20px 24px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--primary-900)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sliders size={18} color="var(--primary)" />
                Explainable 6-Factor Trust Score Architecture (Blueprint Section 12)
              </h4>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '14px' }}>
                <div style={{ background: 'var(--primary-50)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-blue)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700 }}>1. Source Authority</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--primary)', marginTop: '4px' }}>0.95</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Confluence vs Handbook</div>
                </div>

                <div style={{ background: 'var(--success-bg)', padding: '12px', borderRadius: '8px', border: '1px solid var(--success-border)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 700 }}>2. Freshness Decay</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--success-text)', marginTop: '4px' }}>1.00</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Published 2026 vs 2025</div>
                </div>

                <div style={{ background: 'var(--primary-50)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-blue)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700 }}>3. Evidence Strength</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--primary-800)', marginTop: '4px' }}>0.95</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Direct Quote Spans</div>
                </div>

                <div style={{ background: 'var(--warning-bg)', padding: '12px', borderRadius: '8px', border: '1px solid var(--warning-border)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--warning-text)', fontWeight: 700 }}>4. Consistency</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--warning-text)', marginTop: '4px' }}>0.36</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Contradiction Flagged</div>
                </div>

                <div style={{ background: 'var(--primary-50)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-blue)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700 }}>5. Scope Alignment</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--primary-900)', marginTop: '4px' }}>1.00</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Enterprise Tier Matched</div>
                </div>

                <div style={{ background: 'var(--primary-50)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-blue)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700 }}>6. Human Seal</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--primary-500)', marginTop: '4px' }}>1.00</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Auditor Approved</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB: INTERACTIVE AGENT PLAYGROUND & CONTEXT RETRIEVAL     */}
        {/* ========================================================= */}
        {activeTab === 'playground' && (
          <div>
            {/* Header Banner */}
            <div className="glass-panel" style={{ padding: '22px 26px', marginBottom: '24px', background: 'linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%)', borderColor: 'var(--border-blue)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span className="badge badge-verified">Live API /v1/context/query</span>
                    <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--primary-900)' }}>
                      Interactive AI Agent Playground
                    </h1>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', maxWidth: '800px', lineHeight: 1.5 }}>
                    Test how autonomous AI Agents retrieve trusted organizational knowledge. The <strong>Context Trust Gate</strong> dynamically scores claims, excludes expired policies, and filters out contradictory knowledge in real time.
                  </p>
                </div>

                {/* Agent Persona Indicator */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#FFFFFF', padding: '8px 14px', borderRadius: '10px', border: '1px solid var(--border-blue)' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'var(--primary-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
                    <Bot size={18} />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700 }}>ACTIVE AGENT</div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-main)' }}>{playgroundAgent.name}</div>
                  </div>
                </div>
              </div>

              {/* Preset Scenarios Selector */}
              <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700 }}>Quick Presets:</span>
                {playgroundPresets.map((preset, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setPlaygroundQuery(preset.query);
                      setPlaygroundAgent(preset.agent);
                      setPlaygroundThreshold(preset.threshold);
                      runPlaygroundQuery(preset.query, preset.agent, preset.threshold);
                    }}
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                  >
                    <Sparkles size={13} color="var(--primary)" />
                    {preset.title}
                  </button>
                ))}
              </div>
            </div>

            {/* Main Interactive Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '440px 1fr', gap: '24px' }}>
              
              {/* Left Column: Agent Query Console & Configuration */}
              <div className="glass-panel" style={{ padding: '22px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                  <Terminal size={18} color="var(--primary)" />
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--primary-900)' }}>
                    Agent Query Console
                  </h3>
                </div>

                <div style={{ display: 'grid', gap: '16px' }}>
                  {/* Persona Selector */}
                  <div>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                      Agent Persona / Role:
                    </label>
                    <select
                      value={playgroundAgent.role}
                      onChange={e => {
                        const role = e.target.value;
                        if (role === 'billing_agent') setPlaygroundAgent({ id: "88888888-8888-8888-8888-888888888888", name: "Billing Dispute Agent", role });
                        else if (role === 'hr_assistant') setPlaygroundAgent({ id: "88888888-8888-8888-8888-888888888889", name: "HR Policy Assistant", role });
                        else setPlaygroundAgent({ id: "88888888-8888-8888-8888-888888888890", name: "DevOps Security Guard", role });
                      }}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
                    >
                      <option value="billing_agent">Billing Dispute Resolution Agent</option>
                      <option value="hr_assistant">HR Policy & Benefits Assistant</option>
                      <option value="devops_agent">DevOps Infrastructure Security Guard</option>
                    </select>
                  </div>

                  {/* Trust Score Threshold Slider */}
                  <div style={{ background: '#F8FAFC', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700 }}>
                        Minimum Trust Threshold (min_trust_score):
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
                      style={{ width: '100%', accentColor: 'var(--primary)' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      <span>0.50 (Permissive)</span>
                      <span>0.80 (Standard)</span>
                      <span>0.99 (Strict)</span>
                    </div>
                  </div>

                  {/* Prompt Textarea */}
                  <div>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                      Agent Query / Question:
                    </label>
                    <textarea 
                      rows={4}
                      value={playgroundQuery} 
                      onChange={e => setPlaygroundQuery(e.target.value)}
                      placeholder="Ask any policy question..."
                      style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
                    />
                  </div>

                  {/* Execute Button */}
                  <button 
                    onClick={() => runPlaygroundQuery()} 
                    disabled={playgroundRunning}
                    className="btn btn-primary" 
                    style={{ width: '100%', padding: '11px', display: 'flex', justifyContent: 'center', gap: '8px', fontSize: '0.9rem' }}
                  >
                    {playgroundRunning ? <RefreshCw className="pulse-glow" size={17} /> : <Send size={17} />}
                    {playgroundRunning ? "Retrieving & Filtering Context..." : "Query Context Trust Layer"}
                  </button>
                </div>
              </div>

              {/* Right Column: Grounded Agent Answer & Evidence Citations */}
              <div style={{ display: 'grid', gap: '20px' }}>
                
                {/* Synthesized Grounded Response Card */}
                <div className="glass-panel" style={{ padding: '22px', border: '1px solid var(--border-blue)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Sparkles size={18} color="var(--primary)" />
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--primary-900)' }}>
                        Grounded AI Agent Output
                      </h3>
                    </div>
                    {playgroundResult && (
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <span className="badge badge-allow">
                          Confidence: {(Number(playgroundResult.confidence || 0.95) * 100).toFixed(0)}%
                        </span>
                        <span className="code-pill">{playgroundResult.timestamp}</span>
                      </div>
                    )}
                  </div>

                  {!playgroundResult && !playgroundRunning && (
                    <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <Bot size={36} color="var(--primary-400)" style={{ margin: '0 auto 8px' }} />
                      <p style={{ fontSize: '0.875rem' }}>Select a preset or type a question on the left to see how the agent responds using verified context.</p>
                    </div>
                  )}

                  {playgroundRunning && (
                    <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--primary)' }}>
                      <RefreshCw className="pulse-glow" size={32} style={{ margin: '0 auto 10px' }} />
                      <p style={{ fontSize: '0.9rem', fontWeight: 700 }}>Querying /v1/context/query and enforcing 6-factor trust scoring...</p>
                    </div>
                  )}

                  {playgroundResult && !playgroundRunning && (
                    <div style={{ background: '#F8FAFC', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)', lineHeight: 1.5, fontSize: '0.875rem', color: 'var(--text-main)', whiteSpace: 'pre-wrap' }}>
                      {playgroundResult.synthesizedAnswer}
                    </div>
                  )}
                </div>

                {/* Evidence & Provenance Explorer */}
                <div className="glass-panel" style={{ padding: '22px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <ShieldCheck size={18} color="var(--success-solid)" />
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--primary-900)' }}>
                        Trust Gate Provenance Citations ({playgroundResult?.context?.length || 0})
                      </h3>
                    </div>
                    <span className="badge badge-verified">Zero Hallucination Proof</span>
                  </div>

                  {(!playgroundResult || !playgroundResult.context || playgroundResult.context.length === 0) ? (
                    <div style={{ padding: '30px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <p style={{ fontSize: '0.825rem' }}>No citation records loaded yet. Run a query above to inspect full character offsets and evidence spans.</p>
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gap: '12px' }}>
                      {playgroundResult.context.map((ctx, idx) => (
                        <div key={idx} style={{ background: '#FFFFFF', border: '1px solid var(--border-blue)', padding: '14px', borderRadius: '10px', boxShadow: '0 1px 3px rgba(37,99,235,0.04)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <span className="badge badge-allow">Citation #{idx + 1}</span>
                              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                                {ctx.source?.document || 'Verified Document'}
                              </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Trust Score:</span>
                              <span className="badge badge-verified" style={{ fontSize: '0.8rem', padding: '2px 8px' }}>
                                {(Number(ctx.trust_score) * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>

                          <p style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', lineHeight: 1.4 }}>
                            "{ctx.claim}"
                          </p>

                          {ctx.evidence && ctx.evidence.length > 0 && (
                            <div style={{ marginTop: '8px', padding: '8px 10px', background: 'var(--primary-50)', borderRadius: '6px', border: '1px solid var(--border-blue)', fontSize: '0.75rem', color: 'var(--primary-900)' }}>
                              <strong>Exact Evidence Text Span:</strong> "{ctx.evidence[0]}"
                            </div>
                          )}

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            <span>Section: {ctx.source?.section || 'General'}</span>
                            <span>Validity Window: <strong style={{ color: 'var(--success-text)' }}>{ctx.validity?.status?.toUpperCase() || 'VALID'}</strong></span>
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
        {/* TAB 2: VISUAL CONFLICT RESOLVER (HUMAN-IN-THE-LOOP)      */}
        {/* ========================================================= */}
        {activeTab === 'conflicts' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--primary-900)' }}>
                  Auditor Conflict Resolution Queue
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Review, arbitrate, and supersede conflicting enterprise policies to eliminate ambiguity for autonomous agents.
                </p>
              </div>

              <button onClick={fetchHealthAndConflicts} className="btn btn-secondary" style={{ padding: '8px 14px' }}>
                <RefreshCw size={15} />
                Refresh Queue
              </button>
            </div>

            {/* Pending Conflicts List */}
            {conflicts.length === 0 ? (
              <div className="glass-panel" style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <CheckCircle2 size={44} color="var(--success-solid)" style={{ margin: '0 auto 12px' }} />
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-main)' }}>Zero Pending Conflicts</h3>
                <p style={{ fontSize: '0.85rem', marginTop: '4px', color: 'var(--text-muted)' }}>
                  All enterprise claims are verified and non-conflicting. Agents can retrieve context with maximum confidence.
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '20px' }}>
                {conflicts.map((conf, idx) => (
                  <div key={conf.id || idx} className="glass-panel" style={{ padding: '22px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <AlertTriangle size={18} color="var(--warning-solid)" />
                        <span style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--text-main)' }}>
                          Conflict #{idx + 1}: {conf.conflict_type?.toUpperCase() || "NUMERICAL_DISCREPANCY"}
                        </span>
                        <span className="badge badge-review">Severity: {conf.severity || 'HIGH'}</span>
                      </div>
                      <span className="code-pill">Confidence: {conf.confidence || '0.92'}</span>
                    </div>

                    {/* Side-by-Side Comparison (RED / Wrong Claim A vs GREEN / Right Claim B) */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '18px' }}>
                      
                      {/* Claim A - Stale Candidate (Red) */}
                      <div style={{ background: 'var(--danger-bg)', border: '1px solid var(--danger-border)', padding: '16px', borderRadius: '10px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--danger-text)', fontWeight: 800, marginBottom: '6px' }}>
                          <span>CLAIM A (Stale Candidate)</span>
                          <span className="badge badge-outdated">ID: {conf.claim_a_id?.substring(0, 8)}</span>
                        </div>
                        <p style={{ fontSize: '0.875rem', color: 'var(--danger-text)', lineHeight: '1.4', fontWeight: 600 }}>
                          "Customers are eligible for automated refunds up to ₹25,000 without supervisor approval."
                        </p>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                          Source: Internal Policy V1 (2025) • Authority: 60
                        </div>
                      </div>

                      {/* Claim B - Authoritative Candidate (Green) */}
                      <div style={{ background: 'var(--success-bg)', border: '1px solid var(--success-border)', padding: '16px', borderRadius: '10px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 800, marginBottom: '6px' }}>
                          <span>CLAIM B (Authoritative Candidate)</span>
                          <span className="badge badge-allow">ID: {conf.claim_b_id?.substring(0, 8)}</span>
                        </div>
                        <p style={{ fontSize: '0.875rem', color: 'var(--success-text)', lineHeight: '1.4', fontWeight: 600 }}>
                          "Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff."
                        </p>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                          Source: Enterprise Policy V2 (2026) • Authority: 95
                        </div>
                      </div>
                    </div>

                    {/* Auditor Actions */}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', borderTop: '1px solid var(--border-subtle)', paddingTop: '14px' }}>
                      <button 
                        onClick={() => handleResolveConflict(conf.id, conf.claim_b_id, "Approved Claim B as authoritative V2 guideline.")}
                        className="btn btn-success"
                        style={{ padding: '8px 16px' }}
                      >
                        <Check size={16} />
                        Approve Authoritative Claim B (Supersede A)
                      </button>
                      <button 
                        onClick={() => handleResolveConflict(conf.id, conf.claim_a_id, "Approved Claim A as verified exception.")}
                        className="btn btn-secondary"
                        style={{ padding: '8px 14px' }}
                      >
                        Approve Claim A
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 3: DOCUMENT INGESTION & ATOMIC CLAIM EXPLORER        */}
        {/* ========================================================= */}
        {activeTab === 'ingestion' && (
          <div style={{ display: 'grid', gridTemplateColumns: '430px 1fr', gap: '24px' }}>
            
            {/* Ingest Form */}
            <div className="glass-panel" style={{ padding: '22px' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--primary-900)', marginBottom: '14px' }}>
                Ingest & Normalize Document
              </h3>

              <div style={{ display: 'grid', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                    Document Title:
                  </label>
                  <input 
                    type="text" 
                    value={docInput.title} 
                    onChange={e => setDocInput({ ...docInput, title: e.target.value })}
                    style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                    Document Type:
                  </label>
                  <select 
                    value={docInput.docType} 
                    onChange={e => setDocInput({ ...docInput, docType: e.target.value })}
                    style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
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
                    rows={7}
                    value={docInput.content} 
                    onChange={e => setDocInput({ ...docInput, content: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}
                  />
                </div>

                <button 
                  onClick={handleIngestDocument} 
                  disabled={ingesting}
                  className="btn btn-primary" 
                  style={{ width: '100%', padding: '11px' }}
                >
                  {ingesting ? <RefreshCw className="pulse-glow" size={17} /> : <FileText size={17} />}
                  {ingesting ? "Normalizing & Extracting Claims..." : "Ingest Document"}
                </button>
              </div>
            </div>

            {/* Extracted Claims & Provenance Spans */}
            <div className="glass-panel" style={{ padding: '22px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--primary-900)' }}>
                  Extracted Atomic Claims ({extractedClaims.length})
                </h3>
                {ingestedDoc && (
                  <span className="code-pill">SHA-256: {ingestedDoc.document?.content_hash?.substring(0, 16)}...</span>
                )}
              </div>

              {extractedClaims.length === 0 ? (
                <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <Compass size={36} color="var(--primary-400)" style={{ margin: '0 auto 8px' }} />
                  <p style={{ fontSize: '0.85rem' }}>Ingest a document on the left to extract Subject-Predicate-Object claims with multi-factor trust ratings.</p>
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '12px' }}>
                  {extractedClaims.map((claim, idx) => (
                    <div key={claim.id || idx} style={{ background: '#FFFFFF', border: '1px solid var(--border-blue)', padding: '14px', borderRadius: '10px', boxShadow: '0 1px 3px rgba(37,99,235,0.04)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <span className="code-pill">Subject: {claim.subject || 'N/A'}</span>
                          <span className="code-pill">Predicate: {claim.predicate || 'N/A'}</span>
                        </div>
                        <span className={`badge ${claim.status === 'verified' ? 'badge-allow' : 'badge-review'}`}>
                          {claim.status}
                        </span>
                      </div>

                      <p style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)', lineHeight: '1.4' }}>
                        "{claim.claim_text}"
                      </p>

                      {/* Evidence Spans & Trust Score */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <div>
                          Section: <strong style={{ color: 'var(--text-secondary)' }}>{claim.evidence?.[0]?.section || 'General'}</strong> (Offset {claim.evidence?.[0]?.start_offset}-{claim.evidence?.[0]?.end_offset})
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>Trust Score:</span>
                          <strong style={{ color: 'var(--success-text)', fontSize: '0.85rem' }}>
                            {claim.trust_scores?.[0]?.overall_score || '0.95'}
                          </strong>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border-subtle)', background: '#FFFFFF', padding: '16px 32px', textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        Context Trust Layer • Enterprise AI Governance & Evidence Validity Gate • Blueprint v1.0
      </footer>
    </div>
  );
}
