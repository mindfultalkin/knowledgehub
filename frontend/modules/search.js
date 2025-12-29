// modules/search.js - Search Functionality
console.log('Loading search.js...');

// Train NLP model
async function trainNLPModel() {
  try {
    window.showNotification('🤖 Training NLP model on your documents...', 'info');
    
    const response = await fetch(`${window.API_BASE_URL}/nlp/train`, {
      method: 'POST'
    });
    
    const data = await response.json();
    
    if (response.ok) {
      window.showNotification(`✅ ${data.message} (${data.documents_processed || data.total_files || 0} documents)`, 'success');
    } else {
      throw new Error(data.detail || 'Training failed');
    }
    
  } catch (error) {
    console.error('Training failed:', error);
    window.showNotification(`❌ NLP training failed: ${error.message}`, 'error');
  }
}

// Set search type
function setSearchType(type) {
  window.appState.searchType = type;
  if (window.appState.searchQuery) {
    performSearch();
  }
  if (window.renderCurrentView) window.renderCurrentView();
}

// Main search function
async function performSearch() {
  const query = window.appState.searchQuery.trim();
  if (!query) return;
  
  window.appState.loading = true;
  if (window.renderCurrentView) window.renderCurrentView();
  
  try {
    const endpoint = window.appState.searchType === 'simple' ? 
      `${window.API_BASE_URL}/search/simple` : 
      `${window.API_BASE_URL}/search/ai`;
    
    console.log(`🔍 Calling: ${endpoint}?query=${encodeURIComponent(query)}`);
    
    const response = await fetch(`${endpoint}?query=${encodeURIComponent(query)}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Server error:', errorText);
      throw new Error(`Search failed: ${response.status}`);
    }
    
    const data = await response.json();
    window.appState.searchResults = data.results || [];
    window.appState.loading = false;
    
    const message = window.appState.searchType === 'simple' 
      ? `✅ Found ${data.total_results || window.appState.searchResults.length} documents containing "${query}"`
      : `🤖 Found ${data.total_results || window.appState.searchResults.length} semantically similar documents`;
    
    window.showNotification(message, 'success');
    if (window.renderCurrentView) window.renderCurrentView();
    
  } catch (error) {
    console.error('Search failed:', error);
    window.appState.loading = false;
    window.showNotification(`❌ Search failed: ${error.message}`, 'error');
  }
}

// AI search with specific query
function searchWithAI(query) {
  window.appState.searchQuery = query;
  window.appState.searchType = 'ai';
  console.log(`🤖 Setting AI search for: "${query}"`);
  performSearch();
}

// Handle search input
function handleSearch(event) {
  const input = event.target;
  const cursorPosition = input.selectionStart;
  
  window.appState.searchQuery = input.value.toLowerCase();
  filterFiles();
  
  setTimeout(() => {
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
      searchInput.value = input.value;
      searchInput.setSelectionRange(cursorPosition, cursorPosition);
      searchInput.focus();
    }
  }, 0);
}

// Filter files
function filterFiles() {
  let filtered = [...window.appState.files];
  
  if (window.appState.searchQuery) {
    filtered = filtered.filter(file => 
      file.name.toLowerCase().includes(window.appState.searchQuery) ||
      file.owner.toLowerCase().includes(window.appState.searchQuery) ||
      (file.aiTags || []).some(tag => tag.toLowerCase().includes(window.appState.searchQuery))
    );
  }
  
  if (window.appState.selectedFileType !== 'all') {
    filtered = filtered.filter(file => file.type === window.appState.selectedFileType);
  }
  
  filtered.sort((a, b) => {
    if (window.appState.sortBy === 'name') {
      return a.name.localeCompare(b.name);
    } else if (window.appState.sortBy === 'size') {
      return (parseInt(b.size) || 0) - (parseInt(a.size) || 0);
    } else {
      return new Date(b.modifiedTime) - new Date(a.modifiedTime);
    }
  });
  
  window.appState.filteredFiles = filtered;
  if (window.renderCurrentView) window.renderCurrentView();
}

// Search by tag
function searchByTag(tag) {
  window.appState.currentView = 'search';
  window.appState.searchQuery = tag;
  filterFiles();
  if (window.navigateTo) window.navigateTo('search');
}

// Make functions globally available
window.trainNLPModel = trainNLPModel;
window.setSearchType = setSearchType;
window.performSearch = performSearch;
window.searchWithAI = searchWithAI;
window.handleSearch = handleSearch;
window.filterFiles = filterFiles;
window.searchByTag = searchByTag;