// static/js/analysis.js - Simplified Analysis page (no priority articles)

document.addEventListener('DOMContentLoaded', function() {
    initializeAnalysisPage();
});

function initializeAnalysisPage() {
    setupAnalysisTabs();
    loadTrending(); // Load default tab
}

function setupAnalysisTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Update active tab button
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });
    
    // Update active tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const activeTab = document.getElementById(`${tabName}-tab`);
    if (activeTab) {
        activeTab.classList.add('active');
    }
    
    // Load tab-specific data
    switch(tabName) {
        case 'trending':
            loadTrending();
            break;
        case 'duplicates':
            loadDuplicates();
            break;
    }
}

async function loadTrending() {
    const contentEl = document.getElementById('trending-content');
    if (!contentEl) return;
    
    contentEl.innerHTML = '<p class="text-muted">Loading trending topics...</p>';
    
    try {
        const response = await fetch('/api/analysis/trending?hours=24&min_articles=3');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        contentEl.innerHTML = '';
        
        if (!data.trending_topics || data.trending_topics.length === 0) {
            contentEl.innerHTML = '<p class="no-results">No trending topics found in the last 24 hours</p>';
            return;
        }
        
        data.trending_topics.forEach(topic => {
            const topicEl = createTrendingTopic(topic);
            contentEl.appendChild(topicEl);
        });
        
    } catch (err) {
        console.error('Error loading trending topics:', err);
        contentEl.innerHTML = '<p class="no-results">Error loading trending topics</p>';
        showNotification('Error loading trending topics: ' + err.message, 'error');
    }
}

function createTrendingTopic(topic) {
    const topicEl = document.createElement('div');
    topicEl.className = 'trending-item fade-in';
    topicEl.innerHTML = `
        <h3>${escapeHtml(topic.keyword)}</h3>
        <div class="trending-meta">
            <p><strong>Article Count:</strong> ${topic.article_count}</p>
            <p><strong>Sources:</strong> ${topic.sources.join(', ')}</p>
        </div>
        <div class="sample-headlines">
            <p><strong>Sample Headlines:</strong></p>
            ${topic.sample_headlines.map(h => `<p class="sample">• ${escapeHtml(h)}</p>`).join('')}
        </div>
    `;
    return topicEl;
}

async function loadDuplicates() {
    const contentEl = document.getElementById('duplicates-content');
    if (!contentEl) return;
    
    contentEl.innerHTML = '<p class="text-muted">Detecting duplicates...</p>';
    
    try {
        const response = await fetch('/api/analysis/detect-duplicates', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        contentEl.innerHTML = '';
        
        if (!data.duplicate_groups || data.duplicate_groups.length === 0) {
            contentEl.innerHTML = '<p class="no-results">No duplicate articles found</p>';
            return;
        }
        
        data.duplicate_groups.forEach(group => {
            const groupEl = createDuplicateGroup(group);
            contentEl.appendChild(groupEl);
        });
        
    } catch (err) {
        console.error('Error loading duplicates:', err);
        contentEl.innerHTML = '<p class="no-results">Error detecting duplicates</p>';
        showNotification('Error loading duplicates: ' + err.message, 'error');
    }
}

function createDuplicateGroup(group) {
    const groupEl = document.createElement('div');
    groupEl.className = 'duplicate-group fade-in';
    groupEl.innerHTML = `
        <h3>Duplicate Group - ${group.count} similar articles</h3>
        <div class="duplicate-articles">
            ${group.articles.map(article => `
                <div class="duplicate-article">
                    <div class="duplicate-header">
                        <strong>${escapeHtml(article.source)}</strong>
                    </div>
                    <p class="duplicate-headline">${escapeHtml(article.headline)}</p>
                    <a href="${escapeHtml(article.link)}" target="_blank" rel="noopener" class="duplicate-link">View Article →</a>
                </div>
            `).join('')}
        </div>
    `;
    return groupEl;
}

// Helper function
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
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