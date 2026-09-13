import React, { useState, useEffect } from 'react';

export default function McpIntegrationStudio({
  activeOrg,
  showToast,
  initialSubView = 'tester',
  onSubViewChange
}) {
  const [activeSubView, setActiveSubView] = useState(initialSubView); // 'tester' | 'configs' | 'sdks' | 'schemas'
  const [selectedTool, setSelectedTool] = useState('context_trust_get_trusted_context');
  const [toolQuery, setToolQuery] = useState('What is the maximum allowed automated refund policy?');
  const [minTrustScore, setMinTrustScore] = useState(0.75);
  const [maxResults, setMaxResults] = useState(5);
  const [actionType, setActionType] = useState('Process automated refund claim');
  const [actorId, setActorId] = useState('billing-agent-01');
  const [actorRole, setActorRole] = useState('support');
  const [searchText, setSearchText] = useState('refund');
  const [claimText, setClaimText] = useState('Refund window is strictly limited to 30 days.');
  const [invoking, setInvoking] = useState(false);
  const [invocationResult, setInvocationResult] = useState(null);
  const [activeSnippet, setActiveSnippet] = useState('claude'); // 'claude' | 'cursor' | 'ollama' | 'python' | 'langchain' | 'llamaindex' | 'curl'
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  useEffect(() => {
    if (initialSubView) {
      setActiveSubView(initialSubView);
    }
  }, [initialSubView]);

  const handleSelectSubView = (subView) => {
    setActiveSubView(subView);
    if (onSubViewChange) onSubViewChange(subView);
  };

  const tools = [
    {
      id: 'context_trust_get_trusted_context',
      name: 'get_trusted_context',
      icon: '🛡️',
      description: 'Retrieves evidence-backed, verified context before an AI agent makes a decision.',
      category: 'RAG Retrieval',
      params: 'query, min_trust_score, max_results'
    },
    {
      id: 'context_trust_evaluate_decision',
      name: 'evaluate_decision',
      icon: '⚖️',
      description: 'Evaluates agent actions against authority hierarchy and active policy contradictions.',
      category: 'Decision Gate',
      params: 'action_type, actor_id, actor_role'
    },
    {
      id: 'context_trust_search_claims',
      name: 'search_claims',
      icon: '⚡',
      description: 'Queries atomic claims database with predicate matching and trust bounds.',
      category: 'Knowledge Graph',
      params: 'search_text, status, limit'
    },
    {
      id: 'context_trust_check_conflicts',
      name: 'check_conflicts',
      icon: '🚨',
      description: 'Detects if a statement contradicts existing enterprise policies.',
      category: 'Conflict Analysis',
      params: 'claim_text'
    },
    {
      id: 'context_trust_get_lineage',
      name: 'get_lineage',
      icon: '🕸️',
      description: 'Fetches end-to-end DAG lineage and downstream blast radius.',
      category: 'Lineage & Provenance',
      params: 'organization_id'
    },
    {
      id: 'context_trust_steward_audit',
      name: 'steward_audit',
      icon: '🤖',
      description: 'Runs autonomous heuristic audit scan for stale policies and contradictions.',
      category: 'Context Curator',
      params: 'organization_id'
    }
  ];

  const handleExecuteMcp = async () => {
    setInvoking(true);
    setInvocationResult(null);

    const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
    let args = { organization_id: orgId };

    if (selectedTool === 'context_trust_get_trusted_context') {
      args = {
        ...args,
        query: toolQuery,
        agent_id: '88888888-8888-8888-8888-888888888888',
        min_trust_score: Number(minTrustScore),
        max_results: Number(maxResults)
      };
    } else if (selectedTool === 'context_trust_evaluate_decision') {
      args = {
        ...args,
        action_type: actionType,
        actor_id: actorId,
        actor_role: actorRole,
        required_scope: 'Enterprise'
      };
    } else if (selectedTool === 'context_trust_search_claims') {
      args = {
        ...args,
        search_text: searchText,
        status: 'all',
        limit: 5
      };
    } else if (selectedTool === 'context_trust_check_conflicts') {
      args = {
        ...args,
        claim_text: claimText
      };
    }

    try {
      const res = await fetch('/v1/mcp/invoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: selectedTool,
          arguments: args
        })
      });

      if (res.ok) {
        const data = await res.json();
        setInvocationResult(data);
        showToast?.(`MCP tool '${selectedTool}' executed successfully!`);
      } else {
        const err = await res.text();
        showToast?.(`MCP execution failed: ${res.status}`, "error");
      }
    } catch (e) {
      showToast?.(`MCP error: ${e.message}`, "error");
    } finally {
      setInvoking(false);
    }
  };

  const getClientConfigCode = () => {
    const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
    if (activeSnippet === 'claude') {
      return JSON.stringify({
        mcpServers: {
          "context-trust-layer": {
            command: "python",
            args: ["-m", "app.mcp.client_stdio"],
            env: {
              CONTEXT_LAYER_API_URL: "http://127.0.0.1:8000/v1/mcp",
              CONTEXT_LAYER_ORG_ID: orgId
            }
          }
        }
      }, null, 2);
    } else if (activeSnippet === 'cursor') {
      return JSON.stringify({
        mcpServers: {
          "context-trust-layer": {
            url: "http://127.0.0.1:8000/v1/mcp",
            headers: {
              "X-Organization-Id": orgId
            }
          }
        }
      }, null, 2);
    } else if (activeSnippet === 'ollama') {
      return `# Ollama / Local LLM Integration via Context Trust Gateway
from ollama import Client
import requests

ollama_client = Client(host="http://localhost:11434")

def query_with_trusted_context(prompt: str):
    # 1. Fetch grounded enterprise facts from Context Trust Layer
    res = requests.post("http://127.0.0.1:8000/v1/mcp/invoke", json={
        "tool": "context_trust_get_trusted_context",
        "arguments": {"query": prompt, "organization_id": "${orgId}", "min_trust_score": 0.80}
    })
    trusted_facts = res.json().get("result", {})
    
    # 2. Supply verified knowledge to local model
    system_prompt = f"Authoritative Enterprise Knowledge: {trusted_facts}"
    response = ollama_client.chat(model="qwen3:1.7b", messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ])
    return response['message']['content']`;
    } else if (activeSnippet === 'python') {
      return `# Python Context Trust SDK / MCP Client
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000/v1")

# Query Grounded Context before Agent Tool Execution
response = client.post("/mcp/invoke", json={
    "tool": "context_trust_get_trusted_context",
    "arguments": {
        "query": "Is customer eligible for policy refund?",
        "organization_id": "${orgId}",
        "min_trust_score": 0.80
    }
})

trusted_context = response.json()
print("Verified Knowledge:", trusted_context)`;
    } else if (activeSnippet === 'langchain') {
      return `# LangChain Tool Definition
from langchain.tools import tool
import requests

@tool
def get_enterprise_context(query: str) -> str:
    """Queries verified enterprise policies from Context Trust Layer."""
    res = requests.post("http://127.0.0.1:8000/v1/mcp/invoke", json={
        "tool": "context_trust_get_trusted_context",
        "arguments": {"query": query, "organization_id": "${orgId}"}
    })
    return str(res.json().get("result"))`;
    } else if (activeSnippet === 'llamaindex') {
      return `# LlamaIndex Function Tool Definition
from llama_index.core.tools import FunctionTool
import requests

def fetch_trusted_knowledge(query: str) -> str:
    """Retrieves high-trust verified atomic claims."""
    resp = requests.post("http://127.0.0.1:8000/v1/mcp/invoke", json={
        "tool": "context_trust_get_trusted_context",
        "arguments": {"query": query, "organization_id": "${orgId}"}
    })
    return str(resp.json())

context_tool = FunctionTool.from_defaults(fn=fetch_trusted_knowledge)`;
    }
    return `curl -X POST http://127.0.0.1:8000/v1/mcp \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "context_trust_get_trusted_context", "arguments": {"query": "refund policy", "organization_id": "${orgId}"}}, "id": 1}'`;
  };

  const handleCopySnippet = () => {
    navigator.clipboard.writeText(getClientConfigCode());
    setCopiedSnippet(true);
    showToast?.("Configuration snippet copied to clipboard!");
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

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
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #7c3aed 0%, #2026d2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '22px',
            color: '#fff',
            boxShadow: '0 4px 12px rgba(124,58,237,0.25)'
          }}>
            🔌
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
                Agent Integrations & Model Context Protocol (MCP) Hub
              </h2>
              <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                JSON-RPC 2.0 Spec
              </span>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Standard MCP gateway connecting external AI agents (Claude, Cursor, LangChain, Ollama) directly to the Context Trust Layer.
            </p>
          </div>
        </div>

        {/* Top Environment Sub-Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', background: 'var(--bg-card)', padding: '3px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <button
              onClick={() => handleSelectSubView('tester')}
              style={{
                padding: '7px 14px',
                borderRadius: '6px',
                border: 'none',
                background: activeSubView === 'tester' ? '#2026d2' : 'transparent',
                color: activeSubView === 'tester' ? '#fff' : 'var(--text-main)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>🧪 Interactive Tool Tester</span>
            </button>
            <button
              onClick={() => handleSelectSubView('configs')}
              style={{
                padding: '7px 14px',
                borderRadius: '6px',
                border: 'none',
                background: activeSubView === 'configs' ? '#2026d2' : 'transparent',
                color: activeSubView === 'configs' ? '#fff' : 'var(--text-main)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>⚙️ Claude & Cursor Configs</span>
            </button>
            <button
              onClick={() => handleSelectSubView('sdks')}
              style={{
                padding: '7px 14px',
                borderRadius: '6px',
                border: 'none',
                background: activeSubView === 'sdks' ? '#2026d2' : 'transparent',
                color: activeSubView === 'sdks' ? '#fff' : 'var(--text-main)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>💻 Python SDK & Frameworks</span>
            </button>
            <button
              onClick={() => handleSelectSubView('schemas')}
              style={{
                padding: '7px 14px',
                borderRadius: '6px',
                border: 'none',
                background: activeSubView === 'schemas' ? '#2026d2' : 'transparent',
                color: activeSubView === 'schemas' ? '#fff' : 'var(--text-main)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>📋 Tool Schemas</span>
            </button>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* SUB-VIEW 1: INTERACTIVE TOOL TESTER                       */}
      {/* ========================================================= */}
      {activeSubView === 'tester' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(420px, 1.2fr) minmax(400px, 1fr)', gap: '24px' }}>
          {/* Left Column: Tool Selector & Param Inputs */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px'
          }}>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
              1. Select & Configure MCP Tool
            </h3>

            {/* Tools Radio Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {tools.map((t) => {
                const isSelected = selectedTool === t.id;
                return (
                  <div
                    key={t.id}
                    onClick={() => setSelectedTool(t.id)}
                    style={{
                      padding: '12px 14px',
                      borderRadius: '10px',
                      border: `1px solid ${isSelected ? '#2026d2' : 'var(--border-color)'}`,
                      background: isSelected ? 'rgba(32,38,210,0.06)' : 'var(--bg-card)',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                      boxShadow: isSelected ? '0 0 0 2px rgba(32,38,210,0.15)' : 'none',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.82rem', color: isSelected ? '#2026d2' : 'var(--text-main)' }}>
                        {t.icon} {t.name}
                      </span>
                      <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>{t.category}</span>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: 1.3 }}>
                      {t.description}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Dynamic Tool Parameters */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', background: 'var(--bg-card)', padding: '16px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Tool Input Parameters ({activeOrg?.name || 'demo'}):
              </span>

              {selectedTool === 'context_trust_get_trusted_context' && (
                <>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Natural Language Query</label>
                    <input
                      type="text"
                      value={toolQuery}
                      onChange={(e) => setToolQuery(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.82rem' }}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Min Trust Score ({minTrustScore})</label>
                      <input
                        type="range"
                        min="0.5"
                        max="1.0"
                        step="0.05"
                        value={minTrustScore}
                        onChange={(e) => setMinTrustScore(Number(e.target.value))}
                        style={{ width: '100%', accentColor: '#2026d2' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Max Results</label>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={maxResults}
                        onChange={(e) => setMaxResults(Number(e.target.value))}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.82rem' }}
                      />
                    </div>
                  </div>
                </>
              )}

              {selectedTool === 'context_trust_evaluate_decision' && (
                <>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Proposed Action / Decision Statement</label>
                    <input
                      type="text"
                      value={actionType}
                      onChange={(e) => setActionType(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.82rem' }}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Actor ID</label>
                      <input
                        type="text"
                        value={actorId}
                        onChange={(e) => setActorId(e.target.value)}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.82rem' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Actor Role</label>
                      <input
                        type="text"
                        value={actorRole}
                        onChange={(e) => setActorRole(e.target.value)}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.82rem' }}
                      />
                    </div>
                  </div>
                </>
              )}

              {selectedTool === 'context_trust_search_claims' && (
                <div>
                  <label style={{ display: 'block', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Search Keywords / Predicate</label>
                  <input
                    type="text"
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.82rem' }}
                  />
                </div>
              )}

              {selectedTool === 'context_trust_check_conflicts' && (
                <div>
                  <label style={{ display: 'block', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Claim Statement to Check</label>
                  <input
                    type="text"
                    value={claimText}
                    onChange={(e) => setClaimText(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.82rem' }}
                  />
                </div>
              )}

              {selectedTool === 'context_trust_get_lineage' && (
                <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Fetches full DAG graph nodes and blast-radius mappings for organization <strong>{activeOrg?.name || 'demo'}</strong>.
                </p>
              )}

              {selectedTool === 'context_trust_steward_audit' && (
                <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Executes autonomous heuristic scan over all active claims and generates context scorecard.
                </p>
              )}
            </div>

            {/* Invoke Button */}
            <button
              onClick={handleExecuteMcp}
              disabled={invoking}
              style={{
                padding: '12px 24px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #2026d2 0%, #3737d8 100%)',
                color: '#fff',
                border: 'none',
                fontWeight: 600,
                fontSize: '0.92rem',
                cursor: invoking ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                boxShadow: '0 4px 14px rgba(32,38,210,0.25)'
              }}
            >
              {invoking ? <span className="spinner-sm"></span> : <span>⚡</span>}
              <span>{invoking ? 'Executing JSON-RPC Call...' : `Invoke ${selectedTool}`}</span>
            </button>
          </div>

          {/* Right Column: Live Output */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* JSON-RPC Output Console */}
            <div style={{
              background: '#0d1117',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '16px',
              padding: '20px',
              color: '#c9d1d9',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              minHeight: '420px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '10px' }}>
                <span style={{ fontSize: '0.78rem', color: '#58a6ff', fontWeight: 600 }}>
                  JSON-RPC 2.0 Response Payload
                </span>
                <span className="badge badge-verified" style={{ fontSize: '0.62rem' }}>
                  Status: 200 OK
                </span>
              </div>

              <pre style={{
                margin: 0,
                fontSize: '0.75rem',
                fontFamily: 'SFMono-Regular, Menlo, Monaco, monospace',
                overflowY: 'auto',
                maxHeight: '380px',
                lineHeight: 1.45,
                color: '#7ee787'
              }}>
                {invocationResult ? JSON.stringify(invocationResult, null, 2) : `// Click "Invoke" on the left to execute the MCP tool and inspect live JSON response.\n{\n  "jsonrpc": "2.0",\n  "status": "ready",\n  "server": "context-trust-layer",\n  "organization": "${activeOrg?.name || 'demo'}",\n  "tools_available": 6\n}`}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-VIEW 2: CLAUDE & CURSOR CONFIGURATIONS                */}
      {/* ========================================================= */}
      {activeSubView === 'configs' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(350px, 1fr) minmax(400px, 1.3fr)', gap: '24px' }}>
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
              Select AI Agent Client
            </h3>
            <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Choose your AI IDE or Assistant to get ready-to-copy JSON configuration files with your active organization pre-filled.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {[
                { id: 'claude', name: 'Claude Desktop (Anthropic)', desc: 'claude_desktop_config.json' },
                { id: 'cursor', name: 'Cursor IDE', desc: '.cursor/mcp.json' },
                { id: 'ollama', name: 'Ollama (Local LLM)', desc: 'Python Context Bridge' }
              ].map(c => (
                <div
                  key={c.id}
                  onClick={() => setActiveSnippet(c.id)}
                  style={{
                    padding: '12px 14px',
                    borderRadius: '10px',
                    border: `1px solid ${activeSnippet === c.id ? '#2026d2' : 'var(--border-color)'}`,
                    background: activeSnippet === c.id ? 'rgba(32,38,210,0.06)' : 'var(--bg-card)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px'
                  }}
                >
                  <span style={{ fontWeight: 600, fontSize: '0.85rem', color: activeSnippet === c.id ? '#2026d2' : 'var(--text-main)' }}>
                    {c.name}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{c.desc}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: '#0d1117', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '24px', color: '#c9d1d9', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '12px' }}>
              <span style={{ fontSize: '0.82rem', color: '#58a6ff', fontWeight: 600 }}>
                Configuration File Content
              </span>
              <button
                onClick={handleCopySnippet}
                style={{
                  padding: '5px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(255,255,255,0.2)',
                  background: 'rgba(255,255,255,0.08)',
                  color: '#fff',
                  fontSize: '0.74rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {copiedSnippet ? '✓ Copied' : '📋 Copy Configuration'}
              </button>
            </div>

            <pre style={{
              margin: 0,
              fontSize: '0.78rem',
              fontFamily: 'SFMono-Regular, Menlo, Monaco, monospace',
              overflowX: 'auto',
              color: '#f0f6fc',
              lineHeight: 1.5
            }}>
              {getClientConfigCode()}
            </pre>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-VIEW 3: PYTHON SDK & FRAMEWORK INTEGRATIONS           */}
      {/* ========================================================= */}
      {activeSubView === 'sdks' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1fr) minmax(450px, 1.4fr)', gap: '24px' }}>
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
              Developer Frameworks & SDKs
            </h3>
            <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Integrate the Context Trust Layer into your custom Python agents, LangChain tools, LlamaIndex pipelines, or REST HTTP callers.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {[
                { id: 'python', name: 'Python HTTPX SDK Client', desc: 'Direct REST SDK client' },
                { id: 'langchain', name: 'LangChain Tool Wrapper', desc: '@tool function decorator' },
                { id: 'llamaindex', name: 'LlamaIndex Tool Spec', desc: 'FunctionTool integration' },
                { id: 'curl', name: 'Standard cURL / JSON-RPC', desc: 'Raw HTTP POST payload' }
              ].map(s => (
                <div
                  key={s.id}
                  onClick={() => setActiveSnippet(s.id)}
                  style={{
                    padding: '12px 14px',
                    borderRadius: '10px',
                    border: `1px solid ${activeSnippet === s.id ? '#2026d2' : 'var(--border-color)'}`,
                    background: activeSnippet === s.id ? 'rgba(32,38,210,0.06)' : 'var(--bg-card)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px'
                  }}
                >
                  <span style={{ fontWeight: 600, fontSize: '0.85rem', color: activeSnippet === s.id ? '#2026d2' : 'var(--text-main)' }}>
                    {s.name}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{s.desc}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: '#0d1117', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '24px', color: '#c9d1d9', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '12px' }}>
              <span style={{ fontSize: '0.82rem', color: '#58a6ff', fontWeight: 600 }}>
                Code Integration Example
              </span>
              <button
                onClick={handleCopySnippet}
                style={{
                  padding: '5px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(255,255,255,0.2)',
                  background: 'rgba(255,255,255,0.08)',
                  color: '#fff',
                  fontSize: '0.74rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {copiedSnippet ? '✓ Copied' : '📋 Copy Code Snippet'}
              </button>
            </div>

            <pre style={{
              margin: 0,
              fontSize: '0.78rem',
              fontFamily: 'SFMono-Regular, Menlo, Monaco, monospace',
              overflowX: 'auto',
              color: '#f0f6fc',
              lineHeight: 1.5
            }}>
              {getClientConfigCode()}
            </pre>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-VIEW 4: JSON-RPC PROTOCOL & TOOL SCHEMAS              */}
      {/* ========================================================= */}
      {activeSubView === 'schemas' && (
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Registered MCP Tool Schemas (JSON-RPC 2.0)
              </h3>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                All 6 tools are dynamically discoverable by any MCP-compliant client via <code style={{ color: '#2026d2' }}>tools/list</code>.
              </p>
            </div>
            <span className="badge badge-verified">6 Tools Active</span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ background: 'var(--bg-card)', borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Tool Name</th>
                  <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Category</th>
                  <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Required Arguments</th>
                  <th style={{ padding: '10px 14px', color: 'var(--text-main)' }}>Description & Output</th>
                </tr>
              </thead>
              <tbody>
                {tools.map((t, idx) => (
                  <tr key={t.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '12px 14px', fontWeight: 600, color: '#2026d2' }}>
                      {t.icon} {t.name}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span className="badge" style={{ fontSize: '0.68rem' }}>{t.category}</span>
                    </td>
                    <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
                      {t.params}
                    </td>
                    <td style={{ padding: '12px 14px', color: 'var(--text-muted)' }}>
                      {t.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
