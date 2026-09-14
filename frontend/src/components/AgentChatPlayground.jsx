import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Plus, MoreHorizontal, Search, Trash2 } from 'lucide-react';

const STARTER_PROMPTS = [
  {
    title: "Enterprise Refund Policy",
    query: "What is our company refund window for enterprise annual contracts?",
    icon: "💳"
  },
  {
    title: "Remote Work Wi-Fi Security",
    query: "Can remote employees work from public Wi-Fi without VPN?",
    icon: "🔒"
  },
  {
    title: "Production Ingress Authority",
    query: "Who is authorized to approve production ingress firewall exceptions?",
    icon: "🛡️"
  },
  {
    title: "Disputed Policies Review",
    query: "Are there any conflicting refund rules between Slack and Confluence?",
    icon: "⚠️"
  }
];

export default function AgentChatPlayground({
  activeOrg,
  activePersona,
  workspaces,
  showToast,
  selectedSessionId,
  onSessionChange
}) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(selectedSessionId || null);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [inputPrompt, setInputPrompt] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [showPlusMenu, setShowPlusMenu] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState({});

  useEffect(() => {
    if (selectedSessionId && selectedSessionId !== activeSessionId) {
      setActiveSessionId(selectedSessionId);
      loadSessionDetails(selectedSessionId);
    }
  }, [selectedSessionId]);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const plusMenuRef = useRef(null);
  const orgId = activeOrg?.id || '11111111-1111-1111-1111-111111111111';
  const userId = activePersona?.id || null;

  // Close plus menu on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (plusMenuRef.current && !plusMenuRef.current.contains(e.target)) {
        setShowPlusMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result || '';
      setAttachedFile({
        name: file.name,
        size: file.size,
        content: String(content)
      });
      if (showToast) showToast(`Attached document: ${file.name}`);
      setShowPlusMenu(false);
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  // Load chat sessions for active user/persona
  const loadSessions = async (selectFirst = true) => {
    setIsLoadingSessions(true);
    try {
      const url = userId
        ? `/v1/chat/sessions?organization_id=${orgId}&user_id=${userId}`
        : `/v1/chat/sessions?organization_id=${orgId}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
        if (selectFirst && data.length > 0) {
          loadSessionDetails(data[0].id);
        } else if (data.length === 0) {
          setActiveSessionId(null);
          setActiveSession(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error("Failed to load chat sessions", err);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  // Load a single session details & messages
  const loadSessionDetails = async (sessionId) => {
    try {
      const res = await fetch(`/v1/chat/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setActiveSessionId(data.id);
        setActiveSession(data);
        setMessages(data.messages || []);
        if (onSessionChange) onSessionChange(data.id);
      }
    } catch (err) {
      console.error("Failed to load session details", err);
    }
  };

  // Create new session
  const handleCreateNewChat = async (initialTitle = "New Conversation") => {
    try {
      const res = await fetch('/v1/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: orgId,
          user_id: userId,
          user_name: activePersona?.name || 'Anonymous',
          user_role: activePersona?.role || 'developer',
          title: initialTitle,
        }),
      });
      if (res.ok) {
        const newSession = await res.json();
        setSessions(prev => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
        setActiveSession(newSession);
        setMessages([]);
        if (showToast) showToast("Started new chat session");
        return newSession.id;
      }
    } catch (err) {
      console.error("Failed to create new chat session", err);
    }
    return null;
  };

  // Delete session
  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/v1/chat/sessions/${sessionId}`, { method: 'DELETE' });
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.id !== sessionId));
        if (activeSessionId === sessionId) {
          const remaining = sessions.filter(s => s.id !== sessionId);
          if (remaining.length > 0) {
            loadSessionDetails(remaining[0].id);
          } else {
            setActiveSessionId(null);
            setActiveSession(null);
            setMessages([]);
          }
        }
        if (showToast) showToast("Chat session deleted");
      }
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  // Send message
  const handleSendMessage = async (customPrompt = null) => {
    let textToSend = (customPrompt || inputPrompt).trim();
    if ((!textToSend && !attachedFile) || isSending) return;

    if (attachedFile) {
      textToSend = `${textToSend ? textToSend + '\n\n' : ''}[Attached Document: ${attachedFile.name}]\n${attachedFile.content.slice(0, 3000)}`;
      setAttachedFile(null);
    }

    let currentSid = activeSessionId;
    if (!currentSid) {
      currentSid = await handleCreateNewChat(textToSend.slice(0, 50));
      if (!currentSid) return;
    }

    // Optimistically append user message
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: textToSend,
      metadata_json: { author: activePersona?.name || 'User', role: activePersona?.role || 'developer' },
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setInputPrompt('');
    setIsSending(true);

    try {
      const res = await fetch(`/v1/chat/sessions/${currentSid}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: orgId,
          content: textToSend,
          user_id: userId,
          user_name: activePersona?.name || 'User',
          user_role: activePersona?.role || 'developer',
        }),
      });

      if (res.ok) {
        const result = await res.json();
        // Replace with persisted messages
        setMessages(prev => [
          ...prev.filter(m => m.id !== tempUserMsg.id),
          result.user_message,
          result.assistant_message
        ]);
        // Update session list title if updated
        loadSessions(false);
      } else {
        if (showToast) showToast("Failed to process message with Context Gate");
      }
    } catch (err) {
      console.error("Failed to send message", err);
    } finally {
      setIsSending(false);
    }
  };

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  // Reload sessions when user persona or org changes
  useEffect(() => {
    loadSessions(true);
  }, [orgId, userId]);

  const filteredSessions = sessions.filter(s =>
    s.title?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div>
      {/* FULL-SCREEN AI COPILOT CHAT WORKSPACE (PLAIN BACKGROUND, DIRECT CHAT) */}
      <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 150px)', minHeight: '520px', background: 'transparent' }}>

        {/* MAIN WORKSPACE: CONVERSATION STREAM & QUERY BAR */}
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '0', overflow: 'hidden', background: 'transparent' }}>

          {/* Top Left Chat Header (Plain background, clean title) */}
          <div style={{
            padding: '2px 0 14px 0',
            borderBottom: '1px solid var(--border-subtle)',
            marginBottom: '4px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'transparent'
          }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-main)', margin: 0, letterSpacing: '-0.01em' }}>
                Interactive AI Copilot Chat
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Active Persona: <strong>{activePersona?.name || 'Sarah Chen'}</strong> ({activePersona?.role || 'admin'}) • Verified RAG Engine & Contradiction Filter
              </span>
            </div>
            <span className="badge badge-verified" style={{ fontSize: '0.68rem', padding: '3px 8px' }}>
              ● Trust Gate Online
            </span>
          </div>

          {/* Messages Scroll Area */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

            {/* Empty State / Starter Prompts */}
            {messages.length === 0 && (
              <div style={{ margin: 'auto', maxWidth: '640px', textAlign: 'center', padding: '20px 0' }}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🛡️</div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '6px' }}>
                  Ask Context Trust Layer
                </h2>
                <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '20px' }}>
                  Every answer is filtered by freshness decay, authority scoring, and contradiction detection. Expired or disputed claims are automatically highlighted.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', textAlign: 'left' }}>
                  {STARTER_PROMPTS.map((starter, i) => (
                    <button
                      key={i}
                      onClick={() => handleSendMessage(starter.query)}
                      style={{
                        background: 'var(--bg-card-subtle)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '12px',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.15s ease'
                      }}
                      onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--primary)'}
                      onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-subtle)'}
                    >
                      <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '3px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{starter.icon}</span> {starter.title}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                        "{starter.query}"
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message Cards */}
            {messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              const meta = msg.metadata_json || {};
              const decision = meta.decision;
              const citations = meta.citations || [];
              const warnings = meta.warnings || [];
              const isExpanded = expandedCitations[msg.id];

              return (
                <div
                  key={msg.id || idx}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    gap: '4px'
                  }}
                >
                  {/* Author & Timestamp */}
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, padding: '0 4px' }}>
                    {isUser ? (meta.author || activePersona?.name || 'You') : 'Context Trust Copilot'} • {new Date(msg.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>

                  {/* Bubble Content */}
                  <div
                    style={{
                      maxWidth: isUser ? '75%' : '88%',
                      padding: '14px 16px',
                      borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                      background: isUser ? 'var(--primary)' : 'var(--bg-card-subtle)',
                      color: isUser ? '#ffffff' : 'var(--text-main)',
                      border: isUser ? 'none' : '1px solid var(--border-subtle)',
                      fontSize: '0.85rem',
                      lineHeight: 1.55,
                      boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                    }}
                  >
                    {/* Synthesized Text */}
                    <div style={{ whiteSpace: 'pre-wrap', marginBottom: !isUser && (decision || citations.length > 0) ? '12px' : 0 }}>
                      {msg.content}
                    </div>

                    {/* Assistant Trust Details & Citations Card */}
                    {!isUser && (
                      <div>
                        {/* Trust Badges & Metrics Row */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)' }}>
                          {decision && (
                            <span className={`badge ${decision === 'ALLOW' ? 'badge-allow' : decision === 'BLOCK' ? 'badge-block' : 'badge-review'}`} style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                              Gate: {decision}
                            </span>
                          )}
                          {meta.trust_score !== undefined && (
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                              Trust Score: <strong style={{ color: 'var(--primary)' }}>{Math.round(meta.trust_score * 100)}/100</strong>
                            </span>
                          )}
                          {meta.confidence !== undefined && (
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                              Confidence: {Math.round(meta.confidence * 100)}%
                            </span>
                          )}
                        </div>

                        {/* Conflict Warnings Box */}
                        {warnings.length > 0 && (
                          <div style={{ marginTop: '10px', background: 'var(--danger-bg, rgba(239,68,68,0.1))', border: '1px solid var(--danger-border, rgba(239,68,68,0.25))', borderRadius: '6px', padding: '8px 10px', fontSize: '0.75rem', color: 'var(--danger-text)' }}>
                            <div style={{ fontWeight: 800, marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <span>⚠️</span> Contradiction Alert
                            </div>
                            {warnings.map((w, wi) => (
                              <div key={wi}>{w}</div>
                            ))}
                          </div>
                        )}

                        {/* Expandable Citations Accordion */}
                        {citations.length > 0 && (
                          <div style={{ marginTop: '10px' }}>
                            <button
                              onClick={() => setExpandedCitations(prev => ({ ...prev, [msg.id]: !prev[msg.id] }))}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--primary)',
                                fontSize: '0.74rem',
                                fontWeight: 700,
                                cursor: 'pointer',
                                padding: '0',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                            >
                              <span>{isExpanded ? '▾' : '▸'}</span> Grounded Evidence & Citations ({citations.length})
                            </button>

                            {isExpanded && (
                              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                {citations.map((c, ci) => (
                                  <div
                                    key={ci}
                                    style={{
                                      background: 'var(--bg-card)',
                                      border: '1px solid var(--border-subtle)',
                                      borderRadius: '6px',
                                      padding: '8px 10px',
                                      fontSize: '0.75rem'
                                    }}
                                  >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
                                      <strong style={{ color: 'var(--primary)' }}>{c.source_title}</strong>
                                      <span className="badge badge-verified" style={{ fontSize: '0.62rem', padding: '1px 4px' }}>
                                        Trust: {Math.round(c.trust_score * 100)}/100
                                      </span>
                                    </div>
                                    <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', marginBottom: '4px' }}>
                                      "{c.claim_text}"
                                    </div>
                                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                                      Validity: {c.validity} {c.section ? `• Section: ${c.section}` : ''}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Generating / Streaming Indicator */}
            {isSending && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', background: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', maxWidth: '400px' }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--primary)', animation: 'pulse 1s infinite' }} />
                <span style={{ fontSize: '0.8rem', color: 'var(--primary)', fontWeight: 600 }}>
                  Evaluating trust decay & contradiction gate...
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Single-Line Bar (Used for search normally, plain background) */}
          <div style={{ padding: '14px 0 4px 0', background: 'transparent' }}>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                background: '#FFFFFF',
                border: '1px solid var(--border-subtle, #E2E8F0)',
                borderRadius: '24px',
                padding: '10px 18px',
                boxShadow: '0 1px 4px rgba(0, 0, 0, 0.04)'
              }}
            >
              <Search size={18} color="#94A3B8" style={{ flexShrink: 0 }} />
              <input
                type="text"
                value={inputPrompt}
                onChange={e => setInputPrompt(e.target.value)}
                placeholder="Search policy rules or ask AI Copilot a question..."
                disabled={isSending}
                style={{
                  flex: 1,
                  border: 'none',
                  outline: 'none',
                  background: 'transparent',
                  fontSize: '0.875rem',
                  color: 'var(--text-main, #1E293B)',
                  fontFamily: 'inherit',
                  padding: '2px 0'
                }}
              />
              <button
                type="submit"
                disabled={!inputPrompt.trim() || isSending}
                style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '50%',
                  border: 'none',
                  background: !inputPrompt.trim() || isSending ? 'transparent' : 'var(--primary, #4F46E5)',
                  color: !inputPrompt.trim() || isSending ? '#CBD5E1' : '#FFFFFF',
                  cursor: !inputPrompt.trim() || isSending ? 'default' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.9rem',
                  fontWeight: 700,
                  transition: 'all 0.15s ease',
                  flexShrink: 0
                }}
                title="Search / Send"
              >
                {isSending ? "..." : "↑"}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
