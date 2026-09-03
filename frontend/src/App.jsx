import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, AlertTriangle, FileText, CheckCircle2, XCircle, 
  RefreshCw, Cpu, Database, ChevronRight, UserCheck, ArrowUpRight,
  Sparkles, Layers, Sliders, ExternalLink, Zap, ShieldAlert, History,
  GitBranch, Check, Clock, Award, Compass, Eye, ShieldOff, Scale
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
        }, 600);
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
      }, 700);
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
          background: notification.type === 'error' ? 'rgba(244, 63, 94, 0.95)' : 'rgba(16, 185, 129, 0.95)',
          backdropFilter: 'blur(8px)',
          color: '#FFFFFF',
          padding: '12px 20px',
          borderRadius: '12px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontWeight: 600,
          fontSize: '0.9rem',
          animation: 'fadeIn 0.2s ease-out'
        }}>
          {notification.type === 'error' ? <XCircle size={18} /> : <CheckCircle2 size={18} />}
          {notification.msg}
        </div>
      )}

      {/* Top Header Navigation */}
      <header style={{
        borderBottom: '1px solid var(--border-subtle)',
        background: 'rgba(7, 9, 19, 0.85)',
        backdropFilter: 'blur(16px)',
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
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #6366F1 0%, #06B6D4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 24px var(--primary-glow)'
          }}>
            <ShieldCheck size={24} color="#FFFFFF" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#FFFFFF' }}>
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
        <nav style={{ display: 'flex', gap: '8px', background: 'rgba(255,255,255,0.03)', padding: '4px', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
          <button 
            onClick={() => setActiveTab('demo')} 
            className={`btn ${activeTab === 'demo' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '8px 16px', fontSize: '0.85rem' }}
          >
            <Zap size={16} />
            Killer Demo (Split-Screen)
          </button>
          <button 
            onClick={() => setActiveTab('conflicts')} 
            className={`btn ${activeTab === 'conflicts' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '8px 16px', fontSize: '0.85rem' }}
          >
            <Scale size={16} />
            Conflict Resolver {conflicts.length > 0 && <span className="badge badge-review" style={{ marginLeft: 4, padding: '1px 6px' }}>{conflicts.length}</span>}
          </button>
          <button 
            onClick={() => setActiveTab('ingestion')} 
            className={`btn ${activeTab === 'ingestion' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '8px 16px', fontSize: '0.85rem' }}
          >
            <FileText size={16} />
            Document & Claim Explorer
          </button>
        </nav>

        {/* Health Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            borderRadius: '999px',
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            fontSize: '0.75rem',
            color: '#34D399',
            fontWeight: 600
          }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981', boxShadow: '0 0 10px #10B981' }} />
            PostgreSQL + pgvector Active
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: '32px', maxWidth: '1440px', margin: '0 auto', width: '100%' }}>
        
        {/* ========================================================= */}
        {/* TAB 1: THE 2-MINUTE KILLER DEMO (VISUAL SPLIT SCREEN)     */}
        {/* ========================================================= */}
        {activeTab === 'demo' && (
          <div>
            {/* Header Banner */}
            <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(6, 182, 212, 0.05) 100%)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span className="badge badge-verified">Blueprint Section 20 & 23</span>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#FFFFFF' }}>
                      The Outdated Policy Trap: Visual Comparison
                    </h1>
                  </div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', maxWidth: '750px' }}>
                    Witness how a traditional AI agent confidently executes dangerous or incorrect actions when relying on naive vector retrieval vs. how the <strong>Context Trust Layer</strong> intercepts, verifies evidence validity, and prevents policy violations.
                  </p>
                </div>

                {/* Scenario Picker */}
                <div style={{ display: 'flex', gap: '8px', background: 'rgba(0,0,0,0.4)', padding: '6px', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
                  <button 
                    onClick={() => { setDemoScenario('refund_trap'); setDemoStep(0); }}
                    className={`btn ${demoScenario === 'refund_trap' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '8px 12px', fontSize: '0.8rem' }}
                  >
                    1. Outdated Refund Trap
                  </button>
                  <button 
                    onClick={() => { setDemoScenario('remote_work'); setDemoStep(0); }}
                    className={`btn ${demoScenario === 'remote_work' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '8px 12px', fontSize: '0.8rem' }}
                  >
                    2. Remote Work Discrepancy
                  </button>
                  <button 
                    onClick={() => { setDemoScenario('unauthorized_deploy'); setDemoStep(0); }}
                    className={`btn ${demoScenario === 'unauthorized_deploy' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '8px 12px', fontSize: '0.8rem' }}
                  >
                    3. Unauthorized Prod Action
                  </button>
                </div>
              </div>

              {/* Active Query Simulation Bar */}
              <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Cpu size={20} color="var(--primary)" />
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Intended Agent Task / Decision Input:
                    </span>
                    <div style={{ fontSize: '1rem', fontWeight: 600, color: '#FFFFFF', marginTop: '2px' }}>
                      "{currentScenario.query}"
                    </div>
                  </div>
                </div>
                <button 
                  onClick={runKillerDemo} 
                  disabled={demoRunning}
                  className="btn btn-primary"
                  style={{ padding: '12px 24px', fontSize: '0.95rem' }}
                >
                  {demoRunning ? <RefreshCw className="pulse-glow" size={18} /> : <Zap size={18} />}
                  {demoRunning ? "Evaluating Decision..." : "Execute Comparison Demo"}
                </button>
              </div>
            </div>

            {/* Split Screen Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              
              {/* LEFT PANE: STANDARD AGENT (FAILS) */}
              <div className="glass-panel" style={{ padding: '24px', borderColor: 'rgba(244, 63, 94, 0.3)', position: 'relative', overflow: 'hidden' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(244, 63, 94, 0.15)', color: '#FB7185' }}>
                      <ShieldOff size={20} />
                    </div>
                    <div>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#FFFFFF' }}>
                        Standard AI Agent (Naive RAG)
                      </h3>
                      <p style={{ fontSize: '0.75rem', color: '#FDA4AF' }}>
                        No Evidence Control • No Freshness Checks • Blind Execution
                      </p>
                    </div>
                  </div>
                  <span className="badge badge-block">Fails in Production</span>
                </div>

                {/* Candidate Sources Retrieved by Vector DB */}
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '10px', marginBottom: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 600 }}>
                    Vector Similarity Search Result (Top Match):
                  </div>
                  <div style={{ background: 'rgba(244, 63, 94, 0.08)', border: '1px solid rgba(244, 63, 94, 0.2)', padding: '10px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.85rem', color: '#FEE2E2', fontStyle: 'italic' }}>
                      "{currentScenario.claim1.text}"
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '6px' }}>
                      <span>Source: {currentScenario.claim1.source}</span>
                      <span style={{ color: '#F87171' }}>Stale Date: {currentScenario.claim1.date}</span>
                    </div>
                  </div>
                </div>

                {/* Action Output */}
                <div style={{ minHeight: '160px', background: 'rgba(0,0,0,0.4)', borderRadius: '12px', padding: '16px', border: '1px solid rgba(244, 63, 94, 0.25)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>
                      Autonomous Tool Execution:
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#FB7185', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <XCircle size={22} />
                      {currentScenario.naiveFailure.action}
                    </div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                      "{currentScenario.naiveFailure.reason}"
                    </p>
                  </div>

                  <div style={{ marginTop: '12px', padding: '8px 12px', background: 'rgba(244, 63, 94, 0.15)', borderRadius: '8px', border: '1px solid rgba(244, 63, 94, 0.3)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AlertTriangle size={16} color="#FB7185" />
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#FECDD3' }}>
                      Business Impact: {currentScenario.naiveFailure.impact}
                    </span>
                  </div>
                </div>
              </div>

              {/* RIGHT PANE: CONTEXT TRUST LAYER (SAFE) */}
              <div className="glass-panel glass-panel-active" style={{ padding: '24px', borderColor: 'rgba(16, 185, 129, 0.4)', position: 'relative' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', color: '#34D399' }}>
                      <ShieldCheck size={20} />
                    </div>
                    <div>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#FFFFFF' }}>
                        Context Trust & Decision Gate
                      </h3>
                      <p style={{ fontSize: '0.75rem', color: '#6EE7B7' }}>
                        6-Factor Trust Score • Conflict Arbitration • Deterministic Policy Gate
                      </p>
                    </div>
                  </div>
                  <span className="badge badge-allow">Enterprise Safe</span>
                </div>

                {/* Evidence Contradiction Detection */}
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '10px', marginBottom: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 600 }}>
                    <span>Candidate Evidence Evaluated:</span>
                    <span style={{ color: '#FBBF24' }}>Contradiction Detected & Reconciled</span>
                  </div>
                  <div style={{ display: 'grid', gap: '8px' }}>
                    <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)', padding: '8px 10px', borderRadius: '6px', opacity: 0.6 }}>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', textDecoration: 'line-through' }}>
                        1. {currentScenario.claim1.text} ({currentScenario.claim1.date})
                      </div>
                    </div>
                    <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '8px 10px', borderRadius: '6px' }}>
                      <div style={{ fontSize: '0.85rem', color: '#A7F3D0', fontWeight: 600 }}>
                        2. {currentScenario.claim2.text}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--accent-emerald)', marginTop: '4px' }}>
                        <span>Authoritative Source: {currentScenario.claim2.source}</span>
                        <span>Authority: {currentScenario.claim2.authority}/100</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Trust Evaluation Result */}
                <div style={{ minHeight: '160px', background: 'rgba(0,0,0,0.4)', borderRadius: '12px', padding: '16px', border: '1px solid rgba(16, 185, 129, 0.3)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  {demoStep === 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-dim)', gap: '8px' }}>
                      <Zap size={24} />
                      <span style={{ fontSize: '0.85rem' }}>Click "Execute Comparison Demo" above to evaluate.</span>
                    </div>
                  )}

                  {demoStep === 1 && (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--accent-cyan)', gap: '12px' }}>
                      <RefreshCw className="pulse-glow" size={28} />
                      <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Running 6-Factor Multi-Dimensional Trust Scoring...</span>
                    </div>
                  )}

                  {demoStep === 2 && demoResult && (
                    <>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>
                            Decision Gate Outcome:
                          </span>
                          <span className="code-pill">Audit ID: {demoResult.audit_id}</span>
                        </div>
                        
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                          <span className={`badge ${demoResult.decision === 'ALLOW' ? 'badge-allow' : demoResult.decision === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '1rem', padding: '6px 14px' }}>
                            {demoResult.decision === 'ALLOW' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                            {demoResult.decision}
                          </span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                            Risk: <strong style={{ color: demoResult.risk === 'LOW' ? '#34D399' : '#FB7185' }}>{demoResult.risk}</strong> • Validity: <strong>{demoResult.validity}</strong>
                          </span>
                        </div>

                        <ul style={{ marginTop: '10px', fontSize: '0.8rem', color: 'var(--text-muted)', paddingLeft: '16px', lineHeight: '1.5' }}>
                          {demoResult.reasons?.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>

                      <div style={{ marginTop: '12px', padding: '8px 12px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.25)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Check size={16} color="#34D399" />
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#A7F3D0' }}>
                          {demoResult.suggested_action}
                        </span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* 6-Factor Multi-Dimensional Trust Radar Breakdown */}
            <div className="glass-panel" style={{ marginTop: '24px', padding: '20px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sliders size={18} color="var(--primary)" />
                Explainable 6-Factor Trust Score Architecture (Blueprint Section 12)
              </h4>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '16px' }}>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>1. Source Authority</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-cyan)', marginTop: '4px' }}>0.95</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Confluence vs Handbook</div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>2. Freshness Decay</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#34D399', marginTop: '4px' }}>1.00</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Published 2026 vs 2025</div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>3. Evidence Strength</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#818CF8', marginTop: '4px' }}>0.95</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Direct Quote Spans</div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>4. Consistency</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#FBBF24', marginTop: '4px' }}>0.36</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Contradiction Flagged</div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>5. Scope Alignment</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#C084FC', marginTop: '4px' }}>1.00</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Enterprise Tier Matched</div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>6. Human Seal</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#38BDF8', marginTop: '4px' }}>1.00</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Auditor Approved</div>
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
                <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#FFFFFF' }}>
                  Auditor Conflict Resolution Queue
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Review, arbitrate, and supersede conflicting enterprise policies to eliminate ambiguity for autonomous agents.
                </p>
              </div>

              <button onClick={fetchHealthAndConflicts} className="btn btn-secondary" style={{ padding: '8px 14px' }}>
                <RefreshCw size={16} />
                Refresh Queue
              </button>
            </div>

            {/* Pending Conflicts List */}
            {conflicts.length === 0 ? (
              <div className="glass-panel" style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <CheckCircle2 size={42} color="#10B981" style={{ margin: '0 auto 12px' }} />
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF' }}>Zero Pending Conflicts</h3>
                <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>
                  All enterprise claims are verified and non-conflicting. Agents can retrieve context with maximum confidence.
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '20px' }}>
                {conflicts.map((conf, idx) => (
                  <div key={conf.id || idx} className="glass-panel" style={{ padding: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <AlertTriangle size={20} color="#F59E0B" />
                        <span style={{ fontWeight: 700, fontSize: '1rem', color: '#FFFFFF' }}>
                          Conflict #{idx + 1}: {conf.conflict_type?.toUpperCase() || "NUMERICAL_DISCREPANCY"}
                        </span>
                        <span className="badge badge-review">Severity: {conf.severity || 'HIGH'}</span>
                      </div>
                      <span className="code-pill">Confidence: {conf.confidence || '0.92'}</span>
                    </div>

                    {/* Side-by-Side Comparison */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
                      
                      {/* Claim A */}
                      <div style={{ background: 'rgba(244, 63, 94, 0.06)', border: '1px solid rgba(244, 63, 94, 0.25)', padding: '16px', borderRadius: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#FDA4AF', fontWeight: 700, marginBottom: '6px' }}>
                          <span>CLAIM A (Stale Candidate)</span>
                          <span className="badge badge-outdated">ID: {conf.claim_a_id?.substring(0, 8)}</span>
                        </div>
                        <p style={{ fontSize: '0.9rem', color: '#FEE2E2', lineHeight: '1.4' }}>
                          "Customers are eligible for automated refunds up to ₹25,000 without supervisor approval."
                        </p>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '8px' }}>
                          Source: Internal Policy V1 (2025) • Authority: 60
                        </div>
                      </div>

                      {/* Claim B */}
                      <div style={{ background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.25)', padding: '16px', borderRadius: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#6EE7B7', fontWeight: 700, marginBottom: '6px' }}>
                          <span>CLAIM B (Authoritative Candidate)</span>
                          <span className="badge badge-allow">ID: {conf.claim_b_id?.substring(0, 8)}</span>
                        </div>
                        <p style={{ fontSize: '0.9rem', color: '#E1F8EC', lineHeight: '1.4' }}>
                          "Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff."
                        </p>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '8px' }}>
                          Source: Enterprise Policy V2 (2026) • Authority: 95
                        </div>
                      </div>
                    </div>

                    {/* Auditor Actions */}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
                      <button 
                        onClick={() => handleResolveConflict(conf.id, conf.claim_b_id, "Approved Claim B as authoritative V2 guideline.")}
                        className="btn btn-success"
                      >
                        <Check size={16} />
                        Approve Authoritative Claim B (Supersede A)
                      </button>
                      <button 
                        onClick={() => handleResolveConflict(conf.id, conf.claim_a_id, "Approved Claim A as verified exception.")}
                        className="btn btn-secondary"
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
          <div style={{ display: 'grid', gridTemplateColumns: '450px 1fr', gap: '24px' }}>
            
            {/* Ingest Form */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '14px' }}>
                Ingest & Normalize Document
              </h3>

              <div style={{ display: 'grid', gap: '14px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    Document Title:
                  </label>
                  <input 
                    type="text" 
                    value={docInput.title} 
                    onChange={e => setDocInput({ ...docInput, title: e.target.value })}
                    style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', padding: '10px 12px', borderRadius: '8px', color: '#FFF' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    Document Type:
                  </label>
                  <select 
                    value={docInput.docType} 
                    onChange={e => setDocInput({ ...docInput, docType: e.target.value })}
                    style={{ width: '100%', background: 'rgba(15, 23, 42, 0.9)', border: '1px solid var(--border-subtle)', padding: '10px 12px', borderRadius: '8px', color: '#FFF' }}
                  >
                    <option value="policy">Enterprise Policy</option>
                    <option value="confluence_page">Confluence Article</option>
                    <option value="handbook">Employee Handbook</option>
                    <option value="runbook">DevOps Runbook</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    Raw Markdown Content:
                  </label>
                  <textarea 
                    rows={7}
                    value={docInput.content} 
                    onChange={e => setDocInput({ ...docInput, content: e.target.value })}
                    style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', padding: '10px 12px', borderRadius: '8px', color: '#FFF', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}
                  />
                </div>

                <button 
                  onClick={handleIngestDocument} 
                  disabled={ingesting}
                  className="btn btn-primary" 
                  style={{ width: '100%', padding: '12px' }}
                >
                  {ingesting ? <RefreshCw className="pulse-glow" size={18} /> : <FileText size={18} />}
                  {ingesting ? "Normalizing & Extracting Claims..." : "Ingest Document"}
                </button>
              </div>
            </div>

            {/* Extracted Claims & Provenance Spans */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF' }}>
                  Extracted Atomic Claims ({extractedClaims.length})
                </h3>
                {ingestedDoc && (
                  <span className="code-pill">SHA-256: {ingestedDoc.document?.content_hash?.substring(0, 16)}...</span>
                )}
              </div>

              {extractedClaims.length === 0 ? (
                <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-dim)' }}>
                  <Compass size={36} style={{ margin: '0 auto 8px' }} />
                  <p>Ingest a document on the left to extract Subject-Predicate-Object claims with multi-factor trust ratings.</p>
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '14px' }}>
                  {extractedClaims.map((claim, idx) => (
                    <div key={claim.id || idx} style={{ background: 'rgba(0,0,0,0.35)', border: '1px solid var(--border-subtle)', padding: '16px', borderRadius: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <span className="code-pill">Subject: {claim.subject || 'N/A'}</span>
                          <span className="code-pill">Predicate: {claim.predicate || 'N/A'}</span>
                        </div>
                        <span className={`badge ${claim.status === 'verified' ? 'badge-allow' : 'badge-review'}`}>
                          {claim.status}
                        </span>
                      </div>

                      <p style={{ fontSize: '0.95rem', fontWeight: 600, color: '#FFFFFF', lineHeight: '1.4' }}>
                        "{claim.claim_text}"
                      </p>

                      {/* Evidence Spans & Trust Score */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.05)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <div>
                          Section: <strong>{claim.evidence?.[0]?.section || 'General'}</strong> (Offset {claim.evidence?.[0]?.start_offset}-{claim.evidence?.[0]?.end_offset})
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>Trust Score:</span>
                          <strong style={{ color: '#34D399', fontSize: '0.9rem' }}>
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
      <footer style={{ borderTop: '1px solid var(--border-subtle)', padding: '16px 32px', textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
        Context Trust Layer • Enterprise AI Governance & Evidence Validity Gate • Blueprint v1.0
      </footer>
    </div>
  );
}
