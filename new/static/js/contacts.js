document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("contactForm");
    if (form) {
        form.addEventListener("submit", function () {
            const button = form.querySelector("button[type='submit']");
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Envoi...';
            }
        });
    }

    const serviceCards = document.querySelectorAll('.service-card[data-service]');
    const objetSelect = document.getElementById('objet');
    serviceCards.forEach(function (card) {
        card.addEventListener('click', function () {
            const service = card.getAttribute('data-service');
            if (objetSelect && service) {
                objetSelect.value = service;
                const contactForm = document.getElementById('contactForm');
                if (contactForm) {
                    contactForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    const firstInput = contactForm.querySelector('input[name="nom"]');
                    if (firstInput) firstInput.focus();
                }
            }
        });
    });
});
