// static/js/dashboard.js - Dashboard specific functionality

document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

function initializeDashboard() {
    // Load dashboard stats
    loadDashboardStats();
    
    // Set up refresh button
    const refreshBtn = document.getElementById('refresh-dashboard');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDashboardStats);
    }
    
    // Set up health check button
    const healthBtn = document.getElementById('health-check');
    if (healthBtn) {
        healthBtn.addEventListener('click', checkHealth);
    }
    
    // Set up blacklist sync button
    const syncBtn = document.getElementById('sync-blacklist');
    if (syncBtn) {
        syncBtn.addEventListener('click', syncBlacklist);
    }
}

async function loadDashboardStats() {
    try {
        const [stats, health] = await Promise.all([
            fetch('/api/articles/stats').then(r => r.json()),
            fetch('/health').then(r => r.json())
        ]);
        
        // Update stats cards
        document.getElementById('total-articles').textContent = stats.total_articles || 0;
        document.getElementById('articles-today').textContent = stats.articles_today || 0;
        document.getElementById('selected-articles').textContent = stats.selected_articles || 0;
        
        // Update scheduler status
        const statusEl = document.getElementById('scheduler-status');
        if (health.scheduler_running) {
            statusEl.textContent = '✓ Running';
            statusEl.className = 'status-running';
        } else {
            statusEl.textContent = '✗ Stopped';
            statusEl.className = 'status-stopped';
        }
        
        // Load recent sessions
        await loadRecentSessions();
        
    } catch (err) {
        console.error('Error loading dashboard:', err);
        showNotification('Error loading dashboard: ' + err.message, 'error');
    }
}

async function loadRecentSessions() {
    try {
        const response = await fetch('/api/scraper/sessions?limit=5');
        const sessions = await response.json();
        
        const sessionsEl = document.getElementById('recent-sessions');
        if (sessions.length === 0) {
            sessionsEl.innerHTML = '<p class="text-muted">No recent scraping sessions</p>';
            return;
        }
        
        sessionsEl.innerHTML = sessions.map(session => `
            <div class="session-item">
                <div class="session-header">
                    <span class="session-id">${session.session_id}</span>
                    <span class="session-status ${session.status}">${session.status}</span>
                </div>
                <div class="session-meta">
                    <span class="session-date">${formatDate(session.start_time)}</span>
                    <span class="session-articles">${session.articles_found || 0} articles</span>
                </div>
            </div>
        `).join('');
        
    } catch (err) {
        console.error('Error loading sessions:', err);
        document.getElementById('recent-sessions').innerHTML = 
            '<p class="text-muted">Error loading sessions</p>';
    }
}

async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        const message = `
            Status: ${data.status}
            Scheduler: ${data.scheduler_running ? 'Running' : 'Stopped'}
            Jobs: ${data.scheduled_jobs.length}
        `;
        showNotification(message, 'success');
    } catch (err) {
        showNotification('Health check failed: ' + err.message, 'error');
    }
}

async function syncBlacklist() {
    try {
        const response = await fetch('/api/blacklist/sync-db-to-json', {
            method: 'POST'
        });
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