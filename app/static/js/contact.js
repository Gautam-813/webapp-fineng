document.addEventListener('DOMContentLoaded', function() {
    var contactForm = document.getElementById('contactForm');
    var projectForm = document.getElementById('projectRequestForm');

    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!contactForm.checkValidity()) {
                contactForm.classList.add('was-validated');
                return;
            }
            submitContact('/api/contact', contactForm, 'contactSubmitBtn');
        });
    }

    if (projectForm) {
        projectForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!projectForm.checkValidity()) {
                projectForm.classList.add('was-validated');
                return;
            }
            submitContact('/api/custom-project-request', projectForm, 'projectSubmitBtn');
        });
    }
});

function submitContact(url, form, btnId) {
    var btn = document.getElementById(btnId);
    var isProjectRequest = url.includes('custom-project');
    var formData = form === document.getElementById('contactForm')
        ? {
            name: document.getElementById('contactName').value.trim(),
            email: document.getElementById('contactEmail').value.trim(),
            phone: document.getElementById('contactPhone')?.value.trim() || '',
            company: document.getElementById('contactCompany')?.value.trim() || '',
            subject: document.getElementById('contactSubject')?.value.trim() || '',
            message: document.getElementById('contactMessage').value.trim(),
            service_type: document.getElementById('contactServiceType')?.value || 'general'
        }
        : {
            name: document.getElementById('projectName').value.trim(),
            email: document.getElementById('projectEmail').value.trim(),
            phone: document.getElementById('projectPhone')?.value.trim() || '',
            company: document.getElementById('projectCompany')?.value.trim() || '',
            project_type: document.getElementById('projectType')?.value.trim() || '',
            budget_range: document.getElementById('projectBudget')?.value || '',
            timeline: document.getElementById('projectTimeline')?.value.trim() || '',
            description: document.getElementById('projectDescription').value.trim()
        };

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>' + (isProjectRequest ? 'Submitting...' : 'Sending...');
    }

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    })
    .then(function(r) {
        if (!r.ok) return r.json().then(function(err) { throw new Error(err.detail || 'Submission failed'); });
        return r.json();
    })
    .then(function(data) {
        form.reset();
        form.classList.remove('was-validated');
        showAlert(data.message || (isProjectRequest ? 'Project request submitted successfully.' : 'Message sent successfully.'), 'success');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = isProjectRequest
                ? '<i class="bi bi-code-slash me-2"></i>Submit Project Request'
                : '<i class="bi bi-send me-2"></i>Send Message';
        }
    })
    .catch(function(err) {
        showAlert('Error: ' + err.message, 'danger');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = isProjectRequest
                ? '<i class="bi bi-code-slash me-2"></i>Submit Project Request'
                : '<i class="bi bi-send me-2"></i>Send Message';
        }
    });
}
