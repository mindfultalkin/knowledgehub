// app.js - Main Application Entry Point (FIXED SYNTAX + DEFAULT LIST VIEW)
console.log('Loading app.js...');

// ✅ FIXED: Complete toggleFilesView function
window.toggleFilesView = function(viewType) {
  window.appState.filesView = viewType || 'list'; // Default to list
  
  // Re-render files view
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderFiles();
    setTimeout(() => {
      if (window.attachFileCardListeners) window.attachFileCardListeners();
    }, 100);
  }
  
  if (window.showNotification) {
    window.showNotification(`${viewType === 'list' ? 'List' : 'Grid'} view`, 'success');
  }
};

// ✅ FIXED: Complete toggleTemplatesView function  
window.toggleTemplatesView = function(viewType) {
  window.appState.filesView = viewType || 'list'; // Default to list
  
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderTemplates();
    setTimeout(() => window.loadTemplates(), 50);
  }
};

// Initialize filesView state - DEFAULT LIST VIEW
if (!window.appState.filesView) {
  window.appState.filesView = 'list';  // ✅ List is default
}

// Files view wrapper
window.showFilesView = function() {
  const sortedFiles = [...window.appState.files].sort((a, b) => {
    const aHasTags = (a.aiTags?.length > 0 || a.tagCount > 0) ? 0 : 1;
    const bHasTags = (b.aiTags?.length > 0 || b.tagCount > 0) ? 0 : 1;
    return aHasTags - bHasTags;
  }).slice(0, window.appState.filesPerPage || 96);
  
  window.appState.sortedFiles = sortedFiles;
  
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderFiles();
    setTimeout(() => {
      if (window.attachFileCardListeners) window.attachFileCardListeners();
    }, 100);
  }
};

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
        <img src="QL partners logo.jpeg" alt="Company Logo" class="app-logo">Knowledge Hub
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
              <span class="nav-icon"></span><span>Dashboard</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="templates" onclick="window.navigateTo('templates')">
              <span class="nav-icon"></span><span>Templates</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="clause-library" onclick="window.navigateTo('clause-library')">
              <span class="nav-icon"></span><span>Clauses</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="files" onclick="window.navigateTo('files')">
              <span class="nav-icon"></span><span>Resource</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="search" onclick="window.navigateTo('search')">
              <span class="nav-icon"></span><span>Search</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="settings" onclick="window.navigateTo('settings')">
              <span class="nav-icon"></span><span>Settings</span>
            </button>
          </li>
        </ul>
      </nav>
      
      <main class="main-content"></main>
    </div>
    
    <footer class="app-footer">
      <p>Powered by Mindfultalk. All rights reserved.</p>
    </footer>
  `;
  
  // Check authentication status
  try {
    if (window.checkAuthStatus) {
      const authStatus = await window.checkAuthStatus();
      const statusEl = document.getElementById('connectionStatus');
      if (statusEl) {
        if (authStatus.authenticated) {
          statusEl.innerHTML = `
            <div class="status-dot"></div>
            <span>Connected to Google Drive</span>
          `;
          if (window.loadFiles) await window.loadFiles();
          if (window.loadDriveInfo) await window.loadDriveInfo();
        } else {
          statusEl.innerHTML = `
            <div class="status-dot" style="background: #ff9800;"></div>
            <span>Not Connected</span>
          `;
        }
      }
    }
    
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('auth') === 'success') {
      window.history.replaceState({}, document.title, window.location.pathname);
      if (window.showNotification) window.showNotification('Connected successfully!', 'success');
    }
    
  } catch (error) {
    console.error('Initialization error:', error);
  }

  if (window.renderCurrentView) window.renderCurrentView();
}

// View wrapper functions
window.showDashboard = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent && window.renderDashboard) {
    mainContent.innerHTML = window.renderDashboard();
    setTimeout(() => {
      if (window.attachFileCardListeners) window.attachFileCardListeners();
      if (window.updateDashboardOnLoad) window.updateDashboardOnLoad();
    }, 200);
  }
};

window.showTemplatesView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent && window.renderTemplates) {
    mainContent.innerHTML = window.renderTemplates();
    setTimeout(() => window.loadTemplates(), 100);
  }
};

window.showSearchView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent && window.renderSearch) {
    mainContent.innerHTML = window.renderSearch();
  }
};

window.showAITagsView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent && window.renderAITags) {
    mainContent.innerHTML = window.renderAITags();
  }
};

window.showSettingsView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent && window.renderSettings) {
    mainContent.innerHTML = window.renderSettings();
  }
};

// Render current view
window.renderCurrentView = function() {
  switch (window.appState?.currentView) {
    case 'dashboard': window.showDashboard(); break;
    case 'templates': window.showTemplatesView(); break;
    case 'clause-library': if (window.showClauseLibrary) window.showClauseLibrary(); break;
    case 'files': window.showFilesView(); break;
    case 'search': window.showSearchView(); break;
    case 'ai-tags': window.showAITagsView(); break;
    case 'settings': window.showSettingsView(); break;
    default: window.showDashboard(); break;
  }
};

// Safe initialization
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM loaded, initializing app...');
  
  let retryCount = 0;
  const maxRetries = 20;
  
  function safeInit() {
    retryCount++;
    if (retryCount > maxRetries) {
      console.error('Max retries reached');
      return;
    }
    
    if (window.appState && document.getElementById('app-root')) {
      console.log('Dependencies ready');
      initApp();
    } else {
      setTimeout(safeInit, 200);
    }
  }
  
  safeInit();
});
