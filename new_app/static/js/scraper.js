// static/js/scraper.js - Fixed cooldown calculation and enhanced progress display

document.addEventListener('DOMContentLoaded', function() {
    initializeScraperPage();
});

let activeSessionId = null;
let statusPollInterval = null;
let cooldownCheckInterval = null;
let ws = null;

function initializeScraperPage() {
    setupWebSocket();
    loadCategories();
    setupScraperControls();
    loadScrapeHistory();
    checkCooldownStatus(); // Check cooldown immediately
    startCooldownMonitoring(); // Monitor cooldown status
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
        updateScrapeStatusDisplay(data.status);
    }
    
    if (data.type === 'database_update' && data.changes.articles) {
        loadScrapeHistory();
        checkCooldownStatus(); // Refresh cooldown after scrape completes
    }
}

async function checkCooldownStatus() {
    try {
        const response = await fetch('/api/scraper/cooldown-status');
        const data = await response.json();
        
        updateCooldownUI(data);
    } catch (err) {
        console.error('Error checking cooldown:', err);
    }
}

function updateCooldownUI(cooldownData) {
    const startBtn = document.querySelector('button[onclick="startScrape()"]');
    if (!startBtn) return;
    
    // Add or update cooldown indicator
    let cooldownIndicator = document.getElementById('cooldown-indicator');
    if (!cooldownIndicator) {
        cooldownIndicator = document.createElement('div');
        cooldownIndicator.id = 'cooldown-indicator';
        cooldownIndicator.className = 'cooldown-status';
        startBtn.parentElement.insertBefore(cooldownIndicator, startBtn);
    }
    
    if (cooldownData.on_cooldown) {
        startBtn.disabled = true;
        startBtn.classList.add('disabled');
        
        // Fix: Use total seconds, not convert to minutes incorrectly
        const totalSeconds = cooldownData.remaining_seconds;
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        
        cooldownIndicator.innerHTML = `
            <div class="alert alert-warning">
                <strong>⏳ Cooldown Active</strong><br>
                Please wait ${minutes}m ${seconds}s before next scrape<br>
                <small>Last scrape: ${formatDate(cooldownData.last_scrape)}</small>
            </div>
        `;
        cooldownIndicator.style.display = 'block';
    } else {
        startBtn.disabled = false;
        startBtn.classList.remove('disabled');
        
        if (cooldownData.last_scrape) {
            cooldownIndicator.innerHTML = `
                <div class="alert alert-success">
                    <strong>✓ Ready to Scrape</strong><br>
                    <small>Last scrape: ${formatDate(cooldownData.last_scrape)}</small>
                </div>
            `;
        } else {
            cooldownIndicator.innerHTML = `
                <div class="alert alert-info">
                    <strong>✓ Ready to Scrape</strong><br>
                    <small>No recent scrapes detected</small>
                </div>
            `;
        }
        cooldownIndicator.style.display = 'block';
    }
}

function startCooldownMonitoring() {
    // Check cooldown status every 5 seconds for real-time updates
    if (cooldownCheckInterval) {
        clearInterval(cooldownCheckInterval);
    }
    
    cooldownCheckInterval = setInterval(() => {
        checkCooldownStatus();
    }, 5000);
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
            
            // Handle cooldown error specially
            if (response.status === 429) {
                const totalSeconds = errorData.detail.remaining_seconds;
                const minutes = Math.floor(totalSeconds / 60);
                const seconds = totalSeconds % 60;
                showNotification(
                    `⏳ Scraping is on cooldown! Please wait ${minutes}m ${seconds}s`,
                    'error'
                );
                checkCooldownStatus(); // Refresh UI
                return;
            }
            
            throw new Error(errorData.detail?.message || errorData.detail || `HTTP error! status: ${response.status}`);
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
                    <div class="progress-bar-container">
                        <div class="progress-bar" id="scrape-progress-bar" style="width: 0%">
                            <span class="progress-text" id="progress-percent">0%</span>
                        </div>
                    </div>
                    <div class="status-row">
                        <strong>Sources Processed:</strong> 
                        <span id="progress-text">0/0</span>
                    </div>
                    <div class="status-row">
                        <strong>Failed Sources:</strong> 
                        <span id="failed-count" class="text-danger">0</span>
                    </div>
                    <div class="status-row">
                        <strong>Articles Found:</strong> 
                        <span id="articles-count" class="text-success">0</span>
                    </div>
                    <div class="status-row">
                        <strong>New Articles:</strong> 
                        <span id="new-articles-count" class="text-info">0</span>
                    </div>
                    <div class="status-row">
                        <strong>Updated Articles:</strong> 
                        <span id="updated-articles-count" class="text-warning">0</span>
                    </div>
                </div>
            `;
        }
        
        // Start polling for status with faster interval
        startStatusPolling(data.session_id);
        
        // Refresh cooldown status after starting
        checkCooldownStatus();
        
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
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }
    
    updateScrapeStatus(sessionId);
    
    // Poll every 1 second for frequent updates
    statusPollInterval = setInterval(() => {
        updateScrapeStatus(sessionId);
    }, 1000);
}

async function updateScrapeStatus(sessionId) {
    try {
        const response = await fetch(`/api/scraper/status/${sessionId}`);
        
        if (!response.ok) {
            if (response.status === 404) {
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        updateScrapeStatusDisplay(data);
        
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
            
            setTimeout(() => {
                loadScrapeHistory();
                checkCooldownStatus(); // Refresh cooldown after completion
            }, 1000);
        }
    } catch (err) {
        console.error('Status poll error:', err);
    }
}

function updateScrapeStatusDisplay(data) {
    const statusEl = document.getElementById('scrape-status');
    if (!statusEl) return;
    
    // Calculate progress percentage
    const totalSources = data.total_sources || 0;
    const completedSources = data.completed_sources || 0;
    const failedSources = data.failed_sources || 0;
    const processedSources = completedSources + failedSources;
    const progressPercent = totalSources > 0 ? Math.round((processedSources / totalSources) * 100) : 0;
    
    // Update progress bar if it exists
    const progressBar = document.getElementById('scrape-progress-bar');
    if (progressBar) {
        progressBar.style.width = progressPercent + '%';
        const progressText = document.getElementById('progress-percent');
        if (progressText) {
            progressText.textContent = progressPercent + '%';
        }
    }
    
    // Update individual stats
    const progressTextEl = document.getElementById('progress-text');
    if (progressTextEl) {
        progressTextEl.textContent = `${processedSources}/${totalSources}`;
    }
    
    const failedCountEl = document.getElementById('failed-count');
    if (failedCountEl) {
        failedCountEl.textContent = failedSources;
        failedCountEl.className = failedSources > 0 ? 'text-danger' : '';
    }
    
    const articlesCountEl = document.getElementById('articles-count');
    if (articlesCountEl) {
        articlesCountEl.textContent = data.total_articles || 0;
    }
    
    const newArticlesCountEl = document.getElementById('new-articles-count');
    if (newArticlesCountEl) {
        newArticlesCountEl.textContent = data.new_articles || 0;
    }
    
    const updatedArticlesCountEl = document.getElementById('updated-articles-count');
    if (updatedArticlesCountEl) {
        updatedArticlesCountEl.textContent = data.updated_articles || 0;
    }
    
    // Update status badge
    const statusBadges = document.querySelectorAll('.status-badge');
    statusBadges.forEach(badge => {
        badge.className = `status-badge status-${data.status}`;
        badge.textContent = data.status;
    });
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
        
        historyEl.innerHTML = sessions.map(session => {
            const progressPercent = session.progress_percent || 0;
            const statusClass = session.status === 'completed' ? 'success' : 
                              session.status === 'error' ? 'danger' : 
                              session.status === 'in_progress' ? 'warning' : 'info';
            
            return `
                <div class="session-item fade-in">
                    <div class="session-header">
                        <span class="session-id">${session.session_id}</span>
                        <span class="status-badge status-${session.status}">${session.status}</span>
                    </div>
                    <div class="session-meta">
                        <span class="session-date">${formatDate(session.start_time)}</span>
                        <span class="session-articles">${session.articles_found || 0} articles 
                            (${session.new_articles || 0} new, ${session.updated_articles || 0} updated)</span>
                        ${session.status === 'in_progress' ? 
                            `<span class="session-progress">Progress: ${session.completed_sources}/${session.total_sources} sources (${progressPercent}%)</span>` 
                            : ''}
                        ${session.duration_seconds ? `<span>${Math.round(session.duration_seconds)}s</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');
        
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

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }
    if (cooldownCheckInterval) {
        clearInterval(cooldownCheckInterval);
    }
    if (ws) {
        ws.close();
    }
});