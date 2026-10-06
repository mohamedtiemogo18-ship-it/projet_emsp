/* =========================================================
   EMSP - SCRIPT PRINCIPAL
========================================================= */

document.addEventListener("DOMContentLoaded", function () {


    /* =====================================================
       ELEMENTS
    ====================================================== */

    const sections = document.querySelectorAll(".form-section");

    const sidebarLinks = document.querySelectorAll(".sidebar-link");

    const stepperLinks = document.querySelectorAll(".candidate-stepper .step");

    const nextButtons = document.querySelectorAll(".next-btn");

    const prevButtons = document.querySelectorAll(".prev-btn");

    const sidebar = document.getElementById("sidebar");

    const sidebarToggle = document.getElementById("sidebarToggle");

    const form = document.getElementById("inscriptionForm");

    const dossierInput = document.getElementById("numeroDossier");

    const dossierHeader = document.getElementById(
        "numeroDossierHeader"
    );

    const dossierConvocation = document.getElementById(
        "convocationDossier"
    );

    const anneeBac = document.getElementById("anneeBac");


    /* =====================================================
       ANNEES DU BAC
    ====================================================== */

    if (anneeBac) {

        const anneeActuelle =
            new Date().getFullYear();

        for (
            let annee = anneeActuelle;
            annee >= anneeActuelle - 10;
            annee--
        ) {

            const option =
                document.createElement("option");

            option.value = annee;

            option.textContent = annee;

            anneeBac.appendChild(option);

        }

        const valeursFormulaire = JSON.parse(form?.dataset.values || "{}");
        if (valeursFormulaire.annee_bac) {
            anneeBac.value = valeursFormulaire.annee_bac;
        }

    }


    if (form?.dataset.values) {
        const valeursFormulaire = JSON.parse(form.dataset.values);
        Object.entries(valeursFormulaire).forEach(([nom, valeur]) => {
            const champ = form.elements[nom];
            if (champ && valeur !== null && valeur !== undefined) {
                champ.value = valeur;
            }
        });
    }



    /* =====================================================
       AFFICHER UNE SECTION
    ====================================================== */

    function afficherSection(id) {


        sections.forEach(section => {

            section.classList.remove(
                "active-section"
            );

        });


        const section =
            document.getElementById(id);


        if (section) {

            section.classList.add(
                "active-section"
            );

        }


        /* Sidebar */

        sidebarLinks.forEach(link => {

            link.classList.remove("active");

            if (
                link.dataset.section === id
            ) {

                link.classList.add("active");

            }

        });


        /* Stepper */

        stepperLinks.forEach(link => {

            link.classList.remove("step--current", "step--done");

            link.classList.add("step--upcoming");

            if (
                link.dataset.section === id
            ) {

                link.classList.remove("step--upcoming");

                link.classList.add("step--current");

            }

        });


        /* Scroll */

        window.scrollTo({

            top: 0,

            behavior: "smooth"

        });


        /* Fermer sidebar mobile */

        if (window.innerWidth <= 768) {

            sidebar.classList.remove("show");

        }


        /* Progression */

        mettreAJourProgression(id);

    }



    /* =====================================================
       PROGRESSION
    ====================================================== */

    function mettreAJourProgression() {

        const requis = form
            ? [...form.querySelectorAll("input[required], select[required], textarea[required]")]
            : [];
        const remplis = requis.filter(champ => {
            if (champ.type === "checkbox") return champ.checked;
            if (champ.type === "file") return champ.files && champ.files.length > 0;
            return champ.value.trim() !== "";
        });
        const valeur = requis.length ? Math.round((remplis.length / requis.length) * 100) : 0;
        const completionBar = document.getElementById("completionBar");
        const completionText = document.getElementById("completionText");
        if (completionBar) {
            completionBar.style.width = valeur + "%";
            completionBar.setAttribute("aria-valuenow", String(valeur));
        }
        if (completionText) completionText.textContent = valeur + " % complété";


        document
            .querySelectorAll(".progress-card")
            .forEach(card => {

                const progressBar =
                    card.querySelector(".progress-bar");

                const percentage =
                    card.querySelector(
                        ".progress-card-header strong"
                    );


                if (progressBar) {

                    progressBar.style.width =
                        valeur + "%";

                }


                if (percentage) {

                    percentage.textContent =
                        valeur + "%";

                }

            });

    }



    /* =====================================================
       SIDEBAR
    ====================================================== */

    sidebarLinks.forEach(link => {

        link.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                const section =
                    this.dataset.section;

                afficherSection(section);

            }
        );

    });


    stepperLinks.forEach(link => {

        link.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                const section =
                    this.dataset.section;

                afficherSection(section);

            }
        );

    });



    /* =====================================================
       BOUTON SUIVANT
    ====================================================== */

    nextButtons.forEach(button => {

        button.addEventListener(
            "click",
            function () {

                const sectionId =
                    this.dataset.next;

                afficherSection(sectionId);

            }
        );

    });



    /* =====================================================
       BOUTON PRECEDENT
    ====================================================== */

    prevButtons.forEach(button => {

        button.addEventListener(
            "click",
            function () {

                const sectionId =
                    this.dataset.prev;

                afficherSection(sectionId);

            }
        );

    });



    /* =====================================================
       SIDEBAR MOBILE
    ====================================================== */

    if (sidebarToggle) {

        sidebarToggle.addEventListener(
            "click",
            function () {

                const isExpanded = sidebar.classList.toggle("show");
                sidebarToggle.setAttribute("aria-expanded", String(isExpanded));
                sidebarToggle.setAttribute(
                    "aria-label",
                    isExpanded ? "Masquer les étapes du dossier" : "Afficher les étapes du dossier"
                );

            }
        );

    }



    /* =====================================================
       VALIDATION D'UNE SECTION
    ====================================================== */

    function validerSection(
        sectionId,
        bouton
    ) {


        const section =
            document.getElementById(sectionId);


        if (!section) {

            return false;

        }


        const champs =
            section.querySelectorAll(
                "input, select, textarea"
            );


        let valide = true;


        champs.forEach(champ => {

            if (
                champ.hasAttribute("required") &&
                !champ.checkValidity()
            ) {

                champ.classList.add(
                    "is-invalid"
                );

                valide = false;

            } else {

                champ.classList.remove(
                    "is-invalid"
                );

            }

        });


        if (!valide) {

            section
                .querySelector(
                    ":invalid"
                )
                ?.focus();

            return false;

        }


        if (bouton) {

            const ancienHTML =
                bouton.innerHTML;


            bouton.innerHTML =
                '<i class="bi bi-check-circle me-1"></i> Validé';


            bouton.classList.remove(
                "btn-success"
            );


            bouton.classList.add(
                "btn-outline-success"
            );


            setTimeout(() => {

                bouton.innerHTML =
                    ancienHTML;

                bouton.classList.remove(
                    "btn-outline-success"
                );

                bouton.classList.add(
                    "btn-success"
                );

            }, 2000);

        }


        return true;

    }


    function enregistrerBrouillon(bouton) {
        if (!form) {
            return;
        }
        const action = form.elements.action;
        const ancienneAction = action.value;
        action.value = "brouillon";
        bouton.disabled = true;
        fetch(form.action, {
            method: "POST",
            body: new FormData(form)
        }).then(response => {
            if (response.ok) {
                bouton.innerHTML = '<i class="bi bi-check-circle me-1"></i> Brouillon enregistré';
            }
        }).finally(() => {
            action.value = ancienneAction;
            bouton.disabled = false;
        });
    }



    /* =====================================================
       VALIDATION GENERAL
    ====================================================== */

    const validateGeneral =
        document.getElementById(
            "validateGeneral"
        );


    if (validateGeneral) {

        validateGeneral.addEventListener(
            "click",
            function () {

                if (validerSection(
                    "section-generale",
                    this
                )) enregistrerBrouillon(this);

            }
        );

    }



    /* =====================================================
       VALIDATION BAC
    ====================================================== */

    const validateBac =
        document.getElementById(
            "validateBac"
        );


    if (validateBac) {

        validateBac.addEventListener(
            "click",
            function () {

                if (validerSection(
                    "section-bac",
                    this
                )) enregistrerBrouillon(this);

            }
        );

    }



    /* =====================================================
       VALIDATION TUTEURS
    ====================================================== */

    const validateTuteurs =
        document.getElementById(
            "validateTuteurs"
        );


    if (validateTuteurs) {

        validateTuteurs.addEventListener(
            "click",
            function () {

                if (validerSection(
                    "section-tuteurs",
                    this
                )) enregistrerBrouillon(this);

            }
        );

    }



    /* =====================================================
       VALIDATION DOCUMENTS
    ====================================================== */

    const validateDocuments =
        document.getElementById(
            "validateDocuments"
        );


    if (validateDocuments) {

        validateDocuments.addEventListener(
            "click",
            function () {

                if (validerSection(
                    "section-documents",
                    this
                )) enregistrerBrouillon(this);

            }
        );

    }



    /* =====================================================
       FICHIERS
    ====================================================== */

    const fileInputs =
        document.querySelectorAll(
            ".document-upload input[type='file']"
        );


    fileInputs.forEach(input => {


        input.addEventListener(
            "change",
            function () {


                const label =
                    this.closest(
                        ".document-upload"
                    );


                if (!label) {

                    return;

                }


                const small =
                    label.querySelector(
                        "small"
                    );


                if (
                    this.files &&
                    this.files.length > 0
                ) {

                    const fichier =
                        this.files[0];


                    if (small) {
                        small.textContent = fichier.name;
                    }


                    label.classList.add(
                        "file-selected"
                    );

                } else {

                    if (small) {
                        small.textContent = "Aucun fichier sélectionné";
                    }

                    label.classList.remove(
                        "file-selected"
                    );

                }

            }
        );

    });



     if (form) {
          form.addEventListener("input", mettreAJourProgression);
          form.addEventListener("change", mettreAJourProgression);
     }


     /* =====================================================
         VALIDATION FINALE
     ====================================================== */

    if (form) {

        form.addEventListener(
            "submit",
            function (event) {
                /* Confirmation */

                const confirmation =
                    document.getElementById(
                        "confirmation"
                    );


                if (
                    confirmation &&
                    !confirmation.checked
                ) {

                    const erreur = document.createElement("div");
                    erreur.setAttribute("role", "alert");
                    erreur.className = "alert alert-danger mb-3";
                    erreur.textContent = "Veuillez confirmer l'exactitude des informations fournies.";
                    confirmation.closest("section").prepend(erreur);

                    confirmation.focus();

                    afficherSection(
                        "section-documents"
                    );

                    return;

                }


                /* Validation HTML */

                if (!form.checkValidity()) {

                    form.reportValidity();

                    return;

                }


                const bouton =
                    document.getElementById(
                        "submitInscription"
                    );


                bouton.disabled = true;


                bouton.innerHTML =
                    '<span class="spinner-border spinner-border-sm me-2"></span> Traitement...';


            }
        );

    }



    /* =====================================================
       INITIALISATION
    ====================================================== */

    afficherSection(
        "section-generale"
    );


});