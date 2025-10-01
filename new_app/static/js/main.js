    // static/js/main.js - Complete Frontend JavaScript
document.addEventListener('DOMContentLoaded', () => {
    // Initialize keyboard shortcuts
    if (window.AppUtils) {
        window.AppUtils.initKeyboardShortcuts();
    }

    // State management
    let currentPage = 1;
    const pageSize = 50;
    let currentCategory = '';
    let currentSource = '';
    let currentSearch = '';

    // Initialize app
    document.addEventListener('DOMContentLoaded', () => {
        initializeNavigation();
        loadDashboard();
        loadCategories();
        setupDatePickers();
    });

    // Navigation
    function initializeNavigation() {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.target.dataset.view;
                switchView(view);
            });
        });
        
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.target.dataset.tab;
                switchTab(tab);
            });
        });
    }

    function switchView(viewName) {
        // Update nav buttons
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.view === viewName) {
                btn.classList.add('active');
            }
        });
        
        // Update views
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active');
        });
        document.getElementById(`${viewName}-view`).classList.add('active');
        
        // Load view-specific data
        switch(viewName) {
            case 'dashboard':
                loadDashboard();
                break;
            case 'articles':
                loadArticles();
                break;
            case 'scraper':
                loadScraperView();
                break;
            case 'blacklist':
                loadBlacklist();
                break;
            case 'analysis':
                loadAnalysis();
                break;
        }
    }

    function switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            }
        });
        
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        // Load tab-specific data
        switch(tabName) {
            case 'trending':
                loadTrending();
                break;
            case 'duplicates':
                loadDuplicates();
                break;
            case 'priority':
                loadPriority();
                break;
        }
    }

    // Dashboard Functions
    async function loadDashboard() {
        try {
            const [stats, health] = await Promise.all([
                fetch('/api/articles/stats').then(r => r.json()),
                fetch('/health').then(r => r.json())
            ]);
            
            document.getElementById('total-articles').textContent = stats.total_articles;
            document.getElementById('articles-today').textContent = stats.articles_today;
            document.getElementById('selected-articles').textContent = stats.selected_articles;
            document.getElementById('scheduler-status').textContent = 
                health.scheduler_running ? '✓ Running' : '✗ Stopped';
            
            // Load recent sessions (placeholder)
            document.getElementById('recent-sessions').innerHTML = 
                '<p class="text-muted">No recent scraping sessions</p>';
        } catch (err) {
            showNotification('Error loading dashboard: ' + err.message, 'error');
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

    // Articles Functions
    async function loadCategories() {
        try {
            const response = await fetch('/api/scraper/categories');
            const data = await response.json();
            
            const select = document.getElementById('category-filter');
            select.innerHTML = '<option value="">All Categories</option>';
            data.categories.forEach(cat => {
                select.innerHTML += `<option value="${cat}">${cat}</option>`;
            });
        } catch (err) {
            console.error('Error loading categories:', err);
        }
    }

    async function loadArticles() {
        const search = document.getElementById('search-input').value;
        const category = document.getElementById('category-filter').value;
        const source = document.getElementById('source-filter').value;
        
        const skip = (currentPage - 1) * pageSize;
        let url = `/api/articles/?skip=${skip}&limit=${pageSize}`;
        
        if (category) url += `&category=${encodeURIComponent(category)}`;
        if (source) url += `&source=${encodeURIComponent(source)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        
        try {
            const response = await fetch(url);
            const data = await response.json();
            
            const listEl = document.getElementById('articles-list');
            listEl.innerHTML = '';
            
            if (data.articles.length === 0) {
                listEl.innerHTML = '<p class="no-results">No articles found</p>';
                return;
            }
            
            data.articles.forEach(article => {
                const articleEl = document.createElement('div');
                articleEl.className = 'article-item';
                articleEl.innerHTML = `
                    <div class="article-header">
                        <div class="article-headline">
                            <a href="${article.link}" target="_blank">${article.headline}</a>
                        </div>
                        <div class="article-actions">
                            <button class="btn-small" onclick="toggleSelect(${article.id}, ${!article.is_selected})">
                                ${article.is_selected ? '★' : '☆'}
                            </button>
                            <button class="btn-small btn-danger" onclick="addArticleToBlacklist('${article.link}')">
                                🚫
                            </button>
                        </div>
                    </div>
                    <div class="article-meta">
                        <span class="badge">${article.category}</span>
                        <span class="source">${article.source}</span>
                        <span class="date">${formatDate(article.date_scraped)}</span>
                        ${article.priority_score ? `<span class="priority">Priority: ${article.priority_score}</span>` : ''}
                    </div>
                `;
                listEl.appendChild(articleEl);
            });
            
            // Update pagination
            document.getElementById('page-info').textContent = 
                `Page ${currentPage} (${data.articles.length} of ${data.total})`;
        } catch (err) {
            showNotification('Error loading articles: ' + err.message, 'error');
        }
    }

    async function toggleSelect(articleId, selected) {
        try {
            await fetch(`/api/articles/${articleId}`, {
                method: 'PATCH',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({is_selected: selected})
            });
            loadArticles();
        } catch (err) {
            showNotification('Error updating article: ' + err.message, 'error');
        }
    }

    function prevPage() {
        if (currentPage > 1) {
            currentPage--;
            loadArticles();
        }
    }

    function nextPage() {
        currentPage++;
        loadArticles();
    }

    // Scraper Functions
    async function loadScraperView() {
        try {
            const response = await fetch('/api/scraper/categories');
            const data = await response.json();
            
            const container = document.getElementById('category-checkboxes');
            container.innerHTML = '';
            
            data.categories.forEach(cat => {
                container.innerHTML += `
                    <label class="checkbox-label">
                        <input type="checkbox" value="${cat}" class="category-checkbox">
                        ${cat}
                    </label>
                `;
            });
        } catch (err) {
            console.error('Error loading scraper view:', err);
        }
    }

    async function triggerScrape() {
        await startScrape();
    }

    async function startScrape() {
        const sessionType = document.getElementById('session-type').value;
        const checkboxes = document.querySelectorAll('.category-checkbox:checked');
        const categories = Array.from(checkboxes).map(cb => cb.value);
        
        const payload = {
            session_type: sessionType,
            categories: categories.length > 0 ? categories : null
        };
        
        try {
            const response = await fetch('/api/scraper/scrape', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            
            showNotification(data.message + ` (Session: ${data.session_id})`, 'success');
            
            // Poll for status
            pollScrapeStatus(data.session_id);
        } catch (err) {
            showNotification('Error starting scrape: ' + err.message, 'error');
        }
    }

    async function pollScrapeStatus(sessionId) {
        const statusEl = document.getElementById('scrape-status');
        
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/scraper/status/${sessionId}`);
                const data = await response.json();
                
                statusEl.innerHTML = `
                    <div class="scrape-progress">
                        <p><strong>Status:</strong> ${data.status}</p>
                        <p><strong>Progress:</strong> ${data.completed_sources}/${data.total_sources} sources</p>
                        <p><strong>Failed:</strong> ${data.failed_sources}</p>
                        <p><strong>Total Articles:</strong> ${data.total_articles}</p>
                    </div>
                `;
                
                if (data.status === 'completed') {
                    clearInterval(interval);
                    showNotification('Scraping completed!', 'success');
                    loadDashboard();
                }
            } catch (err) {
                clearInterval(interval);
                console.error('Status poll error:', err);
            }
        }, 3000);
    }

    // Blacklist Functions
    async function loadBlacklist() {
        try {
            const response = await fetch('/api/blacklist/?limit=200');
            const data = await response.json();
            
            const listEl = document.getElementById('blacklist-list');
            listEl.innerHTML = '<h2>Blacklisted Patterns</h2>';
            
            if (data.length === 0) {
                listEl.innerHTML += '<p class="no-results">No blacklist entries</p>';
                return;
            }
            
            data.forEach(entry => {
                const entryEl = document.createElement('div');
                entryEl.className = 'blacklist-item';
                entryEl.innerHTML = `
                    <div class="blacklist-pattern">${entry.url_pattern}</div>
                    <div class="blacklist-meta">
                        ${entry.reason ? `<span class="reason">${entry.reason}</span>` : ''}
                        <span class="date">${formatDate(entry.date_added)}</span>
                        <button class="btn-small btn-danger" onclick="removeFromBlacklist(${entry.id})">Remove</button>
                    </div>
                `;
                listEl.appendChild(entryEl);
            });
            
            // Add export button
            listEl.innerHTML += `
                <button class="action-btn" onclick="exportBlacklist()" style="margin-top: 20px;">
                    💾 Export Blacklist to JSON
                </button>
            `;
        } catch (err) {
            showNotification('Error loading blacklist: ' + err.message, 'error');
        }
    }

    async function addToBlacklist() {
        const pattern = document.getElementById('blacklist-pattern').value;
        const reason = document.getElementById('blacklist-reason').value;
        
        if (!pattern) {
            showNotification('Please enter a URL pattern', 'error');
            return;
        }
        
        try {
            await fetch('/api/blacklist/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url_pattern: pattern, reason: reason})
            });
            
            document.getElementById('blacklist-pattern').value = '';
            document.getElementById('blacklist-reason').value = '';
            showNotification('Pattern added to blacklist', 'success');
            loadBlacklist();
        } catch (err) {
            showNotification('Error adding to blacklist: ' + err.message, 'error');
        }
    }

    async function addArticleToBlacklist(url) {
        if (!confirm(`Add ${url} to blacklist?`)) return;
        
        try {
            await fetch('/api/blacklist/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    url_pattern: url,
                    reason: 'Added from article view'
                })
            });
            showNotification('Added to blacklist', 'success');
        } catch (err) {
            showNotification('Error: ' + err.message, 'error');
        }
    }

    async function removeFromBlacklist(id) {
        if (!confirm('Remove this pattern from blacklist?')) return;
        
        try {
            await fetch(`/api/blacklist/${id}`, {method: 'DELETE'});
            showNotification('Pattern removed', 'success');
            loadBlacklist();
        } catch (err) {
            showNotification('Error: ' + err.message, 'error');
        }
    }

    async function exportBlacklist() {
        try {
            const response = await fetch('/api/blacklist/sync-db-to-json', {
                method: 'POST'
            });
            const data = await response.json();
            showNotification(data.message + ' - Check blacklists/ directory', 'success');
        } catch (err) {
            showNotification('Export failed: ' + err.message, 'error');
        }
    }

    // Analysis Functions
    async function loadAnalysis() {
        loadTrending();
    }

    async function loadTrending() {
        try {
            const response = await fetch('/api/analysis/trending?hours=24&min_articles=3');
            const data = await response.json();
            
            const tabEl = document.getElementById('trending-tab');
            tabEl.innerHTML = '<h2>Trending Topics (Last 24 Hours)</h2>';
            
            if (data.trending_topics.length === 0) {
                tabEl.innerHTML += '<p class="no-results">No trending topics found</p>';
                return;
            }
            
            data.trending_topics.forEach(topic => {
                const topicEl = document.createElement('div');
                topicEl.className = 'trending-item';
                topicEl.innerHTML = `
                    <h3>${topic.keyword}</h3>
                    <p><strong>Articles:</strong> ${topic.article_count}</p>
                    <p><strong>Sources:</strong> ${topic.sources.join(', ')}</p>
                    <div class="sample-headlines">
                        ${topic.sample_headlines.map(h => `<p class="sample">• ${h}</p>`).join('')}
                    </div>
                `;
                tabEl.appendChild(topicEl);
            });
        } catch (err) {
            showNotification('Error loading trending topics: ' + err.message, 'error');
        }
    }

    async function loadDuplicates() {
        try {
            const response = await fetch('/api/analysis/detect-duplicates', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            const data = await response.json();
            
            const tabEl = document.getElementById('duplicates-tab');
            tabEl.innerHTML = '<h2>Duplicate Article Groups</h2>';
            
            if (data.duplicate_groups.length === 0) {
                tabEl.innerHTML += '<p class="no-results">No duplicates found</p>';
                return;
            }
            
            data.duplicate_groups.forEach(group => {
                const groupEl = document.createElement('div');
                groupEl.className = 'duplicate-group';
                groupEl.innerHTML = `
                    <h3>Group of ${group.count} similar articles</h3>
                    ${group.articles.map(a => `
                        <div class="duplicate-article">
                            <p><strong>${a.source}:</strong> ${a.headline}</p>
                            <a href="${a.link}" target="_blank">View Article</a>
                        </div>
                    `).join('')}
                `;
                tabEl.appendChild(groupEl);
            });
        } catch (err) {
            showNotification('Error loading duplicates: ' + err.message, 'error');
        }
    }

    async function loadPriority() {
        try {
            const response = await fetch('/api/analysis/prioritize', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            const data = await response.json();
            
            const tabEl = document.getElementById('priority-tab');
            tabEl.innerHTML = '<h2>Prioritized Articles</h2>';
            
            if (data.prioritized_articles.length === 0) {
                tabEl.innerHTML += '<p class="no-results">No articles to prioritize</p>';
                return;
            }
            
            data.prioritized_articles.forEach(article => {
                const articleEl = document.createElement('div');
                articleEl.className = 'priority-article';
                articleEl.innerHTML = `
                    <div class="priority-header">
                        <div class="priority-score">${article.priority_score}</div>
                        <div class="priority-content">
                            <h4><a href="${article.link}" target="_blank">${article.headline}</a></h4>
                            <p><span class="badge">${article.category}</span> ${article.source}</p>
                        </div>
                    </div>
                `;
                tabEl.appendChild(articleEl);
            });
        } catch (err) {
            showNotification('Error loading priority articles: ' + err.message, 'error');
        }
    }

    // Utility Functions
    function setupDatePickers() {
        // Simple date inputs - browsers will provide native date pickers
        const dateInputs = document.querySelectorAll('input[type="date"]');
        dateInputs.forEach(input => {
            if (!input.value) {
                input.value = new Date().toISOString().split('T')[0];
            }
        });
    }

    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function showNotification(message, type = 'info') {
        const notification = document.getElementById('notification');
        notification.textContent = message;
        notification.className = `notification ${type} show`;
        
        setTimeout(() => {
            notification.classList.remove('show');
        }, 5000);
    }
});