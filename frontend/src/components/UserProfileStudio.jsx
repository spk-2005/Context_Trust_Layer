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

  const displayOrgs = (organizations && organizations.length > 0)
    ? organizations.filter(o => 
        !o.name.includes('Test') && 
        !o.name.includes('Auto Resolve') && 
        !o.name.includes('Default Org') &&
        !o.name.includes('Deloitte') &&
        !o.name.includes('Goldman')
      )
    : (activeOrg ? [activeOrg] : []);
  const cleanOrgs = displayOrgs.length > 0 ? displayOrgs : (activeOrg ? [activeOrg] : []);

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
          onClick={() => handleSubSectionClick('personas')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px 6px 0 0',
            border: 'none',
            background: activeSubSection === 'personas' ? '#FFAB4A' : 'transparent',
            color: activeSubSection === 'personas' ? '#1A1207' : 'var(--text-secondary)',
            fontWeight: 700,
            fontSize: '0.82rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '7px'
          }}
        >
          <User size={15} />
          <span>Identity & Personas</span>
          <span className="badge" style={{
            fontSize: '0.62rem',
            background: activeSubSection === 'personas' ? 'rgba(0,0,0,0.15)' : 'var(--bg-card)',
            color: activeSubSection === 'personas' ? '#1A1207' : 'var(--text-muted)'
          }}>
            {personas.length || 4}
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

                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>slug: <code>{org.slug || org.name.toLowerCase().replace(/[^a-z0-9]/g, '-')}</code></span>
                    </div>
                  </div>

                  <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ fontSize: '0.70rem', color: 'var(--text-muted)' }}>
                      {isActive ? 'Session connected' : 'Click card to activate'}
                    </div>

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
              );
            })}
          </div>
        </div>
      )}

      {/* 4. SUB-SECTION: PERSONAS & ROLE SWITCHER */}
      {activeSubSection === 'personas' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
              Individual Personas & Role Clearances
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Switch personas to test role-based access control (RBAC) and Separation of Duties (SoD) enforcement across Trulin.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: '14px' }}>
            {personas.map((persona) => {
              const isSelected = activePersona?.id === persona.id ||
                (activePersona?.email && activePersona.email === persona.email) ||
                (activePersona?.role === persona.role && activePersona?.name === persona.name);
              const initials = persona.name
                ? persona.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
                : 'U';

              return (
                <div
                  key={persona.id || persona.email || persona.role}
                  onClick={() => {
                    if (onSelectPersona) onSelectPersona(persona);
                  }}
                  style={{
                    background: isSelected ? '#FFFDF9' : 'var(--bg-card)',
                    border: `1.5px solid ${isSelected ? '#FFAB4A' : 'var(--border-subtle)'}`,
                    borderRadius: '10px',
                    padding: '16px 18px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    boxShadow: isSelected ? '0 3px 12px rgba(255, 171, 74, 0.14)' : 'none',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '50%',
                      background: isSelected ? 'linear-gradient(135deg, #FFAB4A 0%, #EA580C 100%)' : 'var(--bg-card-subtle)',
                      color: isSelected ? '#1A1207' : 'var(--text-secondary)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: '0.82rem',
                      flexShrink: 0
                    }}>
                      {initials}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {persona.name}
                        </span>
                        <span className="badge" style={{
                          fontSize: '0.60rem',
                          padding: '1px 5px',
                          background: isSelected ? 'rgba(255, 171, 74, 0.15)' : 'var(--bg-card-subtle)',
                          color: isSelected ? '#9A4900' : 'var(--text-muted)',
                          fontWeight: 700
                        }}>
                          {persona.role?.toUpperCase()}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {persona.title || persona.department || 'Enterprise User'}
                      </div>
                    </div>
                  </div>

                  <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.70rem', color: 'var(--text-muted)' }}>
                      {persona.email || `${persona.name.toLowerCase().replace(/\s+/g, '.')}@${activeOrg?.slug || 'company'}.com`}
                    </span>
                    {isSelected ? (
                      <span style={{ fontSize: '0.70rem', color: '#EA580C', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                        <Check size={11} strokeWidth={3} /> Active
                      </span>
                    ) : (
                      <span style={{ fontSize: '0.70rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                        Switch ➔
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
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
