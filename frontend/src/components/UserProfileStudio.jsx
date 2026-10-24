import React, { useState, useEffect } from 'react';
import {
  User,
  Building2,
  FolderGit2,
  Shield,
  ShieldCheck,
  Check,
  ExternalLink,
  Plus,
  Settings,
  Mail,
  Key,
  Calendar,
  Lock,
  ArrowRight,
  Layers,
  Sparkles,
  LogOut
} from 'lucide-react';

export default function UserProfileStudio({
  activeOrg,
  organizations = [],
  onSwitchOrg,
  activeWorkspace,
  workspaces = [],
  onSwitchWorkspace,
  activePersona,
  personas = [],
  onSelectPersona,
  effectiveRole,
  roleMetadata,
  onOpenRegisterOrg,
  onOpenOrgSettings,
  onLaunchSetupWizard,
  onLogout,
  showToast,
  initialSubSection = 'companies',
  onSubSectionChange
}) {
  const [switchingOrgId, setSwitchingOrgId] = useState(null);
  const [activeSubSection, setActiveSubSection] = useState(initialSubSection || 'companies'); // 'companies' | 'security' | 'personas'

  useEffect(() => {
    if (initialSubSection) {
      setActiveSubSection(initialSubSection);
    }
  }, [initialSubSection]);

  const handleSubSectionClick = (sub) => {
    setActiveSubSection(sub);
    onSubSectionChange?.(sub);
  };

  const handleSelectCompany = async (org) => {
    if (org.id === activeOrg?.id) return;
    setSwitchingOrgId(org.id);
    try {
      if (onSwitchOrg) {
        await onSwitchOrg(org);
      }
    } finally {
      setTimeout(() => setSwitchingOrgId(null), 300);
    }
  };

  const userInitials = activePersona?.name
    ? activePersona.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
    : 'SC';

  const cleanOrgs = (organizations && organizations.length > 0)
    ? organizations.filter(o => 
        !o.name.includes('Auto Resolve') && 
        !o.name.includes('Default Org')
      )
    : (activeOrg ? [activeOrg] : []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', maxWidth: '1280px', margin: '0 auto' }}>
      {/* 1. Profile Header Hero */}
      <div style={{
        padding: '10px 4px 16px 4px',
        background: 'transparent',
        border: 'none',
        borderRadius: '0'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
            {/* Initials Avatar */}
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #FFAB4A 0%, #EA580C 100%)',
              color: '#1A1207',
              fontSize: '1.4rem',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 16px rgba(255, 171, 74, 0.35)',
              flexShrink: 0
            }}>
              {userInitials}
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <h1 style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-main)', margin: 0, letterSpacing: '-0.02em' }}>
                  {activePersona?.name || 'Sarah Chen'}
                </h1>
                <span className="badge badge-verified" style={{ fontSize: '0.68rem', padding: '2px 8px' }}>
                  {effectiveRole?.toUpperCase() || 'ADMIN'}
                </span>
                <span className="badge" style={{
                  fontSize: '0.65rem',
                  padding: '2px 8px',
                  background: 'rgba(22, 163, 74, 0.12)',
                  color: '#15803D',
                  border: '1px solid rgba(22, 163, 74, 0.3)',
                  fontWeight: 700
                }}>
                  ● SoD Enforced
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '6px', fontSize: '0.82rem', color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                  <Shield size={13} style={{ color: 'var(--primary-dark)' }} />
                  {roleMetadata?.title || 'Chief Compliance Officer'}
                </span>
                <span>•</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                  <Building2 size={13} style={{ color: 'var(--text-muted)' }} />
                  {activeOrg?.name || 'Default Organization'}
                </span>
                <span>•</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                  <Mail size={13} style={{ color: 'var(--text-muted)' }} />
                  {activePersona?.email || `${activePersona?.name ? activePersona.name.toLowerCase().replace(/\s+/g, '.') : 'admin'}@${activeOrg?.slug || 'company'}.com`}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Profile Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <img 
              src="/Trulin-Main-NoBg.png" 
              alt="Trulin" 
              style={{ height: '26px', maxWidth: '120px', objectFit: 'contain', marginRight: '6px' }} 
            />
            <button
              onClick={() => onOpenOrgSettings && onOpenOrgSettings()}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '7px 14px' }}
            >
              <Settings size={14} />
              <span>Workspace Settings</span>
            </button>
            <button
              onClick={() => onOpenRegisterOrg && onOpenRegisterOrg()}
              className="btn btn-primary"
              style={{ fontSize: '0.8rem', padding: '7px 14px' }}
            >
              <Plus size={14} />
              <span>Register Company</span>
            </button>
            {onLogout && (
              <button
                onClick={onLogout}
                className="btn btn-secondary"
                style={{
                  fontSize: '0.8rem',
                  padding: '7px 14px',
                  color: '#EF4444',
                  borderColor: 'rgba(239, 68, 68, 0.3)',
                  backgroundColor: 'rgba(239, 68, 68, 0.05)'
                }}
                title="Sign out of current session"
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 2. Sub-Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '2px' }}>
        <button
          onClick={() => handleSubSectionClick('companies')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px 6px 0 0',
            border: 'none',
            background: activeSubSection === 'companies' ? '#FFAB4A' : 'transparent',
            color: activeSubSection === 'companies' ? '#1A1207' : 'var(--text-secondary)',
            fontWeight: 700,
            fontSize: '0.82rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '7px'
          }}
        >
          <Building2 size={15} />
          <span>Switch Company & Entity</span>
          <span className="badge" style={{
            fontSize: '0.62rem',
            background: activeSubSection === 'companies' ? 'rgba(0,0,0,0.15)' : 'var(--bg-card)',
            color: activeSubSection === 'companies' ? '#1A1207' : 'var(--text-muted)'
          }}>
            {cleanOrgs.length}
          </span>
        </button>

        <button
          onClick={() => handleSubSectionClick('identity')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px 6px 0 0',
            border: 'none',
            background: activeSubSection === 'identity' ? '#FFAB4A' : 'transparent',
            color: activeSubSection === 'identity' ? '#1A1207' : 'var(--text-secondary)',
            fontWeight: 700,
            fontSize: '0.82rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '7px'
          }}
        >
          <User size={15} />
          <span>Google Identity & Credentials</span>
          <span className="badge" style={{
            fontSize: '0.62rem',
            background: activeSubSection === 'identity' ? 'rgba(0,0,0,0.15)' : 'var(--bg-card)',
            color: activeSubSection === 'identity' ? '#1A1207' : 'var(--text-muted)'
          }}>
            OAuth 2.0
          </span>
        </button>

        <button
          onClick={() => handleSubSectionClick('security')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px 6px 0 0',
            border: 'none',
            background: activeSubSection === 'security' ? '#FFAB4A' : 'transparent',
            color: activeSubSection === 'security' ? '#1A1207' : 'var(--text-secondary)',
            fontWeight: 700,
            fontSize: '0.82rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '7px'
          }}
        >
          <ShieldCheck size={15} />
          <span>Governance & Clearances</span>
        </button>
      </div>

      {/* 3. SUB-SECTION: SIMPLE COMPANY SWITCHER */}
      {activeSubSection === 'companies' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
              Associated Companies & Organizations
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Select an enterprise organization below to switch your operational session. Real-time context, policies, and evidence will dynamically re-route.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))', gap: '14px' }}>
            {cleanOrgs.map((org) => {
              const isActive = activeOrg?.id === org.id;
              const isSwitching = switchingOrgId === org.id;

              return (
                <div
                  key={org.id}
                  onClick={() => handleSelectCompany(org)}
                  style={{
                    background: isActive ? '#FFFDF9' : 'var(--bg-card)',
                    border: `1.5px solid ${isActive ? '#FFAB4A' : 'var(--border-subtle)'}`,
                    borderRadius: '10px',
                    padding: '18px 20px',
                    cursor: isActive ? 'default' : 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: isActive ? '0 4px 14px rgba(255, 171, 74, 0.15)' : 'none',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    position: 'relative'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.borderColor = '#FFC57E';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.borderColor = 'var(--border-subtle)';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                      <div style={{
                        width: '38px',
                        height: '38px',
                        borderRadius: '8px',
                        background: isActive ? 'linear-gradient(135deg, #FFAB4A 0%, #F5982C 100%)' : 'var(--bg-card-subtle)',
                        color: isActive ? '#1A1207' : 'var(--text-muted)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 800,
                        fontSize: '1rem',
                        boxShadow: isActive ? '0 2px 8px rgba(255, 171, 74, 0.25)' : 'none'
                      }}>
                        <Building2 size={18} />
                      </div>

                      {isActive ? (
                        <span className="badge" style={{
                          background: 'rgba(255, 171, 74, 0.18)',
                          color: '#9A4900',
                          border: '1px solid rgba(255, 171, 74, 0.4)',
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}>
                          <Check size={12} strokeWidth={3} />
                          Active Company
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 500 }}>
                          Client Root
                        </span>
                      )}
                    </div>

                    <h3 style={{ fontSize: '0.96rem', fontWeight: 700, color: 'var(--text-main)', margin: '0 0 4px 0' }}>
                      {org.name}
                    </h3>

                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span>slug: <code>{org.slug || org.name.toLowerCase().replace(/[^a-z0-9]/g, '-')}</code></span>
                      {org.setup_completed ? (
                        <span style={{ fontSize: '0.62rem', padding: '1px 5px', borderRadius: '3px', background: '#DCFCE7', color: '#15803D', fontWeight: 700 }}>
                          ✓ Setup Ready
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.62rem', padding: '1px 5px', borderRadius: '3px', background: '#FEF3C7', color: '#B45309', fontWeight: 700 }}>
                          ● Setup Incomplete
                        </span>
                      )}
                    </div>
                  </div>

                  <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
                    <div style={{ fontSize: '0.70rem', color: 'var(--text-muted)' }}>
                      {isActive ? 'Session connected' : 'Click card to activate'}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {onLaunchSetupWizard && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onLaunchSetupWizard(org);
                          }}
                          className="btn btn-secondary"
                          style={{
                            padding: '4px 8px',
                            fontSize: '0.72rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                          title="Run Onboarding Setup Wizard for this organization"
                        >
                          <Sparkles size={11} style={{ color: '#FFAB4A' }} />
                          <span>Setup Wizard</span>
                        </button>
                      )}

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectCompany(org);
                        }}
                        disabled={isActive || isSwitching}
                        className={isActive ? 'btn btn-secondary' : 'btn btn-primary'}
                        style={{
                          padding: '5px 12px',
                          fontSize: '0.75rem',
                          cursor: isActive ? 'default' : 'pointer'
                        }}
                      >
                        {isActive ? 'Currently Active' : isSwitching ? 'Switching...' : 'Switch Company ➔'}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. SUB-SECTION: PERSONAS & ROLE SWITCHER */}
      {/* 4. SUB-SECTION: GOOGLE IDENTITY & CREDENTIALS */}
      {activeSubSection === 'identity' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
              Google Identity & Enterprise Credentials
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Verified Single Sign-On credentials for {activePersona?.name || 'Authorized User'}.
            </p>
          </div>

          <div className="clean-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '18px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div style={{
                  width: '46px',
                  height: '46px',
                  borderRadius: '12px',
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E5E7EB',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.06)'
                }}>
                  <svg width="24" height="24" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                  </svg>
                </div>
                <div>
                  <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    {activePersona?.name || 'Verified User'}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {activePersona?.email || 'user@company.com'}
                  </div>
                </div>
              </div>

              <span className="badge badge-verified" style={{ padding: '4px 10px', fontSize: '0.72rem' }}>
                ● Google Verified Session
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px' }}>
              <div style={{ padding: '12px 14px', background: 'var(--bg-card-subtle)', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                  Authentication Protocol
                </span>
                <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>
                  Google OAuth 2.0 / OpenID Connect (OIDC)
                </div>
              </div>

              <div style={{ padding: '12px 14px', background: 'var(--bg-card-subtle)', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                  Client ID
                </span>
                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px', fontFamily: 'monospace' }}>
                  727103176838-...0us.apps.googleusercontent.com
                </div>
              </div>

              <div style={{ padding: '12px 14px', background: 'var(--bg-card-subtle)', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                  Assigned Workspace Role
                </span>
                <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#EA580C', marginTop: '4px', textTransform: 'uppercase' }}>
                  {effectiveRole || 'ADMIN'}
                </div>
              </div>

              <div style={{ padding: '12px 14px', background: 'var(--bg-card-subtle)', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                  Session Security
                </span>
                <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#16A34A', marginTop: '4px' }}>
                  HMAC-SHA256 Signed JWT Token
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. SUB-SECTION: GOVERNANCE & SECURITY CLEARANCES */}
      {activeSubSection === 'security' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
              Separation of Duties (SoD) & Governance Clearances
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Permissions matrix evaluated by the Trulin Policy-Based Access Control (PBAC) engine for {activePersona?.name || 'this user'}.
            </p>
          </div>

          <div className="clean-panel" style={{ padding: '20px 24px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
              <div style={{ padding: '14px', background: 'var(--bg-card-subtle)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <ShieldCheck size={16} style={{ color: '#16A34A' }} />
                  <span style={{ fontWeight: 700, fontSize: '0.86rem', color: 'var(--text-main)' }}>Policy Resolution Clearance</span>
                </div>
                <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', margin: 0 }}>
                  Authority to approve contradictory claims, resolve knowledge base disputes, and sign off on canonical truth standards.
                </p>
              </div>

              <div style={{ padding: '14px', background: 'var(--bg-card-subtle)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <Lock size={16} style={{ color: '#16A34A' }} />
                  <span style={{ fontWeight: 700, fontSize: '0.86rem', color: 'var(--text-main)' }}>HITL Decision Triage</span>
                </div>
                <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', margin: 0 }}>
                  Clearance to adjudicate high-risk autonomous agent tool-call escalations under EU AI Act Article 14 mandate.
                </p>
              </div>

              <div style={{ padding: '14px', background: 'var(--bg-card-subtle)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <Building2 size={16} style={{ color: '#16A34A' }} />
                  <span style={{ fontWeight: 700, fontSize: '0.86rem', color: 'var(--text-main)' }}>Multi-Tenant Switching</span>
                </div>
                <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', margin: 0 }}>
                  Unrestricted cross-tenant switching across enterprise clients and departmental workspaces.
                </p>
              </div>

              <div style={{ padding: '14px', background: 'var(--bg-card-subtle)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <Key size={16} style={{ color: '#16A34A' }} />
                  <span style={{ fontWeight: 700, fontSize: '0.86rem', color: 'var(--text-main)' }}>Cryptographic Merkle Proofs</span>
                </div>
                <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', margin: 0 }}>
                  Permission to generate RFC 6962 inclusion proofs and verify tamper-evident audit ledger roots.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
