// state.js - Application State Management
console.log('Loading state.js...');

// Main application state
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
  filesPerPage: parseInt(localStorage.getItem('filesPerPage')) || 96,
  nlpSearchResults: [],
  nlpSearchQuery: '',
  nlpSearchLoading: false,
  searchType: 'simple',
  searchResults: []
};

// Global comparison state
let selectedSimilarFileId = null;
let selectedSimilarClauseData = null;
window.selectedClauseData = null;

// Document modal state
let currentDocumentId = null;
let currentDocumentName = null;
let currentClauses = [];
let selectedClauseNumber = null;

// Make everything globally accessible
window.appState = appState;
window.selectedSimilarFileId = selectedSimilarFileId;
window.selectedSimilarClauseData = selectedSimilarClauseData;
window.currentDocumentId = currentDocumentId;
window.currentDocumentName = currentDocumentName;
window.currentClauses = currentClauses;
window.selectedClauseNumber = selectedClauseNumber;