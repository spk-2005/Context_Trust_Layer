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
  ArrowLeft,
  Layers,
  Sparkles,
  LogOut,
  Globe
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

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
  const { user: authUser, token } = useAuth();
  const [switchingOrgId, setSwitchingOrgId] = useState(null);
  const [activeSubSection, setActiveSubSection] = useState(initialSubSection || 'companies'); // 'companies' | 'register' | 'identity' | 'security'

  // Register Company Form state
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanyDomain, setNewCompanyDomain] = useState('');
  const [newCompanyIndustry, setNewCompanyIndustry] = useState('Enterprise AI & Decision Governance');
  const [isRegistering, setIsRegistering] = useState(false);
  const [registerError, setRegisterError] = useState(null);

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

  const displayName = authUser?.name || activePersona?.name || 'Authorized User';
  const displayEmail = authUser?.email || activePersona?.email || 'user@enterprise.com';
  const avatarUrl = authUser?.avatar_url || authUser?.picture || activePersona?.avatar_url;
  const userInitials = displayName
    ? displayName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
    : 'U';

  const cleanOrgs = (organizations && organizations.length > 0)
    ? organizations.filter(o => 
        !o.name.includes('Auto Resolve') && 
        !o.name.includes('Default Org')
      )
    : (activeOrg ? [activeOrg] : []);

  const handleRegisterCompanySubmit = async (e) => {
    e.preventDefault();
    if (!newCompanyName.trim()) {
      setRegisterError('Organization name is required.');
      return;
    }
    setRegisterError(null);
    setIsRegistering(true);

    const slug = newCompanyName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    const domains = newCompanyDomain.trim()
      ? newCompanyDomain.split(',').map(d => d.trim().toLowerCase().replace(/^@/, '')).filter(Boolean)
      : ['gmail.com'];

    try {
      const res = await fetch('/v1/organizations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          name: newCompanyName.trim(),
          slug,
          domain_whitelist: domains,
          setup_completed: true
        })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server returned ${res.status}`);
      }

      const created = await res.json();
      created.setup_completed = true;
      if (onSwitchOrg) {
        await onSwitchOrg(created);
      }
      if (showToast) {
        showToast(`Enterprise organization '${created.name}' registered successfully!`, 'success');
      }
      setNewCompanyName('');
      setNewCompanyDomain('');
      handleSubSectionClick('companies');
    } catch (err) {
      setRegisterError(err.message || 'Failed to register organization.');
    } finally {
      setIsRegistering(false);
    }
  };

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
            {/* Signed-in Profile Avatar */}
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              backgroundColor: '#0F172A',
              color: '#FFFFFF',
              fontSize: '1.25rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
              border: '1px solid #E2E8F0',
              overflow: 'hidden',
              flexShrink: 0
            }}>
              {avatarUrl ? (
                <img
                  src={avatarUrl}
                  alt={displayName}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              ) : (
                <span>{userInitials}</span>
              )}
            </div>

            <div>
              <h1 style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-main)', margin: 0, letterSpacing: '-0.02em' }}>
                {displayName}
              </h1>

              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginTop: '6px', fontSize: '0.82rem', color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                  <Building2 size={13} style={{ color: 'var(--text-muted)' }} />
                  {activeOrg?.name || 'Enterprise Workspace'}
                </span>
                <span>•</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                  <Mail size={13} style={{ color: 'var(--text-muted)' }} />
                  {displayEmail}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Profile Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <button
              onClick={() => onOpenOrgSettings && onOpenOrgSettings()}
              className="btn btn-secondary"
              style={{
                fontSize: '0.8rem',
                padding: '7px 14px',
                borderRadius: '6px',
                border: '1px solid #E2E8F0',
                background: '#FFFFFF',
                color: '#0F172A',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer'
              }}
            >
              <Settings size={14} />
              <span>Workspace Settings</span>
            </button>
            <button
              onClick={() => handleSubSectionClick('register')}
              className="btn btn-primary"
              style={{
                fontSize: '0.8rem',
                padding: '7px 14px',
                borderRadius: '6px',
                background: '#0F172A',
                color: '#FFFFFF',
                fontWeight: 600,
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer'
              }}
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
                  borderRadius: '6px',
                  color: '#EF4444',
                  borderColor: 'rgba(239, 68, 68, 0.3)',
                  backgroundColor: 'rgba(239, 68, 68, 0.05)',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer'
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
            background: activeSubSection === 'companies' ? '#0F172A' : 'transparent',
            color: activeSubSection === 'companies' ? '#FFFFFF' : 'var(--text-secondary)',
            fontWeight: 700,
            fontSize: '0.82rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '7px'
          }}
        >
          <Building2 size={15} />
          <span>Organizations & Entities</span>
          <span className="badge" style={{
            fontSize: '0.62rem',
            background: activeSubSection === 'companies' ? 'rgba(255,255,255,0.2)' : 'var(--bg-card)',
            color: activeSubSection === 'companies' ? '#FFFFFF' : 'var(--text-muted)'
          }}>
            {cleanOrgs.length}
          </span>
        </button>

        <button
          onClick={() => handleSubSectionClick('register')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px 6px 0 0',
            border: 'none',
            background: activeSubSection === 'register' ? '#0F172A' : 'transparent',
            color: activeSubSection === 'register' ? '#FFFFFF' : 'var(--text-secondary)',
            fontWeight: 700,
            fontSize: '0.82rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '7px'
          }}
        >
          <Plus size={15} />
          <span>Register Company</span>
        </button>

        <button
          onClick={() => handleSubSectionClick('identity')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px 6px 0 0',
            border: 'none',
            background: activeSubSection === 'identity' ? '#0F172A' : 'transparent',
            color: activeSubSection === 'identity' ? '#FFFFFF' : 'var(--text-secondary)',
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
            background: activeSubSection === 'identity' ? 'rgba(255,255,255,0.2)' : 'var(--bg-card)',
            color: activeSubSection === 'identity' ? '#FFFFFF' : 'var(--text-muted)'
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
            background: activeSubSection === 'security' ? '#0F172A' : 'transparent',
            color: activeSubSection === 'security' ? '#FFFFFF' : 'var(--text-secondary)',
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

      {/* 3. SUB-SECTION: ENTERPRISE ORGANIZATIONS CARDS */}
      {activeSubSection === 'companies' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
              Associated Companies & Organizations
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Manage and switch operational environments for your enterprise.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {cleanOrgs.map((org) => {
              const isActive = activeOrg?.id === org.id;
              const isSwitching = switchingOrgId === org.id;

              return (
                <div
                  key={org.id}
                  onClick={() => handleSelectCompany(org)}
                  style={{
                    background: '#FFFFFF',
                    border: `1.5px solid ${isActive ? '#0F172A' : '#E2E8F0'}`,
                    borderRadius: '12px',
                    padding: '20px 22px',
                    cursor: isActive ? 'default' : 'pointer',
                    transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                    boxShadow: isActive ? '0 4px 20px -2px rgba(15, 23, 42, 0.08)' : '0 1px 3px rgba(0, 0, 0, 0.04)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    position: 'relative'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.borderColor = '#94A3B8';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.borderColor = '#E2E8F0';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                      <div style={{
                        width: '42px',
                        height: '42px',
                        borderRadius: '10px',
                        background: isActive ? '#0F172A' : '#F1F5F9',
                        color: isActive ? '#FFFFFF' : '#475569',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: isActive ? '0 2px 8px rgba(15, 23, 42, 0.25)' : 'none'
                      }}>
                        <Building2 size={20} />
                      </div>

                      {isActive ? (
                        <span style={{
                          padding: '3px 10px',
                          borderRadius: '20px',
                          background: '#0F172A',
                          color: '#FFFFFF',
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}>
                          <Check size={11} strokeWidth={3} />
                          Active Organization
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 500 }}>
                          Available
                        </span>
                      )}
                    </div>

                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: '0 0 6px 0' }}>
                      {org.name}
                    </h3>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
                      {org.domain_whitelist && org.domain_whitelist.length > 0 && (
                        <span style={{ fontSize: '0.7rem', color: '#475569', background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '2px 8px', borderRadius: '4px' }}>
                          🌐 {org.domain_whitelist.join(', ')}
                        </span>
                      )}
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: org.setup_completed ? '#F0FDF4' : '#FFFBEB',
                        color: org.setup_completed ? '#15803D' : '#B45309',
                        border: `1px solid ${org.setup_completed ? '#DCFCE7' : '#FEF3C7'}`,
                        fontWeight: 600
                      }}>
                        {org.setup_completed ? '✓ Verified Enterprise Tenant' : '● Setup In Progress'}
                      </span>
                    </div>
                  </div>

                  <div style={{ marginTop: '18px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
                    <div style={{ fontSize: '0.72rem', color: isActive ? '#0F172A' : '#64748B', fontWeight: isActive ? 600 : 400 }}>
                      {isActive ? '● Current operational session' : 'Click card to activate'}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onOpenOrgSettings) onOpenOrgSettings(org);
                        }}
                        className="btn btn-secondary"
                        style={{
                          padding: '5px 10px',
                          fontSize: '0.74rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px',
                          background: '#FFFFFF',
                          border: '1px solid #E2E8F0',
                          borderRadius: '6px',
                          color: '#334155',
                          cursor: 'pointer'
                        }}
                        title="Configure settings for this organization"
                      >
                        <Settings size={12} />
                        <span>Settings</span>
                      </button>

                      {!isActive && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectCompany(org);
                          }}
                          disabled={isSwitching}
                          className="btn btn-primary"
                          style={{
                            padding: '5px 14px',
                            fontSize: '0.74rem',
                            fontWeight: 600,
                            borderRadius: '6px',
                            background: '#0F172A',
                            color: '#FFFFFF',
                            border: 'none',
                            cursor: 'pointer'
                          }}
                        >
                          {isSwitching ? 'Switching...' : 'Switch Organization'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. SUB-SECTION: DEDICATED REGISTER COMPANY PAGE (NO POPUPS) */}
      {activeSubSection === 'register' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '780px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              type="button"
              onClick={() => handleSubSectionClick('companies')}
              className="btn btn-secondary"
              style={{
                padding: '6px 12px',
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                borderRadius: '6px',
                border: '1px solid #E2E8F0',
                background: '#FFFFFF',
                color: '#0F172A',
                cursor: 'pointer'
              }}
            >
              <ArrowLeft size={14} />
              <span>Back to Organizations</span>
            </button>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', margin: 0, letterSpacing: '-0.01em' }}>
                Register Enterprise Organization
              </h2>
              <p style={{ margin: '3px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Provision a dedicated multi-tenant operational environment for compliance, governance, and document processing.
              </p>
            </div>
          </div>

          <form
            onSubmit={handleRegisterCompanySubmit}
            className="clean-panel"
            style={{
              padding: '28px',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)'
            }}
          >
            {registerError && (
              <div style={{
                padding: '10px 14px',
                borderRadius: '6px',
                backgroundColor: '#FEF2F2',
                border: '1px solid #FECACA',
                color: '#B91C1C',
                fontSize: '0.82rem'
              }}>
                {registerError}
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                Organization / Company Name *
              </label>
              <input
                type="text"
                placeholder="e.g. Acme Corporation or Horizon Financial"
                value={newCompanyName}
                onChange={(e) => setNewCompanyName(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.88rem',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                Authorized Corporate Email Domains
              </label>
              <input
                type="text"
                placeholder="e.g. acme.com, acmecorp.io (comma-separated)"
                value={newCompanyDomain}
                onChange={(e) => setNewCompanyDomain(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.88rem',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
              <span style={{ fontSize: '0.74rem', color: '#64748B', marginTop: '4px', display: 'block' }}>
                Users signing in with these domains will automatically resolve to this organization.
              </span>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                Primary Industry & Compliance Standard
              </label>
              <select
                value={newCompanyIndustry}
                onChange={(e) => setNewCompanyIndustry(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.88rem',
                  outline: 'none',
                  backgroundColor: '#FFFFFF',
                  boxSizing: 'border-box'
                }}
              >
                <option value="Enterprise AI & Decision Governance">Enterprise AI & Decision Governance (EU AI Act & NIST)</option>
                <option value="Financial Services & Wealth Management">Financial Services & Wealth Management (SEC & FINRA)</option>
                <option value="Healthcare & Life Sciences">Healthcare & Life Sciences (HIPAA & FDA)</option>
                <option value="Defense & Public Sector">Defense & Public Sector (FedRAMP & SOC2)</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '10px', marginTop: '10px', paddingTop: '16px', borderTop: '1px solid #F1F5F9' }}>
              <button
                type="button"
                onClick={() => handleSubSectionClick('companies')}
                disabled={isRegistering}
                className="btn btn-secondary"
                style={{
                  padding: '9px 18px',
                  fontSize: '0.84rem',
                  borderRadius: '8px',
                  border: '1px solid #E2E8F0',
                  background: '#FFFFFF',
                  color: '#475569',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isRegistering || !newCompanyName.trim()}
                className="btn btn-primary"
                style={{
                  padding: '9px 22px',
                  fontSize: '0.84rem',
                  fontWeight: 700,
                  borderRadius: '8px',
                  background: '#0F172A',
                  color: '#FFFFFF',
                  border: 'none',
                  cursor: isRegistering ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                {isRegistering ? <Sparkles size={14} className="spinning" /> : <Plus size={14} />}
                <span>{isRegistering ? 'Provisioning...' : 'Register Enterprise Organization'}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 5. SUB-SECTION: GOOGLE IDENTITY & CREDENTIALS */}
      {activeSubSection === 'identity' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
              Google Identity & Enterprise Credentials
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Verified Single Sign-On credentials for {displayName}.
            </p>
          </div>

          <div className="clean-panel" style={{ padding: '24px', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
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
                    {displayName}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {displayEmail}
                  </div>
                </div>
              </div>

              <span style={{
                padding: '4px 10px',
                fontSize: '0.72rem',
                borderRadius: '20px',
                background: '#F0FDF4',
                color: '#15803D',
                border: '1px solid #DCFCE7',
                fontWeight: 600
              }}>
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
                <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#0F172A', marginTop: '4px', textTransform: 'uppercase' }}>
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

      {/* 6. SUB-SECTION: GOVERNANCE & SECURITY CLEARANCES */}
      {activeSubSection === 'security' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
              Separation of Duties (SoD) & Governance Clearances
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Permissions matrix evaluated by the Trulin Policy-Based Access Control (PBAC) engine for {displayName}.
            </p>
          </div>

          <div className="clean-panel" style={{ padding: '20px 24px', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
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
