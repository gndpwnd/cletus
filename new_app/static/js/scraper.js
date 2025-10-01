// static/js/scraper.js - Scraper page functionality

document.addEventListener('DOMContentLoaded', function() {
    initializeScraperPage();
});

function initializeScraperPage() {
    loadCategories();
    setupScraperControls();
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
    const selectAllBtn = document.getElementById('select-all-categories');
    const selectNoneBtn = document.getElementById('select-none-categories');
    
    if (startBtn) {
        startBtn.addEventListener('click', startScrape);
    }
    
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', () => toggleAllCategories(true));
    }
    
    if (selectNoneBtn) {
        selectNoneBtn.addEventListener('click', () => toggleAllCategories(false));
    }
}

function toggleAllCategories(checked) {
    const checkboxes = document.querySelectorAll('.category-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = checked;
    });
}

async function startScrape() {
    const sessionType = document.getElementById('session-type')?.value || 'manual';
    const checkboxes = document.querySelectorAll('.category-checkbox:checked');
    const categories = Array.from(checkboxes).map(cb => cb.value);
    
    const payload = {
        session_type: sessionType,
        categories: categories.length > 0 ? categories : null
    };
    
    const startBtn = document.getElementById('start-scrape');
    if (startBtn) {
        startBtn.disabled = true;
        startBtn.textContent = 'Starting...';
    }
    
    try {
        const response = await fetch('/api/scraper/scrape', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        showNotification(`Scraping started: ${data.message} (Session: ${data.session_id})`, 'success');
        
        // Start polling for status
        pollScrapeStatus(data.session_id);
        
    } catch (err) {
        console.error('Error starting scrape:', err);
        showNotification('Error starting scrape: ' + err.message, 'error');
    } finally {
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.textContent = 'Start Scraping';
        }
    }
}

async function pollScrapeStatus(sessionId) {
    const statusEl = document.getElementById('scrape-status');
    if (!statusEl) return;
    
    statusEl.innerHTML = `
        <div class="scrape-progress">
            <p><strong>Status:</strong> <span id="scrape-status-text">starting...</span></p>
            <p><strong>Progress:</strong> <span id="scrape-progress">0/0</span> sources</p>
            <p><strong>Failed:</strong> <span id="scrape-failed">0</span></p>
            <p><strong>Total Articles:</strong> <span id="scrape-articles">0</span></p>
        </div>
    `;
    
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`/api/scraper/status/${sessionId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Update status display
            document.getElementById('scrape-status-text').textContent = data.status;
            document.getElementById('scrape-progress').textContent = 
                `${data.completed_sources || 0}/${data.total_sources || 0}`;
            document.getElementById('scrape-failed').textContent = data.failed_sources || 0;
            document.getElementById('scrape-articles').textContent = data.total_articles || 0;
            
            if (data.status === 'completed' || data.status === 'error') {
                clearInterval(interval);
                
                if (data.status === 'completed') {
                    showNotification('Scraping completed successfully!', 'success');
                } else {
                    showNotification('Scraping finished with errors', 'error');
                }
                
                // Reload dashboard to update stats
                setTimeout(() => {
                    if (typeof loadDashboardStats === 'function') {
                        loadDashboardStats();
                    }
                }, 1000);
            }
        } catch (err) {
            console.error('Status poll error:', err);
            clearInterval(interval);
            showNotification('Error checking scrape status: ' + err.message, 'error');
        }
    }, 3000);
}