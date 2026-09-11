import React, { useState, useEffect, useRef } from 'react';

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
  showToast
}) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [inputPrompt, setInputPrompt] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [showPlusMenu, setShowPlusMenu] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState({});

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
      {/* Top Header */}
      <div style={{ marginBottom: '18px' }}>


      </div>

      {/* FULL-SCREEN AI COPILOT CHAT WORKSPACE */}
      <div style={{ display: 'grid', gridTemplateColumns: '290px 1fr', gap: '16px', height: 'calc(100vh - 230px)', minHeight: '620px' }}>

        {/* LEFT SIDEBAR: CONVERSATION HISTORY PER USER */}
        <div className="clean-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '14px' }}>

          {/* New Chat Button */}
          <button
            onClick={() => handleCreateNewChat("New Conversation")}
            className="btn btn-primary"
            style={{
              width: '100%',
              padding: '9px 12px',
              fontSize: '0.82rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              marginBottom: '12px'
            }}
          >
            <span>+</span> New Chat Thread
          </button>

       

          {/* Search History Filter */}
          <div style={{ marginBottom: '10px' }}>
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              style={{ width: '100%', padding: '6px 10px', fontSize: '0.78rem', borderRadius: '6px' }}
            />
          </div>

          {/* Sessions List */}
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {isLoadingSessions && (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.78rem', padding: '20px' }}>
                Loading history...
              </div>
            )}

            {!isLoadingSessions && filteredSessions.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.78rem', padding: '30px 10px' }}>
                No previous conversations.<br />
                Click <strong>+ New Chat</strong> to begin.
              </div>
            )}

            {filteredSessions.map(sess => {
              const isActive = sess.id === activeSessionId;
              return (
                <div
                  key={sess.id}
                  onClick={() => loadSessionDetails(sess.id)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '6px',
                    background: isActive ? 'var(--primary-subtle, rgba(99,102,241,0.12))' : 'transparent',
                    border: isActive ? '1px solid var(--primary)' : '1px solid transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ overflow: 'hidden', paddingRight: '6px' }}>
                    <div style={{
                      fontSize: '0.78rem',
                      fontWeight: isActive ? 700 : 500,
                      color: isActive ? 'var(--primary)' : 'var(--text-main)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {sess.title || 'Untitled Conversation'}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {new Date(sess.updated_at || sess.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })} • {sess.message_count || 0} messages
                    </div>
                  </div>

                  <button
                    onClick={(e) => handleDeleteSession(e, sess.id)}
                    title="Delete conversation"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '4px',
                      fontSize: '0.8rem',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center'
                    }}
                    onMouseEnter={e => e.currentTarget.style.color = 'var(--danger-text)'}
                    onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
                  >
                    ✕
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT MAIN WORKSPACE: CONVERSATION STREAM & QUERY BAR */}
        <div className="clean-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '0', overflow: 'hidden' }}>

          {/* Active Thread Top Bar */}
          <div style={{
            padding: '12px 18px',
            borderBottom: '1px solid var(--border-subtle)',
            background: 'var(--bg-card-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <h3 style={{ fontSize: '0.92rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                {activeSession?.title || 'Interactive AI Context Session'}
              </h3>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                Active Persona: <strong>{activePersona?.name || 'Alex'}</strong> ({activePersona?.role || 'DATA_OWNER'}) • Verified RAG Engine
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

          {/* Bottom Query Input Box (ChatGPT-style Unified Bar) */}
          <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-card)' }}>
            
            {/* Hidden File Input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              accept=".txt,.md,.json,.csv,.pdf,.yaml,.yml"
            />

            {/* Attached File Preview Pill */}
            {attachedFile && (
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                background: 'var(--bg-card-subtle)',
                border: '1px solid var(--primary)',
                borderRadius: '6px',
                padding: '4px 10px',
                fontSize: '0.75rem',
                color: 'var(--primary)',
                marginBottom: '8px'
              }}>
                <span>📄</span>
                <strong>{attachedFile.name}</strong>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>({Math.round(attachedFile.size / 1024)} KB)</span>
                <button
                  type="button"
                  onClick={() => setAttachedFile(null)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', marginLeft: '4px', fontSize: '0.8rem' }}
                  title="Remove attachment"
                >
                  ✕
                </button>
              </div>
            )}

            {/* Unified ChatGPT-style Input Container */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'var(--bg-card-subtle)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '16px',
              padding: '6px 10px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
              position: 'relative'
            }}>
              
              {/* Plus (+) Button with Action Menu */}
              <div ref={plusMenuRef} style={{ position: 'relative' }}>
                <button
                  type="button"
                  onClick={() => setShowPlusMenu(prev => !prev)}
                  title="Attach file or action"
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    border: '1px solid var(--border-subtle)',
                    background: showPlusMenu ? 'var(--primary)' : 'var(--bg-card)',
                    color: showPlusMenu ? '#ffffff' : 'var(--text-main)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    fontSize: '1.2rem',
                    fontWeight: 600,
                    transition: 'all 0.15s ease',
                    lineHeight: 1
                  }}
                >
                  +
                </button>

                {/* Plus Popup Menu */}
                {showPlusMenu && (
                  <div style={{
                    position: 'absolute',
                    bottom: 'calc(100% + 8px)',
                    left: 0,
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
                    zIndex: 200,
                    width: '240px',
                    padding: '6px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px'
                  }}>
                    <button
                      type="button"
                      onClick={() => {
                        fileInputRef.current?.click();
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '8px 10px',
                        background: 'transparent',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '0.78rem',
                        color: 'var(--text-main)',
                        cursor: 'pointer',
                        textAlign: 'left'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover, rgba(99,102,241,0.08))'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <span style={{ fontSize: '0.95rem' }}>📎</span>
                      <div>
                        <div style={{ fontWeight: 600 }}>Attach Document</div>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>.txt, .md, .pdf, .json, .csv</div>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        handleCreateNewChat("New Conversation");
                        setShowPlusMenu(false);
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '8px 10px',
                        background: 'transparent',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '0.78rem',
                        color: 'var(--text-main)',
                        cursor: 'pointer',
                        textAlign: 'left'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover, rgba(99,102,241,0.08))'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <span style={{ fontSize: '0.95rem' }}>✨</span>
                      <div>
                        <div style={{ fontWeight: 600 }}>New Conversation</div>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Start fresh thread</div>
                      </div>
                    </button>
                  </div>
                )}
              </div>

              {/* Textarea */}
              <textarea
                rows={1}
                value={inputPrompt}
                onChange={e => setInputPrompt(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="Ask any policy or governance question..."
                style={{
                  flex: 1,
                  padding: '8px 4px',
                  fontSize: '0.85rem',
                  border: 'none',
                  outline: 'none',
                  background: 'transparent',
                  resize: 'none',
                  fontFamily: 'inherit',
                  color: 'var(--text-main)',
                  minHeight: '28px',
                  maxHeight: '120px'
                }}
              />

              {/* Send Button */}
              <button
                type="button"
                onClick={() => handleSendMessage()}
                disabled={(!inputPrompt.trim() && !attachedFile) || isSending}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  border: 'none',
                  background: (!inputPrompt.trim() && !attachedFile) || isSending ? 'var(--border-subtle)' : 'var(--primary)',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: (!inputPrompt.trim() && !attachedFile) || isSending ? 'not-allowed' : 'pointer',
                  fontSize: '0.95rem',
                  fontWeight: 700,
                  transition: 'all 0.15s ease'
                }}
                title="Send message"
              >
                {isSending ? "..." : "↑"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
