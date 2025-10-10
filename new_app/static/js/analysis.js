// static/js/analysis.js - Complete fixed version
document.addEventListener('DOMContentLoaded', function() {
    initializeAnalysisPage();
});

function initializeAnalysisPage() {
    // Load the default timeframe (24 hours)
    loadTrendingKeywords();
}

// Timeframe switching function
function switchTimeframe(timeframe) {
    console.log('Switching to timeframe:', timeframe);
    
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === timeframe) {
            btn.classList.add('active');
        }
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const tabElement = document.getElementById(`${timeframe}-tab`);
    if (tabElement) {
        tabElement.classList.add('active');
    }
    
    // Load content for the timeframe if not already loaded
    const contentEl = document.getElementById(`${timeframe}-content`);
    if (contentEl && (contentEl.innerHTML.includes('Click "Refresh"') || contentEl.innerHTML.includes('Loading'))) {
        loadTrendingKeywords();
    }
}

// Load trending keywords by timeframe
async function loadTrendingKeywords() {
    try {
        const response = await fetch('/api/analysis/trending-keywords?min_articles=3');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        displayTrendingKeywords(data);
        
    } catch (err) {
        console.error('Error loading trending keywords:', err);
        showNotification('Error loading trending keywords: ' + err.message, 'error');
        
        // Show error in all tabs
        ['24h', '48h', '7d', '30d'].forEach(timeframe => {
            const contentEl = document.getElementById(`${timeframe}-content`);
            if (contentEl) {
                contentEl.innerHTML = '<p class="error-text">Failed to load trending keywords</p>';
            }
        });
    }
}

function displayTrendingKeywords(data) {
    const timeframes = ['24h', '48h', '7d', '30d'];
    
    timeframes.forEach(timeframe => {
        const keywords = data.trending_keywords[timeframe] || [];
        const contentEl = document.getElementById(`${timeframe}-content`);
        
        if (!contentEl) return;
        
        contentEl.innerHTML = '';
        
        if (keywords.length === 0) {
            contentEl.innerHTML = '<p class="no-results">No trending keywords found for this timeframe</p>';
            return;
        }
        
        // Create keywords grid
        const keywordsGrid = document.createElement('div');
        keywordsGrid.className = 'keywords-grid';
        
        keywords.forEach(keyword => {
            const keywordCard = createKeywordCard(keyword);
            keywordsGrid.appendChild(keywordCard);
        });
        
        contentEl.appendChild(keywordsGrid);
    });
}

function createKeywordCard(keyword) {
    const card = document.createElement('div');
    card.className = 'keyword-card';
    
    // Create clickable keyword that opens articles page with search
    const keywordLink = document.createElement('a');
    keywordLink.href = `/articles?search=${encodeURIComponent(keyword.keyword)}`;
    keywordLink.className = 'keyword-link';
    keywordLink.target = '_blank';
    keywordLink.textContent = keyword.keyword;
    keywordLink.title = `Search for "${keyword.keyword}" in articles`;
    
    const stats = document.createElement('div');
    stats.className = 'keyword-stats';
    stats.innerHTML = `
        <span class="stat-item">
            <span class="stat-label">Articles:</span>
            <span class="stat-value">${keyword.article_count}</span>
        </span>
        <span class="stat-item">
            <span class="stat-label">Sources:</span>
            <span class="stat-value">${keyword.source_count}</span>
        </span>
    `;
    
    // Show sample sources if available
    if (keyword.sources && keyword.sources.length > 0) {
        const sources = document.createElement('div');
        sources.className = 'keyword-sources';
        sources.textContent = `Sources: ${keyword.sources.join(', ')}`;
        card.appendChild(keywordLink);
        card.appendChild(stats);
        card.appendChild(sources);
    } else {
        card.appendChild(keywordLink);
        card.appendChild(stats);
    }
    
    return card;
}

// Notification function
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'error' ? '#dc2626' : type === 'success' ? '#16a34a' : '#3b82f6'};
        color: white;
        border-radius: 4px;
        z-index: 10000;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    `;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}