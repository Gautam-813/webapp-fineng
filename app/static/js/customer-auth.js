var pendingRegistrationEmail = '';
var pendingResetEmail = '';

document.addEventListener('DOMContentLoaded', function() {
    var loginForm = document.getElementById('customerLoginForm');
    var registerForm = document.getElementById('customerRegisterForm');
    var registrationOtpForm = document.getElementById('registrationOtpForm');
    var forgotForm = document.getElementById('forgotPasswordForm');
    var resetForm = document.getElementById('resetPasswordForm');

    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!loginForm.checkValidity()) {
                loginForm.classList.add('was-validated');
                return;
            }
            submitLogin();
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!registerForm.checkValidity()) {
                registerForm.classList.add('was-validated');
                return;
            }
            submitRegister();
        });
    }

    if (registrationOtpForm) {
        registrationOtpForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!registrationOtpForm.checkValidity()) {
                registrationOtpForm.classList.add('was-validated');
                return;
            }
            verifyRegistrationOtp();
        });
    }

    document.getElementById('registrationResendBtn')?.addEventListener('click', function() {
        resendOtp(pendingRegistrationEmail, 'registration', 'registrationResendBtn');
    });

    if (forgotForm) {
        forgotForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!forgotForm.checkValidity()) {
                forgotForm.classList.add('was-validated');
                return;
            }
            submitForgotPassword();
        });
    }

    if (resetForm) {
        resetForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!resetForm.checkValidity()) {
                resetForm.classList.add('was-validated');
                return;
            }
            submitResetPassword();
        });
    }

    document.getElementById('resetResendBtn')?.addEventListener('click', function() {
        resendOtp(pendingResetEmail, 'password_reset', 'resetResendBtn');
    });
});

function submitLogin() {
    var btn = document.getElementById('loginSubmitBtn');
    setAuthButton(btn, true, 'Logging in...');

    fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email: document.getElementById('loginEmail').value.trim(),
            password: document.getElementById('loginPassword').value
        })
    })
    .then(function(r) {
        if (!r.ok) return parseError(r, 'Login failed');
        return r.json();
    })
    .then(function() {
        window.location.href = getNextUrl();
    })
    .catch(function(err) {
        showAlert('Error: ' + err.message, 'danger');
        setAuthButton(btn, false, '<i class="bi bi-box-arrow-in-right me-2"></i>Log In');
    });
}

function submitRegister() {
    var btn = document.getElementById('registerSubmitBtn');
    var email = document.getElementById('registerEmail').value.trim().toLowerCase();
    pendingRegistrationEmail = email;
    setAuthButton(btn, true, 'Sending code...');

    fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            full_name: document.getElementById('registerName').value.trim(),
            email: email,
            password: document.getElementById('registerPassword').value
        })
    })
    .then(function(r) {
        if (!r.ok) return parseError(r, 'Registration failed');
        return r.json();
    })
    .then(function(data) {
        document.getElementById('customerRegisterForm').classList.add('d-none');
        document.getElementById('registrationOtpForm').classList.remove('d-none');
        document.getElementById('registrationOtpEmail').textContent = data.email || email;
        document.getElementById('registrationOtpCode').focus();
        showAlert('Verification code sent. Please check your inbox, Spam, Promotions, or Updates folder.', 'success');
    })
    .catch(function(err) {
        showAlert('Error: ' + err.message, 'danger');
    })
    .finally(function() {
        setAuthButton(btn, false, '<i class="bi bi-envelope-check me-2"></i>Send Verification Code');
    });
}

function verifyRegistrationOtp() {
    var btn = document.getElementById('registrationOtpSubmitBtn');
    setAuthButton(btn, true, 'Verifying...');

    fetch('/api/auth/register/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email: pendingRegistrationEmail,
            otp_code: document.getElementById('registrationOtpCode').value.trim()
        })
    })
    .then(function(r) {
        if (!r.ok) return parseError(r, 'Verification failed');
        return r.json();
    })
    .then(function() {
        showAlert('Account verified. You can now log in.', 'success');
        window.location.href = '/login?next=/account';
    })
    .catch(function(err) {
        showAlert('Error: ' + err.message, 'danger');
        setAuthButton(btn, false, '<i class="bi bi-check2-circle me-2"></i>Verify Account');
    });
}

function submitForgotPassword() {
    var btn = document.getElementById('forgotSubmitBtn');
    var email = document.getElementById('forgotEmail').value.trim().toLowerCase();
    pendingResetEmail = email;
    setAuthButton(btn, true, 'Sending code...');

    fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
    })
    .then(function(r) {
        if (!r.ok) return parseError(r, 'Unable to request reset code');
        return r.json();
    })
    .then(function(data) {
        document.getElementById('forgotPasswordForm').classList.add('d-none');
        document.getElementById('resetPasswordForm').classList.remove('d-none');
        document.getElementById('resetOtpEmail').textContent = email;
        document.getElementById('resetOtpCode').focus();
        showAlert((data.message || 'If an account exists, a reset code has been sent.') + ' Check your inbox, Spam, Promotions, or Updates folder.', 'success');
    })
    .catch(function(err) {
        showAlert('Error: ' + err.message, 'danger');
    })
    .finally(function() {
        setAuthButton(btn, false, '<i class="bi bi-envelope-check me-2"></i>Send Reset Code');
    });
}

function submitResetPassword() {
    var btn = document.getElementById('resetSubmitBtn');
    setAuthButton(btn, true, 'Updating...');

    fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email: pendingResetEmail,
            otp_code: document.getElementById('resetOtpCode').value.trim(),
            password: document.getElementById('resetPassword').value
        })
    })
    .then(function(r) {
        if (!r.ok) return parseError(r, 'Password reset failed');
        return r.json();
    })
    .then(function() {
        showAlert('Password updated. You can now log in.', 'success');
        window.location.href = '/login?next=/account';
    })
    .catch(function(err) {
        showAlert('Error: ' + err.message, 'danger');
        setAuthButton(btn, false, '<i class="bi bi-check2-circle me-2"></i>Update Password');
    });
}

function resendOtp(email, purpose, btnId) {
    if (!email) {
        showAlert('Please start the flow again.', 'warning');
        return;
    }
    var btn = document.getElementById(btnId);
    var originalLabel = btn ? btn.innerHTML : '';
    setAuthButton(btn, true, 'Sending...');

    fetch('/api/auth/otp/resend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, purpose: purpose })
    })
    .then(function(r) {
        if (!r.ok) return parseError(r, 'Unable to resend code');
        return r.json();
    })
    .then(function(data) {
        showAlert((data.message || 'Verification code sent.') + ' Check your inbox, Spam, Promotions, or Updates folder.', 'success');
    })
    .catch(function(err) {
        showAlert('Error: ' + err.message, 'danger');
    })
    .finally(function() {
        setAuthButton(btn, false, originalLabel || 'Resend code');
    });
}

function parseError(response, fallback) {
    return response.json().then(function(err) {
        var detail = err.detail || fallback;
        if (Array.isArray(detail)) {
            detail = detail.map(function(item) { return item.msg || item.message || 'Invalid field'; }).join(', ');
        }
        throw new Error(detail);
    });
}

function setAuthButton(btn, loading, label) {
    if (!btn) return;
    btn.disabled = loading;
    btn.innerHTML = loading ? '<span class="spinner-border spinner-border-sm me-2"></span>' + label : label;
}

function getNextUrl() {
    var params = new URLSearchParams(window.location.search);
    var next = params.get('next');
    return next && next.startsWith('/') ? next : '/account';
}
