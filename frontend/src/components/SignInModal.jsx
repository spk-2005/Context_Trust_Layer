import React, { useState } from 'react';
import {
  Shield,
  Key,
  Users,
  Building2,
  Lock,
  Mail,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  X,
  ChevronRight,
  Globe,
  ExternalLink,
  Building,
  Check
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function SignInModal() {
  const {
    isAuthModalOpen,
    setIsAuthModalOpen,
    authModalTab,
    setAuthModalTab,
    personas,
    login,
    register,
    loginAsPersona,
    loginWithSSO,
    loginWithCorporateDomain,
    ssoProviders,
    user: currentUser
  } = useAuth();

  // Form states
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regOrgName, setRegOrgName] = useState('');
  const [regRole, setRegRole] = useState('reviewer');
  const [regDept, setRegDept] = useState('Risk & Governance');

  // SSO states
  const [ssoEmail, setSsoEmail] = useState('elena.rostova@ssfa.com');
  const [ssoProvider, setSsoProvider] = useState('google');

  const [loading, setLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  if (!isAuthModalOpen) return null;

  const handleSSOClick = async (provider) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction(provider === 'google' ? 'Google Workspace' : provider === 'microsoft' ? 'Microsoft Entra ID' : 'Okta Identity');
    try {
      await loginWithSSO(provider);
      setSuccessMsg(`Authenticated successfully via ${provider === 'google' ? 'Google Workspace' : provider === 'microsoft' ? 'Microsoft Entra ID' : 'Okta'}.`);
    } catch (err) {
      setErrorMsg(err.message || `Failed to sign in via ${provider} SSO.`);
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  const handleCorporateSSOSubmit = async (e) => {
    e.preventDefault();
    if (!ssoEmail || !ssoEmail.includes('@')) {
      setErrorMsg('Please enter a valid corporate email address.');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction('Corporate SSO Federation');
    try {
      const domain = ssoEmail.split('@')[1];
      await loginWithCorporateDomain(ssoEmail);
      setSuccessMsg(`Corporate SSO authentication confirmed for @${domain}!`);
    } catch (err) {
      setErrorMsg(err.message || 'Corporate domain SSO sign-in failed.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  const handleEmailLogin = async (e) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);
    try {
      await login(loginEmail, loginPassword);
    } catch (err) {
      setErrorMsg(err.message || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);
    try {
      await register({
        name: regName,
        email: regEmail,
        password: regPassword,
        organization_name: regOrgName || 'Enterprise Tenant',
        role: regRole,
        department: regDept,
        title: regRole === 'admin' ? 'Chief Compliance Officer' : regRole === 'data_owner' ? 'Data Steward' : 'Risk Auditor'
      });
      setSuccessMsg('Account created successfully!');
    } catch (err) {
      setErrorMsg(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const getRoleBadgeStyle = (role) => {
    switch (role?.toLowerCase()) {
      case 'admin':
        return { label: 'ADMIN / CCO', bg: '#ECFDF5', color: '#047857', border: '#A7F3D0' };
      case 'data_owner':
        return { label: 'DATA STEWARD', bg: '#EFF6FF', color: '#1D4ED8', border: '#BFDBFE' };
      case 'reviewer':
        return { label: 'AUDITOR', bg: '#EEF2FF', color: '#4338CA', border: '#C7D2FE' };
      default:
        return { label: 'OPERATOR', bg: '#FFFBEB', color: '#B45309', border: '#FDE68A' };
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '16px'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) setIsAuthModalOpen(false);
      }}
    >
      {/* Modal Dialog Box */}
      <div
        style={{
          width: '100%',
          maxWidth: '520px',
          backgroundColor: '#FFFFFF',
          borderRadius: '12px',
          border: '1px solid #E2E8F0',
          boxShadow: '0 20px 45px -10px rgba(0, 0, 0, 0.22), 0 0 0 1px rgba(0, 0, 0, 0.04)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh'
        }}
      >
        {/* Top Accent Line */}
        <div style={{ height: '4px', background: 'linear-gradient(90deg, #FFAB4A, #F5982C, #EA580C)' }} />

        {/* Modal Header */}
        <div
          style={{
            padding: '18px 24px 14px 24px',
            borderBottom: '1px solid #F1F5F9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FAFAFC'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img 
              src="/Trulin-Main-NoBg.png" 
              alt="Trulin" 
              style={{ height: '32px', maxWidth: '140px', objectFit: 'contain' }} 
            />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  style={{
                    fontSize: '0.62rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    backgroundColor: 'rgba(255,171,74,0.15)',
                    color: '#B45309',
                    border: '1px solid rgba(255,171,74,0.35)',
                    borderRadius: '4px',
                    padding: '1px 6px'
                  }}
                >
                  Auth Gateway
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '1px' }}>
                Enterprise Identity, RBAC Clearance & Tenant Access
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setIsAuthModalOpen(false)}
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              border: '1px solid #E2E8F0',
              background: '#FFFFFF',
              color: '#64748B',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#F1F5F9';
              e.currentTarget.style.color = '#0F172A';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#FFFFFF';
              e.currentTarget.style.color = '#64748B';
            }}
          >
            <X size={15} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #E2E8F0',
            background: '#FFFFFF',
            padding: '0 16px'
          }}
        >
          <button
            type="button"
            onClick={() => { setAuthModalTab('personas'); setErrorMsg(null); }}
            style={{
              flex: 1,
              padding: '11px 8px',
              border: 'none',
              borderBottom: authModalTab === 'personas' ? '2px solid #2563EB' : '2px solid transparent',
              background: 'transparent',
              color: authModalTab === 'personas' ? '#2563EB' : '#64748B',
              fontWeight: authModalTab === 'personas' ? 700 : 500,
              fontSize: '0.74rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '5px',
              transition: 'all 0.15s ease'
            }}
          >
            <Users size={13} />
            <span>Personas</span>
          </button>

          <button
            type="button"
            onClick={() => { setAuthModalTab('sso'); setErrorMsg(null); }}
            style={{
              flex: 1,
              padding: '11px 8px',
              border: 'none',
              borderBottom: authModalTab === 'sso' ? '2px solid #2563EB' : '2px solid transparent',
              background: 'transparent',
              color: authModalTab === 'sso' ? '#2563EB' : '#64748B',
              fontWeight: authModalTab === 'sso' ? 700 : 500,
              fontSize: '0.74rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '5px',
              transition: 'all 0.15s ease'
            }}
          >
            <Globe size={13} />
            <span>Enterprise SSO</span>
          </button>

          <button
            type="button"
            onClick={() => { setAuthModalTab('login'); setErrorMsg(null); }}
            style={{
              flex: 1,
              padding: '11px 8px',
              border: 'none',
              borderBottom: authModalTab === 'login' ? '2px solid #2563EB' : '2px solid transparent',
              background: 'transparent',
              color: authModalTab === 'login' ? '#2563EB' : '#64748B',
              fontWeight: authModalTab === 'login' ? 700 : 500,
              fontSize: '0.74rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '5px',
              transition: 'all 0.15s ease'
            }}
          >
            <Key size={13} />
            <span>Email</span>
          </button>

          <button
            type="button"
            onClick={() => { setAuthModalTab('register'); setErrorMsg(null); }}
            style={{
              flex: 1,
              padding: '11px 12px',
              border: 'none',
              borderBottom: authModalTab === 'register' ? '2px solid #2563EB' : '2px solid transparent',
              background: 'transparent',
              color: authModalTab === 'register' ? '#2563EB' : '#64748B',
              fontWeight: authModalTab === 'register' ? 700 : 500,
              fontSize: '0.78rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.15s ease'
            }}
          >
            <Building2 size={14} />
            <span>New Workspace</span>
          </button>
        </div>

        {/* Notifications */}
        {errorMsg && (
          <div
            style={{
              margin: '12px 20px 0 20px',
              padding: '10px 14px',
              borderRadius: '6px',
              backgroundColor: '#FEF2F2',
              border: '1px solid #FECACA',
              color: '#991B1B',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <AlertCircle size={15} style={{ flexShrink: 0 }} />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div
            style={{
              margin: '12px 20px 0 20px',
              padding: '10px 14px',
              borderRadius: '6px',
              backgroundColor: '#F0FDF4',
              border: '1px solid #BBF7D0',
              color: '#166534',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <CheckCircle2 size={15} style={{ flexShrink: 0 }} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Scrollable Body */}
        <div style={{ padding: '18px 22px', overflowY: 'auto', flex: 1 }}>

          {/* TAB 1: ONE-CLICK PERSONAS */}
          {authModalTab === 'personas' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>
                  Select Persona to Authenticate:
                </span>
                <span style={{ fontSize: '0.68rem', color: '#94A3B8', fontFamily: 'monospace' }}>
                  Atlan RBAC Matrix
                </span>
              </div>

              {personas.map((p) => {
                const badge = getRoleBadgeStyle(p.role);
                const isActive = currentUser?.id === p.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => loginAsPersona(p)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: isActive ? '1px solid #2563EB' : '1px solid #E2E8F0',
                      backgroundColor: isActive ? '#EFF6FF' : '#FFFFFF',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = '#F8FAFC';
                        e.currentTarget.style.borderColor = '#CBD5E1';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = '#FFFFFF';
                        e.currentTarget.style.borderColor = '#E2E8F0';
                      }
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <img
                        src={p.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${p.name}`}
                        alt={p.name}
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: '8px',
                          backgroundColor: '#F1F5F9',
                          border: '1px solid #E2E8F0',
                          objectFit: 'cover',
                          flexShrink: 0
                        }}
                      />
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0F172A' }}>
                            {p.name}
                          </span>
                          <span
                            style={{
                              fontSize: '0.62rem',
                              fontWeight: 700,
                              padding: '1px 5px',
                              borderRadius: '4px',
                              backgroundColor: badge.bg,
                              color: badge.color,
                              border: `1px solid ${badge.border}`
                            }}
                          >
                            {badge.label}
                          </span>
                          {isActive && (
                            <span style={{ fontSize: '0.65rem', color: '#16A34A', fontWeight: 600 }}>
                              ✓ Active
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '2px' }}>
                          {p.title || 'Enterprise Member'} • <span style={{ color: '#94A3B8' }}>{p.department || 'Governance'}</span>
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '2px', color: '#2563EB', fontSize: '0.74rem', fontWeight: 600 }}>
                      <span>Switch</span>
                      <ChevronRight size={14} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* TAB 2: ENTERPRISE SINGLE SIGN-ON & DOMAIN ROUTING */}
          {authModalTab === 'sso' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* Info banner */}
              <div
                style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  backgroundColor: '#EFF6FF',
                  border: '1px solid #BFDBFE',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px'
                }}
              >
                <Globe size={18} style={{ color: '#2563EB', flexShrink: 0, marginTop: '2px' }} />
                <div style={{ fontSize: '0.72rem', color: '#1E40AF', lineHeight: '1.4' }}>
                  <strong style={{ fontWeight: 600 }}>Zero-Config Corporate Tenant Routing:</strong> Enter your work email address. Trulin automatically detects your enterprise domain (e.g. <code>@ssfa.com</code>) and authenticates you directly into your organization's isolated workspace.
                </div>
              </div>

              {/* Form */}
              <form onSubmit={handleCorporateSSOSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Corporate Work Email
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type="email"
                      required
                      placeholder="e.g. elena.rostova@ssfa.com or alex@company.com"
                      value={ssoEmail}
                      onChange={(e) => setSsoEmail(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '8px 12px 8px 34px',
                        borderRadius: '6px',
                        border: '1px solid #CBD5E1',
                        fontSize: '0.80rem',
                        color: '#0F172A',
                        outline: 'none',
                        boxSizing: 'border-box'
                      }}
                    />
                    <Mail
                      size={15}
                      style={{
                        position: 'absolute',
                        left: '11px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        color: '#94A3B8'
                      }}
                    />
                  </div>
                </div>

                {/* Quick Domain Presets */}
                <div>
                  <span style={{ fontSize: '0.68rem', color: '#64748B', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Sample Enterprise Domains:
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {[
                      { domain: 'elena.rostova@ssfa.com', org: 'Trulin Trust Gateway', badge: 'Primary Workspace' },
                      { domain: 'sarah.chen@google.com', org: 'Google Workspace', badge: 'Cloud IdP' },
                      { domain: 'marcus.vance@microsoft.com', org: 'Microsoft Entra', badge: 'Azure AD' },
                      { domain: 'compliance@trulin-demo.ai', org: 'Audit Assurance', badge: 'Governance' }
                    ].map((item) => (
                      <button
                        key={item.domain}
                        type="button"
                        onClick={() => setSsoEmail(item.domain)}
                        style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          border: ssoEmail === item.domain ? '1px solid #2563EB' : '1px solid #E2E8F0',
                          backgroundColor: ssoEmail === item.domain ? '#EFF6FF' : '#F8FAFC',
                          color: ssoEmail === item.domain ? '#1D4ED8' : '#475569',
                          fontSize: '0.68rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        <Building size={11} />
                        <span>{item.domain}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Identity Provider Badges */}
                <div>
                  <span style={{ fontSize: '0.68rem', color: '#64748B', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Identity Provider:
                  </span>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px' }}>
                    {[
                      { id: 'google', name: 'Google', sub: 'OIDC 2.0' },
                      { id: 'microsoft', name: 'Microsoft', sub: 'Entra ID' },
                      { id: 'okta', name: 'Okta', sub: 'Workforce' }
                    ].map((p) => {
                      const isSelected = ssoProvider === p.id;
                      return (
                        <div
                          key={p.id}
                          onClick={() => setSsoProvider(p.id)}
                          style={{
                            padding: '6px 8px',
                            borderRadius: '6px',
                            border: isSelected ? '1px solid #2563EB' : '1px solid #E2E8F0',
                            backgroundColor: isSelected ? '#EFF6FF' : '#FFFFFF',
                            cursor: 'pointer',
                            textAlign: 'center',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          <div style={{ fontSize: '0.74rem', fontWeight: 600, color: isSelected ? '#1D4ED8' : '#334155' }}>
                            {p.name}
                          </div>
                          <div style={{ fontSize: '0.62rem', color: isSelected ? '#2563EB' : '#94A3B8' }}>
                            {p.sub}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    marginTop: '6px',
                    width: '100%',
                    padding: '9px 16px',
                    borderRadius: '6px',
                    backgroundColor: '#2563EB',
                    color: '#FFFFFF',
                    border: 'none',
                    fontSize: '0.80rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'background-color 0.15s ease'
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#1D4ED8'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#2563EB'; }}
                >
                  <Globe size={15} />
                  <span>{loading ? `Authenticating ${loadingAction}...` : 'Authenticate with Enterprise SSO'}</span>
                </button>
              </form>
            </div>
          )}

          {/* TAB 3: EMAIL / PASSWORD LOGIN */}
          {authModalTab === 'login' && (
            <form onSubmit={handleEmailLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Corporate Email
                </label>
                <div style={{ position: 'relative' }}>
                  <Mail size={15} style={{ position: 'absolute', left: '10px', top: '10px', color: '#94A3B8' }} />
                  <input
                    type="email"
                    required
                    placeholder="name@company.com"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px 8px 32px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.82rem',
                      color: '#0F172A',
                      outline: 'none',
                      backgroundColor: '#FFFFFF',
                      boxSizing: 'border-box'
                    }}
                    onFocus={(e) => { e.target.style.borderColor = '#2563EB'; }}
                    onBlur={(e) => { e.target.style.borderColor = '#CBD5E1'; }}
                  />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#334155' }}>
                    Password
                  </label>
                  <span
                    onClick={() => setLoginPassword('ContextTrust2026!')}
                    style={{ fontSize: '0.68rem', color: '#2563EB', cursor: 'pointer' }}
                    title="Click to fill default demo password"
                  >
                    Use default: ContextTrust2026!
                  </span>
                </div>
                <div style={{ position: 'relative' }}>
                  <Lock size={15} style={{ position: 'absolute', left: '10px', top: '10px', color: '#94A3B8' }} />
                  <input
                    type="password"
                    required
                    placeholder="••••••••••••"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px 8px 32px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.82rem',
                      color: '#0F172A',
                      outline: 'none',
                      backgroundColor: '#FFFFFF',
                      boxSizing: 'border-box'
                    }}
                    onFocus={(e) => { e.target.style.borderColor = '#2563EB'; }}
                    onBlur={(e) => { e.target.style.borderColor = '#CBD5E1'; }}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  marginTop: '6px',
                  width: '100%',
                  padding: '10px 16px',
                  borderRadius: '6px',
                  backgroundColor: '#2563EB',
                  color: '#FFFFFF',
                  border: 'none',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  transition: 'background-color 0.15s ease'
                }}
                onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#1D4ED8'; }}
                onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#2563EB'; }}
              >
                {loading ? (
                  <span>Signing in...</span>
                ) : (
                  <>
                    <span>Sign In with Enterprise Credentials</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>
          )}

          {/* TAB 3: NEW WORKSPACE REGISTRATION */}
          {authModalTab === 'register' && (
            <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Elena Rostova"
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.78rem',
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                    Organization *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="SSFA Holdings"
                    value={regOrgName}
                    onChange={(e) => setRegOrgName(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.78rem',
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                  Corporate Work Email *
                </label>
                <input
                  type="email"
                  required
                  placeholder="elena@ssfa.com"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.78rem',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                  Password *
                </label>
                <input
                  type="password"
                  required
                  placeholder="Minimum 6 characters"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.78rem',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                    Role Clearance
                  </label>
                  <select
                    value={regRole}
                    onChange={(e) => setRegRole(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.78rem',
                      outline: 'none',
                      backgroundColor: '#FFFFFF',
                      boxSizing: 'border-box'
                    }}
                  >
                    <option value="reviewer">Auditor / Reviewer</option>
                    <option value="data_owner">Data Steward / Owner</option>
                    <option value="admin">Administrator / CCO</option>
                    <option value="developer">AI Developer</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                    Department
                  </label>
                  <input
                    type="text"
                    placeholder="Risk & Governance"
                    value={regDept}
                    onChange={(e) => setRegDept(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.78rem',
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  marginTop: '8px',
                  width: '100%',
                  padding: '9px 16px',
                  borderRadius: '6px',
                  backgroundColor: '#059669',
                  color: '#FFFFFF',
                  border: 'none',
                  fontSize: '0.80rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease'
                }}
                onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#047857'; }}
                onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#059669'; }}
              >
                {loading ? 'Creating Workspace...' : 'Create Tenant Workspace & Sign In'}
              </button>
            </form>
          )}

        </div>

        {/* Modal Footer: SSO Federation */}
        <div
          style={{
            padding: '12px 22px 14px 22px',
            borderTop: '1px solid #E2E8F0',
            backgroundColor: '#F8FAFC',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.70rem', color: '#64748B', fontWeight: 500 }}>
              Enterprise Single Sign-On:
            </span>
            <span
              style={{
                fontSize: '0.62rem',
                fontFamily: 'monospace',
                color: '#2563EB',
                backgroundColor: '#EFF6FF',
                padding: '1px 6px',
                borderRadius: '4px',
                border: '1px solid #DBEAFE'
              }}
            >
              SAML 2.0 / OIDC
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <button
              type="button"
              disabled={loading}
              onClick={() => handleSSOClick('google')}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '7px 10px',
                borderRadius: '6px',
                border: '1px solid #CBD5E1',
                backgroundColor: loading && loadingAction === 'Google Workspace' ? '#EFF6FF' : '#FFFFFF',
                color: '#334155',
                fontSize: '0.74rem',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.75 : 1,
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#F1F5F9'; }}
              onMouseLeave={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#FFFFFF'; }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
              </svg>
              <span>{loading && loadingAction === 'Google Workspace' ? 'Connecting...' : 'Google Workspace'}</span>
            </button>

            <button
              type="button"
              disabled={loading}
              onClick={() => handleSSOClick('microsoft')}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '7px 10px',
                borderRadius: '6px',
                border: '1px solid #CBD5E1',
                backgroundColor: loading && loadingAction === 'Microsoft Entra ID' ? '#EFF6FF' : '#FFFFFF',
                color: '#334155',
                fontSize: '0.74rem',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.75 : 1,
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#F1F5F9'; }}
              onMouseLeave={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#FFFFFF'; }}
            >
              <svg width="15" height="15" viewBox="0 0 23 23" style={{ flexShrink: 0 }}>
                <path fill="#f35325" d="M1 1h10v10H1z"/>
                <path fill="#81bc06" d="M12 1h10v10H12z"/>
                <path fill="#05a6f0" d="M1 12h10v10H1z"/>
                <path fill="#ffba08" d="M12 12h10v10H12z"/>
              </svg>
              <span>{loading && loadingAction === 'Microsoft Entra ID' ? 'Connecting...' : 'Microsoft Entra ID'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
