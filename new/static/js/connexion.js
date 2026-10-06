document.addEventListener("DOMContentLoaded", function () {

    const passwordInput = document.getElementById("password");
    const togglePassword = document.getElementById("togglePassword");

    if (passwordInput && togglePassword) {

        togglePassword.addEventListener("click", function () {

            const isPassword =
                passwordInput.getAttribute("type") === "password";

            passwordInput.setAttribute(
                "type",
                isPassword ? "text" : "password"
            );

            const icon = togglePassword.querySelector("i");

            if (isPassword) {

                icon.classList.remove("bi-eye");
                icon.classList.add("bi-eye-slash");

                togglePassword.setAttribute(
                    "aria-label",
                    "Masquer le mot de passe"
                );
                togglePassword.setAttribute("aria-pressed", "true");

            } else {

                icon.classList.remove("bi-eye-slash");
                icon.classList.add("bi-eye");

                togglePassword.setAttribute(
                    "aria-label",
                    "Afficher le mot de passe"
                );
                togglePassword.setAttribute("aria-pressed", "false");
            }
        });
    }


    /* =====================================================
       SOUMISSION DU FORMULAIRE
    ====================================================== */

    const loginForm = document.getElementById("loginForm");

    if (loginForm) {

        loginForm.addEventListener("submit", function (event) {

            const identifiant =
                document.getElementById("identifiant").value.trim();

            const password =
                document.getElementById("password").value;

            if (!identifiant || !password) {

                event.preventDefault();

                let error = loginForm.querySelector("[role='alert']");
                if (!error) {
                    error = document.createElement("div");
                    error.setAttribute("role", "alert");
                    error.className = "alert alert-danger";
                    loginForm.prepend(error);
                }
                error.textContent = "Veuillez renseigner votre identifiant et votre mot de passe.";

                return;
            }

        });
    }

});