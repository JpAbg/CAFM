(function () {
    var form = document.getElementById("cafm-sign-up-form");
    var error = document.getElementById("cafm-sign-up-error");

    if (!form || !error) {
        return;
    }

    var card = form.closest(".login-content.page-card");
    var submit = form.querySelector('[type="submit"]');
    var firstName = form.querySelector('[name="first_name"]');
    var lastName = form.querySelector('[name="last_name"]');
    var email = form.querySelector('[name="usr"]');
    var password = form.querySelector('[name="pwd"]');
    var confirmPassword = form.querySelector('[name="confirm_password"]');

    var passwordToggle = form.querySelector(".toggle-password");

    function togglePasswords() {
        var reveal = password.type === "password";
        [password, confirmPassword].forEach(function (input) {
            input.type = reveal ? "text" : "password";
        });
        passwordToggle.textContent = reveal ? "Hide" : "Show";
    }

    passwordToggle.addEventListener("click", togglePasswords);
    passwordToggle.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            togglePasswords();
        }
    });

    function setError(message) {
        error.textContent = message;
        error.hidden = false;
        if (card) {
            card.classList.remove("invalid-login");
            void card.offsetWidth;
            card.classList.add("invalid-login");
        }
    }

    function getServerMessage(data) {
        if (data && data._server_messages) {
            try {
                var messages = JSON.parse(data._server_messages);
                if (messages.length) {
                    try {
                        var detailed = JSON.parse(messages[0]);
                        return detailed.message || messages[0];
                    } catch (error) {
                        return messages[0];
                    }
                }
            } catch (error) {
                return data.message || "Unable to create the account.";
            }
        }
        return (data && (data.message || data.exception)) || "Unable to create the account.";
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        error.hidden = true;

        if (!firstName.value.trim() || !lastName.value.trim() || !email.value.trim() || !password.value || !confirmPassword.value) {
            setError("First name, last name, email, and both password fields are required.");
            var firstMissing = [firstName, lastName, email, password, confirmPassword].find(function (input) {
                return !input.value.trim();
            });
            firstMissing.focus();
            return;
        }
        if (password.value !== confirmPassword.value) {
            setError("The passwords do not match.");
            confirmPassword.focus();
            return;
        }

        submit.disabled = true;
        submit.textContent = "Creating account...";

        fetch("/api/method/cafm.www.sign_up.sign_up_account", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                Accept: "application/json"
            },
            body: new URLSearchParams(new FormData(form)),
            credentials: "same-origin"
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    return { ok: response.ok, data: data };
                });
            })
            .then(function (result) {
                if (!result.ok || result.data.exc) {
                    throw new Error(getServerMessage(result.data));
                }
                submit.textContent = "Account created";
                window.setTimeout(function () {
                    window.location.assign("/login");
                }, 900);
            })
            .catch(function (signInError) {
                setError(signInError.message || "Unable to create the account.");
                submit.disabled = false;
                submit.textContent = "Sign up";
            });
    });
})();
