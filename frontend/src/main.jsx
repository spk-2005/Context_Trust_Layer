import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { AuthProvider } from './context/AuthContext'

// Direct API calls to backend base URL and automatically inject Bearer auth token
const apiBase = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_BACKEND_URL || '').replace(/\/+$/, '');

const originalFetch = window.fetch;
window.fetch = (input, init = {}) => {
  let url = input;
  if (apiBase && typeof input === 'string' && input.startsWith('/v1')) {
    url = `${apiBase}${input}`;
  }
  const token = localStorage.getItem('ctl_token');
  if (token) {
    init.headers = {
      ...(init.headers || {}),
      'Authorization': `Bearer ${token}`
    };
  }
  return originalFetch(url, init);
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
