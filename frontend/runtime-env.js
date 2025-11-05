// LOCAL DEVELOPMENT CONFIGURATION (Default)

window.RUNTIME_ENV = {
  SERVICE_API_BASE_URL: 'http://localhost:8000/api',
  FRONTEND_URL: 'http://localhost:5500',
  ENVIRONMENT: 'development'
};


// For production deployment, comment out the above and uncomment below
/*
window.RUNTIME_ENV = {
  SERVICE_API_BASE_URL: 'https://knowledgehub-eta.vercel.app/api',
  FRONTEND_URL: 'https://knowledgehub-eta.vercel.app',
  ENVIRONMENT: 'production'
};
*/