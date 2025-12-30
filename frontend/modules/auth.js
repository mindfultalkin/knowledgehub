// modules/auth.js - Authentication & Google Drive (PRODUCTION FIXED)
console.log('Loading auth.js...');

// Check auth status - FIXED
async function checkAuthStatus() {
  try {
    const response = await fetch(`${window.API_BASE_URL}/api/auth/status`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    window.appState.authenticated = data.authenticated;
    return data;
  } catch (error) {
    console.error('Auth status check failed:', error);
    return { authenticated: false };
  }
}

// Initiate Google Auth - FIXED
async function initiateGoogleAuth() {
  try {
    const response = await fetch(`${window.API_BASE_URL}/api/auth/google`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    window.location.href = data.auth_url;
  } catch (error) {
    console.error('Auth initiation failed:', error);
    alert('Failed to start Google authentication. Please try again.');
  }
}

// Load files from Drive - FIXED
async function loadFiles() {
  if (!window.appState.authenticated) {
    return;
  }
  
  window.appState.loading = true;
  if (window.renderCurrentView) window.renderCurrentView();
  
  try {
    const response = await fetch(`${window.API_BASE_URL}/api/drive/files?page_size=100`);
    if (!response.ok) {
      throw new Error('Failed to load files');
    }
    
    const data = await response.json();
    window.appState.files = data.files || [];
    window.appState.filteredFiles = window.appState.files;
    window.appState.loading = false;
    
    if (window.renderCurrentView) window.renderCurrentView();
  } catch (error) {
    console.error('Failed to load files:', error);
    window.appState.loading = false;
    alert('Failed to load files. Please try again or reconnect to Google Drive.');
  }
}

// Load drive info - FIXED
async function loadDriveInfo() {
  if (!window.appState.authenticated) {
    return;
  }
  
  try {
    const response = await fetch(`${window.API_BASE_URL}/api/drive/connection-status`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    window.appState.driveInfo = data;
  } catch (error) {
    console.error('Failed to load drive info:', error);
  }
}

// Refresh files - FIXED
async function refreshFiles() {
  window.showNotification('🔄 Refreshing files from Google Drive...', 'info');

  try {
    const syncRes = await fetch(`${window.API_BASE_URL}/api/sync/drive-full`, { method: 'POST' });
    if (!syncRes.ok) {
      window.showNotification('❌ Sync failed. Check backend logs.', 'error');
      return;
    }

    const filesRes = await fetch(`${window.API_BASE_URL}/api/drive/files?page_size=100`);
    if (!filesRes.ok) throw new Error('Failed to load files');

    const data = await filesRes.json();
    window.appState.files = data.files || [];
    window.appState.filteredFiles = window.appState.files;
    if (window.renderCurrentView) window.renderCurrentView();
    window.showNotification('✅ Files refreshed', 'success');
  } catch (e) {
    console.error(e);
    window.showNotification('❌ Refresh failed', 'error');
  }
}

// Upload files
function uploadFiles() {
  window.showNotification('📤 Upload feature coming soon! Use Google Drive directly for now.', 'info');
}

// Voice record
function voiceRecord() {
  window.showNotification('🎤 Voice Recording feature coming soon!', 'info');
}

// Logout user - FIXED
async function logoutUser() {
  if (confirm('Are you sure you want to logout? You will need to reconnect to Google Drive.')) {
    try {
      // Clear local authentication state
      window.appState.authenticated = false;
      window.appState.files = [];
      window.appState.filteredFiles = [];
      window.appState.driveInfo = null;
      
      window.showNotification('🔓 Logging out...', 'info');
      
      // Clear any stored tokens from backend - FIXED
      try {
        await fetch(`${window.API_BASE_URL}/api/auth/logout`, {
          method: 'POST'
        });
      } catch (e) {
        console.log('Logout endpoint not available, clearing locally');
      }
      
      // Redirect to dashboard after short delay
      setTimeout(() => {
        window.appState.currentView = 'dashboard';
        if (window.renderCurrentView) window.renderCurrentView();
        
        // Update connection status
        const statusEl = document.getElementById('connectionStatus');
        if (statusEl) {
          statusEl.innerHTML = `
            <div class="status-dot" style="background: #ff9800;"></div>
            <span>Not Connected</span>
          `;
        }
        
        window.showNotification('✅ Logged out successfully!', 'success');
      }, 500);
      
    } catch (error) {
      console.error('Logout failed:', error);
      window.showNotification('❌ Logout failed. Please try again.', 'error');
    }
  }
}

// Make functions globally available
window.checkAuthStatus = checkAuthStatus;
window.initiateGoogleAuth = initiateGoogleAuth;
window.loadFiles = loadFiles;
window.loadDriveInfo = loadDriveInfo;
window.refreshFiles = refreshFiles;
window.uploadFiles = uploadFiles;
window.voiceRecord = voiceRecord;
window.logoutUser = logoutUser;

console.log('✅ auth.js loaded - all functions ready');

