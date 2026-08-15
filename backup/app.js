const chat = document.getElementById("chat");
const input = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const welcome = document.getElementById("welcome");


// =========================
// Send message
// =========================

async function sendMessage() {

    const message = input.value.trim();

    if (!message) {
        return;
    }

    input.value = "";
    input.style.height = "auto";

    removeWelcome();

    addMessage("user", message);

    setStatus("بتفكر...");

    try {

        const response = await fetch("/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: message
            })

        });

        if (!response.ok) {
            throw new Error("Server error");
        }

        const data = await response.json();

        addMessage(
            "assistant",
            data.response
        );

        setStatus("جاهزة");

    } catch (error) {

        console.error(error);

        addMessage(
            "assistant",
            "حصلت مشكلة في الاتصال ببيرلا 😕"
        );

        setStatus("في مشكلة");
    }
}


// =========================
// Add message
// =========================

function addMessage(sender, text) {

    const row = document.createElement("div");

    row.className =
        "message-row " +
        (sender === "user"
            ? "user"
            : "assistant");


    if (sender === "assistant") {

        const avatar = document.createElement("div");

        avatar.className = "avatar";

        avatar.textContent = "✦";

        row.appendChild(avatar);
    }


    const message = document.createElement("div");

    message.className =
        "message " + sender;

    message.textContent = text;

    row.appendChild(message);

    chat.appendChild(row);

    chat.scrollTop = chat.scrollHeight;
}


// =========================
// Remove welcome
// =========================

function removeWelcome() {

    const element =
        document.getElementById("welcome");

    if (element) {
        element.remove();
    }
}


// =========================
// Status
// =========================

function setStatus(text) {

    const status =
        document.querySelector(".status");

    if (status) {

        status.innerHTML =
            '<span></span>' + text;
    }
}


// =========================
// Send button
// =========================

sendButton.addEventListener(
    "click",
    sendMessage
);


// =========================
// Enter
// =========================

input.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);


// =========================
// Auto resize textarea
// =========================

input.addEventListener(
    "input",
    function() {

        this.style.height = "auto";

        this.style.height =
            Math.min(
                this.scrollHeight,
                150
            ) + "px";
    }
);
