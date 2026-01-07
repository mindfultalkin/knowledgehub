// app.js - Main Application Entry Point (FIXED LIST/GRID)
console.log('Loading app.js...');

// LIST/GRID TOGGLE FUNCTIONS - ADD FIRST
window.toggleFilesView = function(viewType) {
  window.appState.filesView = viewType || 'grid';
  
  // Re-render files view
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderFiles();
    setTimeout(() => {
      if (window.attachFileCardListeners) window.attachFileCardListeners();
    }, 100);
  }
  
  // Update button states
  setTimeout(() => {
    document.querySelectorAll('[onclick*="toggleFilesView"]').forEach(btn => {
      btn.classList.toggle('active-view-btn', 
        (viewType === 'grid' && btn.textContent.includes('Grid')) ||
        (viewType === 'list' && btn.textContent.includes('List'))
      );
    });
  }, 150);
  
  if (window.showNotification) {
    window.showNotification(`${viewType === 'list' ? 'List' : 'Grid'} view`, 'success');
  }
};

// Initialize filesView state
if (!window.appState.filesView) {
  window.appState.filesView = 'list';  // List is now default for ALL file views
}

// Files view wrapper
window.showFilesView = function() {
  // TAGGED FILES FIRST - PERFECT SORTING
  const sortedFiles = [...window.appState.files].sort((a, b) => {
    const aHasTags = (a.aiTags?.length > 0 || a.tagCount > 0) ? 0 : 1;
    const bHasTags = (b.aiTags?.length > 0 || b.tagCount > 0) ? 0 : 1;
    return aHasTags - bHasTags; // Tagged = 0 (top), No tags = 1 (bottom)
  }).slice(0, window.appState.filesPerPage || 24);
  
  // Temporarily store sorted files for renderFiles()
  window.appState.sortedFiles = sortedFiles;
  
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderFiles();
    setTimeout(() => {
      if (window.attachFileCardListeners) window.attachFileCardListeners();
    }, 100);
  }
};

window.toggleTemplatesView = function(viewType) {
  window.appState.filesView = viewType || 'list';
  
  // Re-render + immediately reload data
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = window.renderTemplates();
    // Load data immediately after render
    setTimeout(() => window.loadTemplates(), 50);
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
            <button class="nav-link" data-view="files" onclick="window.navigateTo('files'); window.appState.filesView='list';">
              <span class="nav-icon"></span><span>Files</span>
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
      <p>Knowledge Hub © 2025 | Connected to Your Google Drive | Version 1.0.0</p>
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
    
    // Handle auth success redirect
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('auth') === 'success') {
      window.history.replaceState({}, document.title, window.location.pathname);
      if (window.showNotification) window.showNotification('Connected successfully!', 'success');
    }
    
  } catch (error) {
    console.error('Initialization error:', error);
  }

  // Render initial view
  if (window.renderCurrentView) window.renderCurrentView();
}

// Template Library View
window.showTemplatesView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent && window.renderTemplates) {
    mainContent.innerHTML = window.renderTemplates();
    // Always load data after render
    setTimeout(() => window.loadTemplates(), 100);
  }
};

// View wrapper functions
window.showDashboard = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent && window.renderDashboard) {
    mainContent.innerHTML = window.renderDashboard();
    if (window.attachFileCardListeners) window.attachFileCardListeners();
  }
};

window.showSearchView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent && window.renderSearch) {
    mainContent.innerHTML = window.renderSearch();
    if (window.attachFileCardListeners) window.attachFileCardListeners();
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
    
    // Check core dependencies
    if (window.appState && document.getElementById('app-root')) {
      console.log('Dependencies ready');
      initApp();
    } else {
      setTimeout(safeInit, 200);
    }
  }
  
  safeInit();
});