// static/js/articles.js - Articles page with infinite scroll

document.addEventListener('DOMContentLoaded', function() {
    initializeArticlesPage();
});

let currentArticles = [];
let selectedArticles = new Set();
let isLoading = false;
let hasMore = true;
let currentSkip = 0;
const LOAD_LIMIT = 50;
let currentFilters = {};

function initializeArticlesPage() {
    setupFilterForm();
    loadInitialArticles();
    setupInfiniteScroll();
}

async function loadInitialArticles() {
    currentSkip = 0;
    hasMore = true;
    currentArticles = [];
    selectedArticles.clear();
    
    const listEl = document.getElementById('articles-list');
    if (!listEl) return;
    
    listEl.innerHTML = '<h2>Articles</h2><div id="articles-table-container"></div>';
    
    await loadMoreArticles();
}

async function loadMoreArticles() {
    if (isLoading || !hasMore) return;
    
    isLoading = true;
    showLoadingIndicator();
    
    try {
        const queryString = new URLSearchParams({
            limit: LOAD_LIMIT,
            skip: currentSkip,
            category: currentFilters.category || '',
            source: currentFilters.source || ''
        }).toString();
        
        const response = await fetch(`/api/articles/?${queryString}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.articles && data.articles.length > 0) {
            appendArticles(data.articles);
            currentSkip += data.articles.length;
            
            // Check if there are more articles to load
            hasMore = currentSkip < data.total;
        } else {
            hasMore = false;
        }
        
        updateArticleCount(data.total);
        
    } catch (err) {
        console.error('Error loading articles:', err);
        showNotification('Error loading articles: ' + err.message, 'error');
        hasMore = false;
    } finally {
        isLoading = false;
        hideLoadingIndicator();
    }
}

function appendArticles(articles) {
    const container = document.getElementById('articles-table-container');
    if (!container) return;
    
    let table = container.querySelector('.articles-table');
    let tbody;
    
    // Create table if it doesn't exist
    if (!table) {
        table = document.createElement('table');
        table.className = 'articles-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th class="select-col">
                        <input type="checkbox" id="select-all-checkbox" onchange="toggleSelectAll(this.checked)">
                    </th>
                    <th class="title-col">Article Title</th>
                    <th class="search-col">Search</th>
                    <th class="source-col">Source</th>
                    <th class="category-col">Category</th>
                    <th class="date-col">Published Date</th>
                    <th class="status-col">Status</th>
                </tr>
            </thead>
            <tbody id="articles-table-body"></tbody>
        `;
        container.appendChild(table);
        
        // Add action buttons after table
        const actionContainer = document.createElement('div');
        actionContainer.className = 'articles-actions';
        actionContainer.innerHTML = `
            <button onclick="openSelectedArticles()" class="btn btn-primary" id="open-selected-btn" disabled>Open Selected</button>
            <button onclick="blacklistSelectedArticles()" class="btn btn-danger" id="blacklist-selected-btn" disabled>Blacklist Selected</button>
            <button onclick="searchSelectedArticles()" class="btn btn-info" id="search-selected-btn" disabled>Search Selected</button>
            <button onclick="selectAllArticles()" class="btn btn-secondary" id="select-all-btn">Select All</button>
            <button onclick="deselectAllArticles()" class="btn btn-secondary" id="deselect-all-btn">Deselect All</button>
        `;
        container.appendChild(actionContainer);
    }
    
    tbody = table.querySelector('#articles-table-body');
    
    // Append new articles
    articles.forEach(article => {
        currentArticles.push(article);
        const row = createArticleRow(article);
        tbody.appendChild(row);
    });
}

function createArticleRow(article) {
    const row = document.createElement('tr');
    row.className = 'article-row';
    row.dataset.articleId = article.id;
    
    const publishedDate = article.date_published || article.date_scraped;
    const searchUrl = generateSearchUrl(article.headline);
    
    row.innerHTML = `
        <td class="select-col">
            <input type="checkbox" class="article-checkbox" value="${article.id}" onchange="toggleArticleSelection(${article.id}, this.checked)">
        </td>
        <td class="title-col">
            <a href="${escapeHtml(article.link)}" target="_blank" class="article-link">${escapeHtml(article.headline)}</a>
        </td>
        <td class="search-col">
            <a href="${searchUrl}" target="_blank" class="search-link" title="Search for this article">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <path d="m21 21-4.3-4.3"></path>
                </svg>
            </a>
        </td>
        <td class="source-col">${escapeHtml(article.source)}</td>
        <td class="category-col">${escapeHtml(article.category)}</td>
        <td class="date-col">${formatDate(publishedDate)}</td>
        <td class="status-col">
            ${article.is_duplicate ? '<span class="badge duplicate">Duplicate</span>' : ''}
            ${article.is_selected ? '<span class="badge selected">Selected</span>' : ''}
        </td>
    `;
    
    return row;
}

function setupInfiniteScroll() {
    const container = document.getElementById('articles-table-container');
    if (!container) return;
    
    // Create intersection observer for infinite scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !isLoading && hasMore) {
                loadMoreArticles();
            }
        });
    }, {
        root: container,
        rootMargin: '100px',
        threshold: 0.1
    });
    
    // Observe the loading indicator
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
        observer.observe(loadingIndicator);
    }
}

function showLoadingIndicator() {
    let indicator = document.getElementById('loading-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'loading-indicator';
        indicator.className = 'loading-indicator';
        indicator.innerHTML = '<div class="spinner"></div><p>Loading more articles...</p>';
        
        const container = document.getElementById('articles-table-container');
        if (container) {
            container.appendChild(indicator);
        }
    }
    indicator.style.display = 'flex';
}

function hideLoadingIndicator() {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) {
        if (!hasMore) {
            indicator.innerHTML = '<p>No more articles to load</p>';
            setTimeout(() => {
                indicator.style.display = 'none';
            }, 2000);
        } else {
            indicator.style.display = 'none';
        }
    }
}

function updateArticleCount(total) {
    let countEl = document.getElementById('article-count');
    if (!countEl) {
        countEl = document.createElement('div');
        countEl.id = 'article-count';
        countEl.className = 'article-count';
        const listEl = document.getElementById('articles-list');
        if (listEl) {
            listEl.insertBefore(countEl, listEl.querySelector('#articles-table-container'));
        }
    }
    countEl.textContent = `Showing ${currentArticles.length} of ${total} articles`;
}

function generateSearchUrl(headline) {
    const searchQuery = headline.trim();
    return `https://www.google.com/search?q=${encodeURIComponent(searchQuery)}`;
}

function toggleArticleSelection(articleId, isSelected) {
    if (isSelected) {
        selectedArticles.add(articleId);
    } else {
        selectedArticles.delete(articleId);
    }
    updateActionButtons();
}

function toggleSelectAll(isSelected) {
    const checkboxes = document.querySelectorAll('.article-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = isSelected;
        const articleId = parseInt(checkbox.value);
        if (isSelected) {
            selectedArticles.add(articleId);
        } else {
            selectedArticles.delete(articleId);
        }
    });
    updateActionButtons();
}

function selectAllArticles() {
    const checkboxes = document.querySelectorAll('.article-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
        selectedArticles.add(parseInt(checkbox.value));
    });
    updateActionButtons();
}

function deselectAllArticles() {
    const checkboxes = document.querySelectorAll('.article-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    selectedArticles.clear();
    updateActionButtons();
}

function updateActionButtons() {
    const openBtn = document.getElementById('open-selected-btn');
    const blacklistBtn = document.getElementById('blacklist-selected-btn');
    const searchBtn = document.getElementById('search-selected-btn');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    
    const hasSelection = selectedArticles.size > 0;
    
    if (openBtn) openBtn.disabled = !hasSelection;
    if (blacklistBtn) blacklistBtn.disabled = !hasSelection;
    if (searchBtn) searchBtn.disabled = !hasSelection;
    
    if (selectAllCheckbox) {
        const totalVisible = document.querySelectorAll('.article-checkbox').length;
        selectAllCheckbox.checked = selectedArticles.size === totalVisible && totalVisible > 0;
        selectAllCheckbox.indeterminate = selectedArticles.size > 0 && selectedArticles.size < totalVisible;
    }
}

function openSelectedArticles() {
    if (selectedArticles.size === 0) return;
    
    currentArticles.forEach(article => {
        if (selectedArticles.has(article.id)) {
            window.open(article.link, '_blank');
        }
    });
    
    showNotification(`Opened ${selectedArticles.size} articles in new tabs`, 'success');
}

function searchSelectedArticles() {
    if (selectedArticles.size === 0) return;
    
    currentArticles.forEach(article => {
        if (selectedArticles.has(article.id)) {
            const searchUrl = generateSearchUrl(article.headline);
            window.open(searchUrl, '_blank');
        }
    });
    
    showNotification(`Searched for ${selectedArticles.size} articles in new tabs`, 'success');
}

async function blacklistSelectedArticles() {
    if (selectedArticles.size === 0) return;
    
    if (!confirm(`Blacklist ${selectedArticles.size} selected articles?`)) {
        return;
    }
    
    try {
        const urlsToBlacklist = currentArticles
            .filter(article => selectedArticles.has(article.id))
            .map(article => article.link);
        
        const response = await fetch('/api/blacklist/bulk-add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                patterns: urlsToBlacklist,
                reason: 'Blacklisted via articles page (bulk)'
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        showNotification(result.message, 'success');
        deselectAllArticles();
        
    } catch (err) {
        showNotification('Error blacklisting articles: ' + err.message, 'error');
    }
}

function setupFilterForm() {
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;
    
    const newSearchInput = searchInput.cloneNode(true);
    searchInput.parentNode.replaceChild(newSearchInput, searchInput);
    
    let searchTimeout;
    newSearchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            const searchTerm = e.target.value.trim().toLowerCase();
            filterArticlesLocally(searchTerm);
        }, 300);
    });
    
    newSearchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const searchTerm = e.target.value.trim().toLowerCase();
            filterArticlesLocally(searchTerm);
        }
    });
}

function filterArticlesLocally(searchTerm) {
    const rows = document.querySelectorAll('.article-row');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const titleCell = row.querySelector('.title-col');
        if (!titleCell) return;
        
        const title = titleCell.textContent.toLowerCase();
        
        if (!searchTerm || title.includes(searchTerm)) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    const tbody = document.getElementById('articles-table-body');
    const existingMsg = tbody?.querySelector('.no-results-row');
    
    if (visibleCount === 0 && searchTerm && tbody) {
        if (!existingMsg) {
            const noResultsRow = document.createElement('tr');
            noResultsRow.className = 'no-results-row';
            noResultsRow.innerHTML = '<td colspan="7" style="text-align: center; padding: 20px;">No articles match your search</td>';
            tbody.appendChild(noResultsRow);
        }
    } else if (existingMsg) {
        existingMsg.remove();
    }
}

function clearFilters() {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = '';
        filterArticlesLocally('');
    }
}

function applyFilters() {
    const category = document.getElementById('category-filter')?.value;
    const source = document.getElementById('source-filter')?.value.trim();
    
    currentFilters = { category, source };
    selectedArticles.clear();
    loadInitialArticles();
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

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