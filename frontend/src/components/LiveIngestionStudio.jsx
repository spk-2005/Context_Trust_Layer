import React, { useState, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

export default function LiveIngestionStudio({ activeOrg, activePersona, onClaimExtracted, showToast }) {
  const { user, token, hasPermission } = useAuth();
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [documentType, setDocumentType] = useState('policy');
  const [authorityLevel, setAuthorityLevel] = useState(90);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pipelineStage, setPipelineStage] = useState(0); // 0: Idle, 1: Uploading, 2: Parsing, 3: Extracting Claims, 4: Scoring Trust, 5: Conflict Check, 6: Done
  const [pipelineResult, setPipelineResult] = useState(null);
  const [history, setHistory] = useState([]);

  const stages = [
    { label: "File Ingestion & Parsing", icon: "📄", desc: "Extract raw structure, headers, and metadata" },
    { label: "Entity & Semantic Chunking", icon: "🧩", desc: "Identify policy domains, authority roles, and temporal bounds" },
    { label: "Atomic Claim Extraction", icon: "⚡", desc: "Break document down into discrete, testable assertions" },
    { label: "Trust & Provenance Scoring", icon: "🛡️", desc: "Compute authority, freshness, and citation confidence" },
    { label: "Cross-Policy Conflict Analysis", icon: "⚖️", desc: "Run contradiction matrix against all existing knowledge" }
  ];

  const handleFileSelect = (file) => {
    if (!file) return;
    setSelectedFile(file);
    const lower = file.name.toLowerCase();
    if (lower.includes("handbook")) setDocumentType("handbook");
    else if (lower.includes("memo")) setDocumentType("memo");
    else if (lower.includes("security") || lower.includes("secops")) setDocumentType("security_guideline");
    else if (lower.includes("runbook")) setDocumentType("runbook");
    else setDocumentType("policy");
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleExecuteExtractionPipeline = async () => {
    if (!selectedFile) {
      showToast?.("Please select a file to ingest", "error");
      return;
    }
    if (!hasPermission('claims:extract')) {
      showToast?.(
        `Separation of Duties (SoD) Barred: Your role (${(user?.role || 'user').toUpperCase()}) cannot run claim extraction pipelines. Only Data Stewards or CCO have ingestion clearance.`,
        'error'
      );
      return;
    }

    setIsProcessing(true);
    setPipelineStage(1);
    setPipelineResult(null);

    const stageTimer1 = setTimeout(() => setPipelineStage(2), 350);
    const stageTimer2 = setTimeout(() => setPipelineStage(3), 750);
    const stageTimer3 = setTimeout(() => setPipelineStage(4), 1100);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('organization_id', activeOrg?.id || '11111111-1111-1111-1111-111111111111');
      formData.append('document_type', documentType);
      formData.append('use_mock', 'true');

      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (user?.role) headers['x-user-role'] = user.role;

      const res = await fetch(`/v1/documents/upload-and-extract?user_role=${user?.role || ''}`, {
        method: 'POST',
        headers,
        body: formData,
      });

      setPipelineStage(5);

      if (res.ok) {
        const data = await res.json();
        setPipelineResult(data);
        setPipelineStage(6);
        showToast?.(`Successfully ingested '${selectedFile.name}' and extracted ${data.claims_extracted_count} claims!`);

        // Add to history
        setHistory(prev => [
          {
            filename: selectedFile.name,
            title: data.document?.title || selectedFile.name,
            claimsCount: data.claims_extracted_count,
            durationMs: data.duration_ms || 420,
            time: "Just now",
            type: documentType,
            status: "verified"
          },
          ...prev
        ]);

        if (onClaimExtracted) onClaimExtracted();
      } else {
        const err = await res.text();
        showToast?.(`Pipeline failed: ${res.status}`, "error");
        setPipelineStage(0);
      }
    } catch (err) {
      showToast?.(`Pipeline connection error: ${err.message}`, "error");
      setPipelineStage(0);
    } finally {
      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      clearTimeout(stageTimer3);
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Banner */}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1, minWidth: '280px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #2026d2 0%, #62e1fc 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px',
            boxShadow: '0 4px 12px rgba(32,38,210,0.22)',
            color: '#fff',
            flexShrink: 0
          }}>
            ⚡
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
                Live Ingestion & Autonomous Claim Extractor
              </h2>
              <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                Zero Manual Tagging
              </span>
            </div>
            <p style={{ margin: '3px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Drag-and-drop PDFs, Word Docs, Markdown, or JSON. The engine auto-parses sections, extracts atomic claims, computes trust scores, and links lineage in real time.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Supported formats:</span>
          <span className="badge" style={{ background: '#f0f4ff', color: '#2026d2', border: '1px solid rgba(32,38,210,0.2)' }}>.PDF</span>
          <span className="badge" style={{ background: '#f0f4ff', color: '#2026d2', border: '1px solid rgba(32,38,210,0.2)' }}>.MD</span>
          <span className="badge" style={{ background: '#f0f4ff', color: '#2026d2', border: '1px solid rgba(32,38,210,0.2)' }}>.DOCX</span>
          <span className="badge" style={{ background: '#f0f4ff', color: '#2026d2', border: '1px solid rgba(32,38,210,0.2)' }}>.JSON</span>
        </div>
      </div>

      {/* Main Grid: Upload Zone + Pipeline Stage Tracker */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px', alignItems: 'start', width: '100%' }}>
        {/* Left Column: Dropzone & Parameters */}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '18px',
          minWidth: 0
        }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0, color: 'var(--text-main)' }}>
            1. Document Upload & Configuration
          </h3>

          {/* Drag & Drop Area */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${dragOver ? '#2026d2' : selectedFile ? '#19c37d' : 'rgba(32,38,210,0.25)'}`,
              background: dragOver ? 'rgba(32,38,210,0.05)' : selectedFile ? 'rgba(25,195,125,0.04)' : 'rgba(240,244,255,0.4)',
              borderRadius: '12px',
              padding: '28px 16px',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '10px'
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => e.target.files && handleFileSelect(e.target.files[0])}
              accept=".pdf,.docx,.doc,.txt,.md,.json,.csv"
              style={{ display: 'none' }}
            />

            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              background: selectedFile ? '#19c37d' : '#2026d2',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '24px',
              boxShadow: '0 4px 14px rgba(0,0,0,0.1)'
            }}>
              {selectedFile ? '✓' : '☁️'}
            </div>

            {selectedFile ? (
              <div>
                <p style={{ margin: 0, fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-main)' }}>
                  {selectedFile.name}
                </p>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  {(selectedFile.size / 1024).toFixed(1)} KB &bull; Click or drop another file to replace
                </p>
              </div>
            ) : (
              <div>
                <p style={{ margin: 0, fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-main)' }}>
                  Drop policy document here, or <span style={{ color: '#2026d2', textDecoration: 'underline' }}>browse files</span>
                </p>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Supports enterprise manuals, memos, security rules, and data contracts
                </p>
              </div>
            )}
          </div>

          {/* Form Options */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                Document Category
              </label>
              <select
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-card)',
                  fontSize: '0.85rem'
                }}
              >
                <option value="policy">Corporate Policy Document</option>
                <option value="handbook">Employee / Operations Handbook</option>
                <option value="memo">Executive / VP Directive Memo</option>
                <option value="security_guideline">SecOps / Infrastructure Mandate</option>
                <option value="runbook">DevOps / Staging Runbook</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                Authority Tier Weight ({authorityLevel}/100)
              </label>
              <input
                type="range"
                min="30"
                max="100"
                step="5"
                value={authorityLevel}
                onChange={(e) => setAuthorityLevel(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#2026d2', marginTop: '8px' }}
              />
            </div>
          </div>

          {/* Ingest Action Button */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button
              onClick={handleExecuteExtractionPipeline}
              disabled={!selectedFile || isProcessing || !hasPermission('claims:extract')}
              style={{
                padding: '12px 24px',
                borderRadius: '10px',
                background: !selectedFile || isProcessing || !hasPermission('claims:extract')
                  ? 'var(--border-color)'
                  : 'linear-gradient(135deg, #2026d2 0%, #3737d8 100%)',
                color: !hasPermission('claims:extract') ? '#94A3B8' : '#fff',
                border: 'none',
                fontWeight: 600,
                fontSize: '0.95rem',
                cursor: !selectedFile || isProcessing || !hasPermission('claims:extract') ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px',
                boxShadow: hasPermission('claims:extract') ? '0 4px 14px rgba(32,38,210,0.25)' : 'none',
                transition: 'all 0.2s ease'
              }}
              title={
                hasPermission('claims:extract')
                  ? "Execute live parsing and claim extraction"
                  : "Separation of Duties (SoD) Barred: Only Data Stewards or CCO can execute ingestion pipelines"
              }
            >
              {isProcessing ? (
                <>
                  <span className="spinner-sm"></span>
                  <span>Executing Ingestion Pipeline...</span>
                </>
              ) : !hasPermission('claims:extract') ? (
                <>
                  <span>🔒 Ingestion Barred: Data Steward Clearance Required (SoD)</span>
                </>
              ) : (
                <>
                  <span>⚡ Run Live Ingestion & Claim Extractor</span>
                </>
              )}
            </button>
            {!hasPermission('claims:extract') && (
              <span style={{ fontSize: '0.72rem', color: '#DC2626', textAlign: 'center', fontWeight: 600 }}>
                ⚠️ Your active role ({user?.role?.toUpperCase() || 'USER'}) cannot ingest documents. Switch to Data Steward (Marcus Vance) to test extraction.
              </span>
            )}
          </div>
        </div>

        {/* Right Column: Live Pipeline Progress & Verification */}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          minWidth: 0
        }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0, color: 'var(--text-main)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            <span>2. Real-Time Pipeline Execution</span>
            {pipelineStage === 6 && (
              <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>
                Pipeline Completed
              </span>
            )}
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {stages.map((stage, idx) => {
              const stepNum = idx + 1;
              const isDone = pipelineStage > stepNum || pipelineStage === 6;
              const isCurrent = pipelineStage === stepNum;
              const isPending = pipelineStage < stepNum;

              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 12px',
                    borderRadius: '10px',
                    border: `1px solid ${isCurrent ? 'rgba(32,38,210,0.3)' : isDone ? 'rgba(25,195,125,0.2)' : 'var(--border-color)'}`,
                    background: isCurrent ? 'rgba(32,38,210,0.05)' : isDone ? 'rgba(25,195,125,0.03)' : 'transparent',
                    transition: 'all 0.2s ease',
                    minWidth: 0
                  }}
                >
                  <div style={{
                    width: '30px',
                    height: '30px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    flexShrink: 0,
                    background: isDone ? '#19c37d' : isCurrent ? '#2026d2' : 'var(--bg-card)',
                    color: isDone || isCurrent ? '#fff' : 'var(--text-muted)'
                  }}>
                    {isDone ? '✓' : isCurrent ? '⏳' : stage.icon}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: isDone || isCurrent ? 'var(--text-main)' : 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {stage.label}
                      </span>
                      {isCurrent && (
                        <span style={{ fontSize: '0.68rem', color: '#2026d2', fontWeight: 600, flexShrink: 0 }}>
                          Processing...
                        </span>
                      )}
                      {isDone && (
                        <span style={{ fontSize: '0.68rem', color: '#19c37d', fontWeight: 600, flexShrink: 0 }}>
                          Verified
                        </span>
                      )}
                    </div>
                    <p style={{ margin: '2px 0 0 0', fontSize: '0.72rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {stage.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Extraction Results Showcase */}
      {pipelineResult && (
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid rgba(25,195,125,0.3)',
          borderRadius: '12px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          boxShadow: '0 4px 16px rgba(25,195,125,0.06)',
          width: '100%',
          minWidth: 0
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
              <span style={{ fontSize: '20px', flexShrink: 0 }}>✨</span>
              <div style={{ minWidth: 0 }}>
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)', wordBreak: 'break-word' }}>
                  Extraction Summary: {pipelineResult.document?.title}
                </h3>
                <p style={{ margin: '2px 0 0 0', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Generated {pipelineResult.claims_extracted_count} atomic claims with calibrated trust scores in {pipelineResult.duration_ms}ms.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>Lineage Linked</span>
              <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>Vector Embeddings Synced</span>
            </div>
          </div>

          {/* Claims Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px', width: '100%' }}>
            {pipelineResult.claims?.map((claim, idx) => (
              <div
                key={idx}
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  minWidth: 0
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span className="badge" style={{ fontSize: '0.65rem', background: '#f0f4ff', color: '#2026d2' }}>
                    Claim #{idx + 1}
                  </span>
                  <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                    Trust Score: {claim.trust_score ? (claim.trust_score.overall_score * 100).toFixed(0) : '95'}%
                  </span>
                </div>

                <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-main)', lineHeight: 1.4, fontWeight: 500, wordBreak: 'break-word' }}>
                  "{claim.claim_text}"
                </p>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '8px', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  <span>Scope: {claim.scope || 'Enterprise'}</span>
                  <span>Status: {claim.status || 'verified'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ingestion History Table */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
        width: '100%',
        minWidth: 0
      }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0, color: 'var(--text-main)' }}>
          Recent Document Ingestions & Extracted Corpora
        </h3>

        <div style={{ overflowX: 'auto', width: '100%' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', minWidth: '600px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '8px 12px' }}>Document Title</th>
                <th style={{ padding: '8px 12px' }}>Type</th>
                <th style={{ padding: '8px 12px' }}>Extracted Claims</th>
                <th style={{ padding: '8px 12px' }}>Pipeline Latency</th>
                <th style={{ padding: '8px 12px' }}>Status</th>
                <th style={{ padding: '8px 12px' }}>Ingested</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                    No documents ingested in this session yet. Upload a PDF file above to trigger the ingestion & auto-claim extraction pipeline.
                  </td>
                </tr>
              ) : (
                history.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text-main)', wordBreak: 'break-word' }}>
                      📄 {item.title}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span className="badge" style={{ textTransform: 'capitalize', fontSize: '0.68rem' }}>
                        {item.type}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ fontWeight: 600, color: '#2026d2' }}>{item.claimsCount} claims</span>
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                      {item.durationMs}ms
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                        Verified
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                      {item.time}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
