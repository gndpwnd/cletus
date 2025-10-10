// static/js/dashboard.js - Enhanced Dashboard with auto-updates

document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

let updateInterval = null;
let previousStats = null;

function initializeDashboard() {
    // Load dashboard stats immediately
    loadDashboardStats();
    
    // Start auto-update (every 10 seconds)
    startAutoUpdate();
}

function startAutoUpdate() {
    // Clear any existing interval
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    
    // Update every 10 seconds
    updateInterval = setInterval(() => {
        loadDashboardStats();
    }, 10000);
}

async function loadDashboardStats() {
    try {
        const [stats, health] = await Promise.all([
            fetch('/api/articles/stats').then(r => r.json()),
            fetch('/health').then(r => r.json())
        ]);
        
        // Update stats with animation if values changed
        updateStatCard('total-articles', stats.total_articles || 0);
        updateStatCard('articles-today', stats.articles_today || 0);
        updateStatCard('selected-articles', stats.selected_articles || 0);
        
        // Update scheduler status
        const statusEl = document.getElementById('scheduler-status');
        if (statusEl) {
            if (health.scheduler_running) {
                statusEl.textContent = '✓ Running';
                statusEl.className = 'stat-value status-running';
                statusEl.style.color = '#16a34a';
            } else {
                statusEl.textContent = '✗ Stopped';
                statusEl.className = 'stat-value status-stopped';
                statusEl.style.color = '#dc2626';
            }
        }
        
        // Load recent sessions
        await loadRecentSessions();
        
        // Store current stats for comparison
        previousStats = stats;
        
    } catch (err) {
        console.error('Error loading dashboard:', err);
        // Don't show notification on auto-update errors to avoid spam
        if (!updateInterval) {
            showNotification('Error loading dashboard: ' + err.message, 'error');
        }
    }
}

function updateStatCard(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const currentValue = parseInt(element.textContent) || 0;
    
    if (newValue !== currentValue) {
        // Animate change
        element.style.transition = 'transform 0.3s ease, color 0.3s ease';
        element.style.transform = 'scale(1.1)';
        element.style.color = 'var(--success-color)';
        
        element.textContent = newValue;
        
        setTimeout(() => {
            element.style.transform = 'scale(1)';
            element.style.color = 'var(--primary-color)';
        }, 300);
    } else {
        element.textContent = newValue;
    }
}

async function loadRecentSessions() {
    try {
        const response = await fetch('/api/scraper/sessions?limit=5');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        const sessionsEl = document.getElementById('recent-sessions');
        if (!sessionsEl) return;
        
        // Handle both array and object responses
        const sessions = Array.isArray(data) ? data : (data.sessions || []);
        
        if (sessions.length === 0) {
            sessionsEl.innerHTML = '<p class="text-muted">No recent scraping sessions</p>';
            return;
        }
        
        sessionsEl.innerHTML = sessions.map(session => `
            <div class="session-item fade-in">
                <div class="session-header">
                    <span class="session-id">${session.session_id}</span>
                    <span class="status-badge status-${session.status}">${session.status}</span>
                </div>
                <div class="session-meta">
                    <span class="session-date">${formatDate(session.start_time)}</span>
                    <span class="session-articles">${session.articles_found || 0} articles</span>
                </div>
            </div>
        `).join('');
        
    } catch (err) {
        console.error('Error loading sessions:', err);
        const sessionsEl = document.getElementById('recent-sessions');
        if (sessionsEl && !updateInterval) {
            sessionsEl.innerHTML = '<p class="text-muted">Error loading sessions</p>';
        }
    }
}

async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        const jobsList = data.scheduled_jobs.map(job => 
            `${job.name}: ${job.next_run || 'N/A'}`
        ).join('\n');
        
        const message = `Status: ${data.status}\nScheduler: ${data.scheduler_running ? 'Running' : 'Stopped'}\nJobs: ${data.scheduled_jobs.length}\n\n${jobsList}`;
        
        alert(message);
        showNotification('Health check completed', 'success');
    } catch (err) {
        showNotification('Health check failed: ' + err.message, 'error');
    }
}

async function syncBlacklist() {
    try {
        const response = await fetch('/api/blacklist/sync-db-to-json', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        showNotification(data.message, 'success');
    } catch (err) {
        showNotification('Blacklist sync failed: ' + err.message, 'error');
    }
}

// Helper function
function formatDate(dateString) {
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
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});