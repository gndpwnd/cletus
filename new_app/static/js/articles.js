// static/js/articles.js - Articles page functionality

document.addEventListener('DOMContentLoaded', function() {
    initializeArticlesPage();
});

let currentArticles = [];
let selectedArticles = new Set();

function initializeArticlesPage() {
    loadArticles();
    setupFilterForm();
}

async function loadArticles(params = {}) {
    try {
        // Build query string from parameters
        const queryString = new URLSearchParams({
            limit: params.limit || 50,
            skip: params.skip || 0,
            category: params.category || '',
            source: params.source || ''
        }).toString();
        
        const response = await fetch(`/api/articles/?${queryString}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        const listEl = document.getElementById('articles-list');
        if (!listEl) return;
        
        // Store current articles for selection
        currentArticles = data.articles || [];
        
        listEl.innerHTML = '<h2>Articles</h2>';
        
        if (!currentArticles || currentArticles.length === 0) {
            listEl.innerHTML += '<p class="no-results">No articles found</p>';
            return;
        }
        
        // Update pagination
        updatePagination(data.total, data.skip, data.limit);
        
        // Create articles table
        const table = createArticlesTable(currentArticles);
        listEl.appendChild(table);
        
        // Add action buttons container
        const actionContainer = document.createElement('div');
        actionContainer.className = 'articles-actions';
        actionContainer.innerHTML = `
            <button onclick="openSelectedArticles()" class="btn btn-primary" id="open-selected-btn" disabled>Open Selected</button>
            <button onclick="blacklistSelectedArticles()" class="btn btn-danger" id="blacklist-selected-btn" disabled>Blacklist Selected</button>
            <button onclick="searchSelectedArticles()" class="btn btn-info" id="search-selected-btn" disabled>Search Selected</button>
            <button onclick="selectAllArticles()" class="btn btn-secondary" id="select-all-btn">Select All</button>
            <button onclick="deselectAllArticles()" class="btn btn-secondary" id="deselect-all-btn">Deselect All</button>
        `;
        listEl.appendChild(actionContainer);
        
    } catch (err) {
        console.error('Error loading articles:', err);
        showNotification('Error loading articles: ' + err.message, 'error');
    }
}

function createArticlesTable(articles) {
    const table = document.createElement('table');
    table.className = 'articles-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th class="select-col"><input type="checkbox" id="select-all-checkbox" onchange="toggleSelectAll(this.checked)"></th>
                <th class="title-col">Article Title</th>
                <th class="search-col">Search</th>
                <th class="source-col">Source</th>
                <th class="category-col">Category</th>
                <th class="date-col">Published Date</th>
                <th class="status-col">Status</th>
            </tr>
        </thead>
        <tbody id="articles-table-body">
        </tbody>
    `;
    
    const tbody = table.querySelector('#articles-table-body');
    
    articles.forEach(article => {
        const row = createArticleRow(article);
        tbody.appendChild(row);
    });
    
    return table;
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

function generateSearchUrl(headline) {
    // Clean the headline for search - just encode the entire string properly
    // This will handle spaces and special characters correctly
    const searchQuery = headline.trim();
    
    // Use Google search with proper URL encoding
    // Spaces will be encoded as %20, not as +
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
    
    // Update select all checkbox state
    if (selectAllCheckbox) {
        const totalArticles = document.querySelectorAll('.article-checkbox').length;
        selectAllCheckbox.checked = selectedArticles.size === totalArticles && totalArticles > 0;
        selectAllCheckbox.indeterminate = selectedArticles.size > 0 && selectedArticles.size < totalArticles;
    }
}

function openSelectedArticles() {
    if (selectedArticles.size === 0) return;
    
    // Open each selected article in a new tab
    currentArticles.forEach(article => {
        if (selectedArticles.has(article.id)) {
            window.open(article.link, '_blank');
        }
    });
    
    showNotification(`Opened ${selectedArticles.size} articles in new tabs`, 'success');
}

function searchSelectedArticles() {
    if (selectedArticles.size === 0) return;
    
    // Search for each selected article in new tabs
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
    
    if (!confirm(`Blacklist ${selectedArticles.size} selected articles? This will add their URLs to the blacklist.`)) {
        return;
    }
    
    try {
        const urlsToBlacklist = [];
        
        currentArticles.forEach(article => {
            if (selectedArticles.has(article.id)) {
                urlsToBlacklist.push(article.link);
            }
        });
        
        // Use bulk add endpoint if available, otherwise add one by one
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
        
        // Clear selection after blacklisting
        deselectAllArticles();
        
    } catch (err) {
        showNotification('Error blacklisting articles: ' + err.message, 'error');
    }
}

function setupFilterForm() {
    const searchInput = document.getElementById('search-input');
    const categoryFilter = document.getElementById('category-filter');
    const sourceFilter = document.getElementById('source-filter');
    
    // Add event listeners for real-time filtering or apply on enter
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                loadArticles();
            }
        });
    }
    
    if (sourceFilter) {
        sourceFilter.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                loadArticles();
            }
        });
    }
}

function applyFilters() {
    const search = document.getElementById('search-input')?.value.trim();
    const category = document.getElementById('category-filter')?.value;
    const source = document.getElementById('source-filter')?.value.trim();
    
    // Reset selection when filters change
    selectedArticles.clear();
    
    loadArticles({
        category,
        source,
        skip: 0 // Reset to first page
    });
}

function clearFilters() {
    document.getElementById('search-input').value = '';
    document.getElementById('category-filter').value = '';
    document.getElementById('source-filter').value = '';
    
    // Reset selection when clearing filters
    selectedArticles.clear();
    
    loadArticles({ skip: 0 });
}

function updatePagination(total, skip, limit) {
    const pageEl = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    
    if (!pageEl || !prevBtn || !nextBtn) return;
    
    const currentPage = Math.floor(skip / limit) + 1;
    const totalPages = Math.ceil(total / limit);
    
    pageEl.textContent = `Page ${currentPage} of ${totalPages}`;
    
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
    
    prevBtn.onclick = () => {
        selectedArticles.clear(); // Clear selection when changing pages
        loadArticles({ skip: Math.max(0, skip - limit) });
    };
    
    nextBtn.onclick = () => {
        selectedArticles.clear(); // Clear selection when changing pages
        loadArticles({ skip: skip + limit });
    };
}

// Helper functions
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
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

function showNotification(message, type) {
    // Basic notification implementation
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}