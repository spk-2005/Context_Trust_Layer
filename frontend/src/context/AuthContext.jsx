import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('ctl_token') || null);
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('ctl_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [organization, setOrganization] = useState(() => {
    try {
      const saved = localStorage.getItem('ctl_org');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [personas, setPersonas] = useState([]);
  const [ssoProviders, setSsoProviders] = useState([]);
  const [rbacMatrix, setRbacMatrix] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState('personas'); // 'personas' | 'login' | 'register' | 'sso'

  // 1. Fetch available personas, SSO providers, and RBAC matrix
  const refreshPersonas = async () => {
    try {
      const res = await fetch('/v1/auth/personas');
      if (res.ok) {
        const data = await res.json();
        setPersonas(data);
        if (!user && data.length > 0) {
          const defaultPersona = data.find(p => p.role === 'admin') || data[0];
          loginAsPersona(defaultPersona);
        }
        return data;
      }
    } catch (err) {
      console.warn('Failed to fetch personas:', err);
    }
    return [];
  };

  useEffect(() => {
    async function initAuth() {
      try {
        await refreshPersonas();
        // 2. Fetch SSO providers
        const ssoRes = await fetch('/v1/auth/sso/providers');
        if (ssoRes.ok) {
          const ssoData = await ssoRes.json();
          setSsoProviders(ssoData);
        }
        // 3. Fetch RBAC matrix
        const rbacRes = await fetch('/v1/auth/permissions/matrix');
        if (rbacRes.ok) {
          const rbacData = await rbacRes.json();
          setRbacMatrix(rbacData);
        }
      } catch (err) {
        console.warn('Failed to init auth metadata:', err);
      } finally {
        setIsLoading(false);
      }
    }
    initAuth();
  }, []);

  // Update granted permissions whenever active user changes
  useEffect(() => {
    if (!user) {
      setPermissions([]);
      return;
    }
    const roleKey = (user.role || '').toLowerCase();
    if (rbacMatrix?.roles?.[roleKey]?.permissions) {
      setPermissions(rbacMatrix.roles[roleKey].permissions);
    } else {
      // Local fallback until matrix finishes loading
      if (roleKey === 'admin') {
        setPermissions(['sources:read', 'sources:sync', 'sources:manage', 'claims:read', 'claims:extract', 'claims:edit', 'claims:delete', 'conflicts:read', 'conflicts:resolve', 'conflicts:override', 'decisions:evaluate', 'decisions:audit', 'org:settings', 'org:members', 'org:invite']);
      } else if (roleKey === 'data_owner') {
        setPermissions(['sources:read', 'sources:sync', 'sources:manage', 'claims:read', 'claims:extract', 'claims:edit', 'conflicts:read', 'decisions:evaluate', 'decisions:audit']);
      } else if (roleKey === 'reviewer') {
        setPermissions(['sources:read', 'claims:read', 'conflicts:read', 'conflicts:resolve', 'decisions:evaluate', 'decisions:audit']);
      } else if (roleKey === 'developer') {
        setPermissions(['sources:read', 'claims:read', 'conflicts:read', 'decisions:evaluate']);
      } else {
        setPermissions(['sources:read', 'claims:read', 'conflicts:read']);
      }
    }
  }, [user, rbacMatrix]);

  // 2. Validate token and load user profile if token exists
  useEffect(() => {
    if (!token) return;
    async function verifySession() {
      try {
        const res = await fetch('/v1/auth/me', {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const profile = await res.json();
          setUser(profile);
          localStorage.setItem('ctl_user', JSON.stringify(profile));
          if (profile.organization_id) {
            const orgData = {
              id: profile.organization_id,
              name: profile.organization_name || 'Enterprise Tenant'
            };
            setOrganization(orgData);
            localStorage.setItem('ctl_org', JSON.stringify(orgData));
          }
        } else if (res.status === 401) {
          // Token expired
          logout();
        }
      } catch (err) {
        console.warn('Error verifying session:', err);
      }
    }
    verifySession();
  }, [token]);

  const handleAuthSuccess = (data) => {
    const { access_token, user: userData } = data;
    setToken(access_token);
    setUser(userData);
    localStorage.setItem('ctl_token', access_token);
    localStorage.setItem('ctl_user', JSON.stringify(userData));
    if (userData.organization_id) {
      const orgData = {
        id: userData.organization_id,
        name: userData.organization_name || 'Enterprise Tenant'
      };
      setOrganization(orgData);
      localStorage.setItem('ctl_org', JSON.stringify(orgData));
    }
    setIsAuthModalOpen(false);
  };

  const login = async (email, password) => {
    const res = await fetch('/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Sign in failed. Check your credentials.');
    }
    const data = await res.json();
    handleAuthSuccess(data);
    return data;
  };

  const register = async (formData) => {
    const res = await fetch('/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Registration failed.');
    }
    const data = await res.json();
    handleAuthSuccess(data);
    return data;
  };

  const loginAsPersona = async (persona) => {
    try {
      const res = await fetch('/v1/auth/persona-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: persona.id })
      });
      if (res.ok) {
        const data = await res.json();
        handleAuthSuccess(data);
        return data;
      }
    } catch (err) {
      console.warn('Persona quick-login error:', err);
    }
    // Fallback: set local persona
    setUser(persona);
    localStorage.setItem('ctl_user', JSON.stringify(persona));
    setIsAuthModalOpen(false);
  };

  const loginWithSSO = async (provider, customOptions = {}) => {
    try {
      // 1. Inquire provider authorization endpoint
      const authRes = await fetch(`/v1/auth/sso/authorize/${provider}`);
      if (!authRes.ok) {
        const err = await authRes.json();
        throw new Error(err.detail || `Failed to initiate ${provider} SSO authorization`);
      }
      const authData = await authRes.json();

      if (!authData.is_sandbox && authData.authorization_url && !customOptions.sandboxEmail) {
        // Production live OAuth redirect
        window.location.href = authData.authorization_url;
        return;
      }

      // 2. Sandbox / Developer mock flow for instant local testing
      const callbackPayload = {
        provider,
        code: `sandbox_code_${Date.now()}`,
        mock_email: customOptions.sandboxEmail || (
          provider === 'google'
            ? 'sarah.chen@google.com'
            : provider === 'microsoft'
            ? 'marcus.vance@microsoft.com'
            : 'compliance@okta.com'
        ),
        mock_name: customOptions.sandboxName || (
          provider === 'google'
            ? 'Sarah Chen (Google Workspace)'
            : provider === 'microsoft'
            ? 'Marcus Vance (Entra ID)'
            : 'Enterprise Okta User'
        )
      };

      const cbRes = await fetch('/v1/auth/sso/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(callbackPayload)
      });

      if (!cbRes.ok) {
        const err = await cbRes.json();
        throw new Error(err.detail || 'SSO authentication failed');
      }

      const data = await cbRes.json();
      handleAuthSuccess(data);
      return data;
    } catch (err) {
      console.error('SSO login error:', err);
      throw err;
    }
  };

  const loginWithCorporateDomain = async (corporateEmail, fullName, organizationName) => {
    const res = await fetch('/v1/auth/sso/sandbox-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: 'sso',
        corporate_email: corporateEmail,
        full_name: fullName || undefined,
        organization_name: organizationName || undefined
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Corporate domain SSO failed.');
    }
    const data = await res.json();
    handleAuthSuccess(data);
    return data;
  };

  const switchOrganization = async (orgId) => {
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`/v1/organizations/${orgId}/switch`, {
      method: 'POST',
      headers,
      body: JSON.stringify({})
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to switch organization');
    }
    const data = await res.json();
    handleAuthSuccess({
      access_token: data.access_token,
      user: data.user
    });
    if (data.active_organization) {
      const orgObj = {
        id: data.active_organization.id,
        name: data.active_organization.name,
        slug: data.active_organization.slug,
        domain_whitelist: data.active_organization.domain_whitelist || [],
        member_count: data.active_organization.member_count || 0
      };
      setOrganization(orgObj);
      localStorage.setItem('ctl_org', JSON.stringify(orgObj));
      localStorage.setItem('context_layer_active_org_id', data.active_organization.id);
    }
    return data;
  };

  const hasPermission = (permissionKey) => {
    if (!permissions || permissions.length === 0) return false;
    return permissions.includes(permissionKey);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setOrganization(null);
    localStorage.removeItem('ctl_token');
    localStorage.removeItem('ctl_user');
    localStorage.removeItem('ctl_org');
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        organization,
        personas,
        ssoProviders,
        rbacMatrix,
        permissions,
        hasPermission,
        isLoading,
        isAuthenticated: !!token && !!user,
        isAuthModalOpen,
        setIsAuthModalOpen,
        authModalTab,
        setAuthModalTab,
        login,
        register,
        loginAsPersona,
        loginWithSSO,
        loginWithCorporateDomain,
        switchOrganization,
        logout,
        refreshPersonas,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
