// modules/ui.js - CLEAN VERSION (No extra buttons)
console.log('Loading ui.js...');

// ORIGINAL File card renderer - NO Edit Metadata or View buttons
function renderFileCard(file) {
  const icon = `<div style="font-size:3.5rem;">${window.getFileIcon(file.mimeType, file.name)}</div>`;
  const allTags = file.aiTags || [];
  const tagCount = file.tagCount || allTags.length;
  
  // Show first 3 tags + count if more
  const tagPreview = allTags.length > 0 ? 
    allTags.slice(0, 3).map(tag => `<span class="tag">${tag}</span>`).join('') +
    (tagCount > 3 ? ` <span class="tag-count">+${tagCount-3}</span>` : '') 
    : '<span class="no-tags">No tags</span>';

  return `
    <div class="file-card" 
         data-file-id="${file.id}" 
         data-file-name="${window.escapeHtml(file.name)}" 
         data-file-type="${file.mimeType || file.type}">
      <div class="file-thumbnail">${icon}</div>
      <div class="file-info">
        <div class="file-name" title="${file.name}">${window.escapeHtml(file.name)}</div>
        <div class="file-meta">
          <span>Owner: ${file.owner}</span>
          <span>Date: ${window.formatDate(file.modifiedTime)}</span>
          <span>Size: ${window.formatFileSize(file.size)}</span>
        </div>
        <div class="file-tags">
          ${tagPreview}
        </div>
        ${tagCount > 0 ? `<div class="tag-badge">${tagCount} tag${tagCount > 1 ? 's' : ''}</div>` : ''}
      </div>
    </div>
  `;
}

// FIXED VERSION of attachFileCardListeners()
function attachFileCardListeners() {
  // Grid cards
  document.querySelectorAll('.file-card').forEach(card => {
    card.style.cursor = 'pointer';
    card.addEventListener('click', function(e) {
      // Prevent clicks on child elements (like tags)
      if (e.target.closest('.tag, .tag-badge, .file-tags')) {
        return;
      }
      
      const fileId = this.dataset.fileId;
      const fileName = this.dataset.fileName;
      const fileType = this.dataset.fileType;
      
      if (fileId && fileName && window.openDocumentModal) {
        // ✅ FIXED: Pass all 3 parameters correctly
        window.openDocumentModal(fileId, fileName, fileType);
      } else {
        console.error('Missing file data:', { fileId, fileName, fileType });
      }
    });
  });
  
  // List rows - FIXED VERSION
  document.querySelectorAll('.file-list-row').forEach(row => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', function(e) {
      // Prevent clicks on child elements
      if (e.target.closest('.tag, .tag-count, .tags-cell')) {
        return;
      }
      
      const fileId = this.dataset.fileId;
      
      // Get file object from appState
      let file;
      if (window.currentView === 'templates') {
        file = window.appState.templates?.find(t => t.id === fileId);
      } else {
        file = window.appState.files.find(f => f.id === fileId);
      }
      
      if (file && window.openDocumentModal) {
        // ✅ FIXED: Pass the file object's data
        window.openDocumentModal(file.id, file.name, file.mimeType || file.type);
      }
    });
  });
  
  // Hover effects
  document.querySelectorAll('.file-card, .file-list-row').forEach(el => {
    el.addEventListener('mouseenter', () => el.style.transform = 'translateY(-2px)');
    el.addEventListener('mouseleave', () => el.style.transform = 'none');
  });
}

// Simple search result renderer
function renderSimpleSearchResult(file) {
  const icon = `<div style="font-size:3.5rem;">${window.getFileIcon(file.mimeType, file.name)}</div>`;
  
  return `
    <div class="file-card" onclick='window.viewFile(${JSON.stringify(file).replace(/'/g, "&apos;")})'>
      <div class="file-thumbnail">
        ${icon}
        <div style="position: absolute; top: 8px; right: 8px; background: #4caf50; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.7rem;">
          Exact Match
        </div>
      </div>
      <div class="file-info">
        <div class="file-name" title="${file.name}">${file.name}</div>
        <div class="file-meta">
          <span>Owner: ${file.owner}</span>
          <span>Date: ${window.formatDate(file.modifiedTime)}</span>
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

// AI search result renderer
function renderAISearchResult(file) {
  const icon = `<div style="font-size:3.5rem;">${window.getFileIcon(file.mimeType, file.name)}</div>`;
  const relevanceColor = window.getRelevanceColor(file.relevance);
  
  return `
    <div class="file-card" onclick='window.viewFile(${JSON.stringify(file).replace(/'/g, "&apos;")})'>
      <div class="file-thumbnail" style="position: relative;">
        ${icon}
        <div style="position: absolute; top: 8px; right: 8px; background: ${relevanceColor}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 600;">
          ${file.relevance}
        </div>
      </div>
      <div class="file-info">
        <div class="file-name" title="${file.name}">${file.name}</div>
        <div class="file-meta">
          <span>Owner: ${file.owner}</span>
          <span>Date: ${window.formatDate(file.modifiedTime)}</span>
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

// View file (ORIGINAL)
function viewFile(file) {
  const fileUrl = file.file_url || file.webViewLink || file.fileUrl;
  
  if (fileUrl) {
    window.open(fileUrl, '_blank');
    window.showNotification(`Opening ${file.title || file.name}...`, 'info');
  } else {
    window.showNotification('File URL not available', 'error');
  }
}

// Update navigation
function updateNavigation(view) {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.remove('active');
  });
  
  const activeLink = document.querySelector(`.nav-link[data-view="${view}"]`);
  if (activeLink) {
    activeLink.classList.add('active');
  }
}

// Navigate to view
function navigateTo(view) {
  window.appState.currentView = view;
  updateNavigation(view);
  if (window.renderCurrentView) window.renderCurrentView();
}

// Make functions globally available (NO metadata functions)
window.renderFileCard = renderFileCard;
window.attachFileCardListeners = attachFileCardListeners;
window.renderSimpleSearchResult = renderSimpleSearchResult;
window.renderAISearchResult = renderAISearchResult;
window.viewFile = viewFile;
window.updateNavigation = updateNavigation;
window.navigateTo = navigateTo;