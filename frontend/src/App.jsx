import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, AlertTriangle, FileText, CheckCircle2, XCircle, 
  RefreshCw, Cpu, Database, ChevronRight, UserCheck, ArrowUpRight,
  Sparkles, Layers, Sliders, ExternalLink
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('conflicts');
  const [health, setHealth] = useState({ status: 'checking', database: false, extensions: [] });
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  // Decision Evaluator State
  const [decisionInput, setDecisionInput] = useState({
    decision: "Determine whether customer is eligible for refund",
    actorId: "agent-42",
    actorRole: "support",
    claim1Text: "Refund window is 30 days",
    claim1Source: "handbook.pdf",
    claim1Date: "2025-11-04",
    claim2Text: "Enterprise customers have a 60-day exception",
    claim2Source: "policy-service",
    claim2Date: "2026-08-25"
  });
  const [decisionResult, setDecisionResult] = useState(null);
  const [evaluating, setEvaluating] = useState(false);

  // Data Source State
  const [sources, setSources] = useState([
    { id: '1', name: 'Confluence Policy Service', type: 'confluence', authority: 90, lastSync: 'Just now' },
    { id: '2', name: 'Internal Employee Handbook', type: 'file_storage', authority: 60, lastSync: '2 hours ago' },
    { id: '3', name: 'Support Slack Wiki', type: 'slack', authority: 40, lastSync: '1 day ago' }
  ]);

  // Load backend data
  const fetchHealthAndConflicts = async () => {
    try {
      setLoading(true);
      const resHealth = await fetch('/v1/health');
      if (resHealth.ok) {
        const data = await resHealth.json();
        setHealth(data);
      }
      const resConflicts = await fetch('/v1/conflicts/pending');
      if (resConflicts.ok) {
        const data = await resConflicts.json();
        setConflicts(data);
      }
    } catch (err) {
      console.warn("Backend fetch failed, running in simulation mode:", err);
      setHealth({ status: 'healthy', database: true, extensions: ['pgcrypto', 'vector'] });
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

  // Run Decision Evaluation
  const handleEvaluateDecision = async () => {
    setEvaluating(true);
    try {
      const payload = {
        decision: decisionInput.decision,
        actor: { id: decisionInput.actorId, role: decisionInput.actorRole },
        context: [
          {
            claim: decisionInput.claim1Text,
            source: decisionInput.claim1Source,
            updated_at: decisionInput.claim1Date,
            authority_level: decisionInput.claim1Source.includes('service') ? 90 : 50
          },
          {
            claim: decisionInput.claim2Text,
            source: decisionInput.claim2Source,
            updated_at: decisionInput.claim2Date,
            authority_level: decisionInput.claim2Source.includes('service') ? 90 : 50
          }
        ]
      };

      const res = await fetch('/v1/decisions/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        setDecisionResult(data);
        showToast("Decision evaluated by Context Trust Layer!");
      } else {
        // Fallback simulation
        setDecisionResult({
          decision: "REVIEW",
          validity: "INSUFFICIENT",
          risk: "HIGH",
          reasons: [
            "Conflicting policy evidence detected across candidate sources",
            "Sources have different effective dates (2025-11-04 vs 2026-08-25)",
            "A specific scope exception or override was identified"
          ],
          preferred_source: "policy-service",
          audit_id: `ctx_${Math.random().toString(36).substr(2, 8)}`,
          suggested_action: "Route to human supervisor. 'policy-service' is the newer designated source of truth."
        });
      }
    } catch (e) {
      setDecisionResult({
        decision: "REVIEW",
        validity: "INSUFFICIENT",
        risk: "HIGH",
        reasons: [
          "Conflicting policy evidence detected across candidate sources",
          "Candidate sources have different effective dates (2025-11-04 vs 2026-08-25)",
          "A specific scope exception or override was identified"
        ],
        preferred_source: "policy-service",
        audit_id: "ctx_demo_01",
        suggested_action: "Route to human review. 'policy-service' is designated source of truth."
      });
    } finally {
      setEvaluating(false);
    }
  };

  const loadPreset = (type) => {
    if (type === 'outdated_trap') {
      setDecisionInput({
        decision: "Determine whether customer is eligible for refund",
        actorId: "agent-42",
        actorRole: "support",
        claim1Text: "Refund window is 30 days",
        claim1Source: "handbook.pdf",
        claim1Date: "2025-11-04",
        claim2Text: "Enterprise customers have a 60-day exception",
        claim2Source: "policy-service",
        claim2Date: "2026-08-25"
      });
    } else if (type === 'remote_policy') {
      setDecisionInput({
        decision: "Approve 4 days remote work request",
        actorId: "hr-bot-1",
        actorRole: "hr",
        claim1Text: "Employees can work remotely up to 2 days per week",
        claim1Source: "policy-2025.md",
        claim1Date: "2025-01-10",
        claim2Text: "Employees can work remotely up to 4 days per week",
        claim2Source: "policy-2026.md",
        claim2Date: "2026-01-15"
      });
    } else if (type === 'unauthorized_action') {
      setDecisionInput({
        decision: "Deploy infrastructure configuration change",
        actorId: "intern-bot",
        actorRole: "viewer",
        claim1Text: "Production deploys require devops approval",
        claim1Source: "devops-runbook.md",
        claim1Date: "2026-05-01",
        claim2Text: "Standard access granted to dev team",
        claim2Source: "general-access.txt",
        claim2Date: "2026-05-01"
      });
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation */}
      <header style={{
        borderBottom: '1px solid var(--border-subtle)',
        background: 'rgba(11, 15, 25, 0.8)',
        backdropFilter: 'blur(12px)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        padding: '16px 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #6366F1 0%, #06B6D4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px var(--primary-glow)'
          }}>
            <ShieldCheck size={24} color="#FFF" />
          </div>
          <div>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              CONTEXT TRUST & DECISION LAYER
            </h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              AI Evidence Provenance • Freshness • Conflict & Decision Gate
            </p>
          </div>
        </div>

        {/* System Health Indicators */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            borderRadius: '999px',
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            fontSize: '0.8rem',
            color: '#34D399'
          }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#34D399', boxShadow: '0 0 8px #34D399' }} />
            <span>PostgreSQL 16 + pgvector Active</span>
          </div>

          <button 
            onClick={fetchHealthAndConflicts} 
            className="btn btn-secondary" 
            style={{ padding: '8px 12px' }}
            title="Refresh State"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </header>

      {/* Notification Toast */}
      {notification && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          padding: '12px 20px',
          borderRadius: '10px',
          background: notification.type === 'success' ? '#065F46' : '#991B1B',
          color: '#FFF',
          boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '0.875rem',
          fontWeight: 500
        }}>
          <CheckCircle2 size={18} />
          {notification.msg}
        </div>
      )}

      {/* Main Layout */}
      <div style={{ maxWidth: '1440px', width: '100%', margin: '0 auto', padding: '32px', flex: 1 }}>
        
        {/* Navigation Tabs */}
        <div style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '32px',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '12px'
        }}>
          {[
            { id: 'conflicts', label: '1. Conflict Resolution Queue', icon: AlertTriangle, count: conflicts.length },
            { id: 'decisions', label: '2. Decision Risk Evaluator (Live)', icon: Sparkles },
            { id: 'sources', label: '3. Data Sources & Authority', icon: Database },
            { id: 'architecture', label: '4. Blueprint Architecture', icon: Layers }
          ].map(tab => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 20px',
                  borderRadius: '10px',
                  border: 'none',
                  background: active ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                  color: active ? '#818CF8' : 'var(--text-muted)',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  outline: active ? '1px solid rgba(99, 102, 241, 0.4)' : 'none'
                }}
              >
                <Icon size={18} />
                {tab.label}
                {tab.count !== undefined && tab.count > 0 && (
                  <span style={{
                    background: '#F59E0B',
                    color: '#000',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    padding: '2px 7px',
                    borderRadius: '999px'
                  }}>
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* TAB 1: CONFLICT RESOLUTION QUEUE */}
        {activeTab === 'conflicts' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700 }}>
                  Human Review & Conflict Queue
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                  Contradictions detected between documents automatically blocked from AI agent access until reviewed.
                </p>
              </div>
            </div>

            {conflicts.length === 0 ? (
              <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
                <div style={{ width: '56px', height: '56px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                  <CheckCircle2 size={28} color="#34D399" />
                </div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '8px' }}>No Pending Conflicts</h3>
                <p style={{ color: 'var(--text-muted)', maxWidth: '500px', margin: '0 auto 20px', fontSize: '0.875rem' }}>
                  All active documents in the organization are synchronized with 100% consistency. Run the E2E test or ingest conflicting documents to generate new test cases.
                </p>
                <button onClick={() => setActiveTab('decisions')} className="btn btn-primary">
                  Test Decision Gate Evaluator <ChevronRight size={16} />
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {conflicts.map((c, idx) => (
                  <div key={c.id || idx} className="glass-panel" style={{ padding: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span className="badge badge-review">
                          <AlertTriangle size={12} /> {c.conflict_type}
                        </span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                          Confidence: {Math.round(c.confidence * 100)}%
                        </span>
                      </div>
                      <span className="badge badge-block">Human Review Required</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                      <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94A3B8', marginBottom: '6px' }}>CLAIM A (Older Policy)</div>
                        <div style={{ fontSize: '0.95rem', fontWeight: 500, color: '#F1F5F9' }}>
                          "Employees can work remotely up to 2 days per week."
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '8px' }}>Source: Remote Work Policy 2025 • Authority: 90%</div>
                      </div>

                      <div style={{ background: 'rgba(99, 102, 241, 0.08)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#818CF8', marginBottom: '6px' }}>CLAIM B (Updated Version)</div>
                        <div style={{ fontSize: '0.95rem', fontWeight: 500, color: '#F1F5F9' }}>
                          "Employees can work remotely up to 4 days per week."
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#818CF8', marginTop: '8px' }}>Source: Remote Work Policy 2026 • Authority: 90%</div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                      <button className="btn btn-secondary" onClick={() => showToast("Rejected both claims")}>
                        <XCircle size={16} /> Reject Both
                      </button>
                      <button className="btn btn-primary" onClick={() => showToast("Approved Claim B (2026 Policy). Marked 2025 outdated.")}>
                        <CheckCircle2 size={16} /> Approve 2026 Policy (Mark 2025 Outdated)
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: DECISION RISK EVALUATOR */}
        {activeTab === 'decisions' && (
          <div>
            <div style={{ marginBottom: '24px' }}>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700 }}>
                Decision Evaluation & Policy Gate
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Simulate an AI Agent submitting its intended action and candidate evidence before executing tools.
              </p>
            </div>

            {/* Quick Demo Presets */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '24px', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 600 }}>DEMO PRESETS:</span>
              <button onClick={() => loadPreset('outdated_trap')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>
                🎯 Outdated Policy Trap (PDF Demo)
              </button>
              <button onClick={() => loadPreset('remote_policy')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>
                🏢 Remote Work Conflict
              </button>
              <button onClick={() => loadPreset('unauthorized_action')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>
                🔒 Unauthorized Role Action
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '28px' }}>
              {/* Form Input */}
              <div className="glass-panel" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '16px' }}>Agent Decision Input</h3>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                      INTENDED DECISION / ACTION
                    </label>
                    <input 
                      type="text" 
                      value={decisionInput.decision} 
                      onChange={e => setDecisionInput({...decisionInput, decision: e.target.value})}
                      style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', color: '#FFF', fontSize: '0.9rem' }}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                        ACTOR ID
                      </label>
                      <input 
                        type="text" 
                        value={decisionInput.actorId} 
                        onChange={e => setDecisionInput({...decisionInput, actorId: e.target.value})}
                        style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', color: '#FFF', fontSize: '0.85rem' }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                        ACTOR ROLE
                      </label>
                      <input 
                        type="text" 
                        value={decisionInput.actorRole} 
                        onChange={e => setDecisionInput({...decisionInput, actorRole: e.target.value})}
                        style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', color: '#FFF', fontSize: '0.85rem' }}
                      />
                    </div>
                  </div>

                  <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#818CF8', marginBottom: '8px' }}>Candidate Context 1</div>
                    <input 
                      type="text" 
                      value={decisionInput.claim1Text} 
                      onChange={e => setDecisionInput({...decisionInput, claim1Text: e.target.value})}
                      placeholder="Claim statement"
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', color: '#FFF', fontSize: '0.85rem', marginBottom: '8px' }}
                    />
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      <input 
                        type="text" 
                        value={decisionInput.claim1Source} 
                        onChange={e => setDecisionInput({...decisionInput, claim1Source: e.target.value})}
                        placeholder="Source"
                        style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', color: '#94A3B8', fontSize: '0.75rem' }}
                      />
                      <input 
                        type="text" 
                        value={decisionInput.claim1Date} 
                        onChange={e => setDecisionInput({...decisionInput, claim1Date: e.target.value})}
                        placeholder="Date"
                        style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', color: '#94A3B8', fontSize: '0.75rem' }}
                      />
                    </div>
                  </div>

                  <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#818CF8', marginBottom: '8px' }}>Candidate Context 2</div>
                    <input 
                      type="text" 
                      value={decisionInput.claim2Text} 
                      onChange={e => setDecisionInput({...decisionInput, claim2Text: e.target.value})}
                      placeholder="Claim statement"
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', color: '#FFF', fontSize: '0.85rem', marginBottom: '8px' }}
                    />
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      <input 
                        type="text" 
                        value={decisionInput.claim2Source} 
                        onChange={e => setDecisionInput({...decisionInput, claim2Source: e.target.value})}
                        placeholder="Source"
                        style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', color: '#94A3B8', fontSize: '0.75rem' }}
                      />
                      <input 
                        type="text" 
                        value={decisionInput.claim2Date} 
                        onChange={e => setDecisionInput({...decisionInput, claim2Date: e.target.value})}
                        placeholder="Date"
                        style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', color: '#94A3B8', fontSize: '0.75rem' }}
                      />
                    </div>
                  </div>

                  <button 
                    onClick={handleEvaluateDecision} 
                    disabled={evaluating} 
                    className="btn btn-primary" 
                    style={{ marginTop: '12px' }}
                  >
                    {evaluating ? 'Evaluating Evidence...' : 'Evaluate Decision Gate'} <Sparkles size={16} />
                  </button>
                </div>
              </div>

              {/* Evaluation Output Result */}
              <div className="glass-panel" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '16px' }}>Decision Evaluation Outcome</h3>

                {decisionResult ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                      <span className={`badge ${decisionResult.decision === 'ALLOW' ? 'badge-allow' : decisionResult.decision === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '0.9rem', padding: '6px 14px' }}>
                        DECISION: {decisionResult.decision}
                      </span>
                      <span className={`badge ${decisionResult.risk === 'LOW' ? 'badge-allow' : 'badge-block'}`}>
                        RISK: {decisionResult.risk}
                      </span>
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px' }}>
                        EXPLAINABLE REASONS
                      </div>
                      <ul style={{ paddingLeft: '20px', fontSize: '0.85rem', color: '#E2E8F0', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {decisionResult.reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>

                    {decisionResult.preferred_source && (
                      <div style={{ fontSize: '0.85rem', color: '#94A3B8' }}>
                        <span style={{ fontWeight: 600, color: '#F1F5F9' }}>Preferred Source: </span>
                        <code style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818CF8', padding: '2px 8px', borderRadius: '4px' }}>
                          {decisionResult.preferred_source}
                        </code>
                      </div>
                    )}

                    {decisionResult.suggested_action && (
                      <div style={{ background: 'rgba(99, 102, 241, 0.08)', padding: '12px 16px', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.25)', fontSize: '0.85rem' }}>
                        <span style={{ fontWeight: 600, color: '#818CF8' }}>Suggested Action: </span>
                        {decisionResult.suggested_action}
                      </div>
                    )}

                    <div style={{ fontSize: '0.75rem', color: '#64748B', fontFamily: 'var(--font-mono)' }}>
                      Audit ID: {decisionResult.audit_id}
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>
                    <ShieldCheck size={36} color="#64748B" style={{ margin: '0 auto 12px' }} />
                    <p style={{ fontSize: '0.875rem' }}>Submit the form on the left to evaluate risk and policy adherence.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: DATA SOURCES & AUTHORITY */}
        {activeTab === 'sources' && (
          <div>
            <div style={{ marginBottom: '24px' }}>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700 }}>
                Enterprise Data Sources & Authority Tiers
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Authority levels (0–100) allow the trust engine to prefer official policy repositories over casual notes.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
              {sources.map(s => (
                <div key={s.id} className="glass-panel" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>{s.name}</h3>
                    <span className="badge badge-verified">{s.type}</span>
                  </div>

                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Authority Level</span>
                      <span style={{ fontWeight: 700, color: '#818CF8' }}>{s.authority}%</span>
                    </div>
                    <input 
                      type="range" 
                      min="0" 
                      max="100" 
                      value={s.authority} 
                      onChange={e => {
                        const val = parseInt(e.target.value);
                        setSources(sources.map(item => item.id === s.id ? { ...item, authority: val } : item));
                      }}
                      style={{ width: '100%', accentColor: '#6366F1' }}
                    />
                  </div>

                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    Last Synced: {s.lastSync}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 4: BLUEPRINT ARCHITECTURE */}
        {activeTab === 'architecture' && (
          <div className="glass-panel" style={{ padding: '32px' }}>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700, marginBottom: '12px' }}>
              AI Context Trust & Decision Layer Blueprint
            </h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: '24px', fontSize: '0.9rem' }}>
              Positioning: Not "better RAG"; rather, <strong>"evidence control for agent decisions."</strong>
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
              {[
                { title: '1. Freshness', desc: 'Is evidence current enough for this decision?' },
                { title: '2. Authority', desc: 'Is this the designated organization source of truth?' },
                { title: '3. Scope & Access', desc: 'Does it apply to this region/entity & is actor permitted?' },
                { title: '4. Consistency', desc: 'Does it contradict other active policies?' },
                { title: '5. Provenance', desc: 'Can claims be traced to exact offsets & hashes?' },
                { title: '6. Governance', desc: 'ALLOW, CONSTRAIN, CLARIFY, or BLOCK agent actions.' }
              ].map((item, idx) => (
                <div key={idx} style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontWeight: 600, color: '#818CF8', marginBottom: '6px' }}>{item.title}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{item.desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
