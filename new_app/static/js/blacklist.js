// static/js/blacklist.js - Blacklist page functionality

document.addEventListener('DOMContentLoaded', function() {
    initializeBlacklistPage();
});

function initializeBlacklistPage() {
    loadBlacklist();
    setupBlacklistForm();
}

async function loadBlacklist() {
    try {
        const response = await fetch('/api/blacklist/?limit=200');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        const listEl = document.getElementById('blacklist-list');
        if (!listEl) return;
        
        listEl.innerHTML = '<h2>Blacklisted Patterns</h2>';
        
        if (!data || data.length === 0) {
            listEl.innerHTML += '<p class="no-results">No blacklist entries</p>';
            return;
        }
        
        data.forEach(entry => {
            const entryEl = createBlacklistEntry(entry);
            listEl.appendChild(entryEl);
        });
        
        // Add export button
        const exportBtn = document.createElement('button');
        exportBtn.className = 'action-btn';
        exportBtn.innerHTML = '💾 Export Blacklist to JSON';
        exportBtn.onclick = exportBlacklist;
        exportBtn.style.marginTop = '20px';
        listEl.appendChild(exportBtn);
        
    } catch (err) {
        console.error('Error loading blacklist:', err);
        showNotification('Error loading blacklist: ' + err.message, 'error');
    }
}

function createBlacklistEntry(entry) {
    const entryEl = document.createElement('div');
    entryEl.className = 'blacklist-item';
    entryEl.innerHTML = `
        <div class="blacklist-pattern">${escapeHtml(entry.url_pattern)}</div>
        <div class="blacklist-meta">
            ${entry.reason ? `<span class="reason">${entry.reason}</span>` : ''}
            <span class="date">${formatDate(entry.date_added)}</span>
            <button class="btn-small btn-danger" onclick="removeFromBlacklist(${entry.id})">Remove</button>
        </div>
    `;
    return entryEl;
}

function setupBlacklistForm() {
    const form = document.getElementById('add-blacklist-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            addToBlacklist();
        });
    }
}

async function addToBlacklist() {
    const patternInput = document.getElementById('blacklist-pattern');
    const reasonInput = document.getElementById('blacklist-reason');
    
    const pattern = patternInput?.value.trim();
    const reason = reasonInput?.value.trim();
    
    if (!pattern) {
        showNotification('Please enter a URL pattern', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/blacklist/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                url_pattern: pattern,
                reason: reason || 'Added via web interface'
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Clear form
        if (patternInput) patternInput.value = '';
        if (reasonInput) reasonInput.value = '';
        
        showNotification('Pattern added to blacklist', 'success');
        loadBlacklist(); // Reload the list
        
    } catch (err) {
        showNotification('Error adding to blacklist: ' + err.message, 'error');
    }
}

async function removeFromBlacklist(id) {
    if (!confirm('Remove this pattern from blacklist?')) return;
    
    try {
        const response = await fetch(`/api/blacklist/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        showNotification('Pattern removed from blacklist', 'success');
        loadBlacklist(); // Reload the list
        
    } catch (err) {
        showNotification('Error removing from blacklist: ' + err.message, 'error');
    }
}

async function exportBlacklist() {
    try {
        const response = await fetch('/api/blacklist/sync-db-to-json', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        showNotification(data.message + ' - Check blacklists/ directory', 'success');
        
    } catch (err) {
        showNotification('Export failed: ' + err.message, 'error');
    }
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