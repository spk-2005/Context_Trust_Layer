import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  X,
  RefreshCw,
  Search,
  Filter,
  DollarSign,
  UserCheck,
  Clock,
  FileText,
  Lock,
  ArrowRight,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function HitlEscalationModal({
  isOpen,
  onClose,
  organizationId,
  showToast
}) {
  const { currentRole, user } = useAuth();
  const [escalations, setEscalations] = useState([]);
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('PENDING'); // 'PENDING' | 'APPROVED' | 'REJECTED' | 'ALL'
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedId, setSelectedId] = useState(null);

  // Adjudication form state
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const orgId = organizationId || '11111111-1111-1111-1111-111111111111';

  // Can the current user resolve HITL escalations?
  // Only 'admin' or 'reviewer' has separation of duties sign-off authorization
  const canResolve = ['admin', 'reviewer'].includes(currentRole);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [escRes, sumRes] = await Promise.all([
        fetch(`/v1/hitl/escalations?organization_id=${orgId}`),
        fetch(`/v1/hitl/summary?organization_id=${orgId}`)
      ]);

      if (escRes.ok) {
        const escData = await escRes.json();
        setEscalations(escData);
        if (escData.length > 0 && !selectedId) {
          // select first pending, or first item
          const firstPending = escData.find(e => e.status === 'PENDING') || escData[0];
          setSelectedId(firstPending.id);
        }
      }

      if (sumRes.ok) {
        const sumData = await sumRes.json();
        setSummary(sumData);
      }
    } catch (err) {
      console.warn('Failed to fetch HITL escalations:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchData();
    }
  }, [isOpen, orgId]);

  if (!isOpen) return null;

  const filteredItems = escalations.filter(item => {
    const matchesStatus = filterStatus === 'ALL' || item.status === filterStatus;
    const matchesSearch =
      !searchQuery ||
      item.action_prompt?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.actor_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.category?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const selectedEscalation = escalations.find(e => e.id === selectedId) || filteredItems[0] || null;

  const handleResolve = async (decision) => {
    if (!selectedEscalation) return;
    if (!canResolve) {
      showToast?.('Unauthorized: Only Risk Auditors or CCO can resolve HITL escalations under Separation of Duties.', 'error');
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await fetch(`/v1/hitl/escalations/${selectedEscalation.id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          notes: resolutionNotes.trim() || (decision === 'APPROVE' ? 'Approved with auditor override under EU AI Act Art. 14' : 'Blocked rogue execution'),
          suggested_action: selectedEscalation.suggested_action
        })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Resolution failed');
      }

      const updated = await res.json();
      setEscalations(prev => prev.map(e => (e.id === updated.id ? updated : e)));
      setResolutionNotes('');
      showToast?.(
        decision === 'APPROVE'
          ? `Escalation ${selectedEscalation.audit_id} approved with override.`
          : `Escalation ${selectedEscalation.audit_id} rejected and blocked.`,
        decision === 'APPROVE' ? 'success' : 'info'
      );
      // Refresh summary
      fetch(`/v1/hitl/summary?organization_id=${orgId}`)
        .then(r => r.ok && r.json())
        .then(data => data && setSummary(data))
        .catch(() => {});
    } catch (err) {
      showToast?.(`Error: ${err.message}`, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'PENDING':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: '#FEF3C7', color: '#B45309', border: '1px solid #FCD34D', padding: '2px 8px', borderRadius: '12px', fontSize: '0.72rem', fontWeight: 700 }}>
            <Clock size={11} /> PENDING REVIEW
          </span>
        );
      case 'APPROVED':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: '#ECFDF5', color: '#047857', border: '1px solid #A7F3D0', padding: '2px 8px', borderRadius: '12px', fontSize: '0.72rem', fontWeight: 700 }}>
            <ShieldCheck size={11} /> APPROVED OVERRIDE
          </span>
        );
      case 'REJECTED':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: '#FEE2E2', color: '#B91C1C', border: '1px solid #FCA5A5', padding: '2px 8px', borderRadius: '12px', fontSize: '0.72rem', fontWeight: 700 }}>
            <XCircle size={11} /> REJECTED / BLOCKED
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(5px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: 'var(--bg-card, #ffffff)',
          color: 'var(--text-main, #1e293b)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '1200px',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.35)',
          border: '1px solid var(--border-subtle, #e2e8f0)',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--border-subtle, #e2e8f0)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'linear-gradient(to right, rgba(99, 102, 241, 0.05), transparent)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #F59E0B, #D97706)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)'
              }}
            >
              <UserCheck size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
                  Human-in-the-Loop (HITL) Decision Escalation Queue
                </h2>
                <span
                  style={{
                    background: '#EEF2FF',
                    color: '#4F46E5',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '6px',
                    border: '1px solid #C7D2FE'
                  }}
                >
                  EU AI Act Art. 14
                </span>
              </div>
              <p style={{ margin: '4px 0 0', fontSize: '0.84rem', color: 'var(--text-muted, #64748b)' }}>
                Mandatory human oversight inbox for out-of-policy agent actions flagged for auditor review prior to execution.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={fetchData}
              className="btn btn-secondary"
              style={{ padding: '7px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}
              title="Refresh queue"
            >
              <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </button>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-muted, #94a3b8)',
                padding: '6px',
                borderRadius: '8px'
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Top Summary KPI Banner */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '12px',
            padding: '14px 24px',
            background: 'var(--bg-subtle, #f8fafc)',
            borderBottom: '1px solid var(--border-subtle, #e2e8f0)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: '#FEF3C7', color: '#D97706', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Clock size={16} />
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted, #64748b)', fontWeight: 600 }}>PENDING TRIAGE</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#D97706' }}>
                {summary?.pending_count ?? 0} incidents
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: '#ECFDF5', color: '#059669', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <DollarSign size={16} />
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted, #64748b)', fontWeight: 600 }}>LIABILITY GUARDED</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#059669' }}>
                ${(summary?.total_liability_prevented_usd ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: '#EEF2FF', color: '#4F46E5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <ShieldCheck size={16} />
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted, #64748b)', fontWeight: 600 }}>ARTICLE 14 OVERSIGHT</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#4F46E5' }}>
                {summary?.eu_act_compliance_rate ?? 100}% Compliant
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: '#F1F5F9', color: '#475569', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <UserCheck size={16} />
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted, #64748b)', fontWeight: 600 }}>TOTAL ESCALATIONS</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-main, #1e293b)' }}>
                {summary?.total_count ?? escalations.length} records
              </div>
            </div>
          </div>
        </div>

        {/* Main Body: 2-Column Layout */}
        <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
          {/* Left Column: Filter & List */}
          <div
            style={{
              width: '380px',
              borderRight: '1px solid var(--border-subtle, #e2e8f0)',
              display: 'flex',
              flexDirection: 'column',
              background: 'var(--bg-main, #ffffff)'
            }}
          >
            {/* Search and Filters */}
            <div style={{ padding: '14px', borderBottom: '1px solid var(--border-subtle, #e2e8f0)' }}>
              <div style={{ position: 'relative', marginBottom: '10px' }}>
                <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted, #94a3b8)' }} />
                <input
                  type="text"
                  placeholder="Search agent, prompt, category..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '7px 10px 7px 32px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle, #cbd5e1)',
                    fontSize: '0.82rem',
                    background: 'var(--bg-card, #ffffff)'
                  }}
                />
              </div>

              {/* Status Tabs */}
              <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-subtle, #f1f5f9)', padding: '3px', borderRadius: '8px' }}>
                {[
                  { key: 'PENDING', label: 'Pending' },
                  { key: 'APPROVED', label: 'Approved' },
                  { key: 'REJECTED', label: 'Rejected' },
                  { key: 'ALL', label: 'All' }
                ].map(tab => (
                  <button
                    key={tab.key}
                    onClick={() => setFilterStatus(tab.key)}
                    style={{
                      flex: 1,
                      padding: '5px 0',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '0.74rem',
                      fontWeight: filterStatus === tab.key ? 700 : 500,
                      background: filterStatus === tab.key ? '#ffffff' : 'transparent',
                      color: filterStatus === tab.key ? '#1e293b' : '#64748b',
                      boxShadow: filterStatus === tab.key ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                      cursor: 'pointer'
                    }}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* List */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
              {isLoading && escalations.length === 0 ? (
                <div style={{ padding: '30px 10px', textAlign: 'center', color: 'var(--text-muted, #94a3b8)', fontSize: '0.85rem' }}>
                  <RefreshCw size={20} className="animate-spin" style={{ margin: '0 auto 8px', display: 'block' }} />
                  Loading escalations...
                </div>
              ) : filteredItems.length === 0 ? (
                <div style={{ padding: '40px 15px', textAlign: 'center', color: 'var(--text-muted, #94a3b8)', fontSize: '0.85rem' }}>
                  No escalations match current filters.
                </div>
              ) : (
                filteredItems.map(item => {
                  const isSelected = selectedEscalation?.id === item.id;
                  return (
                    <div
                      key={item.id}
                      onClick={() => setSelectedId(item.id)}
                      style={{
                        padding: '12px',
                        borderRadius: '10px',
                        marginBottom: '8px',
                        cursor: 'pointer',
                        border: isSelected ? '1.5px solid var(--primary, #4F46E5)' : '1px solid var(--border-subtle, #e2e8f0)',
                        background: isSelected ? 'rgba(79, 70, 229, 0.05)' : 'var(--bg-card, #ffffff)',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        {getStatusBadge(item.status)}
                        <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#059669' }}>
                          ${(item.liability_prevented_usd || 0).toLocaleString()}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.83rem', fontWeight: 600, color: 'var(--text-main, #1e293b)', lineHeight: '1.3', marginBottom: '6px' }}>
                        {item.action_prompt?.length > 80 ? `${item.action_prompt.substring(0, 80)}...` : item.action_prompt}
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-muted, #64748b)' }}>
                        <span style={{ fontFamily: 'monospace' }}>{item.actor_id}</span>
                        <span>{item.category}</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Column: Detailed Adjudication Pane */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--bg-subtle, #f8fafc)', overflowY: 'auto' }}>
            {selectedEscalation ? (
              <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
                {/* Threat Banner & Status */}
                <div style={{ background: '#ffffff', border: '1px solid var(--border-subtle, #e2e8f0)', borderRadius: '12px', padding: '16px 20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted, #64748b)' }}>
                          Audit ID:
                        </span>
                        <code style={{ fontSize: '0.8rem', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', color: '#0f172a' }}>
                          {selectedEscalation.audit_id}
                        </code>
                        <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>•</span>
                        <span style={{ fontSize: '0.76rem', color: 'var(--text-muted, #64748b)' }}>
                          {new Date(selectedEscalation.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main, #0f172a)' }}>
                        {selectedEscalation.category}
                      </div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <div style={{ marginBottom: '4px' }}>{getStatusBadge(selectedEscalation.status)}</div>
                      <div style={{ fontSize: '0.76rem', color: '#059669', fontWeight: 700 }}>
                        ${(selectedEscalation.liability_prevented_usd || 0).toLocaleString()} Loss Avoidance
                      </div>
                    </div>
                  </div>

                  {/* Actor details pills */}
                  <div style={{ display: 'flex', gap: '12px', fontSize: '0.78rem', background: '#f8fafc', padding: '8px 12px', borderRadius: '8px', border: '1px solid #f1f5f9' }}>
                    <div>
                      <span style={{ color: '#64748b' }}>Agent ID: </span>
                      <strong style={{ fontFamily: 'monospace' }}>{selectedEscalation.actor_id}</strong>
                    </div>
                    <div>
                      <span style={{ color: '#64748b' }}>Role: </span>
                      <span style={{ background: '#e2e8f0', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>{selectedEscalation.actor_role}</span>
                    </div>
                  </div>
                </div>

                {/* Agent Action Prompt Box */}
                <div style={{ background: '#ffffff', border: '1px solid var(--border-subtle, #e2e8f0)', borderRadius: '12px', padding: '18px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted, #64748b)', marginBottom: '8px' }}>
                    Agent Proposed Action / Decision Prompt
                  </div>
                  <div
                    style={{
                      background: '#0F172A',
                      color: '#F8FAFC',
                      padding: '14px',
                      borderRadius: '8px',
                      fontSize: '0.88rem',
                      fontFamily: 'monospace',
                      lineHeight: '1.5',
                      whiteSpace: 'pre-wrap'
                    }}
                  >
                    {selectedEscalation.action_prompt}
                  </div>
                </div>

                {/* Deterministic Policy Contradictions / Reasons */}
                <div style={{ background: '#ffffff', border: '1px solid var(--border-subtle, #e2e8f0)', borderRadius: '12px', padding: '18px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', color: '#B91C1C', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertTriangle size={14} /> Deterministic Guardrail Violations & Contradictions
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {selectedEscalation.reasons && selectedEscalation.reasons.length > 0 ? (
                      selectedEscalation.reasons.map((r, i) => (
                        <div
                          key={i}
                          style={{
                            background: '#FEF2F2',
                            border: '1px solid #FECACA',
                            color: '#991B1B',
                            padding: '10px 14px',
                            borderRadius: '8px',
                            fontSize: '0.84rem',
                            lineHeight: '1.4'
                          }}
                        >
                          <strong>#{i + 1}: </strong> {r}
                        </div>
                      ))
                    ) : (
                      <div style={{ fontSize: '0.84rem', color: '#64748b' }}>No explicit reasons recorded.</div>
                    )}
                  </div>

                  {selectedEscalation.suggested_action && (
                    <div style={{ marginTop: '14px', background: '#F0FDF4', border: '1px solid #BBF7D0', padding: '10px 14px', borderRadius: '8px', color: '#166534', fontSize: '0.84rem' }}>
                      <strong>Recommended Guidance: </strong> {selectedEscalation.suggested_action}
                    </div>
                  )}
                </div>

                {/* Auditor Resolution Section */}
                {selectedEscalation.status === 'PENDING' ? (
                  <div style={{ background: '#ffffff', border: '1px solid var(--border-subtle, #e2e8f0)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 6px rgba(0,0,0,0.06)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <div style={{ fontSize: '0.88rem', fontWeight: 800, color: 'var(--text-main, #0f172a)' }}>
                        Human Auditor Sign-Off & Adjudication (Article 14)
                      </div>
                      <span style={{ fontSize: '0.74rem', color: '#64748b' }}>
                        Acting as: <strong style={{ color: 'var(--primary, #4F46E5)' }}>{currentRole}</strong>
                      </span>
                    </div>

                    {!canResolve && (
                      <div style={{ background: '#FFFBEB', border: '1px solid #FDE68A', padding: '10px 14px', borderRadius: '8px', color: '#B45309', fontSize: '0.8rem', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Lock size={14} />
                        <span>
                          <strong>Separation of Duties Guard:</strong> Your active role (<code>{currentRole}</code>) does not have <code>conflicts:resolve</code> authorization. Switch to <strong>reviewer</strong> (Risk Auditor) or <strong>admin</strong> to adjudicate.
                        </span>
                      </div>
                    )}

                    <div style={{ marginBottom: '14px' }}>
                      <label style={{ display: 'block', fontSize: '0.76rem', fontWeight: 700, color: '#475569', marginBottom: '6px' }}>
                        Auditor Justification & Compliance Rationale:
                      </label>
                      <textarea
                        rows={3}
                        placeholder="Provide governance rationale for approval override or permanent rejection (e.g., 'Overridden after HR VP verbal sign-off ticket #889')..."
                        value={resolutionNotes}
                        onChange={(e) => setResolutionNotes(e.target.value)}
                        disabled={!canResolve || isSubmitting}
                        style={{
                          width: '100%',
                          padding: '10px',
                          borderRadius: '8px',
                          border: '1px solid var(--border-subtle, #cbd5e1)',
                          fontSize: '0.84rem',
                          fontFamily: 'inherit',
                          resize: 'vertical',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>

                    <div style={{ display: 'flex', gap: '12px' }}>
                      <button
                        onClick={() => handleResolve('APPROVE')}
                        disabled={!canResolve || isSubmitting}
                        className="btn btn-primary"
                        style={{
                          flex: 1,
                          padding: '10px 16px',
                          background: canResolve ? 'linear-gradient(135deg, #10B981, #059669)' : '#94a3b8',
                          border: 'none',
                          color: '#fff',
                          fontWeight: 700,
                          fontSize: '0.85rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px',
                          cursor: canResolve ? 'pointer' : 'not-allowed'
                        }}
                      >
                        <ShieldCheck size={16} />
                        <span>{isSubmitting ? 'Submitting...' : 'Approve with Override'}</span>
                      </button>

                      <button
                        onClick={() => handleResolve('REJECT')}
                        disabled={!canResolve || isSubmitting}
                        style={{
                          flex: 1,
                          padding: '10px 16px',
                          background: canResolve ? '#EF4444' : '#94a3b8',
                          border: 'none',
                          borderRadius: '8px',
                          color: '#fff',
                          fontWeight: 700,
                          fontSize: '0.85rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px',
                          cursor: canResolve ? 'pointer' : 'not-allowed'
                        }}
                      >
                        <XCircle size={16} />
                        <span>{isSubmitting ? 'Submitting...' : 'Reject & Block Action'}</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ background: '#ffffff', border: '1px solid var(--border-subtle, #e2e8f0)', borderRadius: '12px', padding: '18px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted, #64748b)', marginBottom: '10px' }}>
                      Auditor Resolution Record (Cryptographically Signed)
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px', fontSize: '0.82rem' }}>
                      <div>
                        <span style={{ color: '#64748b' }}>Resolved By: </span>
                        <strong>{selectedEscalation.resolved_by_name || 'Risk Auditor'}</strong>
                        <span style={{ marginLeft: '6px', background: '#e2e8f0', padding: '2px 6px', borderRadius: '4px', fontSize: '0.72rem' }}>
                          {selectedEscalation.resolved_by_role || 'reviewer'}
                        </span>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Resolved At: </span>
                        <strong>{selectedEscalation.resolved_at ? new Date(selectedEscalation.resolved_at).toLocaleString() : 'N/A'}</strong>
                      </div>
                    </div>
                    {selectedEscalation.resolution_notes && (
                      <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '0.84rem' }}>
                        <span style={{ color: '#64748b', fontWeight: 600 }}>Auditor Justification: </span>
                        <span>{selectedEscalation.resolution_notes}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted, #94a3b8)' }}>
                Select an escalation item from the left queue to inspect details and provide human oversight.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
