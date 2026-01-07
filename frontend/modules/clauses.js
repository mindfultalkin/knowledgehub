// modules/clauses.js - Clause Management
console.log('Loading clauses.js...');

// Show Clause Library view
async function showClauseLibrary() {
  console.log('Loading Clause Library...');
  
  // Check if user is authenticated
  if (!window.appState.authenticated) {
    console.log('User not authenticated, showing login prompt');
    
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      mainContent.innerHTML = `
        <div class="view-container">
          <div class="view-header">
            <h1 class="view-title">Clause Library</h1>
            <p class="view-subtitle">Browse and manage your saved clauses</p>
          </div>
          
          <div class="auth-container">
            <div class="auth-card">
              <h2>Authentication Required</h2>
              <p>Please connect to Google Drive to access your personal clause library.</p>
              <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 1rem;">
                Your clause library is private and only accessible when you're logged in.
              </p>
              <button class="connect-button" onclick="window.initiateGoogleAuth()" style="margin-top: 2rem;">
                Connect to Google Drive
              </button>
              <button class="btn-secondary" onclick="window.navigateTo('dashboard')" style="margin-top: 1rem;">
                Back to Dashboard
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
              <h1 class="view-title">Clause Library</h1>
              <p class="view-subtitle">Browse and manage your saved clauses</p>
          </div>
          
          <div class="search-section">
              <div class="search-bar">
                  <input 
                      type="text" 
                      id="clauseSearchInput" 
                      class="search-input" 
                      placeholder="Search clauses by title..."
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
            <div class="empty-state-icon"></div>
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

    // ✅ TRY MULTIPLE WAYS TO GET USER EMAIL
    let userEmail = window.appState.userEmail || 
                   localStorage.getItem('googleUserEmail') ||
                   window.appState.user?.email ||
                   window.appState.email;

    // ✅ FALLBACK: Get from Google Drive API
    if (!userEmail) {
      try {
        const response = await fetch(`${window.API_BASE_URL}/auth/account-info`);
        const data = await response.json();
        if (data.authenticated && data.email) {
          userEmail = data.email;
          // Save for future use
          window.appState.userEmail = userEmail;
          localStorage.setItem('googleUserEmail', userEmail);
        }
      } catch (apiError) {
        console.warn('Could not fetch user email from API:', apiError);
      }
    }

    // ✅ FINAL CHECK
    if (!userEmail) {
      console.warn('No user email available - showing public library');
      userEmail = 'public';  // Fallback - shows all or empty
    }

    console.log('🔍 Loading clause library for:', userEmail);
    
    // ✅ SEND EMAIL AS QUERY PARAM
    const url = `${window.API_BASE_URL}/clauses/library?user_email=${encodeURIComponent(userEmail)}`;
    console.log('📡 Fetching:', url);
    
    const response = await fetch(url);
    
    if (!response.ok) {
      console.error('Response status:', response.status);
      if (response.status === 401 || response.status === 403) {
        throw new Error('Authentication failed. Please login again.');
      }
      if (response.status === 400) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Invalid request');
      }
      if (response.status === 404) {
        console.log('No clauses found for this user');
      }
      throw new Error(`Server error: ${response.status}`);
    }
    
    const data = await response.json();
    console.log(`✅ Loaded ${data.count || 0} clauses for ${userEmail}`);
    
    displayClauseLibrary(data.clauses || []);
    
  } catch (error) {
    console.error('❌ Error loading clause library:', error);
    const container = document.getElementById('clauseLibraryContent');
    if (container) {
      if (error.message.includes('Authentication') || error.message.includes('email')) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon"></div>
            <h3>Setup Required</h3>
            <p>${error.message}</p>
            <button onclick="window.initiateGoogleAuth()" class="btn-primary" style="margin-top: 1rem;">
                🔗 Connect Google Drive
            </button>
          </div>
        `;
      } else {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon"></div>
            <h3>No Clauses Found</h3>
            <p>Your personal clause library is empty. Extract clauses from documents to get started!</p>
            <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 1rem;">
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
            <div class="empty-state-icon"></div>
            <h3>No clauses saved yet</h3>
            <p>Extract clauses from documents and save them to build your library</p>
            <div style="margin-top: 1.5rem; color: var(--text-secondary); font-size: 0.9rem;">
              <p><strong>How to add clauses:</strong></p>
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
              View Files with this Clause
          </button>
      </div>
  `).join('');
  
  container.innerHTML = `
      <div class="clause-library-grid">
          ${clauseCards}
      </div>
      <div style="text-align: center; margin-top: 2rem; color: var(--text-secondary); font-size: 0.9rem;">
        <p>Showing ${clauses.length} clauses from your Google Drive</p>
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
    window.showNotification('Please login to view clause files', 'error');
    return;
  }
  
  console.log(`Loading files for clause ID: ${clauseId}`);
  
  try {
    const url = `${window.API_BASE_URL}/clauses/library/${clauseId}/files`;
    console.log(`Fetching from: ${url}`);
    
    const response = await fetch(url);
    
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error('Authentication failed. Please login again.');
      }
      throw new Error(`Failed to load files: ${response.status}`);
    }
    
    const data = await response.json();
    console.log(`Found ${data.files ? data.files.length : 0} files`);
    
    showClauseFilesModal(data);
    
  } catch (error) {
    console.error('Error loading clause files:', error);
    
    if (error.message.includes('Authentication')) {
      window.showNotification('Authentication required', 'error');
      setTimeout(() => {
        window.initiateGoogleAuth();
      }, 1500);
    } else {
      alert('Failed to load files for this clause: ' + error.message);
    }
  }
}

// Show clause files modal
// PREMIUM "Files with this Clause" Modal
// FIXED: Scrollable Modal - Shows ALL Files + Badge Only
function showClauseFilesModal(data) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.style.display = 'flex';
  modal.id = 'clauseFilesModal';
  
  const filesHtml = data.files && data.files.length > 0 ? 
    data.files.map((file, index) => {
      const matchType = file.match_type || 'similar';
      const badgeClass = matchType === 'exact' ? 'badge-exact' : 'badge-similar';
      const icon = window.getFileIcon ? window.getFileIcon(file.mimeType, file.title) : '';
      
      return `
        <div class="clause-file-item ${matchType}" onclick="window.viewFile('${file.id}')" title="Open ${file.title}">
          <div class="file-icon">${icon}</div>
          <div class="file-details">
            <div class="file-title">${window.escapeHtml(file.title)}</div>
            <div class="file-meta">
              <span class="date-small">${window.formatDate(file.modified_at)}</span>
              <span class="owner-small">${file.owner || 'Unknown'}</span>
            </div>
          </div>
          <span class="match-badge ${badgeClass}">
            ${matchType === 'exact' ? 'EXACT' : 'SIMILAR'}
          </span>
        </div>
      `;
    }).join('') : `
      <div class="empty-state" style="grid-column: 1/-1; text-align: center; padding: 3rem;">
        <div class="empty-state-icon"></div>
        <h3 style="color: var(--text-primary);">No matching files</h3>
        <p style="color: var(--text-secondary);">No documents contain this clause</p>
      </div>
    `;
  
  modal.innerHTML = `
    <div class="modal-overlay" onclick="document.getElementById('clauseFilesModal')?.remove()"></div>
    <div class="modal-content" style="width: 95%; max-width: 1000px; max-height: 90vh;">
      <!-- Header -->
      <div class="modal-header">
        <div>
          <h2 style="margin: 0; display: flex; align-items: center; gap: 12px;">
            <div class="modal-icon"></div>
            ${window.escapeHtml(data.clause_title || 'Clause Files')}
          </h2>
          <p class="modal-subtitle" style="margin: 8px 0 0 0; color: var(--primary-color); font-weight: 600;">
            ${data.files ? data.files.length : 0} file(s) found
          </p>
        </div>
        <button class="close-btn" onclick="document.getElementById('clauseFilesModal')?.remove()" title="Close (Esc)">
          <div class="close-icon"></div>
        </button>
      </div>
      
      <!-- Clause Preview -->
      ${data.clause_content ? `
        <div class="clause-preview" style="padding: 1.5rem; margin: 0; background: var(--bg-secondary); border-radius: 0 0 12px 12px; border-bottom: 1px solid var(--border-color);">
          <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <div class="quote-icon"></div>
            <strong style="color: var(--primary-color);">Clause Preview:</strong>
          </div>
          <div style="color: var(--text-primary); line-height: 1.6; font-size: 0.95rem; max-height: 100px; overflow: hidden; position: relative;">
            ${window.escapeHtml(data.clause_content).substring(0, 350)}${data.clause_content.length > 350 ? '...' : ''}
          </div>
        </div>
      ` : ''}
      
      <!-- SCROLLABLE FILES GRID - Shows ALL 7 Files -->
      <div class="modal-body">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-color);">
          <h3 style="margin: 0; display: flex; align-items: center; gap: 8px; color: var(--text-primary);">
            <div class="file-contract-icon"></div> Files Containing This Clause
          </h3>
          <span style="color: var(--primary-color); font-weight: 600; font-size: 1.1rem;">
            ${data.files ? data.files.length : 0} total
          </span>
        </div>
        
        <div class="clause-files-grid" style="max-height: 450px; overflow-y: auto; padding-right: 8px;">
          <!-- Custom scrollbar -->
          <style>
            .clause-files-grid::-webkit-scrollbar { width: 6px; }
            .clause-files-grid::-webkit-scrollbar-track { background: var(--bg-tertiary); border-radius: 3px; }
            .clause-files-grid::-webkit-scrollbar-thumb { 
              background: var(--border-color); border-radius: 3px; 
            }
            .clause-files-grid::-webkit-scrollbar-thumb:hover { background: var(--primary-color); }
          </style>
          ${filesHtml}
        </div>
      </div>
      
      <!-- Footer -->
      <div class="modal-footer" style="justify-content: flex-end; padding: 1rem 1.5rem;">
        <button onclick="document.getElementById('clauseFilesModal')?.remove()" 
                class="btn-secondary" style="min-width: 120px;">
          <div class="times-icon"></div> Close
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // ESC key close
  const escHandler = (e) => {
    if (e.key === 'Escape') {
      modal.remove();
      document.removeEventListener('keydown', escHandler);
    }
  };
  document.addEventListener('keydown', escHandler);
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