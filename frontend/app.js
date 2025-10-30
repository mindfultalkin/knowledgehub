// Knowledge Hub - Enhanced Frontend with All Features

const API_BASE_URL = window.RUNTIME_ENV?.SERVICE_API_BASE_URL;
console.log('API_BASE_URL:', API_BASE_URL);
// Application State
const appState = {
  currentView: 'dashboard',
  authenticated: false,
  files: [],
  filteredFiles: [],
  searchQuery: '',
  selectedFileType: 'all',
  selectedAuthor: 'all',
  sortBy: 'modifiedTime',
  driveInfo: null,
  loading: false,
  theme: localStorage.getItem('theme') || 'light',
  gridSize: localStorage.getItem('gridSize') || 'medium',
  filesPerPage: parseInt(localStorage.getItem('filesPerPage')) || 24
};

// Apply theme on load
document.documentElement.setAttribute('data-theme', appState.theme);

// Utility Functions
function formatDate(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
}

function formatFileSize(bytes) {
  if (!bytes || bytes === '0') return 'N/A';
  const numBytes = parseInt(bytes);
  if (numBytes < 1024) return numBytes + ' B';
  if (numBytes < 1024 * 1024) return (numBytes / 1024).toFixed(1) + ' KB';
  if (numBytes < 1024 * 1024 * 1024) return (numBytes / (1024 * 1024)).toFixed(1) + ' MB';
  return (numBytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

function getFileIcon(mimeType, fileName = '') {
  const nameLower = fileName.toLowerCase();
  
  // Check filename first for better categorization
  if (nameLower.includes('contract') || nameLower.includes('agreement')) {
    return '📜'; // Contract/Agreement
  }
  if (nameLower.includes('rental') || nameLower.includes('lease')) {
    return '🏠'; // Rental/Lease
  }
  if (nameLower.includes('employment') || nameLower.includes('employee')) {
    return '👔'; // Employment
  }
  if (nameLower.includes('clause')) {
    return '📋'; // Clause
  }
  if (nameLower.includes('note') || nameLower.includes('memo')) {
    return '📝'; // Note/Memo
  }
  if (nameLower.includes('practice')) {
    return '⚖️'; // Practice (Legal)
  }
  if (nameLower.includes('template')) {
    return '📄'; // Template
  }
  if (nameLower.includes('invoice') || nameLower.includes('bill')) {
    return '🧾'; // Invoice/Bill
  }
  if (nameLower.includes('receipt')) {
    return '🧾'; // Receipt
  }
  if (nameLower.includes('report')) {
    return '📊'; // Report
  }
  if (nameLower.includes('certificate') || nameLower.includes('cert')) {
    return '🎓'; // Certificate
  }
  if (nameLower.includes('license') || nameLower.includes('licence')) {
    return '🪪'; // License
  }
  if (nameLower.includes('form')) {
    return '📋'; // Form
  }
  if (nameLower.includes('letter')) {
    return '✉️'; // Letter
  }
  
  // Then check MIME type
  if (!mimeType) return '📄';
  
  // Images
  if (mimeType.includes('image/png')) return '🖼️';
  if (mimeType.includes('image/jpeg') || mimeType.includes('image/jpg')) return '📷';
  if (mimeType.includes('image/gif')) return '🎞️';
  if (mimeType.includes('image/svg')) return '🎨';
  if (mimeType.includes('image')) return '🖼️';
  
  // Videos
  if (mimeType.includes('video/mp4')) return '🎬';
  if (mimeType.includes('video/quicktime') || mimeType.includes('video/mov')) return '🎥';
  if (mimeType.includes('video')) return '🎥';
  
  // Audio
  if (mimeType.includes('audio/mpeg') || mimeType.includes('audio/mp3')) return '🎵';
  if (mimeType.includes('audio/wav')) return '🎙️';
  if (mimeType.includes('audio')) return '🎵';
  
  // Documents
  if (mimeType.includes('pdf')) return '📕';
  if (mimeType.includes('msword') || mimeType.includes('wordprocessingml')) return '📘';
  if (mimeType.includes('document')) return '📄';
  
  // Spreadsheets
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return '📊';
  if (mimeType.includes('csv')) return '📈';
  
  // Presentations
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return '📽️';
  
  // Archives
  if (mimeType.includes('zip')) return '🗜️';
  if (mimeType.includes('rar')) return '📦';
  if (mimeType.includes('archive')) return '🗜️';
  
  // Code files
  if (mimeType.includes('text/html')) return '🌐';
  if (mimeType.includes('text/css')) return '🎨';
  if (mimeType.includes('javascript')) return '⚡';
  if (mimeType.includes('text/x-')) return '💻';
  
  // Text files
  if (mimeType.includes('text/plain')) return '📃';
  if (mimeType.includes('text')) return '📄';
  
  // Folders
  if (mimeType.includes('folder')) return '📁';
  
  // Default
  return '📄';
}


// Theme Functions
function toggleTheme() {
  appState.theme = appState.theme === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', appState.theme);
  localStorage.setItem('theme', appState.theme);
  renderCurrentView();
}

function changeGridSize(size) {
  appState.gridSize = size;
  localStorage.setItem('gridSize', size);
  document.documentElement.setAttribute('data-grid-size', size);
  renderCurrentView();
}

function changeFilesPerPage(count) {
  appState.filesPerPage = parseInt(count);
  localStorage.setItem('filesPerPage', count);
  renderCurrentView();
}

// API Functions
async function checkAuthStatus() {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/status`);
    const data = await response.json();
    appState.authenticated = data.authenticated;
    return data;
  } catch (error) {
    console.error('Auth status check failed:', error);
    return { authenticated: false };
  }
}

async function initiateGoogleAuth() {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/google`);
    const data = await response.json();
    window.location.href = data.auth_url;
  } catch (error) {
    console.error('Auth initiation failed:', error);
    alert('Failed to start Google authentication. Please try again.');
  }
}

async function loadFiles() {
  if (!appState.authenticated) {
    return;
  }
  
  appState.loading = true;
  renderCurrentView();
  
  try {
    const response = await fetch(`${API_BASE_URL}/drive/files?page_size=100`);
    if (!response.ok) {
      throw new Error('Failed to load files');
    }
    
    const data = await response.json();
    appState.files = data.files || [];
    appState.filteredFiles = appState.files;
    appState.loading = false;
    
    renderCurrentView();
  } catch (error) {
    console.error('Failed to load files:', error);
    appState.loading = false;
    alert('Failed to load files. Please try again or reconnect to Google Drive.');
  }
}

async function loadDriveInfo() {
  if (!appState.authenticated) {
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/drive/connection-status`);
    const data = await response.json();
    appState.driveInfo = data;
  } catch (error) {
    console.error('Failed to load drive info:', error);
  }
}

function refreshFiles() {
  showNotification('🔄 Refreshing files from Google Drive...', 'info');
  loadFiles();
  loadDriveInfo();
  setTimeout(() => {
    showNotification('✅ Files refreshed successfully!', 'success');
  }, 1000);
}

function uploadFiles() {
  showNotification('📤 Upload feature coming soon! Use Google Drive directly for now.', 'info');
}
function voiceRecord() {
  showNotification('🎤 Voice Recording feature coming soon!', 'info');
}

async function logoutUser() {
  if (confirm('Are you sure you want to logout? You will need to reconnect to Google Drive.')) {
    try {
      // Clear local authentication state
      appState.authenticated = false;
      appState.files = [];
      appState.filteredFiles = [];
      appState.driveInfo = null;
      
      // Show notification
      showNotification('🔓 Logging out...', 'info');
      
      // Clear any stored tokens from backend
      try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST'
        });
      } catch (e) {
        console.log('Logout endpoint not available, clearing locally');
      }
      
      // Redirect to dashboard after short delay
      setTimeout(() => {
        appState.currentView = 'dashboard';
        renderCurrentView();
        
        // Update connection status
        const statusEl = document.getElementById('connectionStatus');
        if (statusEl) {
          statusEl.innerHTML = `
            <div class="status-dot" style="background: #ff9800;"></div>
            <span>Not Connected</span>
          `;
        }
        
        showNotification('✅ Logged out successfully!', 'success');
      }, 500);
      
    } catch (error) {
      console.error('Logout failed:', error);
      showNotification('❌ Logout failed. Please try again.', 'error');
    }
  }
}



function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
    color: white;
    padding: 16px 24px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 1000;
    animation: slideIn 0.3s ease;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// View Rendering Functions
// View Rendering Functions
function renderDashboard() {
  // Calculate custom stats for legal documents with better detection
  const stats = {
    totalFiles: appState.files.length,
    contracts: appState.files.filter(f => {
      const name = f.name.toLowerCase();
      const tags = (f.aiTags || []).map(t => t.toLowerCase());
      return name.includes('contract') || 
             name.includes('agreement') || 
             tags.some(tag => tag.includes('contract') || tag.includes('agreement'));
    }).length,
    clauses: appState.files.filter(f => {
      const name = f.name.toLowerCase();
      const tags = (f.aiTags || []).map(t => t.toLowerCase());
      return name.includes('clause') || 
             tags.some(tag => tag.includes('clause'));
    }).length,
    practiceNotes: appState.files.filter(f => {
      const name = f.name.toLowerCase();
      const tags = (f.aiTags || []).map(t => t.toLowerCase());
      return (name.includes('practice') && (name.includes('note') || name.includes('memo'))) || 
             name.includes('practice note') ||
             tags.some(tag => tag.includes('practice') && (tag.includes('note') || tag.includes('memo')));
    }).length
  };
  
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">📊 Knowledge Hub Dashboard</h1>
        <p class="view-subtitle">Your Google Drive Connection</p>
      </div>
      
      ${!appState.authenticated ? `
        <div class="auth-container">
          <div class="auth-card">
            <h2>🔐 Connect to Your Google Drive</h2>
            <p>Click the button below to securely connect your Google Drive account.</p>
            <button class="connect-button" onclick="initiateGoogleAuth()">
              Connect to Google Drive
            </button>
          </div>
        </div>
      ` : `
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon">📁</div>
            <div class="stat-number">${stats.totalFiles}</div>
            <div class="stat-label">Total Files</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📜</div>
            <div class="stat-number">${stats.contracts}</div>
            <div class="stat-label">Contracts</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📋</div>
            <div class="stat-number">${stats.clauses}</div>
            <div class="stat-label">Clauses</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">⚖️</div>
            <div class="stat-number">${stats.practiceNotes}</div>
            <div class="stat-label">Practice Notes</div>
          </div>
        </div>
        
        ${appState.driveInfo ? `
          <div class="card mb-lg">
            <h2 class="card-title">☁️ Google Drive Connection</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; align-items: center;">
              <div>
                <strong>Account:</strong> ${appState.driveInfo.user?.email || 'Connected'}
              </div>
              <div>
                <strong>Status:</strong> <span style="color: #4caf50;">✓ Connected</span>
              </div>
              <div>
                <strong>Total Files:</strong> ${stats.totalFiles}
              </div>
              <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button class="action-button" onclick="refreshFiles()">🔄 Refresh Drive</button>
                <button class="action-button" onclick="uploadFiles()">📤 Upload Files</button>
                <button class="action-button voice-button" onclick="voiceRecord()" title="Voice Recording">
                  🎤 Voice Record
                </button>
              </div>
            </div>
          </div>
        ` : ''}
        
        <h2 class="view-title" style="margin-top: 32px;">📌 Recent Files</h2>
        ${appState.loading ? '<div class="loading"><div class="spinner"></div></div>' : `
          <div class="files-grid">
            ${appState.files.slice(0, 6).map(file => renderFileCard(file)).join('')}
          </div>
        `}
      `}
    </div>
  `;
}



function renderFileCard(file) {
  // Pass both mimeType and fileName for better icon detection
  const icon = `<div style="font-size:3.5rem;">${getFileIcon(file.mimeType, file.name)}</div>`;
  
  // Get all tags (no limit)
  const allTags = file.aiTags || [];
  
  return `
    <div class="file-card" onclick='viewFile(${JSON.stringify(file).replace(/'/g, "&apos;")})'>
      <div class="file-thumbnail">${icon}</div>
      <div class="file-info">
        <div class="file-name" title="${file.name}">${file.name}</div>
        <div class="file-meta">
          <span>👤 ${file.owner}</span>
          <span>📅 ${formatDate(file.modifiedTime)}</span>
          <span>💾 ${formatFileSize(file.size)}</span>
        </div>
        <div class="file-tags">
          ${allTags.map(tag => `<span class="tag">${tag}</span>`).join('')}
        </div>
      </div>
    </div>
  `;
}




function renderSearch() {
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">🔍 Search Your Drive</h1>
        <p class="view-subtitle">Find files quickly</p>
      </div>
      
      ${!appState.authenticated ? `
        <div class="auth-container">
          <p>Please connect to Google Drive first</p>
          <button class="connect-button" onclick="navigateTo('dashboard')">Go to Dashboard</button>
        </div>
      ` : `
        <div class="search-section">
          <div class="search-bar">
            <input 
              type="text" 
              class="search-input" 
              placeholder="Search files by name..."
              oninput="handleSearch(event)"
              value="${appState.searchQuery}"
            >
            <button class="search-button" onclick="performSearch()">Search</button>
          </div>
          
          <div class="filters-container">
            <div class="filter-group">
              <label class="filter-label">File Type</label>
              <select class="filter-select" onchange="handleFileTypeFilter(event)">
                <option value="all">All Types</option>
                <option value="document">Documents</option>
                <option value="image">Images</option>
                <option value="video">Videos</option>
                <option value="audio">Audio</option>
              </select>
            </div>
            
            <div class="filter-group">
              <label class="filter-label">Sort By</label>
              <select class="filter-select" onchange="handleSortChange(event)">
                <option value="modifiedTime">Date Modified</option>
                <option value="name">Name</option>
                <option value="size">Size</option>
              </select>
            </div>
          </div>
        </div>
        
        <div style="margin: 24px 0;">
          <h2 class="view-title">Results (${appState.filteredFiles.length})</h2>
        </div>
        
        ${appState.loading ? '<div class="loading"><div class="spinner"></div></div>' : 
          appState.filteredFiles.length > 0 ? `
            <div class="files-grid">
              ${appState.filteredFiles.slice(0, appState.filesPerPage).map(file => renderFileCard(file)).join('')}
            </div>
          ` : `
            <div class="empty-state">
              <div class="empty-state-icon">🔍</div>
              <h3>No files found</h3>
              <p>Try adjusting your search criteria</p>
            </div>
          `}
      `}
    </div>
  `;
}

function renderFiles() {
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">📁 All Files</h1>
        <p class="view-subtitle">Browse your Google Drive</p>
      </div>
      
      ${!appState.authenticated ? `
        <div class="auth-container">
          <p>Please connect to Google Drive first</p>
          <button class="connect-button" onclick="navigateTo('dashboard')">Go to Dashboard</button>
        </div>
      ` : appState.loading ? '<div class="loading"><div class="spinner"></div></div>' : `
        <div class="files-grid">
          ${appState.files.slice(0, appState.filesPerPage).map(file => renderFileCard(file)).join('')}
        </div>
        ${appState.files.length > appState.filesPerPage ? `
          <div style="text-align: center; margin-top: 24px;">
            <p style="color: var(--text-secondary);">
              Showing ${appState.filesPerPage} of ${appState.files.length} files
            </p>
          </div>
        ` : ''}
      `}
    </div>
  `;
}

function renderAITags() {
  const allTags = {};
  appState.files.forEach(file => {
    (file.aiTags || []).forEach(tag => {
      allTags[tag] = (allTags[tag] || 0) + 1;
    });
  });
  
  const sortedTags = Object.entries(allTags).sort((a, b) => b[1] - a[1]);
  
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">🏷️ AI Tags</h1>
        <p class="view-subtitle">Auto-generated content tags</p>
      </div>
      
      ${!appState.authenticated ? `
        <div class="auth-container">
          <p>Please connect to Google Drive first</p>
          <button class="connect-button" onclick="navigateTo('dashboard')">Go to Dashboard</button>
        </div>
      ` : sortedTags.length > 0 ? `
        <div class="card mb-lg">
          <h2 class="card-title">Tag Cloud</h2>
          <div class="tag-cloud">
            ${sortedTags.map(([tag, count]) => `
              <span 
                class="tag-cloud-item" 
                style="font-size: ${Math.min(0.875 + (count * 0.25), 2)}rem;"
                onclick="searchByTag('${tag}')"
              >
                ${tag} (${count})
              </span>
            `).join('')}
          </div>
        </div>
        
        <div class="card">
          <h2 class="card-title">📊 Tag Statistics</h2>
          <div style="display: grid; gap: 12px;">
            ${sortedTags.slice(0, 10).map(([tag, count]) => `
              <div style="display: flex; justify-content: space-between; padding: 12px; background: var(--bg-tertiary); border-radius: 8px;">
                <span style="font-weight: 600;">${tag}</span>
                <span style="color: var(--primary-color);">${count} files</span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : `
        <div class="empty-state">
          <div class="empty-state-icon">🏷️</div>
          <h3>No tags generated yet</h3>
          <p>Load some files first</p>
        </div>
      `}
    </div>
  `;
}

function renderSettings() {
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">⚙️ Settings</h1>
        <p class="view-subtitle">Configure your preferences</p>
      </div>
      
      <div class="card mb-lg">
        <h2 class="card-title">Google Drive Connection</h2>
        ${appState.authenticated ? `
          <div style="display: grid; gap: 16px;">
            <div>
              <strong>Status:</strong> <span style="color: #4caf50;">✓ Connected</span>
            </div>
            ${appState.driveInfo?.user ? `
              <div>
                <strong>Account:</strong> ${appState.driveInfo.user.email}
              </div>
              <div>
                <strong>Display Name:</strong> ${appState.driveInfo.user.displayName || 'Not available'}
              </div>
            ` : ''}
            <div style="display: flex; gap: 12px; flex-wrap: wrap;">
              <button class="search-button" onclick="initiateGoogleAuth()" style="width: fit-content;">
                🔄 Reconnect Drive
              </button>
              <button class="logout-button" onclick="logoutUser()" style="width: fit-content;">
                🚪 Logout
              </button>
            </div>
          </div>
        ` : `
          <div>
            <p>Not connected to Google Drive</p>
            <button class="connect-button" onclick="initiateGoogleAuth()">
              Connect Now
            </button>
          </div>
        `}
      </div>
      
      <div class="card mb-lg">
        <h2 class="card-title">🎨 Appearance</h2>
        <div style="display: grid; gap: 16px;">
          <div class="filter-group">
            <label class="filter-label">Theme</label>
            <div style="display: flex; gap: 12px;">
              <button 
                class="theme-button ${appState.theme === 'light' ? 'active' : ''}" 
                onclick="toggleTheme()"
              >
                ☀️ ${appState.theme === 'light' ? 'Light Mode (Active)' : 'Switch to Light'}
              </button>
              <button 
                class="theme-button ${appState.theme === 'dark' ? 'active' : ''}" 
                onclick="toggleTheme()"
              >
                🌙 ${appState.theme === 'dark' ? 'Dark Mode (Active)' : 'Switch to Dark'}
              </button>
            </div>
          </div>
          
          <div class="filter-group">
            <label class="filter-label">Grid Size</label>
            <select class="filter-select" onchange="changeGridSize(event.target.value)" value="${appState.gridSize}">
              <option value="small" ${appState.gridSize === 'small' ? 'selected' : ''}>Small</option>
              <option value="medium" ${appState.gridSize === 'medium' ? 'selected' : ''}>Medium</option>
              <option value="large" ${appState.gridSize === 'large' ? 'selected' : ''}>Large</option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="card mb-lg">
        <h2 class="card-title">📄 Display Settings</h2>
        <div style="display: grid; gap: 16px;">
          <div class="filter-group">
            <label class="filter-label">Files per page</label>
            <select class="filter-select" onchange="changeFilesPerPage(event.target.value)">
              <option value="12" ${appState.filesPerPage === 12 ? 'selected' : ''}>12</option>
              <option value="24" ${appState.filesPerPage === 24 ? 'selected' : ''}>24 (Default)</option>
              <option value="48" ${appState.filesPerPage === 48 ? 'selected' : ''}>48</option>
              <option value="96" ${appState.filesPerPage === 96 ? 'selected' : ''}>96</option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="card">
        <h2 class="card-title">🏷️ About Tagging</h2>
        <p>Tags are automatically generated from:</p>
        <ul style="margin-top: 12px; margin-left: 20px;">
          <li>File names</li>
          <li>File types</li>
          <li>Content keywords</li>
        </ul>
        <p style="margin-top: 12px; font-size: 0.9em; color: var(--text-secondary);">
          Note: Using simple keyword-based tagging (no external AI API required)
        </p>
      </div>
    </div>
  `;
}


// Event Handlers
function handleSearch(event) {
  const input = event.target;
  const cursorPosition = input.selectionStart; // Save cursor position
  
  appState.searchQuery = input.value.toLowerCase();
  filterFiles();
  
  // Restore cursor position after re-render
  setTimeout(() => {
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
      searchInput.value = input.value;
      searchInput.setSelectionRange(cursorPosition, cursorPosition);
      searchInput.focus();
    }
  }, 0);
}

function handleFileTypeFilter(event) {
  appState.selectedFileType = event.target.value;
  filterFiles();
}

function handleSortChange(event) {
  appState.sortBy = event.target.value;
  filterFiles();
}

function filterFiles() {
  let filtered = [...appState.files];
  
  if (appState.searchQuery) {
    filtered = filtered.filter(file => 
      file.name.toLowerCase().includes(appState.searchQuery) ||
      file.owner.toLowerCase().includes(appState.searchQuery) ||
      (file.aiTags || []).some(tag => tag.toLowerCase().includes(appState.searchQuery))
    );
  }
  
  if (appState.selectedFileType !== 'all') {
    filtered = filtered.filter(file => file.type === appState.selectedFileType);
  }
  
  filtered.sort((a, b) => {
    if (appState.sortBy === 'name') {
      return a.name.localeCompare(b.name);
    } else if (appState.sortBy === 'size') {
      return (parseInt(b.size) || 0) - (parseInt(a.size) || 0);
    } else {
      return new Date(b.modifiedTime) - new Date(a.modifiedTime);
    }
  });
  
  appState.filteredFiles = filtered;
  renderCurrentView();
}

function performSearch() {
  filterFiles();
}

function searchByTag(tag) {
  appState.currentView = 'search';
  appState.searchQuery = tag;
  filterFiles();
  navigateTo('search');
}

function viewFile(file) {
  if (file.webViewLink) {
    window.open(file.webViewLink, '_blank');
  } else {
    alert(`File: ${file.name}\nType: ${file.type}\nSize: ${formatFileSize(file.size)}\nModified: ${formatDate(file.modifiedTime)}\nTags: ${(file.aiTags || []).join(', ')}`);
  }
}

function navigateTo(view) {
  appState.currentView = view;
  
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.remove('active');
  });
  const activeLink = document.querySelector(`[data-view="${view}"]`);
  if (activeLink) {
    activeLink.classList.add('active');
  }
  
  renderCurrentView();
}

function renderCurrentView() {
  const mainContent = document.querySelector('.main-content');
  if (!mainContent) return;
  
  let content = '';
  switch (appState.currentView) {
    case 'dashboard':
      content = renderDashboard();
      break;
    case 'search':
      content = renderSearch();
      break;
    case 'files':
      content = renderFiles();
      break;
    case 'ai-tags':
      content = renderAITags();
      break;
    case 'settings':
      content = renderSettings();
      break;
  }
  
  mainContent.innerHTML = content;
}

// Initialize Application
async function initApp() {
  const root = document.getElementById('app-root');
  
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
            <button class="nav-link active" data-view="dashboard" onclick="navigateTo('dashboard')">
              <span class="nav-icon">📊</span>
              <span>Dashboard</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="search" onclick="navigateTo('search')">
              <span class="nav-icon">🔍</span>
              <span>Search</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="files" onclick="navigateTo('files')">
              <span class="nav-icon">📁</span>
              <span>Files</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="ai-tags" onclick="navigateTo('ai-tags')">
              <span class="nav-icon">🏷️</span>
              <span>AI Tags</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-link" data-view="settings" onclick="navigateTo('settings')">
              <span class="nav-icon">⚙️</span>
              <span>Settings</span>
            </button>
          </li>
        </ul>
      </nav>
      
      <main class="main-content"></main>
    </div>
    
    <footer class="app-footer">
      <p>Knowledge Hub © 2024 | Connected to Your Google Drive | Version 1.0.0</p>
    </footer>
  `;
  
  const authStatus = await checkAuthStatus();
  
  const statusEl = document.getElementById('connectionStatus');
  if (authStatus.authenticated) {
    statusEl.innerHTML = `
      <div class="status-dot"></div>
      <span>Connected to Google Drive</span>
    `;
    await loadFiles();
    await loadDriveInfo();
  } else {
    statusEl.innerHTML = `
      <div class="status-dot" style="background: #ff9800;"></div>
      <span>Not Connected</span>
    `;
  }
  
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('auth') === 'success') {
    window.history.replaceState({}, document.title, window.location.pathname);
    window.location.reload();
  }
  
  renderCurrentView();
}

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

// Run app
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
