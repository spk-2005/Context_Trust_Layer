import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, Plus, MoreHorizontal, Search, Trash2, 
  CheckCircle2, Clock, ShieldCheck, Sparkles, AlertTriangle, 
  Copy, Check, ChevronDown, ChevronRight, BookOpen, Layers, Shield
} from 'lucide-react';

const PROCESS_STEPS = [
  {
    action: "Searching indexed policy claims & vector embeddings",
    tag: "Retrieval",
    icon: "🔍"
  },
  {
    action: "Evaluating freshness decay & temporal validity",
    tag: "Decay Engine",
    icon: "⏳"
  },
  {
    action: "Auditing cross-source contradictions & policy disputes",
    tag: "Zero-Trust Gate",
    icon: "🛡️"
  },
  {
    action: "Evaluating governance thresholds & synthesizing answer",
    tag: "Context Gate",
    icon: "✨"
  }
];

// Modern Transparent Single-Spot Text Morphing Process Indicator
function ChatProcessingPipeline({ activeWorkspace }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      setElapsedMs(elapsed);
      const stepIdx = Math.min(Math.floor(elapsed / 750), PROCESS_STEPS.length - 1);
      setCurrentStep(stepIdx);
    }, 100);

    return () => clearInterval(interval);
  }, []);

  const step = PROCESS_STEPS[currentStep] || PROCESS_STEPS[0];

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '8px 4px',
        margin: '4px 0',
        background: 'transparent',
        border: 'none',
        boxShadow: 'none',
        width: '100%',
        minHeight: '36px'
      }}
    >
      {/* Sleek Gradient Rotating Spinner */}
      <div className="chat-process-spinner" />

      {/* Single-Spot Morphing Text with Smooth Keyframe Transition */}
      <div
        key={currentStep}
        className="chat-process-text-active"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
          color: '#1E293B',
          fontSize: '0.84rem'
        }}
      >
        <span style={{ fontSize: '0.9rem' }}>{step.icon}</span>
        <span style={{ fontWeight: 600, color: '#334155' }}>
          {step.action}
        </span>
        <span className="chat-bouncing-dots">
          <span />
          <span />
          <span />
        </span>
        {activeWorkspace && activeWorkspace.id !== 'all' && (
          <span style={{
            fontSize: '0.68rem',
            padding: '1px 6px',
            borderRadius: '10px',
            background: 'rgba(255, 171, 74, 0.15)',
            color: '#C2410C',
            fontWeight: 700
          }}>
            {activeWorkspace.name.split(' ')[0]}
          </span>
        )}
      </div>

      {/* Elapsed Counter */}
      <div style={{
        marginLeft: 'auto',
        fontSize: '0.72rem',
        color: '#94A3B8',
        fontWeight: 600,
        fontFamily: 'monospace'
      }}>
        {(elapsedMs / 1000).toFixed(1)}s
      </div>
    </div>
  );
}

// Rich Formatted Content Renderer for Catchy & Scannable Answers
function RichAnswerContent({ content }) {
  if (!content) return null;

  // Split into paragraphs / lines
  const rawLines = content.split('\n');
  const elements = [];
  let currentBulletList = [];

  const flushBulletList = () => {
    if (currentBulletList.length > 0) {
      elements.push(
        <div key={`bullets-${elements.length}`} style={{ margin: '8px 0', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {currentBulletList.map((item, bIdx) => (
            <div key={bIdx} className="chat-bullet-row">
              <div className="chat-bullet-dot" />
              <div style={{ flex: 1, color: '#1E293B', fontSize: '0.84rem' }}>
                {renderInlineFormatted(item)}
              </div>
            </div>
          ))}
        </div>
      );
      currentBulletList = [];
    }
  };

  const renderInlineFormatted = (text) => {
    // Parse bold text **text** and inline backticks
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, pIdx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        const inner = part.slice(2, -2);
        return (
          <strong key={pIdx} style={{ fontWeight: 700, color: 'var(--text-main, #0F172A)' }}>
            {inner}
          </strong>
        );
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        const inner = part.slice(1, -1);
        return (
          <code key={pIdx} style={{
            background: '#F1F5F9',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: '0.82em',
            color: '#0F172A',
            fontFamily: 'monospace'
          }}>
            {inner}
          </code>
        );
      }
      return part;
    });
  };

  for (let i = 0; i < rawLines.length; i++) {
    const line = rawLines[i].trim();
    if (!line) {
      flushBulletList();
      continue;
    }

    // Check for bullet items: `- `, `* `, `• `, `1. `
    const bulletMatch = line.match(/^([-*•]|\d+\.)\s+(.+)$/);
    if (bulletMatch) {
      currentBulletList.push(bulletMatch[2]);
      continue;
    }

    flushBulletList();

    // Check for Callout / Highlight cards (e.g. `💡`, `✨`, `⚠️`, `📌`, `**Direct Answer`, `**Bottom Line`)
    if (
      line.startsWith('💡') ||
      line.startsWith('✨') ||
      line.startsWith('📌') ||
      line.toLowerCase().includes('bottom line') ||
      line.toLowerCase().includes('direct answer') ||
      line.toLowerCase().includes('policy summary')
    ) {
      elements.push(
        <div key={`highlight-${i}`} className="chat-highlight-card">
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <span style={{ fontSize: '1.1rem', lineHeight: 1 }}>
              {line.startsWith('⚠️') ? '⚠️' : line.startsWith('✨') ? '✨' : line.startsWith('📌') ? '📌' : '💡'}
            </span>
            <div style={{ flex: 1 }}>
              {renderInlineFormatted(line.replace(/^[💡✨⚠️📌]\s*/, ''))}
            </div>
          </div>
        </div>
      );
      continue;
    }

    // Header elements `### `, `## `
    if (line.startsWith('### ') || line.startsWith('## ')) {
      const headerText = line.replace(/^#+\s*/, '');
      elements.push(
        <h4 key={`header-${i}`} style={{
          fontSize: '0.9rem',
          fontWeight: 700,
          color: '#0F172A',
          margin: '12px 0 6px 0',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <span style={{ width: '4px', height: '14px', background: '#FFAB4A', borderRadius: '2px', display: 'inline-block' }} />
          {renderInlineFormatted(headerText)}
        </h4>
      );
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={`p-${i}`} style={{ margin: '6px 0', lineHeight: 1.6, fontSize: '0.85rem', color: '#1E293B' }}>
        {renderInlineFormatted(line)}
      </p>
    );
  }

  flushBulletList();
  return <div>{elements}</div>;
}

const STARTER_PROMPTS_BY_WORKSPACE = {
  all: [
    { title: "Enterprise Refund Policy", query: "What is our company refund window for enterprise annual contracts?", icon: "💳" },
    { title: "Remote Work Wi-Fi Security", query: "Can remote employees work from public Wi-Fi without VPN?", icon: "🔒" },
    { title: "Production Ingress Authority", query: "Who is authorized to approve production ingress firewall exceptions?", icon: "🛡️" },
    { title: "Disputed Policies Review", query: "Are there any conflicting refund rules between Slack and Confluence?", icon: "⚠️" }
  ],
  finance: [
    { title: "Enterprise Refund Window", query: "What is our company refund window for enterprise annual contracts?", icon: "💳" },
    { title: "Invoice Dispute Arbitration", query: "What are the financial approval thresholds and dispute arbitration rules for billing?", icon: "📊" },
    { title: "Mid-Cycle Proration Rules", query: "How is billing proration calculated when enterprise accounts change contract tiers?", icon: "💰" },
    { title: "Billing vs Slack Conflict", query: "Are there any conflicting refund statements in sales channels versus the billing handbook?", icon: "⚠️" }
  ],
  secops: [
    { title: "Production Ingress Firewall", query: "Who is authorized to approve production ingress firewall exceptions?", icon: "🛡️" },
    { title: "Zero Trust Token Expiry", query: "What is the mandatory session timeout and mTLS certificate renewal rule for core services?", icon: "🔐" },
    { title: "Emergency Sev-1 Bypass", query: "Can emergency hotfixes bypass automated compliance verification during Sev-1 incidents?", icon: "⚡" },
    { title: "KMS Key Rotation Policy", query: "What are the cryptographic key rotation intervals enforced by our SecOps baseline?", icon: "🔑" }
  ],
  hr: [
    { title: "Remote Work Wi-Fi Security", query: "Can remote employees work from public Wi-Fi without VPN?", icon: "🔒" },
    { title: "International Leave Policy", query: "What are the mandatory leave guidelines and annual holiday allowances for remote team members?", icon: "🌴" },
    { title: "Home Office Stipend", query: "What is the reimbursement policy and expense allowance for home workstation equipment?", icon: "💻" },
    { title: "Contractor Compliance Checks", query: "Are background checks and security sign-offs mandatory for external contractors?", icon: "📋" }
  ],
  support: [
    { title: "Enterprise SLA Targets", query: "What is the guaranteed response time SLA for Tier-0 critical client incidents?", icon: "⏱️" },
    { title: "Customer Escalation Hierarchy", query: "When does an unresolved customer ticket get escalated to Engineering and Executive leadership?", icon: "📈" },
    { title: "Goodwill Credit Authorizations", query: "What is the maximum billing credit a frontline support lead can grant directly?", icon: "💵" },
    { title: "SSO Login Incident Playbook", query: "What is the standard procedure when a customer tenant experiences SAML SSO auth failure?", icon: "🔍" }
  ],
  staging: [
    { title: "Sandbox Test Claims", query: "What sandbox policy claims are currently staged for upcoming policy release?", icon: "🧪" },
    { title: "Mock Ingestion Rules", query: "How are synthetic ingestion events validated against staging confidence gates?", icon: "🔬" }
  ]
};

export default function AgentChatPlayground({
  activeOrg,
  activePersona,
  activeWorkspace,
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
  const [copiedMsgId, setCopiedMsgId] = useState(null);

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

  // Load chat sessions for active user/persona & workspace
  const loadSessions = async (selectFirst = true) => {
    setIsLoadingSessions(true);
    try {
      let url = userId
        ? `/v1/chat/sessions?organization_id=${orgId}&user_id=${userId}`
        : `/v1/chat/sessions?organization_id=${orgId}`;
      if (activeWorkspace && activeWorkspace.id !== 'all') {
        url += `&workspace_id=${activeWorkspace.id}`;
      }
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

  // Reload sessions whenever active workspace or org changes
  useEffect(() => {
    loadSessions(true);
  }, [activeWorkspace?.id, orgId, userId]);

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

  // Create new session tagged with active departmental workspace
  const handleCreateNewChat = async (initialTitle = "New Conversation") => {
    try {
      const wsPrefix = activeWorkspace && activeWorkspace.id !== 'all' ? `[${activeWorkspace.name.split(' ')[0]}] ` : '';
      const finalTitle = initialTitle.startsWith('[') ? initialTitle : `${wsPrefix}${initialTitle}`;
      const res = await fetch('/v1/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: orgId,
          user_id: userId,
          user_name: activePersona?.name || 'Anonymous',
          user_role: activePersona?.role || 'developer',
          title: finalTitle,
          workspace_id: activeWorkspace?.id || 'all',
          domain: activeWorkspace?.domain || 'global',
        }),
      });
      if (res.ok) {
        const newSession = await res.json();
        setSessions(prev => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
        setActiveSession(newSession);
        setMessages([]);
        if (showToast) showToast(`Started new chat in ${activeWorkspace?.name || 'workspace'}`);
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
          workspace_id: activeWorkspace?.id || 'all',
          domain: activeWorkspace?.domain || 'global',
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
      <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 130px)', maxHeight: 'calc(100vh - 130px)', background: 'transparent', overflow: 'hidden' }}>

        {/* MAIN WORKSPACE: CONVERSATION STREAM & QUERY BAR */}
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '0', overflow: 'hidden', background: 'transparent' }}>

          {/* Messages Scroll Area - No unnecessary scrollbar in empty state */}
          <div
            id="chat-messages-container"
            style={{
              flex: 1,
              overflowY: messages.length === 0 ? 'hidden' : 'auto',
              padding: messages.length === 0 ? '8px 12px' : '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              justifyContent: messages.length === 0 ? 'center' : 'flex-start'
            }}
          >

            {/* Empty State: Centered Big Rectangular Chat Box + Prompts */}
            {messages.length === 0 && (
              <div style={{
                margin: 'auto',
                width: '100%',
                maxWidth: '680px',
                textAlign: 'center',
                padding: '10px 0',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center'
              }}>
                {/* Ask Trulin - Smaller text */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <h2 style={{
                    fontSize: '1rem',
                    fontWeight: 700,
                    color: 'var(--text-main, #0F172A)',
                    margin: 0,
                    letterSpacing: '-0.01em'
                  }}>
                    Ask
                  </h2>
                  <img src="/Trulin-Main-NoBg.png" alt="Trulin" style={{ height: '24px', objectFit: 'contain' }} />
                
                </div>

                {/* Subtitle - Smaller text */}
                <p style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-muted, #64748B)',
                  lineHeight: 1.45,
                  maxWidth: '540px',
                  marginBottom: '10px'
                }}>
                  Every answer is filtered by freshness decay, authority scoring, and contradiction detection. Expired or disputed claims are automatically highlighted.
                </p>

                {/* Workspace Retrieval Scope Badge */}
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '4px 12px',
                  borderRadius: '20px',
                  fontSize: '0.74rem',
                  fontWeight: 600,
                  background: activeWorkspace && activeWorkspace.id !== 'all' ? 'rgba(37, 99, 235, 0.08)' : 'rgba(100, 116, 139, 0.08)',
                  color: activeWorkspace && activeWorkspace.id !== 'all' ? 'var(--primary, #2563EB)' : '#64748B',
                  border: `1px solid ${activeWorkspace && activeWorkspace.id !== 'all' ? 'rgba(37, 99, 235, 0.2)' : 'rgba(100, 116, 139, 0.2)'}`,
                  marginBottom: '16px'
                }}>
                  <span>{activeWorkspace?.icon || '🏢'}</span>
                  <span>Scope: <strong>{activeWorkspace?.name || 'All Workspaces (Unified)'}</strong></span>
                  {activeWorkspace && activeWorkspace.id !== 'all' ? (
                    <span style={{ fontSize: '0.68rem', color: '#16A34A', background: 'rgba(22, 163, 74, 0.1)', padding: '1px 6px', borderRadius: '10px', marginLeft: '4px' }}>● Isolated Departmental Retrieval</span>
                  ) : (
                    <span style={{ fontSize: '0.68rem', color: '#2563EB', background: 'rgba(37, 99, 235, 0.1)', padding: '1px 6px', borderRadius: '10px', marginLeft: '4px' }}>● Unified Enterprise Retrieval</span>
                  )}
                </div>

                {/* Big Rectangular Chat Box at Center with Disco Blue Animated Border & Glow Shadow */}
                <div
                  className="disco-blue-border-card"
                  style={{
                    width: '100%',
                    padding: '14px 18px 12px 18px',
                    marginBottom: '16px',
                    textAlign: 'left'
                  }}
                >
                  <textarea
                    rows={2}
                    value={inputPrompt}
                    onChange={e => setInputPrompt(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    placeholder={activeWorkspace && activeWorkspace.id !== 'all' ? `Ask Trulin in ${activeWorkspace.name} (queries scoped to ${activeWorkspace.domain} claims)...` : "Search policy rules or ask AI Copilot a question..."}
                    disabled={isSending}
                    style={{
                      width: '100%',
                      border: 'none',
                      outline: 'none',
                      background: 'transparent',
                      resize: 'none',
                      fontSize: '0.875rem',
                      color: 'var(--text-main, #0F172A)',
                      fontFamily: 'inherit',
                      lineHeight: 1.5,
                      padding: 0
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', paddingTop: '6px', borderTop: '1px solid #F1F5F9' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.7rem', color: 'var(--text-muted, #94A3B8)' }}>
                      <Search size={13} color="#94A3B8" />
                      <span>Press <kbd style={{ padding: '1px 5px', background: '#F1F5F9', borderRadius: '4px', border: '1px solid #E2E8F0', fontSize: '0.66rem', fontWeight: 600 }}>Enter</kbd> to ask</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleSendMessage()}
                      disabled={!inputPrompt.trim() || isSending}
                      style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '6px',
                        border: 'none',
                        background: !inputPrompt.trim() || isSending ? '#F1F5F9' : 'var(--primary, #2563EB)',
                        color: !inputPrompt.trim() || isSending ? '#94A3B8' : '#FFFFFF',
                        cursor: !inputPrompt.trim() || isSending ? 'default' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.85rem',
                        fontWeight: 700,
                        transition: 'all 0.15s ease'
                      }}
                      title="Send Question"
                    >
                      {isSending ? "..." : "↑"}
                    </button>
                  </div>
                </div>

                {/* Below that: Suggested Prompts */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '8px',
                  width: '100%',
                  textAlign: 'left'
                }}>
                  {(STARTER_PROMPTS_BY_WORKSPACE[activeWorkspace?.id || 'all'] || STARTER_PROMPTS_BY_WORKSPACE.all).map((starter, i) => (
                    <button
                      key={i}
                      onClick={() => handleSendMessage(starter.query)}
                      style={{
                        background: 'var(--bg-card-subtle, #F8FAFC)',
                        border: '1px solid var(--border-subtle, #E2E8F0)',
                        borderRadius: '8px',
                        padding: '10px 12px',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.15s ease'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.borderColor = 'var(--primary, #2563EB)';
                        e.currentTarget.style.background = '#FFFFFF';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.borderColor = 'var(--border-subtle, #E2E8F0)';
                        e.currentTarget.style.background = 'var(--bg-card-subtle, #F8FAFC)';
                      }}
                    >
                      <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main, #0F172A)', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{starter.icon}</span> {starter.title}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted, #64748B)', lineHeight: 1.35 }}>
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
              const isCopied = copiedMsgId === msg.id;

              return (
                <div
                  key={msg.id || idx}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    gap: '4px',
                    width: '100%'
                  }}
                >
                  {/* Author & Timestamp */}
                  <div style={{
                    fontSize: '0.68rem',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                    padding: '0 4px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}>
                    {!isUser && <img src="/Trulin-Main-NoBg.png" alt="Trulin" style={{ height: '14px', objectFit: 'contain' }} />}
                    <span>{isUser ? (meta.author || activePersona?.name || 'You') : 'Context Trust Copilot'}</span>
                    <span>•</span>
                    <span>{new Date(msg.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>

                  {/* Message Bubble */}
                  {isUser ? (
                    <div
                      className="user-question-card"
                      style={{
                        maxWidth: '78%',
                        padding: '12px 16px',
                        borderRadius: '14px 14px 2px 14px',
                        color: 'var(--text-main, #0F172A)',
                        fontSize: '0.86rem',
                        lineHeight: 1.55,
                      }}
                    >
                      <div style={{ whiteSpace: 'pre-wrap' }}>
                        {msg.content}
                      </div>
                    </div>
                  ) : (
                    <div
                      className="chat-answer-bubble"
                      style={{
                        maxWidth: '92%',
                        width: '100%',
                        background: '#FFFFFF',
                        border: '1px solid #E2E8F0',
                        borderRadius: '14px 14px 14px 2px',
                        boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
                        overflow: 'hidden'
                      }}
                    >
                      {/* Top Header Verdict Bar */}
                      <div className="chat-verdict-bar">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          {decision && (
                            <span
                              className={`badge ${decision === 'ALLOW' ? 'badge-allow' : decision === 'BLOCK' ? 'badge-block' : 'badge-review'}`}
                              style={{ fontSize: '0.7rem', padding: '2px 9px', fontWeight: 700, borderRadius: '6px' }}
                            >
                              GATE: {decision}
                            </span>
                          )}
                          {meta.trust_score !== undefined && (
                            <span style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '5px',
                              fontSize: '0.74rem',
                              fontWeight: 700,
                              color: '#334155',
                              background: '#F1F5F9',
                              padding: '2px 8px',
                              borderRadius: '6px'
                            }}>
                              <span>🛡️ Trust Score:</span>
                              <strong style={{ color: '#EA580C' }}>{Math.round(meta.trust_score * 100)}/100</strong>
                            </span>
                          )}
                          {meta.confidence !== undefined && (
                            <span style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600 }}>
                              Confidence: {Math.round(meta.confidence * 100)}%
                            </span>
                          )}
                        </div>

                        {/* Quick Copy Button */}
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(msg.content);
                            setCopiedMsgId(msg.id);
                            if (showToast) showToast("Answer copied to clipboard!");
                            setTimeout(() => setCopiedMsgId(null), 2000);
                          }}
                          style={{
                            background: isCopied ? '#F0FDF4' : 'transparent',
                            border: `1px solid ${isCopied ? '#86EFAC' : '#E2E8F0'}`,
                            borderRadius: '6px',
                            padding: '3px 8px',
                            fontSize: '0.7rem',
                            fontWeight: 600,
                            color: isCopied ? '#16A34A' : '#64748B',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            transition: 'all 0.15s ease'
                          }}
                          title="Copy Answer"
                        >
                          {isCopied ? <Check size={12} color="#16A34A" /> : <Copy size={12} color="#64748B" />}
                          <span>{isCopied ? "Copied" : "Copy"}</span>
                        </button>
                      </div>

                      {/* Main Structured Body */}
                      <div style={{ padding: '14px 18px' }}>
                        <RichAnswerContent content={msg.content} />

                        {/* Conflict Warnings Alert */}
                        {warnings.length > 0 && (
                          <div style={{
                            marginTop: '12px',
                            background: 'rgba(239, 68, 68, 0.08)',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            borderLeft: '4px solid #DC2626',
                            borderRadius: '8px',
                            padding: '10px 14px',
                            fontSize: '0.78rem',
                            color: '#991B1B'
                          }}>
                            <div style={{ fontWeight: 800, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <AlertTriangle size={15} color="#DC2626" />
                              <span>Contradiction & Policy Dispute Alert</span>
                            </div>
                            {warnings.map((w, wi) => (
                              <div key={wi} style={{ lineHeight: 1.4, marginTop: '2px' }}>{w}</div>
                            ))}
                          </div>
                        )}

                        {/* Expandable Evidence & Citations */}
                        {citations.length > 0 && (
                          <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #F1F5F9' }}>
                            <button
                              type="button"
                              onClick={() => setExpandedCitations(prev => ({ ...prev, [msg.id]: !prev[msg.id] }))}
                              style={{
                                background: '#F8FAFC',
                                border: '1px solid #E2E8F0',
                                borderRadius: '8px',
                                color: '#1E293B',
                                fontSize: '0.74rem',
                                fontWeight: 700,
                                cursor: 'pointer',
                                padding: '6px 12px',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                                transition: 'all 0.15s ease'
                              }}
                            >
                              {isExpanded ? <ChevronDown size={14} color="#EA580C" /> : <ChevronRight size={14} color="#EA580C" />}
                              <BookOpen size={13} color="#EA580C" />
                              <span>Grounded Evidence & Verified Citations ({citations.length})</span>
                            </button>

                            {isExpanded && (
                              <div style={{
                                marginTop: '10px',
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                                gap: '8px'
                              }}>
                                {citations.map((c, ci) => (
                                  <div
                                    key={ci}
                                    style={{
                                      background: '#FAFAFA',
                                      border: '1px solid #E2E8F0',
                                      borderRadius: '8px',
                                      padding: '10px 12px',
                                      fontSize: '0.76rem',
                                      display: 'flex',
                                      flexDirection: 'column',
                                      gap: '4px'
                                    }}
                                  >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                      <strong style={{ color: '#0F172A', fontSize: '0.78rem' }}>
                                        {c.source_title}
                                      </strong>
                                      <span className="badge badge-verified" style={{ fontSize: '0.64rem', padding: '1px 6px', borderRadius: '4px' }}>
                                        Trust: {Math.round(c.trust_score * 100)}/100
                                      </span>
                                    </div>
                                    <div style={{ color: '#475569', fontStyle: 'italic', lineHeight: 1.4, margin: '2px 0' }}>
                                      "{c.claim_text}"
                                    </div>
                                    <div style={{ fontSize: '0.68rem', color: '#94A3B8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <span>Status: <strong style={{ color: '#16A34A' }}>{c.validity || 'Active'}</strong></span>
                                      {c.section && <span>• {c.section}</span>}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Dynamic Multi-Step Process Pipeline Animation */}
            {isSending && (
              <ChatProcessingPipeline activeWorkspace={activeWorkspace} />
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Single-Line Bar - Only shown when active conversation messages exist */}
          {messages.length > 0 && (
            <div style={{ padding: '10px 0 2px 0', background: 'transparent', flexShrink: 0 }}>
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
                {activeWorkspace && (
                  <span style={{
                    fontSize: '0.72rem',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    background: activeWorkspace.id !== 'all' ? 'rgba(37, 99, 235, 0.08)' : '#F1F5F9',
                    color: activeWorkspace.id !== 'all' ? 'var(--primary, #2563EB)' : '#64748B',
                    fontWeight: 600,
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}>
                    <span>{activeWorkspace.icon || '🏢'}</span>
                    <span>{activeWorkspace.id === 'all' ? 'Unified' : activeWorkspace.name.split(' ')[0]}</span>
                  </span>
                )}
                <input
                  type="text"
                  value={inputPrompt}
                  onChange={e => setInputPrompt(e.target.value)}
                  placeholder={activeWorkspace && activeWorkspace.id !== 'all' ? `Ask in ${activeWorkspace.name}...` : "Search policy rules or ask AI Copilot a question..."}
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
                    background: !inputPrompt.trim() || isSending ? 'transparent' : 'var(--primary, #2563EB)',
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
          )}
        </div>
      </div>
    </div>
  );
}

