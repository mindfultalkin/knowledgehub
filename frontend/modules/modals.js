// modules/modals.js - Modal Management
console.log('Loading modals.js...');

// Open document modal
async function openDocumentModal(fileId, fileName, mimeType) {
  window.currentDocumentId = fileId;
  window.currentDocumentName = fileName;

  if (window.toggleView) window.toggleView('clauses');

  const titleEl = document.getElementById('modalTitle');
  if (titleEl) {
    titleEl.textContent = fileName;
  }

  const modal = document.getElementById('documentModal');
  if (modal) {
    modal.style.display = 'flex';
  }

  const similarFilesContent = document.getElementById('similarFilesContent');
  if (similarFilesContent) {
    similarFilesContent.innerHTML = '<div class="empty-state">Select a clause to find similar files</div>';
  }

  await autoLoadCachedClauses(fileId);

  const tagsContainer = document.getElementById('tagsContainer');
  if (tagsContainer) {
    tagsContainer.innerHTML = '<div class="loading-state">Loading tags...</div>';
    const tags = await fetchDocumentTags(fileId);
    updateTagsDisplay(fileId, tags);
  }

  await loadContractRiskScore(fileId);

  const driveBtn = document.getElementById('driveBtn');
  if (driveBtn) {
    driveBtn.onclick = () =>
      window.open(`https://drive.google.com/file/d/${fileId}/view`, '_blank');
  }
}

// Close modal
function closeModal() {
  const modal = document.getElementById('documentModal');
  if (modal) modal.style.display = 'none';
  window.currentDocumentId = null;
  window.currentClauses = [];
  window.selectedClauseNumber = null;

  const clausesList = document.getElementById('clausesList');
  if (clausesList) {
    clausesList.innerHTML = '<div class="loading-state">Click "Extract Clauses" to analyze document</div>';
  }
  
  const selectedContainer = document.getElementById('selectedClauseContainer');
  if (selectedContainer) {
    selectedContainer.style.display = 'none';
  }

  const compareSection = document.getElementById('inlineCompareSection');
  if (compareSection) compareSection.remove();
}

// Auto load cached clauses
async function autoLoadCachedClauses(fileId) {
  const clausesList = document.getElementById('clausesList');
  if (!clausesList) return;
  
  clausesList.innerHTML = '<div class="loading-state">Loading clauses...</div>';
  
  try {
    const response = await fetch(`${window.API_BASE_URL}/documents/${fileId}/cached-clauses`);
    
    if (response.ok) {
      const data = await response.json();
      
      if (data.clauses && data.clauses.length > 0) {
        console.log(`Found ${data.clauses.length} cached clauses`);
        window.currentClauses = data.clauses;
        displayClausesList(window.currentClauses);
        return;
      }
    }
    
    clausesList.innerHTML = `
        <div class="empty-state">
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">No clauses extracted yet</p>
            <button onclick="window.extractClausesNow()" class="btn-primary" style="padding: 0.75rem 1.5rem; font-size: 0.9rem;">
                Extract Clauses Now
            </button>
        </div>
    `;
    
  } catch (error) {
    console.error('Error loading cached clauses:', error);
    clausesList.innerHTML = `
        <div class="empty-state">
            <p style="color: red; margin-bottom: 1rem;">Error loading clauses</p>
            <button onclick="window.extractClausesNow()" class="btn-primary">
                Extract Clauses
            </button>
        </div>
    `;
  }
}

// Extract clauses
async function extractClausesNow() {
  const clausesList = document.getElementById('clausesList');
  if (!clausesList) return;
  
  clausesList.innerHTML = '<div class="loading-state">Extracting clauses... This may take 10-30 seconds...</div>';
  
  try {
    const response = await fetch(`${window.API_BASE_URL}/documents/${window.currentDocumentId}/extract-clauses`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to extract clauses');
    }
    
    console.log(`Extracted ${data.clauses.length} clauses`);
    window.currentClauses = data.clauses;
    displayClausesList(window.currentClauses);
    
    window.showNotification(`Successfully extracted ${data.clauses.length} clauses!`, 'success');
    
  } catch (error) {
    console.error('Error extracting clauses:', error);
    clausesList.innerHTML = `
        <div class="empty-state" style="color: red;">
            <p style="margin-bottom: 1rem;">Failed to extract clauses</p>
            <p style="font-size: 0.85rem; margin-bottom: 1rem;">${error.message}</p>
            <button onclick="window.extractClausesNow()" class="btn-primary">
                Try Again
            </button>
        </div>
    `;
  }
}

// Display clauses list
function displayClausesList(clauses) {
  const container = document.getElementById('clausesList');
  if (!container) return;
  
  if (!clauses || clauses.length === 0) {
    container.innerHTML = '<div class="empty-state">No clauses found in this document</div>';
    return;
  }
  
  container.innerHTML = `
  <div style="display:flex;justify-content:flex-end;margin-bottom:10px;">
    <button class="btn-secondary" style="font-size:0.85rem;padding:6px 10px;"
      onclick="window.refetchClausesNow()" title="Re-extract clauses"
    >
      ⟳ Refetch
    </button>
  </div>
` + clauses.map(clause => `
      <div class="clause-item" onclick="window.selectClause(${clause.clause_number})" data-clause="${clause.clause_number}">
          <div class="clause-item-number">${clause.section_number || clause.clause_number}</div>
          <div class="clause-item-title">${clause.clause_title || clause.title}</div>
      </div>
  `).join('');
}

//Refetch Clauses List
async function refetchClausesNow() {
  const clausesList = document.getElementById('clausesList');
  if (!clausesList) return;

  if (!confirm('This will re-extract clauses again. Continue?')) return;

  clausesList.innerHTML =
    '<div class="loading-state">Re-extracting clauses... Please wait...</div>';

  try {
    const response = await fetch(
      `${window.API_BASE_URL}/documents/${window.currentDocumentId}/refetch-clauses`,
      { method: 'POST' }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to re-extract clauses');
    }

    window.currentClauses = data.clauses || [];
    displayClausesList(window.currentClauses);

    window.showNotification(
      `Re-extracted ${data.count} clauses successfully`,
      'success'
    );
  } catch (error) {
    console.error('Refetch error:', error);
    clausesList.innerHTML = `
      <div class="empty-state" style="color:red;">
        <p>Failed to re-extract clauses</p>
        <p style="font-size:0.85rem;">${error.message}</p>
        <button onclick="window.refetchClausesNow()" class="btn-primary">
          Try Again
        </button>
      </div>
    `;
  }
}


// Select clause
async function selectClause(clauseNumber) {
  window.selectedClauseNumber = clauseNumber;
  
  document.querySelectorAll('.clause-item').forEach(item => {
    item.classList.remove('active');
  });
  const selectedItem = document.querySelector(`.clause-item[data-clause="${clauseNumber}"]`);
  if (selectedItem) {
    selectedItem.classList.add('active');
  }
  
  const clause = window.currentClauses.find(c => c.clause_number === clauseNumber);
  
  if (!clause) {
    console.error('Clause not found:', clauseNumber);
    return;
  }
  
  console.log('Selected clause:', clause);
  
  displaySelectedClause(clause);
  
  await findSimilarFiles(clause.title); 
  
  window.selectedClauseData = {
    file_title: window.currentDocumentName,
    clause_title: clause.title || clause.clause_title,
    clause_content: clause.content || clause.clause_content
  };
  window.selectedSimilarFileId = null;
  window.selectedSimilarClauseData = null;
}

// Display selected clause
async function displaySelectedClause(clause) {
  const container = document.getElementById('selectedClauseContainer');
  const titleEl = document.getElementById('selectedClauseTitle');
  const contentEl = document.getElementById('selectedClauseContent');
  
  if (!container || !titleEl || !contentEl) return;
  
  console.log('Displaying clause:', clause);
  
  container.style.display = 'block';
  
  const clauseNumber = clause.section_number || clause.clause_number || '';
  const clauseTitle = clause.title || clause.clause_title || 'Untitled Clause';
  const clauseContent = clause.content || clause.clause_content || 'No content available';
  
  titleEl.textContent = `${clauseNumber}. ${clauseTitle}`;
  contentEl.textContent = clauseContent;
  
  const saveBtn = document.getElementById('saveToLibraryBtn');
  if (saveBtn) {
    saveBtn.textContent = 'Checking...';
    saveBtn.disabled = true;
    
    try {
      const response = await fetch(
        `${window.API_BASE_URL}/clauses/check-saved/${window.currentDocumentId}/${clause.clause_number}`
      );
      const data = await response.json();
      
      if (data.saved) {
        saveBtn.textContent = 'Saved to Library';
        saveBtn.classList.add('saved');
        saveBtn.disabled = true;
      } else {
        saveBtn.textContent = 'Save to Library';
        saveBtn.classList.remove('saved');
        saveBtn.disabled = false;
      }
    } catch (error) {
      console.error('Error checking saved status:', error);
      saveBtn.textContent = 'Save to Library';
      saveBtn.classList.remove('saved');
      saveBtn.disabled = false;
    }
  }
}

async function saveClauseToLibrary() {
  if (!window.currentDocumentId || window.selectedClauseNumber === null) {
    alert('No clause selected');
    return;
  }

  const saveBtn = document.getElementById('saveToLibraryBtn');
  if (!saveBtn) return;

  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';

  try {
    // Try to get user email from multiple sources
    let userEmail = window.userEmail || 
                   localStorage.getItem('user_email') || 
                   window.appState.userEmail || 
                   window.appState.user?.email;

    if (!userEmail) {
      // Fallback: fetch from API
      const response = await fetch(`${window.API_BASE_URL}/auth/account-info`);
      const data = await response.json();
      if (data.authenticated && data.email) {
        userEmail = data.email;
        window.appState.userEmail = userEmail;
        localStorage.setItem('user_email', userEmail);
      }
    }

    if (!userEmail) {
      alert('User email is required');
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save to Library';
      return;
    }

    // Send user_email as query parameter
    const url = `${window.API_BASE_URL}/clauses/save-to-library?user_email=${encodeURIComponent(userEmail)}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        document_id: window.currentDocumentId,
        clause_number: window.selectedClauseNumber
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to save clause');
    }

    saveBtn.textContent = 'Saved to Library';
    saveBtn.classList.add('saved');
    saveBtn.disabled = true;

    const message = data.already_saved 
      ? 'Clause was already in library' 
      : 'Clause saved to library successfully!';
    window.showNotification(message, 'success');

  } catch (error) {
    console.error('Error saving clause:', error);
    alert('Failed to save clause: ' + error.message);
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save to Library';
    saveBtn.classList.remove('saved');
  }
}


// Find similar files
async function findSimilarFiles(clauseTitle) {
  const container = document.getElementById('similarFilesContent');
  if (!container) return;
  
  container.innerHTML = '<div class="loading-state">Searching for similar files...</div>';
  
  console.log('Finding similar files for clause:', clauseTitle);
  
  try {
    const response = await fetch(
      `${window.API_BASE_URL}/clauses/${encodeURIComponent(clauseTitle)}/similar-files?current_file_id=${window.currentDocumentId}`
    );
    
    const data = await response.json();
    
    console.log('Similar files response:', data);
    
    if (!data.found || data.count === 0) {
      container.innerHTML = '<div class="empty-state">No other files found with this clause</div>';
      return;
    }
    
    container.innerHTML = data.files.map(file => `
        <div class="similar-file-item" style="display:flex;align-items:center;gap:10px;">
            <input type="radio" name="compare-similar"
                value="${file.file_id || file.id}"
                data-title="${window.escapeHtml(file.clause_title)}"
                data-content="${window.escapeHtml(file.clause_content)}"
                data-source="${window.escapeHtml(file.file_name)}"
                onchange="window.onSelectSimilarClause('${file.file_id || file.id}')"
                ${window.selectedSimilarFileId === (file.file_id || file.id) ? 'checked' : ''}>
            <div class="similar-file-info" style="flex:1;">
                <div class="file-title">${window.escapeHtml(file.file_name)}</div>
                <div class="file-meta-small">${window.escapeHtml(file.section_number)}. ${window.escapeHtml(file.clause_title)}</div>
                <span class="match-badge ${file.match_type}">${file.match_type ? file.match_type.toUpperCase() : ''}</span>
            </div>
        </div>
    `).join('') +
    `<div style="margin-top:16px;">
        <button id="compareBtn" class="btn-primary" style="width:100%;" disabled>
            Compare With Selected
        </button>
    </div>`;
    
    const compareBtn = document.getElementById('compareBtn');
    if (compareBtn) {
      compareBtn.onclick = function() {
        if (!window.selectedSimilarClauseData || !window.selectedClauseData) return;
        window.showInlineComparison(window.selectedClauseData, window.selectedSimilarClauseData);
      };
    }
    
    console.log(`Displayed ${data.count} similar files`);
    
  } catch (error) {
    console.error('Error finding similar files:', error);
    container.innerHTML = '<div class="empty-state">Error loading similar files</div>';
  }
}

// On select similar clause
function onSelectSimilarClause(fileId) {
  window.selectedSimilarFileId = fileId;
  const radio = document.querySelector(`input[name='compare-similar'][value="${fileId}"]`);
  if (radio) {
    window.selectedSimilarClauseData = {
      file_id: fileId,
      clause_title: radio.dataset.title,
      clause_content: radio.dataset.content,
      file_title: radio.dataset.source
    };
    const compareBtn = document.getElementById('compareBtn');
    if (compareBtn) {
      compareBtn.disabled = false;
    }
  }
  document.querySelectorAll("input[name='compare-similar']").forEach(r => {
    if (r.value !== fileId) r.checked = false;
  });
}

// Show inline comparison
function showInlineComparison(mainClause, similarClause) {
  let existing = document.getElementById('inlineCompareSection');
  if (existing) existing.remove();
  
  const html = `
    <div id="inlineCompareSection" style="margin-top: 32px; border-top: 2px solid #ececf0; border-radius: 10px; background: #f9fcff; padding: 2.3rem 1.2rem 2.5rem 1.2rem; box-shadow:0 2px 22px 0 rgba(22,33,77,.09);">
      <h3 style="margin-bottom:2.2rem; font-size:1.22rem; letter-spacing:-0.5px; font-weight:800; color:#26327e;">
        <span style="vertical-align:-2px; margin-right:8px;">
          <svg width="22" height="22" fill="#5c64d6"><rect width="22" height="22" rx="6" fill="#e9ebfa"/><path d="M6 6h10v2H6V6zm0 4h10v6H6v-6zm2 2v2h6v-2H8z" fill="#555ab8"/></svg>
        </span>
        Clause Comparison Result
      </h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:40px;">
        <div style="background:#fff;border:2px solid #4b72e0;border-radius:9px;padding:1.3rem 1.5rem;">
          <div style="font-size:1.01rem; font-weight:700; color:#356bc9;margin-bottom:5px;">
            <span style="vertical-align:-4px;"></span> ${window.escapeHtml(mainClause.file_title)}
          </div>
          <div class="clause-title" style="font-size:1.09rem;color:#181845;font-weight:700;margin-bottom:10px;">${window.escapeHtml(mainClause.clause_title)}</div>
          <hr style="border: none; border-top: 1px solid #e6e7ea; margin:12px 0;">
          <div class="clause-content-diff" style="background:#eaf5fc;padding:17px 17px 14px;border-radius:7px;white-space:pre-line;min-height:65px;">
            ${mainClause.clause_content ? window.highlightDiff(mainClause.clause_content, similarClause.clause_content, 'left') : '<em>No content found.</em>'}
          </div>
        </div>
        <div style="background:#fff;border:2px solid #28b7a5;border-radius:9px;padding:1.3rem 1.5rem;">
          <div style="font-size:1.01rem; font-weight:700; color:#179076;margin-bottom:5px;">
            <span style="vertical-align:-4px;"></span> ${window.escapeHtml(similarClause.file_title)}
          </div>
          <div class="clause-title" style="font-size:1.09rem;color:#181845;font-weight:700;margin-bottom:10px;">${window.escapeHtml(similarClause.clause_title)}</div>
          <hr style="border: none; border-top: 1px solid #e6e7ea; margin:12px 0;">
          <div class="clause-content-diff" style="background:#eafaf2;padding:17px 17px 14px;border-radius:7px;white-space:pre-line;min-height:65px;">
            ${similarClause.clause_content ? window.highlightDiff(similarClause.clause_content, mainClause.clause_content, 'right') : '<em>No content found.</em>'}
          </div>
        </div>
      </div>
      <div style="text-align:center;margin-top:32px;">
        <button onclick="window.clearInlineComparison()" class="btn-primary" style="background:#ff4040;border:none;">Remove Comparison</button>
      </div>
    </div>
  `;

  const modalContent = document.querySelector('.modal-content');
  const threeColumnLayout = document.querySelector('.three-column-layout');
  
  if (modalContent && threeColumnLayout) {
    threeColumnLayout.insertAdjacentHTML('afterend', html);
    
    setTimeout(() => {
      const comparisonSection = document.getElementById('inlineCompareSection');
      if (comparisonSection) {
        comparisonSection.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'start'
        });
      }
    }, 100);
  }
}

// Clear inline comparison
function clearInlineComparison() {
  let section = document.getElementById('inlineCompareSection');
  if (section) {
    section.remove();
  }
  
  document.querySelectorAll("input[name='compare-similar']").forEach(radio => {
    radio.checked = false;
  });
  
  const compareBtn = document.getElementById('compareBtn');
  if (compareBtn) {
    compareBtn.disabled = true;
  }
  
  window.selectedSimilarFileId = null;
  window.selectedSimilarClauseData = null;
}

// Load contract risk score
async function loadContractRiskScore(fileId) {
  try {
    const response = await fetch(`${window.API_BASE_URL}/contracts/${fileId}/risk-score`);
    if (!response.ok) {
      window.showNotification('Could not load risk score', 'warning');
      return;
    }
    const riskData = await response.json();
    displayRiskScoreCard(riskData);
    displayRiskBreakdown(riskData);
  } catch (error) {
    window.showNotification('Error loading risk score', 'error');
    console.error(error);
  }
}

// Display risk score card
function displayRiskScoreCard(riskData) {
  const scoreEl = document.getElementById('riskScoreNumber');
  const levelEl = document.getElementById('riskScoreLevel');
  const cardEl = document.querySelector('.risk-score-card');
  if (!scoreEl || !levelEl || !cardEl) return;

  const score = riskData.risk_score || 0;
  const level = riskData.risk_level || 'UNKNOWN';
  scoreEl.textContent = score;

  let indicator = '';
  if (level === 'LOW') indicator = 'LOW';
  else if (level === 'MEDIUM') indicator = 'MEDIUM';

  levelEl.textContent = `${indicator} ${level}`;
  cardEl.classList.remove('medium-risk', 'high-risk');
  if (level === 'MEDIUM') cardEl.classList.add('medium-risk');
  else if (level === 'HIGH') cardEl.classList.add('high-risk');
}

// Display risk breakdown
function displayRiskBreakdown(riskData) {
  const goodList = document.getElementById('goodClausesList');
  const cautionList = document.getElementById('cautionClausesList');
  const missingList = document.getElementById('missingClausesList');
  if (goodList) {
    goodList.innerHTML = Array.isArray(riskData.good_clauses) && riskData.good_clauses.length
      ? riskData.good_clauses.map(clause => `<li>FOUND: ${clause}</li>`).join('')
      : '<li style="color: #999;">No favorable clauses detected</li>';
  }
  if (cautionList) {
    cautionList.innerHTML = Array.isArray(riskData.caution_clauses) && riskData.caution_clauses.length
      ? riskData.caution_clauses.map(clause => `<li>CAUTION: ${clause}</li>`).join('')
      : '<li style="color: #999;">No caution items detected</li>';
  }
  if (missingList) {
    missingList.innerHTML = Array.isArray(riskData.missing_clauses) && riskData.missing_clauses.length
      ? riskData.missing_clauses.map(clause => `<li>MISSING: ${clause}</li>`).join('')
      : '<li style="color: #999;">No missing clauses detected</li>';
  }
}

// Toggle view
function toggleView(viewType) {
  const clausesView = document.getElementById('clausesView');
  const riskView = document.getElementById('riskView');
  const showClausesBtn = document.getElementById('showClausesBtn');
  const showRiskBtn = document.getElementById('showRiskBtn');
  if (viewType === 'clauses') {
    if (clausesView) clausesView.style.display = 'block';
    if (clausesView) clausesView.classList.add('active');
    if (riskView) riskView.style.display = 'none';
    if (riskView) riskView.classList.remove('active');
    if (showClausesBtn) showClausesBtn.classList.add('active');
    if (showRiskBtn) showRiskBtn.classList.remove('active');
  } else {
    if (riskView) riskView.style.display = 'block';
    if (riskView) riskView.classList.add('active');
    if (clausesView) clausesView.style.display = 'none';
    if (clausesView) clausesView.classList.remove('active');
    if (showRiskBtn) showRiskBtn.classList.add('active');
    if (showClausesBtn) showClausesBtn.classList.remove('active');
  }
}

// Tag management
async function fetchDocumentTags(documentId) {
  console.log(`Fetching tags for document ID: ${documentId}`);
  
  try {
    const res = await fetch(`${window.API_BASE_URL}/documents/${documentId}/tags`);
    
    if (!res.ok) {
      throw new Error(`API failed (${res.status}): ${res.statusText}`);
    }
    
    const data = await res.json();
    console.log(`✅ Tags loaded successfully:`, data.tags || []);
    
    return data.tags || [];
    
  } catch (error) {
    console.error('❌ Error fetching tags:', error);
    
    // Graceful fallback: use file data if available
    const file = window.appState?.files?.find(f => f.id === documentId);
    if (file?.aiTags?.length > 0) {
      console.log(`🔄 Using cached aiTags from file:`, file.aiTags);
      return file.aiTags;
    }
    
    window.showNotification('Could not load tags (using cached data)', 'warning');
    return [];
  }
}

async function removeTag(documentId, tag) {
  if (!confirm(`Remove tag "${tag}"?`)) return;

  try {
    const res = await fetch(`${window.API_BASE_URL}/documents/${documentId}/tags/remove`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag }),
    });
    
    if (!res.ok) throw new Error('Failed to remove tag');
    
    const data = await res.json();
    console.log('✅ Tag removed:', data);
    
    // ✅ Update modal tags display
    window.updateTagsDisplay(documentId, data.tags || []);
    window.showNotification(`Tag "${tag}" removed`, 'success');
    
    // ✅ CRITICAL: Refresh the file list to update file cards
    console.log('🔄 Refreshing file list...');
    if (window.refreshFiles) {
      await window.refreshFiles();
    }
    
    // ✅ Update the specific file in appState
    const fileIndex = window.appState.files.findIndex(f => f.id === documentId);
    if (fileIndex !== -1) {
      window.appState.files[fileIndex].aiTags = data.tags || [];
      window.appState.files[fileIndex].tagCount = (data.tags || []).length;
      console.log('✅ Updated file in appState:', window.appState.files[fileIndex]);
    }
  } catch (e) {
    console.error('Remove tag error', e);
    window.showNotification('Failed to remove tag', 'error');
  }
}


function updateTagsDisplay(documentId, tags) {
  const tagsContainer = document.getElementById('tagsContainer');
  if (!tagsContainer) return;

  const safeTags = Array.isArray(tags) ? tags : [];

  if (!safeTags.length) {
    tagsContainer.innerHTML = `
      <div class="tags-content">
        <em style="color:var(--text-secondary);font-size:0.85rem;">No tags yet</em>
        ${window.IS_ADMIN ? `
        <button
          type="button"
          onclick="window.addTag('${documentId}')"
          class="btn-secondary"
          style="margin-top:12px;width:100%;text-align:center;"
        >
          Add Tag
        </button>
        ` : ''}
      </div>
    `;
    return;
  }

  tagsContainer.innerHTML = `
    <div class="tags-content">
      ${safeTags.map(tag => `
        <span class="tag">
          ${tag}
          ${window.IS_ADMIN ? `
          <button
            type="button"
            onclick="window.removeTag('${documentId}', '${tag.replace(/'/g, "\\'")}')"
            style="
              background:none;
              border:none;
              color:#fff;
              cursor:pointer;
              margin-left:6px;
              font-weight:bold;
              font-size:0.95rem;
            "
          >×</button>
          ` : ''}
        </span>
      `).join('')}
      ${window.IS_ADMIN ? `
      <button
        type="button"
        onclick="window.addTag('${documentId}')"
        class="btn-secondary"
        style="margin-top:12px;width:100%;text-align:center;"
      >
        Add Tag
      </button>
      ` : ''}
    </div>
  `;
}

// Note modal functions
function openNoteModal() {
  console.log('openNoteModal called');

  const existing = document.getElementById('noteModal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.id = 'noteModal';

  modal.innerHTML = `
    <div class="modal-overlay" onclick="window.closeNoteModal()"></div>
    <div class="modal-content" style="max-width:600px;">
      <div class="modal-header">
        <h2>Add Note</h2>
        <button class="close-btn" onclick="window.closeNoteModal()">×</button>
      </div>
      <div class="modal-body">
        <label>Title</label>
        <input id="noteTitle" class="input" placeholder="Enter note title" />

        <label style="margin-top:1rem;">Content</label>
        <textarea id="noteContent" class="textarea" rows="8"
          placeholder="Type your note here..."></textarea>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="window.closeNoteModal()">Cancel</button>
        <button class="btn-primary" onclick="window.saveNote()">Save Note</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);
}

function closeNoteModal() {
  const modal = document.getElementById('noteModal');
  if (modal) modal.remove();
}

async function saveNote() {
  const title = (document.getElementById('noteTitle')?.value || '').trim();
  const content = document.getElementById('noteContent')?.value || '';

  if (!title) {
    window.showNotification('Title is required', 'error');
    return;
  }

  try {
    window.showNotification('Creating note...', 'info');

    const res = await fetch(`${window.API_BASE_URL}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content }),
    });

    if (!res.ok) throw new Error(`Failed (${res.status})`);
    await res.json();

    window.showNotification('Note created', 'success');
    window.closeNoteModal();
    if (window.refreshFiles) {
      await window.refreshFiles();
    }
  } catch (e) {
    console.error('Create note error', e);
    window.showNotification('Failed to create note', 'error');
  }
}

// Add this BEFORE the window. exports at the bottom
window.addTag = async function(documentId) {
  const tagName = prompt('Enter tag name (must exist in master list):');
  if (!tagName?.trim()) return;
  
  try {
    const response = await fetch(`${window.API_BASE_URL}/documents/${documentId}/tags/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag: tagName.trim() })
    });
    
    if (response.ok) {
      const data = await response.json();
      window.updateTagsDisplay(documentId, data.tags || []);
      window.showNotification(`Added: ${tagName}`, 'success');
      
      // ✅ CRITICAL: Refresh file list to show tag in card
      if (window.refreshFiles) {
        setTimeout(() => window.refreshFiles(), 500);  // Small delay for DB sync
      }
    } else {
      window.showNotification('Tag not in master list', 'error');
    }
  } catch (error) {
    console.error('Add tag failed:', error);
    window.showNotification('Failed to add tag', 'error');
  }
};
window.removeTag = async function(documentId, tag) {
  if (!confirm(`Remove tag "${tag}"?`)) return;

  try {
    const res = await fetch(`${window.API_BASE_URL}/documents/${documentId}/tags/remove`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag }),
    });
    
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Failed to remove tag');
    }
    
    const data = await res.json();
    window.updateTagsDisplay(documentId, data.tags || []);
    window.showNotification(`Tag "${tag}" removed`, 'success');
    
    // ✅ CRITICAL: Refresh file list to update tag count/badges in file row
    if (window.refreshFiles) {
      setTimeout(() => window.refreshFiles(), 500);  // Small delay for DB sync
    }
    
  } catch (e) {
    console.error('Remove tag error:', e);
    window.showNotification(`Failed to remove tag: ${e.message}`, 'error');
  }
};



// Make functions globally available
window.openDocumentModal = openDocumentModal;
window.closeModal = closeModal;
window.autoLoadCachedClauses = autoLoadCachedClauses;
window.extractClausesNow = extractClausesNow;
window.refetchClausesNow = refetchClausesNow;
window.displayClausesList = displayClausesList;
window.selectClause = selectClause;
window.displaySelectedClause = displaySelectedClause;
window.saveClauseToLibrary = saveClauseToLibrary;
window.findSimilarFiles = findSimilarFiles;
window.onSelectSimilarClause = onSelectSimilarClause;
window.showInlineComparison = showInlineComparison;
window.clearInlineComparison = clearInlineComparison;
window.loadContractRiskScore = loadContractRiskScore;
window.displayRiskScoreCard = displayRiskScoreCard;
window.displayRiskBreakdown = displayRiskBreakdown;
window.toggleView = toggleView;
window.fetchDocumentTags = fetchDocumentTags;
window.addTag = addTag;
window.removeTag = removeTag;
window.updateTagsDisplay = updateTagsDisplay;
window.openNoteModal = openNoteModal;
window.closeNoteModal = closeNoteModal;
window.saveNote = saveNote;