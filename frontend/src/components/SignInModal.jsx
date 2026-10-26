import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  X,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Building2,
  Lock
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function SignInModal() {
  const {
    isAuthModalOpen,
    setIsAuthModalOpen,
    loginWithSSO,
    loginWithGoogleCredential
  } = useAuth();

  const [loading, setLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const isPreviewBranch = typeof window !== 'undefined' &&
    window.location.hostname.includes('.vercel.app') &&
    !window.location.hostname.startsWith('context-trust-layer.vercel.app');

  const googleBtnRef = useRef(null);

  useEffect(() => {
    if (isPreviewBranch) return; // Skip GIS iframe on temporary preview branches to prevent origin_mismatch
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '727103176838-d6flfi3ef09448699or2n90opjjfn0us.apps.googleusercontent.com';
    if (window.google?.accounts?.id && googleBtnRef.current && isAuthModalOpen) {
      try {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (response) => {
            if (response.credential) {
              try {
                setLoading(true);
                setLoadingAction('Authenticating Google Account...');
                await loginWithGoogleCredential(response.credential);
                setSuccessMsg('Google authentication verified! Welcome.');
                setTimeout(() => setIsAuthModalOpen(false), 600);
              } catch (err) {
                setErrorMsg(err.message || 'Google Sign-In failed.');
              } finally {
                setLoading(false);
                setLoadingAction('');
              }
            }
          },
          auto_select: false,
        });
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: 'outline',
          size: 'large',
          type: 'standard',
          shape: 'rectangular',
          text: 'signin_with',
          logo_alignment: 'left',
          width: 340,
        });
      } catch (err) {
        console.warn('GIS button render error:', err);
      }
    }
  }, [googleBtnRef.current, isAuthModalOpen, isPreviewBranch]);

  if (!isAuthModalOpen) return null;

  const handleGoogleDirect = async (forceSandbox = false) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setLoadingAction(isPreviewBranch ? 'Connecting with Google Workspace...' : 'Authenticating with Google Workspace...');
    try {
      if (isPreviewBranch || forceSandbox) {
        // Instant Google Workspace access on PR preview links without needing Google Cloud origin whitelisting
        await loginWithSSO('google', {
          sandboxEmail: 'sarah.chen@google.com',
          sandboxName: 'Sarah Chen (Google Workspace)'
        });
      } else {
        await loginWithSSO('google');
      }
      setSuccessMsg('Authenticated successfully via Google!');
      setTimeout(() => setIsAuthModalOpen(false), 600);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to sign in via Google.');
    } finally {
      setLoading(false);
      setLoadingAction('');
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
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000,
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
          maxWidth: '460px',
          backgroundColor: '#FFFFFF',
          borderRadius: '14px',
          border: '1px solid #E2E8F0',
          boxShadow: '0 24px 48px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.04)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Top Accent Gradient Bar */}
        <div style={{ height: '4px', background: 'linear-gradient(90deg, #FFAB4A, #F5982C, #EA580C)' }} />

        {/* Modal Header */}
        <div
          style={{
            padding: '18px 22px 14px 22px',
            borderBottom: '1px solid #F1F5F9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FAFAFC'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <img 
              src="/Trulin-Main-NoBg.png" 
              alt="Trulin" 
              style={{ height: '28px', maxWidth: '120px', objectFit: 'contain' }} 
            />
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
              Enterprise Sign In
            </span>
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

        {/* Body Content: Exclusively Google Sign In */}
        <div style={{ padding: '24px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          {/* Google Brand Graphic */}
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '14px',
              backgroundColor: '#F8FAFC',
              border: '1px solid #E2E8F0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '14px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
            </svg>
          </div>

          <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0F172A', margin: '0 0 4px 0', textAlign: 'center' }}>
            Sign in with Google
          </h3>
          <p style={{ fontSize: '0.78rem', color: '#64748B', margin: '0 0 16px 0', textAlign: 'center', maxWidth: '340px' }}>
            Use your corporate Google Workspace or Google Account to access your enterprise organization and AI trust gateway.
          </p>

          {isPreviewBranch && (
            <div
              style={{
                marginBottom: '16px',
                padding: '5px 12px',
                borderRadius: '20px',
                backgroundColor: '#EFF6FF',
                border: '1px solid #BFDBFE',
                color: '#1E40AF',
                fontSize: '0.74rem',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#2563EB' }}></span>
              <span>Preview Branch</span>
              <span style={{ color: '#93C5FD' }}>•</span>
              <span>1-Click Google Workspace Session</span>
            </div>
          )}

          {/* Single Google Sign-In Action (no duplicate buttons, single Google icon) */}
          <div style={{ width: '100%', display: 'flex', justifyContent: 'center', marginTop: '4px' }}>
            {/* Direct Google button with Google Icon */}
            <button
              type="button"
              disabled={loading}
              onClick={handleGoogleDirect}
              style={{
                width: '100%',
                maxWidth: '300px',
                padding: '11px 18px',
                borderRadius: '8px',
                border: '1px solid #D1D5DB',
                backgroundColor: '#FFFFFF',
                color: '#1F2937',
                fontSize: '0.88rem',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.currentTarget.style.borderColor = '#9CA3AF';
                  e.currentTarget.style.backgroundColor = '#F9FAFB';
                }
              }}
              onMouseLeave={(e) => {
                if (!loading) {
                  e.currentTarget.style.borderColor = '#D1D5DB';
                  e.currentTarget.style.backgroundColor = '#FFFFFF';
                }
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
              </svg>
              <span>{loading ? (loadingAction || 'Connecting...') : 'Sign in with Google'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
