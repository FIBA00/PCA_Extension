const form = document.getElementById("promptForm");
const resultDisplay = document.getElementById("resultDisplay");
const resultMeta = document.getElementById("resultMeta");

const scrollToForm = document.querySelector("[data-scroll-to-form]");
const scrollToInfo = document.querySelector("[data-scroll-to-info]");
const presetToolbars = document.querySelectorAll(".preset-toolbar");
const copyPromptBtn = document.getElementById("btn-copy-prompt");


const API_VERSION = "v1.1";
const API_ROOT = `api/${API_VERSION}`;
const PROMPT_API = `${API_ROOT}/pcrafter`;

function showToast(message) {
    loginToast.textContent = message;
    loginToast.classList.add("show");
    window.setTimeout(() => {
        loginToast.classList.remove("show");
    }, 2500);
}


scrollToForm?.addEventListener("click", () => {
    document.getElementById("formSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
});

scrollToInfo?.addEventListener("click", () => {
    document.getElementById("infoSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
});

// render form for user input


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
