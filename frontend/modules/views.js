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
              <div><strong>Account:</strong> ${window.appState.driveInfo.user?.email || 'Connected'}</div>
              <div><strong>Status:</strong> <span style="color: #4caf50;">✓ Connected</span></div>
              <div><strong>Total Files:</strong> ${stats.totalFiles}</div>
              <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button class="action-button" onclick="window.refreshFiles()">🔄 Refresh Drive</button>
                <button class="action-button" onclick="window.uploadFiles()">📤 Upload Files</button>
                <button class="action-button voice-button" onclick="window.voiceRecord()" title="Voice Recording">🎤 Voice Record</button>
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
          <div class="search-bar">
            <input 
              type="text" 
              class="search-input" 
              placeholder="Enter your search query..."
              oninput="window.handleSearch(event)"
              value="${window.appState.searchQuery}"
              onkeypress="if(event.key === 'Enter') window.performSearch()"
            >
            <button class="search-button" onclick="window.performGroupedSearch(window.appState.searchQuery)">Search</button>
          </div>
          
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
        
        <div id="searchResults"></div>
      `}
    </div>
  `;
}

// Render files view
// Render files view - WITH LIST/GRID TOGGLE
function renderFiles() {
  // 🔥 SORT TAGGED FILES FIRST
  const sortedFiles = [...window.appState.files].sort((a, b) => {
    const aHasTags = (a.aiTags?.length > 0 || a.tagCount > 0) ? 0 : 1;
    const bHasTags = (b.aiTags?.length > 0 || b.tagCount > 0) ? 0 : 1;
    return aHasTags - bHasTags;
  }).slice(0, window.appState.filesPerPage || 24);

  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">📁 All Files</h1>
        <p class="view-subtitle">Tagged files first ✓</p>
      </div>
      
      ${!window.appState.authenticated ? `
        <div class="auth-container">
          <p>Please connect to Google Drive first</p>
          <button class="connect-button" onclick="window.navigateTo('dashboard')">Go to Dashboard</button>
        </div>
      ` : window.appState.loading ? '<div class="loading"><div class="spinner"></div></div>' : `
        <!-- VIEW TOGGLE BUTTONS -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <span id="filesCount" style="font-weight: 600; color: var(--primary-color);">
              ${sortedFiles.length} files (Tagged first)
            </span>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="action-button ${window.appState.filesView === 'grid' ? 'active-view-btn' : ''}" 
                    onclick="window.toggleFilesView('grid')" title="Grid View">
              🗂️ Grid
            </button>
            <button class="action-button ${window.appState.filesView === 'list' ? 'active-view-btn' : ''}" 
                    onclick="window.toggleFilesView('list')" title="List View">
              📋 List
            </button>
            <button class="action-button" onclick="window.refreshFiles()" style="background: var(--accent-color);">
              🔄 Refresh
            </button>
          </div>
        </div>

        <!-- GRID VIEW -->
        ${window.appState.filesView !== 'list' ? `
          <div class="files-grid" id="filesGrid">
            ${sortedFiles.map(file => window.renderFileCard(file)).join('')}
          </div>
        ` : ''}

        <!-- LIST VIEW -->
        ${window.appState.filesView === 'list' ? `
          <div class="files-list-container" id="filesList">
            <div class="files-list-header">
              <span style="flex: 3; font-weight: 600;">📄 File Name</span>
              <span style="flex: 1; font-weight: 600; text-align: center;">🏷️ Tags</span>
              <span style="flex: 1; font-weight: 600; text-align: center;">📅 Modified</span>
              <span style="flex: 1; font-weight: 600; text-align: right;">💾 Size</span>
            </div>
            <div class="files-list-body">
              ${sortedFiles.map(file => window.renderFileListRow(file)).join('')}
            </div>
          </div>
        ` : ''}

        ${window.appState.files.length > (window.appState.filesPerPage || 24) ? `
          <div style="text-align: center; margin-top: 24px;">
            <p style="color: var(--text-secondary);">
              Showing ${sortedFiles.length} of ${window.appState.files.length} files (Tagged first)
            </p>
          </div>
        ` : ''}
      `}
    </div>
  `;
}

// NEW: List row renderer
function renderFileListRow(file) {
  const allTags = file.aiTags || [];
  const tagPreview = allTags.slice(0, 2).join(', ') + (allTags.length > 2 ? '...' : '');
  
  return `
    <div class="file-list-row" data-file-id="${file.id}">
      <div class="file-list-cell name-cell" style="flex: 3;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="font-size: 1.5rem;">${window.getFileIcon(file.mimeType, file.name)}</div>
          <div>
            <div style="font-weight: 600; margin-bottom: 2px;">${file.name}</div>
            <div style="font-size: 0.8rem; color: var(--text-secondary);">${file.owner}</div>
          </div>
        </div>
      </div>
      <div class="file-list-cell tags-cell" style="flex: 1; text-align: center;">
        ${allTags.length ? 
          allTags.slice(0, 3).map(tag => `<span class="tag" style="font-size: 0.75rem;">${tag}</span>`).join(' ') +
          (allTags.length > 3 ? `<span>+${allTags.length-3}</span>` : '')
          : 'No tags'
        }
      </div>
      <div class="file-list-cell date-cell" style="flex: 1; text-align: center;">
        ${window.formatDate(file.modifiedTime)}
      </div>
      <div class="file-list-cell size-cell" style="flex: 1; text-align: right;">
        ${window.formatFileSize(file.size)}
      </div>
    </div>
  `;
}


// NEW: Template Library View
function renderTemplates() {
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">📄 Template Library</h1>
        <p class="view-subtitle">Filter by Practice Area, Tags, or Search</p>
      </div>
      
      ${!window.appState.authenticated ? `
        <div class="auth-container">
          <button class="connect-button" onclick="window.navigateTo('dashboard')">Connect Drive</button>
        </div>
      ` : `
        <div class="card mb-lg" style="padding: 20px;">
          <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: end;">
            <div style="flex: 1; min-width: 250px;">
              <label style="display: block; margin-bottom: 4px; font-weight: 600;">Search</label>
              <input type="text" id="templateSearch" placeholder="employment, NDA, service agreement..." style="width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #ddd;">
            </div>
            
            <div style="min-width: 220px;">
              <label style="display: block; margin-bottom: 4px; font-weight: 600;">Practice Area</label>
              <select id="practiceAreaFilter" style="width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #ddd;">
                <option value="">Loading practice areas...</option>
              </select>
            </div>
            
            <button class="action-button" onclick="window.loadTemplates()" style="white-space: nowrap;">
              🔄 Refresh
            </button>
          </div>
        </div>
        
        <div class="stats-row" style="margin-bottom: 20px;">
          <span id="templateCount" style="font-weight: 600; color: var(--primary-color);">Loading...</span>
          <span style="color: var(--text-secondary);">files found</span>
        </div>
        
        <div id="templatesGrid" class="files-grid">
          <div class="empty-state">
            <div style="font-size: 4rem;">📄</div>
            <h3>Loading templates...</h3>
          </div>
        </div>
      `}
    </div>
  `;
}

window.loadTemplates = async function() {
  try {
    const params = new URLSearchParams();
    const search = document.getElementById('templateSearch')?.value;
    const practiceArea = document.getElementById('practiceAreaFilter')?.value;
    
    if (search) params.set('search', search);
    if (practiceArea) params.set('practice_area', practiceArea);
    
    const response = await fetch(`${window.API_BASE_URL}/templates?${params}`);
    const data = await response.json();
    
    const grid = document.getElementById('templatesGrid');
    const countEl = document.getElementById('templateCount');
    const practiceSelect = document.getElementById('practiceAreaFilter');
    
    if (grid && data.templates) {
      if (data.templates.length === 0) {
        grid.innerHTML = `
          <div class="empty-state" style="grid-column: 1/-1;">
            <div style="font-size: 4rem;">📄</div>
            <h3>No templates match your filters</h3>
            <p>Try "employment", "HR", "service agreement", "NDA"</p>
          </div>
        `;
      } else {
        // ✅ Use renderFileCard for perfect file display
        grid.innerHTML = data.templates.map(file => window.renderFileCard(file)).join('');
        window.attachFileCardListeners();
        
        // Update count
        if (countEl) countEl.textContent = data.total || data.templates.length;
      }
      
      // ✅ Populate practice area dropdown
      if (practiceSelect && data.practice_areas) {
        practiceSelect.innerHTML = `
          <option value="">All Practice Areas (${data.practice_areas.length})</option>
          ${data.practice_areas.map(area => `<option value="${area}">${area}</option>`).join('')}
        `;
      }
    }
  } catch (error) {
    console.error('Templates load error:', error);
    document.getElementById('templatesGrid').innerHTML = `
      <div class="empty-state">
        <div style="font-size: 4rem; color: #f44336;">⚠️</div>
        <h3>Connection error</h3>
        <p>Check backend is running on port 8000</p>
      </div>
    `;
  }
};


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
            <div><strong>Status:</strong> <span style="color: #4caf50;">✓ Connected</span></div>
            ${window.appState.driveInfo?.user ? `
              <div><strong>Account:</strong> ${window.appState.driveInfo.user.email}</div>
              <div><strong>Display Name:</strong> ${window.appState.driveInfo.user.displayName || 'Not available'}</div>
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

// NEW: Template Functions
window.loadTemplates = async function() {
  try {
    const params = new URLSearchParams();
    const search = document.getElementById('templateSearch')?.value;
    const practiceArea = document.getElementById('practiceAreaFilter')?.value;
    const subPractice = document.getElementById('subPracticeFilter')?.value;
    
    if (search) params.set('search', search);
    if (practiceArea) params.set('practice_area', practiceArea);
    if (subPractice) params.set('sub_practice', subPractice);
    
    const response = await fetch(`${window.API_BASE_URL}/templates?${params}`);
    const data = await response.json();
    
    const grid = document.getElementById('templatesGrid');
    if (grid && data.templates) {
      if (data.templates.length === 0) {
        grid.innerHTML = `
          <div class="empty-state" style="grid-column: 1/-1;">
            <div style="font-size: 4rem;">📄</div>
            <h3>No templates match your filters</h3>
            <p>Try "employment", "HR policy", "service agreement"</p>
          </div>
        `;
      } else {
        grid.innerHTML = data.templates.map(file => window.renderFileCard(file)).join('');
        window.attachFileCardListeners();
        
        // Populate practice area dropdown
        if (data.practice_areas) {
          const select = document.getElementById('practiceAreaFilter');
          if (select) {
            select.innerHTML = '<option value="">All Practice Areas</option>' + 
              data.practice_areas.map(area => `<option value="${area}">${area}</option>`).join('');
          }
        }
      }
    }
  } catch (error) {
    console.error('Templates error:', error);
    document.getElementById('templatesGrid').innerHTML = `
      <div class="empty-state">
        <div style="font-size: 4rem; color: #f44336;">⚠️</div>
        <h3>Backend error</h3>
      </div>
    `;
  }
};
// Auto-load on filter change
document.addEventListener('change', function(e) {
  if (e.target.id === 'practiceAreaFilter' || e.target.id === 'subPracticeFilter' || e.target.id === 'templateSearch') {
    window.loadTemplates();
  }
});


// Make functions globally available
window.renderDashboard = renderDashboard;
window.renderSearch = renderSearch;
window.renderFiles = renderFiles;
window.renderAITags = renderAITags;
window.renderSettings = renderSettings;
window.renderTemplates = renderTemplates;
