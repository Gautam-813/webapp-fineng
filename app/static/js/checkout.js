document.addEventListener('DOMContentLoaded', function() {
    var form = document.getElementById('checkoutForm');
    if (!form) return;

    var nameInput = document.getElementById('customerName');
    var emailInput = document.getElementById('customerEmail');
    var submitBtn = document.getElementById('placeOrderBtn');
    var checkoutSummary = document.getElementById('checkoutSummary');
    var checkoutItems = document.getElementById('checkoutItems');
    var checkoutTotal = document.getElementById('checkoutTotal');
    var orderTotalText = document.getElementById('orderTotalText');

    fetch('/api/auth/me')
        .then(function(r) {
            if (!r.ok) throw new Error('guest');
            return r.json();
        })
        .then(function(user) {
            if (nameInput && !nameInput.value) nameInput.value = user.full_name || '';
            if (emailInput) {
                emailInput.value = user.email || '';
                emailInput.readOnly = true;
            }
            var authNote = document.getElementById('checkoutAuthNote');
            var guestNote = document.getElementById('checkoutGuestNote');
            if (authNote) {
                authNote.classList.remove('d-none');
                authNote.textContent = 'Signed in as ' + user.email + '. This order will be attached to your account.';
            }
            if (guestNote) guestNote.classList.add('d-none');
        })
        .catch(function() {});

    function renderCheckoutCart() {
        var cartContainer = document.getElementById('checkoutCartItems');
        if (!cartContainer) return Promise.resolve([]);

        cartContainer.innerHTML = '<p class="text-muted small">Loading cart...</p>';

        return getCart().then(function(cart) {
            if (cart.length === 0) {
                cartContainer.innerHTML =
                    '<div class="empty-state text-center p-4">' +
                    '<i class="bi bi-cart3 d-block text-muted mb-3" style="font-size: 2.25rem;"></i>' +
                    '<h6 class="fw-bold mb-1">Your cart is empty</h6>' +
                    '<p class="text-muted small mb-3">Add an EA, copier, indicator, or automation tool before placing an order.</p>' +
                    '<a href="/products" class="btn btn-primary btn-sm">Browse Products</a>' +
                    '</div>';
                if (submitBtn) submitBtn.disabled = true;
                if (checkoutSummary) checkoutSummary.classList.add('d-none');
                if (checkoutTotal) checkoutTotal.textContent = '$0.00';
                if (orderTotalText) orderTotalText.textContent = '$0.00';
                return cart;
            }

            if (submitBtn) submitBtn.disabled = false;
            if (checkoutSummary) checkoutSummary.classList.remove('d-none');

            var html = '';
            var total = 0;
            cart.forEach(function(item) {
                var lineTotal = parseFloat(item.unit_price) * (item.quantity || 1);
                var thumb = item.thumbnail_url
                    ? '<img src="' + escapeCartHtml(item.thumbnail_url) + '" alt="' + escapeCartHtml(item.name) + '">'
                    : '<i class="bi bi-box"></i>';
                total += lineTotal;
                html +=
                    '<div class="checkout-line-item">' +
                    '<div class="checkout-item-media">' + thumb + '</div>' +
                    '<div class="flex-grow-1">' +
                    '<span class="fw-semibold small d-block">' + escapeCartHtml(item.name) + '</span>' +
                    '<small class="text-muted">Qty: ' + (item.quantity || 1) + ' x $' + parseFloat(item.unit_price).toFixed(2) + '</small>' +
                    '</div>' +
                    '<span class="fw-bold">$' + lineTotal.toFixed(2) + '</span>' +
                    '</div>';
            });

            cartContainer.innerHTML = html;

            if (checkoutItems) {
                var itemsHtml = '';
                cart.forEach(function(item) {
                    var t = parseFloat(item.unit_price) * (item.quantity || 1);
                    itemsHtml += '<div class="d-flex justify-content-between small mb-2"><span>' + escapeCartHtml(item.name) + ' x' + (item.quantity || 1) + '</span><span class="fw-semibold">$' + t.toFixed(2) + '</span></div>';
                });
                checkoutItems.innerHTML = itemsHtml;
            }

            if (checkoutTotal) checkoutTotal.textContent = '$' + total.toFixed(2);
            if (orderTotalText) orderTotalText.textContent = '$' + total.toFixed(2);
            return cart;
        });
    }

    renderCheckoutCart();

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }

        getCart().then(function(cart) {
            if (cart.length === 0) {
                showAlert('Your cart is empty. Add a product before placing an order.', 'warning');
                renderCheckoutCart();
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creating order...';

            var items = cart.map(function(item) {
                return {
                    product_id: item.product_id,
                    quantity: item.quantity || 1
                };
            });

            return fetch('/api/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    customer_name: nameInput.value.trim(),
                    customer_email: emailInput.value.trim(),
                    items: items
                })
            })
            .then(function(r) {
                if (!r.ok) return r.json().then(function(err) { throw new Error(err.detail || 'Checkout failed'); });
                return r.json();
            })
            .then(function(data) {
                return clearCart().then(function() {
                    if (data.confirmation_url) {
                        window.location.href = data.confirmation_url;
                    } else {
                        window.location.href = '/order/confirmation?order_id=' + data.order_id;
                    }
                });
            });
        })
        .catch(function(err) {
            showAlert('Error: ' + err.message, 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-check-circle me-2"></i>Place Order - ' + (orderTotalText ? orderTotalText.textContent : '');
        });
    });
});
