document.addEventListener('DOMContentLoaded', function() {
    var authNav = document.getElementById('authNav');
    if (!authNav) return;

    function renderGuest() {
        authNav.innerHTML =
            '<a href="/login" class="btn btn-sm btn-outline-light">Log In</a>' +
            '<a href="/register" class="btn btn-sm btn-success">Register</a>';
    }

    function renderUser(user) {
        var adminLink = user.role === 'admin'
            ? '<li><a href="/admin" class="dropdown-item"><i class="bi bi-speedometer2 me-2"></i>Admin</a></li>'
            : '';
        var adminPanelButton = user.role === 'admin'
            ? '<a href="/admin" class="btn btn-sm btn-success admin-panel-shortcut"><i class="bi bi-speedometer2 me-1"></i>Admin Panel</a>'
            : '';
        authNav.innerHTML =
            adminPanelButton +
            '<div class="dropdown">' +
            '<button class="btn btn-sm btn-outline-light dropdown-toggle" type="button" data-bs-toggle="dropdown">' +
            '<i class="bi bi-person-circle me-1"></i>' + escapeAuthHtml(user.full_name || user.email) +
            '</button>' +
            '<ul class="dropdown-menu dropdown-menu-end">' +
            '<li><a href="/account" class="dropdown-item"><i class="bi bi-grid-1x2 me-2"></i>Account</a></li>' +
            '<li><a href="/account/orders" class="dropdown-item"><i class="bi bi-receipt me-2"></i>Orders</a></li>' +
            '<li><a href="/account/support" class="dropdown-item"><i class="bi bi-life-preserver me-2"></i>Support</a></li>' +
            adminLink +
            '<li><hr class="dropdown-divider"></li>' +
            '<li><button type="button" class="dropdown-item" id="customerLogoutBtn"><i class="bi bi-box-arrow-right me-2"></i>Log Out</button></li>' +
            '</ul>' +
            '</div>';

        var logoutBtn = document.getElementById('customerLogoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', function() {
                fetch('/api/auth/logout', { method: 'POST' }).then(function() {
                    window.location.href = '/';
                });
            });
        }
    }

    fetch('/api/auth/me')
        .then(function(r) {
            if (!r.ok) throw new Error('guest');
            return r.json();
        })
        .then(renderUser)
        .catch(renderGuest);
});

function escapeAuthHtml(value) {
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
