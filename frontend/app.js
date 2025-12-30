// app.js - Main Application Entry Point
console.log('Loading app.js...');

// Initialize application
async function initApp() {
  console.log('Initializing app...');
  
  const root = document.getElementById('app-root');
  if (!root) {
    console.error('App root not found');
    return;
  }
  
  root.innerHTML = `
    <header class="app-header">
      <div class="app-title">
        🎓 Knowledge Hub
      </div>
      <div class="connection-status" id="connectionStatus">
        <div class="status-dot" style="background: #666;"></div>
        <span>Checking connection...</span>
      </div>
    </header>
    
    <div class="app-container">
      <nav class="sidebar">
        <ul class="nav-menu">
          <li class="nav-item">
            <button class="nav-link active" data-view="dashboard" onclick="window.navigateTo('dashboard')">
              <span class="nav-icon">📊</span>
              <span>Dashboard</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="search" onclick="window.navigateTo('search')">
              <span class="nav-icon">🔍</span>
              <span>Search</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="files" onclick="window.navigateTo('files')">
              <span class="nav-icon">📁</span>
              <span>Files</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="ai-tags" onclick="window.navigateTo('ai-tags')">
              <span class="nav-icon">🏷️</span>
              <span>AI Tags</span>
            </button>
          </li>
          <li class="nav-item">
              <button class="nav-link" data-view="clause-library" onclick="window.navigateTo('clause-library')">
                  <span class="nav-icon">📋</span>
                  <span>Clauses</span>
              </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="settings" onclick="window.navigateTo('settings')">
              <span class="nav-icon">⚙️</span>
              <span>Settings</span>
            </button>
          </li>
        </ul>
      </nav>
      
      <main class="main-content"></main>
    </div>
    
    <footer class="app-footer">
      <p>Knowledge Hub © 2025 | Connected to Your Google Drive | Version 1.0.0</p>
    </footer>
  `;
  
  // Check authentication status
  try {
    const authStatus = await window.checkAuthStatus();
    
    const statusEl = document.getElementById('connectionStatus');
    if (statusEl) {
      if (authStatus.authenticated) {
        statusEl.innerHTML = `
          <div class="status-dot"></div>
          <span>Connected to Google Drive</span>
        `;
        await window.loadFiles();
        await window.loadDriveInfo();
      } else {
        statusEl.innerHTML = `
          <div class="status-dot" style="background: #ff9800;"></div>
          <span>Not Connected</span>
        `;
      }
    }
    
    // Handle auth success redirect
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('auth') === 'success') {
      window.history.replaceState({}, document.title, window.location.pathname);
      window.showNotification('✅ Connected successfully!', 'success');
    }
    
  } catch (error) {
    console.error('Initialization error:', error);
    const statusEl = document.getElementById('connectionStatus');
    if (statusEl) {
      statusEl.innerHTML = `
        <div class="status-dot" style="background: #f44336;"></div>
        <span>Connection Error</span>
      `;
    }
  }

  // Render initial view
  window.renderCurrentView();
}

// View wrapper functions
window.showDashboard = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderDashboard();
    window.attachFileCardListeners();
  }
};

window.showSearchView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderSearch();
    window.attachFileCardListeners();
  }
};

window.showFilesView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderFiles();
    window.attachFileCardListeners();
  }
};

window.showAITagsView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderAITags();
  }
};

window.showSettingsView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderSettings();
  }
};

// Render current view
window.renderCurrentView = function() {
  switch (window.appState.currentView) {
    case 'dashboard':
      window.showDashboard();
      break;
    case 'search':
      window.showSearchView();
      break;
    case 'files':
      window.showFilesView();
      break;
    case 'ai-tags':
      window.showAITagsView();
      break;
    case 'clause-library':
      window.showClauseLibrary();
      break;
    case 'settings':
      window.showSettingsView();
      break;
    default:
      window.showDashboard();
  }
};

// Add CSS for search type buttons
const searchStyle = document.createElement('style');
searchStyle.textContent = `
  .search-type-button {
    padding: 10px 20px;
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 2px solid transparent;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
    font-weight: 600;
  }
  
  .search-type-button.active {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-dark);
  }
  
  .search-type-button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
  }
`;
document.head.appendChild(searchStyle);

// Animations CSS
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from { transform: translateX(400px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  @keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(400px); opacity: 0; }
  }
  
  .action-button {
    padding: 8px 16px;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
  }
  
  .action-button:hover {
    background: var(--primary-dark);
    transform: translateY(-2px);
  }
  
  .theme-button {
    flex: 1;
    padding: 12px;
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 2px solid transparent;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 600;
  }
  
  .theme-button.active {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-dark);
  }
  
  .theme-button:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
  
  /* Dark theme */
  [data-theme="dark"] {
    --bg-primary: #111111ff;
    --bg-secondary: #080808ff;
    --bg-tertiary: #0f3460;
    --text-primary: #eaeaea;
    --text-secondary: #a0a0a0;
    --border-color: #2d2d44;
  }
  
  [data-theme="dark"] .app-header {
    background: linear-gradient(135deg, #080808ff, #000000ff);
  }
  
  [data-theme="dark"] .sidebar {
    background: #000000ff;
  }
  
  /* Grid sizes */
  [data-grid-size="small"] .files-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }
  
  [data-grid-size="large"] .files-grid {
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  }
`;
document.head.appendChild(style);

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM loaded, initializing app...');
  
  // Small delay to ensure all modules are loaded
  setTimeout(() => {
    initApp().catch(error => {
      console.error('Failed to initialize app:', error);
      const root = document.getElementById('app-root');
      if (root) {
        root.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: red;">
                <h2>Application Error</h2>
                <p>${error.message}</p>
                <p>Please check console for details</p>
                <button onclick="location.reload()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #2196f3; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    Reload Page
                </button>
            </div>
        `;
      }
    });
  }, 100);
});