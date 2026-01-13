// modules/auth.js - Authentication & Google Drive (SIMPLIFIED)
console.log('Loading auth.js...');

// Check auth status
async function checkAuthStatus() {
  try {
    const response = await fetch(`${window.API_BASE_URL}/auth/status`);
    const data = await response.json();
    window.appState.authenticated = data.authenticated;
    
    console.log('Auth status check:', data);
    
    // Update UI
    updateAuthUI(data.authenticated);
    
    return data;
  } catch (error) {
    console.error('Auth status check failed:', error);
    window.appState.authenticated = false;
    updateAuthUI(false);
    return { authenticated: false };
  }
}

// Update UI based on authentication status
function updateAuthUI(isAuthenticated) {
  const statusEl = document.getElementById('connectionStatus');
  if (statusEl) {
    if (isAuthenticated) {
      statusEl.innerHTML = `
        <div class="status-dot" style="background: #4CAF50;"></div>
        <span>Connected to Google Drive</span>
      `;
    } else {
      statusEl.innerHTML = `
        <div class="status-dot" style="background: #ff9800;"></div>
        <span>Not Connected</span>
      `;
    }
  }
}

// Initiate Google Auth
async function initiateGoogleAuth() {
  try {
    const response = await fetch(`${window.API_BASE_URL}/auth/google`);
    const data = await response.json();
    
    console.log('Redirecting to Google auth URL');
    window.location.href = data.auth_url;
    
  } catch (error) {
    console.error('Auth initiation failed:', error);
    if (window.showNotification) {
      window.showNotification('Failed to start Google authentication. Please try again.', 'error');
    }
  }
}

// Load files from Drive
async function loadFiles() {
  if (!window.appState.authenticated) {
    return;
  }
  
  window.appState.loading = true;
  if (window.renderCurrentView) window.renderCurrentView();
  
  try {
    // Try database first
    const response = await fetch(`${window.API_BASE_URL}/documents?limit=50`);
    if (response.ok) {
      const data = await response.json();
      window.appState.files = data.documents || [];
      window.appState.filteredFiles = window.appState.files;
      window.appState.loading = false;
      
      console.log(`Loaded ${window.appState.files.length} files from database`);
      
      if (window.renderCurrentView) window.renderCurrentView();
      return;
    }
    
    // Fallback to direct Drive API
    const driveResponse = await fetch(`${window.API_BASE_URL}/drive/files?page_size=100`);
    if (!driveResponse.ok) {
      throw new Error('Failed to load files');
    }
    
    const driveData = await driveResponse.json();
    window.appState.files = driveData.files || [];
    window.appState.filteredFiles = window.appState.files;
    window.appState.loading = false;
    
    console.log(`Loaded ${window.appState.files.length} files from Drive API`);
    
    if (window.renderCurrentView) window.renderCurrentView();
  } catch (error) {
    console.error('Failed to load files:', error);
    window.appState.loading = false;
    
    if (window.showNotification) {
      window.showNotification('Failed to load files. Please try refreshing.', 'error');
    }
  }
}

// Load drive info - REMOVED /auth/account-info call
async function loadDriveInfo() {
  if (!window.appState.authenticated) {
    return;
  }
  
  try {
    // Use the auth/status endpoint instead
    const response = await fetch(`${window.API_BASE_URL}/auth/status`);
    if (response.ok) {
      const data = await response.json();
      if (data.authenticated) {
        window.appState.accountInfo = {
          email: data.user?.email || 'Connected User',
          name: data.user?.displayName || 'Google Drive User'
        };
        console.log('Loaded account info:', window.appState.accountInfo.email);
      }
    }
  } catch (error) {
    console.error('Failed to load account info:', error);
  }
}

// Refresh files
async function refreshFiles() {
  if (!window.appState.authenticated) {
    if (window.showNotification) {
      window.showNotification('Please connect to Google Drive first', 'error');
    }
    return;
  }
  
  if (window.showNotification) {
    window.showNotification('Refreshing files from Google Drive...', 'info');
  }

  try {
    const syncRes = await fetch(`${window.API_BASE_URL}/sync/drive-full`, { method: 'POST' });
    const syncData = await syncRes.json();
    
    if (window.showNotification) {
      window.showNotification(syncData.message || 'Sync completed', 'success');
    }

    // Reload files after sync
    await loadFiles();
    
  } catch (e) {
    console.error(e);
    if (window.showNotification) {
      window.showNotification('Refresh failed. Please try again.', 'error');
    }
  }
}

// Logout user
async function logoutUser() {
  if (confirm('Are you sure you want to logout? You will need to reconnect to Google Drive.')) {
    try {
      // Clear local authentication state
      window.appState.authenticated = false;
      window.appState.files = [];
      window.appState.filteredFiles = [];
      window.appState.accountInfo = null;
      
      if (window.showNotification) {
        window.showNotification('Logging out...', 'info');
      }
      
      // Call backend logout
      try {
        await fetch(`${window.API_BASE_URL}/auth/logout`, {
          method: 'POST'
        });
      } catch (e) {
        console.log('Logout endpoint not available, clearing locally');
      }
      
      // Update UI
      updateAuthUI(false);
      
      // Redirect to dashboard
      if (window.navigateTo) {
        window.navigateTo('dashboard');
      }
      
      if (window.showNotification) {
        window.showNotification('Logged out successfully!', 'success');
      }
      
    } catch (error) {
      console.error('Logout failed:', error);
      if (window.showNotification) {
        window.showNotification('Logout failed. Please try again.', 'error');
      }
    }
  }
}

// Make functions globally available
window.checkAuthStatus = checkAuthStatus;
window.initiateGoogleAuth = initiateGoogleAuth;
window.loadFiles = loadFiles;
window.loadDriveInfo = loadDriveInfo;
window.refreshFiles = refreshFiles;
window.logoutUser = logoutUser;