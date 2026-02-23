// config.js - Global Configuration
console.log('Loading config.js...');

// Get API URL from runtime environment or use empty string
const API_BASE_URL = window.RUNTIME_ENV?.SERVICE_API_BASE_URL || 'http://localhost:8000';
console.log('API_BASE_URL:', API_BASE_URL);

// Make it globally available
window.API_BASE_URL = API_BASE_URL;

// ===============================
// Load Google Picker config (from backend)
// ===============================
async function loadGoogleConfig() {
  try {
    const res = await fetch(`${window.API_BASE_URL}/auth/google-config`);
    if (!res.ok) {
      console.warn('Google config not available');
      return;
    }

    const data = await res.json();
    window.GOOGLE_CLIENT_ID = data.client_id;
    window.GOOGLE_API_KEY = data.api_key;

    console.log('✅ Google Picker config loaded');
  } catch (e) {
    console.warn('Failed to load Google Picker config', e);
  }
}

// expose globally
window.loadGoogleConfig = loadGoogleConfig;
window.loadGoogleConfig();