// modules/views.js - View Rendering
console.log('Loading views.js...');

// Render dashboard
function renderDashboard() {
  const stats = {
    totalFiles: window.appState.files.length,
    contracts: window.appState.files.filter(f => {
      const name = f.name.toLowerCase();
      const tags = (f.aiTags || []).map(t => t.toLowerCase());
      return name.includes('contract') || 
             name.includes('agreement') || 
             tags.some(tag => tag.includes('contract') || tag.includes('agreement'));
    }).length,
    clauses: window.appState.files.filter(f => {
      const name = f.name.toLowerCase();
      const tags = (f.aiTags || []).map(t => t.toLowerCase());
      return name.includes('clause') || 
             tags.some(tag => tag.includes('clause'));
    }).length,
    practiceNotes: window.appState.files.filter(f => {
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
      
      ${!window.appState.authenticated ? `
        <div class="auth-container">
          <div class="auth-card">
            <h2>🔐 Connect to Your Google Drive</h2>
            <p>Click the button below to securely connect your Google Drive account.</p>
            <button class="connect-button" onclick="window.initiateGoogleAuth()">
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
        
        ${window.appState.driveInfo ? `
          <div class="card mb-lg">
            <h2 class="card-title">☁️ Google Drive Connection</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; align-items: center;">
              <div>
                <strong>Account:</strong> ${window.appState.driveInfo.user?.email || 'Connected'}
              </div>
              <div>
                <strong>Status:</strong> <span style="color: #4caf50;">✓ Connected</span>
              </div>
              <div>
                <strong>Total Files:</strong> ${stats.totalFiles}
              </div>
              <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button class="action-button" onclick="window.refreshFiles()">🔄 Refresh Drive</button>
                <button class="action-button" onclick="window.uploadFiles()">📤 Upload Files</button>
                <button class="action-button voice-button" onclick="window.voiceRecord()" title="Voice Recording">
                  🎤 Voice Record
                </button>
                <button class="action-button" onclick="window.openNoteModal()">📝 Add Note</button>
              </div>
            </div>
          </div>
        ` : ''}
        
        <h2 class="view-title" style="margin-top: 32px;">📌 Recent Files</h2>
        ${window.appState.loading ? '<div class="loading"><div class="spinner"></div></div>' : `
          <div class="files-grid">
            ${window.appState.files.slice(0, 6).map(file => window.renderFileCard(file)).join('')}
          </div>
        `}
      `}
    </div>
  `;
}

// Render search view
function renderSearch() {
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">🔍 Search Your Documents</h1>
        <p class="view-subtitle">Choose your search method</p>
      </div>
      
      ${!window.appState.authenticated ? `
        <div class="auth-container">
          <p>Please connect to Google Drive first</p>
          <button class="connect-button" onclick="window.navigateTo('dashboard')">Go to Dashboard</button>
        </div>
      ` : `
        <div class="search-section">
          <!-- Search Bar -->
          <div class="search-bar">
            <input 
              type="text" 
              class="search-input" 
              placeholder="Enter your search query..."
              oninput="window.handleSearch(event)"
              value="${window.appState.searchQuery}"
              onkeypress="if(event.key === 'Enter') window.performSearch()"
            >
            <button class="search-button" onclick="window.performSearch()">Search</button>
          </div>
          
          <!-- Search Type Selection -->
          <div style="display: flex; gap: 12px; margin: 16px 0; flex-wrap: wrap;">
            <button class="search-type-button ${window.appState.searchType === 'simple' ? 'active' : ''}" 
                    onclick="window.setSearchType('simple')">
              🔍 Exact Match
            </button>
            <button class="search-type-button ${window.appState.searchType === 'ai' ? 'active' : ''}" 
                    onclick="window.setSearchType('ai')">
              🤖 AI Semantic
            </button>
            <button class="action-button" onclick="window.trainNLPModel()" 
                    style="margin-left: auto; background: linear-gradient(135deg, #667eea, #764ba2);">
              🚀 Train AI Model
            </button>
          </div>
          
          <!-- Search Description -->
          <div style="margin: 12px 0; padding: 12px; background: var(--bg-tertiary); border-radius: 8px;">
            <strong>${window.appState.searchType === 'simple' ? '🔍 Exact Match Search:' : '🤖 AI Semantic Search:'}</strong>
            <span style="color: var(--text-secondary);">
              ${window.appState.searchType === 'simple' 
                ? 'Finds documents containing ALL your exact words' 
                : 'Understands meaning and finds conceptually similar documents'}
            </span>
          </div>
          
          ${window.appState.searchType === 'ai' ? `
            <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
              <button class="suggestion-tag" onclick="window.searchWithAI('rental agreement')">🏠 Rental Agreement</button>
              <button class="suggestion-tag" onclick="window.searchWithAI('employment contract')">👔 Employment Contract</button>
              <button class="suggestion-tag" onclick="window.searchWithAI('payment terms')">💰 Payment Terms</button>
              <button class="suggestion-tag" onclick="window.searchWithAI('confidentiality clause')">🔒 Confidentiality</button>
            </div>
          ` : ''}
        </div>
        
        <!-- Search Results -->
        <div style="margin: 24px 0;">
          <h2 class="view-title">
            ${window.appState.searchType === 'simple' ? '🔍' : '🤖'} 
            ${window.appState.searchType === 'simple' ? 'Exact Match' : 'AI Semantic'} 
            Results for "${window.appState.searchQuery}"
            ${window.appState.searchResults.length ? `(${window.appState.searchResults.length} found)` : ''}
          </h2>
          
          ${window.appState.loading ? '<div class="loading"><div class="spinner"></div></div>' : 
            window.appState.searchResults.length > 0 ? `
              <div class="files-grid">
                ${window.appState.searchResults.map(file => 
                  window.appState.searchType === 'simple' 
                    ? window.renderSimpleSearchResult(file) 
                    : window.renderAISearchResult(file)
                ).join('')}
              </div>
            ` : window.appState.searchQuery ? `
              <div class="empty-state">
                <div class="empty-state-icon">${window.appState.searchType === 'simple' ? '🔍' : '🤖'}</div>
                <h3>No documents found</h3>
                <p>${window.appState.searchType === 'simple' 
                  ? `No documents contain all the words: "${window.appState.searchQuery}"` 
                  : 'Try different search terms or train the AI model'}</p>
              </div>
            ` : ''}
        </div>
      `}
    </div>
  `;
}

// Render files view
function renderFiles() {
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">📁 All Files</h1>
        <p class="view-subtitle">Browse your Google Drive</p>
      </div>
      
      ${!window.appState.authenticated ? `
        <div class="auth-container">
          <p>Please connect to Google Drive first</p>
          <button class="connect-button" onclick="window.navigateTo('dashboard')">Go to Dashboard</button>
        </div>
      ` : window.appState.loading ? '<div class="loading"><div class="spinner"></div></div>' : `
        <div class="files-grid">
          ${window.appState.files.slice(0, window.appState.filesPerPage).map(file => window.renderFileCard(file)).join('')}
        </div>
        ${window.appState.files.length > window.appState.filesPerPage ? `
          <div style="text-align: center; margin-top: 24px;">
            <p style="color: var(--text-secondary);">
              Showing ${window.appState.filesPerPage} of ${window.appState.files.length} files
            </p>
          </div>
        ` : ''}
      `}
    </div>
  `;
}

// Render AI tags view
function renderAITags() {
  const allTags = {};
  window.appState.files.forEach(file => {
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
      
      ${!window.appState.authenticated ? `
        <div class="auth-container">
          <p>Please connect to Google Drive first</p>
          <button class="connect-button" onclick="window.navigateTo('dashboard')">Go to Dashboard</button>
        </div>
      ` : sortedTags.length > 0 ? `
        <div class="card mb-lg">
          <h2 class="card-title">Tag Cloud</h2>
          <div class="tag-cloud">
            ${sortedTags.map(([tag, count]) => `
              <span 
                class="tag-cloud-item" 
                style="font-size: ${Math.min(0.875 + (count * 0.25), 2)}rem;"
                onclick="window.searchByTag('${tag}')"
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

// Render settings view
function renderSettings() {
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">⚙️ Settings</h1>
        <p class="view-subtitle">Configure your preferences</p>
      </div>
      
      <div class="card mb-lg">
        <h2 class="card-title">Google Drive Connection</h2>
        ${window.appState.authenticated ? `
          <div style="display: grid; gap: 16px;">
            <div>
              <strong>Status:</strong> <span style="color: #4caf50;">✓ Connected</span>
            </div>
            ${window.appState.driveInfo?.user ? `
              <div>
                <strong>Account:</strong> ${window.appState.driveInfo.user.email}
              </div>
              <div>
                <strong>Display Name:</strong> ${window.appState.driveInfo.user.displayName || 'Not available'}
              </div>
            ` : ''}
            <div style="display: flex; gap: 12px; flex-wrap: wrap;">
              <button class="search-button" onclick="window.initiateGoogleAuth()" style="width: fit-content;">
                🔄 Reconnect Drive
              </button>
              <button class="logout-button" onclick="window.logoutUser()" style="width: fit-content;">
                🚪 Logout
              </button>
            </div>
          </div>
        ` : `
          <div>
            <p>Not connected to Google Drive</p>
            <button class="connect-button" onclick="window.initiateGoogleAuth()">
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
                class="theme-button ${window.appState.theme === 'light' ? 'active' : ''}" 
                onclick="window.toggleTheme()"
              >
                ☀️ ${window.appState.theme === 'light' ? 'Light Mode (Active)' : 'Switch to Light'}
              </button>
              <button 
                class="theme-button ${window.appState.theme === 'dark' ? 'active' : ''}" 
                onclick="window.toggleTheme()"
              >
                🌙 ${window.appState.theme === 'dark' ? 'Dark Mode (Active)' : 'Switch to Dark'}
              </button>
            </div>
          </div>
          
          <div class="filter-group">
            <label class="filter-label">Grid Size</label>
            <select class="filter-select" onchange="window.changeGridSize(event.target.value)" value="${window.appState.gridSize}">
              <option value="small" ${window.appState.gridSize === 'small' ? 'selected' : ''}>Small</option>
              <option value="medium" ${window.appState.gridSize === 'medium' ? 'selected' : ''}>Medium</option>
              <option value="large" ${window.appState.gridSize === 'large' ? 'selected' : ''}>Large</option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="card mb-lg">
        <h2 class="card-title">📄 Display Settings</h2>
        <div style="display: grid; gap: 16px;">
          <div class="filter-group">
            <label class="filter-label">Files per page</label>
            <select class="filter-select" onchange="window.changeFilesPerPage(event.target.value)">
              <option value="12" ${window.appState.filesPerPage === 12 ? 'selected' : ''}>12</option>
              <option value="24" ${window.appState.filesPerPage === 24 ? 'selected' : ''}>24 (Default)</option>
              <option value="48" ${window.appState.filesPerPage === 48 ? 'selected' : ''}>48</option>
              <option value="96" ${window.appState.filesPerPage === 96 ? 'selected' : ''}>96</option>
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

// Make functions globally available
window.renderDashboard = renderDashboard;
window.renderSearch = renderSearch;
window.renderFiles = renderFiles;
window.renderAITags = renderAITags;
window.renderSettings = renderSettings;