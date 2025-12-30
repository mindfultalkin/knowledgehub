// LOCAL DEVELOPMENT CONFIGURATION (Default)
// window.RUNTIME_ENV = {
//   SERVICE_API_BASE_URL: 'http://localhost:8000/api',
//   FRONTEND_URL: 'http://localhost:5500',
//   ENVIRONMENT: 'development'
// };


// For production deployment, comment out the above and uncomment below
// 

// Runtime environment configuration for frontend
window.APP_CONFIG = {
    API_BASE_URL: window.location.origin + '/api',
    ENVIRONMENT: 'production',
    // Add other frontend configuration here
};

console.log('🚀 Knowledge Hub Frontend initialized'); 