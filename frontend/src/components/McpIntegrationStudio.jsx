import React, { useState, useEffect } from 'react';

export default function McpIntegrationStudio({ activeOrg, showToast }) {
  const [selectedTool, setSelectedTool] = useState('context_trust_get_trusted_context');
  const [toolQuery, setToolQuery] = useState('What is the maximum allowed automated refund for India customers?');
  const [minTrustScore, setMinTrustScore] = useState(0.75);
  const [maxResults, setMaxResults] = useState(5);
  const [actionType, setActionType] = useState('Determine whether customer is eligible for 45-day refund');
  const [actorId, setActorId] = useState('billing-agent-01');
  const [actorRole, setActorRole] = useState('support');
  const [searchText, setSearchText] = useState('refund');
  const [claimText, setClaimText] = useState('Refund window is strictly limited to 30 days.');
  const [invoking, setInvoking] = useState(false);
  const [invocationResult, setInvocationResult] = useState(null);
  const [activeSnippet, setActiveSnippet] = useState('claude'); // 'claude' | 'cursor' | 'python' | 'langchain' | 'curl'
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  const tools = [
    {
      id: 'context_trust_get_trusted_context',
      name: 'get_trusted_context',
      icon: '🛡️',
      description: 'Retrieves evidence-backed, verified context before an AI agent makes a decision.',
      category: 'RAG Retrieval'
    },
    {
      id: 'context_trust_evaluate_decision',
      name: 'evaluate_decision',
      icon: '⚖️',
      description: 'Evaluates agent actions against authority hierarchy and active policy contradictions.',
      category: 'Decision Gate'
    },
    {
      id: 'context_trust_search_claims',
      name: 'search_claims',
      icon: '⚡',
      description: 'Queries atomic claims database with predicate matching and trust bounds.',
      category: 'Knowledge Graph'
    },
    {
      id: 'context_trust_check_conflicts',
      name: 'check_conflicts',
      icon: '🚨',
      description: 'Detects if a statement contradicts existing enterprise policies.',
      category: 'Conflict Analysis'
    },
    {
      id: 'context_trust_get_lineage',
      name: 'get_lineage',
      icon: '🕸️',
      description: 'Fetches end-to-end DAG lineage and downstream blast radius.',
      category: 'Lineage & Provenance'
    },
    {
      id: 'context_trust_steward_audit',
      name: 'steward_audit',
      icon: '🤖',
      description: 'Runs autonomous heuristic audit scan for stale policies and contradictions.',
      category: 'Context Curator'
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
    } else if (activeSnippet === 'python') {
      return `# Python MCP / SDK Client Example
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000/v1")

# Query Grounded Context before Agent Tool Call
response = client.post("/mcp/invoke", json={
    "tool": "context_trust_get_trusted_context",
    "arguments": {
        "query": "Can customer receive 45-day refund?",
        "organization_id": "${orgId}",
        "min_trust_score": 0.80
    }
})

trusted_context = response.json()
print("Grounded Context:", trusted_context)`;
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
    }
    return `curl -X POST http://127.0.0.1:8000/v1/mcp \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'`;
  };

  const handleCopySnippet = () => {
    navigator.clipboard.writeText(getClientConfigCode());
    setCopiedSnippet(true);
    showToast?.("Configuration snippet copied to clipboard!");
    setTimeout(() => setCopiedSnippet(false), 2000);
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
                Model Context Protocol (MCP) Server & Agent Hub
              </h2>
              <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                Standard JSON-RPC 2.0
              </span>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Connect external AI agents (Claude Desktop, Cursor, OpenAI Swarm, LangChain) directly to the Context Trust Layer over standard MCP protocol.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="badge" style={{ background: '#f0f4ff', color: '#2026d2' }}>Endpoint: /v1/mcp</span>
          <span className="badge badge-verified">Protocol v2024-11-05</span>
        </div>
      </div>

      {/* Main Grid: Tool Runner + JSON Response & Integrations */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(420px, 1.2fr) minmax(400px, 1fr)', gap: '24px' }}>
        {/* Left Column: Interactive Tool Tester */}
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
            1. Select & Execute MCP Tool
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
              Tool Input Parameters:
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
                Fetches full DAG graph nodes and blast-radius mappings for active workspace.
              </p>
            )}

            {selectedTool === 'context_trust_steward_audit' && (
              <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Executes autonomous heuristic scan over all active claims and generates scorecard.
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

        {/* Right Column: Live Output & Exporters */}
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
            maxHeight: '380px'
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
              maxHeight: '300px',
              lineHeight: 1.45,
              color: '#7ee787'
            }}>
              {invocationResult ? JSON.stringify(invocationResult, null, 2) : `// Execute any tool on the left to inspect live JSON payload.\n{\n  "jsonrpc": "2.0",\n  "status": "ready",\n  "server": "context-trust-layer",\n  "tools_available": 6\n}`}
            </pre>
          </div>

          {/* 1-Click Client Configuration Exporter */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h4 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Client Integration Snippets
              </h4>
              <button
                onClick={handleCopySnippet}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-card)',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <span>{copiedSnippet ? '✓ Copied' : '📋 Copy Config'}</span>
              </button>
            </div>

            {/* Snippet Tabs */}
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {[
                { id: 'claude', label: 'Claude Desktop' },
                { id: 'cursor', label: 'Cursor IDE' },
                { id: 'python', label: 'Python SDK' },
                { id: 'langchain', label: 'LangChain' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveSnippet(tab.id)}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    background: activeSnippet === tab.id ? '#2026d2' : 'transparent',
                    color: activeSnippet === tab.id ? '#fff' : 'var(--text-muted)',
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <pre style={{
              margin: 0,
              padding: '12px',
              borderRadius: '8px',
              background: '#0d1117',
              color: '#f0f6fc',
              fontSize: '0.72rem',
              fontFamily: 'SFMono-Regular, Menlo, Monaco, monospace',
              overflowX: 'auto',
              maxHeight: '140px',
              lineHeight: 1.4
            }}>
              {getClientConfigCode()}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
