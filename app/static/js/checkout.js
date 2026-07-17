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

    function renderCheckoutCart() {
        var cartContainer = document.getElementById('checkoutCartItems');
        if (!cartContainer) return Promise.resolve([]);

        cartContainer.innerHTML = '<p class="text-muted small">Loading cart...</p>';

        return getCart().then(function(cart) {
            if (cart.length === 0) {
                cartContainer.innerHTML = '<p class="text-muted">Your cart is empty. <a href="/products">Browse products</a></p>';
                if (submitBtn) submitBtn.disabled = true;
                if (checkoutSummary) checkoutSummary.classList.add('d-none');
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
                showAlert('Your cart is empty.', 'warning');
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
