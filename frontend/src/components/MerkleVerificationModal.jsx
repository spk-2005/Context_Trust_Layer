import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  CheckCircle2,
  XCircle,
  X,
  RefreshCw,
  Copy,
  ExternalLink,
  Download,
  FileText,
  Binary,
  Layers,
  Search,
  Check
} from 'lucide-react';

export default function MerkleVerificationModal({
  isOpen,
  onClose,
  initialAuditToken,
  organizationId,
  showToast
}) {
  const [tokenInput, setTokenInput] = useState(initialAuditToken || '');
  const [ledgerStatus, setLedgerStatus] = useState(null);
  const [proofData, setProofData] = useState(null);
  const [certificate, setCertificate] = useState(null);
  const [verificationResult, setVerificationResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [copiedRoot, setCopiedRoot] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  const orgId = organizationId || '11111111-1111-1111-1111-111111111111';

  const fetchLedgerStatus = async () => {
    try {
      const res = await fetch(`/v1/merkle/status?organization_id=${orgId}`);
      if (res.ok) {
        const data = await res.json();
        setLedgerStatus(data);
      }
    } catch (err) {
      console.warn('Failed to fetch Merkle status:', err);
    }
  };

  const fetchProofAndCertificate = async (targetToken) => {
    const t = targetToken || tokenInput;
    if (!t) return;

    try {
      setIsLoading(true);
      setVerificationResult(null);

      const [proofRes, certRes] = await Promise.all([
        fetch(`/v1/merkle/proof/${encodeURIComponent(t)}?organization_id=${orgId}`),
        fetch(`/v1/merkle/certificate/${encodeURIComponent(t)}?organization_id=${orgId}`)
      ]);

      if (proofRes.ok) {
        const pData = await proofRes.json();
        setProofData(pData);

        // Auto-run verification
        verifyProofDirectly(pData);
      } else {
        setProofData(null);
      }

      if (certRes.ok) {
        const cData = await certRes.json();
        setCertificate(cData);
      }
    } catch (err) {
      console.warn('Error fetching Merkle proof:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const verifyProofDirectly = async (proof) => {
    if (!proof) return;
    try {
      setIsVerifying(true);
      const res = await fetch('/v1/merkle/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          audit_token: proof.audit_token,
          root_hash: proof.root_hash,
          proof_path: proof.proof_path
        })
      });

      if (res.ok) {
        const vData = await res.json();
        setVerificationResult(vData);
      }
    } catch (err) {
      console.warn('Verification error:', err);
    } finally {
      setIsVerifying(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchLedgerStatus();
      if (initialAuditToken) {
        setTokenInput(initialAuditToken);
        fetchProofAndCertificate(initialAuditToken);
      }
    }
  }, [isOpen, initialAuditToken]);

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    if (type === 'root') {
      setCopiedRoot(true);
      setTimeout(() => setCopiedRoot(false), 2000);
    } else {
      setCopiedToken(true);
      setTimeout(() => setCopiedToken(false), 2000);
    }
    showToast?.('Copied to clipboard', 'info');
  };

  if (!isOpen) return null;

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
          maxWidth: '1150px',
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
            background: 'linear-gradient(to right, rgba(16, 185, 129, 0.05), transparent)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #10B981, #059669)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
              }}
            >
              <Binary size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
                  Cryptographic Merkle Tree Audit Ledger & Verifier
                </h2>
                <span
                  style={{
                    background: '#ECFDF5',
                    color: '#047857',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '6px',
                    border: '1px solid #A7F3D0'
                  }}
                >
                  EU AI Act Art. 12
                </span>
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
                  SHA-256 Proofs
                </span>
              </div>
              <p style={{ margin: '4px 0 0', fontSize: '0.84rem', color: 'var(--text-muted, #64748b)' }}>
                Immutable, append-only cryptographic ledger verifying that decision audit logs cannot be retroactively tampered or deleted.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={() => {
                fetchLedgerStatus();
                fetchProofAndCertificate();
              }}
              className="btn btn-secondary"
              style={{ padding: '7px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
              <span>Refresh Ledger</span>
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

        {/* Top Status & Anchor KPI Banner */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '12px',
            padding: '14px 24px',
            background: 'var(--bg-subtle, #f8fafc)',
            borderBottom: '1px solid var(--border-subtle, #e2e8f0)'
          }}
        >
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted, #64748b)', fontWeight: 600 }}>MERKLE ROOT ANCHOR</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
              <code style={{ fontSize: '0.78rem', color: '#0F172A', fontWeight: 700, background: '#E2E8F0', padding: '2px 6px', borderRadius: '4px' }}>
                {ledgerStatus?.root_hash ? `${ledgerStatus.root_hash.substring(0, 16)}...` : 'Calculating...'}
              </code>
              {ledgerStatus?.root_hash && (
                <button
                  type="button"
                  onClick={() => copyToClipboard(ledgerStatus.root_hash, 'root')}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '2px', color: '#64748b' }}
                  title="Copy full root hash"
                >
                  {copiedRoot ? <Check size={14} color="#059669" /> : <Copy size={14} />}
                </button>
              )}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted, #64748b)', fontWeight: 600 }}>SEALED AUDIT RECORDS</div>
            <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#047857' }}>
              {ledgerStatus?.total_sealed_records ?? 0} Decisions Sealed
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted, #64748b)', fontWeight: 600 }}>TREE DEPTH & BATCH HEIGHT</div>
            <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#4F46E5' }}>
              Height #{ledgerStatus?.batch_height ?? 0} (Depth {ledgerStatus?.tree_depth ?? 1})
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted, #64748b)', fontWeight: 600 }}>COMPLIANCE MANDATE</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main, #1e293b)' }}>
              EU AI Act Art. 12 Compliant
            </div>
          </div>
        </div>

        {/* Search Bar for Audit Token */}
        <div style={{ padding: '14px 24px', borderBottom: '1px solid var(--border-subtle, #e2e8f0)', display: 'flex', gap: '10px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              type="text"
              placeholder="Paste an audit token (e.g. audit_tok_9a8b7c6d5e4f3a2b1c0d)..."
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              style={{
                width: '100%',
                padding: '9px 12px 9px 36px',
                borderRadius: '8px',
                border: '1px solid #cbd5e1',
                fontSize: '0.86rem',
                fontFamily: 'monospace',
                background: 'var(--bg-card, #ffffff)'
              }}
            />
          </div>
          <button
            onClick={() => fetchProofAndCertificate(tokenInput)}
            className="btn btn-primary"
            style={{ padding: '9px 18px', background: '#059669', border: 'none', color: '#fff', fontWeight: 700, fontSize: '0.84rem' }}
          >
            <span>Verify Token</span>
          </button>
        </div>

        {/* Main Body: Proof Inspector & Official Certificate */}
        <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
          {/* Left: Cryptographic Proof Path Visualizer */}
          <div style={{ flex: 1.1, padding: '24px', overflowY: 'auto', borderRight: '1px solid var(--border-subtle, #e2e8f0)' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#0f172a', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={18} color="#059669" />
              <span>Inclusion Proof Path (Leaf to Merkle Root)</span>
            </div>

            {verificationResult && (
              <div
                style={{
                  padding: '14px 18px',
                  borderRadius: '10px',
                  border: `1.5px solid ${verificationResult.is_valid ? '#10B981' : '#EF4444'}`,
                  background: verificationResult.is_valid ? '#ECFDF5' : '#FEF2F2',
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px'
                }}
              >
                {verificationResult.is_valid ? (
                  <ShieldCheck size={28} color="#047857" />
                ) : (
                  <ShieldAlert size={28} color="#B91C1C" />
                )}
                <div>
                  <div style={{ fontSize: '0.92rem', fontWeight: 800, color: verificationResult.is_valid ? '#047857' : '#B91C1C' }}>
                    {verificationResult.is_valid ? 'CRYPTOGRAPHIC PROOF VERIFIED' : 'PROOF VALIDATION FAILED'}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted, #64748b)' }}>
                    {verificationResult.message}
                  </div>
                </div>
              </div>
            )}

            {proofData ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {/* Leaf Node */}
                <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b' }}>LEAF 0: AUDIT TOKEN TARGET</span>
                    <span style={{ fontSize: '0.7rem', background: '#dcfce7', color: '#166534', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                      SHA-256 (leaf:{proofData.audit_token.substring(0, 10)}...)
                    </span>
                  </div>
                  <code style={{ fontSize: '0.78rem', color: '#0f172a', wordBreak: 'break-all' }}>
                    {proofData.leaf_hash}
                  </code>
                </div>

                {/* Sibling Steps */}
                {proofData.proof_path.map((step, idx) => (
                  <div key={idx} style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '10px', padding: '12px', marginLeft: `${(idx + 1) * 14}px` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#475569' }}>
                        STEP {idx + 1}: SIBLING NODE ({step.direction.toUpperCase()})
                      </span>
                      <span style={{ fontSize: '0.7rem', background: '#e0e7ff', color: '#3730a3', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                        Level {idx + 1}
                      </span>
                    </div>
                    <code style={{ fontSize: '0.78rem', color: '#334155', wordBreak: 'break-all' }}>
                      {step.hash}
                    </code>
                  </div>
                ))}

                {/* Root Anchor */}
                <div style={{ background: '#f0fdf4', border: '1.5px solid #86efac', borderRadius: '10px', padding: '14px', marginLeft: `${(proofData.proof_path.length + 1) * 14}px` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.76rem', fontWeight: 800, color: '#166534' }}>
                      MERKLE ROOT ANCHOR (LEVEL {proofData.tree_depth})
                    </span>
                    <span style={{ fontSize: '0.72rem', background: '#166534', color: '#fff', padding: '2px 8px', borderRadius: '10px', fontWeight: 700 }}>
                      IMMUTABLE
                    </span>
                  </div>
                  <code style={{ fontSize: '0.82rem', color: '#14532d', fontWeight: 700, wordBreak: 'break-all' }}>
                    {proofData.root_hash}
                  </code>
                </div>
              </div>
            ) : (
              <div style={{ padding: '40px 10px', textAlign: 'center', color: '#94a3b8' }}>
                Enter an audit token above or select an audit log item to inspect its Merkle proof.
              </div>
            )}
          </div>

          {/* Right: EU AI Act Article 12 Official Certificate */}
          <div style={{ flex: 1, padding: '24px', overflowY: 'auto', background: 'var(--bg-subtle, #f8fafc)' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#0f172a', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} color="#4F46E5" />
              <span>EU AI Act Article 12 Certificate</span>
            </div>

            {certificate ? (
              <div
                style={{
                  background: '#ffffff',
                  border: '1px solid #cbd5e1',
                  borderRadius: '12px',
                  padding: '20px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px' }}>
                  <div>
                    <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 700 }}>CERTIFICATE REFERENCE</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a', fontFamily: 'monospace' }}>
                      {certificate.certificate_id}
                    </div>
                  </div>
                  <span style={{ background: '#dcfce7', color: '#166534', padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem', fontWeight: 700 }}>
                    Article 12 Verified
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.8rem' }}>
                  <div>
                    <span style={{ color: '#64748b' }}>Actor ID: </span>
                    <strong>{certificate.actor_id}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Role: </span>
                    <span style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>{certificate.actor_role}</span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Decision Verdict: </span>
                    <strong style={{ color: certificate.verdict === 'BLOCK' ? '#dc2626' : '#059669' }}>{certificate.verdict}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Anchored At: </span>
                    <span>{new Date(certificate.timestamp).toLocaleString()}</span>
                  </div>
                </div>

                <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px 12px' }}>
                  <div style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 700, marginBottom: '2px' }}>CRYPTOGRAPHIC SEAL (HMAC-SHA256)</div>
                  <code style={{ fontSize: '0.76rem', color: '#0f172a', wordBreak: 'break-all' }}>
                    {certificate.compliance_seal}
                  </code>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(certificate, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${certificate.certificate_id}.json`;
                    a.click();
                    showToast?.('Certificate downloaded successfully!', 'success');
                  }}
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', padding: '9px 16px', fontSize: '0.82rem' }}
                >
                  <Download size={14} />
                  <span>Download Compliance Dossier (JSON)</span>
                </button>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 10px', color: '#94a3b8' }}>
                Load an audit token to view its official Article 12 compliance certificate.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
