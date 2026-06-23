const form = document.getElementById("promptForm");
const resultDisplay = document.getElementById("resultDisplay");
const resultMeta = document.getElementById("resultMeta");

const scrollToForm = document.querySelector("[data-scroll-to-form]");
const scrollToInfo = document.querySelector("[data-scroll-to-info]");
const presetToolbars = document.querySelectorAll(".preset-toolbar");
const copyPromptBtn = document.getElementById("btn-copy-prompt");
const loginBtn = document.querySelector("#login-btn");
const profileBtn = document.getElementById("profile-btn");
const profileInitials = document.getElementById("profile-initials");
const profileName = document.getElementById("profile-name");
const profileMenu = document.getElementById("profile-menu");
const profileEmail = document.getElementById("profile-email");
const profileMenuEmail = document.getElementById("profile-menu-email");
const profilePlan = document.getElementById("profile-plan");
const logoutBtn = document.getElementById("logout-btn");
const loginModal = document.getElementById("login-modal");
const modalMessage = document.getElementById("modal-message");
const modalLoginBtn = document.getElementById("modal-login-btn");
const closeBtn = document.querySelector(".close");
const loginToast = document.getElementById("login-toast");


const API_VERSION = "v1.1";
const API_ROOT = `api/${API_VERSION}`;
const PROMPT_API = `${API_ROOT}/pcrafter`;
const USER_API = `${API_ROOT}/user`;

function showToast(message) {
    loginToast.textContent = message;
    loginToast.classList.add("show");
    window.setTimeout(() => {
        loginToast.classList.remove("show");
    }, 2500);
}

function getInitials(email) {
    if (!email) return "?";
    const name = email.split("@")[0];
    const parts = name.split(/[._-]+/).filter(Boolean);
    if (parts.length === 1) {
        return parts[0].slice(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[1][0]).toUpperCase();
}

function getDisplayName(email) {
    if (!email) return "Guest";
    const name = email.split("@")[0];
    return name
        .split(/[._-]+/)
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function setLoggedIn(user) {
    // Change signup button to logout after successful authentication
    loginBtn.textContent = "Logout";
    loginBtn.style.display = "inline-block";
    // Attach logout handler to the same button
    loginBtn.onclick = () => {
        fetch(`${USER_API}/logout`, {
            method: "POST",
            credentials: "include",
        }).then((response) => {
            if (response.ok) {
                sessionStorage.removeItem("access_token");
                sessionStorage.removeItem("refresh_token");
                sessionStorage.removeItem("user");
                setLoggedOut();
                showToast("Logged out successfully");
                // Reload to reset UI state
                window.location.reload();
            } else {
                alert("Logout failed");
            }
        }).catch((error) => {
            console.error("Logout error:", error);
            alert("An error occurred during logout");
        });
    };
    // Show profile information
    profileBtn.disabled = false;
    profileName.textContent = getDisplayName(user.email);
    profileEmail.textContent = user.email;
    profileMenuEmail.textContent = user.email;
    profilePlan.textContent = user.plan || "Free";
    profileInitials.textContent = getInitials(user.email);
    profileMenu.style.display = "none";
    const pending = sessionStorage.getItem("loginPending");
    if (pending) {
        showToast("Account created successfully");
        sessionStorage.removeItem("loginPending");
    }
}

function setLoggedOut() {
    loginBtn.textContent = "Login / Sign Up";
    loginBtn.style.display = "inline-block";
    profileBtn.disabled = true;
    profileName.textContent = "Guest";
    profileEmail.textContent = "guest@promptcrafter.ai";
    profileMenuEmail.textContent = "";
    profilePlan.textContent = "Free";
    profileMenu.style.display = "none";
}

function checkLogin() {
    // Try cookie-based session first (credentials: include), then attempt a refresh to obtain tokens,
    // finally fall back to stored tokens in sessionStorage.
    return (async () => {
        try {
            const resp = await fetch(`${USER_API}/me`, { method: "GET", credentials: "include" });
            if (resp.ok) {
                const user = await resp.json();
                // persist user for the session
                sessionStorage.setItem("user", JSON.stringify(user));
                setLoggedIn(user);
                return user;
            }

            // If unauthorized, try to exchange refresh token (if backend supports cookie-based refresh)
            if (resp.status === 401) {
                try {
                    const r = await fetch(`${USER_API}/refresh`, { method: "GET", credentials: "include" });
                    if (r.ok) {
                        const tokenPayload = await r.json();
                        if (tokenPayload.access_token) {
                            // store tokens to sessionStorage for Authorization header use
                            sessionStorage.setItem("access_token", tokenPayload.access_token);
                        }
                        if (tokenPayload.refresh_token) {
                            sessionStorage.setItem("refresh_token", tokenPayload.refresh_token);
                        }
                        // retry /me with Authorization header
                        const me = await fetch(`${USER_API}/me`, {
                            method: "GET",
                            headers: { "Authorization": `Bearer ${sessionStorage.getItem("access_token")}` },
                        });
                        if (me.ok) {
                            const user = await me.json();
                            sessionStorage.setItem("user", JSON.stringify(user));
                            setLoggedIn(user);
                            return user;
                        }
                    }
                } catch (err) {
                    // refresh failed, continue to stored token fallback
                }
            }

            // Final fallback: try with stored access_token (if any)
            const stored = sessionStorage.getItem("access_token");
            if (stored) {
                const r2 = await fetch(`${USER_API}/me`, { method: "GET", headers: { "Authorization": `Bearer ${stored}` } });
                if (r2.ok) {
                    const user = await r2.json();
                    sessionStorage.setItem("user", JSON.stringify(user));
                    setLoggedIn(user);
                    return user;
                }
            }

            // Not logged in
            setLoggedOut();
            return null;
        } catch (err) {
            setLoggedOut();
            return null;
        }
    })();
}

scrollToForm?.addEventListener("click", () => {
    document.getElementById("formSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
});

scrollToInfo?.addEventListener("click", () => {
    document.getElementById("infoSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
});

// render form for user input

loginBtn.addEventListener("click", () => {
    // First check whether the user is already authenticated (cookies or stored token).
    checkLogin().then((user) => {
        if (user && user.email) {
            // Already logged in — update UI and skip redirect.
            setLoggedIn(user);
            return;
        }
        // Not logged in — start OAuth redirect.
        sessionStorage.setItem("loginPending", "true");
        window.location.href = `${USER_API}/login/google`;
    });
});

profileBtn.addEventListener("click", (e) => {
    if (profileBtn.disabled) return;
    // Toggle left-expanding menu by toggling an `open-left` class on the button
    profileBtn.classList.toggle("open-left");
    const isOpen = profileBtn.classList.contains("open-left");
    profileMenu.style.display = isOpen ? "block" : "none";
    e.stopPropagation();
});

// Close profile menu when clicking outside
window.addEventListener("click", (ev) => {
    if (!profileBtn.contains(ev.target) && !profileMenu.contains(ev.target)) {
        profileBtn.classList.remove("open-left");
        profileMenu.style.display = "none";
    }
});

presetToolbars.forEach((toolbar) => {
    toolbar.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLButtonElement)) return;
        const field = toolbar.dataset.field;
        const input = form?.querySelector(`input[name="${field}"]`);
        if (!input) return;

        toolbar.querySelectorAll(".preset").forEach((btn) => btn.classList.remove("active"));
        target.classList.add("active");
        input.value = target.textContent.trim();
    });
});

function renderResult(structured, natural) {
    resultDisplay.innerText = structured;
    resultMeta.innerHTML = "";
    const label = document.createElement("p");
    label.textContent = "Natural preview:";
    const metaValue = document.createElement("p");
    metaValue.className = "meta-value";
    metaValue.textContent = natural;
    resultMeta.appendChild(label);
    resultMeta.appendChild(metaValue);
}

function renderEmpty() {
    resultDisplay.innerHTML = `
    <p class="empty-state">No prompt yet. Fill the form to see the structured content.</p>
  `;
    resultMeta.innerText = "";
    window.currentPrompts = null;
}

form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {};
    for (const [key, value] of formData.entries()) {
        if (!value) continue;
        if (key === "tags") {
            payload[key] = value
                .split(",")
                .map((tag) => tag.trim())
                .filter(Boolean);
        } else {
            payload[key] = value;
        }
    }

    if (!payload.task) {
        return;
    }

    resultDisplay.innerHTML = "<p class='empty-state'>Processing…</p>";
    resultMeta.innerHTML = "";

    try {
        const response = await fetch(`${PROMPT_API}/process`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            if (response.status === 429) {
                const data = await response.json();
                modalMessage.textContent = data.detail;
                loginModal.style.display = "block";
                return;
            } else {
                throw new Error("Server rejected the prompt");
            }
        }

        const data = await response.json();
        renderResult(data.structured_prompt, data.natural_prompt);
        window.currentPrompts = {
            structured: data.structured_prompt,
            natural: data.natural_prompt
        };
    } catch (error) {
        resultDisplay.innerHTML = `<p class='empty-state'>${error.message}</p>`;
        resultMeta.innerHTML = "";
        window.currentPrompts = null;
    }
});

logoutBtn.addEventListener("click", () => {
    fetch(`${USER_API}/logout`, {
        method: "POST",
        credentials: "include",
    }).then((response) => {
        if (response.ok) {
            // clear session storage tokens and user info
            sessionStorage.removeItem("access_token");
            sessionStorage.removeItem("refresh_token");
            sessionStorage.removeItem("user");
            window.location.reload();
        } else {
            alert("Logout failed");
        }
    }).catch((error) => {
        console.error("Logout error:", error);
        alert("An error occurred during logout");
    });
});

copyPromptBtn.addEventListener("click", () => {
    const selected = document.querySelector('input[name="copy-option"]:checked').value;
    const text = window.currentPrompts ? window.currentPrompts[selected] : "";
    if (text) {
        navigator.clipboard.writeText(text).then(() => {
            alert("Prompt copied to clipboard!");
        }).catch(err => {
            console.error("Failed to copy: ", err);
            alert("Failed to copy prompt");
        });
    } else {
        alert("No prompt to copy");
    }
});

closeBtn.addEventListener("click", () => {
    loginModal.style.display = "none";
});

modalLoginBtn.addEventListener("click", () => {
    sessionStorage.setItem("loginPending", "true");
    window.location.href = `${USER_API}/login/google`;
    loginModal.style.display = "none";
});

// Close modal when clicking outside
window.addEventListener("click", (event) => {
    if (event.target === loginModal) {
        loginModal.style.display = "none";
    }
});

checkLogin();
