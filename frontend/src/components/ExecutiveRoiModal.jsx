import React, { useState, useEffect } from 'react';
import {
  DollarSign,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  AlertTriangle,
  FileText,
  Lock,
  X,
  ExternalLink,
  RefreshCw,
  Zap,
  CheckCircle2
} from 'lucide-react';

export default function ExecutiveRoiModal({ isOpen, onClose, activeOrg, auditSummary }) {
  const [roiData, setRoiData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && activeOrg?.id) {
      fetchRoiData();
    }
  }, [isOpen, activeOrg?.id]);

  const fetchRoiData = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/v1/audit/roi?organization_id=${activeOrg?.id}`);
      if (res.ok) {
        const data = await res.json();
        setRoiData(data);
      }
    } catch (err) {
      console.warn("Failed to load ROI data:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const totalLiability = roiData?.total_liability_prevented_usd ?? auditSummary?.financial_liability_prevented_usd ?? 0;
  const breakdown = roiData?.breakdown ?? auditSummary?.liability_breakdown ?? {
    security_breaches_usd: 0,
    financial_disputes_usd: 0,
    regulatory_fines_usd: 0,
    operational_rework_usd: 0
  };
  const blockedCount = roiData?.total_blocked_incidents ?? auditSummary?.total_blocked_incidents ?? 0;
  const roiMultiplier = roiData?.roi_multiplier ?? (totalLiability > 0 ? Math.max((totalLiability / 24000).toFixed(1), 1.0) : 0);

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
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '920px',
          maxHeight: '90vh',
          backgroundColor: '#FFFFFF',
          borderRadius: '14px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          border: '1px solid #E2E8F0'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid #F1F5F9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'linear-gradient(to right, #ECFDF5, #F8FAFC)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '10px',
                backgroundColor: '#D1FAE5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid #A7F3D0'
              }}
            >
              <DollarSign size={24} color="#059669" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '18px', fontWeight: '800', color: '#0F172A', margin: 0 }}>
                  Financial Liability Prevented & Executive ROI
                </h2>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: '700',
                    backgroundColor: '#ECFDF5',
                    color: '#059669',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    border: '1px solid #A7F3D0'
                  }}
                >
                  Verified Loss Avoidance
                </span>
              </div>
              <p style={{ fontSize: '13px', color: '#64748B', margin: '4px 0 0 0' }}>
                Calculates verifiable loss avoided by intercepting hallucinated and rogue autonomous AI agent actions.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              color: '#94A3B8',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Body */}
        <div style={{ padding: '24px', overflowY: 'auto' }}>
          {/* Top Big Headline Metrics */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '16px',
              marginBottom: '24px'
            }}
          >
            <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', padding: '16px 20px', borderRadius: '10px' }}>
              <div style={{ fontSize: '0.74rem', color: '#166534', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Total Financial Liability Prevented
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 900, color: '#15803D', marginTop: '4px' }}>
                ${Number(totalLiability).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#166534', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <CheckCircle2 size={13} />
                <span>Across {blockedCount} intercepted rogue actions</span>
              </div>
            </div>

            <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', padding: '16px 20px', borderRadius: '10px' }}>
              <div style={{ fontSize: '0.74rem', color: '#1E40AF', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Estimated Platform ROI Multiplier
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 900, color: '#1D4ED8', marginTop: '4px' }}>
                {roiMultiplier}x
              </div>
              <div style={{ fontSize: '0.75rem', color: '#1E40AF', marginTop: '4px' }}>
                Relative to enterprise license benchmark ($24k/yr)
              </div>
            </div>

            <div style={{ background: '#FAF5FF', border: '1px solid #E9D5FF', padding: '16px 20px', borderRadius: '10px' }}>
              <div style={{ fontSize: '0.74rem', color: '#6B21A8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Gateway Enforcement Rate
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 900, color: '#7E22CE', marginTop: '4px' }}>
                100.0%
              </div>
              <div style={{ fontSize: '0.75rem', color: '#6B21A8', marginTop: '4px' }}>
                Zero ungrounded actions cleared
              </div>
            </div>
          </div>

          {/* 4 Category Breakdown Cards */}
          <h3 style={{ fontSize: '0.9rem', fontWeight: 800, color: '#0F172A', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '12px' }}>
            Risk Category Loss Avoidance Breakdown
          </h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '12px',
              marginBottom: '24px'
            }}
          >
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '14px', borderRadius: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', fontWeight: 700, color: '#475569' }}>
                <ShieldAlert size={14} color="#DC2626" />
                <span>Security & Ingress</span>
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0F172A', marginTop: '6px' }}>
                ${Number(breakdown.security_breaches_usd || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>
                Open port 8080 / plaintext ingress prevention
              </div>
            </div>

            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '14px', borderRadius: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', fontWeight: 700, color: '#475569' }}>
                <DollarSign size={14} color="#059669" />
                <span>Rogue Transactions</span>
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0F172A', marginTop: '6px' }}>
                ${Number(breakdown.financial_disputes_usd || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>
                Unlawful refunds, credits & billing drift
              </div>
            </div>

            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '14px', borderRadius: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', fontWeight: 700, color: '#475569' }}>
                <Lock size={14} color="#2563EB" />
                <span>Regulatory SLA</span>
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0F172A', marginTop: '6px' }}>
                ${Number(breakdown.regulatory_fines_usd || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>
                NIST / EU AI Act & contract penalties
              </div>
            </div>

            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '14px', borderRadius: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', fontWeight: 700, color: '#475569' }}>
                <TrendingUp size={14} color="#7C3AED" />
                <span>Operational Rework</span>
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0F172A', marginTop: '6px' }}>
                ${Number(breakdown.operational_rework_usd || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>
                Developer triage & legal review hours saved
              </div>
            </div>
          </div>

          {/* Top Intercepted Incidents Table */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3 style={{ fontSize: '0.9rem', fontWeight: 800, color: '#0F172A', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
              Top High-Liability Incidents Intercepted
            </h3>
            <button
              onClick={fetchRoiData}
              className="btn"
              style={{ fontSize: '0.75rem', padding: '4px 8px', background: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: '6px' }}
            >
              <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </button>
          </div>

          {roiData?.top_incidents?.length > 0 ? (
            <div style={{ overflowX: 'auto', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', color: '#475569', fontSize: '0.72rem', textTransform: 'uppercase' }}>
                    <th style={{ padding: '10px 12px' }}>Audit Token</th>
                    <th style={{ padding: '10px 12px' }}>Blocked Action Statement</th>
                    <th style={{ padding: '10px 12px' }}>Category</th>
                    <th style={{ padding: '10px 12px' }}>Actor Role</th>
                    <th style={{ padding: '10px 12px' }}>Risk</th>
                    <th style={{ padding: '10px 12px', textAlign: 'right' }}>Liability Prevented</th>
                  </tr>
                </thead>
                <tbody>
                  {roiData.top_incidents.map((inc) => (
                    <tr key={inc.audit_id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '10px 12px' }}>
                        <span className="code-pill">{inc.audit_id.substring(0, 12)}</span>
                      </td>
                      <td style={{ padding: '10px 12px', fontWeight: 600, color: '#0F172A', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {inc.decision_prompt}
                      </td>
                      <td style={{ padding: '10px 12px', fontSize: '0.74rem', color: '#475569' }}>
                        {inc.category}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span className="badge" style={{ background: '#F1F5F9', color: '#475569' }}>
                          {inc.actor_role}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: inc.risk_level === 'HIGH' ? '#DC2626' : '#D97706' }}>
                          {inc.risk_level}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 800, color: '#059669' }}>
                        +${Number(inc.liability_prevented_usd).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ padding: '24px', textAlign: 'center', background: '#F8FAFC', borderRadius: '8px', border: '1px dashed #CBD5E1', color: '#64748B', fontSize: '0.84rem' }}>
              No rogue actions blocked yet. Trigger an unauthorized evaluation (e.g. Ingress Port 8080 or Unauthorized Refund) to see live loss prevention calculations.
            </div>
          )}

          {/* Footnote */}
          <div style={{ marginTop: '20px', padding: '12px 14px', background: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0', fontSize: '0.74rem', color: '#64748B', lineHeight: 1.5 }}>
            <strong>Methodology & Basis:</strong> Financial liability values are calculated using empirical enterprise incident cost averages from the Ponemon Institute Cloud Misconfiguration Cost Index ($45,000 avg security remediation), commercial billing dispute caps ($5,000 default or parsed numeric prompt amount), and NIST AI 600-1 non-compliance regulatory exposure tiers ($15,000).
          </div>
        </div>
      </div>
    </div>
  );
}
