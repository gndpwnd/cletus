// static/js/analysis.js - Analysis page functionality

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
            switchAnalysisTab(tabName);
        });
    });
}

function switchAnalysisTab(tabName) {
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
        case 'priority':
            loadPriority();
            break;
    }
}

async function loadTrending() {
    try {
        const response = await fetch('/api/analysis/trending?hours=24&min_articles=3');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        const tabEl = document.getElementById('trending-tab');
        if (!tabEl) return;
        
        tabEl.innerHTML = '<h2>Trending Topics (Last 24 Hours)</h2>';
        
        if (!data.trending_topics || data.trending_topics.length === 0) {
            tabEl.innerHTML += '<p class="no-results">No trending topics found</p>';
            return;
        }
        
        data.trending_topics.forEach(topic => {
            const topicEl = createTrendingTopic(topic);
            tabEl.appendChild(topicEl);
        });
        
    } catch (err) {
        console.error('Error loading trending topics:', err);
        showNotification('Error loading trending topics: ' + err.message, 'error');
    }
}

function createTrendingTopic(topic) {
    const topicEl = document.createElement('div');
    topicEl.className = 'trending-item';
    topicEl.innerHTML = `
        <h3>${escapeHtml(topic.keyword)}</h3>
        <p><strong>Articles:</strong> ${topic.article_count}</p>
        <p><strong>Sources:</strong> ${topic.sources.join(', ')}</p>
        <div class="sample-headlines">
            ${topic.sample_headlines.map(h => `<p class="sample">• ${escapeHtml(h)}</p>`).join('')}
        </div>
    `;
    return topicEl;
}

async function loadDuplicates() {
    try {
        const response = await fetch('/api/analysis/detect-duplicates', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        const tabEl = document.getElementById('duplicates-tab');
        if (!tabEl) return;
        
        tabEl.innerHTML = '<h2>Duplicate Article Groups</h2>';
        
        if (!data.duplicate_groups || data.duplicate_groups.length === 0) {
            tabEl.innerHTML += '<p class="no-results">No duplicates found</p>';
            return;
        }
        
        data.duplicate_groups.forEach(group => {
            const groupEl = createDuplicateGroup(group);
            tabEl.appendChild(groupEl);
        });
        
    } catch (err) {
        console.error('Error loading duplicates:', err);
        showNotification('Error loading duplicates: ' + err.message, 'error');
    }
}

function createDuplicateGroup(group) {
    const groupEl = document.createElement('div');
    groupEl.className = 'duplicate-group';
    groupEl.innerHTML = `
        <h3>Group of ${group.count} similar articles</h3>
        ${group.articles.map(article => `
            <div class="duplicate-article">
                <p><strong>${escapeHtml(article.source)}:</strong> ${escapeHtml(article.headline)}</p>
                <a href="${article.link}" target="_blank" rel="noopener">View Article</a>
            </div>
        `).join('')}
    `;
    return groupEl;
}

async function loadPriority() {
    try {
        const response = await fetch('/api/analysis/prioritize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        const tabEl = document.getElementById('priority-tab');
        if (!tabEl) return;
        
        tabEl.innerHTML = '<h2>Prioritized Articles</h2>';
        
        if (!data.prioritized_articles || data.prioritized_articles.length === 0) {
            tabEl.innerHTML += '<p class="no-results">No articles to prioritize</p>';
            return;
        }
        
        data.prioritized_articles.forEach(article => {
            const articleEl = createPriorityArticle(article);
            tabEl.appendChild(articleEl);
        });
        
    } catch (err) {
        console.error('Error loading priority articles:', err);
        showNotification('Error loading priority articles: ' + err.message, 'error');
    }
}

function createPriorityArticle(article) {
    const articleEl = document.createElement('div');
    articleEl.className = 'priority-article';
    articleEl.innerHTML = `
        <div class="priority-header">
            <div class="priority-score">${article.priority_score.toFixed(1)}</div>
            <div class="priority-content">
                <h4><a href="${article.link}" target="_blank" rel="noopener">${escapeHtml(article.headline)}</a></h4>
                <p><span class="badge">${article.category}</span> ${article.source}</p>
            </div>
        </div>
    `;
    return articleEl;
}

// Helper function
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}