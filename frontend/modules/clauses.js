// modules/clauses.js - Clause Management
console.log('Loading clauses.js...');

// Show Clause Library view
async function showClauseLibrary() {
  console.log('📋 Loading Clause Library...');
  
  // Check if user is authenticated
  if (!window.appState.authenticated) {
    console.log('User not authenticated, showing login prompt');
    
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      mainContent.innerHTML = `
        <div class="view-container">
          <div class="view-header">
            <h1 class="view-title">📋 Clause Library</h1>
            <p class="view-subtitle">Browse and manage your saved clauses</p>
          </div>
          
          <div class="auth-container">
            <div class="auth-card">
              <h2>🔐 Authentication Required</h2>
              <p>Please connect to Google Drive to access your personal clause library.</p>
              <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 1rem;">
                Your clause library is private and only accessible when you're logged in.
              </p>
              <button class="connect-button" onclick="window.initiateGoogleAuth()" style="margin-top: 2rem;">
                🔗 Connect to Google Drive
              </button>
              <button class="btn-secondary" onclick="window.navigateTo('dashboard')" style="margin-top: 1rem;">
                ← Back to Dashboard
              </button>
            </div>
          </div>
        </div>
      `;
    }
    return;
  }
  
  // User is authenticated, proceed to load library
  window.appState.currentView = 'clause-library';
  if (window.updateNavigation) window.updateNavigation('clause-library');
  
  const content = `
      <div class="view-container">
          <div class="view-header">
              <h1 class="view-title">📋 Clause Library</h1>
              <p class="view-subtitle">Browse and manage your saved clauses</p>
          </div>
          
          <div class="search-section">
              <div class="search-bar">
                  <input 
                      type="text" 
                      id="clauseSearchInput" 
                      class="search-input" 
                      placeholder="🔍 Search clauses by title..."
                      onkeyup="window.filterClauses()"
                  >
              </div>
          </div>
          
          <div id="clauseLibraryContent" class="clause-library-content">
              <div class="loading">
                  <div class="spinner"></div>
              </div>
          </div>
      </div>
  `;
  
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.innerHTML = content;
  }
  
  await loadClauseLibrary();
}

// Load clause library
async function loadClauseLibrary() {
  try {
    // Double-check authentication
    if (!window.appState.authenticated) {
      console.warn('User not authenticated, cannot load clause library');
      const container = document.getElementById('clauseLibraryContent');
      if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔒</div>
                <h3>Authentication Required</h3>
                <p>Please login to access your clause library</p>
                <button onclick="window.initiateGoogleAuth()" class="btn-primary" style="margin-top: 1rem;">
                    Connect to Google Drive
                </button>
            </div>
        `;
      }
      return;
    }
    
    console.log('Loading clause library for authenticated user...');
    const response = await fetch(`${window.API_BASE_URL}/clauses/library`);
    
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error('Authentication failed. Please login again.');
      }
      throw new Error('Failed to load clause library');
    }
    
    const data = await response.json();
    console.log(`📚 Loaded ${data.count} clauses from library`);
    
    displayClauseLibrary(data.clauses);
    
  } catch (error) {
    console.error('Error loading clause library:', error);
    const container = document.getElementById('clauseLibraryContent');
    if (container) {
      if (error.message.includes('Authentication')) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔒</div>
                <h3>Authentication Error</h3>
                <p>${error.message}</p>
                <button onclick="window.initiateGoogleAuth()" class="btn-primary" style="margin-top: 1rem;">
                    Reconnect to Google Drive
                </button>
            </div>
        `;
      } else {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <p>Failed to load clause library</p>
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.5rem;">
                  ${error.message}
                </p>
            </div>
        `;
      }
    }
  }
}

// Display clause library
function displayClauseLibrary(clauses) {
  const container = document.getElementById('clauseLibraryContent');
  if (!container) return;
  
  if (!clauses || clauses.length === 0) {
    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">📋</div>
            <h3>No clauses saved yet</h3>
            <p>Extract clauses from documents and save them to build your library</p>
            <div style="margin-top: 1.5rem; color: var(--text-secondary); font-size: 0.9rem;">
              <p>📝 <strong>How to add clauses:</strong></p>
              <ol style="text-align: left; margin: 0.5rem 0 0 1.5rem;">
                <li>Connect to Google Drive</li>
                <li>Browse your files</li>
                <li>Click on a document to open it</li>
                <li>Click "Extract Clauses"</li>
                <li>Select a clause and click "Save to Library"</li>
              </ol>
            </div>
        </div>
    `;
    return;
  }
  
  const clauseCards = clauses.map(clause => `
      <div class="clause-library-card" data-clause-id="${clause.id}" data-clause-title="${window.escapeHtml(clause.title)}">
          <div class="clause-card-header">
              <h3 class="clause-card-title">${window.escapeHtml(clause.title)}</h3>
              ${clause.section_number ? `<span class="clause-section-badge">${window.escapeHtml(clause.section_number)}</span>` : ''}
          </div>
          
          <div class="clause-card-preview">
              ${window.escapeHtml(clause.content_preview)}
          </div>
          
          <div class="clause-card-meta">
              <div class="clause-meta-item">
                  <span class="meta-label">From:</span>
                  <span class="meta-value">${window.escapeHtml(clause.source_document || 'Unknown')}</span>
              </div>
              <div class="clause-meta-item">
                  <span class="meta-label">Saved:</span>
                  <span class="meta-value">${window.formatDate(clause.created_at)}</span>
              </div>
          </div>
          
          <button class="btn-view-files" onclick="window.viewClauseFiles(${clause.id}, event)">
              📄 View Files with this Clause
          </button>
      </div>
  `).join('');
  
  container.innerHTML = `
      <div class="clause-library-grid">
          ${clauseCards}
      </div>
      <div style="text-align: center; margin-top: 2rem; color: var(--text-secondary); font-size: 0.9rem;">
        <p>📚 Showing ${clauses.length} clauses from your Google Drive</p>
      </div>
  `;
}

// View clause files - ADD AUTH CHECK HERE TOO
async function viewClauseFiles(clauseId, event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  
  // Check authentication
  if (!window.appState.authenticated) {
    window.showNotification('🔒 Please login to view clause files', 'error');
    return;
  }
  
  console.log(`🔍 Loading files for clause ID: ${clauseId}`);
  
  try {
    const url = `${window.API_BASE_URL}/clauses/library/${clauseId}/files`;
    console.log(`📡 Fetching from: ${url}`);
    
    const response = await fetch(url);
    
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error('Authentication failed. Please login again.');
      }
      throw new Error(`Failed to load files: ${response.status}`);
    }
    
    const data = await response.json();
    console.log(`✅ Found ${data.files ? data.files.length : 0} files`);
    
    showClauseFilesModal(data);
    
  } catch (error) {
    console.error('Error loading clause files:', error);
    
    if (error.message.includes('Authentication')) {
      window.showNotification('🔒 Authentication required', 'error');
      setTimeout(() => {
        window.initiateGoogleAuth();
      }, 1500);
    } else {
      alert('Failed to load files for this clause: ' + error.message);
    }
  }
}

// Show clause files modal
// 🔥 PREMIUM "Files with this Clause" Modal
function showClauseFilesModal(data) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.style.display = 'flex';
  modal.id = 'clauseFilesModal';
  
  const filesHtml = data.files && data.files.length > 0 ? 
    data.files.map(file => {
      const matchType = file.match_type || 'similar';
      const badgeClass = matchType === 'exact' ? 'exact' : 'similar';
      const icon = window.getFileIcon ? window.getFileIcon(file.mimeType, file.title) : '📄';
      
      return `
        <div class="clause-file-item" onclick="window.viewFile('${file.id}')" title="Open ${file.title}">
          <div class="file-icon">${icon}</div>
          <div class="file-details">
            <div class="file-title">${window.escapeHtml(file.title)}</div>
            <div class="file-meta-small">
              <span>📅 ${window.formatDate(file.modified_at)}</span>
              <span style="color: var(--text-secondary);">👤 ${file.owner || 'Unknown'}</span>
            </div>
          </div>
          <span class="match-badge ${badgeClass}">${matchType.toUpperCase()}</span>
          <button class="btn-open-file">
            <i class="fas fa-external-link-alt"></i> Open
          </button>
        </div>
      `;
    }).join('') : `
      <div class="empty-state" style="text-align: center; padding: 3rem;">
        <i class="fas fa-inbox" style="font-size: 4rem; color: var(--border-color);"></i>
        <h3 style="color: var(--text-primary);">No files found</h3>
        <p style="color: var(--text-secondary);">No documents contain this clause</p>
      </div>
    `;
  
  modal.innerHTML = `
    <div class="modal-overlay" onclick="this.parentNode.remove()"></div>
    <div class="modal-content" style="max-width: 900px; max-height: 85vh;">
      <div class="modal-header">
        <div>
          <h2 style="margin: 0;">📋 ${window.escapeHtml(data.clause_title || 'Clause Files')}</h2>
          <p class="modal-subtitle" style="margin: 4px 0 0 0;">
            ${data.files ? data.files.length : 0} file(s) contain this clause
          </p>
        </div>
        <button class="close-btn" onclick="this.closest('.modal').remove()" title="Close">
          <i class="fas fa-times"></i>
        </button>
      </div>
      
      <div class="modal-body" style="padding: 2rem;">
        <!-- Clause Preview -->
        ${data.clause_content ? `
          <div class="clause-content-preview" style="margin-bottom: 2rem; padding: 1.5rem; background: var(--bg-tertiary); border-radius: 12px; border-left: 4px solid var(--primary-color);">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
              <i class="fas fa-quote-left" style="color: var(--primary-color); font-size: 1.5rem;"></i>
              <strong style="color: var(--primary-color);">Clause Preview:</strong>
            </div>
            <div style="color: var(--text-primary); line-height: 1.6; font-size: 0.95rem; max-height: 120px; overflow: hidden;">
              ${window.escapeHtml(data.clause_content).substring(0, 400)}${data.clause_content.length > 400 ? '...' : ''}
            </div>
          </div>
        ` : ''}
        
        <!-- Files List -->
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <h3 style="margin: 0 0 1rem 0; color: var(--primary-color); display: flex; align-items: center; gap: 8px;">
            <i class="fas fa-file-contract"></i> Files Containing This Clause
          </h3>
          <div class="clause-files-list">${filesHtml}</div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button onclick="this.closest('.modal').remove()" class="btn-primary" style="min-width: 140px;">
          <i class="fas fa-times"></i> Close
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
}


// Close clause files modal
function closeClauseFilesModal() {
  const modal = document.getElementById('clauseFilesModal');
  if (modal) {
    modal.remove();
  }
}

// Filter clauses
function filterClauses() {
  const searchInput = document.getElementById('clauseSearchInput');
  if (!searchInput) return;
  
  const query = searchInput.value.toLowerCase();
  const cards = document.querySelectorAll('.clause-library-card');
  
  cards.forEach(card => {
    const title = card.dataset.clauseTitle.toLowerCase();
    if (title.includes(query)) {
      card.style.display = 'block';
    } else {
      card.style.display = 'none';
    }
  });
}

// Make functions globally available
window.showClauseLibrary = showClauseLibrary;
window.loadClauseLibrary = loadClauseLibrary;
window.displayClauseLibrary = displayClauseLibrary;
window.viewClauseFiles = viewClauseFiles;
window.showClauseFilesModal = showClauseFilesModal;
window.closeClauseFilesModal = closeClauseFilesModal;
window.filterClauses = filterClauses;