// modules/clauses.js - Modern Clause Library (simplified modal)
console.log('✅ Loading clauses.js...');

// Global variables
let allClauses = [];

// Show Clause Library view
async function showClauseLibrary() {
  console.log('📚 Loading Clause Library...');

  // Check if user is authenticated
  if (!window.appState.authenticated) {
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      mainContent.innerHTML = `
        <div class="auth-required-view">
          <div class="auth-card">
            <div class="auth-icon"></div>
            <h2>Authentication Required</h2>
            <p>Please connect to Google Drive to access your personal clause library.</p>
            <button class="btn-primary" onclick="window.initiateGoogleAuth()">
              <span class="btn-icon"></span> Connect to Google Drive
            </button>
          </div>
        </div>
      `;
    }
    return;
  }

  // User is authenticated
  window.appState.currentView = 'clause-library';
  if (window.updateNavigation) window.updateNavigation('clause-library');

  const content = `
    <div class="clause-library-view">
      <!-- Header -->
      <div class="library-header">
        <div class="header-content">
          <h1 class="page-title">Clause Library</h1>
          <p class="page-subtitle">Manage and organize your saved legal clauses</p>
        </div>
        <div class="header-actions">
          <div class="search-container">
            <input 
              type="text" 
              id="clauseSearchInput" 
              class="search-input" 
              placeholder="Search clauses by tags ..."
              onkeyup="window.filterClauses()"
            >
            <span class="search-icon">🔍</span>
          </div>
          <button class="btn-filter" onclick="window.showTagFilterModal()">
            <span class="btn-icon"></span>
            Filter by Tags
            ${window.appState.activeTagFilters?.length > 0 ? 
              `<span class="badge">${window.appState.activeTagFilters.length}</span>` : ''}
          </button>
        </div>
      </div>
      
      <!-- Active Filters -->
      <div id="activeFiltersBar" class="active-filters-bar">
        ${window.appState.activeTagFilters?.length > 0 ? `
          <div class="active-filters">
            <span class="filters-label">Active filters:</span>
            <span class="filter-pill">
              ${window.appState.activeTagFilters.length} tag(s)
              <button class="clear-filter" onclick="window.clearTagFilters()">×</button>
            </span>
          </div>
        ` : ''}
      </div>
      
      <!-- Main Content -->
      <div id="clauseLibraryContent" class="clause-library-content">
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Loading your clauses...</p>
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
  console.log('🔍 Loading clause library...');

  try {
    // Get user email
    let userEmail =
      window.appState.userEmail ||
      localStorage.getItem('googleUserEmail') ||
      window.appState.user?.email;

    if (!userEmail) {
      try {
        const response = await fetch(`${window.API_BASE_URL}/auth/account-info`);
        const data = await response.json();
        if (data.authenticated && data.email) {
          userEmail = data.email;
          window.appState.userEmail = userEmail;
          localStorage.setItem('googleUserEmail', userEmail);
        }
      } catch (apiError) {
        console.warn('Could not fetch user email from API:', apiError);
      }
    }

    if (!userEmail) {
      userEmail = 'public';
    }

    console.log('Loading library for:', userEmail);

    // Load all clauses
    const url = `${window.API_BASE_URL}/clauses/library?user_email=${encodeURIComponent(
      userEmail
    )}`;
    console.log('Fetching from:', url);

    const response = await fetch(url);
    if (!response.ok) {
      console.error('Response error:', response.status);
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    console.log('✅ Received data:', data);

    allClauses = data.clauses || [];
    console.log(`Loaded ${allClauses.length} clauses`);

    // Filter clauses if tag filters are active
    let filteredClauses = allClauses;
    const activeTagIds = window.appState.activeTagFilters || [];

    if (activeTagIds.length > 0) {
      console.log(`Filtering by ${activeTagIds.length} tag(s)`);
      filteredClauses = await loadFilteredClauses(activeTagIds, userEmail);
    }

    displayClauseLibrary(filteredClauses);
  } catch (error) {
    console.error('❌ Error loading clause library:', error);
    const container = document.getElementById('clauseLibraryContent');
    if (container) {
      container.innerHTML = `
        <div class="error-state">
          <div class="error-icon">❌</div>
          <h3>Error Loading Clauses</h3>
          <p>${error.message}</p>
          <button onclick="window.loadClauseLibrary()" class="btn-secondary">
            Try Again
          </button>
        </div>
      `;
    }
  }
}

// Load filtered clauses by tags
async function loadFilteredClauses(tagIds, userEmail) {
  const filteredClauses = [];

  for (const tagId of tagIds) {
    try {
      const url = `${window.API_BASE_URL}/clauses/library/filter/by-tag?tag_id=${tagId}&user_email=${encodeURIComponent(
        userEmail
      )}`;
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        data.clauses.forEach((clause) => {
          if (!filteredClauses.find((c) => c.id === clause.id)) {
            filteredClauses.push(clause);
          }
        });
      }
    } catch (error) {
      console.warn(`Error loading tag ${tagId}:`, error);
    }
  }

  return filteredClauses;
}

// Display clause library
function displayClauseLibrary(clauses) {
  const container = document.getElementById('clauseLibraryContent');
  if (!container) {
    console.error('Container not found!');
    return;
  }

  if (!clauses || clauses.length === 0) {
    const noClausesMessage =
      window.appState.activeTagFilters?.length > 0
        ? 'No clauses match your filter criteria.'
        : 'Your clause library is empty. Extract clauses from documents to get started.';

    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📋</div>
        <h3>No Clauses Found</h3>
        <p>${noClausesMessage}</p>
        ${
          window.appState.activeTagFilters?.length > 0
            ? `<button onclick="window.clearTagFilters()" class="btn-primary">
                 Clear Filters
               </button>`
            : ''
        }
      </div>
    `;
    return;
  }

  const clauseCards = clauses
    .map((clause) => {
      const tags = clause.tags || [];
      return `
        <div class="clause-card" data-clause-id="${clause.id}">
          <!-- Card Header -->
          <div class="card-header">
            <div class="title-section">
              <h3 class="clause-title" title="${window.escapeHtml(clause.title)}">
                ${window.escapeHtml(clause.title)}
              </h3>
              ${
                clause.section_number
                  ? `<span class="section-tag">${window.escapeHtml(
                      clause.section_number
                    )}</span>`
                  : ''
              }
            </div>
            <button class="card-menu-btn" onclick="window.openClauseModal(${
              clause.id
            })" title="View clause">
              ⋮
            </button>
          </div>

          <!-- Content Preview -->
          <div class="content-preview">
            ${window.escapeHtml(clause.content_preview || 'No preview available')}
          </div>

          <!-- Tags -->
          <div class="tags-container">
            ${
              tags.length > 0
                ? tags
                    .slice(0, 3)
                    .map(
                      (tag) =>
                        `<span class="tag">${window.escapeHtml(tag.name)}</span>`
                    )
                    .join('')
                : '<span class="no-tags">No tags</span>'
            }
            ${
              tags.length > 3
                ? `<span class="more-tags">+${tags.length - 3} more</span>`
                : ''
            }
          </div>

          <!-- Metadata -->
          <div class="metadata">
            <div class="meta-item">
              <span class="meta-icon">📄</span>
              <span class="meta-text" title="${window.escapeHtml(
                clause.source_document || 'Unknown'
              )}">
                ${window.escapeHtml(
                  (clause.source_document || 'Unknown').substring(0, 25)
                )}${(clause.source_document || '').length > 25 ? '...' : ''}
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-icon"></span>
              <span class="meta-text">${window.formatDate(
                clause.created_at
              )}</span>
            </div>
          </div>

          <!-- Action Button -->
          <button class="view-btn" onclick="window.openClauseModal(${clause.id})">
            <span class="btn-icon"></span> View Clause
          </button>
        </div>
      `;
    })
    .join('');

  container.innerHTML = `
    <div class="clauses-grid">
      ${clauseCards}
    </div>
    <div class="results-footer">
      <p>Showing ${clauses.length} clause${clauses.length !== 1 ? 's' : ''}</p>
    </div>
  `;
}

// Open clause modal (same API logic, simpler modal)
// ✅ FIXED: Use existing list endpoint + find clause by ID
async function openClauseModal(clauseId) {
  console.log('Opening modal for clause ID:', clauseId);

  try {
    let userEmail = window.appState.userEmail || localStorage.getItem('googleUserEmail');
    if (!userEmail) {
      window.showNotification('Please login first', 'error');
      return;
    }

    // ✅ USE EXISTING LIST ENDPOINT (this works)
    const url = `${window.API_BASE_URL}/clauses/library?user_email=${encodeURIComponent(userEmail)}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to load clause library');

    const data = await response.json();
    const clause = data.clauses.find(c => c.id == clauseId);

    if (!clause) {
      window.showNotification('Clause not found', 'error');
      return;
    }

    // Load tags for this clause
    let tags = [];
    try {
      const tagsResponse = await fetch(`${window.API_BASE_URL}/clauses/library/${clauseId}/tags?user_email=${encodeURIComponent(userEmail)}`);
      if (tagsResponse.ok) {
        const tagsData = await tagsResponse.json();
        tags = tagsData.tags || [];
      }
    } catch (e) {
      console.warn('Could not load tags:', e);
      tags = clause.tags || []; // Fallback to tags in clause object
    }

    // Files section - Skip for now (no endpoint)
    const containingFiles = []; 

    showClauseModal(clause, tags, containingFiles);
  } catch (error) {
    console.error('❌ Error opening clause modal:', error);
    window.showNotification('Failed to load clause details', 'error');
  }
}



// Simplified clause modal: only title, content, tags, copy, close
function showClauseModal(clause, tags, containingFiles) {
  const modalOverlay = document.createElement('div');
  modalOverlay.className = 'modal-overlay';
  modalOverlay.id = 'clauseModal';

  const safeTitle = window.escapeHtml(clause.title || '');
  const safeContent = window.escapeHtml(clause.content || clause.content_preview || 'No content available');

  modalOverlay.innerHTML = `
    <div class="modal-container clause-modal">
      <!-- Header -->
      <div class="modal-header">
        <div class="modal-title-section">
          <h2 class="modal-title">${safeTitle}</h2>
          ${clause.section_number ? `<span class="section-tag">${window.escapeHtml(clause.section_number)}</span>` : ''}
        </div>
        <button class="modal-close-btn" onclick="window.closeClauseModal()" title="Close">×</button>
      </div>

      <!-- Body -->
      <div class="modal-body">
        <!-- COMPLETE Clause Content (Scrollable) -->
        <div class="modal-section full-content-section">
          <div class="section-header">
            <h3 class="section-title">Clause Content</h3>
            <button class="copy-btn-perplexity" onclick="window.copyClauseContent('${safeTitle}', \`${safeContent}\`)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
              </svg>
            </button>
          </div>
          <div class="content-container scrollable-clause-content">
            <div class="full-clause-content">${safeContent}</div>
          </div>
        </div>

        <!-- Tags Section -->
        <div class="modal-section">
          <div class="section-header">
            <h3 class="section-title">Tags</h3>
          </div>
          
          <!-- Existing Tags -->
          <div class="tags-display">
            ${tags.length > 0 ? tags.map(tag => `
              <span class="tag tag-bordered removable-tag" data-tag-id="${tag.id}">
                ${window.escapeHtml(tag.name)}
                <button class="tag-remove-btn-small" onclick="window.removeClauseTag(${clause.id}, ${tag.id})" title="Remove">×</button>
              </span>
            `).join('') : '<span class="no-tags">No tags added</span>'}
          </div>

          <!-- Add New Tag -->
          <div class="add-tag-section">
            <div class="add-tag-input-container">
              <input type="text" id="tagInput" class="tag-input" placeholder="Type tag name and press Enter or click Add">
              <button class="add-tag-btn" onclick="window.addTagToClause(${clause.id})">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Files Containing This Clause -->
        ${containingFiles.length > 0 ? `
        <div class="modal-section">
          <div class="section-header">
            <h3 class="section-title">Files Containing This Clause (${containingFiles.length})</h3>
          </div>
          <div class="containing-files-list">
            ${containingFiles.map(file => `
              <div class="containing-file-item">
                <span class="file-icon">📄</span>
                <span class="file-name" title="${window.escapeHtml(file.name)}">${window.escapeHtml(file.name)}</span>
                ${file.id ? `<a href="#" onclick="window.openFile('${file.id}'); return false;" class="file-link">Open File</a>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
        ` : ''}
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <button class="btn-secondary" onclick="window.closeClauseModal()">Close</button>
      </div>
    </div>
  `;

  document.body.appendChild(modalOverlay);

  // Add Enter key support for tag input
  const tagInput = document.getElementById('tagInput');
  if (tagInput) {
    tagInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        window.addTagToClause(clause.id);
      }
    });
  }

  // ESC to close
  const escHandler = (e) => {
    if (e.key === 'Escape') window.closeClauseModal();
  };
  document.addEventListener('keydown', escHandler);
  modalOverlay._escHandler = escHandler;
}


// Close clause modal
function closeClauseModal() {
  const modal = document.getElementById('clauseModal');
  if (modal) {
    if (modal._escHandler) {
      document.removeEventListener('keydown', modal._escHandler);
    }
    modal.remove();
  }
}

// Add tag to clause (reused, now modal has inline input with id="tagInput")
async function addTagToClause(clauseId) {
  const input = document.getElementById('tagInput');
  if (!input || !input.value.trim()) {
    window.showNotification('Please enter a tag name', 'error');
    return;
  }

  const userEmail =
    window.appState.userEmail || localStorage.getItem('googleUserEmail');
  if (!userEmail) {
    window.showNotification('Please login first', 'error');
    return;
  }

  try {
    const response = await fetch(
      `${window.API_BASE_URL}/clauses/library/tags/add?user_email=${encodeURIComponent(
        userEmail
      )}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clause_id: clauseId,
          tag_name: input.value.trim(),
        }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to add tag');
    }

    const data = await response.json();
    window.showNotification(data.message || 'Tag added successfully', 'success');

    // Reload clause library and refresh modal
    setTimeout(() => {
      loadClauseLibrary();
      // Re-open modal to refresh tags
      openClauseModal(clauseId);
    }, 400);
  } catch (error) {
    console.error('❌ Error adding tag:', error);
    window.showNotification(error.message, 'error');
  }
}

// Remove clause tag
async function removeClauseTag(clauseId, tagId) {
  if (!confirm('Remove this tag from the clause?')) return;

  const userEmail =
    window.appState.userEmail || localStorage.getItem('googleUserEmail');
  if (!userEmail) {
    window.showNotification('Please login first', 'error');
    return;
  }

  try {
    const response = await fetch(
      `${window.API_BASE_URL}/clauses/library/tags/remove?user_email=${encodeURIComponent(
        userEmail
      )}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clause_id: clauseId,
          tag_id: tagId,
        }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to remove tag');
    }

    const data = await response.json();
    window.showNotification(data.message || 'Tag removed', 'success');

    // Reload and refresh modal
    setTimeout(() => {
      loadClauseLibrary();
      openClauseModal(clauseId);
    }, 400);
  } catch (error) {
    console.error('❌ Error removing tag:', error);
    window.showNotification(error.message, 'error');
  }
}

// Copy clause content
function copyClauseContent(title, content) {
  const textToCopy = `${title}\n\n${content}`;
  navigator.clipboard
    .writeText(textToCopy)
    .then(() => {
      window.showNotification('Clause copied to clipboard!', 'success');
    })
    .catch((err) => {
      console.error('Failed to copy:', err);
      window.showNotification('Failed to copy to clipboard', 'error');
    });
}

// Tag filter modal (unchanged)
async function showTagFilterModal() {
  const userEmail =
    window.appState.userEmail || localStorage.getItem('googleUserEmail');
  if (!userEmail) {
    window.showNotification('Please login first', 'error');
    return;
  }

  try {
    const tagsResponse = await fetch(
      `${window.API_BASE_URL}/clauses/library/tags/all?user_email=${encodeURIComponent(
        userEmail
      )}`
    );
    let allTags = [];
    if (tagsResponse.ok) {
      const tagsData = await tagsResponse.json();
      allTags = tagsData.tags || [];
    }

    const activeTagIds = window.appState.activeTagFilters || [];

    const modalOverlay = document.createElement('div');
    modalOverlay.className = 'modal-overlay';
    modalOverlay.id = 'tagFilterModal';

    modalOverlay.innerHTML = `
      <div class="modal-container small">
        <div class="modal-header">
          <h3 class="modal-title">Filter by Tags</h3>
          <button class="modal-close-btn" onclick="this.closest('.modal-overlay').remove()">
            ×
          </button>
        </div>
        <div class="modal-body">
          <div class="modal-section">
            <div class="filter-options">
              ${
                allTags.length > 0
                  ? allTags
                      .map(
                        (tag) => `
                    <label class="filter-option">
                      <input 
                        type="checkbox" 
                        value="${tag.id}" 
                        ${activeTagIds.includes(tag.id) ? 'checked' : ''}
                        onchange="window.toggleTagFilter(${tag.id})"
                        class="filter-checkbox"
                      >
                      <span class="filter-label">${window.escapeHtml(tag.name)}</span>
                      <span class="filter-count">(${tag.usage_count || 0})</span>
                    </label>
                  `
                      )
                      .join('')
                  : '<p class="no-tags-message">No tags available</p>'
              }
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="window.clearTagFilters(); this.closest('.modal-overlay').remove()">
            Clear All
          </button>
          <button class="btn-primary" onclick="window.applyTagFilters(); this.closest('.modal-overlay').remove()">
            Apply Filters
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modalOverlay);
  } catch (error) {
    console.error('Error loading tag filters:', error);
    window.showNotification('Failed to load tags', 'error');
  }
}

// Tag filter helpers
function toggleTagFilter(tagId) {
  if (!window.appState.activeTagFilters) {
    window.appState.activeTagFilters = [];
  }

  const index = window.appState.activeTagFilters.indexOf(tagId);
  if (index === -1) {
    window.appState.activeTagFilters.push(tagId);
  } else {
    window.appState.activeTagFilters.splice(index, 1);
  }
}

function applyTagFilters() {
  loadClauseLibrary();
}

function clearTagFilters() {
  window.appState.activeTagFilters = [];
  loadClauseLibrary();
}

// Filter clauses by search
function filterClauses() {
  const searchInput = document.getElementById('clauseSearchInput');
  if (!searchInput) return;

  const query = searchInput.value.toLowerCase().trim();
  if (!query) {
    displayClauseLibrary(allClauses);
    return;
  }

  const filteredClauses = allClauses.filter((clause) => {
    const title = (clause.title || '').toLowerCase();
    const content = (clause.content_preview || '').toLowerCase();
    const sourceDoc = (clause.source_document || '').toLowerCase();
    const tags = clause.tags
      ? clause.tags.map((t) => t.name.toLowerCase()).join(' ')
      : '';

    return (
      title.includes(query) ||
      content.includes(query) ||
      sourceDoc.includes(query) ||
      tags.includes(query)
    );
  });

  displayClauseLibrary(filteredClauses);
}

// Make functions globally available
window.showClauseLibrary = showClauseLibrary;
window.loadClauseLibrary = loadClauseLibrary;
window.openClauseModal = openClauseModal;
window.closeClauseModal = closeClauseModal;
window.showTagFilterModal = showTagFilterModal;
window.toggleTagFilter = toggleTagFilter;
window.applyTagFilters = applyTagFilters;
window.clearTagFilters = clearTagFilters;
window.addTagToClause = addTagToClause;
window.removeClauseTag = removeClauseTag;
window.copyClauseContent = copyClauseContent;
window.filterClauses = filterClauses;

console.log('✅ clauses.js loaded successfully (simplified modal)!');
