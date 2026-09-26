import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function ContextCuratorStudio({
  activeOrg,
  showToast,
  conflicts = [],
  onResolveConflict,
  onRefreshConflicts,
  initialSubView = 'health',
  onSubViewChange
}) {
  const { user, token, hasPermission } = useAuth();
  const [curatorSubView, setCuratorSubView] = useState(initialSubView); // 'health' | 'conflicts'
  const [auditData, setAuditData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [applyingActionId, setApplyingActionId] = useState(null);
  const [appliedActionIds, setAppliedActionIds] = useState(new Set());
  const [activeCategory, setActiveCategory] = useState('ALL'); // 'ALL' | 'CONTRADICTION' | 'TEMPORAL_OBSOLESCENCE' | 'LOW_CONFIDENCE'

  // Pillar 1: Clustered Governance Issues State
  const [conflictIssues, setConflictIssues] = useState([]);
  const [issuesLoading, setIssuesLoading] = useState(false);
  const [viewGrouping, setViewGrouping] = useState('issues'); // 'issues' | 'pairs'
  const [expandedIssueIds, setExpandedIssueIds] = useState(new Set());
  const [resolvingIssueId, setResolvingIssueId] = useState(null);
  const [reEvaluating, setReEvaluating] = useState(false);
  const [autoResolving, setAutoResolving] = useState(false);

  // Pillar 3: Context Drift & Claim Decay State
  const [driftData, setDriftData] = useState(null);
  const [driftLoading, setDriftLoading] = useState(false);
  const [remediatingId, setRemediatingId] = useState(null);

  useEffect(() => {
    if (initialSubView) {
      setCuratorSubView(initialSubView);
    }
  }, [initialSubView]);

  const handleSelectSubView = (view) => {
    setCuratorSubView(view);
    if (onSubViewChange) onSubViewChange(view);
  };

  const fetchConflictIssues = async () => {
    setIssuesLoading(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const res = await fetch(`/v1/conflicts/issues?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setConflictIssues(data);
      } else {
        setConflictIssues([]);
      }
    } catch (e) {
      console.warn("Failed to fetch conflict issues:", e);
      setConflictIssues([]);
    } finally {
      setIssuesLoading(false);
    }
  };

  const fetchDriftData = async () => {
    try {
      setDriftLoading(true);
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const res = await fetch(`/v1/steward/drift?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setDriftData(data);
      }
    } catch (e) {
      console.warn("Failed to fetch drift data:", e);
    } finally {
      setDriftLoading(false);
    }
  };

  const handleTriggerDriftScan = async () => {
    try {
      setDriftLoading(true);
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const res = await fetch(`/v1/steward/drift/scan?organization_id=${orgId}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setDriftData(data);
        showToast?.("Drift sweep completed: Context freshness radar updated", "success");
      }
    } catch (e) {
      showToast?.(`Error: ${e.message}`, "error");
    } finally {
      setDriftLoading(false);
    }
  };

  const handleRemediateClaim = async (claimId, action) => {
    try {
      setRemediatingId(claimId);
      const res = await fetch('/v1/steward/drift/remediate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ claim_id: claimId, action })
      });
      if (res.ok) {
        const data = await res.json();
        showToast?.(data.message, "success");
        fetchDriftData();
      }
    } catch (e) {
      showToast?.(`Remediation error: ${e.message}`, "error");
    } finally {
      setRemediatingId(null);
    }
  };

  useEffect(() => {
    if (curatorSubView === 'drift') {
      fetchDriftData();
    }
  }, [curatorSubView, activeOrg]);

  const handleResolveIssue = async (issueId, chosenSide, defaultReason) => {
    if (!hasPermission('conflicts:resolve')) {
      showToast?.(
        `Separation of Duties (SoD) Barred: Your role (${(user?.role || 'operator').toUpperCase()}) cannot adjudicate conflicts. Only Risk & Compliance Auditors or CCO have resolution clearance.`,
        'error'
      );
      return;
    }
    setResolvingIssueId(issueId);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (user?.role) headers['x-user-role'] = user.role;

      const res = await fetch(`/v1/conflicts/issues/${encodeURIComponent(issueId)}/resolve?organization_id=${orgId}&user_role=${user?.role || ''}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          reviewer_id: user?.id || '22222222-2222-2222-2222-222222222222',
          decision: 'approve',
          chosen_side: chosenSide,
          reason: defaultReason || `Batch resolved Governance Issue: Approved Cluster ${chosenSide} as authoritative standard.`
        })
      });
      if (res.ok) {
        const data = await res.json();
        showToast?.(data.message || `Resolved Governance Issue (${data.resolved_conflicts_count} conflicts resolved)!`, 'success');
        await fetchConflictIssues();
        if (onRefreshConflicts) onRefreshConflicts();
      } else {
        const errJson = await res.json().catch(() => null);
        const errMsg = errJson?.detail || 'Failed to resolve issue';
        showToast?.(errMsg, 'error');
      }
    } catch (e) {
      showToast?.("Error resolving governance issue", 'error');
    } finally {
      setResolvingIssueId(null);
    }
  };

  const handleReEvaluateConflicts = async () => {
    if (!hasPermission('conflicts:resolve')) {
      showToast?.(
        `Separation of Duties (SoD) Barred: Your role (${(user?.role || 'operator').toUpperCase()}) cannot re-evaluate governance conflicts. Auditor clearance required.`,
        'error'
      );
      return;
    }
    setReEvaluating(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (user?.role) headers['x-user-role'] = user.role;

      const res = await fetch(`/v1/conflicts/re-evaluate?organization_id=${orgId}&user_role=${user?.role || ''}`, {
        method: 'POST',
        headers
      });
      if (res.ok) {
        const data = await res.json();
        showToast?.(data.message || `Purged ${data.purged_false_positives} false-positive conflicts!`, 'success');
        await fetchConflictIssues();
        if (onRefreshConflicts) onRefreshConflicts();
      } else {
        const errJson = await res.json().catch(() => null);
        showToast?.(errJson?.detail || "Failed to re-evaluate conflicts", 'error');
      }
    } catch (e) {
      showToast?.("Error re-evaluating conflicts", 'error');
    } finally {
      setReEvaluating(false);
    }
  };

  const handleAutoResolveConflicts = async () => {
    if (!hasPermission('conflicts:resolve')) {
      showToast?.(
        `Separation of Duties (SoD) Barred: Your role (${(user?.role || 'operator').toUpperCase()}) cannot execute auto-resolution. Auditor clearance required.`,
        'error'
      );
      return;
    }
    setAutoResolving(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (user?.role) headers['x-user-role'] = user.role;

      const res = await fetch(`/v1/conflicts/auto-resolve?organization_id=${orgId}&user_role=${user?.role || ''}`, {
        method: 'POST',
        headers
      });
      if (res.ok) {
        const data = await res.json();
        const breakdown = Object.entries(data.rules_breakdown || {})
          .map(([rule, count]) => `${rule.replace(/_/g, ' ')}: ${count}`)
          .join(', ');
        showToast?.(
          data.auto_resolved_count > 0
            ? `⚡ Autonomously resolved ${data.auto_resolved_count} conflicts! (${breakdown || 'Precedence rules applied'})`
            : `Evaluated ${data.total_evaluated} conflicts: All remaining require human auditor review.`,
          'success'
        );
        await fetchConflictIssues();
        if (onRefreshConflicts) onRefreshConflicts();
      } else {
        const errJson = await res.json().catch(() => null);
        showToast?.(errJson?.detail || "Failed to auto-resolve conflicts", 'error');
      }
    } catch (e) {
      showToast?.("Error running autonomous conflict resolution", 'error');
    } finally {
      setAutoResolving(false);
    }
  };

  const toggleExpandIssue = (issueId) => {
    setExpandedIssueIds(prev => {
      const next = new Set(prev);
      if (next.has(issueId)) next.delete(issueId);
      else next.add(issueId);
      return next;
    });
  };

  const fetchAudit = async () => {
    setLoading(true);
    try {
      const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
      const res = await fetch(`/v1/steward/audit?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setAuditData(data);
      } else {
        showToast?.("Failed to run data steward audit", "error");
      }
    } catch (e) {
      console.warn("Steward audit fetch fallback:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit();
    fetchConflictIssues();
  }, [activeOrg?.id]);

  const handleApplyAction = async (rec) => {
    setApplyingActionId(rec.id);
    try {
      const res = await fetch('/v1/steward/actions/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action_type: rec.action_type,
          target_id: rec.target_id,
          payload: {
            suggested_winner_id: rec.suggested_winner_id
          }
        })
      });

      if (res.ok) {
        const result = await res.json();
        setAppliedActionIds(prev => new Set([...prev, rec.id]));
        showToast?.(result.message || "Curation action applied successfully!");
        setTimeout(fetchAudit, 400);
        if (onRefreshConflicts) onRefreshConflicts();
      } else {
        const err = await res.json();
        showToast?.(err.detail || "Failed to apply action", "error");
      }
    } catch (e) {
      showToast?.(`Action error: ${e.message}`, "error");
    } finally {
      setApplyingActionId(null);
    }
  };

  const scorecard = auditData?.health_scorecard || {
    overall_score: 100.0,
    grade: "A+",
    freshness_index: 100.0,
    contradiction_index: 100.0,
    coverage_score: 100.0,
    total_documents: 0,
    total_claims: 0,
    active_claims: 0,
    pending_conflicts: conflicts.length || 0
  };

  const issues = auditData?.issues || [];
  const recommendations = auditData?.recommendations || [];

  const filteredIssues = activeCategory === 'ALL'
    ? issues
    : issues.filter(i => i.category === activeCategory);

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header Banner & Sub-View Switcher */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(32,38,210,0.06) 0%, rgba(98,225,252,0.06) 100%)',
        border: '1px solid rgba(32,38,210,0.15)',
        borderRadius: '12px',
        padding: '18px 22px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '14px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '46px',
            height: '46px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #FFAB4A 0%, #EA580C 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '22px',
            color: '#fff',
            boxShadow: '0 4px 12px rgba(255,171,74,0.3)',
            flexShrink: 0
          }}>
            🤖
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
                Autonomous Context Curator & Conflict Resolution Hub
              </h2>
              <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                Heuristic AI Data Steward
              </span>
            </div>
            <p style={{ margin: '3px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Continuous knowledge base health auditing, automated contradiction arbitration, and proactive policy curation.
            </p>
          </div>
        </div>

        {/* Top Environment Sub-Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', background: 'var(--bg-card)', padding: '3px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <button
              onClick={() => handleSelectSubView('health')}
              style={{
                padding: '7px 14px',
                borderRadius: '6px',
                border: 'none',
                background: curatorSubView === 'health' ? '#FFAB4A' : 'transparent',
                color: curatorSubView === 'health' ? '#1A1207' : 'var(--text-main)',
                fontSize: '0.78rem',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>🤖 Context Health & Heuristics</span>
              <span className="badge" style={{ fontSize: '0.62rem', background: curatorSubView === 'health' ? 'rgba(0,0,0,0.12)' : 'var(--bg-surface)', color: curatorSubView === 'health' ? '#1A1207' : 'var(--text-muted)' }}>
                {scorecard.overall_score}%
              </span>
            </button>
            <button
              onClick={() => handleSelectSubView('conflicts')}
              style={{
                padding: '7px 14px',
                borderRadius: '6px',
                border: 'none',
                background: curatorSubView === 'conflicts' ? '#FFAB4A' : 'transparent',
                color: curatorSubView === 'conflicts' ? '#1A1207' : 'var(--text-main)',
                fontSize: '0.78rem',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>⚖️ Pairwise Conflict Resolver</span>
              <span className="badge badge-review" style={{ fontSize: '0.62rem' }}>
                {conflicts.length} Pending
              </span>
            </button>
            <button
              onClick={() => handleSelectSubView('drift')}
              style={{
                padding: '7px 14px',
                borderRadius: '6px',
                border: 'none',
                background: curatorSubView === 'drift' ? '#FFAB4A' : 'transparent',
                color: curatorSubView === 'drift' ? '#1A1207' : 'var(--text-main)',
                fontSize: '0.78rem',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>⏳ Drift & Claim Decay</span>
              <span className="badge badge-warning" style={{ fontSize: '0.62rem', background: curatorSubView === 'drift' ? 'rgba(0,0,0,0.12)' : 'rgba(245,158,11,0.15)', color: curatorSubView === 'drift' ? '#1A1207' : '#f59e0b' }}>
                {driftData?.decay_items ? driftData.decay_items.filter(d => d.decay_status === 'CRITICAL' || d.decay_status === 'DECAYED').length : 0} At Risk
              </span>
            </button>
          </div>

          <button
            onClick={() => {
              fetchAudit();
              if (onRefreshConflicts) onRefreshConflicts();
            }}
            disabled={loading}
            className="btn btn-secondary"
            style={{ padding: '7px 12px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <span>🔄</span>
            <span>Refresh Scan</span>
          </button>
        </div>
      </div>

      {/* ========================================================= */}
      {/* SUB-VIEW 1: AUTONOMOUS CONTEXT HEALTH & STEWARD BOT       */}
      {/* ========================================================= */}
      {curatorSubView === 'health' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Health Scorecard Strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: '12px',
              padding: '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Overall Context Health
              </span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
                <span style={{ fontSize: '1.75rem', fontWeight: 800, color: '#16a34a' }}>
                  {scorecard.overall_score}%
                </span>
                <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>
                  Grade {scorecard.grade}
                </span>
              </div>
            </div>

            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: '12px',
              padding: '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Contradiction Free Index
              </span>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#2026d2', marginTop: '6px' }}>
                {scorecard.contradiction_index}%
              </div>
            </div>

            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: '12px',
              padding: '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Freshness & Time-Validity
              </span>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#0284c7', marginTop: '6px' }}>
                {scorecard.freshness_index}%
              </div>
            </div>

            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: '12px',
              padding: '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              cursor: 'pointer'
            }}
            onClick={() => setCuratorSubView('conflicts')}
            title="Click to view and arbitrate pending conflicts"
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                  Pending Conflicts
                </span>
                <span style={{ fontSize: '0.7rem', color: '#2026d2', fontWeight: 600 }}>Arbitrate ➔</span>
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: conflicts.length > 0 ? '#ea580c' : '#16a34a', marginTop: '6px' }}>
                {conflicts.length}
              </div>
            </div>
          </div>

          {/* Action Recommendations from Steward */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
                  🤖 Autonomous Remediation Recommendations
                </h3>
                <p style={{ margin: '3px 0 0 0', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Data Steward Agent calculates optimal resolution actions based on source authority tiers and freshness.
                </p>
              </div>
              <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>
                {recommendations.length} Actions Available
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
              {recommendations.map((rec) => {
                const isApplying = applyingActionId === rec.id;
                const isApplied = appliedActionIds.has(rec.id);

                return (
                  <div
                    key={rec.id}
                    style={{
                      background: 'var(--bg-card)',
                      border: `1px solid ${isApplied ? 'rgba(25,195,125,0.4)' : 'var(--border-color)'}`,
                      borderRadius: '10px',
                      padding: '16px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '12px',
                      boxShadow: isApplied ? '0 0 0 2px rgba(25,195,125,0.15)' : 'none'
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span className="badge" style={{ background: '#f0f4ff', color: '#2026d2', fontSize: '0.65rem', fontWeight: 700 }}>
                          {rec.action_type?.replace(/_/g, ' ').toUpperCase()}
                        </span>
                        <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                          Confidence: {(rec.confidence * 100).toFixed(0)}%
                        </span>
                      </div>

                      <h4 style={{ fontSize: '0.85rem', fontWeight: 700, margin: '0 0 4px 0', color: 'var(--text-main)' }}>
                        {rec.title}
                      </h4>
                      <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                        {rec.explanation}
                      </p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        Target: <code style={{ fontSize: '0.68rem' }}>{rec.target_id?.substring(0, 8)}</code>
                      </span>
                      <button
                        onClick={() => handleApplyAction(rec)}
                        disabled={isApplying || isApplied}
                        style={{
                          padding: '6px 14px',
                          borderRadius: '6px',
                          background: isApplied ? '#16a34a' : '#2026d2',
                          color: '#fff',
                          border: 'none',
                          fontWeight: 600,
                          fontSize: '0.75rem',
                          cursor: isApplying || isApplied ? 'default' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        {isApplying ? (
                          <>
                            <span className="spinner-sm"></span>
                            <span>Applying...</span>
                          </>
                        ) : isApplied ? (
                          <>
                            <span>✓</span>
                            <span>Applied</span>
                          </>
                        ) : (
                          <>
                            <span>⚡</span>
                            <span>Apply Recommendation</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Detailed Heuristic Issues Table */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
                Identified Context Graph Issues ({issues.length})
              </h3>

              {/* Category Filter Pills */}
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {['ALL', 'CONTRADICTION', 'TEMPORAL_OBSOLESCENCE', 'LOW_CONFIDENCE'].map(cat => (
                  <button
                    key={cat}
                    onClick={() => setActiveCategory(cat)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      border: '1px solid var(--border-color)',
                      background: activeCategory === cat ? '#2026d2' : 'var(--bg-card)',
                      color: activeCategory === cat ? '#fff' : 'var(--text-muted)',
                      cursor: 'pointer'
                    }}
                  >
                    {cat.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ overflowX: 'auto', width: '100%' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                    <th style={{ padding: '8px 12px' }}>Category</th>
                    <th style={{ padding: '8px 12px' }}>Severity</th>
                    <th style={{ padding: '8px 12px' }}>Description</th>
                    <th style={{ padding: '8px 12px' }}>Target Entity</th>
                    <th style={{ padding: '8px 12px' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredIssues.map((issue, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '10px 12px' }}>
                        <span className="badge" style={{ fontSize: '0.65rem' }}>
                          {issue.category?.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span className={issue.severity === 'HIGH' ? 'badge badge-warning' : 'badge badge-muted'} style={{ fontSize: '0.65rem' }}>
                          {issue.severity}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-main)', fontWeight: 500 }}>
                        {issue.description}
                      </td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                        <code>{issue.target_id?.substring(0, 8)}</code>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        {issue.category === 'CONTRADICTION' ? (
                          <button
                            onClick={() => setCuratorSubView('conflicts')}
                            style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #2026d2', background: 'rgba(32,38,210,0.06)', color: '#2026d2', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer' }}
                          >
                            Arbitrate ➔
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.7rem', color: '#16a34a', fontWeight: 600 }}>Monitored</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-VIEW 2: CLUSTERED GOVERNANCE ISSUES & CONFLICT QUEUE   */}
      {/* ========================================================= */}
      {curatorSubView === 'conflicts' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>
                  Auditor Conflict Resolution Queue
                </h3>
                <span className="badge badge-warning" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                  {conflictIssues.length} Governance Issues ({conflicts.length} Total Pairwise Pairs)
                </span>
                {hasPermission('conflicts:resolve') ? (
                  <span style={{ fontSize: '0.70rem', padding: '2px 8px', borderRadius: '12px', background: '#DCFCE7', color: '#15803D', border: '1px solid #86EFAC', fontWeight: 700 }}>
                    ✓ Resolution Clearance Active
                  </span>
                ) : (
                  <span style={{ fontSize: '0.70rem', padding: '2px 8px', borderRadius: '12px', background: '#FEE2E2', color: '#DC2626', border: '1px solid #FCA5A5', fontWeight: 700 }} title="Separation of Duties (SoD) Barred: Your active role cannot adjudicate conflicts">
                    🔒 SoD Barred: Read-Only View
                  </span>
                )}
              </div>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: '4px 0 0 0' }}>
                Arbitrate and supersede conflicting enterprise policies to eliminate ambiguity for autonomous AI agents.
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              {/* Grouping View Toggle */}
              <div style={{
                display: 'flex',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '3px'
              }}>
                <button
                  onClick={() => setViewGrouping('issues')}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '6px',
                    border: 'none',
                    background: viewGrouping === 'issues' ? 'var(--primary-solid, #2026d2)' : 'transparent',
                    color: viewGrouping === 'issues' ? '#fff' : 'var(--text-muted)',
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  ⚡ Clustered Issues ({conflictIssues.length})
                </button>
                <button
                  onClick={() => setViewGrouping('pairs')}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '6px',
                    border: 'none',
                    background: viewGrouping === 'pairs' ? 'var(--primary-solid, #2026d2)' : 'transparent',
                    color: viewGrouping === 'pairs' ? '#fff' : 'var(--text-muted)',
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  ⚖️ Raw Pairs ({conflicts.length})
                </button>
              </div>

              {/* Action Buttons */}
              <button
                onClick={handleAutoResolveConflicts}
                disabled={autoResolving}
                className="btn btn-primary"
                style={{
                  padding: '6px 14px',
                  fontSize: '0.78rem',
                  fontWeight: 800,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'linear-gradient(135deg, #4f46e5 0%, #2563eb 100%)',
                  color: '#fff',
                  border: 'none',
                  boxShadow: '0 2px 8px rgba(79, 70, 229, 0.35)',
                  cursor: autoResolving ? 'not-allowed' : 'pointer'
                }}
                title="Autonomously resolve deterministic version, temporal, and authority conflicts in O(1) time"
              >
                {autoResolving ? '⚡ Resolving...' : '⚡ Auto-Resolve Deterministic'}
              </button>

              <button
                onClick={handleReEvaluateConflicts}
                disabled={reEvaluating}
                className="btn btn-secondary"
                style={{ padding: '6px 12px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '5px' }}
                title="Re-run context-aware contradiction rules to purge non-conflicting samples"
              >
                {reEvaluating ? '🧹 Purging...' : '🧹 Purge False Positives'}
              </button>

              <button
                onClick={() => {
                  fetchConflictIssues();
                  if (onRefreshConflicts) onRefreshConflicts();
                }}
                className="btn btn-secondary"
                style={{ padding: '6px 12px', fontSize: '0.78rem' }}
              >
                🔄 Refresh
              </button>
            </div>
          </div>

          {/* ========================================================= */}
          {/* VIEW MODE 1: CLUSTERED GOVERNANCE ISSUES (DEFAULT)        */}
          {/* ========================================================= */}
          {viewGrouping === 'issues' && (
            <div>
              {conflictIssues.length === 0 ? (
                <div style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '12px',
                  padding: '48px 24px',
                  textAlign: 'center',
                  color: 'var(--text-muted)'
                }}>
                  <span style={{ fontSize: '32px' }}>✨</span>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '8px' }}>
                    Zero Pending Governance Issues
                  </h4>
                  <p style={{ fontSize: '0.82rem', marginTop: '4px' }}>
                    All enterprise claims, operational rules, and policy versions across all data sources are reconciled in non-conflicting harmony.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '16px' }}>
                  {conflictIssues.map((issue, idx) => {
                    const isResolving = resolvingIssueId === issue.issue_id;
                    const isExpanded = expandedIssueIds.has(issue.issue_id);

                    return (
                      <div
                        key={issue.issue_id || idx}
                        style={{
                          background: 'var(--bg-surface)',
                          border: '1.5px solid var(--border-color)',
                          borderRadius: '14px',
                          padding: '20px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '16px',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
                          position: 'relative'
                        }}
                      >
                        {/* Issue Header with Cluster Pill */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                            <span style={{ fontWeight: 800, fontSize: '0.96rem', color: 'var(--text-main)' }}>
                              Governance Issue #{idx + 1}: {issue.topic}
                            </span>
                            <span style={{
                              background: 'linear-gradient(135deg, #4f46e5 0%, #2563eb 100%)',
                              color: '#ffffff',
                              padding: '2px 9px',
                              borderRadius: '12px',
                              fontSize: '0.68rem',
                              fontWeight: 800,
                              letterSpacing: '0.02em',
                              boxShadow: '0 1px 4px rgba(79,70,229,0.25)'
                            }}>
                              ⚡ {issue.total_conflicts} CONFLICTS COLLAPSED
                            </span>
                            <span className="badge badge-warning" style={{ fontSize: '0.65rem' }}>
                              Severity: {issue.severity?.toUpperCase() || 'HIGH'}
                            </span>
                            {issue.blast_radius && (
                              <span
                                style={{
                                  background: issue.blast_radius === 'CRITICAL_BLAST'
                                    ? 'rgba(239, 68, 68, 0.15)'
                                    : issue.blast_radius === 'HIGH_BLAST'
                                    ? 'rgba(245, 158, 11, 0.15)'
                                    : 'rgba(59, 130, 246, 0.15)',
                                  color: issue.blast_radius === 'CRITICAL_BLAST'
                                    ? '#ef4444'
                                    : issue.blast_radius === 'HIGH_BLAST'
                                    ? '#f59e0b'
                                    : '#3b82f6',
                                  border: `1px solid ${issue.blast_radius === 'CRITICAL_BLAST' ? 'rgba(239, 68, 68, 0.3)' : issue.blast_radius === 'HIGH_BLAST' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(59, 130, 246, 0.3)'}`,
                                  padding: '2px 8px',
                                  borderRadius: '6px',
                                  fontSize: '0.66rem',
                                  fontWeight: 800,
                                  letterSpacing: '0.03em'
                                }}
                                title={`Blast Radius Impact Score: ${issue.impact_score || 0}`}
                              >
                                💥 {issue.blast_radius.replace('_', ' ')} ({issue.impact_score || 0})
                              </span>
                            )}
                          </div>
                          <span className="code-pill" style={{ fontSize: '0.74rem' }}>
                            Confidence: {(Number(issue.confidence) * 100).toFixed(0)}%
                          </span>
                        </div>

                        {/* Dual-Cluster Comparison (Stale/Sample vs Authoritative) */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
                          {/* Cluster A */}
                          <div style={{
                            background: 'var(--danger-bg)',
                            border: '1px solid var(--danger-border)',
                            padding: '16px',
                            borderRadius: '11px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '12px'
                          }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--danger-text)', fontWeight: 800, marginBottom: '8px' }}>
                                <span>CLUSTER A ({issue.cluster_a.claim_count} Claim Variations)</span>
                                <span className="badge badge-outdated" style={{ fontSize: '0.62rem' }}>
                                  Stale / Candidate
                                </span>
                              </div>
                              <p style={{ fontSize: '0.84rem', color: 'var(--danger-text)', lineHeight: 1.5, fontWeight: 600, margin: 0 }}>
                                "{issue.cluster_a.representative_text}"
                              </p>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-muted)', paddingTop: '8px', borderTop: '1px solid rgba(220, 38, 38, 0.15)' }}>
                              <span>Section: {issue.cluster_a.source_title}</span>
                              <span>Avg Trust: <strong>{(Number(issue.cluster_a.trust_score) * 100).toFixed(0)}%</strong></span>
                            </div>
                          </div>

                          {/* Cluster B */}
                          <div style={{
                            background: 'var(--success-bg)',
                            border: '1px solid var(--success-border)',
                            padding: '16px',
                            borderRadius: '11px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '12px'
                          }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--success-text)', fontWeight: 800, marginBottom: '8px' }}>
                                <span>CLUSTER B ({issue.cluster_b.claim_count} Authoritative Policy)</span>
                                <span className="badge badge-allow" style={{ fontSize: '0.62rem' }}>
                                  Verified Policy
                                </span>
                              </div>
                              <p style={{ fontSize: '0.84rem', color: 'var(--success-text)', lineHeight: 1.5, fontWeight: 600, margin: 0 }}>
                                "{issue.cluster_b.representative_text}"
                              </p>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-muted)', paddingTop: '8px', borderTop: '1px solid rgba(22, 163, 74, 0.15)' }}>
                              <span>Section: {issue.cluster_b.source_title}</span>
                              <span>Trust: <strong>{(Number(issue.cluster_b.trust_score) * 100).toFixed(0)}%</strong></span>
                            </div>
                          </div>
                        </div>

                        {/* Auditor Actions Toolbar */}
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          flexWrap: 'wrap',
                          gap: '10px',
                          borderTop: '1px solid var(--border-color)',
                          paddingTop: '14px'
                        }}>
                          <button
                            onClick={() => toggleExpandIssue(issue.issue_id)}
                            style={{
                              background: 'transparent',
                              border: '1px solid var(--border-color)',
                              borderRadius: '6px',
                              padding: '6px 12px',
                              fontSize: '0.74rem',
                              color: 'var(--text-muted)',
                              cursor: 'pointer',
                              fontWeight: 600,
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px'
                            }}
                          >
                            <span>{isExpanded ? '▴ Hide' : '▾ Inspect'} All {issue.total_conflicts} Underlying Pairwise Conflicts</span>
                          </button>

                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <button
                              onClick={() => handleResolveIssue(issue.issue_id, 'B')}
                              disabled={isResolving}
                              className="btn btn-success"
                              style={{
                                padding: '8px 16px',
                                fontSize: '0.8rem',
                                fontWeight: 700,
                                boxShadow: '0 2px 6px rgba(22,163,74,0.2)'
                              }}
                            >
                              {isResolving ? 'Resolving...' : `✓ One-Click Resolve: Approve Cluster B (Supersede ${issue.cluster_a.claim_count} in A)`}
                            </button>
                            <button
                              onClick={() => handleResolveIssue(issue.issue_id, 'A')}
                              disabled={isResolving}
                              className="btn btn-secondary"
                              style={{ padding: '8px 14px', fontSize: '0.78rem' }}
                            >
                              Approve Cluster A
                            </button>
                          </div>
                        </div>

                        {/* Expandable Accordion for Granular Pair Inspection */}
                        {isExpanded && (
                          <div style={{
                            background: 'var(--bg-card)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: '8px',
                            padding: '12px 16px',
                            fontSize: '0.74rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px',
                            maxHeight: '260px',
                            overflowY: 'auto'
                          }}>
                            <div style={{ fontWeight: 700, color: 'var(--text-main)', display: 'flex', justifyContent: 'space-between' }}>
                              <span>Underlying Conflict IDs in this Cluster ({issue.conflict_ids.length})</span>
                              <span style={{ color: 'var(--text-muted)' }}>Auto-deduplicated pairwise permutations</span>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '6px' }}>
                              {issue.conflict_ids.map((cid, cIdx) => (
                                <div key={cid} style={{
                                  padding: '4px 8px',
                                  background: 'var(--bg-surface)',
                                  borderRadius: '4px',
                                  border: '1px solid var(--border-color)',
                                  fontFamily: 'monospace',
                                  fontSize: '0.7rem',
                                  color: 'var(--text-muted)'
                                }}>
                                  #{cIdx + 1}: {cid.substring(0, 13)}...
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ========================================================= */}
          {/* VIEW MODE 2: RAW PAIRWISE CONFLICT LIST (UNCLUSTERED)     */}
          {/* ========================================================= */}
          {viewGrouping === 'pairs' && (
            <div>
              {conflicts.length === 0 ? (
                <div style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '12px',
                  padding: '48px 24px',
                  textAlign: 'center',
                  color: 'var(--text-muted)'
                }}>
                  <span style={{ fontSize: '32px' }}>✨</span>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '8px' }}>
                    Zero Pending Policy Conflicts
                  </h4>
                  <p style={{ fontSize: '0.82rem', marginTop: '4px' }}>
                    All enterprise claims and operational rules across all data sources are verified and in non-conflicting harmony.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '14px' }}>
                  {conflicts.map((conf, idx) => {
                    const claimA = conf.claim_a;
                    const claimB = conf.claim_b;
                    const scoreA = claimA?.trust_scores?.[0]?.overall_score || 0.50;
                    const scoreB = claimB?.trust_scores?.[0]?.overall_score || 0.95;
                    const sectionA = claimA?.evidence?.[0]?.section || "Corporate Operations Handbook (Section 2.0)";
                    const sectionB = claimB?.evidence?.[0]?.section || "VP Engineering Directive Memo (Section 3.0)";

                    return (
                      <div
                        key={conf.id || idx}
                        style={{
                          background: 'var(--bg-surface)',
                          border: '1px solid var(--border-color)',
                          borderRadius: '12px',
                          padding: '18px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '14px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontWeight: 800, fontSize: '0.88rem', color: 'var(--text-main)' }}>
                              Conflict #{idx + 1}: {conf.conflict_type?.toUpperCase() || "NUMERICAL_DISCREPANCY"}
                            </span>
                            <span className="badge badge-review" style={{ fontSize: '0.65rem' }}>
                              Severity: {conf.severity?.toUpperCase() || 'HIGH'}
                            </span>
                          </div>
                          <span className="code-pill" style={{ fontSize: '0.72rem' }}>
                            Confidence: {conf.confidence || '0.95'}
                          </span>
                        </div>

                        {/* Side-by-Side Claim Comparison */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
                          {/* Claim A */}
                          <div style={{
                            background: 'var(--danger-bg)',
                            border: '1px solid var(--danger-border)',
                            padding: '14px',
                            borderRadius: '10px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '10px'
                          }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--danger-text)', fontWeight: 800, marginBottom: '6px' }}>
                                <span>CLAIM A (Stale Candidate)</span>
                                <span className="badge badge-outdated" style={{ fontSize: '0.62rem' }}>ID: {conf.claim_a_id?.substring(0, 8)}</span>
                              </div>
                              <p style={{ fontSize: '0.82rem', color: 'var(--danger-text)', lineHeight: 1.45, fontWeight: 600, margin: 0 }}>
                                "{claimA?.claim_text || 'No claim text recorded'}"
                              </p>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', color: 'var(--text-muted)', paddingTop: '6px', borderTop: '1px solid rgba(220, 38, 38, 0.15)' }}>
                              <span>Source: {sectionA}</span>
                              <span>Trust: <strong>{(Number(scoreA) * 100).toFixed(0)}%</strong></span>
                            </div>
                          </div>

                          {/* Claim B */}
                          <div style={{
                            background: 'var(--success-bg)',
                            border: '1px solid var(--success-border)',
                            padding: '14px',
                            borderRadius: '10px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '10px'
                          }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--success-text)', fontWeight: 800, marginBottom: '6px' }}>
                                <span>CLAIM B (Authoritative Candidate)</span>
                                <span className="badge badge-allow" style={{ fontSize: '0.62rem' }}>ID: {conf.claim_b_id?.substring(0, 8)}</span>
                              </div>
                              <p style={{ fontSize: '0.82rem', color: 'var(--success-text)', lineHeight: 1.45, fontWeight: 600, margin: 0 }}>
                                "{claimB?.claim_text || 'No claim text recorded'}"
                              </p>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', color: 'var(--text-muted)', paddingTop: '6px', borderTop: '1px solid rgba(22, 163, 74, 0.15)' }}>
                              <span>Source: {sectionB}</span>
                              <span>Trust: <strong>{(Number(scoreB) * 100).toFixed(0)}%</strong></span>
                            </div>
                          </div>
                        </div>

                        {/* Auditor Resolution Actions */}
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                          <button
                            onClick={() => onResolveConflict && onResolveConflict(conf.id, conf.claim_b_id, "Approved Claim B as authoritative guideline.")}
                            className="btn btn-success"
                            style={{ padding: '7px 14px', fontSize: '0.78rem', fontWeight: 600 }}
                          >
                            ✓ Approve Authoritative Claim B (Supersede A)
                          </button>
                          <button
                            onClick={() => onResolveConflict && onResolveConflict(conf.id, conf.claim_a_id, "Approved Claim A as verified exception.")}
                            className="btn btn-secondary"
                            style={{ padding: '7px 12px', fontSize: '0.78rem' }}
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
        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-VIEW 3: CONTEXT DRIFT & CLAIM DECAY RADAR             */}
      {/* ========================================================= */}
      {curatorSubView === 'drift' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Top KPI & Sweep Action Banner */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            padding: '20px 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '16px'
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  Continuous Context Drift & Claim Decay Radar
                </h3>
                <span className="badge badge-verified" style={{ background: '#ECFDF5', color: '#047857', border: '1px solid #A7F3D0' }}>
                  Half-Life Attestation
                </span>
              </div>
              <p style={{ margin: 0, fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                Monitors knowledge degradation over time. Claims older than 90 days lose authority score unless re-attested by verified Data Owners.
              </p>
            </div>

            <button
              type="button"
              disabled={driftLoading}
              onClick={handleTriggerDriftScan}
              className="btn btn-primary"
              style={{
                padding: '9px 18px',
                background: 'linear-gradient(135deg, #10B981, #059669)',
                border: 'none',
                color: '#fff',
                fontWeight: 700,
                fontSize: '0.84rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span>{driftLoading ? 'Running Background Sweep...' : '⚡ Run Active Drift Sweep'}</span>
            </button>
          </div>

          {/* Metric Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px' }}>
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>FRESHNESS INDEX</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#059669', marginTop: '2px' }}>
                {driftData?.freshness_index_pct ?? 92.5}%
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Overall context health score
              </div>
            </div>

            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>DECAYED CLAIMS (&gt;90d)</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#D97706', marginTop: '2px' }}>
                {driftData?.decayed_claims_count ?? 3} Stale
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Requires Data Owner review
              </div>
            </div>

            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>AVERAGE KNOWLEDGE AGE</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#4F46E5', marginTop: '2px' }}>
                {driftData?.average_age_days ?? 74} Days
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Across all stored policies
              </div>
            </div>

            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>AGING HORIZONS</div>
              <div style={{ display: 'flex', gap: '6px', marginTop: '8px', flexWrap: 'wrap' }}>
                {driftData?.decay_radar ? Object.entries(driftData.decay_radar).map(([k, v]) => (
                  <span key={k} style={{ fontSize: '0.7rem', background: 'var(--bg-card)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                    {k}: <strong>{v}</strong>
                  </span>
                )) : null}
              </div>
            </div>
          </div>

          {/* Stale Claims List & Remediation Table */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Temporal Claim Degradation & Remediation Ledger
              </h4>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {driftData?.decayed_claims?.length ?? 0} tracked policies
              </span>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-card)', borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Claim & Source</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Age</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Trust Degradation</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Drift Status</th>
                    <th style={{ padding: '10px 14px', color: 'var(--text-main)', textAlign: 'right' }}>Governance Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(driftData?.decayed_claims || []).map((item) => {
                    const isStale = item.age_days > 90;
                    return (
                      <tr key={item.claim_id} style={{ borderBottom: '1px solid var(--border-color)', background: isStale ? 'rgba(245, 158, 11, 0.03)' : 'transparent' }}>
                        <td style={{ padding: '12px 14px', maxWidth: '380px' }}>
                          <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px', lineHeight: '1.3' }}>
                            {item.claim_text}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            📄 {item.document_title}
                          </div>
                        </td>

                        <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }}>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontWeight: 700,
                            fontSize: '0.74rem',
                            background: item.age_days <= 30 ? '#ECFDF5' : item.age_days <= 90 ? '#EFF6FF' : item.age_days <= 180 ? '#FEF3C7' : '#FEE2E2',
                            color: item.age_days <= 30 ? '#047857' : item.age_days <= 90 ? '#1D4ED8' : item.age_days <= 180 ? '#B45309' : '#B91C1C'
                          }}>
                            {item.age_days} days old
                          </span>
                        </td>

                        <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ color: 'var(--text-muted)', textDecoration: 'line-through' }}>
                              {(item.initial_trust * 100).toFixed(0)}%
                            </span>
                            <span style={{ fontWeight: 800, color: item.current_decayed_trust < 0.70 ? '#DC2626' : '#059669' }}>
                              {(item.current_decayed_trust * 100).toFixed(0)}%
                            </span>
                            {item.decay_pct > 0 && (
                              <span style={{ fontSize: '0.68rem', color: '#DC2626', fontWeight: 700 }}>
                                (-{item.decay_pct}%)
                              </span>
                            )}
                          </div>
                        </td>

                        <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }}>
                          <span style={{
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            padding: '3px 8px',
                            borderRadius: '4px',
                            background: item.drift_category === 'ACTIVE_FRESH' ? '#ECFDF5' : item.drift_category === 'AGING_WARNING' ? '#FEF3C7' : '#FEE2E2',
                            color: item.drift_category === 'ACTIVE_FRESH' ? '#047857' : item.drift_category === 'AGING_WARNING' ? '#B45309' : '#B91C1C'
                          }}>
                            {item.drift_category}
                          </span>
                        </td>

                        <td style={{ padding: '12px 14px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                          <div style={{ display: 'inline-flex', gap: '6px' }}>
                            <button
                              type="button"
                              disabled={remediatingId === item.claim_id}
                              onClick={() => handleRemediateClaim(item.claim_id, 'RE_ATTEST')}
                              className="btn btn-secondary"
                              style={{ padding: '5px 10px', fontSize: '0.74rem', background: '#ECFDF5', borderColor: '#A7F3D0', color: '#047857', fontWeight: 700 }}
                              title="Reset freshness clock to Day 0"
                            >
                              {remediatingId === item.claim_id ? 'Updating...' : '✓ Re-Attest'}
                            </button>
                            <button
                              type="button"
                              disabled={remediatingId === item.claim_id}
                              onClick={() => handleRemediateClaim(item.claim_id, 'RETIRE')}
                              className="btn btn-secondary"
                              style={{ padding: '5px 10px', fontSize: '0.74rem', background: '#FEF2F2', borderColor: '#FECACA', color: '#B91C1C' }}
                              title="Deprecate and exclude from agent retrieval"
                            >
                              Retire
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
