import React, { useState, useEffect } from 'react';

export default function ContextCuratorStudio({
  activeOrg,
  showToast,
  conflicts = [],
  onResolveConflict,
  onRefreshConflicts,
  initialSubView = 'health',
  onSubViewChange
}) {
  const [curatorSubView, setCuratorSubView] = useState(initialSubView); // 'health' | 'conflicts'
  const [auditData, setAuditData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [applyingActionId, setApplyingActionId] = useState(null);
  const [appliedActionIds, setAppliedActionIds] = useState(new Set());
  const [activeCategory, setActiveCategory] = useState('ALL'); // 'ALL' | 'CONTRADICTION' | 'TEMPORAL_OBSOLESCENCE' | 'LOW_CONFIDENCE'

  useEffect(() => {
    if (initialSubView) {
      setCuratorSubView(initialSubView);
    }
  }, [initialSubView]);

  const handleSelectSubView = (view) => {
    setCuratorSubView(view);
    if (onSubViewChange) onSubViewChange(view);
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
            background: 'linear-gradient(135deg, #19c37d 0%, #2026d2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '22px',
            color: '#fff',
            boxShadow: '0 4px 12px rgba(25,195,125,0.25)',
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
                background: curatorSubView === 'health' ? '#2026d2' : 'transparent',
                color: curatorSubView === 'health' ? '#fff' : 'var(--text-main)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>🤖 Context Health & Heuristics</span>
              <span className="badge" style={{ fontSize: '0.62rem', background: curatorSubView === 'health' ? 'rgba(255,255,255,0.25)' : 'var(--bg-surface)', color: curatorSubView === 'health' ? '#fff' : 'var(--text-muted)' }}>
                {scorecard.overall_score}%
              </span>
            </button>
            <button
              onClick={() => handleSelectSubView('conflicts')}
              style={{
                padding: '7px 14px',
                borderRadius: '6px',
                border: 'none',
                background: curatorSubView === 'conflicts' ? '#2026d2' : 'transparent',
                color: curatorSubView === 'conflicts' ? '#fff' : 'var(--text-main)',
                fontSize: '0.78rem',
                fontWeight: 600,
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
      {/* SUB-VIEW 2: PAIRWISE CONFLICT RESOLUTION QUEUE           */}
      {/* ========================================================= */}
      {curatorSubView === 'conflicts' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>
                Auditor Conflict Resolution Queue ({conflicts.length} Pending)
              </h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: '3px 0 0 0' }}>
                Review, arbitrate, and supersede conflicting enterprise policies to eliminate ambiguity for autonomous agents.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={onRefreshConflicts}
                className="btn btn-secondary"
                style={{ padding: '6px 12px', fontSize: '0.78rem' }}
              >
                Refresh Queue
              </button>
            </div>
          </div>

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
  );
}
