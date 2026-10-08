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
  Sparkles,
  Zap,
  Globe,
  Check,
  ChevronRight,
  ShieldCheck,
  Building,
  Layers
} from 'lucide-react';
import { useAuth, DEFAULT_ENTERPRISE_PERSONAS } from '../context/AuthContext';

const CURATED_DEMO_PERSONAS = [
  {
    id: '55555555-5555-5555-5555-555555555555',
    name: 'Alex Vance',
    initials: 'AV',
    roleTag: 'AUDITOR',
    role: 'developer',
    title: 'Autonomous Systems Engineer',
    email: 'alex.vance@ssfa.com',
    desc: 'Autonomous Systems Engineer · alex.vance@ssfa.com',
    avatarBg: '#FFEDD5',
    avatarColor: '#C2410C',
    tagBg: '#FFEDD5',
    tagColor: '#C2410C',
    tagBorder: '#FED7AA'
  },
  {
    id: '44444444-4444-4444-4444-444444444444',
    name: 'Lead Risk Auditor',
    initials: 'LA',
    roleTag: 'AUDITOR',
    role: 'reviewer',
    title: 'Lead Risk Auditor',
    email: 'auditor@trulin-demo.ai',
    desc: 'Corporate SSO · auditor@trulin-demo.ai',
    avatarBg: '#FEF3C7',
    avatarColor: '#B45309',
    tagBg: '#FFEDD5',
    tagColor: '#C2410C',
    tagBorder: '#FED7AA'
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    name: 'Compliance Lead',
    initials: 'CL',
    roleTag: 'GOVERNANCE',
    role: 'admin',
    title: 'Chief Compliance Officer',
    email: 'compliance.lead@ssfa.com',
    desc: 'Enterprise Team Member · compliance.lead@ssfa.com',
    avatarBg: '#D1FAE5',
    avatarColor: '#047857',
    tagBg: '#FFEDD5',
    tagColor: '#C2410C',
    tagBorder: '#FED7AA'
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    name: 'Data Steward',
    initials: 'DS',
    roleTag: 'STEWARD',
    role: 'data_owner',
    title: 'Principal Data Steward',
    email: 'marcus.steward@ssfa.com',
    desc: 'Policy & Data Operations · marcus.steward@ssfa.com',
    avatarBg: '#EDE9FE',
    avatarColor: '#6D28D9',
    tagBg: '#FFEDD5',
    tagColor: '#C2410C',
    tagBorder: '#FED7AA'
  }
];

export default function AuthLandingView() {
  const {
    login,
    register,
    loginAsPersona,
    loginWithSSO,
    loginWithCorporateDomain,
    personas,
  } = useAuth();

  const [activeTab, setActiveTab] = useState('personas'); // 'personas' | 'login' | 'register' | 'sso'
  
  // Login form state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [keepSignedIn, setKeepSignedIn] = useState(true);

  // Register form state
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regOrgName, setRegOrgName] = useState('');
  const [regRole, setRegRole] = useState('admin');
  const [regDept, setRegDept] = useState('AI Operations & Governance');

  // SSO state
  const [ssoEmail, setSsoEmail] = useState('');

  // UI state
  const [loading, setLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const demoPersonas = CURATED_DEMO_PERSONAS;

  const handleEmailLogin = async (e) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) {
      setErrorMsg('Please enter both email and password.');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction('Authenticating credentials...');
    try {
      await login(loginEmail.trim(), loginPassword);
      setSuccessMsg('Authentication successful! Loading workspace...');
    } catch (err) {
      setErrorMsg(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regEmail || !regPassword || !regName) {
      setErrorMsg('Please provide your name, email, and password.');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction('Creating account and provisioning workspace...');
    try {
      await register({
        name: regName.trim(),
        email: regEmail.trim().toLowerCase(),
        password: regPassword,
        organization_name: regOrgName.trim() || undefined,
        role: regRole,
        department: regDept,
        title: regRole === 'admin' ? 'Chief Compliance Officer' : regRole === 'data_owner' ? 'Principal Data Steward' : 'Lead Risk Auditor'
      });
      setSuccessMsg('Account registered successfully! Welcome to Trulin.');
    } catch (err) {
      setErrorMsg(err.message || 'Registration failed. Please check your inputs.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  const handlePersonaSelect = async (persona) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction(`Signing in as ${persona.name}...`);
    try {
      await loginAsPersona(persona);
      setSuccessMsg(`Authenticated as ${persona.name}!`);
    } catch (err) {
      setErrorMsg(err.message || 'Persona quick-login failed.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  const handleSSO = async (provider) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction(provider === 'google' ? 'Google Workspace / Gmail SSO...' : provider === 'microsoft' ? 'Microsoft Entra ID...' : 'Okta Identity...');
    try {
      await loginWithSSO(provider);
      setSuccessMsg(`Signed in via ${provider.toUpperCase()} SSO!`);
    } catch (err) {
      setErrorMsg(err.message || 'SSO authentication failed.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  const handleCorporateSSOSubmit = async (e) => {
    e.preventDefault();
    if (!ssoEmail || !ssoEmail.includes('@')) {
      setErrorMsg('Please enter a valid corporate or personal email address.');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction('Resolving domain & tenant credentials...');
    try {
      await loginWithCorporateDomain(ssoEmail);
      setSuccessMsg(`Authenticated via domain for ${ssoEmail}!`);
    } catch (err) {
      setErrorMsg(err.message || 'Domain sign-in failed.');
    } finally {
      setLoading(false);
      setLoadingAction('');
    }
  };

  const fillDemoLogin = (email, password = 'password123') => {
    setLoginEmail(email);
    setLoginPassword(password);
    setErrorMsg(null);
  };

  const getPersonaBadge = (role) => {
    switch (role?.toLowerCase()) {
      case 'admin':
        return { label: 'ADMIN / CCO', bg: '#ECFDF5', color: '#047857', border: '#A7F3D0', avatarBg: '#D1FAE5', avatarColor: '#065F46' };
      case 'data_owner':
        return { label: 'STEWARD', bg: '#EFF6FF', color: '#1D4ED8', border: '#BFDBFE', avatarBg: '#DBEAFE', avatarColor: '#1E40AF' };
      case 'reviewer':
        return { label: 'AUDITOR', bg: '#FFF7ED', color: '#C2410C', border: '#FED7AA', avatarBg: '#FFEDD5', avatarColor: '#9A3412' };
      case 'developer':
        return { label: 'ENGINEER', bg: '#FDF4FF', color: '#86198F', border: '#F5D0FE', avatarBg: '#FAE8FF', avatarColor: '#701A75' };
      default:
        return { label: 'GOVERNANCE', bg: '#F1F5F9', color: '#475569', border: '#E2E8F0', avatarBg: '#E2E8F0', avatarColor: '#334155' };
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100vw',
        backgroundColor: '#F7F6F2',
        backgroundImage: 'linear-gradient(to right, rgba(0,0,0,0.035) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,0,0,0.035) 1px, transparent 1px)',
        backgroundSize: '24px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        boxSizing: 'border-box',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
      }}
    >
      {/* Central Floating Portal Card */}
      <div
        style={{
          width: '100%',
          maxWidth: '1040px',
          backgroundColor: '#FFFFFF',
          borderRadius: '20px',
          border: '1px solid #EBE7DE',
          boxShadow: '0 20px 60px -15px rgba(0, 0, 0, 0.07), 0 0 1px 1px rgba(0,0,0,0.02)',
          display: 'grid',
          gridTemplateColumns: '375px 1fr',
          overflow: 'hidden'
        }}
      >
        {/* ========================================================= */}
        {/* LEFT COLUMN: BRAND HERO (Champagne Cream Gradient)        */}
        {/* ========================================================= */}
        <div
          style={{
            background: 'linear-gradient(180deg, #FFF9F3 0%, #FFF4E8 100%)',
            borderRight: '1px solid #F0E8DC',
            padding: '36px 32px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            boxSizing: 'border-box'
          }}
        >
          <div>
            {/* Top Brand Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '32px' }}>
              <img
                src="/Trulin-Main-NoBg.png"
                alt="Trulin."
                style={{ height: '28px', maxWidth: '130px', objectFit: 'contain' }}
              />
              <span
                style={{
                  fontSize: '0.64rem',
                  fontWeight: 700,
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                  padding: '3px 8px',
                  borderRadius: '12px',
                  backgroundColor: '#FFF7ED',
                  color: '#EA580C',
                  border: '1px solid #FED7AA'
                }}
              >
                Trust Layer AI
              </span>
            </div>

            {/* Overline Tag */}
            <div
              style={{
                fontSize: '0.67rem',
                fontWeight: 700,
                letterSpacing: '0.07em',
                textTransform: 'uppercase',
                color: '#EA580C',
                marginBottom: '10px'
              }}
            >
              — Enterprise Intelligence, Verified
            </div>

            {/* Editorial Serif Heading */}
            <h1
              style={{
                fontFamily: "'Playfair Display', 'Newsreader', Georgia, serif",
                fontSize: '2.45rem',
                lineHeight: 1.15,
                fontWeight: 800,
                color: '#111827',
                margin: '0 0 14px 0',
                letterSpacing: '-0.02em'
              }}
            >
              Trust your AI.<br />
              <span
                style={{
                  fontStyle: 'italic',
                  color: '#EA580C',
                  fontWeight: 700
                }}
              >
                Prove every decision.
              </span>
            </h1>

            {/* Subparagraph */}
            <p
              style={{
                fontSize: '0.84rem',
                color: '#6B7280',
                lineHeight: 1.6,
                margin: '0 0 28px 0'
              }}
            >
              The enterprise governance layer that turns complex AI activity into clear, traceable, and defensible outcomes.
            </p>

            {/* 3 Value Propositions */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Value 1 */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    backgroundColor: '#FFEDD5',
                    color: '#EA580C',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}
                >
                  <Shield size={16} strokeWidth={2} />
                </div>
                <div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#111827' }}>
                    Cryptographic trust
                  </div>
                  <div style={{ fontSize: '0.74rem', color: '#6B7280', marginTop: '1px', lineHeight: 1.4 }}>
                    Every claim, document, and decision is verified with immutable provenance.
                  </div>
                </div>
              </div>

              {/* Value 2 */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    backgroundColor: '#FFEDD5',
                    color: '#EA580C',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}
                >
                  <Zap size={16} strokeWidth={2} />
                </div>
                <div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#111827' }}>
                    Built for modern teams
                  </div>
                  <div style={{ fontSize: '0.74rem', color: '#6B7280', marginTop: '1px', lineHeight: 1.4 }}>
                    Sign in personally or connect your organization through secure federation.
                  </div>
                </div>
              </div>

              {/* Value 3 */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    backgroundColor: '#FFEDD5',
                    color: '#EA580C',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}
                >
                  <Users size={16} strokeWidth={2} />
                </div>
                <div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#111827' }}>
                    Role-based by design
                  </div>
                  <div style={{ fontSize: '0.74rem', color: '#6B7280', marginTop: '1px', lineHeight: 1.4 }}>
                    Explore tailored workspaces for governance, data, and audit leaders.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Security Footer */}
          <div
            style={{
              paddingTop: '20px',
              marginTop: '28px',
              borderTop: '1px solid #F0E8DC',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.7rem',
              color: '#6B7280'
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Lock size={12} color="#6B7280" />
              <span>TLS 1.3 & JWT encrypted</span>
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10B981' }} />
              <span>All systems operational</span>
            </span>
          </div>
        </div>

        {/* ========================================================= */}
        {/* RIGHT COLUMN: INTERACTIVE AUTH PORTAL                    */}
        {/* ========================================================= */}
        <div
          style={{
            backgroundColor: '#FFFFFF',
            padding: '36px 40px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            boxSizing: 'border-box'
          }}
        >
          <div>
            {/* Top Row: Tag & Protected Badge */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
              <span
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  letterSpacing: '0.07em',
                  textTransform: 'uppercase',
                  color: '#EA580C'
                }}
              >
                Secure Access Portal
              </span>
              <span
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.68rem',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: '12px',
                  backgroundColor: '#ECFDF5',
                  color: '#047857',
                  border: '1px solid #A7F3D0'
                }}
              >
                <ShieldCheck size={12} color="#047857" />
                <span>Protected</span>
              </span>
            </div>

            {/* Portal Headline */}
            <h2
              style={{
                fontFamily: "'Playfair Display', 'Newsreader', Georgia, serif",
                fontSize: '1.75rem',
                fontWeight: 700,
                color: '#111827',
                margin: '2px 0 2px 0'
              }}
            >
              Welcome to Trulin
            </h2>

            <p style={{ fontSize: '0.8rem', color: '#6B7280', margin: '0 0 20px 0' }}>
              Choose how you'd like to enter your trust workspace.
            </p>

            {/* 4 Segmented Pills Tab Switcher */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '4px',
                backgroundColor: '#F3F4F6',
                padding: '4px',
                borderRadius: '10px',
                marginBottom: '22px'
              }}
            >
              <button
                type="button"
                onClick={() => { setActiveTab('personas'); setErrorMsg(null); }}
                style={{
                  padding: '7px 4px',
                  borderRadius: '8px',
                  border: activeTab === 'personas' ? '1.5px solid #111827' : '1.5px solid transparent',
                  backgroundColor: activeTab === 'personas' ? '#FFFFFF' : 'transparent',
                  color: activeTab === 'personas' ? '#111827' : '#6B7280',
                  fontWeight: activeTab === 'personas' ? 700 : 500,
                  fontSize: '0.74rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '5px',
                  boxShadow: activeTab === 'personas' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                <Sparkles size={12} color={activeTab === 'personas' ? '#EA580C' : '#6B7280'} />
                <span>Demo access</span>
              </button>

              <button
                type="button"
                onClick={() => { setActiveTab('login'); setErrorMsg(null); }}
                style={{
                  padding: '7px 4px',
                  borderRadius: '8px',
                  border: activeTab === 'login' ? '1.5px solid #111827' : '1.5px solid transparent',
                  backgroundColor: activeTab === 'login' ? '#FFFFFF' : 'transparent',
                  color: activeTab === 'login' ? '#111827' : '#6B7280',
                  fontWeight: activeTab === 'login' ? 700 : 500,
                  fontSize: '0.74rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '5px',
                  boxShadow: activeTab === 'login' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                <Key size={12} color={activeTab === 'login' ? '#EA580C' : '#6B7280'} />
                <span>Sign In</span>
              </button>

              <button
                type="button"
                onClick={() => { setActiveTab('register'); setErrorMsg(null); }}
                style={{
                  padding: '7px 4px',
                  borderRadius: '8px',
                  border: activeTab === 'register' ? '1.5px solid #111827' : '1.5px solid transparent',
                  backgroundColor: activeTab === 'register' ? '#FFFFFF' : 'transparent',
                  color: activeTab === 'register' ? '#111827' : '#6B7280',
                  fontWeight: activeTab === 'register' ? 700 : 500,
                  fontSize: '0.74rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '5px',
                  boxShadow: activeTab === 'register' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                <Users size={12} color={activeTab === 'register' ? '#EA580C' : '#6B7280'} />
                <span>Create account</span>
              </button>

              <button
                type="button"
                onClick={() => { setActiveTab('sso'); setErrorMsg(null); }}
                style={{
                  padding: '7px 4px',
                  borderRadius: '8px',
                  border: activeTab === 'sso' ? '1.5px solid #111827' : '1.5px solid transparent',
                  backgroundColor: activeTab === 'sso' ? '#FFFFFF' : 'transparent',
                  color: activeTab === 'sso' ? '#111827' : '#6B7280',
                  fontWeight: activeTab === 'sso' ? 700 : 500,
                  fontSize: '0.74rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '5px',
                  boxShadow: activeTab === 'sso' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                <Globe size={12} color={activeTab === 'sso' ? '#EA580C' : '#6B7280'} />
                <span>SSO</span>
              </button>
            </div>

            {/* Error & Success Feedback Alerts */}
            {errorMsg && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  backgroundColor: '#FEF2F2',
                  border: '1px solid #FECACA',
                  color: '#B91C1C',
                  fontSize: '0.78rem',
                  marginBottom: '14px'
                }}
              >
                <AlertCircle size={15} color="#DC2626" style={{ flexShrink: 0 }} />
                <span>{errorMsg}</span>
              </div>
            )}

            {successMsg && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  backgroundColor: '#ECFDF5',
                  border: '1px solid #A7F3D0',
                  color: '#047857',
                  fontSize: '0.78rem',
                  marginBottom: '14px'
                }}
              >
                <CheckCircle2 size={15} color="#10B981" style={{ flexShrink: 0 }} />
                <span>{successMsg}</span>
              </div>
            )}

            {/* ========================================================= */}
            {/* TAB 1: DEMO ACCESS (Choose a demo workspace)              */}
            {/* ========================================================= */}
            {activeTab === 'personas' && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
                  <div>
                    <span style={{ fontSize: '0.64rem', fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: '#EA580C' }}>
                      Explore Instantly
                    </span>
                    <h3 style={{ fontFamily: "'Playfair Display', 'Newsreader', Georgia, serif", fontSize: '1.28rem', fontWeight: 700, color: '#111827', margin: '2px 0 2px 0' }}>
                      Choose a demo workspace
                    </h3>
                  </div>
                  <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#C2410C', backgroundColor: '#FFEDD5', border: '1px solid #FED7AA', padding: '2px 8px', borderRadius: '10px' }}>
                    {demoPersonas.length} roles available
                  </span>
                </div>
                <p style={{ fontSize: '0.76rem', color: '#6B7280', margin: '0 0 12px 0' }}>
                  Experience role-based governance. No password needed.
                </p>

                {/* Persona Cards List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {demoPersonas.map((p) => {
                    return (
                      <button
                        key={p.id || p.email}
                        type="button"
                        disabled={loading}
                        onClick={() => handlePersonaSelect(p)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '10px 14px',
                          backgroundColor: '#FFFFFF',
                          borderRadius: '10px',
                          border: '1px solid #E5E7EB',
                          cursor: loading ? 'not-allowed' : 'pointer',
                          textAlign: 'left',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={(e) => {
                          if (!loading) {
                            e.currentTarget.style.borderColor = '#FDBA74';
                            e.currentTarget.style.backgroundColor = '#FFFBF5';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!loading) {
                            e.currentTarget.style.borderColor = '#E5E7EB';
                            e.currentTarget.style.backgroundColor = '#FFFFFF';
                          }
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div
                            style={{
                              width: '32px',
                              height: '32px',
                              borderRadius: '8px',
                              backgroundColor: p.avatarBg,
                              color: p.avatarColor,
                              fontWeight: 700,
                              fontSize: '0.78rem',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              flexShrink: 0
                            }}
                          >
                            {p.initials}
                          </div>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#111827' }}>{p.name}</span>
                              <span
                                style={{
                                  fontSize: '0.58rem',
                                  fontWeight: 700,
                                  letterSpacing: '0.04em',
                                  padding: '1px 5px',
                                  borderRadius: '4px',
                                  backgroundColor: p.tagBg,
                                  color: p.tagColor,
                                  border: `1px solid ${p.tagBorder}`
                                }}
                              >
                                {p.roleTag}
                              </span>
                            </div>
                            <div style={{ fontSize: '0.7rem', color: '#6B7280', marginTop: '1px' }}>
                              {p.desc}
                            </div>
                          </div>
                        </div>

                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '3px',
                            fontSize: '0.74rem',
                            fontWeight: 700,
                            color: '#EA580C'
                          }}
                        >
                          <span>Launch</span>
                          <ChevronRight size={13} />
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.7rem', color: '#6B7280', marginTop: '12px' }}>
                  <ShieldCheck size={12} color="#10B981" />
                  <span>Demo workspaces are isolated and reset after every session.</span>
                </div>
              </div>
            )}

            {/* ========================================================= */}
            {/* TAB 2: SIGN IN TO YOUR WORKSPACE                          */}
            {/* ========================================================= */}
            {activeTab === 'login' && (
              <form onSubmit={handleEmailLogin}>
                <div style={{ marginBottom: '2px' }}>
                  <span style={{ fontSize: '0.64rem', fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: '#EA580C' }}>
                    Good to See You
                  </span>
                  <h3 style={{ fontFamily: "'Playfair Display', 'Newsreader', Georgia, serif", fontSize: '1.28rem', fontWeight: 700, color: '#111827', margin: '2px 0 2px 0' }}>
                    Sign in to your workspace
                  </h3>
                </div>
                <p style={{ fontSize: '0.76rem', color: '#6B7280', margin: '0 0 14px 0' }}>
                  Use your work email or personal Gmail account.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, color: '#374151', marginBottom: '4px' }}>
                      Email address
                    </label>
                    <div style={{ position: 'relative' }}>
                      <Mail size={15} style={{ position: 'absolute', left: '12px', top: '11px', color: '#9CA3AF' }} />
                      <input
                        type="email"
                        value={loginEmail}
                        onChange={(e) => setLoginEmail(e.target.value)}
                        placeholder="name@company.com"
                        required
                        style={{
                          width: '100%',
                          padding: '9px 12px 9px 36px',
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #D1D5DB',
                          borderRadius: '8px',
                          color: '#111827',
                          fontSize: '0.82rem',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 600, color: '#374151', marginBottom: '4px' }}>
                      Password
                    </label>
                    <div style={{ position: 'relative' }}>
                      <Lock size={15} style={{ position: 'absolute', left: '12px', top: '11px', color: '#9CA3AF' }} />
                      <input
                        type="password"
                        value={loginPassword}
                        onChange={(e) => setLoginPassword(e.target.value)}
                        placeholder="Enter your password"
                        required
                        style={{
                          width: '100%',
                          padding: '9px 12px 9px 36px',
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #D1D5DB',
                          borderRadius: '8px',
                          color: '#111827',
                          fontSize: '0.82rem',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.74rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#6B7280', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={keepSignedIn}
                        onChange={(e) => setKeepSignedIn(e.target.checked)}
                        style={{ accentColor: '#EA580C' }}
                      />
                      <span>Keep me signed in</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => fillDemoLogin('sarah.chen@ssfa.com')}
                      style={{ background: 'none', border: 'none', color: '#EA580C', fontWeight: 600, cursor: 'pointer', padding: 0 }}
                    >
                      Forgot password?
                    </button>
                  </div>

                  {/* Quick Fill Chips */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '7px 10px',
                      borderRadius: '8px',
                      backgroundColor: '#F9FAFB',
                      border: '1px solid #E5E7EB'
                    }}
                  >
                    <span style={{ fontSize: '0.7rem', color: '#6B7280', fontWeight: 500 }}>Quick fill:</span>
                    <button
                      type="button"
                      onClick={() => fillDemoLogin('sarah.chen@ssfa.com')}
                      style={{
                        fontSize: '0.68rem',
                        color: '#374151',
                        backgroundColor: '#FFFFFF',
                        border: '1px solid #D1D5DB',
                        borderRadius: '4px',
                        padding: '2px 7px',
                        cursor: 'pointer',
                        fontWeight: 600
                      }}
                    >
                      Admin
                    </button>
                    <button
                      type="button"
                      onClick={() => fillDemoLogin('marcus.vance@ssfa.com')}
                      style={{
                        fontSize: '0.68rem',
                        color: '#374151',
                        backgroundColor: '#FFFFFF',
                        border: '1px solid #D1D5DB',
                        borderRadius: '4px',
                        padding: '2px 7px',
                        cursor: 'pointer',
                        fontWeight: 600
                      }}
                    >
                      Steward
                    </button>
                    <button
                      type="button"
                      onClick={() => fillDemoLogin('demo@gmail.com')}
                      style={{
                        fontSize: '0.68rem',
                        color: '#374151',
                        backgroundColor: '#FFFFFF',
                        border: '1px solid #D1D5DB',
                        borderRadius: '4px',
                        padding: '2px 7px',
                        cursor: 'pointer',
                        fontWeight: 600
                      }}
                    >
                      Gmail demo
                    </button>
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={loading}
                    style={{
                      marginTop: '4px',
                      padding: '11px',
                      borderRadius: '8px',
                      border: 'none',
                      backgroundColor: '#F95716',
                      color: '#FFFFFF',
                      fontWeight: 700,
                      fontSize: '0.84rem',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      boxShadow: '0 4px 12px rgba(249, 87, 22, 0.3)',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {loading ? (
                      <span>{loadingAction || 'Signing in...'}</span>
                    ) : (
                      <>
                        <span>Sign in securely</span>
                        <ArrowRight size={15} />
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}

            {/* ========================================================= */}
            {/* TAB 3: CREATE YOUR WORKSPACE                              */}
            {/* ========================================================= */}
            {activeTab === 'register' && (
              <form onSubmit={handleRegister}>
                <div style={{ marginBottom: '2px' }}>
                  <span style={{ fontSize: '0.64rem', fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: '#EA580C' }}>
                    Start Building Trust
                  </span>
                  <h3 style={{ fontFamily: "'Playfair Display', 'Newsreader', Georgia, serif", fontSize: '1.28rem', fontWeight: 700, color: '#111827', margin: '2px 0 2px 0' }}>
                    Create your workspace
                  </h3>
                </div>
                <p style={{ fontSize: '0.76rem', color: '#6B7280', margin: '0 0 12px 0' }}>
                  Set up your governance environment in under a minute.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {/* Row 1: Full name & Email */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#374151', marginBottom: '3px' }}>
                        Full name
                      </label>
                      <input
                        type="text"
                        value={regName}
                        onChange={(e) => setRegName(e.target.value)}
                        placeholder="e.g. Alex Rivera"
                        required
                        style={{
                          width: '100%',
                          padding: '8px 10px',
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #D1D5DB',
                          borderRadius: '8px',
                          color: '#111827',
                          fontSize: '0.8rem',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#374151', marginBottom: '3px' }}>
                        Email address
                      </label>
                      <input
                        type="email"
                        value={regEmail}
                        onChange={(e) => setRegEmail(e.target.value)}
                        placeholder="name@company.com"
                        required
                        style={{
                          width: '100%',
                          padding: '8px 10px',
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #D1D5DB',
                          borderRadius: '8px',
                          color: '#111827',
                          fontSize: '0.8rem',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>
                  </div>

                  {/* Row 2: Password & Organization */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#374151', marginBottom: '3px' }}>
                        Password
                      </label>
                      <input
                        type="password"
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        placeholder="At least 6 characters"
                        required
                        style={{
                          width: '100%',
                          padding: '8px 10px',
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #D1D5DB',
                          borderRadius: '8px',
                          color: '#111827',
                          fontSize: '0.8rem',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#374151', marginBottom: '3px' }}>
                        Organization
                      </label>
                      <input
                        type="text"
                        value={regOrgName}
                        onChange={(e) => setRegOrgName(e.target.value)}
                        placeholder="Your company (optional)"
                        style={{
                          width: '100%',
                          padding: '8px 10px',
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #D1D5DB',
                          borderRadius: '8px',
                          color: '#111827',
                          fontSize: '0.8rem',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>
                  </div>

                  {/* Row 3: Role & Department */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#374151', marginBottom: '3px' }}>
                        Assigned role
                      </label>
                      <select
                        value={regRole}
                        onChange={(e) => setRegRole(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '8px 10px',
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #D1D5DB',
                          borderRadius: '8px',
                          color: '#111827',
                          fontSize: '0.8rem',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      >
                        <option value="admin">Administrator / CCO</option>
                        <option value="data_owner">Data Steward</option>
                        <option value="reviewer">Risk Auditor</option>
                        <option value="developer">Systems Engineer</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: '#374151', marginBottom: '3px' }}>
                        Department
                      </label>
                      <input
                        type="text"
                        value={regDept}
                        onChange={(e) => setRegDept(e.target.value)}
                        placeholder="AI Operations & Governance"
                        style={{
                          width: '100%',
                          padding: '8px 10px',
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #D1D5DB',
                          borderRadius: '8px',
                          color: '#111827',
                          fontSize: '0.8rem',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={loading}
                    style={{
                      marginTop: '4px',
                      padding: '11px',
                      borderRadius: '8px',
                      border: 'none',
                      backgroundColor: '#F95716',
                      color: '#FFFFFF',
                      fontWeight: 700,
                      fontSize: '0.84rem',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      boxShadow: '0 4px 12px rgba(249, 87, 22, 0.3)',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {loading ? (
                      <span>{loadingAction || 'Creating account...'}</span>
                    ) : (
                      <>
                        <span>Create account & enter workspace</span>
                        <ArrowRight size={15} />
                      </>
                    )}
                  </button>

                  <div style={{ fontSize: '0.68rem', color: '#9CA3AF', textAlign: 'center', marginTop: '2px' }}>
                    By continuing, you agree to Trulin's Terms and Privacy Policy.
                  </div>
                </div>
              </form>
            )}

            {/* ========================================================= */}
            {/* TAB 4: CONTINUE WITH IDENTITY PROVIDER (SSO)             */}
            {/* ========================================================= */}
            {activeTab === 'sso' && (
              <div>
                <div style={{ marginBottom: '2px' }}>
                  <span style={{ fontSize: '0.64rem', fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: '#EA580C' }}>
                    Enterprise Access
                  </span>
                  <h3 style={{ fontFamily: "'Playfair Display', 'Newsreader', Georgia, serif", fontSize: '1.28rem', fontWeight: 700, color: '#111827', margin: '2px 0 2px 0' }}>
                    Continue with your identity provider
                  </h3>
                </div>
                <p style={{ fontSize: '0.76rem', color: '#6B7280', margin: '0 0 14px 0' }}>
                  Authenticate with your organization's existing credentials.
                </p>

                {/* 3 SSO Provider Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '16px' }}>
                  {/* Google */}
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => handleSSO('google')}
                    style={{
                      padding: '12px 10px',
                      borderRadius: '10px',
                      backgroundColor: '#FFFFFF',
                      border: '1px solid #E5E7EB',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      textAlign: 'left',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#FDBA74'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#E5E7EB'; }}
                  >
                    <div style={{ width: '26px', height: '26px', borderRadius: '6px', backgroundColor: '#FFEDD5', color: '#EA580C', fontWeight: 800, fontSize: '0.78rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      G
                    </div>
                    <div style={{ overflow: 'hidden', flex: 1 }}>
                      <div style={{ fontSize: '0.76rem', fontWeight: 700, color: '#111827', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Google Workspace</div>
                      <div style={{ fontSize: '0.66rem', color: '#9CA3AF' }}>Continue securely &gt;</div>
                    </div>
                  </button>

                  {/* Microsoft */}
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => handleSSO('microsoft')}
                    style={{
                      padding: '12px 10px',
                      borderRadius: '10px',
                      backgroundColor: '#FFFFFF',
                      border: '1px solid #E5E7EB',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      textAlign: 'left',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#93C5FD'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#E5E7EB'; }}
                  >
                    <div style={{ width: '26px', height: '26px', borderRadius: '6px', backgroundColor: '#DBEAFE', color: '#1D4ED8', fontWeight: 800, fontSize: '0.78rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      M
                    </div>
                    <div style={{ overflow: 'hidden', flex: 1 }}>
                      <div style={{ fontSize: '0.76rem', fontWeight: 700, color: '#111827', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Microsoft Entra</div>
                      <div style={{ fontSize: '0.66rem', color: '#9CA3AF' }}>Continue securely &gt;</div>
                    </div>
                  </button>

                  {/* Okta */}
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => handleSSO('okta')}
                    style={{
                      padding: '12px 10px',
                      borderRadius: '10px',
                      backgroundColor: '#FFFFFF',
                      border: '1px solid #E5E7EB',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      textAlign: 'left',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#A7F3D0'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#E5E7EB'; }}
                  >
                    <div style={{ width: '26px', height: '26px', borderRadius: '6px', backgroundColor: '#D1FAE5', color: '#047857', fontWeight: 800, fontSize: '0.78rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      O
                    </div>
                    <div style={{ overflow: 'hidden', flex: 1 }}>
                      <div style={{ fontSize: '0.76rem', fontWeight: 700, color: '#111827', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Okta Identity</div>
                      <div style={{ fontSize: '0.66rem', color: '#9CA3AF' }}>Continue securely &gt;</div>
                    </div>
                  </button>
                </div>

                {/* Divider */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '14px 0' }}>
                  <div style={{ flex: 1, height: '1px', backgroundColor: '#E5E7EB' }} />
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#9CA3AF', letterSpacing: '0.06em' }}>OR USE DOMAIN ROUTING</span>
                  <div style={{ flex: 1, height: '1px', backgroundColor: '#E5E7EB' }} />
                </div>

                {/* Domain Input */}
                <form onSubmit={handleCorporateSSOSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.72rem', fontWeight: 600, color: '#374151' }}>
                    Corporate email or domain
                  </label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <div style={{ position: 'relative', flex: 1 }}>
                      <Globe size={15} style={{ position: 'absolute', left: '12px', top: '10px', color: '#9CA3AF' }} />
                      <input
                        type="email"
                        value={ssoEmail}
                        onChange={(e) => setSsoEmail(e.target.value)}
                        placeholder="name@company.com"
                        required
                        style={{
                          width: '100%',
                          padding: '8px 12px 8px 36px',
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #D1D5DB',
                          borderRadius: '8px',
                          color: '#111827',
                          fontSize: '0.8rem',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={loading}
                      style={{
                        padding: '8px 16px',
                        borderRadius: '8px',
                        border: '1px solid #EA580C',
                        backgroundColor: '#FFFFFF',
                        color: '#EA580C',
                        fontWeight: 700,
                        fontSize: '0.78rem',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        whiteSpace: 'nowrap',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      <span>Authenticate</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>
                </form>

                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.7rem', color: '#6B7280', marginTop: '14px' }}>
                  <ShieldCheck size={12} color="#10B981" />
                  <span>SAML 2.0 and OIDC compatible. Credentials never touch Trulin.</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
