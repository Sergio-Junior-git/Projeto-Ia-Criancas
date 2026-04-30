const shell = document.querySelector(".study-shell");
const csrfToken = document.querySelector("meta[name='csrf-token']").content;
const state = {
    requestId: null,
    hint: "",
    selectedOption: "",
    currentType: "short_answer",
};

const activityBox = document.querySelector("#activityBox");
const difficultyLabel = document.querySelector("#difficultyLabel");
const answerInput = document.querySelector("#answerInput");
const answerLabel = document.querySelector("#answerLabel");
const optionsBox = document.querySelector("#optionsBox");
const feedbackBox = document.querySelector("#feedbackBox");
const hintBox = document.querySelector("#hintBox");
const retryButton = document.querySelector("#retryButton");

function showPanel(targetId) {
    document.querySelectorAll(".content-panel").forEach((panel) => {
        panel.classList.toggle("active", panel.id === targetId);
    });
    document.querySelectorAll(".tab").forEach((tab) => {
        tab.classList.toggle("active", tab.dataset.target === targetId);
    });
}

document.querySelectorAll("[data-target], [data-target-tab]").forEach((button) => {
    button.addEventListener("click", () => showPanel(button.dataset.target || button.dataset.targetTab));
});

async function generateQuestion() {
    feedbackBox.hidden = true;
    hintBox.hidden = true;
    retryButton.hidden = true;
    optionsBox.innerHTML = "";
    answerInput.value = "";
    state.selectedOption = "";

    activityBox.replaceChildren(createParagraph("Gerando atividade..."));

    const response = await fetch("/api/activity/generate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({
            discipline: shell.dataset.discipline,
            level: shell.dataset.level,
            topic: shell.dataset.topic,
        }),
    });

    const activity = await response.json();
    if (!response.ok) {
        activityBox.replaceChildren(createParagraph(activity.error || "Nao foi possivel gerar a atividade."));
        return;
    }
    state.requestId = activity.request_id;
    state.hint = activity.hint;
    state.currentType = activity.type;
    difficultyLabel.textContent = `Dificuldade ${activity.difficulty} | resposta em ${activity.latency_ms} ms`;
    activityBox.replaceChildren(createParagraph(activity.question));

    if (activity.type === "multiple_choice") {
        answerLabel.hidden = true;
        activity.options.forEach((option) => {
            const button = document.createElement("button");
            button.className = "option-button";
            button.type = "button";
            button.textContent = option;
            button.addEventListener("click", () => {
                document.querySelectorAll(".option-button").forEach((item) => item.classList.remove("selected"));
                button.classList.add("selected");
                state.selectedOption = option;
            });
            optionsBox.appendChild(button);
        });
    } else {
        answerLabel.hidden = false;
    }
}

function createParagraph(text) {
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    return paragraph;
}

async function sendAnswer() {
    if (!state.requestId) {
        await generateQuestion();
        return;
    }

    const answer = state.currentType === "multiple_choice" ? state.selectedOption : answerInput.value;
    if (!answer.trim()) {
        feedbackBox.hidden = false;
        feedbackBox.className = "feedback-box error";
        feedbackBox.textContent = "Escolha ou escreva uma resposta antes de enviar.";
        return;
    }

    const response = await fetch("/api/activity/answer", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({
            request_id: state.requestId,
            answer,
        }),
    });

    const result = await response.json();
    if (!response.ok) {
        feedbackBox.hidden = false;
        feedbackBox.className = "feedback-box error";
        feedbackBox.textContent = result.error || "Nao foi possivel corrigir a resposta.";
        return;
    }
    feedbackBox.hidden = false;
    feedbackBox.className = result.correct ? "feedback-box" : "feedback-box error";
    feedbackBox.textContent = `${result.feedback} Proxima dificuldade: ${result.next_difficulty}.`;
    retryButton.hidden = result.correct;
}

document.querySelector("#newQuestion").addEventListener("click", generateQuestion);
document.querySelector("#sendAnswer").addEventListener("click", sendAnswer);
document.querySelector("#retryButton").addEventListener("click", () => {
    feedbackBox.hidden = true;
    retryButton.hidden = true;
    answerInput.focus();
});
document.querySelector("#hintButton").addEventListener("click", () => {
    hintBox.hidden = false;
    hintBox.textContent = state.hint || "Gere uma questao primeiro para receber uma dica.";
});
