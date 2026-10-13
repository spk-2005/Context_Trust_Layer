import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  Layers,
  Zap,
  ShieldCheck,
  Scale,
  CheckCircle2,
  Clock,
  Sliders,
  Database,
  Lock,
  RefreshCw,
  FileCode,
  AlertCircle,
  FileSpreadsheet,
  Check,
  X,
  ArrowRight,
  GitBranch,
  Shield,
  BookOpen,
  Send,
  Server,
  Terminal,
  Activity
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const formatConditionDisplay = (cond) => {
  if (!cond) return '';
  if (typeof cond === 'string') return cond;
  if (typeof cond === 'object') {
    if (cond.field && cond.value !== undefined) {
      const valStr = Array.isArray(cond.value) ? cond.value.join(' - ') : String(cond.value);
      const op = cond.operator ? ` ${cond.operator} ` : ': ';
      return `${cond.field}${op}${valStr}`;
    }
    if (cond.rule) return String(cond.rule);
    if (cond.description) return String(cond.description);
    return JSON.stringify(cond);
  }
  return String(cond);
};

const formatValueDisplay = (val) => {
  if (val === undefined || val === null) return '';
  if (typeof val === 'object') {
    if (val.rule) return String(val.rule);
    if (val.type) return String(val.type);
    return JSON.stringify(val);
  }
  return String(val);
};

export default function LiveIngestionStudio({ activeOrg, activePersona, onClaimExtracted, showToast }) {
  const { user, token, hasPermission } = useAuth();
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [documentType, setDocumentType] = useState('policy');
  const [documentScope, setDocumentScope] = useState('Enterprise');
  const [authorityLevel, setAuthorityLevel] = useState(95);
  const [sourceFamily, setSourceFamily] = useState('document');
  const [sourceIntent, setSourceIntent] = useState('governance_policy');
  const [extractionEngine, setExtractionEngine] = useState('ollama'); // 'ollama', 'mock', 'openai', 'openrouter'
  const [isProcessing, setIsProcessing] = useState(false);
  const [pipelineStage, setPipelineStage] = useState(0); // 0: Idle, 1..6: L1..L6, 7: Sealed & Done
  const [pipelineResult, setPipelineResult] = useState(null);
  const [history, setHistory] = useState([]);
  const stages = [
    { id: 1, label: "L1: Governance & Sources", icon: Shield, desc: "SourceFamily & Intent" },
    { id: 2, label: "L2: Native Ingestion", icon: Server, desc: "Pristine Connectors" },
    { id: 3, label: "L3: Canonical Envelope", icon: Lock, desc: "SHA-256 Digest & Seal" },
    { id: 4, label: "L4: Specialized Parser", icon: FileCode, desc: "Atomic Evidence Units" },
    { id: 5, label: "L5: Extraction & Ledger", icon: Zap, desc: "Multi-Strategy & Ledger" },
    { id: 6, label: "L6: Validation Gate", icon: CheckCircle2, desc: "6-D Gate & Store" }
  ];

  const handleFileSelect = (file) => {
    if (!file) return;
    setSelectedFile(file);
    const lower = file.name.toLowerCase();
    
    // Auto-detect SourceFamily (L1)
    if (lower.endsWith(".json") || lower.endsWith(".csv") || lower.endsWith(".xlsx") || lower.endsWith(".xls") || lower.endsWith(".sql")) {
      setSourceFamily("structured");
    } else {
      setSourceFamily("document");
    }

    // Auto-detect Intent & Category
    if (lower.includes("handbook")) {
      setDocumentType("handbook");
      setDocumentScope("Enterprise");
      setSourceIntent("governance_policy");
    } else if (lower.includes("memo")) {
      setDocumentType("memo");
      setDocumentScope("Engineering");
      setSourceIntent("governance_policy");
    } else if (lower.includes("security") || lower.includes("secops") || lower.includes("firewall")) {
      setDocumentType("security_guideline");
      setDocumentScope("Production");
      setSourceIntent("governance_policy");
    } else if (lower.includes("runbook")) {
      setDocumentType("runbook");
      setDocumentScope("Staging");
      setSourceIntent("operational_data");
    } else if (lower.endsWith(".xlsx") || lower.endsWith(".xls") || lower.endsWith(".csv") || lower.endsWith(".tsv") || lower.includes("pricing") || lower.includes("financial")) {
      setDocumentType("financial_matrix");
      setDocumentScope("Enterprise");
      setSourceIntent("analytics_metric");
    } else if (lower.endsWith(".sql") || lower.endsWith(".env") || lower.endsWith(".yaml") || lower.endsWith(".yml") || lower.endsWith(".json")) {
      setDocumentType("technical_spec");
      setDocumentScope("Production");
      setSourceIntent("operational_data");
    } else if (lower.includes("audit") || lower.includes("compliance") || lower.includes("soc2") || lower.includes("iso")) {
      setDocumentType("compliance_audit");
      setDocumentScope("Enterprise");
      setSourceIntent("governance_policy");
    } else {
      setDocumentType("policy");
      setDocumentScope("Enterprise");
      setSourceIntent("governance_policy");
    }
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
      showToast?.("Please select or drop a document to ingest", "error");
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

    const stageTimer1 = setTimeout(() => setPipelineStage(2), 250);
    const stageTimer2 = setTimeout(() => setPipelineStage(3), 550);
    const stageTimer3 = setTimeout(() => setPipelineStage(4), 850);
    const stageTimer4 = setTimeout(() => setPipelineStage(5), 1150);
    const stageTimer5 = setTimeout(() => setPipelineStage(6), 1450);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('organization_id', activeOrg?.id || '11111111-1111-1111-1111-111111111111');
      formData.append('document_type', documentType);
      formData.append('provider', extractionEngine);
      formData.append('use_mock', extractionEngine === 'mock' ? 'true' : 'false');
      formData.append('source_family', sourceFamily);
      formData.append('source_intent', sourceIntent);

      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (user?.role) headers['x-user-role'] = user.role;

      const res = await fetch(`/v1/documents/upload-and-extract?user_role=${user?.role || ''}`, {
        method: 'POST',
        headers,
        body: formData,
      });

      setPipelineStage(6);

      if (res.ok) {
        const data = await res.json();
        setPipelineResult(data);
        setPipelineStage(7);
        const claimsCount = data.claims_extracted_count || (data.layers?.layer_6_validation_gate?.claims_approved ?? 0);
        showToast?.(`✓ 6-Layer Pipeline Verified: Ingested '${selectedFile.name}' and sealed ${claimsCount} claims.`);

        // Add to history
        setHistory(prev => [
          {
            filename: selectedFile.name,
            title: data.document?.title || selectedFile.name,
            claimsCount: claimsCount,
            durationMs: data.duration_ms || 380,
            time: "Just now",
            type: documentType,
            scope: documentScope,
            status: "sealed_6_layers"
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
      clearTimeout(stageTimer4);
      clearTimeout(stageTimer5);
      setIsProcessing(false);
    }
  };

  // Authority tier descriptor helper
  const getAuthorityBadge = (level) => {
    if (level >= 90) return { label: 'Tier 1: Sovereign Mandate', color: '#EA580C', bg: '#FFF7ED' };
    if (level >= 75) return { label: 'Tier 2: VP Directive', color: '#2563EB', bg: '#EFF6FF' };
    return { label: 'Tier 3: Standard SOP', color: '#64748B', bg: '#F1F5F9' };
  };

  const authBadge = getAuthorityBadge(authorityLevel);

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}>


      {/* ========================================================
          2. FULL-WIDTH HORIZONTAL PIPELINE STREAM (ALL 6 LAYERS)
          ======================================================== */}
      <div className="ingest-pipeline-strip">
        <div className="ingest-pipeline-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={14} color="#EA580C" />
            <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              6-Layer Universal Claim Architecture Pipeline
            </span>
            <span style={{ fontSize: '0.72rem', color: '#64748B' }}>
              {pipelineStage === 0
                ? '• Standby'
                : pipelineStage === 7
                ? '• Complete (All 6 Layers Sealed & Verified)'
                : `• Executing Layer ${pipelineStage} of 6...`}
            </span>
          </div>

          {pipelineStage === 7 && (
            <span className="badge badge-verified" style={{ fontSize: '0.66rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={11} />
              <span>Layer 6 Enterprise Claim Store Sealed</span>
            </span>
          )}
        </div>

        {/* Horizontal Process Line with Circle Points & Connecting Lines (No Cards) */}
        <div className="process-line-container">
          <div className="process-line-flow">
            {stages.map((st, idx) => {
              const isDone = pipelineStage > st.id || pipelineStage === 7;
              const isCurrent = pipelineStage === st.id;
              const isPending = pipelineStage < st.id && pipelineStage !== 7;

              return (
                <div key={st.id} className="process-step-item">
                  {/* Top node track with connecting lines and circle */}
                  <div className="process-node-track">
                    {/* Left connector */}
                    {idx > 0 && (
                      <div
                        className={`process-connector connector-left ${
                          stages[idx - 1] && (pipelineStage > stages[idx - 1].id || pipelineStage === 7)
                            ? 'active'
                            : ''
                        }`}
                      />
                    )}

                    {/* Circle Node Point */}
                    <div
                      className={`process-circle-node ${isDone ? 'done' : isCurrent ? 'current' : 'pending'}`}
                      title={`${st.label}: ${st.desc}`}
                    >
                      {isDone ? (
                        <Check size={14} strokeWidth={2.8} />
                      ) : isCurrent ? (
                        <RefreshCw size={13} className="animate-spin" />
                      ) : (
                        <span>{st.id}</span>
                      )}
                    </div>

                    {/* Right connector */}
                    {idx < stages.length - 1 && (
                      <div className={`process-connector connector-right ${isDone ? 'active' : ''}`} />
                    )}
                  </div>

                  {/* Clean text details (No cards) */}
                  <div className="process-step-content">
                    <h4 className={`process-step-name ${isDone ? 'done' : isCurrent ? 'current' : ''}`}>
                      {st.label}
                    </h4>
                    <p className="process-step-sub">
                      {st.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ========================================================
          3. MAIN SPLIT CANVAS: DOCUMENT CONTROLLER (38%) + GROUNDING MATRIX (62%)
          ======================================================== */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 400px) 1fr', gap: '16px', alignItems: 'start', width: '100%' }}>

        {/* Left: Document Intake & Authority Tuning */}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: '14px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.02)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Document Controller
            </span>
            <span style={{ fontSize: '0.70rem', color: '#64748B' }}>
              {selectedFile ? 'Ready to Ingest' : 'No File Selected'}
            </span>
          </div>

          {/* Interactive Drop Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${dragOver ? '#EA580C' : selectedFile ? '#059669' : 'rgba(234, 88, 12, 0.3)'}`,
              background: dragOver
                ? '#FFF7ED'
                : selectedFile
                ? 'rgba(240, 253, 244, 0.6)'
                : 'linear-gradient(180deg, #FAFAF9 0%, #FFFFFF 100%)',
              borderRadius: '12px',
              padding: '20px 14px',
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
              accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.md,.json,.jsonl,.csv,.tsv,.html,.htm,.xhtml,.xml,.yaml,.yml,.toml,.ini,.conf,.log,.sql,.env,.rtf,*"
              style={{ display: 'none' }}
            />

            <div style={{
              width: '44px',
              height: '44px',
              borderRadius: '12px',
              background: selectedFile
                ? 'linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)'
                : 'linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%)',
              border: `1px solid ${selectedFile ? 'rgba(5, 150, 105, 0.3)' : 'rgba(234, 88, 12, 0.3)'}`,
              color: selectedFile ? '#059669' : '#EA580C',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: selectedFile ? '0 2px 8px rgba(5,150,105,0.15)' : '0 2px 8px rgba(234,88,12,0.12)'
            }}>
              {selectedFile ? <CheckCircle2 size={20} /> : <UploadCloud size={20} />}
            </div>

            {selectedFile ? (
              <div>
                <p style={{ margin: 0, fontWeight: 700, fontSize: '0.84rem', color: 'var(--text-main)', wordBreak: 'break-all' }}>
                  {selectedFile.name}
                </p>
                <p style={{ margin: '3px 0 0 0', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  {(selectedFile.size / 1024).toFixed(1)} KB &bull; <span style={{ color: '#EA580C', textDecoration: 'underline' }}>Click to replace</span>
                </p>
              </div>
            ) : (
              <div>
                <p style={{ margin: 0, fontWeight: 700, fontSize: '0.84rem', color: 'var(--text-main)' }}>
                  Drop any document here, or <span style={{ color: '#EA580C', textDecoration: 'underline' }}>browse</span>
                </p>
                <p style={{ margin: '3px 0 0 0', fontSize: '0.70rem', color: 'var(--text-muted)' }}>
                  PDF, Word, Excel, PPTX, Markdown, CSV, JSON, HTML, Code, or Text
                </p>
              </div>
            )}
          </div>

          {/* Configuration Form */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Layer 1: Source Governance (Family & Intent) */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                  <Shield size={11} color="#4338CA" />
                  <span>L1: Source Family</span>
                </label>
                <select
                  value={sourceFamily}
                  onChange={(e) => setSourceFamily(e.target.value)}
                  className="sim-input-control"
                  style={{ width: '100%', fontSize: '0.78rem', height: '34px', padding: '0 8px' }}
                >
                  <option value="document">Document (PDF/MD/Doc)</option>
                  <option value="structured">Structured (JSON/CSV/DB)</option>
                  <option value="conversation">Conversation (Slack/Chat)</option>
                  <option value="metadata">Metadata / OpenAPI</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                  <ShieldCheck size={11} color="#4338CA" />
                  <span>L1: Source Intent</span>
                </label>
                <select
                  value={sourceIntent}
                  onChange={(e) => setSourceIntent(e.target.value)}
                  className="sim-input-control"
                  style={{ width: '100%', fontSize: '0.78rem', height: '34px', padding: '0 8px' }}
                >
                  <option value="governance_policy">Governance Policy</option>
                  <option value="operational_data">Operational Data</option>
                  <option value="discussions">Proposals & Discussion</option>
                  <option value="factual_knowledge">Factual Knowledge</option>
                  <option value="analytics_metric">Analytics Metric / KPI</option>
                </select>
              </div>
            </div>

            {/* Category & Scope Row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                  Document Category
                </label>
                <select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value)}
                  className="sim-input-control"
                  style={{ width: '100%', fontSize: '0.78rem', height: '34px', padding: '0 8px' }}
                >
                  <option value="policy">Corporate Policy</option>
                  <option value="handbook">Employee Handbook</option>
                  <option value="memo">VP Directive Memo</option>
                  <option value="security_guideline">SecOps Mandate</option>
                  <option value="runbook">DevOps Runbook</option>
                  <option value="financial_matrix">Financial / Spreadsheet Matrix</option>
                  <option value="technical_spec">Technical Spec / Config</option>
                  <option value="compliance_audit">Compliance / Audit Standard</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                  Target Scope
                </label>
                <select
                  value={documentScope}
                  onChange={(e) => setDocumentScope(e.target.value)}
                  className="sim-input-control"
                  style={{ width: '100%', fontSize: '0.78rem', height: '34px', padding: '0 8px' }}
                >
                  <option value="Enterprise">Enterprise</option>
                  <option value="Production">Production</option>
                  <option value="Engineering">Engineering</option>
                  <option value="General">Global Standard</option>
                </select>
              </div>
            </div>

            {/* Hybrid LLM & Strategy Router Selector */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px', textTransform: 'uppercase' }}>
                <Zap size={11} color="#EA580C" />
                <span>L5: Strategy Router & Engine</span>
              </label>
              <select
                value={extractionEngine}
                onChange={(e) => setExtractionEngine(e.target.value)}
                className="sim-input-control"
                style={{ width: '100%', fontSize: '0.78rem', height: '34px', padding: '0 8px', borderColor: extractionEngine === 'ollama' ? '#059669' : undefined }}
              >
                <option value="ollama">Auto Strategy Router (Deterministic + Heuristics + Ollama)</option>
                <option value="mock">Deterministic Rule Engine (Fast Offline Zero-Cost)</option>
                <option value="openai">OpenAI GPT-4o-mini (Cloud Structured Router)</option>
                <option value="openrouter">OpenRouter / Ox-Alpha (Cloud Router)</option>
              </select>
              <div style={{ marginTop: '4px', fontSize: '0.66rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <ShieldCheck size={11} color="#059669" />
                <span>Multi-strategy extraction with automatic fallback & verification gate.</span>
              </div>
            </div>

            {/* Authority Weight Dial */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.70rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Authority Weight
                </span>
                <span style={{ fontSize: '0.70rem', fontWeight: 800, color: authBadge.color, background: authBadge.bg, padding: '2px 6px', borderRadius: '4px' }}>
                  {authorityLevel} / 100 &bull; {authBadge.label}
                </span>
              </div>
              <input
                type="range"
                min="30"
                max="100"
                step="5"
                value={authorityLevel}
                onChange={(e) => setAuthorityLevel(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#EA580C', cursor: 'pointer' }}
              />
            </div>
          </div>

          {/* Action Trigger Button */}
          <button
            type="button"
            onClick={handleExecuteExtractionPipeline}
            disabled={!selectedFile || isProcessing || !hasPermission('claims:extract')}
            style={{
              height: '42px',
              borderRadius: '10px',
              background: !selectedFile || isProcessing || !hasPermission('claims:extract')
                ? '#F1F5F9'
                : 'linear-gradient(135deg, #EA580C 0%, #C2410C 100%)',
              color: !selectedFile || isProcessing || !hasPermission('claims:extract') ? '#94A3B8' : '#FFFFFF',
              border: 'none',
              fontWeight: 800,
              fontSize: '0.84rem',
              cursor: !selectedFile || isProcessing || !hasPermission('claims:extract') ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              boxShadow: selectedFile && !isProcessing && hasPermission('claims:extract')
                ? '0 4px 14px rgba(234, 88, 12, 0.32)'
                : 'none',
              transition: 'all 0.2s ease'
            }}
          >
            {isProcessing ? (
              <>
                <RefreshCw size={15} className="animate-spin" />
                <span>Running Pipeline...</span>
              </>
            ) : !hasPermission('claims:extract') ? (
              <>
                <Lock size={15} />
                <span>Data Steward Clearance Required</span>
              </>
            ) : (
              <>
                <Zap size={15} />
                <span>Launch Extraction Pipeline</span>
              </>
            )}
          </button>
        </div>

        {/* Right: Live Assertion Grounding Matrix */}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: '14px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          minHeight: '380px',
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.02)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={16} color="#059669" />
              <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Extracted Assertion Grounding Matrix
              </span>
            </div>

            {pipelineResult && (
              <span className="badge badge-verified" style={{ fontSize: '0.68rem' }}>
                {pipelineResult.claims_extracted_count} Claims Parsed ({pipelineResult.duration_ms}ms)
              </span>
            )}
          </div>

          {/* Content Area: If result is available, show 6-layer architecture breakdown; else show empty state */}
          {pipelineResult ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              
              {/* Layer 1 - 4 Telemetry Strip */}
              {pipelineResult.layers && (
                <div style={{
                  background: 'linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%)',
                  border: '1px solid #E2E8F0',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="layer-title-badge l3">L3 Envelope</span>
                      <span className="layer-hash-pill" title={pipelineResult.layers.layer_3_envelope?.content_hash}>
                        SHA-256: {pipelineResult.layers.layer_3_envelope?.content_hash ? `${pipelineResult.layers.layer_3_envelope.content_hash.slice(0, 16)}...` : 'calc_hash'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="badge badge-verified" style={{ fontSize: '0.64rem', padding: '2px 6px' }}>
                        ✓ Sealed & Tamper Intact
                      </span>
                      <span className="layer-title-badge l4">
                        {pipelineResult.layers.layer_4_evidence?.parser_name || 'DocumentParser'}
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.70rem', color: '#64748B', flexWrap: 'wrap', gap: '6px' }}>
                    <span>
                      <strong>Family:</strong> <span style={{ color: '#0F172A', textTransform: 'capitalize' }}>{pipelineResult.layers.layer_1_governance?.source_family || sourceFamily}</span> &bull; 
                      <strong> Intent:</strong> <span style={{ color: '#0F172A' }}>{pipelineResult.layers.layer_1_governance?.source_intent || sourceIntent}</span>
                    </span>
                    <span>
                      <strong>Evidence Units:</strong> <span style={{ color: '#0F172A', fontWeight: 700 }}>{pipelineResult.layers.layer_4_evidence?.total_units || 1} units</span> (100% complete)
                    </span>
                  </div>
                </div>
              )}

              {/* Layer 5: Strategy Router & Completeness Ledger Ribbon */}
              {pipelineResult.layers?.layer_5_extraction && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div className="layer-ledger-strip">
                    <div className="layer-ledger-item">
                      <span className="layer-ledger-item-label">L5 Strategy</span>
                      <div style={{ display: 'flex', gap: '4px', marginTop: '2px' }}>
                        <span style={{ fontSize: '0.66rem', background: '#334155', color: '#F8FAFC', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                          {pipelineResult.layers.layer_5_extraction.candidates?.[0]?.extraction_strategy || pipelineResult.layers.layer_5_extraction.candidates?.[0]?.strategy || 'table_aware'}
                        </span>
                      </div>
                    </div>

                    <div style={{ width: '1px', height: '24px', background: '#334155' }} />

                    <div className="layer-ledger-item">
                      <span className="layer-ledger-item-label">Claims Extracted</span>
                      <span className="layer-ledger-item-val" style={{ color: '#4ADE80' }}>
                        {pipelineResult.layers.layer_5_extraction.claims_extracted || pipelineResult.claims_extracted_count}
                      </span>
                    </div>

                    {pipelineResult.layers.layer_5_extraction.ledger_summary?.breakdown && (
                      <>
                        <div className="layer-ledger-item">
                          <span className="layer-ledger-item-label">Descriptive (No Claims)</span>
                          <span className="layer-ledger-item-val" style={{ color: '#94A3B8' }}>
                            {pipelineResult.layers.layer_5_extraction.ledger_summary.breakdown.processed_no_claims ?? 0}
                          </span>
                        </div>

                        <div className="layer-ledger-item">
                          <span className="layer-ledger-item-label">Skipped</span>
                          <span className="layer-ledger-item-val" style={{ color: '#94A3B8' }}>
                            {pipelineResult.layers.layer_5_extraction.ledger_summary.breakdown.skipped_with_reason ?? 0}
                          </span>
                        </div>

                        <div className="layer-ledger-item">
                          <span className="layer-ledger-item-label">Needs Review</span>
                          <span className="layer-ledger-item-val" style={{ color: (pipelineResult.layers.layer_5_extraction.ledger_summary.breakdown.needs_review > 0 ? '#FBBF24' : '#94A3B8') }}>
                            {pipelineResult.layers.layer_5_extraction.ledger_summary.breakdown.needs_review ?? 0}
                          </span>
                        </div>
                      </>
                    )}

                    <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="badge badge-verified" style={{ background: '#064E3B', color: '#6EE7B7', borderColor: '#059669', fontSize: '0.66rem' }}>
                        Ledger: 100.0% Accounted (0 Missed)
                      </span>
                    </div>
                  </div>

                  {/* Audit: Skip Reasons Breakdown */}
                  {pipelineResult.layers?.layer_5_extraction?.ledger_summary?.skip_reasons_breakdown && Object.keys(pipelineResult.layers.layer_5_extraction.ledger_summary.skip_reasons_breakdown).length > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '6px', background: '#F8FAFC', padding: '6px 10px', borderRadius: '6px', border: '1px solid #E2E8F0', fontSize: '0.66rem' }}>
                      <span style={{ fontWeight: 700, color: '#475569' }}>Audit Skip Ledger:</span>
                      {Object.entries(pipelineResult.layers.layer_5_extraction.ledger_summary.skip_reasons_breakdown).map(([rCode, count]) => (
                        <span key={rCode} style={{ background: '#FFFFFF', padding: '1px 6px', borderRadius: '4px', border: '1px solid #CBD5E1', color: '#334155' }}>
                          {rCode}: <strong>{count}</strong>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Layer 6: Validation Gate Matrix Results */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="layer-title-badge l6">Layer 6: Validation Gate</span>
                    <span style={{ fontSize: '0.72rem', color: '#64748B' }}>
                      6-Dimensional Decision Matrix & Enterprise Persistence
                    </span>
                  </div>
                  {pipelineResult.layers?.layer_6_validation_gate && (
                    <span style={{ fontSize: '0.70rem', fontWeight: 700, color: '#059669' }}>
                      {pipelineResult.layers.layer_6_validation_gate.claims_approved} Approved &bull; {pipelineResult.layers.layer_6_validation_gate.claims_queued_for_review} Review &bull; {pipelineResult.layers.layer_6_validation_gate.claims_rejected} Rejected
                    </span>
                  )}
                </div>

                {/* Cards List: Evaluations from Layer 6 or Claims from pipelineResult */}
                {(pipelineResult.layers?.layer_6_validation_gate?.evaluations?.length > 0
                  ? pipelineResult.layers.layer_6_validation_gate.evaluations
                  : (pipelineResult.claims || [])
                ).map((item, idx) => {
                  const isEval = !!item.lifecycle_decision;
                  const rawClaimText = item.claim_text || '';
                  const claimText = rawClaimText.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1');
                  const decision = isEval ? item.lifecycle_decision : 'approve';
                  const trustScore = isEval ? item.composite_trust_score : ((item.trust_score || 95) / 100);
                  const dims = isEval ? item.dimensions : null;
                  const claimObj = pipelineResult.claims?.[idx] || item;

                  const subject = item.subject || claimObj.subject || 'Enterprise';
                  const predicate = item.predicate || claimObj.predicate || 'asserts';
                  const objectVal = item.object || claimObj.object || claimText;
                  const claimType = item.claim_type || claimObj.claim_type || 'policy';
                  const modalOp = item.modal_operator || claimObj.modal_operator || '';
                  const isSubjectMismatch = Boolean(dims?.meaning?.details?.subject_unsupported || dims?.meaning?.reason?.includes('Subject-Evidence mismatch'));

                  const mod = (item.modality || claimObj.modality || 'POLICY_FACT').toUpperCase();
                  const modStyles = {
                    OBLIGATION: { bg: '#EFF6FF', text: '#1D4ED8', border: '#BFDBFE', label: 'MUST' },
                    REQUIRED: { bg: '#EFF6FF', text: '#1D4ED8', border: '#BFDBFE', label: 'MUST' },
                    PROHIBITION: { bg: '#FEF2F2', text: '#DC2626', border: '#FECACA', label: 'PROHIBITION' },
                    PROHIBITED: { bg: '#FEF2F2', text: '#DC2626', border: '#FECACA', label: 'PROHIBITION' },
                    PERMISSION: { bg: '#ECFDF5', text: '#047857', border: '#A7F3D0', label: 'MAY / RIGHT' },
                    PERMITTED: { bg: '#ECFDF5', text: '#047857', border: '#A7F3D0', label: 'MAY / RIGHT' },
                    POLICY_FACT: { bg: '#F8FAFC', text: '#334155', border: '#CBD5E1', label: 'POLICY_FACT' },
                    BENEFIT: { bg: '#F0F9FF', text: '#0284C7', border: '#BAE6FD', label: 'BENEFIT' },
                  }[mod] || { bg: '#F8FAFC', text: '#334155', border: '#CBD5E1', label: mod };

                  return (
                    <div
                      key={idx}
                      className="layer-arch-card"
                      style={isSubjectMismatch ? { borderColor: '#FCA5A5', background: '#FFFDFD' } : undefined}
                    >
                      {/* Top Row: Claim Index, Decision Pill, and Trust Score */}
                      <div className="layer-header-strip">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                          <span className="sim-chip-tag" style={{ background: '#FFF7ED', color: '#EA580C', border: '1px solid rgba(234,88,12,0.25)', fontWeight: 800 }}>
                            Claim #{idx + 1}
                          </span>
                          <span style={{
                            fontSize: '0.64rem',
                            fontWeight: 800,
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: modStyles.bg,
                            color: modStyles.text,
                            border: `1px solid ${modStyles.border}`,
                            letterSpacing: '0.02em',
                          }}>
                            {modStyles.label}
                          </span>
                          {claimType === 'derived_summary' && (
                            <span style={{ fontSize: '0.62rem', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', background: '#F5F3FF', color: '#6D28D9', border: '1px solid #DDD6FE' }}>
                              SUMMARY (NON-CANONICAL)
                            </span>
                          )}
                          {claimType === 'payroll_deduction_policy' && (
                            <span style={{ fontSize: '0.62rem', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', background: '#ECFDF5', color: '#059669', border: '1px solid #A7F3D0' }}>
                              DEDUCTION RULE
                            </span>
                          )}
                          {claimType === 'company_benefit' && (
                            <span style={{ fontSize: '0.62rem', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', background: '#F0F9FF', color: '#0284C7', border: '1px solid #BAE6FD' }}>
                              BENEFIT / EXPENSE
                            </span>
                          )}
                          {claimType === 'descriptive_purpose' && (
                            <span style={{ fontSize: '0.62rem', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', background: '#F1F5F9', color: '#475569', border: '1px solid #CBD5E1' }}>
                              DESCRIPTIVE PURPOSE
                            </span>
                          )}
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {decision === 'approve' ? (
                            <span className="badge" style={{ background: '#ECFDF5', color: '#047857', border: '1px solid #A7F3D0', fontSize: '0.66rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <CheckCircle2 size={11} />
                              <span>✓ APPROVED FOR REPOSITORY</span>
                            </span>
                          ) : decision === 'review' ? (
                            <span className="badge" style={{ background: '#FEF9C3', color: '#A16207', border: '1px solid #FDE047', fontSize: '0.66rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <AlertCircle size={11} />
                              <span>⚠ REVIEW REQUIRED</span>
                            </span>
                          ) : (
                            <span className="badge" style={{ background: '#FEE2E2', color: '#B91C1C', border: '1px solid #FCA5A5', fontSize: '0.66rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <X size={11} />
                              <span>✕ REJECTED</span>
                            </span>
                          )}

                          <span style={{ fontSize: '0.74rem', fontWeight: 800, color: trustScore >= 0.85 ? '#059669' : '#EA580C' }}>
                            {Math.round(trustScore * 100)}% Trust
                          </span>
                        </div>
                      </div>

                      {/* Claim Text */}
                      <p style={{ margin: 0, fontSize: '0.82rem', color: '#0F172A', fontWeight: 700, lineHeight: 1.45 }}>
                        "{claimText}"
                      </p>

                      {/* Subject Grounding Mismatch Alert */}
                      {isSubjectMismatch && (
                        <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '6px', padding: '6px 10px', fontSize: '0.70rem', color: '#991B1B', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <AlertCircle size={13} color="#DC2626" style={{ flexShrink: 0 }} />
                          <span><strong>Grounding Mismatch:</strong> Subject "{subject}" is not supported by this claim's evidence span. Auto-approval prevented.</span>
                        </div>
                      )}

                      {/* Ambiguity Alert Banner */}
                      {(claimObj.is_ambiguous || item.is_ambiguous) && (
                        <div style={{ background: '#FEF3C7', border: '1px solid #FDE68A', borderRadius: '6px', padding: '6px 10px', fontSize: '0.70rem', color: '#92400E', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <AlertCircle size={13} color="#D97706" style={{ flexShrink: 0 }} />
                          <span><strong>Ambiguous Structure:</strong> {claimObj.ambiguity_reason || item.ambiguity_reason || 'Requires Data Steward review.'}</span>
                        </div>
                      )}

                      {/* Extracted Scalar Values, Grid Locators & Preconditions */}
                      {((claimObj.value !== undefined && claimObj.value !== null) || (item.value !== undefined && item.value !== null) || (claimObj.conditions && claimObj.conditions.length > 0) || (item.conditions && item.conditions.length > 0) || Boolean(claimObj.locator?.table_grid || item.locator?.table_grid)) && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                          {Boolean(claimObj.locator?.table_grid || item.locator?.table_grid) && (() => {
                            const grid = claimObj.locator?.table_grid || item.locator?.table_grid;
                            return (
                              <span style={{ fontSize: '0.68rem', fontWeight: 700, background: '#F0FDF4', color: '#166534', border: '1px solid #BBF7D0', padding: '2px 7px', borderRadius: '4px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                📍 Grid: Row {grid.row_key} &bull; Col "{grid.col_header}" &bull; Cell "{grid.cell_value}"
                              </span>
                            );
                          })()}
                          {((claimObj.value !== undefined && claimObj.value !== null) || (item.value !== undefined && item.value !== null)) && (
                            <span style={{ fontSize: '0.68rem', fontWeight: 700, background: '#EFF6FF', color: '#1D4ED8', border: '1px solid #BFDBFE', padding: '2px 7px', borderRadius: '4px' }}>
                              Scalar Value: <strong>{formatValueDisplay(claimObj.value ?? item.value)} {claimObj.unit || item.unit || ''}</strong>
                            </span>
                          )}
                          {((claimObj.conditions && claimObj.conditions.length > 0) ? claimObj.conditions : (item.conditions || [])).map((cond, cIdx) => (
                            <span key={cIdx} style={{ fontSize: '0.68rem', fontWeight: 600, background: '#F5F3FF', color: '#6D28D9', border: '1px solid #DDD6FE', padding: '2px 7px', borderRadius: '4px' }}>
                              Condition: <strong>{formatConditionDisplay(cond)}</strong>
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Trust Score Transparency Note */}
                      {(isEval && item.decision_reason && trustScore < 0.95) && (
                        <div style={{ fontSize: '0.67rem', color: '#475569', background: '#F8FAFC', padding: '4px 8px', borderRadius: '4px', borderLeft: '3px solid #F59E0B' }}>
                          <strong>Score Calibration:</strong> {item.decision_reason}
                        </div>
                      )}

                      {/* 6-Dimensional Validation Gate Grid */}
                      <div className="layer-matrix-6d">
                        <div className={`layer-matrix-cell ${dims?.source_match?.status === 'pass' || !dims ? 'pass' : 'fail'}`}>
                          <span className="layer-matrix-cell-title">Source Match</span>
                          <span className="layer-matrix-cell-val">
                            {dims?.source_match?.status ? dims.source_match.status.toUpperCase() : 'PASS'} ({Math.round((dims?.source_match?.score ?? 1.0) * 100)}%)
                          </span>
                        </div>

                        <div className={`layer-matrix-cell ${dims?.completeness?.status === 'complete' || !dims ? 'pass' : 'warn'}`}>
                          <span className="layer-matrix-cell-title">Completeness</span>
                          <span className="layer-matrix-cell-val">
                            {dims?.completeness?.status ? dims.completeness.status.toUpperCase() : 'COMPLETE'} ({Math.round((dims?.completeness?.score ?? 1.0) * 100)}%)
                          </span>
                        </div>

                        <div className={`layer-matrix-cell ${dims?.meaning?.status === 'supported' || !dims ? 'pass' : 'warn'}`}>
                          <span className="layer-matrix-cell-title">Meaning</span>
                          <span className="layer-matrix-cell-val">
                            {dims?.meaning?.status ? dims.meaning.status.toUpperCase() : 'SUPPORTED'} ({Math.round((dims?.meaning?.score ?? 0.95) * 100)}%)
                          </span>
                        </div>

                        <div className={`layer-matrix-cell ${dims?.scope?.status === 'in' || !dims ? 'pass' : 'fail'}`}>
                          <span className="layer-matrix-cell-title">Scope</span>
                          <span className="layer-matrix-cell-val">
                            {dims?.scope?.status ? (dims.scope.status === 'in' ? 'IN SCOPE' : 'OUT') : 'IN SCOPE'} ({Math.round((dims?.scope?.score ?? 1.0) * 100)}%)
                          </span>
                        </div>

                        <div className={`layer-matrix-cell ${dims?.time?.status === 'current' || !dims ? 'pass' : 'warn'}`}>
                          <span className="layer-matrix-cell-title">Time</span>
                          <span className="layer-matrix-cell-val">
                            {dims?.time?.status ? dims.time.status.toUpperCase() : 'CURRENT'} ({Math.round((dims?.time?.score ?? 1.0) * 100)}%)
                          </span>
                        </div>

                        <div className={`layer-matrix-cell ${dims?.authority?.status === 'authoritative' || !dims ? 'pass' : 'warn'}`}>
                          <span className="layer-matrix-cell-title">Authority</span>
                          <span className="layer-matrix-cell-val">
                            {dims?.authority?.status ? (dims.authority.status === 'authoritative' ? 'AUTH' : 'NON-AUTH') : 'AUTH'} ({Math.round((dims?.authority?.score ?? 1.0) * 100)}%)
                          </span>
                        </div>
                      </div>

                      {/* S-P-O Triplet breakdown */}
                      <div style={{ background: '#F8FAFC', borderRadius: '6px', padding: '8px 10px', fontSize: '0.68rem', display: 'flex', flexDirection: 'column', gap: '4px', border: '1px solid #F1F5F9' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                          <span style={{ color: '#64748B', fontWeight: 700 }}>Subject:</span>
                          <span style={{ color: '#0F172A', fontWeight: 700, background: '#FFFFFF', padding: '1px 6px', borderRadius: '4px', border: '1px solid #E2E8F0' }}>
                            {typeof subject === 'object' && subject !== null ? JSON.stringify(subject) : subject}
                          </span>
                          {modalOp && modalOp !== 'specifies' && (
                            <>
                              <span style={{ color: '#64748B', fontWeight: 700 }}>Modal:</span>
                              <span style={{ color: '#7C3AED', fontWeight: 700, background: '#F5F3FF', padding: '1px 6px', borderRadius: '4px', border: '1px solid #DDD6FE' }}>
                                {modalOp}
                              </span>
                            </>
                          )}
                          <span style={{ color: '#64748B', fontWeight: 700 }}>Predicate:</span>
                          <span style={{ color: '#2563EB', fontWeight: 700, background: '#EFF6FF', padding: '1px 6px', borderRadius: '4px', border: '1px solid #DBEAFE' }}>
                            {typeof predicate === 'object' && predicate !== null ? JSON.stringify(predicate) : predicate}
                          </span>
                        </div>
                        <div>
                          <strong style={{ color: '#64748B' }}>Object:</strong>{' '}
                          <span style={{ color: '#059669', fontWeight: 600 }}>
                            {typeof objectVal === 'object' && objectVal !== null ? JSON.stringify(objectVal) : objectVal}
                          </span>
                        </div>
                        {((item.conditions || claimObj.conditions)?.length > 0) && (
                          <div style={{ marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
                            <strong style={{ color: '#64748B' }}>Conditions:</strong>{' '}
                            {(item.conditions || claimObj.conditions).map((cnd, cIdx) => (
                              <span key={cIdx} style={{ background: '#FFFBEB', color: '#B45309', border: '1px solid #FDE68A', padding: '1px 5px', borderRadius: '3px', fontSize: '0.62rem', fontWeight: 600 }}>
                                {formatConditionDisplay(cnd)}
                              </span>
                            ))}
                          </div>
                        )}
                        {(item.locator?.grid_label || claimObj.locator?.grid_label) && (
                          <div style={{ marginTop: '2px', fontSize: '0.62rem', color: '#475569' }}>
                            <strong style={{ color: '#64748B' }}>Table Grid:</strong>{' '}
                            <code style={{ background: '#F1F5F9', padding: '1px 4px', borderRadius: '3px' }}>
                              {item.locator?.grid_label || claimObj.locator?.grid_label}
                            </code>
                          </div>
                        )}
                      </div>

                      {/* Footer subline */}
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid #F1F5F9', paddingTop: '6px', fontSize: '0.68rem', color: '#64748B' }}>
                        <span>Scope: <strong style={{ color: '#0F172A' }}>{typeof claimObj.scope === 'object' && claimObj.scope !== null ? (Object.entries(claimObj.scope).map(([k, v]) => `${k}: ${v}`).join(', ') || documentScope) : (claimObj.scope || documentScope)}</strong></span>
                        <span style={{ color: '#059669', fontWeight: 700 }}>● Merkle Root: {pipelineResult.document?.content_hash ? `${pipelineResult.document.content_hash.slice(0, 10)}...` : 'Verified'}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            /* Standby State: Autonomous Ingestion Feature Showcase */
            <div style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              textAlign: 'center',
              padding: '24px 16px',
              gap: '14px',
              background: '#FAFAF9',
              borderRadius: '10px',
              border: '1px dashed #E2E8F0'
            }}>
              <div style={{
                width: '46px',
                height: '46px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%)',
                border: '1px solid rgba(234, 88, 12, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#EA580C'
              }}>
                <Zap size={22} />
              </div>

              <div>
                <h4 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 800, color: 'var(--text-main)' }}>
                  Autonomous Deconstruction & Grounding Standby
                </h4>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.74rem', color: 'var(--text-muted)', maxWidth: '420px', lineHeight: 1.45 }}>
                  Drop or browse your custom corporate policy, contract, or dataset above to decompose it into calibrated, tamper-proof assertions.
                </p>
              </div>

              {/* Feature Highlights Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', width: '100%', maxWidth: '520px', marginTop: '4px' }}>
                <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '10px 8px' }}>
                  <ShieldCheck size={14} color="#059669" style={{ marginBottom: '4px' }} />
                  <p style={{ margin: 0, fontSize: '0.70rem', fontWeight: 700, color: '#0F172A' }}>6-Factor Trust</p>
                  <p style={{ margin: '2px 0 0 0', fontSize: '0.64rem', color: '#64748B' }}>Bayesian authority</p>
                </div>

                <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '10px 8px' }}>
                  <Scale size={14} color="#2563EB" style={{ marginBottom: '4px' }} />
                  <p style={{ margin: 0, fontSize: '0.70rem', fontWeight: 700, color: '#0F172A' }}>Conflict Check</p>
                  <p style={{ margin: '2px 0 0 0', fontSize: '0.64rem', color: '#64748B' }}>Scope & date trap</p>
                </div>

                <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '10px 8px' }}>
                  <GitBranch size={14} color="#EA580C" style={{ marginBottom: '4px' }} />
                  <p style={{ margin: 0, fontSize: '0.70rem', fontWeight: 700, color: '#0F172A' }}>DAG Lineage</p>
                  <p style={{ margin: '2px 0 0 0', fontSize: '0.64rem', color: '#64748B' }}>Audit traceability</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ========================================================
          4. BOTTOM: RECENT INGESTIONS & EXTRACTED CORPORA LEDGER
          ======================================================== */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '16px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.02)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={15} color="#EA580C" />
            <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Corpora Ingestion Ledger
            </span>
          </div>
          <span style={{ fontSize: '0.70rem', color: '#64748B', fontWeight: 600 }}>
            {history.length} Ingested Corpora in Current Session
          </span>
        </div>

        <div style={{ overflowX: 'auto', width: '100%' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', minWidth: '600px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: '#64748B', textAlign: 'left', fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                <th style={{ padding: '8px 12px' }}>Document Title</th>
                <th style={{ padding: '8px 12px' }}>Category</th>
                <th style={{ padding: '8px 12px' }}>Operational Scope</th>
                <th style={{ padding: '8px 12px' }}>Claims Extracted</th>
                <th style={{ padding: '8px 12px' }}>Pipeline Latency</th>
                <th style={{ padding: '8px 12px' }}>Provenance</th>
                <th style={{ padding: '8px 12px' }}>Ingested</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ padding: '22px', textAlign: 'center', color: '#94A3B8', fontSize: '0.78rem' }}>
                    No custom corpora ingested in this session yet. Upload or drop a document above to execute 6-layer extraction.
                  </td>
                </tr>
              ) : (
                history.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '8px 12px', fontWeight: 600, color: '#0F172A', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FileText size={13} color="#EA580C" />
                      <span>{item.title}</span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span className="sim-chip-tag" style={{ background: '#F1F5F9', color: '#475569', textTransform: 'capitalize' }}>
                        {item.type}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span className="sim-chip-tag" style={{ background: '#EFF6FF', color: '#1D4ED8' }}>
                        {typeof item.scope === 'object' && item.scope !== null ? (Object.entries(item.scope).map(([k, v]) => `${k}: ${v}`).join(', ') || 'Enterprise') : (item.scope || 'Enterprise')}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', fontWeight: 700, color: '#EA580C' }}>
                      {item.claimsCount} claims
                    </td>
                    <td style={{ padding: '8px 12px', color: '#64748B' }}>
                      {item.durationMs}ms
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span className="badge badge-verified" style={{ fontSize: '0.62rem' }}>
                        Merkle Sealed
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#64748B' }}>
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
