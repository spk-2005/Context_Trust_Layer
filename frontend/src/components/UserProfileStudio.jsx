import React, { useState, useEffect } from 'react';
import {
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
  Globe,
  User,
  Phone,
  Clock,
  Save,
  CheckCircle2
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
  onOpenRbacModal,
  onLaunchSetupWizard,
  onLogout,
  showToast,
  initialSubSection = 'user_profile',
  onSubSectionChange
}) {
  const { user: authUser, token, updateUser } = useAuth();
  const [switchingOrgId, setSwitchingOrgId] = useState(null);
  const [activeSubSection, setActiveSubSection] = useState(
    initialSubSection && initialSubSection !== 'identity' && initialSubSection !== 'security' ? initialSubSection : 'user_profile'
  ); // 'user_profile' | 'companies' | 'register'

  // Editable Non-Confidential Profile state
  const [editName, setEditName] = useState('');
  const [editTitle, setEditTitle] = useState('');
  const [editDepartment, setEditDepartment] = useState('');
  const [editTimezone, setEditTimezone] = useState('UTC');
  const [editPhone, setEditPhone] = useState('');
  const [editBio, setEditBio] = useState('');
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSavedMsg, setProfileSavedMsg] = useState(false);

  // Sync initial user details into edit form
  useEffect(() => {
    const currentName = authUser?.name || activePersona?.name || 'PRASANNA KUMAR SIMHADRI';
    const currentTitle = authUser?.title || activePersona?.title || 'Administrator';
    const currentDept = authUser?.department || activePersona?.department || 'Trust & Governance';
    const currentTz = authUser?.timezone || 'UTC';
    const currentPhone = authUser?.phone || '';
    const currentBio = authUser?.bio || 'Enterprise security and compliance administrator for autonomous AI decision gates.';

    setEditName(currentName);
    setEditTitle(currentTitle);
    setEditDepartment(currentDept);
    setEditTimezone(currentTz);
    setEditPhone(currentPhone);
    setEditBio(currentBio);
  }, [authUser, activePersona]);

  // Register Company Form state
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanyDomain, setNewCompanyDomain] = useState('');
  const [newCompanyIndustry, setNewCompanyIndustry] = useState('Enterprise AI & Decision Governance');
  const [isRegistering, setIsRegistering] = useState(false);
  const [registerError, setRegisterError] = useState(null);

  useEffect(() => {
    if (initialSubSection && initialSubSection !== 'identity' && initialSubSection !== 'security') {
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

  const handleSaveProfileSubmit = async (e) => {
    e.preventDefault();
    if (!editName.trim()) {
      if (showToast) showToast('Name cannot be empty', 'error');
      return;
    }

    setIsSavingProfile(true);
    const updatedUser = {
      name: editName.trim(),
      title: editTitle.trim(),
      department: editDepartment.trim(),
      timezone: editTimezone,
      phone: editPhone.trim(),
      bio: editBio.trim()
    };

    if (authUser?.id) {
      try {
        await fetch(`/v1/users/${authUser.id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify({
            name: editName.trim(),
            title: editTitle.trim(),
            department: editDepartment.trim()
          })
        });
      } catch (err) {
        console.warn('Backend patch user error:', err);
      }
    }

    if (updateUser) {
      updateUser(updatedUser);
    }

    if (onSelectPersona && activePersona) {
      onSelectPersona({ ...activePersona, ...updatedUser });
    }

    setProfileSavedMsg(true);
    if (showToast) {
      showToast('Profile information successfully updated!', 'success');
    }

    setTimeout(() => {
      setIsSavingProfile(false);
      setTimeout(() => setProfileSavedMsg(false), 3000);
    }, 400);
  };

  const displayName = authUser?.name || activePersona?.name || editName || 'Authorized User';
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
      {/* 1. Profile Header Hero (Dedicated to User Profile view) */}
      {activeSubSection === 'user_profile' && (
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
          </div>
        </div>
      )}

      {/* 2. SUB-SECTION: MY USER PROFILE (EDITABLE NON-CONFIDENTIAL DATA) */}
      {activeSubSection === 'user_profile' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '820px' }}>
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
              User Profile & Account Information
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Manage and customize your non-confidential operational profile and identity attributes.
            </p>
          </div>

          <form
            onSubmit={handleSaveProfileSubmit}
            className="clean-panel"
            style={{
              padding: '28px',
              display: 'flex',
              flexDirection: 'column',
              gap: '22px',
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)'
            }}
          >
            {profileSavedMsg && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 14px',
                borderRadius: '6px',
                backgroundColor: '#F0FDF4',
                border: '1px solid #DCFCE7',
                color: '#15803D',
                fontSize: '0.82rem',
                fontWeight: 600
              }}>
                <CheckCircle2 size={16} />
                <span>Profile details successfully updated and saved!</span>
              </div>
            )}

            {/* Editable Fields Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Full Display Name *
                </label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="e.g. John Doe"
                  required
                  style={{
                    width: '100%',
                    padding: '9px 12px',
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
                  Job Title / Operational Role
                </label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  placeholder="e.g. Security & Compliance Architect"
                  style={{
                    width: '100%',
                    padding: '9px 12px',
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
                  Department / Business Unit
                </label>
                <input
                  type="text"
                  value={editDepartment}
                  onChange={(e) => setEditDepartment(e.target.value)}
                  placeholder="e.g. Trust & Governance Platform"
                  style={{
                    width: '100%',
                    padding: '9px 12px',
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
                  Preferred Timezone
                </label>
                <select
                  value={editTimezone}
                  onChange={(e) => setEditTimezone(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.88rem',
                    outline: 'none',
                    backgroundColor: '#FFFFFF',
                    boxSizing: 'border-box'
                  }}
                >
                  <option value="UTC">UTC (Coordinated Universal Time)</option>
                  <option value="America/New_York">America/New_York (EST / EDT)</option>
                  <option value="America/Los_Angeles">America/Los_Angeles (PST / PDT)</option>
                  <option value="Europe/London">Europe/London (GMT / BST)</option>
                  <option value="Europe/Berlin">Europe/Berlin (CET / CEST)</option>
                  <option value="Asia/Kolkata">Asia/Kolkata (IST +05:30)</option>
                  <option value="Asia/Singapore">Asia/Singapore (SGT +08:00)</option>
                  <option value="Asia/Tokyo">Asia/Tokyo (JST +09:00)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                  Contact Phone (Optional)
                </label>
                <input
                  type="tel"
                  value={editPhone}
                  onChange={(e) => setEditPhone(e.target.value)}
                  placeholder="+1 (555) 000-0000"
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.88rem',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                Professional Bio & Responsibilities
              </label>
              <textarea
                rows={3}
                value={editBio}
                onChange={(e) => setEditBio(e.target.value)}
                placeholder="Brief summary of your governance scope and decision responsibilities..."
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.86rem',
                  outline: 'none',
                  boxSizing: 'border-box',
                  fontFamily: 'inherit',
                  resize: 'vertical'
                }}
              />
            </div>

            {/* Read-Only Confidential & Security Identity Details */}
            <div style={{
              background: '#F8FAFC',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              padding: '16px 18px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}>
              <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Authentication & Confidential Credentials (Managed by Single Sign-On)
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
                <div>
                  <span style={{ fontSize: '0.7rem', color: '#64748B', display: 'block' }}>Primary Authentication Email</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '3px' }}>
                    <Lock size={12} style={{ color: '#64748B' }} />
                    <span style={{ fontSize: '0.84rem', fontWeight: 600, color: '#0F172A' }}>{displayEmail}</span>
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '0.7rem', color: '#64748B', display: 'block' }}>System Governance Role</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '3px', flexWrap: 'wrap' }}>
                    <Shield size={12} style={{ color: '#047857' }} />
                    <span style={{ fontSize: '0.84rem', fontWeight: 700, color: '#047857' }}>
                      {effectiveRole?.toUpperCase() || 'ADMIN'}
                    </span>
                    <span style={{ fontSize: '0.64rem', color: '#64748B' }}>(System enforced)</span>
                    {onOpenRbacModal && (
                      <button
                        type="button"
                        onClick={onOpenRbacModal}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#0F172A',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          textDecoration: 'underline',
                          padding: '0 4px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '3px',
                          marginLeft: '4px'
                        }}
                      >
                        <ShieldCheck size={12} />
                        <span>Inspect RBAC Matrix →</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '10px', paddingTop: '8px' }}>
              <button
                type="submit"
                disabled={isSavingProfile}
                className="btn btn-primary"
                style={{
                  padding: '9px 24px',
                  fontSize: '0.84rem',
                  fontWeight: 700,
                  borderRadius: '8px',
                  background: '#0F172A',
                  color: '#FFFFFF',
                  border: 'none',
                  cursor: isSavingProfile ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
                }}
              >
                {isSavingProfile ? <Sparkles size={14} className="spinning" /> : <Save size={14} />}
                <span>{isSavingProfile ? 'Saving...' : 'Save Profile Changes'}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 4. SUB-SECTION: ENTERPRISE ORGANIZATIONS CARDS */}
      {activeSubSection === 'companies' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                Associated Companies & Organizations
              </h2>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Manage, switch operational environments, or configure workspace settings for your enterprise.
              </p>
            </div>

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
                          padding: '6px 12px',
                          fontSize: '0.76rem',
                          fontWeight: 600,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          background: '#FFFFFF',
                          border: '1px solid #CBD5E1',
                          borderRadius: '6px',
                          color: '#0F172A',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
                        onMouseLeave={e => e.currentTarget.style.background = '#FFFFFF'}
                        title="Configure workspace settings for this organization"
                      >
                        <Settings size={13} style={{ color: '#475569' }} />
                        <span>Workspace Settings</span>
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

      {/* 5. SUB-SECTION: DEDICATED REGISTER COMPANY PAGE (NO POPUPS) */}
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
    </div>
  );
}
