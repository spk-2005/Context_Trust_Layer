import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { AuthProvider } from './context/AuthContext'

// Inject Bearer auth token into all /v1/* API requests.
// NOTE: Never prepend a base URL here — the browser cannot resolve the Docker-internal
// hostname 'backend'. Vite's dev-server proxy (vite.config.js) transparently forwards
// relative /v1/* requests to http://backend:8000 inside the Docker network.
const originalFetch = window.fetch;
window.fetch = async (input, init = {}) => {
  const token = localStorage.getItem('ctl_token');
  const deviceId = localStorage.getItem('ctl_device_id') || 'dev_client';

  if (!init.headers) {
    init.headers = {};
  }
  if (init.headers instanceof Headers) {
    if (token && !init.headers.has('Authorization')) {
      init.headers.set('Authorization', `Bearer ${token}`);
    }
    if (!init.headers.has('X-Device-Id')) {
      init.headers.set('X-Device-Id', deviceId);
    }
  } else if (Array.isArray(init.headers)) {
    if (token) init.headers.push(['Authorization', `Bearer ${token}`]);
    init.headers.push(['X-Device-Id', deviceId]);
  } else {
    if (token && !init.headers['Authorization']) {
      init.headers['Authorization'] = `Bearer ${token}`;
    }
    if (!init.headers['X-Device-Id']) {
      init.headers['X-Device-Id'] = deviceId;
    }
  }

  const response = await originalFetch(input, init);
  if (response.status === 401) {
    try {
      const clone = response.clone();
      const err = await clone.json();
      if (err?.detail && typeof err.detail === 'string' && err.detail.includes('SESSION_SUPERSEDED')) {
        localStorage.removeItem('ctl_token');
        if (typeof BroadcastChannel !== 'undefined') {
          const bc = new BroadcastChannel('ctl_sync_channel');
          bc.postMessage({ type: 'SESSION_SUPERSEDED' });
          bc.close();
        }
      }
    } catch {}
  }
  return response;
};

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("Trulin ErrorBoundary caught error:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#0B0F19',
          color: '#F8FAFC',
          fontFamily: 'Inter, sans-serif',
          padding: '24px'
        }}>
          <div style={{
            maxWidth: '560px',
            background: '#161E2E',
            border: '1px solid #E2881E',
            borderRadius: '14px',
            padding: '32px',
            textAlign: 'center',
            boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
          }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '16px' }}>🛡️</div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '8px' }}>
              Trulin Session Restored
            </h2>
            <p style={{ color: '#94A3B8', fontSize: '0.9rem', marginBottom: '20px' }}>
              {this.state.error?.message || "An unexpected error occurred during rendering."}
            </p>
            <button
              onClick={() => { localStorage.clear(); window.location.href = '/'; }}
              style={{
                background: 'linear-gradient(135deg, #FFAB4A 0%, #F5982C 100%)',
                color: '#1A1207',
                border: 'none',
                padding: '10px 24px',
                borderRadius: '8px',
                fontWeight: 700,
                fontSize: '0.9rem',
                cursor: 'pointer'
              }}
            >
              Reload Trulin Dashboard
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <App />
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
