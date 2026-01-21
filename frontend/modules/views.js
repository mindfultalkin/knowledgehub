// modules/views.js - View Rendering
console.log('Loading views.js...');
window.IS_ADMIN = window.location.search.includes('admin');

// ADD THIS EXACTLY HERE - Line 3
window.debounce = window.debounce || function(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

// Render dashboard
function renderDashboard() {
  // Sync stats - use cached values or defaults
  const stats = {
    totalFiles: window.appState.files?.length || 0,
    templates: window.appState.templateCount || 0,
    clauses: window.appState.clauseCount || 0, // From clause library API
    practiceArea: 0 // As requested
  };

  // TAG CLOUD DATA
  const allTags = {};
  window.appState.files?.forEach(file => {
    (file.aiTags || []).forEach(tag => {
      allTags[tag] = (allTags[tag] || 0) + 1;
    });
  });
  const sortedTags = Object.entries(allTags)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12);

  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">Knowledge Hub Dashboard</h1>
        <p class="view-subtitle">Your Google Drive Connection</p>
      </div>
      
      ${!window.appState.authenticated ? `
        <div class="auth-container">
          <div class="auth-card">
            <h2>Connect to Your Google Drive</h2>
            <p>Click the button below to securely connect your Google Drive account.</p>
            ${window.IS_ADMIN ? `
            <button class="connect-button" onclick="window.initiateGoogleAuth()">
              Connect to Google Drive
            </button>
            ` : '<div style="color: red; font-weight: 600;">Contact admin to connect Google Drive.</div>'}
          </div>
        </div>
      ` : `
        <!-- Stats Grid - UPDATED WITH FONT AWESOME ICONS -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon" style="width: 36px; height: 36px; font-size: 1.25rem;">
              <i class="fas fa-folder-open"></i>
            </div>
            <div class="stat-number">${stats.totalFiles}</div>
            <div class="stat-label">Total Files</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon" style="width: 36px; height: 36px; font-size: 1.25rem;">
              <i class="fas fa-file-contract"></i>
            </div>
            <div class="stat-number">${stats.templates}</div>
            <div class="stat-label">Templates</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon" style="width: 36px; height: 36px; font-size: 1.25rem;">
              <i class="fas fa-file-signature"></i>
            </div>
            <div class="stat-number">${stats.clauses}</div>
            <div class="stat-label">Clauses</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon" style="width: 36px; height: 36px; font-size: 1.25rem;">
              <i class="fas fa-balance-scale"></i>
            </div>
            <div class="stat-number">${stats.practiceArea}</div>
            <div class="stat-label">Practice Area</div>
          </div>
        </div>

        <!-- Google Drive Connection -->
        ${window.appState.driveInfo ? `
          <div class="card mb-lg">
            <h2 class="card-title">Google Drive Connection</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; align-items: center;">
              <div><strong>Account:</strong> ${window.appState.driveInfo.user?.email || 'Connected'}</div>
              <div><strong>Status:</strong> <span style="color: #4caf50;">Connected</span></div>
              <div><strong>Total Files:</strong> ${stats.totalFiles}</div>
            ${window.IS_ADMIN ? `
              <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button class="action-button" onclick="window.refreshFiles()">Refresh</button>
                <button class="action-button" onclick="window.refreshDashboardStats()">Update Stats</button>
                <button class="action-button voice-button" onclick="window.voiceRecord()" title="Voice Record">Voice</button>
                <button class="action-button" onclick="window.openNoteModal()">Note</button>
              </div>
            ` : ''}
            </div>
          </div>
        ` : ''}

        <!-- PROFESSIONAL TAG CLOUD -->
        ${sortedTags.length > 0 ? `
          <div class="card mb-lg">
            <h2 class="card-title" style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
              <div class="tags-icon"></div>
              Top Tags
            </h2>
            <div class="tag-cloud-dashboard">
              ${sortedTags.map(([tag, count]) => `
                <span class="dashboard-tag" 
                      data-count="${count >= 5 ? '5+' : count}"
                      onclick="window.searchByTag('${tag.replace(/'/g, "\\'")}')"
                      title="Search ${tag} (${count} files)">
                  ${tag}
                </span>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- 4 Recent Files -->
        <div class="recent-files-section">
          <h2 class="view-title">Recent Files (4)</h2>
          ${window.appState.loading ? '<div class="loading"><div class="spinner"></div></div>' : `
            <div class="files-grid" style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));">
              ${window.appState.files.slice(0, 4).map(file => window.renderFileCard(file)).join('')}
            </div>
            ${window.appState.files.length > 4 ? `
              <div style="text-align: center; margin-top: 1.5rem;">
                <button class="action-button" onclick="window.navigateTo('files')" style="background: var(--primary-color);">
                  View All Files (${window.appState.files.length})
                </button>
              </div>
            ` : ''}
          `}
        </div>
      `}
    </div>
  `;
}

// Render search view
function renderSearch() {
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">Search Your Documents</h1>
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
              Exact Match
            </button>
            <button class="search-type-button ${window.appState.searchType === 'ai' ? 'active' : ''}" 
                    onclick="window.setSearchType('ai')">
              AI Semantic
            </button>
            <button class="action-button" onclick="window.trainNLPModel()" 
                    style="margin-left: auto; background: linear-gradient(135deg, #667eea, #764ba2);">
              Train AI Model
            </button>
          </div>
          
          <div style="margin: 12px 0; padding: 12px; background: var(--bg-tertiary); border-radius: 8px;">
            <strong>${window.appState.searchType === 'simple' ? 'Exact Match Search:' : 'AI Semantic Search:'}</strong>
            <span style="color: var(--text-secondary);">
              ${window.appState.searchType === 'simple' 
                ? 'Finds documents containing ALL your exact words' 
                : 'Understands meaning and finds conceptually similar documents'}
            </span>
          </div>
          
          ${window.appState.searchType === 'ai' ? `
            <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
              <button class="suggestion-tag" onclick="window.searchWithAI('rental agreement')">Rental Agreement</button>
              <button class="suggestion-tag" onclick="window.searchWithAI('employment contract')">Employment Contract</button>
              <button class="suggestion-tag" onclick="window.searchWithAI('payment terms')">Payment Terms</button>
              <button class="suggestion-tag" onclick="window.searchWithAI('confidentiality clause')">Confidentiality</button>
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
  // SORT TAGGED FILES FIRST
  const sortedFiles = [...window.appState.files].sort((a, b) => {
    const aHasTags = (a.aiTags?.length > 0 || a.tagCount > 0) ? 0 : 1;
    const bHasTags = (b.aiTags?.length > 0 || b.tagCount > 0) ? 0 : 1;
    return aHasTags - bHasTags;
  }).slice(0, window.appState.filesPerPage || 96);

  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">All Files</h1>
      </div>
      
      ${!window.appState.authenticated ? `
        <div class="auth-container">
          <p>Please connect to Google Drive first</p>
          <button class="connect-button" onclick="window.navigateTo('dashboard')">Go to Dashboard</button>
        </div>
      ` : window.appState.loading ? '<div class="loading"><div class="spinner"></div></div>' : `
        <!-- VIEW TOGGLE BUTTONS - GOOGLE DRIVE STYLE -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <span id="filesCount" style="font-weight: 600; color: var(--primary-color);">
              ${sortedFiles.length} files 
            </span>
          </div>
          <div style="display: flex; gap: 4px; padding: 4px; background: var(--bg-secondary); border-radius: 6px; border: 1px solid var(--border-color);">
            <!-- Grid View Icon (Active when grid) -->
            <button class="view-toggle-btn ${window.appState.filesView !== 'list' ? 'active' : ''}" 
                    onclick="window.toggleFilesView('grid')" title="Grid view">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <rect x="3" y="3" width="7" height="7" rx="1"/>
                <rect x="14" y="3" width="7" height="7" rx="1"/>
                <rect x="14" y="14" width="7" height="7" rx="1"/>
                <rect x="3" y="14" width="7" height="7" rx="1"/>
              </svg>
            </button>
            
            <!-- List View Icon (Active when list) -->
            <button class="view-toggle-btn ${window.appState.filesView === 'list' ? 'active' : ''}" 
                    onclick="window.toggleFilesView('list')" title="List view">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M8 4h12"/>
                <path d="M8 10h12"/>
                <path d="M8 16h12"/>
              </svg>
            </button>
            
            <div class="view-separator"></div>
            
            <!-- Refresh Button -->
            <button class="action-button" onclick="window.refreshFiles()" style="background: white; color: black; padding: 6px 10px;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px;">
                <path d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
              </svg>
              Refresh
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
              <span style="flex: 3; font-weight: 600;">File Name</span>
              <span style="flex: 1; font-weight: 600; text-align: center;">Tags</span>
              <span style="flex: 1; font-weight: 600; text-align: center;">Modified</span>
              <span style="flex: 1; font-weight: 600; text-align: right;">Size</span>
            </div>
            <div class="files-list-body">
              ${sortedFiles.map(file => window.renderFileListRow(file)).join('')}
            </div>
          </div>
        ` : ''}

        ${window.appState.files.length > (window.appState.filesPerPage || 96) ? `
          <div style="text-align: center; margin-top: 24px;">
            <p style="color: var(--text-secondary);">
              Showing ${sortedFiles.length} of ${window.appState.files.length} files 
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
  const tagCount = file.tagCount || allTags.length;  // ✅ Use accurate count from API
  
  return `
    <div class="file-list-row" data-file-id="${file.id}">
      <div class="file-list-cell name-cell" style="flex: 3;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="font-size: 1.5rem;">${window.getFileIcon(file.mimeType, file.name)}</div>
          <div>
            <div style="font-weight: 600; margin-bottom: 2px;">${window.escapeHtml(file.name)}</div>
            <div style="font-size: 0.8rem; color: var(--text-secondary);">${file.owner || 'Unknown'}</div>
          </div>
        </div>
      </div>
      <div class="file-list-cell tags-cell" style="flex: 1; text-align: center;">
        ${allTags.length ? 
          allTags.slice(0, 3).map(tag => 
            `<span class="tag" style="font-size: 0.75rem; background: var(--tag-bg); padding: 2px 6px; border-radius: 4px;">${window.escapeHtml(tag)}</span>`
          ).join(' ') +
          (tagCount > 3 ? `<span style="font-size: 0.75rem; color: var(--text-secondary);">+${tagCount-3}</span>` : '')
          : '<span style="font-size: 0.75rem; color: var(--text-secondary);">No tags</span>'
        }
      </div>
      <div class="file-list-cell date-cell" style="flex: 1; text-align: center;">
        ${window.formatDate(file.modifiedTime) || 'Unknown'}
      </div>
      <div class="file-list-cell size-cell" style="flex: 1; text-align: right;">
        ${window.formatFileSize(file.size) || 'Unknown'}
      </div>
    </div>
  `;
}


// NEW: Template Library View
// FIXED: Template Library View - Full API Integration
function renderTemplates() {
  return `
    <div class="view-container">
      <div class="view-header">
        <h1 class="view-title">Template Library</h1>
        <p class="view-subtitle">All tagged templates + practice areas</p>
      </div>
      
      ${!window.appState.authenticated ? `
        ${window.IS_ADMIN ? `
          <div class="auth-container">
            <button class="connect-button" onclick="window.navigateTo('dashboard')">Connect Drive</button>
          </div>
        ` : '<div style="color: red; font-weight: 600; text-align: center;">Contact admin to connect Google Drive.</div>'}
      ` : `
        <!-- VIEW TOGGLE BUTTONS - GOOGLE DRIVE STYLE -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <span id="templateCount" style="font-weight: 600; color: var(--primary-color);">Loading...</span>
          </div>
          <div style="display: flex; gap: 4px; padding: 4px; background: var(--bg-secondary); border-radius: 6px; border: 1px solid var(--border-color);">
            <!-- Grid View Icon -->
            <button class="view-toggle-btn ${window.appState.filesView !== 'list' ? 'active' : ''}" 
                    onclick="window.toggleTemplatesView('grid')" title="Grid view">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <rect x="3" y="3" width="7" height="7" rx="1"/>
                <rect x="14" y="3" width="7" height="7" rx="1"/>
                <rect x="14" y="14" width="7" height="7" rx="1"/>
                <rect x="3" y="14" width="7" height="7" rx="1"/>
              </svg>
            </button>
            
            <!-- List View Icon -->
            <button class="view-toggle-btn ${window.appState.filesView === 'list' ? 'active' : ''}" 
                    onclick="window.toggleTemplatesView('list')" title="List view">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M8 4h12"/>
                <path d="M8 10h12"/>
                <path d="M8 16h12"/>
              </svg>
            </button>
            
            <div class="view-separator"></div>
            
            <!-- Refresh Button -->
            <button class="action-button" onclick="window.loadTemplates()" style="background: white; color: black; padding: 6px 10px;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px;">
                <path d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
              </svg>
              Refresh
            </button>
          </div>
        </div>



        <!-- FIXED: Search + Practice Area SIDE-BY-SIDE -->
        <div class="card mb-lg" style="padding: 20px;">
          <div style="display: flex; gap: 16px; align-items: end; max-width: 800px;">
            <!-- Search - Left, wider -->
            <div style="flex: 2; min-width: 300px;">
              <label style="display: block; margin-bottom: 8px; font-weight: 600; font-size: 0.9rem;">Search Templates</label>
              <input type="text" id="templateSearch" placeholder="Search templates by tags..." 
                     style="width: 100%; padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border-color, #ddd); font-size: 1rem; box-sizing: border-box;"
                     oninput="window.loadTemplatesDebounced()">
            </div>
            
            <!-- Practice Area - Right, compact -->
            <div style="flex: 1; min-width: 220px; max-width: 280px;">
              <label style="display: block; margin-bottom: 8px; font-weight: 600; font-size: 0.9rem;">Practice Area</label>
              <select id="practiceAreaFilter" 
                      style="width: 100%; padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border-color, #ddd); font-size: 1rem; box-sizing: border-box;"
                      onchange="window.loadTemplates()">
                <option value="">All TAGS (Loading...)</option>
              </select>
          </div>
        </div>

        <!-- CONTENT CONTAINER -->
        <div id="templatesContent">
          <div class="loading">
            <div class="spinner"></div>
            <p>Loading templates...</p>
          </div>
        </div>
      `}
    </div>
  `;
}

window.loadTemplates = async function() {
  try {
    const contentContainer = document.getElementById('templatesContent');
    if (!contentContainer) return console.error('Templates container missing');
    
    contentContainer.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading...</p></div>';

    // GET FILTER VALUES
    const searchInput = document.getElementById('templateSearch');
    const practiceSelect = document.getElementById('practiceAreaFilter');
    
    const search = searchInput ? searchInput.value.trim() : '';
    const practiceArea = practiceSelect ? practiceSelect.value : '';

    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (practiceArea) params.set('practice_area', practiceArea);

    const response = await fetch(`${window.API_BASE_URL}/templates?${params}`);
    const data = await response.json();

    const countEl = document.getElementById('templateCount');

    // ✅ CACHE TEMPLATE COUNT GLOBALLY
    window.appState.templateCount = data.total || data.templates.length || 0;

    if (data.templates && data.templates.length > 0) {
      // GRID VIEW
      if (window.appState.filesView !== 'list') {
        contentContainer.innerHTML = `
          <div class="files-grid" id="templatesGrid">
            ${data.templates.map(file => window.renderFileCard(file)).join('')}
          </div>
        `;
        setTimeout(() => {
          if (window.attachFileCardListeners) window.attachFileCardListeners();
        }, 100);
      } else {
        // LIST VIEW
        contentContainer.innerHTML = `
          <div class="files-list-container" id="templatesList">
            <div class="files-list-header">
              <span style="flex: 3; font-weight: 600;">Template Name</span>
              <span style="flex: 1; font-weight: 600; text-align: center;">Tags</span>
              <span style="flex: 1; font-weight: 600; text-align: center;">Modified</span>
              <span style="flex: 1; font-weight: 600; text-align: right;">Size</span>
            </div>
            <div class="files-list-body">
              ${data.templates.map(file => window.renderFileListRow(file)).join('')}
            </div>
          </div>
        `;
        setTimeout(() => {
          if (window.attachFileCardListeners) window.attachFileCardListeners();
        }, 100);
      }
      
      // UPDATE COUNTER
      if (countEl) {
        countEl.textContent = `${window.appState.templateCount} templates`;
      }
      
      // RE-POPULATE DROPDOWN
      if (practiceSelect && data.practice_areas && Array.isArray(data.practice_areas)) {
        const currentValue = practiceSelect.value;
        practiceSelect.innerHTML = `
          <option value="">All Areas (${data.practice_areas.length})</option>
          ${data.practice_areas.map(area => 
            `<option value="${area}" ${area === currentValue ? 'selected' : ''}>${area}</option>`
          ).join('')}
        `;
      }
    } else {
      contentContainer.innerHTML = `
        <div class="empty-state">
          <div class="document-icon"></div>
          <h3>No templates match filters</h3>
          <p>Try different search or TAGS</p>
        </div>
      `;
      if (countEl) countEl.textContent = '0 templates';
      window.appState.templateCount = 0; // ✅ Cache 0 when empty
    }
  } catch (error) {
    console.error('Templates load error:', error);
    const contentContainer = document.getElementById('templatesContent');
    if (contentContainer) {
      contentContainer.innerHTML = `
        <div class="empty-state" style="color: #f44336;">
          <div class="warning-icon"></div>
          <h3>Failed to load templates</h3>
          <p>Check: ${error.message}</p>
        </div>
      `;
    }
    window.appState.templateCount = 0; // ✅ Cache 0 on error
  }
};


// ADD THIS EXACTLY AFTER renderTemplates() function
window.loadTemplatesDebounced = window.debounce(window.loadTemplates, 300);

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
        <h1 class="view-title">AI Tags</h1>
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
          <h2 class="card-title">Tag Statistics</h2>
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
          <div class="empty-state-icon"></div>
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
        <h1 class="view-title">Settings</h1>
        <p class="view-subtitle">Configure your preferences</p>
      </div>
      
      <div class="card mb-lg">
        <h2 class="card-title">Google Drive Connection</h2>
        ${window.appState.authenticated ? `
          <div style="display: grid; gap: 16px;">
            <div><strong>Status:</strong> <span style="color: #4caf50;">Connected</span></div>
            ${window.appState.driveInfo?.user ? `
              <div><strong>Account:</strong> ${window.appState.driveInfo.user.email}</div>
              <div><strong>Display Name:</strong> ${window.appState.driveInfo.user.displayName || 'Not available'}</div>
            ` : ''}
            ${window.IS_ADMIN ? `
              <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                <button class="search-button" onclick="window.initiateGoogleAuth()">
                  Reconnect Drive
                </button>
                <button class="logout-button" onclick="window.logoutUser()">
                  Logout
                </button>
              </div>
            ` : ''}
          </div>
        ` : `
          ${window.IS_ADMIN ? `
          <div>
            <p>Not connected to Google Drive</p>
            <button class="connect-button" onclick="window.initiateGoogleAuth()">
              Connect Now
            </button>
          </div>
          ` : '<div><p>Google Drive connection is required.</p></div>'}
        `}
      </div>
      
      <div class="card mb-lg">
        <h2 class="card-title">Appearance</h2>
        <div style="display: grid; gap: 16px;">
          <div class="filter-group">
            <label class="filter-label">Theme</label>
            <div style="display: flex; gap: 12px;">
              <button 
                class="theme-button ${window.appState.theme === 'light' ? 'active' : ''}" 
                onclick="window.toggleTheme()"
              >
                ${window.appState.theme === 'light' ? 'Light Mode (Active)' : 'Switch to Light'}
              </button>
              <button 
                class="theme-button ${window.appState.theme === 'dark' ? 'active' : ''}" 
                onclick="window.toggleTheme()"
              >
                ${window.appState.theme === 'dark' ? 'Dark Mode (Active)' : 'Switch to Dark'}
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
        <h2 class="card-title">Display Settings</h2>
        <div style="display: grid; gap: 16px;">
          <div class="filter-group">
            <label class="filter-label">Files per page</label>
            <select class="filter-select" onchange="window.changeFilesPerPage(event.target.value)">
              <option value="12" ${window.appState.filesPerPage === 12 ? 'selected' : ''}>12</option>
              <option value="24" ${window.appState.filesPerPage === 24 ? 'selected' : ''}>24</option>
              <option value="48" ${window.appState.filesPerPage === 48 ? 'selected' : ''}>48</option>
              <option value="96" ${window.appState.filesPerPage === 96 ? 'selected' : ''}>96(Default)</option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="card">
        <h2 class="card-title">About Tagging</h2>
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

// Auto-load on filter change
document.addEventListener('change', function(e) {
  if (e.target.id === 'practiceAreaFilter' || e.target.id === 'subPracticeFilter' || e.target.id === 'templateSearch') {
    window.loadTemplates();
  }
});


// Fetch and update dashboard stats
window.refreshDashboardStats = async function() {
  try {
    const userEmail = window.appState.userEmail || localStorage.getItem('googleUserEmail') || 'public';
    
    // Refresh clause count
    const clauseResponse = await fetch(`${window.API_BASE_URL}/clauses/library?user_email=${encodeURIComponent(userEmail)}`);
    let clauseCount = 0;
    if (clauseResponse.ok) {
      const clauseData = await clauseResponse.json();
      clauseCount = clauseData.clauses?.length || 0;
    }
    
    // Refresh template count
    await window.refreshTemplateCount();
    
    // Cache values
    window.appState.clauseCount = clauseCount;
    
    // Update DOM
    const stats = document.querySelectorAll('.stat-number');
    if (stats[1]) stats[1].textContent = window.appState.templateCount; // Templates
    if (stats[2]) stats[2].textContent = clauseCount; // Clauses
    
    if (window.showNotification) {
      window.showNotification(`Updated: ${window.appState.templateCount} templates, ${clauseCount} clauses`, 'success');
    }
  } catch (error) {
    console.error('Failed to refresh stats:', error);
  }
};


// Update dashboard template count from API
window.refreshTemplateCount = async function() {
  try {
    const response = await fetch(`${window.API_BASE_URL}/templates`);
    if (response.ok) {
      const data = await response.json();
      window.appState.templateCount = data.total || data.templates?.length || 0;
      
      // Update dashboard stat if visible
      const templateStat = document.querySelector('.stat-card:nth-child(2) .stat-number');
      if (templateStat) {
        templateStat.textContent = window.appState.templateCount;
      }
    }
  } catch (error) {
    console.error('Failed to refresh template count:', error);
  }
};


// Auto-refresh stats on dashboard load
window.updateDashboardOnLoad = function() {
  setTimeout(() => {
    if (window.appState.authenticated) {
      window.refreshDashboardStats();
    }
  }, 500);
};


// Make functions globally available
window.renderDashboard = renderDashboard;
window.renderSearch = renderSearch;
window.renderFiles = renderFiles;
window.renderAITags = renderAITags;
window.renderSettings = renderSettings;
window.renderTemplates = renderTemplates;