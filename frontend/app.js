// Knowledge Hub - Enhanced Frontend with All Features
const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || '';
// const API_BASE_URL = window.RUNTIME_ENV?.SERVICE_API_BASE_URL;
console.log('API_BASE_URL:', API_BASE_URL);
// Application State
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
  filesPerPage: parseInt(localStorage.getItem('filesPerPage')) || 24,
  
  // ADD THESE 3 LINES - Keep your existing nlp properties if any
  nlpSearchResults: [],
  nlpSearchQuery: '',
  nlpSearchLoading: false,
  
  // NEW PROPERTIES FOR DUAL SEARCH
  searchType: 'simple', // 'simple' or 'ai'
  searchResults: []
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
// ADD THESE NEW FUNCTIONS FOR NLP SEARCH

async function performNLPSearch(query) {
  if (!query.trim()) return;
  
  appState.nlpSearchLoading = true;
  appState.nlpSearchQuery = query;
  renderCurrentView();
  
  try {
    // Add min_score parameter to only get high-relevance results
    const response = await fetch(`${API_BASE_URL}/nlp/search?query=${encodeURIComponent(query)}&top_k=10&min_score=0.4`);
    if (!response.ok) {
      throw new Error('NLP search failed');
    }
    
    const data = await response.json();
    appState.nlpSearchResults = data.results || [];
    appState.nlpSearchLoading = false;
    
    // Show message based on results
    if (appState.nlpSearchResults.length > 0) {
      showNotification(`🔍 Found ${data.total_results} highly relevant documents`, 'success');
    } else {
      showNotification('🔍 No highly relevant documents found. Try different search terms.', 'info');
    }
    
    renderCurrentView();
    
  } catch (error) {
    console.error('NLP search failed:', error);
    appState.nlpSearchLoading = false;
    showNotification('❌ NLP search failed.', 'error');
  }
}

async function trainNLPModel() {
  try {
    showNotification('🤖 Training NLP model on your documents...', 'info');
    
    const response = await fetch(`${API_BASE_URL}/nlp/train`, {
      method: 'POST'
    });
    
    const data = await response.json();
    
    if (response.ok) {
      showNotification(`✅ ${data.message} (${data.documents_processed} documents)`, 'success');
    } else {
      throw new Error(data.detail || 'Training failed');
    }
    
  } catch (error) {
    console.error('Training failed:', error);
    showNotification('❌ NLP training failed. Please try again.', 'error');
  }
}

function getRelevanceColor(relevance) {
  const colors = {
    'Very High': '#4caf50',
    'High': '#8bc34a',
    'Medium': '#ff9800',
    'Low': '#ff5722',
    'Very Low': '#f44336'
  };
  return colors[relevance] || '#666';
}

function renderNLPSearchResult(file) {
  const icon = `<div style="font-size:3.5rem;">${getFileIcon(file.mimeType, file.name)}</div>`;
  
  return `
    <div class="file-card" data-file-id="${file.id}" data-file-name="${file.name}" data-file-type="${file.mimeType || file.type}">
      <div class="file-thumbnail" style="position: relative;">
        ${icon}
        <div style="position: absolute; top: 8px; right: 8px; background: ${getRelevanceColor(file.relevance)}; 
             color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 600;">
          ${file.relevance}
        </div>
      </div>
      <div class="file-info">
        <div class="file-name" title="${file.name}">${file.name}</div>
        <div class="file-meta">
          <span>👤 ${file.owner}</span>
          <span>📅 ${formatDate(file.modifiedTime)}</span>
          <span>💾 ${formatFileSize(file.size)}</span>
        </div>
        <div style="margin: 8px 0; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4;">
          ${file.snippet || 'No content preview available'}
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
          <span style="font-size: 0.75rem; color: var(--primary-color); font-weight: 600;">
            Match: ${(file.score * 100).toFixed(1)}%
          </span>
          <span style="font-size: 0.7rem; color: var(--text-secondary);">
            AI Search
          </span>
        </div>
      </div>
    </div>
  `;
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
    <div class="file-card" data-file-id="${file.id}" data-file-name="${file.name}" data-file-type="${file.mimeType || file.type}">
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
// Add click handlers to all file cards
document.addEventListener('DOMContentLoaded', function() {
    attachFileCardListeners();
});

function attachFileCardListeners() {
    document.querySelectorAll('.file-card').forEach(card => {
        card.addEventListener('click', function() {
            const fileId = this.dataset.fileId;
            const fileName = this.dataset.fileName;
            const fileType = this.dataset.fileType;
            
            if (fileId) {
                openDocumentModal(fileId, fileName, fileType);
            }
        });
    });
}





function renderSearch() {
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">🔍 Search Your Documents</h1>
        <p class="view-subtitle">Choose your search method</p>
      </div>
      
      ${!appState.authenticated ? `
        <div class="auth-container">
          <p>Please connect to Google Drive first</p>
          <button class="connect-button" onclick="navigateTo('dashboard')">Go to Dashboard</button>
        </div>
      ` : `
        <div class="search-section">
          <!-- Search Bar -->
          <div class="search-bar">
            <input 
              type="text" 
              class="search-input" 
              placeholder="Enter your search query..."
              oninput="handleSearch(event)"
              value="${appState.searchQuery}"
              onkeypress="if(event.key === 'Enter') performSearch()"
            >
            <button class="search-button" onclick="performSearch()">Search</button>
          </div>
          
          <!-- Search Type Selection -->
          <div style="display: flex; gap: 12px; margin: 16px 0; flex-wrap: wrap;">
            <button class="search-type-button ${appState.searchType === 'simple' ? 'active' : ''}" 
                    onclick="setSearchType('simple')">
              🔍 Exact Match
            </button>
            <button class="search-type-button ${appState.searchType === 'ai' ? 'active' : ''}" 
                    onclick="setSearchType('ai')">
              🤖 AI Semantic
            </button>
            <button class="action-button" onclick="trainNLPModel()" 
                    style="margin-left: auto; background: linear-gradient(135deg, #667eea, #764ba2);">
              🚀 Train AI Model
            </button>
          </div>
          
          <!-- Search Description -->
          <div style="margin: 12px 0; padding: 12px; background: var(--bg-tertiary); border-radius: 8px;">
            <strong>${appState.searchType === 'simple' ? '🔍 Exact Match Search:' : '🤖 AI Semantic Search:'}</strong>
            <span style="color: var(--text-secondary);">
              ${appState.searchType === 'simple' 
                ? 'Finds documents containing ALL your exact words' 
                : 'Understands meaning and finds conceptually similar documents'}
            </span>
          </div>
          
          ${appState.searchType === 'ai' ? `
            <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
              <button class="suggestion-tag" onclick="searchWithAI('rental agreement')">🏠 Rental Agreement</button>
              <button class="suggestion-tag" onclick="searchWithAI('employment contract')">👔 Employment Contract</button>
              <button class="suggestion-tag" onclick="searchWithAI('payment terms')">💰 Payment Terms</button>
              <button class="suggestion-tag" onclick="searchWithAI('confidentiality clause')">🔒 Confidentiality</button>
            </div>
          ` : ''}
        </div>
        
        <!-- Search Results -->
        <div style="margin: 24px 0;">
          <h2 class="view-title">
            ${appState.searchType === 'simple' ? '🔍' : '🤖'} 
            ${appState.searchType === 'simple' ? 'Exact Match' : 'AI Semantic'} 
            Results for "${appState.searchQuery}"
            ${appState.searchResults.length ? `(${appState.searchResults.length} found)` : ''}
          </h2>
          
          ${appState.loading ? '<div class="loading"><div class="spinner"></div></div>' : 
            appState.searchResults.length > 0 ? `
              <div class="files-grid">
                ${appState.searchResults.map(file => 
                  appState.searchType === 'simple' 
                    ? renderSimpleSearchResult(file) 
                    : renderAISearchResult(file)
                ).join('')}
              </div>
            ` : appState.searchQuery ? `
              <div class="empty-state">
                <div class="empty-state-icon">${appState.searchType === 'simple' ? '🔍' : '🤖'}</div>
                <h3>No documents found</h3>
                <p>${appState.searchType === 'simple' 
                  ? `No documents contain all the words: "${appState.searchQuery}"` 
                  : 'Try different search terms or train the AI model'}</p>
              </div>
            ` : ''}
        </div>
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
    // Open document modal for clause extraction
    if (file.id) {
        openDocumentModal(file.id, file.name, file.mimeType || file.type);
    } else {
        // Fallback to opening in new tab if no ID
        if (file.webViewLink) {
            window.open(file.webViewLink, '_blank');
        } else {
            alert(`File: ${file.name}\nType: ${file.type}\nSize: ${formatFileSize(file.size)}\nModified: ${formatDate(file.modifiedTime)}\nTags: ${file.aiTags.join(', ')}`);
        }
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
  attachFileCardListeners();
}
// ==================== ADD THESE NEW FUNCTIONS ====================

// Search type selector
function setSearchType(type) {
  appState.searchType = type;
  if (appState.searchQuery) {
    performSearch();
  }
  renderCurrentView();
}

// Main search function
async function performSearch() {
  const query = appState.searchQuery.trim();
  if (!query) return;
  
  appState.loading = true;
  renderCurrentView();
  
  try {
    const endpoint = appState.searchType === 'simple' ? '/search/simple' : '/search/ai';
    const response = await fetch(`${API_BASE_URL}${endpoint}?query=${encodeURIComponent(query)}`);
    
    if (!response.ok) throw new Error('Search failed');
    
    const data = await response.json();
    appState.searchResults = data.results || [];
    appState.loading = false;
    
    const message = appState.searchType === 'simple' 
      ? `✅ Found ${data.total_results} documents containing "${query}"`
      : `🤖 Found ${data.total_results} semantically similar documents`;
    
    showNotification(message, 'success');
    renderCurrentView();
    
  } catch (error) {
    console.error('Search failed:', error);
    appState.loading = false;
    showNotification('❌ Search failed', 'error');
  }
}

// AI search with specific query
function searchWithAI(query) {
  appState.searchQuery = query;
  appState.searchType = 'ai';
  performSearch();
}

// Different result renderers
function renderSimpleSearchResult(file) {
  const icon = `<div style="font-size:3.5rem;">${getFileIcon(file.mimeType, file.name)}</div>`;
  
  return `
    <div class="file-card" onclick='viewFile(${JSON.stringify(file).replace(/'/g, "&apos;")})'>
      <div class="file-thumbnail">
        ${icon}
        <div style="position: absolute; top: 8px; right: 8px; background: #4caf50; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.7rem;">
          🔍 Exact Match
        </div>
      </div>
      <div class="file-info">
        <div class="file-name" title="${file.name}">${file.name}</div>
        <div class="file-meta">
          <span>👤 ${file.owner}</span>
          <span>📅 ${formatDate(file.modifiedTime)}</span>
        </div>
        ${file.content_preview ? `
          <div style="margin: 8px 0; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4; background: var(--bg-tertiary); padding: 8px; border-radius: 4px;">
            ${file.content_preview}
          </div>
        ` : ''}
      </div>
    </div>
  `;
}

function renderAISearchResult(file) {
  const icon = `<div style="font-size:3.5rem;">${getFileIcon(file.mimeType, file.name)}</div>`;
  const relevanceColor = getRelevanceColor(file.relevance);
  
  return `
    <div class="file-card" onclick='viewFile(${JSON.stringify(file).replace(/'/g, "&apos;")})'>
      <div class="file-thumbnail" style="position: relative;">
        ${icon}
        <div style="position: absolute; top: 8px; right: 8px; background: ${relevanceColor}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 600;">
          ${file.relevance}
        </div>
      </div>
      <div class="file-info">
        <div class="file-name" title="${file.name}">${file.name}</div>
        <div class="file-meta">
          <span>👤 ${file.owner}</span>
          <span>📅 ${formatDate(file.modifiedTime)}</span>
        </div>
        <div style="margin: 8px 0; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4;">
          ${file.snippet || 'No content preview'}
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
          <span style="font-size: 0.75rem; color: var(--primary-color); font-weight: 600;">
            Match: ${(file.score * 100).toFixed(1)}%
          </span>
          <span style="font-size: 0.7rem; color: var(--text-secondary);">
            AI Search
          </span>
        </div>
      </div>
    </div>
  `;
}

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


// File Preview Modal
function viewFile(file) {
    const fileUrl = file.file_url || file.webViewLink || file.fileUrl;
    
    if (fileUrl) {
        window.open(fileUrl, '_blank');
        showNotification(`Opening ${file.title || file.name}...`, 'info');
    } else {
        showNotification('File URL not available', 'error');
    }
}
// ============================================================
// CLAUSE EXTRACTION FUNCTIONALITY
// ============================================================

let currentDocumentId = null;
let currentClauses = [];
let selectedClauseNumber = null;

/**
 * Open document modal and load details
 */

/**
 * Open document modal and load details
 */
async function openDocumentModal(fileId, fileName, mimeType) {
    currentDocumentId = fileId;
    currentDocumentName = fileName;

    // Set modal title
    document.getElementById('modalTitle').textContent = fileName;

    // Show modal dialog
    const modal = document.getElementById('documentModal');
    modal.style.display = 'flex';

    // Clear similar files
    const similarFilesContent = document.getElementById('similarFilesContent');
    if (similarFilesContent) {
        similarFilesContent.innerHTML = '<div class="empty-state">Select a clause to find similar files</div>';
    }

    // Load clauses
    await autoLoadCachedClauses(fileId);

    // Tags
    const tagsContainer = document.getElementById('tagsContainer');
    if (tagsContainer) {
        let tags = [];
        const doc = (window.appState && Array.isArray(appState.files))
            ? appState.files.find(f => f.id === fileId)
            : null;
        if (doc && doc.aiTags && doc.aiTags.length > 0) {
            tags = doc.aiTags;
        } else {
            tags = fileName
                .replace(/\.[\w\d]+$/, '')
                .split(/[\s\-_\.]+/)
                .filter(w => w.length > 2);
        }
        tagsContainer.innerHTML = tags.length
            ? tags.map(tag => `<span class="tag">${tag}</span>`).join(' ')
            : '<em>No tags</em>';
    }

    // Set Open in Drive button handler
    const driveBtn = document.getElementById('driveBtn');
    if (driveBtn) {
        driveBtn.onclick = () => window.open(`https://drive.google.com/file/d/${fileId}/view`, '_blank');
    }
}





/**
 * Update autoLoadCachedClauses to show extract button if no clauses
 */
async function autoLoadCachedClauses(fileId) {
    const clausesList = document.getElementById('clausesList');
    clausesList.innerHTML = '<div class="loading-state">Loading clauses...</div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/documents/${fileId}/cached-clauses`);
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.clauses && data.clauses.length > 0) {
                console.log(`✅ Found ${data.clauses.length} cached clauses`);
                currentClauses = data.clauses;
                displayClausesList(currentClauses);
                return;
            }
        }
        
        // No cached clauses - show extract button
        clausesList.innerHTML = `
            <div class="empty-state">
                <p style="margin-bottom: 1rem; color: var(--text-secondary);">📄 No clauses extracted yet</p>
                <button onclick="extractClausesNow()" class="btn-primary" style="padding: 0.75rem 1.5rem; font-size: 0.9rem;">
                    🔍 Extract Clauses Now
                </button>
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading cached clauses:', error);
        clausesList.innerHTML = `
            <div class="empty-state">
                <p style="color: red; margin-bottom: 1rem;">❌ Error loading clauses</p>
                <button onclick="extractClausesNow()" class="btn-primary">
                    🔍 Extract Clauses
                </button>
            </div>
        `;
    }
}

/**
 * Extract clauses for current document (manual trigger)
 */
async function extractClausesNow() {
    const clausesList = document.getElementById('clausesList');
    clausesList.innerHTML = '<div class="loading-state">⏳ Extracting clauses... This may take 10-30 seconds...</div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/documents/${currentDocumentId}/extract-clauses`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to extract clauses');
        }
        
        console.log(`✅ Extracted ${data.clauses.length} clauses`);
        currentClauses = data.clauses;
        displayClausesList(currentClauses);
        
        // Show success message
        showNotification(`✅ Successfully extracted ${data.clauses.length} clauses!`, 'success');
        
    } catch (error) {
        console.error('Error extracting clauses:', error);
        clausesList.innerHTML = `
            <div class="empty-state" style="color: red;">
                <p style="margin-bottom: 1rem;">❌ Failed to extract clauses</p>
                <p style="font-size: 0.85rem; margin-bottom: 1rem;">${error.message}</p>
                <button onclick="extractClausesNow()" class="btn-primary">
                    🔄 Try Again
                </button>
            </div>
        `;
    }
}

/**
 * Show notification (if you don't have this function already)
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196F3'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}


/**
 * Auto-load cached clauses if they exist
 */
/**
 * Auto-load cached clauses if they exist, otherwise show extract button
 */
async function autoLoadCachedClauses(fileId) {
    const clausesList = document.getElementById('clausesList');
    clausesList.innerHTML = '<div class="loading-state">Loading clauses...</div>';
    
    try {
        // Try to fetch cached clauses
        const response = await fetch(`${API_BASE_URL}/documents/${fileId}/cached-clauses`);
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.clauses && data.clauses.length > 0) {
                // Clauses found in cache - display them!
                console.log(`✅ Found ${data.clauses.length} cached clauses`);
                currentClauses = data.clauses;
                displayClausesList(currentClauses);
                return;
            }
        }
        
        // No cached clauses - show extract button
        clausesList.innerHTML = `
            <div class="empty-state" style="text-align: center; padding: 2rem;">
                <p style="margin-bottom: 1.5rem; color: var(--text-secondary); font-size: 0.95rem;">
                    📄 No clauses extracted yet
                </p>
                <button 
                    onclick="extractClausesNow()" 
                    class="btn-primary" 
                    style="padding: 0.75rem 2rem; font-size: 0.95rem; cursor: pointer;">
                    🔍 Extract Clauses Now
                </button>
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading cached clauses:', error);
        clausesList.innerHTML = `
            <div class="empty-state" style="text-align: center; padding: 2rem;">
                <p style="color: #ff5722; margin-bottom: 1rem;">❌ Error loading clauses</p>
                <button 
                    onclick="extractClausesNow()" 
                    class="btn-primary" 
                    style="padding: 0.75rem 2rem; cursor: pointer;">
                    🔍 Extract Clauses
                </button>
            </div>
        `;
    }
}

/**
 * When user selects a clause, find similar files
 */
async function selectClause(clauseNumber) {
    selectedClauseNumber = clauseNumber;
    
    // Highlight selected clause
    document.querySelectorAll('.clause-item').forEach(item => {
        item.classList.remove('active');
    });
    const selectedItem = document.querySelector(`.clause-item[data-clause="${clauseNumber}"]`);
    if (selectedItem) {
        selectedItem.classList.add('active');
    }
    
    // Find clause data
    const clause = currentClauses.find(c => c.clause_number === clauseNumber);
    
    if (!clause) {
        console.error('Clause not found:', clauseNumber);
        return;
    }
    
    console.log('Selected clause:', clause);
    
    // Display clause content in middle panel
    displaySelectedClause(clause);
    
    // Find similar files with this clause title
    await findSimilarFiles(clause.title); 
}

/**
 * Find and display similar files
 */
async function findSimilarFiles(clauseTitle) {
    const container = document.getElementById('similarFilesContent');
    container.innerHTML = '<div class="loading-state">🔍 Searching for similar files...</div>';
    
    console.log('Finding similar files for clause:', clauseTitle);
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/clauses/${encodeURIComponent(clauseTitle)}/similar-files?current_file_id=${currentDocumentId}`
        );
        
        const data = await response.json();
        
        console.log('Similar files response:', data);
        
        if (!data.found || data.count === 0) {
            container.innerHTML = '<div class="empty-state">❌ No other files found with this clause</div>';
            return;
        }
        
        // Display similar files
        container.innerHTML = data.files.map(file => `
            <div class="similar-file-item" onclick="openDocumentModal('${file.file_id}', '${file.file_name}', 'application/pdf')">
                <div class="similar-file-icon">📄</div>
                <div class="similar-file-info">
                    <div class="similar-file-name">${file.file_name}</div>
                    <div class="similar-file-clause">${file.section_number}. ${file.clause_title}</div>
                    <span class="match-badge ${file.match_type}">${file.match_type}</span>
                </div>
            </div>
        `).join('');
        
        console.log(`✅ Displayed ${data.count} similar files`);
        
    } catch (error) {
        console.error('Error finding similar files:', error);
        container.innerHTML = '<div class="empty-state">⚠️ Error loading similar files</div>';
    }
}



/**
 * Load document details (tags, file info)
 */
/**
 * Load document details (tags, file info)
 */
/**
 * Load document details (tags) when modal opens
 */
async function loadDocumentDetails(fileId) {
    try {
        // Find file from appState.files array
        const file = appState.files.find(f => f.id === fileId);
        
        if (!file) {
            console.error('File not found in appState');
            displayTags([]);
            return;
        }
        
        console.log('File object:', file);
        
        // Display tags from file object
        const tags = file.aiTags || file.tags || [];
        displayTags(tags);
        
    } catch (error) {
        console.error('Error loading document details:', error);
        displayTags([]);
    }
}

/**
 * Display tags in the modal
 */
function displayTags(tags) {
    const container = document.getElementById('tagsContent');
    
    if (!tags || tags.length === 0) {
        container.innerHTML = '<div class="empty-state">No tags available</div>';
        return;
    }
    
    container.innerHTML = tags.map(tag => 
        `<span class="tag">${tag}</span>`
    ).join('');
}




/**
 * Display tags in modal
 */
function displayTags(tags) {
    const container = document.getElementById('tagsContent');
    
    if (!tags || tags.length === 0) {
        container.innerHTML = '<p class="empty-state">No tags</p>';
        return;
    }
    
    container.innerHTML = tags.map(tag => 
        `<span class="tag">${tag}</span>`
    ).join('');
}

/**
 * Display file information
 */
/**
 * Display file information
 */
/**
 * Display file information
 */
function displayFileInfo(file) {
    const container = document.getElementById('fileInfoContent');
    
    // Format file size
    const formatSize = (bytes) => {
        if (!bytes || bytes === 'Unknown') return 'Unknown';
        const sizes = ['B', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 B';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    };
    
    // Format date
    const formatDate = (dateStr) => {
        if (!dateStr || dateStr === 'Unknown') return 'Unknown';
        const date = new Date(dateStr);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    };
    
    const info = [
        { label: 'Type', value: file.mime_type || file.mimeType || 'Unknown' },
        { label: 'Size', value: formatSize(file.size) },
        { label: 'Owner', value: file.ownerName || 'Unknown' },
        { label: 'Modified', value: formatDate(file.modified_time || file.modifiedTime) },
        { label: 'Created', value: formatDate(file.created_time || file.createdTime) }
    ];
    
    container.innerHTML = info.map(item => `
        <div class="info-row">
            <span class="info-label">${item.label}:</span>
            <span class="info-value">${item.value}</span>
        </div>
    `).join('');
}



/**
 * Extract clauses from document
 */
async function extractClauses() {
    if (!currentDocumentId) {
        alert('No document selected');
        return;
    }
    
    const clausesList = document.getElementById('clausesList');
    clausesList.innerHTML = '<div class="loading-state">Extracting clauses... Please wait.</div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/documents/${currentDocumentId}/extract-clauses`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to extract clauses');
        }
        
        const data = await response.json();
        currentClauses = data.clauses || [];
        
        if (currentClauses.length === 0) {
            clausesList.innerHTML = '<div class="empty-state">No clauses found in this document</div>';
            return;
        }
        
        // Display clauses list
        displayClausesList(currentClauses);
        
    } catch (error) {
        console.error('Error extracting clauses:', error);
        clausesList.innerHTML = '<div class="empty-state">Error extracting clauses. Please try again.</div>';
        alert('Failed to extract clauses: ' + error.message);
    }
}

/**
 * Display list of clauses (titles only, no content preview)
 */
function displayClausesList(clauses) {
    const container = document.getElementById('clausesList');
    
    container.innerHTML = clauses.map(clause => `
        <div class="clause-item" onclick="selectClause(${clause.clause_number})" data-clause="${clause.clause_number}">
            <div class="clause-item-number">${clause.section_number || clause.clause_number}</div>
            <div class="clause-item-title">${clause.clause_title || clause.title}</div>
        </div>
    `).join('');
}

/**
 * Select and display a clause
 */
async function selectClause(clauseNumber) {
    selectedClauseNumber = clauseNumber;
    
    console.log('🔍 Clause clicked:', clauseNumber);
    
    // Highlight selected clause
    document.querySelectorAll('.clause-item').forEach(item => {
        item.classList.remove('active');
    });
    const selectedItem = document.querySelector(`.clause-item[data-clause="${clauseNumber}"]`);
    if (selectedItem) {
        selectedItem.classList.add('active');
    }
    
    // Find clause data
    const clause = currentClauses.find(c => c.clause_number === clauseNumber);
    
    if (!clause) {
        console.error('❌ Clause not found:', clauseNumber);
        return;
    }
    
    console.log('✅ Selected clause:', clause);
    
    // Display clause content in middle panel
    displaySelectedClause(clause);
    
    // Find similar files with this clause title
    const clauseTitle = clause.title || clause.clause_title;
    console.log('🔍 Searching for similar files with title:', clauseTitle);
    await findSimilarFiles(clauseTitle);
}
/**
 * Display selected clause content
 */
/**
 * Display selected clause content
 */
function displaySelectedClause(clause) {
    const container = document.getElementById('selectedClauseContainer');
    const titleEl = document.getElementById('selectedClauseTitle');
    const contentEl = document.getElementById('selectedClauseContent');
    
    console.log('📄 Displaying clause:', clause);
    
    // Show container
    container.style.display = 'block';
    
    // Get clause data (try ALL possible property names!)
    const clauseNumber = clause.section_number || clause.clause_number || clause.clauseNumber || clause.sectionNumber || '';
    const clauseTitle = clause.title || clause.clause_title || clause.clauseTitle || 'Untitled Clause';
    
    // ← THIS IS THE KEY FIX - Try ALL possible content property names!
    const clauseContent = clause.content || clause.clause_content || clause.clauseContent || clause.text || 'No content available';
    
    console.log('📝 Title:', clauseTitle);
    console.log('📝 Content length:', clauseContent?.length || 0);
    console.log('📝 Content preview:', clauseContent?.substring(0, 100));
    
    // Set content
    titleEl.textContent = `${clauseNumber}. ${clauseTitle}`;
    contentEl.textContent = clauseContent;
    
    // Reset save button
    const saveBtn = document.getElementById('saveToLibraryBtn');
    if (saveBtn) {
        saveBtn.textContent = '💾 Save to Library';
        saveBtn.classList.remove('saved');
        saveBtn.disabled = false;
    }
}


/**
 * Save clause to library
 */
/**
 * Save clause to library
 */
async function saveClauseToLibrary() {
    if (!currentDocumentId || selectedClauseNumber === null) {
        alert('No clause selected');
        return;
    }
    
    const saveBtn = document.getElementById('saveToLibraryBtn');
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/clauses/save-to-library`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_id: currentDocumentId,
                clause_number: selectedClauseNumber
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to save clause');
        }
        
        if (data.already_saved) {
            saveBtn.textContent = '✓ Already Saved';
        } else {
            saveBtn.textContent = '✓ Saved to Library';
        }
        
        saveBtn.classList.add('saved');
        
        // Show success notification
        showNotification('Clause saved to library successfully!', 'success');
        
    } catch (error) {
        console.error('Error saving clause:', error);
        alert('Failed to save clause: ' + error.message);
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 Save to Library';
    }
}


/**
 * Close modal
 */
function closeModal() {
    const modal = document.getElementById('documentModal');
    modal.style.display = 'none';
    
    // Reset state
    currentDocumentId = null;
    currentClauses = [];
    selectedClauseNumber = null;
    
    // Clear content
    document.getElementById('clausesList').innerHTML = 
        '<div class="loading-state">Click "Extract Clauses" to analyze document</div>';
    document.getElementById('selectedClauseContainer').style.display = 'none';
}

/**
 * Show notification (helper function)
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4CAF50' : '#2196F3'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * Format file size (helper function)
 */
function formatFileSize(bytes) {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

/**
 * Format date (helper function)
 */
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}







// ==================== END OF NEW FUNCTIONS ====================

// KEEP YOUR EXISTING initApp() function below - DON'T REMOVE IT
async function initApp() {
  // ... your existing initApp code ...
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
    showNotification('✅ Connected successfully!', 'success');  // ✅ ADD THIS
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
