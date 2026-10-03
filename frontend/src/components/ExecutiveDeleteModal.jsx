import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Archive,
  Trash2,
  X,
  ShieldAlert,
  Layers,
  Scale,
  FileText,
  Database,
  CheckCircle2,
  Loader2,
  Info
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

/**
 * ExecutiveDeleteModal
 *
 * Enterprise governance dialog for the CEO / Administrator to:
 * 1. Safe Decommission (Soft Archive) - Deprecates claims & resolves contradictions, preserving audit ledger.
 * 2. Permanent Purge (Hard Delete) - Permanently deletes records with foreign key cascade.
 */
export default function ExecutiveDeleteModal({
  isOpen,
  onClose,
  asset,
  onSuccess,
  showToast
}) {
  const { user } = useAuth();
  const [mode, setMode] = useState('archive'); // 'archive' | 'permanent'
  const [blastRadius, setBlastRadius] = useState(null);
  const [isLoadingRadius, setIsLoadingRadius] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmInput, setConfirmInput] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);

  const isConnector = asset?.type === 'connector' || asset?.mode === 'connector';
  const assetId = asset?.data?.source_id || asset?.data?.doc_id || String(asset?.id || '').replace(/^(doc_|src_|source_|connector_)/, '');
  const assetName = asset?.label || asset?.title || (isConnector ? 'Data Connector' : 'Policy Document');

  // Load Blast Radius on open
  useEffect(() => {
    if (!isOpen || !assetId) {
      setBlastRadius(null);
      setConfirmInput('');
      setErrorMsg(null);
      return;
    }

    let isMounted = true;
    const fetchBlastRadius = async () => {
      setIsLoadingRadius(true);
      setErrorMsg(null);
      try {
        const endpoint = isConnector
          ? `/v1/sources/${assetId}/blast-radius`
          : `/v1/documents/${assetId}/blast-radius`;
        const res = await fetch(endpoint);
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setBlastRadius(data);
        } else {
          const errData = await res.json().catch(() => ({}));
          if (isMounted) setErrorMsg(errData.detail || 'Could not calculate blast radius.');
        }
      } catch (err) {
        if (isMounted) setErrorMsg('Failed to connect to governance API.');
      } finally {
        if (isMounted) setIsLoadingRadius(false);
      }
    };

    fetchBlastRadius();
    return () => {
      isMounted = false;
    };
  }, [isOpen, assetId, isConnector]);

  if (!isOpen || !asset) return null;

  const isConfirmed = mode === 'archive' || confirmInput.trim().toLowerCase() === assetName.trim().toLowerCase() || confirmInput.trim() === 'CONFIRM';

  const handleExecute = async () => {
    if (!isConfirmed) return;
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const endpoint = isConnector
        ? `/v1/sources/${assetId}?mode=${mode}&user_name=${encodeURIComponent(user?.name || 'Sarah Chen')}&user_role=${encodeURIComponent(user?.role || 'admin')}&user_id=${user?.id || ''}`
        : `/v1/documents/${assetId}?mode=${mode}&user_name=${encodeURIComponent(user?.name || 'Sarah Chen')}&user_role=${encodeURIComponent(user?.role || 'admin')}&user_id=${user?.id || ''}`;

      const res = await fetch(endpoint, { method: 'DELETE' });
      const data = await res.json().catch(() => ({}));

      if (res.ok) {
        const msg = mode === 'archive'
          ? `Decommissioned "${assetName}" successfully.`
          : `Permanently purged "${assetName}".`;
        showToast?.(msg, 'success');
        onSuccess?.({ assetId, mode, isConnector, data });
        onClose();
      } else {
        setErrorMsg(data.detail || 'Failed to complete deletion request.');
      }
    } catch (err) {
      setErrorMsg('Network error executing deletion.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !isSubmitting) onClose();
      }}
    >
      <div
        style={{
          background: '#FFFFFF',
          borderRadius: '12px',
          width: '100%',
          maxWidth: '560px',
          boxShadow: '0 20px 40px -15px rgba(0, 0, 0, 0.25)',
          border: '1px solid #E2E8F0',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          animation: 'fadeIn 0.15s ease'
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderBottom: '1px solid #F1F5F9',
          background: mode === 'permanent' ? '#FEF2F2' : '#FFF7ED'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              background: mode === 'permanent' ? '#FEE2E2' : '#FFEDD5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: mode === 'permanent' ? '#DC2626' : '#EA580C'
            }}>
              {mode === 'permanent' ? <Trash2 size={18} strokeWidth={2.2} /> : <Archive size={18} strokeWidth={2.2} />}
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 800, color: '#0F172A' }}>
                Executive Governance Action
              </h3>
              <div style={{ fontSize: '0.72rem', color: '#64748B', display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span>CEO Persona Clearance</span>
                <span>•</span>
                <span style={{ fontWeight: 600, color: mode === 'permanent' ? '#DC2626' : '#EA580C' }}>
                  {mode === 'permanent' ? 'Permanent Purge' : 'Safe Decommission'}
                </span>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94A3B8',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              padding: '4px',
              borderRadius: '6px'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Target Asset Summary */}
          <div style={{
            background: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            padding: '12px 14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
              <div style={{
                width: '30px',
                height: '30px',
                borderRadius: '6px',
                background: '#FFFFFF',
                border: '1px solid #CBD5E1',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#475569',
                flexShrink: 0
              }}>
                {isConnector ? <Database size={15} /> : <FileText size={15} />}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  color: '#0F172A',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  {assetName}
                </div>
                <div style={{ fontSize: '0.68rem', color: '#64748B', textTransform: 'uppercase', fontWeight: 600 }}>
                  {isConnector ? 'Data Source Connector' : 'Policy Document'} • ID: {assetId.substring(0, 13)}...
                </div>
              </div>
            </div>
          </div>

          {/* Blast Radius Calculation Metric Badges */}
          <div>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <ShieldAlert size={13} color="#EA580C" />
              <span>Calculated Blast Radius Impact</span>
            </div>

            {isLoadingRadius ? (
              <div style={{ padding: '16px', background: '#F8FAFC', borderRadius: '8px', textAlign: 'center', fontSize: '0.74rem', color: '#64748B', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Loader2 size={15} className="spin" />
                <span>Evaluating lineage connections, claims & active conflicts...</span>
              </div>
            ) : blastRadius ? (
              <div style={{ display: 'grid', gridTemplateColumns: isConnector ? '1fr 1fr 1fr' : '1fr 1fr', gap: '8px' }}>
                {isConnector && (
                  <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '10px 12px' }}>
                    <div style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 600 }}>SYNCED DOCUMENTS</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0F172A', marginTop: '2px' }}>
                      {blastRadius.documents_count || 0}
                    </div>
                  </div>
                )}
                <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '10px 12px' }}>
                  <div style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 600 }}>ATOMIC CLAIMS</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#EA580C', marginTop: '2px' }}>
                    {blastRadius.claims_count || 0}
                  </div>
                </div>
                <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '10px 12px' }}>
                  <div style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 600 }}>ACTIVE CONFLICTS</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: blastRadius.conflicts_count > 0 ? '#DC2626' : '#10B981', marginTop: '2px' }}>
                    {blastRadius.conflicts_count || 0}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ padding: '10px', background: '#F8FAFC', borderRadius: '6px', fontSize: '0.72rem', color: '#64748B' }}>
                Direct deletion with database cascading foreign keys enabled.
              </div>
            )}
          </div>

          {/* Action Choice: Mode Selector */}
          <div>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>
              Select Governance Execution Mode
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {/* Option A: Archive (Recommended) */}
              <div
                onClick={() => setMode('archive')}
                style={{
                  border: mode === 'archive' ? '2px solid #EA580C' : '1px solid #CBD5E1',
                  background: mode === 'archive' ? '#FFF7ED' : '#FFFFFF',
                  borderRadius: '8px',
                  padding: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Archive size={15} color={mode === 'archive' ? '#EA580C' : '#64748B'} />
                    <span style={{ fontSize: '0.78rem', fontWeight: 700, color: mode === 'archive' ? '#EA580C' : '#0F172A' }}>
                      Safe Decommission
                    </span>
                  </div>
                  {mode === 'archive' && <CheckCircle2 size={15} color="#EA580C" />}
                </div>
                <div style={{ fontSize: '0.69rem', color: '#64748B', lineHeight: 1.4 }}>
                  Deprecates atomic claims and auto-resolves contradictions. Preserves historical Merkle audit ledger.
                </div>
                <span style={{ fontSize: '0.62rem', fontWeight: 700, color: '#059669', background: '#ECFDF5', padding: '2px 5px', borderRadius: '4px', alignSelf: 'flex-start' }}>
                  RECOMMENDED
                </span>
              </div>

              {/* Option B: Permanent Purge */}
              <div
                onClick={() => setMode('permanent')}
                style={{
                  border: mode === 'permanent' ? '2px solid #DC2626' : '1px solid #CBD5E1',
                  background: mode === 'permanent' ? '#FEF2F2' : '#FFFFFF',
                  borderRadius: '8px',
                  padding: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Trash2 size={15} color={mode === 'permanent' ? '#DC2626' : '#64748B'} />
                    <span style={{ fontSize: '0.78rem', fontWeight: 700, color: mode === 'permanent' ? '#DC2626' : '#0F172A' }}>
                      Permanent Purge
                    </span>
                  </div>
                  {mode === 'permanent' && <CheckCircle2 size={15} color="#DC2626" />}
                </div>
                <div style={{ fontSize: '0.69rem', color: '#64748B', lineHeight: 1.4 }}>
                  Completely erases all rows and child tables from PostgreSQL. Irreversible action.
                </div>
                <span style={{ fontSize: '0.62rem', fontWeight: 700, color: '#DC2626', background: '#FEE2E2', padding: '2px 5px', borderRadius: '4px', alignSelf: 'flex-start' }}>
                  HARD PURGE
                </span>
              </div>
            </div>
          </div>

          {/* Type-to-Confirm Safeguard for Permanent Delete */}
          {mode === 'permanent' && (
            <div style={{ background: '#FFF1F2', border: '1px solid #FECDD3', borderRadius: '8px', padding: '12px' }}>
              <div style={{ fontSize: '0.72rem', color: '#9F1239', fontWeight: 700, marginBottom: '6px' }}>
                Safety Confirmation: Type <span style={{ fontFamily: 'monospace', background: '#FFE4E6', padding: '1px 4px', borderRadius: '3px' }}>CONFIRM</span> or the asset name to execute:
              </div>
              <input
                type="text"
                value={confirmInput}
                onChange={(e) => setConfirmInput(e.target.value)}
                placeholder={`Type "${assetName}" or CONFIRM`}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  borderRadius: '6px',
                  border: '1px solid #FDA4AF',
                  fontSize: '0.76rem',
                  outline: 'none',
                  background: '#FFFFFF',
                  color: '#0F172A',
                  boxSizing: 'border-box'
                }}
              />
            </div>
          )}

          {errorMsg && (
            <div style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', color: '#B91C1C', borderRadius: '6px', padding: '8px 12px', fontSize: '0.74rem' }}>
              {errorMsg}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div style={{
          padding: '14px 20px',
          background: '#F8FAFC',
          borderTop: '1px solid #F1F5F9',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '10px'
        }}>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            style={{
              padding: '7px 14px',
              borderRadius: '6px',
              border: '1px solid #CBD5E1',
              background: '#FFFFFF',
              color: '#475569',
              fontSize: '0.76rem',
              fontWeight: 600,
              cursor: isSubmitting ? 'not-allowed' : 'pointer'
            }}
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleExecute}
            disabled={!isConfirmed || isSubmitting}
            style={{
              padding: '7px 16px',
              borderRadius: '6px',
              border: 'none',
              background: !isConfirmed || isSubmitting
                ? '#CBD5E1'
                : mode === 'permanent'
                ? '#DC2626'
                : '#EA580C',
              color: '#FFFFFF',
              fontSize: '0.76rem',
              fontWeight: 700,
              cursor: !isConfirmed || isSubmitting ? 'not-allowed' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: isConfirmed && !isSubmitting ? '0 2px 8px rgba(0,0,0,0.12)' : 'none'
            }}
          >
            {isSubmitting ? (
              <>
                <Loader2 size={14} className="spin" />
                <span>Executing...</span>
              </>
            ) : mode === 'permanent' ? (
              <>
                <Trash2 size={14} />
                <span>Permanently Purge Asset</span>
              </>
            ) : (
              <>
                <Archive size={14} />
                <span>Decommission Asset</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
