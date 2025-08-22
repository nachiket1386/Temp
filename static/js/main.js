/**
 * Main JavaScript file for Labour Attendance Management System
 * Handles common functionality across all pages
 */

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeCommonFeatures();
    initializeFormValidation();
    initializeTooltips();
    initializeModals();
    initializeTableFeatures();
});

/**
 * Initialize common features
 */
function initializeCommonFeatures() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // Add loading states to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing...';
            }
        });
    });

    // Initialize date inputs with appropriate constraints
    initializeDateInputs();
}

/**
 * Initialize date inputs with constraints
 */
function initializeDateInputs() {
    const today = new Date().toISOString().split('T')[0];
    
    // Set max date to today for past date inputs
    const pastDateInputs = document.querySelectorAll('input[type="date"][data-max="today"]');
    pastDateInputs.forEach(input => {
        input.max = today;
    });

    // Set min date to today for future date inputs
    const futureDateInputs = document.querySelectorAll('input[type="date"][data-min="today"]');
    futureDateInputs.forEach(input => {
        input.min = today;
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    // Custom validation for password confirmation
    const passwordInputs = document.querySelectorAll('input[name="new_password"]');
    const confirmInputs = document.querySelectorAll('input[name="confirm_password"]');
    
    if (passwordInputs.length && confirmInputs.length) {
        confirmInputs.forEach(confirmInput => {
            confirmInput.addEventListener('input', function() {
                const passwordInput = document.querySelector('input[name="new_password"]');
                if (passwordInput && this.value !== passwordInput.value) {
                    this.setCustomValidity('Passwords do not match');
                } else {
                    this.setCustomValidity('');
                }
            });
        });
    }

    // Validate date ranges
    const dateFromInputs = document.querySelectorAll('input[name="date_from"]');
    const dateToInputs = document.querySelectorAll('input[name="date_to"]');
    
    dateFromInputs.forEach(fromInput => {
        fromInput.addEventListener('change', validateDateRange);
    });
    
    dateToInputs.forEach(toInput => {
        toInput.addEventListener('change', validateDateRange);
    });
}

/**
 * Validate date range inputs
 */
function validateDateRange() {
    const form = this.closest('form');
    if (!form) return;
    
    const fromInput = form.querySelector('input[name="date_from"]');
    const toInput = form.querySelector('input[name="date_to"]');
    
    if (fromInput && toInput && fromInput.value && toInput.value) {
        if (new Date(toInput.value) < new Date(fromInput.value)) {
            toInput.setCustomValidity('End date cannot be before start date');
        } else {
            toInput.setCustomValidity('');
        }
    }
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(tooltipTriggerEl => {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize modal functionality
 */
function initializeModals() {
    // Clear modal forms when hidden
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('hidden.bs.modal', function() {
            const forms = this.querySelectorAll('form');
            forms.forEach(form => {
                form.reset();
                form.classList.remove('was-validated');
                
                // Clear custom validation messages
                const inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    input.setCustomValidity('');
                });
            });
        });
    });
}

/**
 * Initialize table features
 */
function initializeTableFeatures() {
    // Add sorting capability to tables
    const sortableTables = document.querySelectorAll('.table-sortable');
    sortableTables.forEach(table => {
        initializeTableSorting(table);
    });

    // Add row selection for bulk operations
    const selectableTables = document.querySelectorAll('.table-selectable');
    selectableTables.forEach(table => {
        initializeTableSelection(table);
    });
}

/**
 * Initialize table sorting
 */
function initializeTableSorting(table) {
    const headers = table.querySelectorAll('th[data-sortable]');
    
    headers.forEach(header => {
        header.style.cursor = 'pointer';
        header.innerHTML += ' <i class="bi bi-arrow-down-up text-muted"></i>';
        
        header.addEventListener('click', function() {
            const column = this.dataset.sortable;
            const currentSort = this.dataset.sort || 'none';
            
            // Reset all other headers
            headers.forEach(h => {
                if (h !== this) {
                    h.dataset.sort = 'none';
                    const icon = h.querySelector('.bi');
                    if (icon) {
                        icon.className = 'bi bi-arrow-down-up text-muted';
                    }
                }
            });
            
            // Toggle current header
            let newSort, iconClass;
            if (currentSort === 'none' || currentSort === 'desc') {
                newSort = 'asc';
                iconClass = 'bi bi-arrow-up text-primary';
            } else {
                newSort = 'desc';
                iconClass = 'bi bi-arrow-down text-primary';
            }
            
            this.dataset.sort = newSort;
            const icon = this.querySelector('.bi');
            if (icon) {
                icon.className = iconClass;
            }
            
            // Perform sorting (this would typically trigger a server request)
            sortTable(table, column, newSort);
        });
    });
}

/**
 * Sort table rows
 */
function sortTable(table, column, direction) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aCell = a.querySelector(`td[data-sort="${column}"]`);
        const bCell = b.querySelector(`td[data-sort="${column}"]`);
        
        if (!aCell || !bCell) return 0;
        
        const aValue = aCell.dataset.value || aCell.textContent.trim();
        const bValue = bCell.dataset.value || bCell.textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aValue);
        const bNum = parseFloat(bValue);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return direction === 'asc' ? aNum - bNum : bNum - aNum;
        }
        
        // Compare as strings
        return direction === 'asc' 
            ? aValue.localeCompare(bValue)
            : bValue.localeCompare(aValue);
    });
    
    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Initialize table row selection
 */
function initializeTableSelection(table) {
    const selectAllCheckbox = table.querySelector('th input[type="checkbox"]');
    const rowCheckboxes = table.querySelectorAll('td input[type="checkbox"]');
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            rowCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBulkActionButtons();
        });
    }
    
    rowCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateSelectAllState();
            updateBulkActionButtons();
        });
    });
}

/**
 * Update select all checkbox state
 */
function updateSelectAllState() {
    const table = document.querySelector('.table-selectable');
    if (!table) return;
    
    const selectAllCheckbox = table.querySelector('th input[type="checkbox"]');
    const rowCheckboxes = table.querySelectorAll('td input[type="checkbox"]');
    
    if (selectAllCheckbox && rowCheckboxes.length) {
        const checkedCount = Array.from(rowCheckboxes).filter(cb => cb.checked).length;
        
        selectAllCheckbox.checked = checkedCount === rowCheckboxes.length;
        selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < rowCheckboxes.length;
    }
}

/**
 * Update bulk action buttons
 */
function updateBulkActionButtons() {
    const table = document.querySelector('.table-selectable');
    if (!table) return;
    
    const rowCheckboxes = table.querySelectorAll('td input[type="checkbox"]');
    const checkedCount = Array.from(rowCheckboxes).filter(cb => cb.checked).length;
    
    const bulkActions = document.querySelectorAll('.bulk-action');
    bulkActions.forEach(action => {
        action.disabled = checkedCount === 0;
    });
    
    const selectionCount = document.querySelector('.selection-count');
    if (selectionCount) {
        selectionCount.textContent = checkedCount;
    }
}

/**
 * CSV File Upload Enhancement
 */
function initializeCSVUpload() {
    const fileInput = document.querySelector('input[type="file"][accept=".csv"]');
    const uploadArea = document.querySelector('.csv-upload-area');
    
    if (!fileInput || !uploadArea) return;
    
    // Drag and drop functionality
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].name.endsWith('.csv')) {
            fileInput.files = files;
            displaySelectedFile(files[0]);
        }
    });
    
    // File input change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            displaySelectedFile(this.files[0]);
        }
    });
}

/**
 * Display selected file information
 */
function displaySelectedFile(file) {
    const info = document.querySelector('.file-info');
    if (info) {
        info.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-file-earmark-text"></i>
                <strong>${file.name}</strong> (${formatFileSize(file.size)})
            </div>
        `;
    }
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Notification Management
 */
function initializeNotifications() {
    // Auto-refresh notification count
    setInterval(refreshNotificationCount, 30000); // Every 30 seconds
    
    // Mark notification as read on click
    const notificationLinks = document.querySelectorAll('.notification-item');
    notificationLinks.forEach(link => {
        link.addEventListener('click', function() {
            const notificationId = this.dataset.notificationId;
            if (notificationId) {
                markNotificationAsRead(notificationId);
            }
        });
    });
}

/**
 * Refresh notification count
 */
function refreshNotificationCount() {
    fetch('/api/notifications/count')
        .then(response => response.json())
        .then(data => {
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                if (data.count > 0) {
                    badge.textContent = data.count > 99 ? '99+' : data.count;
                    badge.style.display = 'inline';
                } else {
                    badge.style.display = 'none';
                }
            }
        })
        .catch(error => {
            console.error('Failed to refresh notification count:', error);
        });
}

/**
 * Mark notification as read
 */
function markNotificationAsRead(notificationId) {
    fetch(`/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => {
        if (response.ok) {
            refreshNotificationCount();
        }
    })
    .catch(error => {
        console.error('Failed to mark notification as read:', error);
    });
}

/**
 * Get CSRF token from page
 */
function getCSRFToken() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    return csrfToken ? csrfToken.getAttribute('content') : '';
}

/**
 * Utility Functions
 */

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Format date for display
function formatDate(dateString, format = 'YYYY-MM-DD') {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Invalid Date';
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    switch (format) {
        case 'DD-MM-YYYY':
            return `${day}-${month}-${year}`;
        case 'MM/DD/YYYY':
            return `${month}/${day}/${year}`;
        default:
            return `${year}-${month}-${day}`;
    }
}

// Format time for display
function formatTime(timeString) {
    if (!timeString) return '--';
    
    const [hours, minutes] = timeString.split(':');
    const hour12 = parseInt(hours) % 12 || 12;
    const ampm = parseInt(hours) >= 12 ? 'PM' : 'AM';
    
    return `${hour12}:${minutes} ${ampm}`;
}

// Show loading state
function showLoading(element) {
    element.classList.add('loading');
    element.disabled = true;
}

// Hide loading state
function hideLoading(element) {
    element.classList.remove('loading');
    element.disabled = false;
}

// Show toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Create toast container if it doesn't exist
function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

// Initialize page-specific features based on current page
function initializePageFeatures() {
    const path = window.location.pathname;
    
    if (path.includes('/import')) {
        initializeCSVUpload();
    }
    
    if (path.includes('/notifications')) {
        initializeNotifications();
    }
    
    // Add more page-specific initializations as needed
}

// Initialize page features when DOM is ready
document.addEventListener('DOMContentLoaded', initializePageFeatures);

// Export functions for use in templates
window.LAMS = {
    showToast,
    formatDate,
    formatTime,
    showLoading,
    hideLoading,
    markNotificationAsRead,
    debounce
};
