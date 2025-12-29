// modules/utils.js - Utility Functions
console.log('Loading utils.js...');

// Apply theme on load
document.documentElement.setAttribute('data-theme', window.appState.theme);

// Format date
function formatDate(dateString) {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
}

// Format file size
function formatFileSize(bytes) {
  if (!bytes || bytes === '0') return 'N/A';
  const numBytes = parseInt(bytes);
  if (numBytes < 1024) return numBytes + ' B';
  if (numBytes < 1024 * 1024) return (numBytes / 1024).toFixed(1) + ' KB';
  if (numBytes < 1024 * 1024 * 1024) return (numBytes / (1024 * 1024)).toFixed(1) + ' MB';
  return (numBytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

// Get file icon
function getFileIcon(mimeType, fileName = '') {
  const nameLower = fileName.toLowerCase();
  
  // Check filename first
  if (nameLower.includes('contract') || nameLower.includes('agreement')) return '📜';
  if (nameLower.includes('rental') || nameLower.includes('lease')) return '🏠';
  if (nameLower.includes('employment') || nameLower.includes('employee')) return '👔';
  if (nameLower.includes('clause')) return '📋';
  if (nameLower.includes('note') || nameLower.includes('memo')) return '📝';
  if (nameLower.includes('practice')) return '⚖️';
  if (nameLower.includes('template')) return '📄';
  if (nameLower.includes('invoice') || nameLower.includes('bill')) return '🧾';
  if (nameLower.includes('receipt')) return '🧾';
  if (nameLower.includes('report')) return '📊';
  if (nameLower.includes('certificate') || nameLower.includes('cert')) return '🎓';
  if (nameLower.includes('license') || nameLower.includes('licence')) return '🪪';
  if (nameLower.includes('form')) return '📋';
  if (nameLower.includes('letter')) return '✉️';
  
  // Then check MIME type
  if (!mimeType) return '📄';
  
  if (mimeType.includes('pdf')) return '📕';
  if (mimeType.includes('msword') || mimeType.includes('wordprocessingml')) return '📘';
  if (mimeType.includes('document')) return '📄';
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return '📊';
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return '📽️';
  if (mimeType.includes('image')) return '🖼️';
  if (mimeType.includes('video')) return '🎥';
  if (mimeType.includes('audio')) return '🎵';
  if (mimeType.includes('text')) return '📄';
  if (mimeType.includes('folder')) return '📁';
  
  return '📄';
}

// Theme functions
function toggleTheme() {
  window.appState.theme = window.appState.theme === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', window.appState.theme);
  localStorage.setItem('theme', window.appState.theme);
  if (window.renderCurrentView) window.renderCurrentView();
}

function changeGridSize(size) {
  window.appState.gridSize = size;
  localStorage.setItem('gridSize', size);
  document.documentElement.setAttribute('data-grid-size', size);
  if (window.renderCurrentView) window.renderCurrentView();
}

function changeFilesPerPage(count) {
  window.appState.filesPerPage = parseInt(count);
  localStorage.setItem('filesPerPage', count);
  if (window.renderCurrentView) window.renderCurrentView();
}

// Show notification
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
    color: white;
    padding: 16px 24px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 1000;
    animation: slideIn 0.3s ease;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Escape HTML
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Get relevance color
function getRelevanceColor(relevance) {
  const colors = {
    'Very High': '#4caf50',
    'High': '#8bc34a',
    'Medium': '#ff9800',
    'Low': '#ff5722',
    'Very Low': '#f44336'
  };
  return colors[relevance] || '#666';
}

// Highlight differences
function highlightDiff(a, b, side) {
  if (!a || !b) return escapeHtml(a || '');
  const aWords = a.split(' ');
  const bWords = b.split(' ');
  let html = '';
  for (let i = 0; i < aWords.length; i++) {
    if (aWords[i] !== bWords[i]) {
      html += `<span style="background:${side === 'left' ? '#ffdbe3' : '#d2ffd6'};border-radius:4px;padding:1px 2px;">${escapeHtml(aWords[i])}</span> `;
    } else {
      html += escapeHtml(aWords[i]) + ' ';
    }
  }
  return html.trim();
}

// Make functions globally available
window.formatDate = formatDate;
window.formatFileSize = formatFileSize;
window.getFileIcon = getFileIcon;
window.toggleTheme = toggleTheme;
window.changeGridSize = changeGridSize;
window.changeFilesPerPage = changeFilesPerPage;
window.showNotification = showNotification;
window.escapeHtml = escapeHtml;
window.getRelevanceColor = getRelevanceColor;
window.highlightDiff = highlightDiff;