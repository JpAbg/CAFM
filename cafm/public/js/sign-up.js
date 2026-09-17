(function () {
    function addSignInButton() {
        if (window.location.pathname !== "/login") {
            return;
        }

        var loginCard = document.querySelector("section.for-login .login-content");
        if (!loginCard || loginCard.querySelector(".cafm-sign-up-link")) {
            return;
        }

        var button = document.createElement("a");
        button.className = "btn btn-login cafm-sign-up-link";
        button.href = "/sign-up";
        button.textContent = "Sign up";
        button.setAttribute("aria-label", "Open sign up page");

        var divider = loginCard.querySelector(".login-divider");
        if (divider) {
            divider.insertAdjacentElement("afterend", button);
        } else {
            loginCard.appendChild(button);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", addSignInButton);
    } else {
        addSignInButton();
    }
})();