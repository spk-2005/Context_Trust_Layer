import React, { useState, useEffect } from 'react';
import {
  X,
  FileText,
  Database,
  Layers,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Search,
  ExternalLink,
  Copy,
  Check,
  Sparkles,
  ArrowRight,
  Filter,
  Trash2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import ExecutiveDeleteModal from './ExecutiveDeleteModal';

export default function AssetInspectorDrawer({
  isOpen,
  onClose,
  assetType = 'document', // 'document' | 'connector'
  assetId,
  assetTitle,
  onNavigateToCurator,
  showToast
}) {
  const { user } = useAuth();
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('claims'); // 'claims' | 'conflicts' | 'overview' | 'content'
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [claimSearch, setClaimSearch] = useState('');
  const [claimStatusFilter, setClaimStatusFilter] = useState('all');
  const [copiedHash, setCopiedHash] = useState(false);

  useEffect(() => {
    if (!isOpen || !assetId) {
      setData(null);
      return;
    }

    const fetchArtifacts = async () => {
      setLoading(true);
      setError(null);
      try {
        const endpoint = assetType === 'connector' 
          ? `/v1/sources/${assetId}/artifacts`
          : `/v1/documents/${assetId}/artifacts`;
        
        const res = await fetch(endpoint);
        if (!res.ok) {
          throw new Error(`Failed to load asset artifacts (${res.status})`);
        }
        const json = await res.json();
        setData(json);
        // If there are conflicts and no claims, default to conflicts tab
        if ((json.claims?.length || 0) === 0 && (json.conflicts?.length || 0) > 0) {
          setActiveTab('conflicts');
        } else {
          setActiveTab('claims');
        }
      } catch (err) {
        console.error("Asset inspector fetch error:", err);
        setError(err.message || 'Unable to retrieve asset artifacts');
      } finally {
        setLoading(false);
      }
    };

    fetchArtifacts();
  }, [isOpen, assetId, assetType]);

  if (!isOpen) return null;

  const doc = data?.document;
  const src = data?.source;
  const claims = data?.claims || [];
  const conflicts = data?.conflicts || [];
  const docs = data?.documents || [];

  const filteredClaims = claims.filter(c => {
    if (claimStatusFilter !== 'all' && (c.status || '').toLowerCase() !== claimStatusFilter) {
      return false;
    }
    if (!claimSearch.trim()) return true;
    const q = claimSearch.toLowerCase();
    return (
      (c.claim_text || '').toLowerCase().includes(q) ||
      (c.subject || '').toLowerCase().includes(q) ||
      (c.predicate || '').toLowerCase().includes(q) ||
      (c.object || '').toLowerCase().includes(q)
    );
  });

  const handleCopyText = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      zIndex: 9999,
      display: 'flex',
      justifyContent: 'flex-end',
      background: 'rgba(15, 23, 42, 0.45)',
      backdropFilter: 'blur(3px)',
      animation: 'fadeIn 0.18s ease-out'
    }}>
      {/* Backdrop click area */}
      <div 
        style={{ flex: 1 }} 
        onClick={onClose}
        title="Click outside to close"
      />

      {/* Slide-Over Drawer Container */}
      <div style={{
        width: '100%',
        maxWidth: '720px',
        height: '100vh',
        background: '#FFFFFF',
        boxShadow: '-8px 0 32px rgba(0, 0, 0, 0.15)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        animation: 'slideInRight 0.22s cubic-bezier(0.16, 1, 0.3, 1)'
      }}>
        {/* Drawer Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%)',
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: assetType === 'connector' ? '#EEF2FF' : '#FFF7ED',
              color: assetType === 'connector' ? '#4F46E5' : '#C2410C',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              border: `1px solid ${assetType === 'connector' ? '#C7D2FE' : '#FFEDD5'}`
            }}>
              {assetType === 'connector' ? <Database size={20} /> : <FileText size={20} />}
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <h2 style={{
                  margin: 0,
                  fontSize: '1.1rem',
                  fontWeight: 800,
                  color: 'var(--text-main)',
                  lineHeight: '1.3'
                }}>
                  {assetTitle || doc?.title || src?.name || 'Asset Deep-Dive'}
                </h2>
                <span className="badge badge-verified" style={{ fontSize: '0.68rem', padding: '2px 7px' }}>
                  {assetType === 'connector' ? 'Connector Asset' : (doc?.document_type || 'Policy Document')}
                </span>
              </div>

              <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                {src && (
                  <span>
                    Source: <strong style={{ color: 'var(--primary)' }}>{src.name}</strong> ({src.source_type})
                  </span>
                )}
                {doc?.external_id && (
                  <span>• External ID: <code style={{ fontSize: '0.72rem' }}>{doc.external_id}</code></span>
                )}
                <span>• Ingested in PostgreSQL</span>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {user?.role === 'admin' && (
              <button
                type="button"
                onClick={() => setIsDeleteModalOpen(true)}
                title={`Decommission or Purge ${assetTitle || (assetType === 'connector' ? 'Connector' : 'Document')}`}
                style={{
                  padding: '5px 10px',
                  borderRadius: '6px',
                  border: '1px solid #FCA5A5',
                  background: '#FEF2F2',
                  color: '#DC2626',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={e => { e.currentTarget.style.background = '#FEE2E2'; }}
                onMouseLeave={e => { e.currentTarget.style.background = '#FEF2F2'; }}
              >
                <Trash2 size={13} strokeWidth={2.2} />
                <span>Delete Asset</span>
              </button>
            )}

            <button
              type="button"
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#64748B',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Close Drawer"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Tab Switcher */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '0 24px',
          borderBottom: '1px solid var(--border-subtle)',
          background: '#FFFFFF'
        }}>
          <button
            type="button"
            onClick={() => setActiveTab('claims')}
            style={{
              padding: '12px 14px',
              border: 'none',
              background: 'transparent',
              fontSize: '0.84rem',
              fontWeight: activeTab === 'claims' ? 700 : 500,
              color: activeTab === 'claims' ? 'var(--primary, #2563EB)' : '#64748B',
              borderBottom: activeTab === 'claims' ? '2px solid var(--primary, #2563EB)' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Layers size={14} />
            <span>Extracted Claims</span>
            <span style={{
              background: activeTab === 'claims' ? 'rgba(37,99,235,0.1)' : '#F1F5F9',
              color: activeTab === 'claims' ? 'var(--primary, #2563EB)' : '#64748B',
              padding: '1px 6px',
              borderRadius: '999px',
              fontSize: '0.68rem',
              fontWeight: 700
            }}>
              {claims.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('conflicts')}
            style={{
              padding: '12px 14px',
              border: 'none',
              background: 'transparent',
              fontSize: '0.84rem',
              fontWeight: activeTab === 'conflicts' ? 700 : 500,
              color: activeTab === 'conflicts' ? '#DC2626' : '#64748B',
              borderBottom: activeTab === 'conflicts' ? '2px solid #DC2626' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <AlertTriangle size={14} style={{ color: conflicts.length > 0 ? '#DC2626' : '#94A3B8' }} />
            <span>Associated Conflicts</span>
            <span style={{
              background: conflicts.length > 0 ? '#FEE2E2' : '#F1F5F9',
              color: conflicts.length > 0 ? '#B91C1C' : '#64748B',
              padding: '1px 6px',
              borderRadius: '999px',
              fontSize: '0.68rem',
              fontWeight: 700
            }}>
              {conflicts.length}
            </span>
          </button>

          {assetType === 'connector' && (
            <button
              type="button"
              onClick={() => setActiveTab('documents')}
              style={{
                padding: '12px 14px',
                border: 'none',
                background: 'transparent',
                fontSize: '0.84rem',
                fontWeight: activeTab === 'documents' ? 700 : 500,
                color: activeTab === 'documents' ? 'var(--primary, #2563EB)' : '#64748B',
                borderBottom: activeTab === 'documents' ? '2px solid var(--primary, #2563EB)' : '2px solid transparent',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <FileText size={14} />
              <span>Synced Documents</span>
              <span style={{
                background: '#F1F5F9',
                color: '#64748B',
                padding: '1px 6px',
                borderRadius: '999px',
                fontSize: '0.68rem',
                fontWeight: 700
              }}>
                {docs.length}
              </span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            style={{
              padding: '12px 14px',
              border: 'none',
              background: 'transparent',
              fontSize: '0.84rem',
              fontWeight: activeTab === 'overview' ? 700 : 500,
              color: activeTab === 'overview' ? 'var(--primary, #2563EB)' : '#64748B',
              borderBottom: activeTab === 'overview' ? '2px solid var(--primary, #2563EB)' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <ShieldCheck size={14} />
            <span>Provenance & Metadata</span>
          </button>

          {doc?.content_preview && (
            <button
              type="button"
              onClick={() => setActiveTab('content')}
              style={{
                padding: '12px 14px',
                border: 'none',
                background: 'transparent',
                fontSize: '0.84rem',
                fontWeight: activeTab === 'content' ? 700 : 500,
                color: activeTab === 'content' ? 'var(--primary, #2563EB)' : '#64748B',
                borderBottom: activeTab === 'content' ? '2px solid var(--primary, #2563EB)' : '2px solid transparent',
                cursor: 'pointer'
              }}
            >
              Content Preview
            </button>
          )}
        </div>

        {/* Drawer Body Area */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 24px',
          background: '#F8FAFC'
        }}>
          {loading ? (
            <div style={{ padding: '60px 0', textAlign: 'center', color: '#64748B' }}>
              <div style={{
                width: '32px',
                height: '32px',
                border: '3px solid #E2E8F0',
                borderTopColor: 'var(--primary, #2563EB)',
                borderRadius: '50%',
                margin: '0 auto 16px',
                animation: 'spin 0.8s linear infinite'
              }} />
              <div style={{ fontSize: '0.88rem', fontWeight: 600 }}>Loading corresponding claims & conflicts...</div>
            </div>
          ) : error ? (
            <div style={{
              padding: '24px',
              borderRadius: '8px',
              background: '#FEF2F2',
              border: '1px solid #FCA5A5',
              color: '#991B1B',
              fontSize: '0.85rem'
            }}>
              <strong>Error:</strong> {error}
            </div>
          ) : (
            <>
              {/* TAB 1: CLAIMS */}
              {activeTab === 'claims' && (
                <div>
                  {/* Search and Filters Bar */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '12px',
                    marginBottom: '16px',
                    flexWrap: 'wrap'
                  }}>
                    <div style={{ position: 'relative', flex: 1, minWidth: '220px' }}>
                      <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
                      <input
                        type="text"
                        placeholder="Search claims in this asset..."
                        value={claimSearch}
                        onChange={e => setClaimSearch(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '7px 10px 7px 32px',
                          fontSize: '0.8rem',
                          borderRadius: '6px',
                          border: '1px solid var(--border-subtle)',
                          background: '#FFFFFF'
                        }}
                      />
                    </div>

                    <div style={{ display: 'flex', gap: '6px' }}>
                      {['all', 'verified', 'outdated'].map(st => (
                        <button
                          key={st}
                          type="button"
                          onClick={() => setClaimStatusFilter(st)}
                          style={{
                            padding: '5px 10px',
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            borderRadius: '6px',
                            border: claimStatusFilter === st ? '1px solid var(--primary)' : '1px solid var(--border-subtle)',
                            background: claimStatusFilter === st ? '#EFF6FF' : '#FFFFFF',
                            color: claimStatusFilter === st ? 'var(--primary)' : '#64748B',
                            cursor: 'pointer'
                          }}
                        >
                          {st.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>

                  {filteredClaims.length === 0 ? (
                    <div style={{
                      padding: '48px 20px',
                      textAlign: 'center',
                      background: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px dashed var(--border-subtle)',
                      color: '#64748B'
                    }}>
                      <Layers size={28} style={{ margin: '0 auto 10px', color: '#94A3B8' }} />
                      <div style={{ fontSize: '0.88rem', fontWeight: 600 }}>No atomic claims matched</div>
                      <div style={{ fontSize: '0.75rem', color: '#94A3B8', marginTop: '4px' }}>
                        {claims.length === 0 
                          ? 'This document has not been parsed into atomic claims yet.' 
                          : 'Try clearing your search query or status filter.'}
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gap: '12px' }}>
                      {filteredClaims.map((claim, idx) => {
                        const score = Number(claim.trust_score || 0.95);
                        const pct = (score * 100).toFixed(0);
                        const isHigh = score >= 0.9;
                        const isMed = score >= 0.7 && score < 0.9;

                        return (
                          <div
                            key={claim.id || idx}
                            style={{
                              background: '#FFFFFF',
                              border: '1px solid var(--border-subtle)',
                              borderRadius: '8px',
                              padding: '14px 16px',
                              transition: 'box-shadow 0.15s ease',
                              boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                                <span className="code-pill" style={{ background: '#F1F5F9', color: '#334155' }}>
                                  <strong>Subject:</strong> {claim.subject}
                                </span>
                                <span className="code-pill" style={{ background: '#F8FAFC', color: '#64748B' }}>
                                  {claim.predicate}
                                </span>
                                {claim.object && (
                                  <span className="code-pill" style={{ background: '#F1F5F9', color: '#334155' }}>
                                    {claim.object}
                                  </span>
                                )}
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span className={`badge ${claim.status === 'verified' ? 'badge-allow' : 'badge-outdated'}`} style={{ fontSize: '0.65rem' }}>
                                  {claim.status}
                                </span>
                                <div style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '5px',
                                  fontSize: '0.72rem',
                                  fontWeight: 700,
                                  color: isHigh ? '#16A34A' : isMed ? '#D97706' : '#DC2626'
                                }}>
                                  <span>{pct}% Trust</span>
                                  <div style={{
                                    width: '32px',
                                    height: '6px',
                                    background: '#E2E8F0',
                                    borderRadius: '999px',
                                    overflow: 'hidden'
                                  }}>
                                    <div style={{
                                      width: `${pct}%`,
                                      height: '100%',
                                      background: isHigh ? '#16A34A' : isMed ? '#F59E0B' : '#EF4444'
                                    }} />
                                  </div>
                                </div>
                              </div>
                            </div>

                            <p style={{
                              margin: '0 0 10px 0',
                              fontSize: '0.86rem',
                              fontWeight: 600,
                              color: 'var(--text-main)',
                              lineHeight: '1.45'
                            }}>
                              "{claim.claim_text}"
                            </p>

                            <div style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              fontSize: '0.72rem',
                              color: '#64748B',
                              paddingTop: '8px',
                              borderTop: '1px solid #F1F5F9',
                              flexWrap: 'wrap',
                              gap: '6px'
                            }}>
                              <span>Section: <strong>{claim.section || 'General'}</strong></span>
                              {claim.quote && (
                                <span style={{ fontStyle: 'italic', maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={claim.quote}>
                                  Evidence: "{claim.quote}"
                                </span>
                              )}
                              <span>ID: <code style={{ fontSize: '0.7rem' }}>{claim.id?.substring(0, 8)}</code></span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: CONFLICTS */}
              {activeTab === 'conflicts' && (
                <div>
                  {conflicts.length === 0 ? (
                    <div style={{
                      padding: '48px 24px',
                      textAlign: 'center',
                      background: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #D1FAE5',
                      color: '#065F46'
                    }}>
                      <CheckCircle2 size={36} style={{ margin: '0 auto 12px', color: '#10B981' }} />
                      <div style={{ fontSize: '1rem', fontWeight: 800 }}>Zero Contradictions Detected</div>
                      <div style={{ fontSize: '0.78rem', color: '#047857', marginTop: '6px', maxWidth: '420px', margin: '6px auto 0' }}>
                        All atomic claims extracted from this asset are in complete semantic harmony with enterprise standards. No pairwise conflicts found.
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gap: '14px' }}>
                      <div style={{
                        padding: '10px 14px',
                        background: '#FEF2F2',
                        border: '1px solid #FCA5A5',
                        borderRadius: '8px',
                        fontSize: '0.78rem',
                        color: '#991B1B',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '8px'
                      }}>
                        <span>
                          ⚠️ <strong>{conflicts.length} active contradiction(s)</strong> detected involving statements from this asset.
                        </span>
                        {onNavigateToCurator && (
                          <button
                            type="button"
                            onClick={() => {
                              onClose();
                              onNavigateToCurator();
                            }}
                            className="btn btn-secondary"
                            style={{
                              fontSize: '0.72rem',
                              padding: '4px 10px',
                              background: '#FFFFFF',
                              color: '#991B1B',
                              borderColor: '#FCA5A5'
                            }}
                          >
                            Open in Curator Bot ➔
                          </button>
                        )}
                      </div>

                      {conflicts.map((conflict, idx) => (
                        <div
                          key={conflict.id || idx}
                          style={{
                            background: '#FFFFFF',
                            border: '1px solid #FCA5A5',
                            borderRadius: '8px',
                            padding: '16px',
                            boxShadow: '0 2px 6px rgba(220, 38, 38, 0.05)'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                            <span className="badge badge-outdated" style={{ background: '#FEE2E2', color: '#B91C1C', border: '1px solid #FCA5A5' }}>
                              Severity: {conflict.severity || 'HIGH'}
                            </span>
                            <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>
                              Conflict ID: {conflict.id?.substring(0, 8)}...
                            </span>
                          </div>

                          {/* Side-by-side contradiction card */}
                          <div style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr auto 1fr',
                            gap: '12px',
                            alignItems: 'center',
                            background: '#F8FAFC',
                            padding: '12px',
                            borderRadius: '8px',
                            border: '1px dashed #CBD5E1'
                          }}>
                            {/* Side A */}
                            <div style={{ background: '#FFFFFF', padding: '10px 12px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                              <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', marginBottom: '4px' }}>
                                Claim Statement A
                              </div>
                              <p style={{ margin: 0, fontSize: '0.82rem', fontWeight: 600, color: '#0F172A', lineHeight: '1.4' }}>
                                "{conflict.claim_a_text}"
                              </p>
                            </div>

                            {/* Clash Icon */}
                            <div style={{
                              width: '30px',
                              height: '30px',
                              borderRadius: '50%',
                              background: '#FEE2E2',
                              color: '#DC2626',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontWeight: 900,
                              fontSize: '0.75rem'
                            }}>
                              VS
                            </div>

                            {/* Side B */}
                            <div style={{ background: '#FFFFFF', padding: '10px 12px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                              <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', marginBottom: '4px' }}>
                                Claim Statement B
                              </div>
                              <p style={{ margin: 0, fontSize: '0.82rem', fontWeight: 600, color: '#0F172A', lineHeight: '1.4' }}>
                                "{conflict.claim_b_text}"
                              </p>
                            </div>
                          </div>

                          <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span>Type: <strong>{conflict.conflict_type || 'Direct Semantic Contradiction'}</strong></span>
                            <span>Status: <strong style={{ color: '#DC2626' }}>{conflict.resolution_status}</strong></span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB: SYNCED DOCUMENTS (Connector view only) */}
              {activeTab === 'documents' && (
                <div style={{ display: 'grid', gap: '10px' }}>
                  {docs.length === 0 ? (
                    <div style={{ padding: '40px 20px', textAlign: 'center', color: '#64748B' }}>
                      No documents synced by this connector yet.
                    </div>
                  ) : (
                    docs.map((d, i) => (
                      <div
                        key={d.id || i}
                        style={{
                          background: '#FFFFFF',
                          padding: '12px 14px',
                          borderRadius: '8px',
                          border: '1px solid var(--border-subtle)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-main)' }}>
                            {d.title}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '2px' }}>
                            Type: {d.document_type} • ID: <code>{d.id?.substring(0, 8)}</code>
                          </div>
                        </div>
                        <span className="badge badge-verified" style={{ fontSize: '0.68rem' }}>
                          {d.status}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* TAB 3: PROVENANCE & METADATA */}
              {activeTab === 'overview' && (
                <div style={{
                  background: '#FFFFFF',
                  borderRadius: '8px',
                  border: '1px solid var(--border-subtle)',
                  padding: '20px'
                }}>
                  <h4 style={{ margin: '0 0 16px 0', fontSize: '0.92rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    Cryptographic & Lineage Metadata
                  </h4>

                  <div style={{ display: 'grid', gap: '12px', fontSize: '0.82rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid #F1F5F9' }}>
                      <span style={{ color: '#64748B' }}>Asset Title:</span>
                      <strong style={{ color: '#0F172A' }}>{doc?.title || src?.name}</strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid #F1F5F9' }}>
                      <span style={{ color: '#64748B' }}>PostgreSQL Asset UUID:</span>
                      <code>{doc?.id || src?.id}</code>
                    </div>

                    {doc?.external_id && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid #F1F5F9' }}>
                        <span style={{ color: '#64748B' }}>External System ID:</span>
                        <code>{doc.external_id}</code>
                      </div>
                    )}

                    {src && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid #F1F5F9' }}>
                        <span style={{ color: '#64748B' }}>Parent Connector:</span>
                        <strong style={{ color: 'var(--primary)' }}>{src.name} ({src.source_type})</strong>
                      </div>
                    )}

                    {doc?.content_hash && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '8px', borderBottom: '1px solid #F1F5F9' }}>
                        <span style={{ color: '#64748B' }}>SHA-256 Hash:</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <code style={{ fontSize: '0.72rem' }}>{doc.content_hash.substring(0, 28)}...</code>
                          <button
                            type="button"
                            onClick={() => handleCopyText(doc.content_hash)}
                            style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '2px', color: copiedHash ? '#16A34A' : '#64748B' }}
                            title="Copy full hash"
                          >
                            {copiedHash ? <Check size={13} /> : <Copy size={13} />}
                          </button>
                        </div>
                      </div>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid #F1F5F9' }}>
                      <span style={{ color: '#64748B' }}>Total Derived Claims:</span>
                      <strong>{claims.length} atomic rules</strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid #F1F5F9' }}>
                      <span style={{ color: '#64748B' }}>Active Contradictions:</span>
                      <strong style={{ color: conflicts.length > 0 ? '#DC2626' : '#16A34A' }}>
                        {conflicts.length} conflict(s)
                      </strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#64748B' }}>Ingestion Timestamp:</span>
                      <span>{doc?.created_at ? new Date(doc.created_at).toLocaleString() : 'N/A'}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: RAW CONTENT PREVIEW */}
              {activeTab === 'content' && doc?.content_preview && (
                <div style={{
                  background: '#FFFFFF',
                  borderRadius: '8px',
                  border: '1px solid var(--border-subtle)',
                  padding: '16px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#64748B' }}>
                      Normalized Markdown Stream (First 2,000 characters)
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopyText(doc.content_preview)}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                    >
                      {copiedHash ? 'Copied!' : 'Copy Text'}
                    </button>
                  </div>
                  <pre style={{
                    margin: 0,
                    padding: '12px',
                    background: '#0F172A',
                    color: '#E2E8F0',
                    borderRadius: '6px',
                    fontSize: '0.76rem',
                    lineHeight: '1.5',
                    fontFamily: 'var(--font-mono)',
                    whiteSpace: 'pre-wrap',
                    maxHeight: '400px',
                    overflowY: 'auto'
                  }}>
                    {doc.content_preview}
                  </pre>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Executive Decommission / Purge Modal */}
      <ExecutiveDeleteModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        asset={{
          id: assetId,
          label: assetTitle || doc?.title || src?.name || (assetType === 'connector' ? 'Data Connector' : 'Policy Document'),
          type: assetType,
          data: { doc_id: assetId, source_id: assetId }
        }}
        onSuccess={() => {
          onClose();
        }}
        showToast={showToast}
      />
    </div>
  );
}

