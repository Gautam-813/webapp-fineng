var accountState = {
    user: null,
    orderPage: {
        page: 1,
        pageSize: 10,
        total: 0,
        pages: 1
    }
};

document.addEventListener('DOMContentLoaded', function() {
    initAccountPortal();
});

function initAccountPortal() {
    var shell = document.querySelector('[data-account-page]');
    if (!shell) return;

    bindAccountLogout();

    loadAccountUser()
        .then(function(user) {
            accountState.user = user;
            populateAccountIdentity(user);
            var page = shell.dataset.accountPage;
            if (page === 'dashboard') return initDashboard();
            if (page === 'orders') return initOrdersPage();
            if (page === 'profile') return initProfilePage();
            if (page === 'support') return initSupportPage();
            if (page === 'projects') return initProjectsPage();
        })
        .catch(function(err) {
            if (err.message === 'Not authenticated') {
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                return;
            }
            showAlert('Error: ' + err.message, 'danger');
        });
}

function loadAccountUser() {
    return fetch('/api/account/profile')
        .then(function(r) {
            if (!r.ok) throw new Error('Not authenticated');
            return r.json();
        });
}

function populateAccountIdentity(user) {
    setText('accountName', user.full_name || user.email);
    setText('accountEmail', user.email);

    var nameFields = ['profileFullName', 'supportName', 'projectName'];
    nameFields.forEach(function(id) {
        var el = document.getElementById(id);
        if (el && !el.value) el.value = user.full_name || '';
    });

    var emailFields = ['profileEmail', 'supportEmail', 'projectEmail'];
    emailFields.forEach(function(id) {
        var el = document.getElementById(id);
        if (el && !el.value) el.value = user.email || '';
    });

    var phoneFields = ['profilePhone', 'projectPhone'];
    phoneFields.forEach(function(id) {
        var el = document.getElementById(id);
        if (el && !el.value) el.value = user.phone || '';
    });
}

function bindAccountLogout() {
    document.querySelectorAll('[data-account-logout]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            fetch('/api/auth/logout', { method: 'POST' }).then(function() {
                window.location.href = '/';
            });
        });
    });
}

function initDashboard() {
    return loadAccountOrders(1, 5)
        .then(function(data) {
            renderAccountStats(data.stats || {});
            renderRecentOrders(data.items || []);
        });
}

function initOrdersPage() {
    document.getElementById('accountStatusFilter')?.addEventListener('change', function() {
        loadOrdersPage(1);
    });
    document.getElementById('accountPageSize')?.addEventListener('change', function() {
        loadOrdersPage(1);
    });
    document.getElementById('accountPrevPage')?.addEventListener('click', function() {
        if (accountState.orderPage.page > 1) loadOrdersPage(accountState.orderPage.page - 1);
    });
    document.getElementById('accountNextPage')?.addEventListener('click', function() {
        if (accountState.orderPage.page < accountState.orderPage.pages) loadOrdersPage(accountState.orderPage.page + 1);
    });
    return loadOrdersPage(1);
}

function loadOrdersPage(page) {
    var container = document.getElementById('accountOrdersList');
    if (container) {
        container.innerHTML = '<p class="text-muted small mb-0">Loading orders...</p>';
    }
    var pageSize = Number(document.getElementById('accountPageSize')?.value || 10);
    return loadAccountOrders(page || accountState.orderPage.page, pageSize)
        .then(function(data) {
            accountState.orderPage.page = data.page || 1;
            accountState.orderPage.pageSize = data.page_size || pageSize;
            accountState.orderPage.total = data.total || 0;
            accountState.orderPage.pages = data.pages || 1;
            renderAccountStats(data.stats || {});
            renderAccountOrders(data.items || []);
            updateAccountPagination();
        });
}

function loadAccountOrders(page, pageSize) {
    var params = new URLSearchParams({
        page: page || accountState.orderPage.page,
        page_size: pageSize || document.getElementById('accountPageSize')?.value || '10'
    });
    var status = document.getElementById('accountStatusFilter')?.value || '';
    if (status) params.set('status', status);

    return fetch('/api/account/orders?' + params.toString())
        .then(function(r) {
            if (!r.ok) throw new Error('Unable to load orders');
            return r.json();
        });
}

function renderAccountStats(stats) {
    setText('accountOrderCount', stats.total_orders || 0);
    setText('accountConfirmedCount', stats.confirmed_orders || 0);
    setText('accountPaidCount', stats.paid_orders || 0);
    setText('accountOrderValue', formatAccountMoney(stats.order_value));
}

function renderRecentOrders(orders) {
    var container = document.getElementById('accountRecentOrders');
    if (!container) return;
    if (!orders.length) {
        container.innerHTML = accountEmptyState('bi-bag', 'No orders yet', 'Browse products and complete demo checkout to create your first order.', '/products', 'Browse Products');
        return;
    }
    container.innerHTML = orders.map(orderRowHtml).join('');
}

function renderAccountOrders(orders) {
    var container = document.getElementById('accountOrdersList');
    if (!container) return;
    if (!orders.length) {
        container.innerHTML = accountEmptyState('bi-bag', 'No orders found', 'Complete demo checkout or adjust the status filter.', '/products', 'Browse Products');
        return;
    }
    container.innerHTML = orders.map(orderRowHtml).join('');
}

function orderRowHtml(order) {
    var items = order.items || [];
    var itemSummary = items.map(function(item) {
        return escapeAccountHtml(item.product_name) + ' x' + item.quantity;
    }).join(', ');
    return '<div class="account-order-row">' +
        '<div>' +
        '<div class="d-flex align-items-center gap-2 flex-wrap mb-1">' +
        '<strong>Order #' + order.id + '</strong>' + statusBadge(order.status) +
        '</div>' +
        '<p class="text-muted small mb-1">' + escapeAccountHtml(itemSummary || 'No items') + '</p>' +
        '<span class="text-muted small">' + formatAccountDate(order.created_at) + '</span>' +
        '</div>' +
        '<div class="text-lg-end">' +
        '<strong class="d-block">' + formatAccountMoney(order.total_amount) + '</strong>' +
        '<span class="text-muted small">' + escapeAccountHtml(order.currency || 'USD') + '</span>' +
        '</div>' +
        '</div>';
}

function updateAccountPagination() {
    var start = accountState.orderPage.total ? ((accountState.orderPage.page - 1) * accountState.orderPage.pageSize) + 1 : 0;
    var end = Math.min(accountState.orderPage.page * accountState.orderPage.pageSize, accountState.orderPage.total);
    setText('accountPageSummary', 'Showing ' + start + '-' + end + ' of ' + accountState.orderPage.total + ' orders');
    setText('accountCurrentPage', 'Page ' + accountState.orderPage.page + ' of ' + accountState.orderPage.pages);

    var prev = document.getElementById('accountPrevPage');
    var next = document.getElementById('accountNextPage');
    if (prev) prev.disabled = accountState.orderPage.page <= 1;
    if (next) next.disabled = accountState.orderPage.page >= accountState.orderPage.pages;
}

function initProfilePage() {
    return fetch('/api/account/profile')
        .then(function(r) {
            if (!r.ok) throw new Error('Unable to load profile');
            return r.json();
        })
        .then(function(profile) {
            populateAccountIdentity(profile);
            renderProfileStatus(profile);
            bindProfileForm();
        });
}

function bindProfileForm() {
    var form = document.getElementById('accountProfileForm');
    if (!form) return;
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }
        var btn = document.getElementById('profileSaveBtn');
        setAccountButton(btn, true, 'Saving...');
        fetch('/api/account/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                full_name: document.getElementById('profileFullName').value.trim(),
                phone: document.getElementById('profilePhone').value.trim()
            })
        })
        .then(function(r) {
            if (!r.ok) return r.json().then(function(err) { throw new Error(err.detail || 'Unable to save profile'); });
            return r.json();
        })
        .then(function(profile) {
            accountState.user = profile;
            populateAccountIdentity(profile);
            renderProfileStatus(profile);
            showAlert('Profile updated successfully.', 'success');
            setAccountButton(btn, false, '<i class="bi bi-check2-circle me-1"></i>Save Profile');
        })
        .catch(function(err) {
            showAlert('Error: ' + err.message, 'danger');
            setAccountButton(btn, false, '<i class="bi bi-check2-circle me-1"></i>Save Profile');
        });
    });
}

function renderProfileStatus(profile) {
    var panel = document.getElementById('profileStatusPanel');
    if (!panel) return;
    panel.innerHTML =
        '<div class="account-info-row"><span>Email</span><strong>' + escapeAccountHtml(profile.email) + '</strong></div>' +
        '<div class="account-info-row"><span>Role</span><strong>' + escapeAccountHtml(profile.role || 'customer') + '</strong></div>' +
        '<div class="account-info-row"><span>Status</span><strong>' + escapeAccountHtml(profile.status || 'active') + '</strong></div>' +
        '<div class="account-info-row"><span>Created</span><strong>' + formatAccountDate(profile.created_at) + '</strong></div>';
}

function initSupportPage() {
    bindSupportForm();
    return Promise.all([
        loadSupportRequests(),
        Promise.resolve(populateAccountIdentity(accountState.user || {}))
    ]);
}

function bindSupportForm() {
    var form = document.getElementById('accountSupportForm');
    if (!form) return;
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }
        var btn = document.getElementById('supportSubmitBtn');
        setAccountButton(btn, true, 'Sending...');
        fetch('/api/contact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: document.getElementById('supportName').value.trim(),
                email: document.getElementById('supportEmail').value.trim(),
                subject: document.getElementById('supportSubject').value.trim(),
                message: document.getElementById('supportMessage').value.trim(),
                service_type: document.getElementById('supportServiceType').value || 'product_support'
            })
        })
        .then(function(r) {
            if (!r.ok) return r.json().then(function(err) { throw new Error(err.detail || 'Unable to send support request'); });
            return r.json();
        })
        .then(function(data) {
            form.reset();
            form.classList.remove('was-validated');
            populateAccountIdentity(accountState.user || {});
            showAlert(data.message || 'Support request sent.', 'success');
            setAccountButton(btn, false, '<i class="bi bi-send me-1"></i>Send Support Request');
            return loadSupportRequests();
        })
        .catch(function(err) {
            showAlert('Error: ' + err.message, 'danger');
            setAccountButton(btn, false, '<i class="bi bi-send me-1"></i>Send Support Request');
        });
    });
}

function loadSupportRequests() {
    return fetch('/api/account/support?page=1&page_size=10')
        .then(function(r) {
            if (!r.ok) throw new Error('Unable to load support requests');
            return r.json();
        })
        .then(function(data) {
            renderSupportRequests(data.items || []);
        });
}

function renderSupportRequests(items) {
    var container = document.getElementById('accountSupportList');
    if (!container) return;
    if (!items.length) {
        container.innerHTML = accountEmptyState('bi-life-preserver', 'No support requests yet', 'Send a request when you need setup, order, or product help.', '', '');
        return;
    }
    container.innerHTML = items.map(function(item) {
        return '<div class="account-ticket-row">' +
            '<div class="d-flex justify-content-between gap-2 flex-wrap mb-1">' +
            '<strong>' + escapeAccountHtml(item.subject || item.service_type || 'Support request') + '</strong>' +
            statusBadge(item.status) +
            '</div>' +
            '<p class="text-muted small mb-1">' + escapeAccountHtml(trimAccountText(item.message, 120)) + '</p>' +
            '<span class="text-muted small">' + formatAccountDate(item.created_at) + '</span>' +
            '</div>';
    }).join('');
}

function initProjectsPage() {
    bindProjectForm();
    populateAccountIdentity(accountState.user || {});
    return loadProjectRequests();
}

function bindProjectForm() {
    var form = document.getElementById('accountProjectForm');
    if (!form) return;
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }
        var btn = document.getElementById('projectSubmitBtn');
        setAccountButton(btn, true, 'Submitting...');
        fetch('/api/custom-project-request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: document.getElementById('projectName').value.trim(),
                email: document.getElementById('projectEmail').value.trim(),
                phone: document.getElementById('projectPhone').value.trim(),
                company: document.getElementById('projectCompany').value.trim(),
                project_type: document.getElementById('projectType').value,
                budget_range: document.getElementById('projectBudget').value,
                timeline: document.getElementById('projectTimeline').value.trim(),
                description: document.getElementById('projectDescription').value.trim()
            })
        })
        .then(function(r) {
            if (!r.ok) return r.json().then(function(err) { throw new Error(err.detail || 'Unable to submit project request'); });
            return r.json();
        })
        .then(function(data) {
            form.reset();
            form.classList.remove('was-validated');
            populateAccountIdentity(accountState.user || {});
            showAlert(data.message || 'Project request submitted.', 'success');
            setAccountButton(btn, false, '<i class="bi bi-code-slash me-1"></i>Submit Project Request');
            return loadProjectRequests();
        })
        .catch(function(err) {
            showAlert('Error: ' + err.message, 'danger');
            setAccountButton(btn, false, '<i class="bi bi-code-slash me-1"></i>Submit Project Request');
        });
    });
}

function loadProjectRequests() {
    return fetch('/api/account/projects?page=1&page_size=10')
        .then(function(r) {
            if (!r.ok) throw new Error('Unable to load project requests');
            return r.json();
        })
        .then(function(data) {
            renderProjectStats(data.stats || {});
            renderProjectRequests(data.items || []);
        });
}

function renderProjectStats(stats) {
    setText('projectTotal', stats.total_projects || 0);
    setText('projectNew', stats.new_projects || 0);
    setText('projectInProgress', stats.in_progress_projects || 0);
    setText('projectCompleted', stats.completed_projects || 0);
}

function renderProjectRequests(items) {
    var container = document.getElementById('accountProjectsList');
    if (!container) return;
    if (!items.length) {
        container.innerHTML = accountEmptyState('bi-tools', 'No project requests yet', 'Submit a custom software brief when you are ready.', '', '');
        return;
    }
    container.innerHTML = items.map(function(item) {
        return '<div class="account-ticket-row">' +
            '<div class="d-flex justify-content-between gap-2 flex-wrap mb-1">' +
            '<strong>' + escapeAccountHtml(item.project_type || 'Custom project') + '</strong>' +
            statusBadge(item.status) +
            '</div>' +
            '<p class="text-muted small mb-1">' + escapeAccountHtml(trimAccountText(item.description, 130)) + '</p>' +
            '<div class="d-flex gap-2 flex-wrap text-muted small">' +
            '<span>' + escapeAccountHtml(item.budget_range || 'Budget open') + '</span>' +
            '<span>' + escapeAccountHtml(item.timeline || 'Timeline open') + '</span>' +
            '</div>' +
            '<span class="text-muted small d-block mt-1">' + formatAccountDate(item.created_at) + '</span>' +
            '</div>';
    }).join('');
}

function accountEmptyState(icon, title, message, href, label) {
    var action = href && label ? '<a href="' + href + '" class="btn btn-primary btn-sm">' + escapeAccountHtml(label) + '</a>' : '';
    return '<div class="account-empty-state">' +
        '<i class="bi ' + icon + '"></i>' +
        '<h3 class="h6 fw-bold mb-1">' + escapeAccountHtml(title) + '</h3>' +
        '<p class="text-muted small mb-3">' + escapeAccountHtml(message) + '</p>' +
        action +
        '</div>';
}

function statusBadge(status) {
    var normalized = status || 'pending';
    var badgeClass = (normalized === 'paid' || normalized === 'confirmed' || normalized === 'completed') ? 'success'
        : (normalized === 'pending' || normalized === 'new' || normalized === 'in_progress') ? 'warning'
        : (normalized === 'failed' || normalized === 'cancelled') ? 'danger'
        : 'secondary';
    return '<span class="badge bg-' + badgeClass + ' bg-opacity-10 text-' + badgeClass + ' small">' + escapeAccountHtml(normalized.replace(/_/g, ' ')) + '</span>';
}

function setAccountButton(btn, loading, label) {
    if (!btn) return;
    btn.disabled = loading;
    btn.innerHTML = loading ? '<span class="spinner-border spinner-border-sm me-2"></span>' + label : label;
}

function setText(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatAccountMoney(value) {
    return '$' + parseFloat(value || 0).toFixed(2);
}

function formatAccountDate(value) {
    return value ? new Date(value).toLocaleString() : 'Unknown date';
}

function trimAccountText(value, maxLength) {
    var text = String(value || '');
    return text.length > maxLength ? text.slice(0, maxLength - 1) + '...' : text;
}

function escapeAccountHtml(value) {
    return String(value || '').replace(/[&<>"']/g, function(ch) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[ch];
    });
}
