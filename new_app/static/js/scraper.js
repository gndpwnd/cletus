// static/js/scraper.js - Enhanced with real-time status updates

document.addEventListener('DOMContentLoaded', function() {
    initializeScraperPage();
});

let activeSessionId = null;
let statusPollInterval = null;
let ws = null;

function initializeScraperPage() {
    setupWebSocket();
    loadCategories();
    setupScraperControls();
    loadScrapeHistory();
}

function setupWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(setupWebSocket, 3000);
    };
}

function handleWebSocketMessage(data) {
    if (data.type === 'scrape_update' && data.session_id === activeSessionId) {
        // Update scrape status in real-time
        updateScrapeStatusDisplay(data.status);
    }
    
    if (data.type === 'database_update' && data.changes.articles) {
        // Reload history when scrape completes
        loadScrapeHistory();
    }
}

async function loadCategories() {
    try {
        const response = await fetch('/api/scraper/categories');
        const data = await response.json();
        
        const container = document.getElementById('category-checkboxes');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (data.categories && data.categories.length > 0) {
            data.categories.forEach(cat => {
                const label = document.createElement('label');
                label.className = 'checkbox-label';
                label.innerHTML = `
                    <input type="checkbox" value="${cat}" class="category-checkbox" checked>
                    ${cat}
                `;
                container.appendChild(label);
            });
        }
    } catch (err) {
        console.error('Error loading categories:', err);
        showNotification('Error loading categories: ' + err.message, 'error');
    }
}

function setupScraperControls() {
    const startBtn = document.getElementById('start-scrape');
    if (startBtn) {
        startBtn.addEventListener('click', startScrape);
    }
}

function selectAllCategories() {
    const checkboxes = document.querySelectorAll('.category-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
    });
}

function deselectAllCategories() {
    const checkboxes = document.querySelectorAll('.category-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
}

async function startScrape() {
    const sessionType = document.getElementById('session-type')?.value || 'manual';
    const checkboxes = document.querySelectorAll('.category-checkbox:checked');
    const categories = Array.from(checkboxes).map(cb => cb.value);
    
    if (categories.length === 0) {
        showNotification('Please select at least one category to scrape', 'error');
        return;
    }
    
    const payload = {
        session_type: sessionType,
        categories: categories
    };
    
    const startBtn = document.querySelector('button[onclick="startScrape()"]');
    if (startBtn) {
        startBtn.disabled = true;
        startBtn.innerHTML = '<span class="loading-spinner"></span> Starting...';
    }
    
    try {
        const response = await fetch('/api/scraper/scrape', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        showNotification(`Scraping started! Session: ${data.session_id}`, 'success');
        
        // Store active session ID
        activeSessionId = data.session_id;
        
        // Initialize status display
        const statusEl = document.getElementById('scrape-status');
        if (statusEl) {
            statusEl.innerHTML = `
                <div class="scrape-progress">
                    <div class="status-row">
                        <strong>Session ID:</strong> 
                        <span class="session-id">${data.session_id}</span>
                    </div>
                    <div class="status-row">
                        <strong>Status:</strong> 
                        <span class="status-badge status-started">Starting...</span>
                    </div>
                    <div class="status-row">
                        <strong>Progress:</strong> 
                        <span id="progress-text">Initializing...</span>
                    </div>
                    <div class="status-row">
                        <strong>Articles Found:</strong> 
                        <span id="articles-count" class="text-success">0</span>
                    </div>
                </div>
            `;
        }
        
        // Start polling for status
        startStatusPolling(data.session_id);
        
    } catch (err) {
        console.error('Error starting scrape:', err);
        showNotification('Error starting scrape: ' + err.message, 'error');
    } finally {
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.innerHTML = 'Start Scraping';
        }
    }
}

function startStatusPolling(sessionId) {
    // Clear any existing interval
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }
    
    // Update status immediately
    updateScrapeStatus(sessionId);
    
    // Poll every 2 seconds
    statusPollInterval = setInterval(() => {
        updateScrapeStatus(sessionId);
    }, 2000);
}

async function updateScrapeStatus(sessionId) {
    try {
        const response = await fetch(`/api/scraper/status/${sessionId}`);
        
        if (!response.ok) {
            // Session might not exist yet, try again
            if (response.status === 404) {
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        updateScrapeStatusDisplay(data);
        
        // If scraping is complete or errored, stop polling
        if (data.status === 'completed' || data.status === 'error') {
            if (statusPollInterval) {
                clearInterval(statusPollInterval);
                statusPollInterval = null;
            }
            
            activeSessionId = null;
            
            if (data.status === 'completed') {
                showNotification('Scraping completed successfully!', 'success');
            } else {
                showNotification('Scraping finished with errors', 'error');
            }
            
            // Reload history after completion
            setTimeout(() => {
                loadScrapeHistory();
            }, 1000);
        }
    } catch (err) {
        console.error('Status poll error:', err);
        // Don't stop polling on temporary errors
    }
}

function updateScrapeStatusDisplay(data) {
    const statusEl = document.getElementById('scrape-status');
    if (!statusEl) return;
    
    // Update status display with real-time data
    statusEl.innerHTML = `
        <div class="scrape-progress">
            <div class="status-row">
                <strong>Session ID:</strong> 
                <span class="session-id">${data.session_id || activeSessionId}</span>
            </div>
            <div class="status-row">
                <strong>Status:</strong> 
                <span class="status-badge status-${data.status}">${data.status}</span>
            </div>
            <div class="status-row">
                <strong>Progress:</strong> 
                <span id="progress-text">${data.completed_sources || 0}/${data.total_sources || 0} sources</span>
            </div>
            <div class="status-row">
                <strong>Failed Sources:</strong> 
                <span class="${data.failed_sources > 0 ? 'text-danger' : ''}">${data.failed_sources || 0}</span>
            </div>
            <div class="status-row">
                <strong>Articles Found:</strong> 
                <span id="articles-count" class="text-success">${data.total_articles || 0}</span>
            </div>
            ${data.duration_seconds ? `
            <div class="status-row">
                <strong>Duration:</strong> 
                <span>${Math.round(data.duration_seconds)}s</span>
            </div>
            ` : ''}
        </div>
    `;
}

async function loadScrapeHistory() {
    try {
        const response = await fetch('/api/scraper/sessions?limit=10');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const sessions = await response.json();
        
        const historyEl = document.getElementById('scrape-history');
        if (!historyEl) return;
        
        if (!sessions || sessions.length === 0) {
            historyEl.innerHTML = '<p class="text-muted">No scraping sessions found</p>';
            return;
        }
        
        historyEl.innerHTML = sessions.map(session => `
            <div class="session-item fade-in">
                <div class="session-header">
                    <span class="session-id">${session.session_id}</span>
                    <span class="status-badge status-${session.status}">${session.status}</span>
                </div>
                <div class="session-meta">
                    <span class="session-date">${formatDate(session.start_time)}</span>
                    <span class="session-articles">${session.articles_found || 0} articles found</span>
                    ${session.duration_seconds ? `<span>${Math.round(session.duration_seconds)}s</span>` : ''}
                </div>
            </div>
        `).join('');
        
    } catch (err) {
        console.error('Error loading scrape history:', err);
        const historyEl = document.getElementById('scrape-history');
        if (historyEl) {
            historyEl.innerHTML = '<p class="text-muted">Error loading history</p>';
        }
    }
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    if (!notification) return;
    
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 5000);
}