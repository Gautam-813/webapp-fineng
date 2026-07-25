var CART_SESSION_KEY = 'tfc_cart_session_id';

function getCartSessionId() {
    var sessionId = localStorage.getItem(CART_SESSION_KEY);
    if (!sessionId) {
        sessionId = 'cart_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2);
        localStorage.setItem(CART_SESSION_KEY, sessionId);
    }
    return sessionId;
}

function cartApiUrl(path) {
    return '/api/cart' + path + '?session_id=' + encodeURIComponent(getCartSessionId());
}

function escapeCartHtml(value) {
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

function getCart() {
    return fetch(cartApiUrl(''))
        .then(function(r) {
            if (!r.ok) throw new Error('Unable to load cart');
            return r.json();
        })
        .then(function(cart) {
            return cart.items || [];
        })
        .catch(function() {
            return [];
        });
}

function updateCartBadge() {
    return getCart().then(function(cart) {
        var badge = document.getElementById('cartBadge');
        if (!badge) return;
        var count = cart.reduce(function(sum, item) { return sum + (item.quantity || 1); }, 0);
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline';
        } else {
            badge.style.display = 'none';
        }
    });
}

function addToCart(data) {
    var productId = parseInt(data.productId);
    var productName = data.productName || 'Product';

    return fetch(cartApiUrl('/items'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            product_id: productId,
            quantity: 1
        })
    })
    .then(function(r) {
        if (!r.ok) return r.json().then(function(err) { throw new Error(err.detail || 'Could not add item'); });
        return r.json();
    })
    .then(function() {
        updateCartBadge();
        showAlert('Added <strong>' + escapeCartHtml(productName) + '</strong> to cart!', 'success');
    })
    .catch(function(err) {
        showAlert('Error: ' + err.message, 'danger');
    });
}

function removeFromCart(productId) {
    return getCart()
        .then(function(cart) {
            var item = cart.find(function(i) { return i.product_id === productId; });
            if (!item) return;
            return fetch(cartApiUrl('/items/' + item.item_id), { method: 'DELETE' })
                .then(function(r) {
                    if (!r.ok && r.status !== 204) throw new Error('Unable to remove item');
                });
        })
        .then(function() {
            updateCartBadge();
            renderCartPage();
        })
        .catch(function(err) {
            showAlert('Error: ' + err.message, 'danger');
        });
}

function clearCart() {
    return fetch(cartApiUrl(''), { method: 'DELETE' })
        .then(function() {
            localStorage.removeItem('tfc_cart');
            return updateCartBadge();
        });
}

function getCartTotal() {
    return getCart().then(function(cart) {
        return cart.reduce(function(sum, item) {
            return sum + (parseFloat(item.unit_price) * (item.quantity || 1));
        }, 0);
    });
}

function renderCartPage() {
    var container = document.getElementById('cartItemsList');
    var emptyMsg = document.getElementById('emptyCartMessage');
    var subtotalEl = document.getElementById('cartSubtotal');
    var totalEl = document.getElementById('cartTotal');
    var checkoutBtn = document.getElementById('checkoutBtn');
    var itemSummary = document.getElementById('cartItemSummary');

    if (!container) return;

    container.innerHTML = '<div class="text-muted small py-3">Loading cart...</div>';
    container.style.display = 'block';

    getCart().then(function(cart) {
        if (cart.length === 0) {
            container.style.display = 'none';
            if (emptyMsg) emptyMsg.style.display = 'block';
            if (subtotalEl) subtotalEl.textContent = '$0.00';
            if (totalEl) totalEl.textContent = '$0.00';
            if (checkoutBtn) checkoutBtn.style.display = 'none';
            if (itemSummary) itemSummary.textContent = '0 items';
            return;
        }

        if (emptyMsg) emptyMsg.style.display = 'none';
        container.style.display = 'block';

        var html = '';
        var subtotal = 0;
        var count = 0;

        cart.forEach(function(item) {
            var total = parseFloat(item.unit_price) * (item.quantity || 1);
            var thumb = item.thumbnail_url
                ? '<img src="' + escapeCartHtml(item.thumbnail_url) + '" alt="' + escapeCartHtml(item.name) + '">'
                : '<i class="bi bi-box"></i>';
            subtotal += total;
            count += item.quantity || 1;
            html +=
                '<div class="cart-line-item">' +
                '<div class="cart-item-media">' + thumb + '</div>' +
                '<div class="cart-item-main">' +
                '<h6 class="fw-bold mb-1">' + escapeCartHtml(item.name) + '</h6>' +
                '<div class="text-muted small">$' + parseFloat(item.unit_price).toFixed(2) + ' each</div>' +
                '</div>' +
                '<div class="cart-qty-control input-group input-group-sm">' +
                '<button class="btn btn-outline-secondary" type="button" onclick="updateCartQty(' + item.product_id + ', -1)">-</button>' +
                '<input type="text" class="form-control text-center" value="' + (item.quantity || 1) + '" readonly style="background: #fff;">' +
                '<button class="btn btn-outline-secondary" type="button" onclick="updateCartQty(' + item.product_id + ', 1)">+</button>' +
                '</div>' +
                '<div class="cart-line-total fw-bold">$' + total.toFixed(2) + '</div>' +
                '<button class="btn btn-sm btn-outline-danger cart-remove-btn" onclick="removeFromCart(' + item.product_id + ')" title="Remove">' +
                '<i class="bi bi-trash"></i>' +
                '</button>' +
                '</div>';
        });

        container.innerHTML = html;

        if (subtotalEl) subtotalEl.textContent = '$' + subtotal.toFixed(2);
        if (totalEl) totalEl.textContent = '$' + subtotal.toFixed(2);
        if (checkoutBtn) checkoutBtn.style.display = 'block';
        if (itemSummary) itemSummary.textContent = count + (count === 1 ? ' item' : ' items');
    });
}

function updateCartQty(productId, delta) {
    return getCart()
        .then(function(cart) {
            var item = cart.find(function(i) { return i.product_id === productId; });
            if (!item) return;
            var quantity = Math.max(1, (item.quantity || 1) + delta);
            return fetch(cartApiUrl('/items/' + item.item_id), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ quantity: quantity })
            }).then(function(r) {
                if (!r.ok) throw new Error('Unable to update quantity');
            });
        })
        .then(function() {
            updateCartBadge();
            renderCartPage();
        })
        .catch(function(err) {
            showAlert('Error: ' + err.message, 'danger');
        });
}

document.addEventListener('DOMContentLoaded', updateCartBadge);
