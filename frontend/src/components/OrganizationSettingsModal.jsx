import React, { useState, useEffect } from 'react';
import {
  Building2,
  Globe,
  Users,
  Mail,
  X,
  Plus,
  Trash2,
  Copy,
  Check,
  Shield,
  Clock,
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function OrganizationSettingsModal({ isOpen, onClose, activeOrg, onOrgUpdated }) {
  const { token, user: currentUser } = useAuth();

  const [activeTab, setActiveTab] = useState('domains'); // 'domains' | 'members' | 'invites'
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // General & Domain Whitelist states
  const [orgName, setOrgName] = useState('');
  const [orgSlug, setOrgSlug] = useState('');
  const [domains, setDomains] = useState([]);
  const [newDomainInput, setNewDomainInput] = useState('');
  const [authMethods, setAuthMethods] = useState(['password', 'google', 'microsoft', 'okta']);

  // Members states
  const [members, setMembers] = useState([]);
  const [membersLoading, setMembersLoading] = useState(false);

  // Invites states
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('reviewer');
  const [invites, setInvites] = useState([]);
  const [invitesLoading, setInvitesLoading] = useState(false);
  const [lastCreatedInvite, setLastCreatedInvite] = useState(null);
  const [copiedLink, setCopiedLink] = useState(false);

  // Initialize or fetch organization details when opened
  useEffect(() => {
    if (!isOpen || !activeOrg?.id) return;
    setErrorMsg(null);
    setSuccessMsg(null);
    setOrgName(activeOrg.name || '');
    setOrgSlug(activeOrg.slug || '');
    setDomains(activeOrg.domain_whitelist || []);
    setAuthMethods(activeOrg.allowed_auth_methods || ['password', 'google', 'microsoft', 'okta']);

    fetchOrgDetails();
    fetchMembers();
    fetchInvites();
  }, [isOpen, activeOrg?.id]);

  const fetchOrgDetails = async () => {
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/settings`);
      if (res.ok) {
        const data = await res.json();
        setOrgName(data.name);
        setOrgSlug(data.slug);
        setDomains(data.domain_whitelist || []);
        if (data.allowed_auth_methods) setAuthMethods(data.allowed_auth_methods);
      }
    } catch (err) {
      console.warn('Failed to fetch org details:', err);
    }
  };

  const fetchMembers = async () => {
    setMembersLoading(true);
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/members`);
      if (res.ok) {
        const data = await res.json();
        setMembers(data);
      }
    } catch (err) {
      console.warn('Failed to fetch org members:', err);
    } finally {
      setMembersLoading(false);
    }
  };

  const fetchInvites = async () => {
    setInvitesLoading(true);
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/invites`);
      if (res.ok) {
        const data = await res.json();
        setInvites(data);
      }
    } catch (err) {
      console.warn('Failed to fetch org invites:', err);
    } finally {
      setInvitesLoading(false);
    }
  };

  if (!isOpen) return null;

  // Domain Management Handlers
  const handleAddDomain = (e) => {
    e.preventDefault();
    const clean = newDomainInput.trim().toLowerCase().replace('@', '');
    if (!clean) return;
    if (domains.includes(clean)) {
      setErrorMsg(`Domain '${clean}' is already in the whitelist.`);
      return;
    }
    setDomains([...domains, clean]);
    setNewDomainInput('');
  };

  const handleRemoveDomain = (domToRemove) => {
    setDomains(domains.filter(d => d !== domToRemove));
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: orgName.trim(),
          slug: orgSlug.trim().toLowerCase(),
          domain_whitelist: domains,
          allowed_auth_methods: authMethods,
        })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to update organization settings');
      }
      const updated = await res.json();
      setSuccessMsg('Organization settings and domain whitelist updated successfully!');
      if (onOrgUpdated) onOrgUpdated(updated);
    } catch (err) {
      setErrorMsg(err.message || 'Error updating settings');
    } finally {
      setLoading(false);
    }
  };

  // Member Management Handlers
  const handleChangeRole = async (userId, newRole) => {
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/members/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole })
      });
      if (res.ok) {
        const updatedUser = await res.json();
        setMembers(members.map(m => m.id === userId ? { ...m, role: updatedUser.role } : m));
        setSuccessMsg(`Updated role for ${updatedUser.name} to ${newRole.toUpperCase()}`);
      }
    } catch (err) {
      setErrorMsg('Failed to update member role');
    }
  };

  const handleRemoveMember = async (userId, userName) => {
    if (!confirm(`Are you sure you want to remove ${userName} from this workspace?`)) return;
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/members/${userId}`, {
        method: 'DELETE'
      });
      if (res.ok || res.status === 204) {
        setMembers(members.filter(m => m.id !== userId));
        setSuccessMsg(`Removed ${userName} from workspace.`);
      }
    } catch (err) {
      setErrorMsg('Failed to remove member');
    }
  };

  // Invite Management Handlers
  const handleCreateInvite = async (e) => {
    e.preventDefault();
    if (!inviteEmail.includes('@')) {
      setErrorMsg('Please provide a valid corporate email address.');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/invites`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to generate invitation link');
      }
      const newInvite = await res.json();
      setLastCreatedInvite(newInvite);
      setInvites([newInvite, ...invites]);
      setInviteEmail('');
      setSuccessMsg(`Generated invitation link for ${newInvite.email}!`);
    } catch (err) {
      setErrorMsg(err.message || 'Error generating invite');
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeInvite = async (inviteId) => {
    try {
      const res = await fetch(`/v1/organizations/${activeOrg.id}/invites/${inviteId}`, {
        method: 'DELETE'
      });
      if (res.ok || res.status === 204) {
        setInvites(invites.filter(i => i.id !== inviteId));
        if (lastCreatedInvite?.id === inviteId) setLastCreatedInvite(null);
        setSuccessMsg('Invitation revoked.');
      }
    } catch (err) {
      setErrorMsg('Failed to revoke invitation');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
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
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '640px',
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
        <div style={{ height: '4px', background: 'linear-gradient(90deg, #2563EB, #10B981, #6366F1)' }} />

        {/* Modal Header */}
        <div
          style={{
            padding: '16px 22px 14px 22px',
            borderBottom: '1px solid #F1F5F9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FAFAFC'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: '#EFF6FF',
                border: '1px solid #DBEAFE',
                color: '#2563EB',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}
            >
              <Building2 size={18} strokeWidth={2.2} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 700, color: '#0F172A' }}>
                  {activeOrg?.name || 'Workspace Management'}
                </h3>
                <span
                  style={{
                    fontSize: '0.62rem',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: '#EFF6FF',
                    color: '#2563EB',
                    border: '1px solid #DBEAFE',
                    fontFamily: 'monospace',
                    fontWeight: 600
                  }}
                >
                  TENANT: {activeOrg?.slug || 'tenant'}
                </span>
              </div>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.73rem', color: '#64748B' }}>
                Manage corporate domain routing, team roles, and secure enterprise invite links.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            style={{
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '6px',
              padding: '6px',
              cursor: 'pointer',
              color: '#64748B',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s ease'
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
            onClick={() => { setActiveTab('domains'); setErrorMsg(null); }}
            style={{
              flex: 1,
              padding: '11px 12px',
              border: 'none',
              borderBottom: activeTab === 'domains' ? '2px solid #2563EB' : '2px solid transparent',
              background: 'transparent',
              color: activeTab === 'domains' ? '#2563EB' : '#64748B',
              fontWeight: activeTab === 'domains' ? 700 : 500,
              fontSize: '0.78rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <Globe size={14} />
            <span>Domain Whitelist & SSO</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('members'); setErrorMsg(null); }}
            style={{
              flex: 1,
              padding: '11px 12px',
              border: 'none',
              borderBottom: activeTab === 'members' ? '2px solid #2563EB' : '2px solid transparent',
              background: 'transparent',
              color: activeTab === 'members' ? '#2563EB' : '#64748B',
              fontWeight: activeTab === 'members' ? 700 : 500,
              fontSize: '0.78rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <Users size={14} />
            <span>Team Members ({members.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('invites'); setErrorMsg(null); }}
            style={{
              flex: 1,
              padding: '11px 12px',
              border: 'none',
              borderBottom: activeTab === 'invites' ? '2px solid #2563EB' : '2px solid transparent',
              background: 'transparent',
              color: activeTab === 'invites' ? '#2563EB' : '#64748B',
              fontWeight: activeTab === 'invites' ? 700 : 500,
              fontSize: '0.78rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <Mail size={14} />
            <span>Invite Links ({invites.length})</span>
          </button>
        </div>

        {/* Notifications */}
        {errorMsg && (
          <div
            style={{
              margin: '12px 20px 0 20px',
              padding: '9px 12px',
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
              padding: '9px 12px',
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

          {/* TAB 1: DOMAIN WHITELIST & SSO SETTINGS */}
          {activeTab === 'domains' && (
            <form onSubmit={handleSaveSettings} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Organization Name
                  </label>
                  <input
                    type="text"
                    required
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.80rem',
                      color: '#0F172A',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Workspace Identifier (Slug)
                  </label>
                  <input
                    type="text"
                    required
                    value={orgSlug}
                    onChange={(e) => setOrgSlug(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.80rem',
                      color: '#0F172A',
                      fontFamily: 'monospace',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>

              {/* Domain Whitelist Tags */}
              <div
                style={{
                  padding: '14px',
                  borderRadius: '8px',
                  backgroundColor: '#F8FAFC',
                  border: '1px solid #E2E8F0',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#1E293B', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Globe size={14} color="#2563EB" />
                      Corporate Domain Whitelist
                    </span>
                    <p style={{ margin: '2px 0 0 0', fontSize: '0.68rem', color: '#64748B' }}>
                      Employees registering or logging in with these email domains automatically bind to this tenant.
                    </p>
                  </div>
                </div>

                {/* Tag Pills */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', minHeight: '32px' }}>
                  {domains.length === 0 ? (
                    <span style={{ fontSize: '0.72rem', color: '#94A3B8', fontStyle: 'italic', padding: '4px 0' }}>
                      No corporate domains whitelisted yet. (Anyone with invite or SSO can join).
                    </span>
                  ) : (
                    domains.map(dom => (
                      <div
                        key={dom}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          backgroundColor: '#EFF6FF',
                          border: '1px solid #BFDBFE',
                          color: '#1D4ED8',
                          fontSize: '0.72rem',
                          fontWeight: 600
                        }}
                      >
                        <span>@{dom}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveDomain(dom)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#2563EB',
                            cursor: 'pointer',
                            padding: 0,
                            display: 'flex',
                            alignItems: 'center'
                          }}
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))
                  )}
                </div>

                {/* Add domain input */}
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    placeholder="e.g. ssfa.com or subsidiary.corp"
                    value={newDomainInput}
                    onChange={(e) => setNewDomainInput(e.target.value)}
                    style={{
                      flex: 1,
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.75rem',
                      outline: 'none'
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleAddDomain}
                    style={{
                      padding: '7px 12px',
                      borderRadius: '6px',
                      backgroundColor: '#2563EB',
                      color: '#FFFFFF',
                      border: 'none',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Plus size={13} />
                    <span>Add Domain</span>
                  </button>
                </div>
              </div>

              {/* Allowed Auth Methods */}
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#334155', marginBottom: '8px' }}>
                  Allowed Authentication Providers
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  {[
                    { id: 'google', label: 'Google Workspace (OIDC)', icon: '🌐' },
                    { id: 'microsoft', label: 'Microsoft Entra ID / Azure', icon: '🏢' },
                    { id: 'okta', label: 'Okta Workforce Identity', icon: '🔒' },
                    { id: 'password', label: 'Corporate Password Auth', icon: '🔑' },
                  ].map(method => {
                    const isChecked = authMethods.includes(method.id);
                    return (
                      <label
                        key={method.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '8px 10px',
                          borderRadius: '6px',
                          border: isChecked ? '1px solid #BFDBFE' : '1px solid #E2E8F0',
                          backgroundColor: isChecked ? '#EFF6FF' : '#FFFFFF',
                          cursor: 'pointer',
                          fontSize: '0.74rem',
                          color: isChecked ? '#1E40AF' : '#475569',
                          fontWeight: 500
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setAuthMethods([...authMethods, method.id]);
                            } else {
                              setAuthMethods(authMethods.filter(m => m !== method.id));
                            }
                          }}
                        />
                        <span>{method.icon} {method.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  marginTop: '6px',
                  padding: '9px 16px',
                  borderRadius: '6px',
                  backgroundColor: '#2563EB',
                  color: '#FFFFFF',
                  border: 'none',
                  fontSize: '0.80rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  alignSelf: 'flex-end',
                  transition: 'background-color 0.15s ease'
                }}
              >
                {loading ? 'Saving Settings...' : 'Save Workspace Governance'}
              </button>
            </form>
          )}

          {/* TAB 2: TEAM MEMBERS */}
          {activeTab === 'members' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>
                  Workspace Members ({members.length})
                </span>
                <button
                  type="button"
                  onClick={fetchMembers}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#2563EB',
                    fontSize: '0.72rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <RefreshCw size={12} />
                  <span>Refresh</span>
                </button>
              </div>

              {membersLoading ? (
                <div style={{ textAlign: 'center', padding: '24px', color: '#64748B', fontSize: '0.75rem' }}>
                  Loading workspace team members...
                </div>
              ) : members.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '24px', color: '#64748B', fontSize: '0.75rem' }}>
                  No members found in this workspace.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {members.map(m => {
                    const badge = getRoleBadgeStyle(m.role);
                    const isSelf = currentUser?.id === m.id;
                    return (
                      <div
                        key={m.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '10px 12px',
                          borderRadius: '8px',
                          border: '1px solid #E2E8F0',
                          backgroundColor: '#FFFFFF'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <img
                            src={m.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${m.name}`}
                            alt={m.name}
                            style={{
                              width: '34px',
                              height: '34px',
                              borderRadius: '8px',
                              backgroundColor: '#F1F5F9',
                              border: '1px solid #E2E8F0',
                              objectFit: 'cover'
                            }}
                          />
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0F172A' }}>
                                {m.name}
                              </span>
                              {isSelf && (
                                <span style={{ fontSize: '0.62rem', color: '#16A34A', fontWeight: 600, background: '#DCFCE7', padding: '1px 5px', borderRadius: '4px' }}>
                                  You
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: '0.70rem', color: '#64748B' }}>
                              {m.email} • <span style={{ color: '#94A3B8' }}>{m.department || 'Governance'}</span>
                            </div>
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {/* Role Selector */}
                          <select
                            value={m.role.toLowerCase()}
                            onChange={(e) => handleChangeRole(m.id, e.target.value)}
                            style={{
                              padding: '4px 8px',
                              borderRadius: '4px',
                              border: '1px solid #CBD5E1',
                              backgroundColor: '#F8FAFC',
                              fontSize: '0.70rem',
                              fontWeight: 600,
                              color: '#334155',
                              cursor: 'pointer'
                            }}
                          >
                            <option value="admin">ADMIN / CCO</option>
                            <option value="data_owner">DATA STEWARD</option>
                            <option value="reviewer">AUDITOR</option>
                            <option value="developer">OPERATOR</option>
                          </select>

                          {!isSelf && (
                            <button
                              type="button"
                              onClick={() => handleRemoveMember(m.id, m.name)}
                              title="Remove from workspace"
                              style={{
                                background: '#FEF2F2',
                                border: '1px solid #FECACA',
                                color: '#EF4444',
                                borderRadius: '4px',
                                padding: '5px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center'
                              }}
                            >
                              <Trash2 size={12} />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: ENTERPRISE INVITES */}
          {activeTab === 'invites' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* Form to create invite */}
              <form
                onSubmit={handleCreateInvite}
                style={{
                  padding: '14px',
                  borderRadius: '8px',
                  backgroundColor: '#F8FAFC',
                  border: '1px solid #E2E8F0',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px'
                }}
              >
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#1E293B', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Mail size={14} color="#2563EB" />
                  Invite Colleague into Workspace
                </span>

                <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr auto', gap: '8px' }}>
                  <input
                    type="email"
                    required
                    placeholder="Colleague's work email (e.g. auditor@ssfa.com)"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    style={{
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.75rem',
                      outline: 'none'
                    }}
                  />

                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    style={{
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      backgroundColor: '#FFFFFF',
                      fontSize: '0.75rem',
                      fontWeight: 500,
                      color: '#334155'
                    }}
                  >
                    <option value="reviewer">Auditor / Reviewer</option>
                    <option value="data_owner">Data Steward</option>
                    <option value="developer">Operator / Dev</option>
                    <option value="admin">Chief Compliance Officer (Admin)</option>
                  </select>

                  <button
                    type="submit"
                    disabled={loading}
                    style={{
                      padding: '7px 14px',
                      borderRadius: '6px',
                      backgroundColor: '#2563EB',
                      color: '#FFFFFF',
                      border: 'none',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {loading ? 'Generating...' : 'Generate Invite Link'}
                  </button>
                </div>
              </form>

              {/* Just Created Invite Link Box */}
              {lastCreatedInvite && (
                <div
                  style={{
                    padding: '12px 14px',
                    borderRadius: '8px',
                    backgroundColor: '#F0FDF4',
                    border: '1px solid #BBF7D0',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.74rem', fontWeight: 600, color: '#166534' }}>
                      ✓ Shareable Invitation Link for {lastCreatedInvite.email}:
                    </span>
                    <span style={{ fontSize: '0.64rem', color: '#15803D' }}>Valid for 7 days</span>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <input
                      type="text"
                      readOnly
                      value={lastCreatedInvite.invite_url}
                      style={{
                        flex: 1,
                        padding: '6px 10px',
                        borderRadius: '4px',
                        border: '1px solid #86EFAC',
                        backgroundColor: '#FFFFFF',
                        fontSize: '0.72rem',
                        color: '#166534',
                        fontFamily: 'monospace'
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => copyToClipboard(lastCreatedInvite.invite_url)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '4px',
                        backgroundColor: copiedLink ? '#16A34A' : '#15803D',
                        color: '#FFFFFF',
                        border: 'none',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      {copiedLink ? <Check size={12} /> : <Copy size={12} />}
                      <span>{copiedLink ? 'Copied!' : 'Copy Link'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* List of Pending Invites */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
                <span style={{ fontSize: '0.74rem', fontWeight: 600, color: '#475569' }}>
                  Pending Invitations ({invites.length})
                </span>

                {invitesLoading ? (
                  <div style={{ textAlign: 'center', padding: '16px', color: '#64748B', fontSize: '0.75rem' }}>
                    Loading invitations...
                  </div>
                ) : invites.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '16px', color: '#94A3B8', fontSize: '0.75rem', fontStyle: 'italic' }}>
                    No pending invitations for this workspace.
                  </div>
                ) : (
                  invites.map(inv => (
                    <div
                      key={inv.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        borderRadius: '6px',
                        border: '1px solid #E2E8F0',
                        backgroundColor: '#FFFFFF'
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#0F172A' }}>
                            {inv.email}
                          </span>
                          <span style={{ fontSize: '0.62rem', padding: '1px 5px', borderRadius: '4px', backgroundColor: '#EFF6FF', color: '#2563EB', fontWeight: 600 }}>
                            {inv.role.toUpperCase()}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.68rem', color: '#64748B', marginTop: '2px' }}>
                          Expires: {new Date(inv.expires_at).toLocaleDateString()}
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(inv.invite_url)}
                          title="Copy invite URL"
                          style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            backgroundColor: '#F1F5F9',
                            border: '1px solid #CBD5E1',
                            color: '#334155',
                            fontSize: '0.68rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          <Copy size={11} />
                          <span>Copy</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleRevokeInvite(inv.id)}
                          title="Revoke invitation"
                          style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            backgroundColor: '#FEF2F2',
                            border: '1px solid #FECACA',
                            color: '#DC2626',
                            fontSize: '0.68rem',
                            fontWeight: 600,
                            cursor: 'pointer'
                          }}
                        >
                          Revoke
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
