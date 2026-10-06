document.querySelectorAll('.password-toggle').forEach((button) => {
  button.addEventListener('click', () => {
    const passwordInput = document.getElementById(button.dataset.target);
    const icon = button.querySelector('i');
    const isHidden = passwordInput.type === 'password';

    passwordInput.type = isHidden ? 'text' : 'password';
    icon.classList.toggle('bi-eye', !isHidden);
    icon.classList.toggle('bi-eye-slash', isHidden);
    button.setAttribute('aria-label', isHidden ? 'Masquer le mot de passe' : 'Afficher le mot de passe');
  });
});