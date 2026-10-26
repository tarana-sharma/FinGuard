
const loginTab = document.getElementById("loginTab");
const registerTab = document.getElementById("registerTab");
const authForm = document.getElementById("authForm");
const nameGroup = document.getElementById("nameGroup");
const fullName = document.getElementById("fullName");
const email = document.getElementById("email");
const password = document.getElementById("password");
const message = document.getElementById("authMessage");
const submitBtn = document.getElementById("submitBtn");

let mode = "login";

function setMode(newMode) {
    mode = newMode;
    const registering = mode === "register";

    loginTab.classList.toggle("active", !registering);
    registerTab.classList.toggle("active", registering);
    nameGroup.classList.toggle("hidden", !registering);

    fullName.required = registering;

    document.getElementById("formTitle").textContent =
        registering ? "Create your account" : "Welcome back";

    document.getElementById("formSubtitle").textContent =
        registering
            ? "Start managing your finances with FinGuard."
            : "Sign in to access your financial dashboard.";

    submitBtn.textContent =
        registering ? "Create Account" : "Sign In";

    password.autocomplete =
        registering ? "new-password" : "current-password";

    password.value = "";
    message.textContent = "";
    message.className = "auth-message";
}

loginTab.addEventListener("click", () => setMode("login"));
registerTab.addEventListener("click", () => setMode("register"));

authForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const registering = mode === "register";

    const payload = {
        email: email.value.trim(),
        password: password.value
    };

    if (registering) {
        payload.full_name = fullName.value.trim();
    }

    message.textContent = "";
    message.className = "auth-message";
    submitBtn.disabled = true;

    try {
        const response = await fetch(
            registering ? "/api/register" : "/api/login",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                credentials: "same-origin",
                body: JSON.stringify(payload)
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.message || "Something went wrong"
            );
        }

        if (registering) {
            setMode("login");
            message.textContent =
                "Account created! Please sign in.";
            message.classList.add("success");
        } else {
            window.location.href = "/dashboard";
        }

    } catch (error) {
        message.textContent = error.message;
        message.classList.add("error");
    } finally {
        submitBtn.disabled = false;
    }
});
