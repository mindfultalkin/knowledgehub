// config.js - FIXED for Production
console.log('Loading config.js...');

// Production Railway URL
const RAILWAY_URL = 'https://knowledgehub-production-9572.up.railway.app';

// Auto-detect environment
let API_BASE_URL;
if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    // Production - use Railway
    API_BASE_URL = RAILWAY_URL;
    console.log('🌐 Production mode - API:', API_BASE_URL);
} else {
    // Local development
    API_BASE_URL = 'http://localhost:8000';
    console.log('🏠 Local mode - API:', API_BASE_URL);
}

// Railway env var fallback
if (window.RUNTIME_ENV?.SERVICE_API_BASE_URL) {
    API_BASE_URL = window.RUNTIME_ENV.SERVICE_API_BASE_URL;
}

console.log('✅ Final API_BASE_URL:', API_BASE_URL);
window.API_BASE_URL = API_BASE_URL;
