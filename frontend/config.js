// config.js - Global Configuration
console.log('Loading config.js...');

// Get API URL from runtime environment or use empty string
const API_BASE_URL = window.RUNTIME_ENV?.SERVICE_API_BASE_URL || 'http://localhost:8000';
console.log('API_BASE_URL:', API_BASE_URL);

// Make it globally available
window.API_BASE_URL = API_BASE_URL;