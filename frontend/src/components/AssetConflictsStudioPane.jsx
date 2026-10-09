import React, { useState, useMemo } from 'react';
import {
  Scale,
  AlertTriangle,
  CheckCircle2,
  GitBranch,
  FileText,
  Copy,
  Check,
  Search,
  Filter,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  ChevronRight,
  Info,
  X
} from 'lucide-react';

export default function AssetConflictsStudioPane({
  asset,
  conflicts = [],
  conflictMap = {},
  graphData,
  onFocusInDag,
  onLocateInDoc,
  showToast
}) {
  const [filterStatus, setFilterStatus] = useState('all'); // 'all' | 'active' | 'resolved'
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedConflictId, setCopiedConflictId] = useState(null);

  const totalConflicts = conflicts.length;

  const metrics = useMemo(() => {
    let activeCount = 0;
    let resolvedCount = 0;
    let criticalCount = 0;

    conflicts.forEach(c => {
      const st = (c.status || '').toLowerCase();
      const isResolved = st === 'resolved' || st === 'dismissed';
      if (isResolved) {
        resolvedCount++;
      } else {
        activeCount++;
      }

      const sev = (c.severity || 'high').toLowerCase();
      if (sev === 'critical') {
        criticalCount++;
      }
    });

    return {
      total: totalConflicts,
      active: activeCount,
      resolved: resolvedCount,
      critical: criticalCount
    };
  }, [conflicts, totalConflicts]);

  const filteredConflicts = useMemo(() => {
    return conflicts.filter(c => {
      const st = (c.status || '').toLowerCase();
      const isResolved = st === 'resolved' || st === 'dismissed';

      if (filterStatus === 'active' && isResolved) return false;
      if (filterStatus === 'resolved' && !isResolved) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const label = (c.label || '').toLowerCase();
        const desc = (c.description || c.data?.description || '').toLowerCase();
        const cItem = conflictMap[c.id];
        const clA = graphData?.nodes?.find(n => n.id === cItem?.claimAId);
        const clB = graphData?.nodes?.find(n => n.id === cItem?.claimBId);
        const textA = (clA?.fullText || clA?.label || '').toLowerCase();
        const textB = (clB?.fullText || clB?.label || '').toLowerCase();

        if (!label.includes(q) && !desc.includes(q) && !textA.includes(q) && !textB.includes(q)) {
          return false;
        }
      }

      return true;
    });
  }, [conflicts, conflictMap, graphData, filterStatus, searchQuery]);

  const handleCopyConflict = (c, clA, clB) => {
    const textA = clA?.fullText || clA?.label || 'N/A';
    const textB = clB?.fullText || clB?.label || 'N/A';
    const summary = `CONFLICT: ${c.label || c.id}\nStatus: ${c.status || 'Active'}\nSeverity: ${c.severity || 'High'}\nAssertion A: "${textA}"\nAssertion B: "${textB}"`;
    navigator.clipboard.writeText(summary);
    setCopiedConflictId(c.id);
    showToast?.('Conflict summary copied to clipboard');
    setTimeout(() => setCopiedConflictId(null), 2000);
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '14px',
      width: '100%',
      minHeight: '480px',
      background: '#F8FAFC',
      padding: '16px',
      borderRadius: '10px',
      border: '1px solid #E2E8F0',
      boxSizing: 'border-box'
    }}>
      {/* 1. HEADER & METRICS BAR */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '8px',
        padding: '14px 18px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: '#FFF7ED',
              color: '#EA580C',
              fontWeight: 800
            }}>
              ⚖️
            </span>
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, color: '#0F172A' }}>
              Contradictions & Policy Conflicts ({totalConflicts})
            </h3>
            <span style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: '999px',
              background: metrics.active > 0 ? '#FFEDD5' : '#DCFCE7',
              color: metrics.active > 0 ? '#C2410C' : '#15803D',
              border: `1px solid ${metrics.active > 0 ? '#FED7AA' : '#86EFAC'}`
            }}>
              {metrics.active > 0 ? `${metrics.active} Active / Unresolved` : 'All Resolved'}
            </span>
          </div>
          <p style={{ margin: '4px 0 0 36px', fontSize: '0.78rem', color: '#64748B' }}>
            Cross-policy contradictions detected by the Context Layer verification engine for <strong>{asset?.node?.label || 'this asset'}</strong>.
          </p>
        </div>

        {/* Telemetry Chips */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{
            background: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '6px',
            padding: '6px 12px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>Active</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 800, color: metrics.active > 0 ? '#EA580C' : '#059669' }}>
              {metrics.active}
            </div>
          </div>

          <div style={{
            background: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '6px',
            padding: '6px 12px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '0.66rem', color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>Resolved</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#059669' }}>
              {metrics.resolved}
            </div>
          </div>
        </div>
      </div>

      {/* 2. CONTROLS BAR */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '8px',
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        <div style={{
          position: 'relative',
          flex: '1 1 240px',
          maxWidth: '380px'
        }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
          <input
            type="text"
            placeholder="Search conflicts or conflicting assertions..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '6px 28px 6px 30px',
              fontSize: '0.78rem',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              outline: 'none',
              background: '#F8FAFC',
              color: '#0F172A',
              boxSizing: 'border-box'
            }}
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              style={{
                position: 'absolute',
                right: '8px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: '#94A3B8',
                padding: '2px'
              }}
            >
              <X size={12} />
            </button>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', background: '#F1F5F9', padding: '2px', borderRadius: '6px' }}>
          {[
            { id: 'all', label: `All (${totalConflicts})` },
            { id: 'active', label: `⚠️ Active (${metrics.active})` },
            { id: 'resolved', label: `✅ Resolved (${metrics.resolved})` }
          ].map(tab => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setFilterStatus(tab.id)}
              style={{
                padding: '4px 10px',
                fontSize: '0.72rem',
                fontWeight: filterStatus === tab.id ? 700 : 500,
                borderRadius: '5px',
                border: 'none',
                background: filterStatus === tab.id ? '#FFFFFF' : 'transparent',
                color: filterStatus === tab.id ? '#0F172A' : '#64748B',
                boxShadow: filterStatus === tab.id ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 3. CONFLICTS LIST */}
      {totalConflicts === 0 ? (
        <div style={{
          background: '#F0FDF4',
          border: '1px solid #BBF7D0',
          borderRadius: '8px',
          padding: '36px 20px',
          textAlign: 'center',
          color: '#15803D'
        }}>
          <CheckCircle2 size={32} style={{ color: '#16A34A', margin: '0 auto 8px auto' }} />
          <h4 style={{ margin: '0 0 4px 0', fontSize: '0.95rem', fontWeight: 800 }}>
            Zero Contradictions Detected
          </h4>
          <p style={{ margin: 0, fontSize: '0.78rem', color: '#166534' }}>
            All atomic claims extracted from <strong>{asset?.node?.label}</strong> are 100% consistent across your enterprise knowledge base.
          </p>
        </div>
      ) : filteredConflicts.length === 0 ? (
        <div style={{
          background: '#FFFFFF',
          border: '1px dashed #CBD5E1',
          borderRadius: '8px',
          padding: '36px 20px',
          textAlign: 'center',
          color: '#64748B'
        }}>
          <AlertTriangle size={28} style={{ color: '#F59E0B', margin: '0 auto 8px auto' }} />
          <h4 style={{ margin: '0 0 4px 0', fontSize: '0.9rem', color: '#0F172A', fontWeight: 700 }}>
            No matching conflicts found
          </h4>
          <p style={{ margin: 0, fontSize: '0.76rem' }}>
            Try adjusting your search query or status filter.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {filteredConflicts.map((c, idx) => {
            const cItem = conflictMap[c.id];
            const clA = graphData?.nodes?.find(n => n.id === cItem?.claimAId);
            const clB = graphData?.nodes?.find(n => n.id === cItem?.claimBId);
            const st = (c.status || '').toLowerCase();
            const isResolved = st === 'resolved' || st === 'dismissed';
            const severity = (c.severity || 'HIGH').toUpperCase();

            return (
              <div
                key={c.id || idx}
                style={{
                  background: '#FFFFFF',
                  border: isResolved ? '1px solid #BBF7D0' : '1.5px solid #FED7AA',
                  borderRadius: '9px',
                  padding: '14px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
                }}
              >
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{
                      fontSize: '0.66rem',
                      fontWeight: 700,
                      color: '#64748B',
                      background: '#F1F5F9',
                      padding: '2px 7px',
                      borderRadius: '4px'
                    }}>
                      #{idx + 1}
                    </span>
                    <span style={{
                      fontSize: '0.64rem',
                      fontWeight: 800,
                      padding: '2px 8px',
                      borderRadius: '999px',
                      background: isResolved ? '#DCFCE7' : '#FFEDD5',
                      color: isResolved ? '#15803D' : '#C2410C',
                      border: `1px solid ${isResolved ? '#86EFAC' : '#FDBA74'}`
                    }}>
                      {isResolved ? '✅ RESOLVED' : '⚠️ ACTIVE / UNRESOLVED'} &bull; {severity} SEVERITY
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {onFocusInDag && (
                      <button
                        type="button"
                        onClick={() => onFocusInDag(c)}
                        title="Focus this conflict and parent claims in Lineage DAG"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '4px 9px',
                          borderRadius: '5px',
                          border: '1px solid #EA580C',
                          background: '#FFF7ED',
                          color: '#C2410C',
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          transition: 'background 0.15s ease'
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = '#FFEDD5'}
                        onMouseLeave={e => e.currentTarget.style.background = '#FFF7ED'}
                      >
                        <GitBranch size={12} />
                        <span>Focus in DAG</span>
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => handleCopyConflict(c, clA, clB)}
                      title="Copy contradiction summary"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '3px',
                        padding: '4px 8px',
                        borderRadius: '5px',
                        border: '1px solid #E2E8F0',
                        background: copiedConflictId === c.id ? '#DCFCE7' : '#F8FAFC',
                        color: copiedConflictId === c.id ? '#15803D' : '#64748B',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      {copiedConflictId === c.id ? <Check size={12} /> : <Copy size={12} />}
                      <span>{copiedConflictId === c.id ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                </div>

                {/* Conflict Label & Description */}
                <div>
                  <h4 style={{ margin: '0 0 4px 0', fontSize: '0.86rem', fontWeight: 800, color: '#0F172A' }}>
                    {c.label || `Contradiction in ${c.id}`}
                  </h4>
                  {c.description && (
                    <p style={{ margin: 0, fontSize: '0.76rem', color: '#475569', lineHeight: 1.4 }}>
                      {c.description}
                    </p>
                  )}
                </div>

                {/* Side-by-side Assertion Comparison */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: '10px',
                  marginTop: '4px'
                }}>
                  {/* Assertion A (This Document) */}
                  <div style={{
                    background: '#F0F9FF',
                    border: '1px solid #BAE6FD',
                    borderLeft: '4px solid #0284C7',
                    borderRadius: '6px',
                    padding: '10px 12px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '6px'
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#0284C7', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Assertion A &bull; {asset?.node?.label || 'This Document'}
                        </span>
                        {clA && (
                          <span style={{ fontSize: '0.64rem', fontWeight: 700, color: '#0369A1' }}>
                            Trust: {Math.round((clA.trustScore ?? 0.95) * 100)}%
                          </span>
                        )}
                      </div>
                      <p style={{ margin: 0, fontSize: '0.76rem', color: '#0F172A', fontWeight: 600, lineHeight: 1.4 }}>
                        "{clA?.fullText || clA?.label || cItem?.claimAText || 'Assertion statement from current policy'}"
                      </p>
                    </div>

                    {onLocateInDoc && clA && (
                      <div style={{ paddingTop: '4px' }}>
                        <button
                          type="button"
                          onClick={() => onLocateInDoc(clA)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '2px 6px',
                            fontSize: '0.64rem',
                            fontWeight: 600,
                            color: '#0284C7',
                            background: '#FFFFFF',
                            border: '1px solid #BAE6FD',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        >
                          <FileText size={10} />
                          Locate in Canvas
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Assertion B (Opposing Document) */}
                  <div style={{
                    background: '#FFF7ED',
                    border: '1px solid #FED7AA',
                    borderLeft: '4px solid #EA580C',
                    borderRadius: '6px',
                    padding: '10px 12px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '6px'
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '0.64rem', fontWeight: 800, color: '#EA580C', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Assertion B &bull; Opposing Policy
                        </span>
                        {clB && (
                          <span style={{ fontSize: '0.64rem', fontWeight: 700, color: '#C2410C' }}>
                            Trust: {Math.round((clB.trustScore ?? 0.95) * 100)}%
                          </span>
                        )}
                      </div>
                      <p style={{ margin: 0, fontSize: '0.76rem', color: '#0F172A', fontWeight: 600, lineHeight: 1.4 }}>
                        "{clB?.fullText || clB?.label || cItem?.claimBText || 'Contradicting statement from enterprise knowledge'}"
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
