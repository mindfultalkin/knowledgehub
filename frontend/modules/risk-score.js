// modules/risk-score.js - Phase 1: Risk Analysis Module
console.log('Loading risk-score.js...');



// ============================================================================
// STATE MANAGEMENT
// ============================================================================
window.riskAnalysisState = {
  uploadedFiles: [],
  analysisResults: [],
  isAnalyzing: false
};

// ============================================================================
// MAIN VIEW RENDERER
// ============================================================================
window.renderRiskScore = function() {
  return `
    <div class="risk-score-page">
      <!-- Header Section -->
      <div class="page-header">
        <div class="header-content">
          <h1 class="page-title-serif">
            <i class="fas fa-shield-alt"></i>
            Contract Risk Analysis
          </h1>
          <p class="page-subtitle">
            Upload contracts for instant risk assessment
          </p>
        </div>
      </div>

      <!-- Upload Section -->
      <div class="upload-section" id="uploadSection">
        ${renderUploadArea()}
      </div>

      <!-- Analysis Results Section -->
      <div class="analysis-results-section" id="analysisResultsSection" style="display: none;">
        ${renderAnalysisResults()}
      </div>
    </div>
  `;
};

// ============================================================================
// UPLOAD AREA RENDERER
// ============================================================================
function renderUploadArea() {
  return `
    <div class="upload-container">
      <!-- Drag & Drop Zone -->
      <div class="upload-zone" id="uploadZone">
        <div class="upload-icon">
          <i class="fas fa-cloud-upload-alt"></i>
        </div>
        <h3 class="upload-title">Upload Contract for Risk Analysis</h3>
        <p class="upload-description">
          Drag and drop files here, or click to browse
        </p>
        <p class="upload-formats">
          <i class="fas fa-file-word"></i> DOCX
          <i class="fas fa-file-pdf"></i> PDF
          <i class="fab fa-google-drive"></i> Google Docs
        </p>
        <input 
          type="file" 
          id="fileInput" 
          accept=".docx,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf"
          multiple
          style="display: none;"
        />
      </div>

      <!-- OR Divider -->
      <div class="upload-divider">
        <span>OR</span>
      </div>

      <!-- Google Drive Button -->
      <button class="btn-drive-select" onclick="window.selectFromDrive()">
        <i class="fab fa-google-drive"></i>
        Select from Google Drive
      </button>

      <!-- Uploaded Files List -->
      <div class="uploaded-files-list" id="uploadedFilesList" style="display: none;">
        <h4><i class="fas fa-list"></i> Files Ready for Analysis</h4>
        <div id="uploadedFilesContainer"></div>
        <div class="upload-actions">
          <button class="btn-secondary" onclick="window.clearUploadedFiles()">
            <i class="fas fa-times"></i> Clear All
          </button>
          <button class="btn-primary" onclick="window.analyzeUploadedFiles()">
            <i class="fas fa-chart-line"></i> Analyze Risk
          </button>
        </div>
      </div>
    </div>
  `;
}

// ============================================================================
// ANALYSIS RESULTS RENDERER (Phase 2 will populate this)
// ============================================================================
function renderAnalysisResults() {
  const results = window.riskAnalysisState.analysisResults;
  
  if (results.length === 0) {
    return `
      <div class="empty-state">
        <i class="fas fa-chart-bar"></i>
        <p>No analysis results yet</p>
      </div>
    `;
  }

  return `
    <div class="results-header">
      <h2><i class="fas fa-clipboard-check"></i> Risk Analysis Results</h2>
      <button class="btn-secondary" onclick="window.clearAnalysisResults()">
        <i class="fas fa-trash"></i> Clear Results
      </button>
    </div>
    <div class="results-grid" id="resultsGrid">
      ${results.map(result => renderSingleResult(result)).join('')}
    </div>
  `;
}

function renderSingleResult(result) {
  const riskColor = result.risk_level === 'LOW' ? '#10b981' : 
                    result.risk_level === 'MEDIUM' ? '#f59e0b' : '#ef4444';
  
  return `
    <div class="result-card">
      <div class="result-header">
        <h3>${result.fileName}</h3>
        <div class="risk-badge" style="background: ${riskColor}">
          ${result.risk_level} RISK
        </div>
      </div>
      <div class="result-score">
        <div class="score-circle" style="border-color: ${riskColor}">
          <span class="score-number">${result.risk_score}</span>
          <span class="score-label">/100</span>
        </div>
      </div>
      <div class="result-summary">
        <div class="summary-item good">
          <i class="fas fa-check-circle"></i>
          <span>${result.good_clauses?.length || 0} Protected</span>
        </div>
        <div class="summary-item caution">
          <i class="fas fa-exclamation-triangle"></i>
          <span>${result.caution_clauses?.length || 0} At Risk</span>
        </div>
        <div class="summary-item missing">
          <i class="fas fa-times-circle"></i>
          <span>${result.missing_clauses?.length || 0} Missing</span>
        </div>
      </div>
      <button class="btn-view-details" onclick="window.viewDetailedRiskReport('${result.fileId}')">
        <i class="fas fa-eye"></i> View Detailed Report
      </button>
    </div>
  `;
}

// ============================================================================
// EVENT HANDLERS - UPLOAD ZONE
// ============================================================================
window.initRiskScoreListeners = function() {
  const uploadZone = document.getElementById('uploadZone');
  const fileInput = document.getElementById('fileInput');

  if (!uploadZone || !fileInput) return;

  // Click to upload
  uploadZone.addEventListener('click', () => {
    fileInput.click();
  });

  // File input change
  fileInput.addEventListener('change', (e) => {
    handleFileSelection(e.target.files);
  });

  // Drag and drop
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });

  uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
  });

  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    handleFileSelection(e.dataTransfer.files);
  });
};

// ============================================================================
// FILE HANDLING
// ============================================================================
function handleFileSelection(files) {
  if (!files || files.length === 0) return;

  const validFiles = Array.from(files).filter(file => {
    const isValid = file.type === 'application/pdf' || 
                    file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
                    file.name.endsWith('.docx') || 
                    file.name.endsWith('.pdf');
    
    if (!isValid) {
      window.showNotification(`${file.name} is not a supported format`, 'error');
    }
    return isValid;
  });

  if (validFiles.length === 0) return;

  validFiles.forEach(file => {
    const fileId = 'local_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    window.riskAnalysisState.uploadedFiles.push({
      id: fileId,
      name: file.name,
      type: file.type,
      size: file.size,
      file: file,
      source: 'local'
    });
  });

  updateUploadedFilesList();
  window.showNotification(`${validFiles.length} file(s) added`, 'success');
}

function updateUploadedFilesList() {
  const files = window.riskAnalysisState.uploadedFiles;
  const listContainer = document.getElementById('uploadedFilesList');
  const filesContainer = document.getElementById('uploadedFilesContainer');

  if (!listContainer || !filesContainer) return;

  if (files.length === 0) {
    listContainer.style.display = 'none';
    return;
  }

  listContainer.style.display = 'block';
  filesContainer.innerHTML = files.map(file => `
    <div class="uploaded-file-item">
      <div class="file-icon">
        <i class="fas fa-file-${file.name.endsWith('.pdf') ? 'pdf' : 'word'}"></i>
      </div>
      <div class="file-info">
        <div class="file-name">${file.name}</div>
        <div class="file-meta">
          ${(file.size / 1024).toFixed(1)} KB
          <span class="file-source">
            <i class="fas fa-${file.source === 'local' ? 'desktop' : 'cloud'}"></i>
            ${file.source === 'local' ? 'Local' : 'Drive'}
          </span>
        </div>
      </div>
      <button class="btn-remove-file" onclick="window.removeUploadedFile('${file.id}')">
        <i class="fas fa-times"></i>
      </button>
    </div>
  `).join('');
}

// ============================================================================
// PUBLIC API FUNCTIONS
// ============================================================================
window.selectFromDrive = function () {
  // Phase 1: Google Drive integration disabled
  window.showNotification(
    'Google Drive integration is coming soon ',
    'info'
  );
};

async function loadGooglePickerAPI() {
  return new Promise((resolve, reject) => {
    if (window.google && window.google.picker) {
      resolve();
      return;
    }
    
    const script = document.createElement('script');
    script.src = 'https://apis.google.com/js/api.js';
    script.onload = () => {
      window.gapi.load('picker', {
        callback: resolve,
        onerror: reject
      });
    };
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

function createDrivePicker() {
  // Get Google Client ID from config
  const clientId = window.GOOGLE_CLIENT_ID || '';
  
  if (!clientId) {
    window.showNotification('Google Drive picker not configured', 'error');
    return;
  }
  
  const picker = new google.picker.PickerBuilder()
    .addView(new google.picker.DocsView()
      .setIncludeFolders(false)
      .setMimeTypes('application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword,application/vnd.google-apps.document'))
    .addView(new google.picker.DocsView()
      .setLabel('Starred')
      .setStarred(true))
    .setOAuthToken(window.googleAccessToken)
    .setDeveloperKey(window.GOOGLE_API_KEY || '')
    .setCallback(pickerCallback)
    .setTitle('Select Contract for Risk Analysis')
    .build();
  
  picker.setVisible(true);
}

async function pickerCallback(data) {
  if (data.action === google.picker.Action.PICKED) {
    const files = data.docs;
    
    for (const file of files) {
      try {
        // Download file from Drive
        const response = await fetch(`${API_BASE_URL}/drive/files/${file.id}/download`);
        
        if (!response.ok) {
          throw new Error('Failed to download file from Drive');
        }
        
        const blob = await response.blob();
        const localFile = new File([blob], file.name, { type: file.mimeType });
        
        // Add to uploaded files
        const fileId = 'drive_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        window.riskAnalysisState.uploadedFiles.push({
          id: fileId,
          name: file.name,
          type: file.mimeType,
          size: blob.size,
          file: localFile,
          source: 'drive'
        });
        
      } catch (error) {
        console.error(`Error processing ${file.name}:`, error);
        window.showNotification(`Failed to load ${file.name}`, 'error');
      }
    }
    
    updateUploadedFilesList();
    window.showNotification(`${files.length} file(s) added from Drive`, 'success');
  }
}

window.removeUploadedFile = function(fileId) {
  window.riskAnalysisState.uploadedFiles = window.riskAnalysisState.uploadedFiles.filter(
    f => f.id !== fileId
  );
  updateUploadedFilesList();
  window.showNotification('File removed', 'success');
};

window.clearUploadedFiles = function() {
  if (!confirm('Clear all uploaded files?')) return;
  
  window.riskAnalysisState.uploadedFiles = [];
  updateUploadedFilesList();
  window.showNotification('All files cleared', 'success');
};

window.analyzeUploadedFiles = async function() {
  const files = window.riskAnalysisState.uploadedFiles;
  
  if (files.length === 0) {
    window.showNotification('Please upload files first', 'warning');
    return;
  }

  window.riskAnalysisState.isAnalyzing = true;
  window.showNotification('Analyzing contracts... This may take a moment', 'info');

  try {
    // Show loading state
    const uploadSection = document.getElementById('uploadSection');
    const resultsSection = document.getElementById('analysisResultsSection');
    
    if (uploadSection) uploadSection.style.display = 'none';
    if (resultsSection) {
      resultsSection.style.display = 'block';
      resultsSection.innerHTML = `
        <div class="loading-analysis">
          <div class="spinner-large"></div>
          <h3>Analyzing ${files.length} contract${files.length > 1 ? 's' : ''}...</h3>
          <p>Extracting clauses and calculating risk scores</p>
        </div>
      `;
    }

    // Process each file
    const results = [];
    for (const fileData of files) {
      try {
        const result = await analyzeContract(fileData);
        results.push(result);
      } catch (error) {
        console.error(`Error analyzing ${fileData.name}:`, error);
        window.showNotification(`Failed to analyze ${fileData.name}`, 'error');
      }
    }

    // Store results
    window.riskAnalysisState.analysisResults = results;

    // Render results
    if (resultsSection) {
      resultsSection.innerHTML = renderAnalysisResults();
    }

    window.showNotification(`Analysis complete! ${results.length} contract(s) processed`, 'success');

  } catch (error) {
    console.error('Analysis error:', error);
    window.showNotification('Analysis failed. Please try again.', 'error');
  } finally {
    window.riskAnalysisState.isAnalyzing = false;
  }
};

// ============================================================================
// CONTRACT ANALYSIS (Connects to Backend)
// ============================================================================
async function analyzeContract(fileData) {
  const formData = new FormData();
  formData.append('file', fileData.file);

  try {
    // Use single-step quick analysis endpoint
    const response = await fetch(`${API_BASE_URL}/risk-analysis/quick-analysis`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || 'Failed to analyze document');
    }


    const analysisData = await response.json();

    // Generate unique file ID for this session
    const fileId = 'temp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

    return {
      fileId: fileId,
      fileName: fileData.name,
      risk_score: analysisData.risk_score,
      risk_level: analysisData.risk_level,
      good_clauses: analysisData.good_clauses || [],
      caution_clauses: analysisData.caution_clauses || [],
      missing_clauses: analysisData.missing_clauses || [],
      clauses: analysisData.clauses || [],
      clauses_count: analysisData.clauses_count
    };

  } catch (error) {
    console.error('Contract analysis error:', error);
    throw error;
  }
}

window.clearAnalysisResults = function() {
  if (!confirm('Clear all analysis results?')) return;

  window.riskAnalysisState.analysisResults = [];
  window.riskAnalysisState.uploadedFiles = [];

  const uploadSection = document.getElementById('uploadSection');
  const resultsSection = document.getElementById('analysisResultsSection');

  if (uploadSection) uploadSection.style.display = 'block';
  if (resultsSection) resultsSection.style.display = 'none';

  // Re-render upload area
  if (uploadSection) {
    uploadSection.innerHTML = renderUploadArea();
    window.initRiskScoreListeners();
  }

  window.showNotification('Results cleared', 'success');
};

window.viewDetailedRiskReport = function(fileId) {
  const result = window.riskAnalysisState.analysisResults.find(r => r.fileId === fileId);
  
  if (!result) {
    window.showNotification('Analysis result not found', 'error');
    return;
  }
  
  // Show detailed modal
  showDetailedReportModal(result);
};

// ============================================================================
// DETAILED REPORT MODAL
// ============================================================================

function showDetailedReportModal(result) {
  const modal = document.createElement('div');
  modal.id = 'detailedReportModal';
  modal.className = 'modal active';
  
  const riskColor = result.risk_level === 'LOW' ? '#10b981' : 
                    result.risk_level === 'MEDIUM' ? '#f59e0b' : '#ef4444';
  
  modal.innerHTML = `
    <div class="modal-overlay" onclick="window.closeDetailedReport()"></div>
    <div class="modal-content detailed-report-content">
      <!-- Header -->
      <div class="detailed-report-header">
        <div>
          <h2 class="modal-title-serif">
            <i class="fas fa-file-contract"></i>
            Detailed Risk Analysis
          </h2>
          <p class="modal-subtitle">${result.fileName}</p>
        </div>
        <div class="header-actions">
          <button class="btn-icon" onclick="window.exportReportPDF('${result.fileId}')" title="Export PDF">
            <i class="fas fa-file-pdf"></i>
          </button>
          <button class="btn-icon" onclick="window.copyReportToClipboard('${result.fileId}')" title="Copy to Clipboard">
            <i class="fas fa-copy"></i>
          </button>
          <button class="btn-icon" onclick="window.printReport('${result.fileId}')" title="Print">
            <i class="fas fa-print"></i>
          </button>
          <button class="close-btn" onclick="window.closeDetailedReport()">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
      
      <!-- Body -->
      <div class="detailed-report-body">
        <!-- Executive Summary -->
        <div class="report-section">
          <h3><i class="fas fa-chart-bar"></i> Executive Summary</h3>
          <div class="executive-summary">
            <div class="summary-card" style="border-left: 4px solid ${riskColor}">
              <div class="summary-score">
                <span class="score-large">${result.risk_score}</span>
                <span class="score-max">/100</span>
              </div>
              <div class="summary-level" style="color: ${riskColor}">
                ${result.risk_level} RISK
              </div>
            </div>
            <div class="summary-stats">
              <div class="stat-item">
                <i class="fas fa-file-alt"></i>
                <span class="stat-label">Total Clauses</span>
                <span class="stat-value">${result.clauses_count}</span>
              </div>
              <div class="stat-item good">
                <i class="fas fa-check-circle"></i>
                <span class="stat-label">Protected</span>
                <span class="stat-value">${result.good_clauses?.length || 0}</span>
              </div>
              <div class="stat-item caution">
                <i class="fas fa-exclamation-triangle"></i>
                <span class="stat-label">At Risk</span>
                <span class="stat-value">${result.caution_clauses?.length || 0}</span>
              </div>
              <div class="stat-item danger">
                <i class="fas fa-times-circle"></i>
                <span class="stat-label">Missing</span>
                <span class="stat-value">${result.missing_clauses?.length || 0}</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Protected Clauses -->
        ${renderClauseSection('Protected Clauses', result.good_clauses, 'check-circle', '#10b981', 'These clauses provide adequate protection.')}
        
        <!-- Risk Areas -->
        ${renderClauseSection('Risk Areas', result.caution_clauses, 'exclamation-triangle', '#f59e0b', 'These clauses require attention and may need revision.')}
        
        <!-- Missing Clauses -->
        ${renderClauseSection('Missing Critical Clauses', result.missing_clauses, 'times-circle', '#ef4444', 'These essential clauses are missing and should be added.')}
        
        <!-- Detailed Clause Analysis -->
        <div class="report-section">
          <h3><i class="fas fa-list-alt"></i> Clause-by-Clause Analysis</h3>
          <div class="clause-analysis-list">
            ${renderDetailedClauses(result.clauses || [])}
          </div>
        </div>
        
        <!-- Recommendations -->
        <div class="report-section">
          <h3><i class="fas fa-lightbulb"></i> Recommendations</h3>
          <div class="recommendations-list">
            ${generateRecommendations(result)}
          </div>
        </div>
      </div>
      
      <!-- Footer -->
      <div class="modal-footer">
        <button class="btn-secondary" onclick="window.closeDetailedReport()">
          <i class="fas fa-times"></i> Close
        </button>
        <button class="btn-primary" onclick="window.exportReportPDF('${result.fileId}')">
          <i class="fas fa-download"></i> Export Report
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Animate in
  setTimeout(() => {
    modal.classList.add('active');
  }, 10);
}

function renderClauseSection(title, clauses, icon, color, description) {
  if (!clauses || clauses.length === 0) {
    return `
      <div class="report-section">
        <h3><i class="fas fa-${icon}" style="color: ${color}"></i> ${title}</h3>
        <p class="empty-state-text">None found</p>
      </div>
    `;
  }
  
  return `
    <div class="report-section">
      <h3><i class="fas fa-${icon}" style="color: ${color}"></i> ${title}</h3>
      <p class="section-description">${description}</p>
      <ul class="clause-list">
        ${clauses.map(clause => `
          <li class="clause-list-item">
            <i class="fas fa-${icon}" style="color: ${color}"></i>
            <span>${clause}</span>
          </li>
        `).join('')}
      </ul>
    </div>
  `;
}

function renderDetailedClauses(clauses) {
  if (!clauses || clauses.length === 0) {
    return '<p class="empty-state-text">No clause details available</p>';
  }
  
  return clauses.map(clause => {
    const riskColor = clause.risk_level === 'Low' ? '#10b981' : 
                      clause.risk_level === 'Medium' ? '#f59e0b' : '#ef4444';
    
    return `
      <div class="detailed-clause-card">
        <div class="clause-card-header">
          <div>
            <span class="clause-number">${clause.section_number || clause.clause_number}</span>
            <h4 class="clause-title">${clause.title}</h4>
          </div>
          <span class="risk-badge-small" style="background: ${riskColor}">
            ${clause.risk_level} Risk
          </span>
        </div>
        <div class="clause-card-body">
          <p class="clause-content">${clause.content?.substring(0, 200)}${clause.content?.length > 200 ? '...' : ''}</p>
          <div class="clause-score">
            <span class="score-label">Risk Score:</span>
            <div class="score-bar">
              <div class="score-fill" style="width: ${clause.risk_score}%; background: ${riskColor}"></div>
            </div>
            <span class="score-number">${clause.risk_score}/100</span>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function generateRecommendations(result) {
  const recommendations = [];
  
  // Based on risk level
  if (result.risk_level === 'HIGH') {
    recommendations.push({
      priority: 'high',
      text: 'This contract requires immediate legal review before execution.',
      icon: 'exclamation-triangle'
    });
  }
  
  // Based on missing clauses
  if (result.missing_clauses?.length > 0) {
    recommendations.push({
      priority: 'high',
      text: `Add ${result.missing_clauses.length} missing critical clauses to strengthen contract protection.`,
      icon: 'plus-circle'
    });
  }
  
  // Based on caution clauses
  if (result.caution_clauses?.length > 0) {
    recommendations.push({
      priority: 'medium',
      text: `Review and revise ${result.caution_clauses.length} clauses that present potential risks.`,
      icon: 'edit'
    });
  }
  
  // Based on score
  if (result.risk_score < 60) {
    recommendations.push({
      priority: 'high',
      text: 'Consider using a standard template as this contract has significant gaps.',
      icon: 'file-contract'
    });
  } else if (result.risk_score >= 80) {
    recommendations.push({
      priority: 'low',
      text: 'Contract structure is solid. Minor improvements may be beneficial.',
      icon: 'check-circle'
    });
  }
  
  return recommendations.map(rec => {
    const color = rec.priority === 'high' ? '#ef4444' : 
                  rec.priority === 'medium' ? '#f59e0b' : '#10b981';
    
    return `
      <div class="recommendation-item" style="border-left-color: ${color}">
        <i class="fas fa-${rec.icon}" style="color: ${color}"></i>
        <div>
          <span class="rec-priority" style="color: ${color}">${rec.priority.toUpperCase()} PRIORITY</span>
          <p class="rec-text">${rec.text}</p>
        </div>
      </div>
    `;
  }).join('');
}

window.closeDetailedReport = function() {
  const modal = document.getElementById('detailedReportModal');
  if (modal) {
    modal.classList.remove('active');
    setTimeout(() => modal.remove(), 300);
  }
};

// ============================================================================
// EXPORT FUNCTIONS
// ============================================================================

window.exportReportPDF = function(fileId) {
  window.showNotification('Generating PDF report...', 'info');
  
  // This would integrate with a PDF generation library in production
  // For now, show a placeholder
  setTimeout(() => {
    window.showNotification('PDF generation coming soon!', 'info');
  }, 1000);
};

window.copyReportToClipboard = function(fileId) {
  const result = window.riskAnalysisState.analysisResults.find(r => r.fileId === fileId);
  
  if (!result) return;
  
  const reportText = `
RISK ANALYSIS REPORT
${result.fileName}
${'='.repeat(60)}

OVERALL RISK SCORE: ${result.risk_score}/100
RISK LEVEL: ${result.risk_level}

SUMMARY:
- Total Clauses: ${result.clauses_count}
- Protected Clauses: ${result.good_clauses?.length || 0}
- Risk Areas: ${result.caution_clauses?.length || 0}
- Missing Clauses: ${result.missing_clauses?.length || 0}

PROTECTED CLAUSES:
${(result.good_clauses || []).map(c => `✓ ${c}`).join('\n')}

RISK AREAS:
${(result.caution_clauses || []).map(c => `⚠ ${c}`).join('\n')}

MISSING CLAUSES:
${(result.missing_clauses || []).map(c => `✗ ${c}`).join('\n')}

Generated by QL Partners Knowledge Hub
${new Date().toLocaleString()}
  `.trim();
  
  navigator.clipboard.writeText(reportText).then(() => {
    window.showNotification('Report copied to clipboard!', 'success');
  }).catch(() => {
    window.showNotification('Failed to copy report', 'error');
  });
};

window.printReport = function(fileId) {
  window.print();
};

// ============================================================================
// VIEW INITIALIZATION
// ============================================================================
window.showRiskScoreView = function() {
  const mainContent = document.querySelector('.main-content');
  if (mainContent && window.renderRiskScore) {
    mainContent.innerHTML = window.renderRiskScore();
    
    // Initialize event listeners
    setTimeout(() => {
      window.initRiskScoreListeners();
    }, 100);
  }
};

console.log('✅ Risk Score module loaded');
