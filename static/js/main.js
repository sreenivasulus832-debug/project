/**
 * main.js
 * Frontend interactivity for the Online Voting System
 * Includes mobile menu toggle, ballot submission confirmation,
 * demo credentials autofill, modal popup controls, and alert auto-dismissal.
 */

document.addEventListener("DOMContentLoaded", () => {
    // ------------------------------------------------------------------
    // 1. Mobile Navigation Hamburger Menu Toggle
    // ------------------------------------------------------------------
    const navToggle = document.getElementById("navToggle");
    const navMenu = document.getElementById("navMenu");

    if (navToggle && navMenu) {
        navToggle.addEventListener("click", () => {
            navMenu.classList.toggle("active");
            const isOpen = navMenu.classList.contains("active");
            navToggle.setAttribute("aria-expanded", isOpen);
        });
    }

    // ------------------------------------------------------------------
    // 2. Ballot Voting Confirmation Dialog
    // ------------------------------------------------------------------
    const votingForm = document.getElementById("votingBallotForm");
    if (votingForm) {
        votingForm.addEventListener("submit", (e) => {
            const selectedRadio = votingForm.querySelector('input[name="candidate_id"]:checked');
            
            if (!selectedRadio) {
                e.preventDefault();
                alert("Please select a candidate before submitting your ballot.");
                return;
            }

            const candidateName = selectedRadio.getAttribute("data-candidate-name") || "the selected candidate";
            const confirmMsg = 
                `Are you sure you want to vote for:\n\n` +
                `👉 ${candidateName}\n\n` +
                `Important: Once submitted, your vote is recorded permanently in the database and cannot be modified.`;

            if (!window.confirm(confirmMsg)) {
                e.preventDefault(); // Cancel form submission if user changes their mind
            }
        });
    }

    // ------------------------------------------------------------------
    // 3. Highlight Selected Candidate Radio Card Visually
    // ------------------------------------------------------------------
    const candidateRadios = document.querySelectorAll('.candidate-radio-card input[type="radio"]');
    candidateRadios.forEach((radio) => {
        radio.addEventListener("change", () => {
            document.querySelectorAll('.candidate-radio-card').forEach((card) => {
                card.classList.remove('selected');
            });
            if (radio.checked) {
                const parentCard = radio.closest('.candidate-radio-card');
                if (parentCard) {
                    parentCard.classList.add('selected');
                }
            }
        });
    });

    // ------------------------------------------------------------------
    // 4. Auto-dismiss Flash Alerts after 6 seconds
    // ------------------------------------------------------------------
    const flashAlerts = document.querySelectorAll(".alert");
    flashAlerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-8px)";
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });

    // ------------------------------------------------------------------
    // 5. Close Modals on Backdrop Click or Escape Key
    // ------------------------------------------------------------------
    const modals = document.querySelectorAll(".modal-backdrop");
    modals.forEach((modal) => {
        modal.addEventListener("click", (e) => {
            // Close if clicked directly on the darkened backdrop, not the dialog box
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            const activeModal = document.querySelector(".modal-backdrop.active");
            if (activeModal) {
                closeModal(activeModal.id);
            }
        }
    });
});

/**
 * Open a modal popup by ID and set focus to the first input.
 * @param {string} modalId 
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add("active");
        document.body.style.overflow = "hidden"; // Prevent background scroll
        setTimeout(() => {
            const firstInput = modal.querySelector("input:not([type='hidden']), select, textarea");
            if (firstInput) {
                firstInput.focus();
            }
        }, 100);
    }
}

/**
 * Close a modal popup by ID and restore background scrolling.
 * @param {string} modalId 
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
    }
}

/**
 * Open the candidate modal with a pre-selected election poll ID.
 * Allows adding candidate details manually for a specific election.
 * @param {string|number} pollId 
 */
function openCandidateModalForPoll(pollId) {
    const selectElem = document.getElementById("modal_cand_poll_id");
    if (selectElem && pollId) {
        selectElem.value = pollId;
    }
    openModal("candidateModal");
}

/**
 * Helper to auto-fill sample credentials on the Sign In page.
 * Extremely helpful for classroom demos and testing.
 * @param {string} studentId 
 * @param {string} password 
 */
function fillCredentials(studentId, password) {
    const idInput = document.getElementById("student_id");
    const pwInput = document.getElementById("password");
    if (idInput && pwInput) {
        idInput.value = studentId;
        pwInput.value = password;
        // Focus the submit button so user can just hit Enter
        const submitBtn = document.querySelector("#loginForm button[type='submit']");
        if (submitBtn) {
            submitBtn.focus();
        }
    }
}

/**
 * Helper to auto-fill administrator demo credentials on the Admin Sign In page.
 * @param {string} adminId 
 * @param {string} password 
 */
function fillAdminCredentials(adminId, password) {
    const idInput = document.getElementById("admin_id") || document.getElementById("student_id");
    const pwInput = document.getElementById("admin_password") || document.getElementById("password");
    if (idInput && pwInput) {
        idInput.value = adminId;
        pwInput.value = password;
        const submitBtn = document.querySelector("#adminLoginForm button[type='submit']") || document.querySelector("button[type='submit']");
        if (submitBtn) {
            submitBtn.focus();
        }
    }
}
