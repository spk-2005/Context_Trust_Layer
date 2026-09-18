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

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>,
)
