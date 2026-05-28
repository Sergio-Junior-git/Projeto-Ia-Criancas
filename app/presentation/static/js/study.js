const shell = document.querySelector(".study-shell");
const csrfToken = document.querySelector("meta[name='csrf-token']").content;
const state = {
    requestId: null,
    hint: "",
    selectedOption: "",
    currentType: "short_answer",
};

function speakText(text) {
    if (!("speechSynthesis" in window)) {
        alert("Este navegador nao consegue ler o texto em voz alta.");
        return;
    }

    const voice = new SpeechSynthesisUtterance(text);
    voice.lang = "pt-BR";
    voice.rate = 0.85;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(voice);
}

const activityBox = document.querySelector("#activityBox");
const difficultyLabel = document.querySelector("#difficultyLabel");
const answerInput = document.querySelector("#answerInput");
const answerLabel = document.querySelector("#answerLabel");
const optionsBox = document.querySelector("#optionsBox");
const feedbackBox = document.querySelector("#feedbackBox");
const hintBox = document.querySelector("#hintBox");
const retryButton = document.querySelector("#retryButton");
const newQuestionButton = document.querySelector("#newQuestion");
const sendAnswerButton = document.querySelector("#sendAnswer");
const hintButton = document.querySelector("#hintButton");

const topicVisuals = {
    vogais: "A E I O U",
    "sons das letras": "BA",
    "figuras e palavras": "CASA",
    "silabas simples": "BO-LA",
    rimas: "SOL",
    "nomes de objetos": "BOLA",
    contagem: "1 2 3",
    formas: "FORMA",
    "maior e menor": "5 > 2",
    "numeros ate 20": "1 2 3",
    "soma simples": "2 + 1",
    sequencias: "1 2 3",
    "operacoes": "3 + 2",
    "problemas simples": "2 + 2",
    tabuada: "2 x 3",
    cores: "AZUL",
    animais: "GATO",
    cumprimentos: "OI",
    numeros: "UNO",
    familia: "MAE",
    objetos: "LAPIS",
    colores: "ROJO",
    saludos: "HOLA",
    comidas: "PAN",
};

function showPanel(targetId) {
    document.querySelectorAll(".content-panel").forEach((panel) => {
        panel.classList.toggle("active", panel.id === targetId);
    });
    document.querySelectorAll(".tab").forEach((tab) => {
        tab.classList.toggle("active", tab.dataset.target === targetId);
    });
}

document.querySelectorAll("[data-target], [data-target-tab]").forEach((button) => {
    button.addEventListener("click", async () => {
        const targetId = button.dataset.target || button.dataset.targetTab;
        showPanel(targetId);
        if (targetId === "activityPanel" && !state.requestId) {
            await generateQuestion();
        }
    });
});

async function generateQuestion() {
    feedbackBox.hidden = true;
    hintBox.hidden = true;
    retryButton.hidden = true;
    optionsBox.innerHTML = "";
    answerInput.value = "";
    state.selectedOption = "";
    state.requestId = null;

    newQuestionButton.disabled = true;
    sendAnswerButton.disabled = true;
    activityBox.replaceChildren(createVisualCard("...", "Preparando um desafio..."));

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
    newQuestionButton.disabled = false;
    sendAnswerButton.disabled = false;
    if (!response.ok) {
        activityBox.replaceChildren(createParagraph(activity.error || "Nao foi possivel gerar a atividade."));
        return;
    }
    state.requestId = activity.request_id;
    state.hint = activity.hint;
    state.currentType = activity.type;
    difficultyLabel.textContent = `Fase ${activity.difficulty}`;
    activityBox.replaceChildren(createVisualCard(getVisualText(), activity.question));

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
                speakText(option);
            });
            optionsBox.appendChild(button);
        });
    } else {
        answerLabel.hidden = false;
        answerInput.focus();
    }

    speakText(activity.question);
}

function createParagraph(text) {
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    return paragraph;
}

function createVisualCard(visual, question) {
    const card = document.createElement("div");
    card.className = "visual-card";

    const visualText = document.createElement("div");
    visualText.className = "visual-card-symbol";
    visualText.textContent = visual;

    const questionRow = document.createElement("div");
    questionRow.className = "visual-card-question";
    questionRow.appendChild(createParagraph(question));

    const listenButton = document.createElement("button");
    listenButton.className = "listen-button";
    listenButton.type = "button";
    listenButton.textContent = "Ouvir";
    listenButton.addEventListener("click", () => speakText(question));
    questionRow.appendChild(listenButton);

    card.append(visualText, questionRow);
    return card;
}

function getVisualText() {
    return topicVisuals[shell.dataset.topic] || shell.dataset.topic.toUpperCase();
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
    feedbackBox.textContent = result.correct ? "Muito bem! Voce acertou." : result.feedback;
    speakText(feedbackBox.textContent);
    retryButton.hidden = result.correct;
}

newQuestionButton.addEventListener("click", generateQuestion);
sendAnswerButton.addEventListener("click", sendAnswer);
document.querySelector("#retryButton").addEventListener("click", () => {
    feedbackBox.hidden = true;
    retryButton.hidden = true;
    answerInput.focus();
});
hintButton.addEventListener("click", () => {
    hintBox.hidden = false;
    hintBox.textContent = state.hint || "Gere uma questao primeiro para receber uma dica.";
    speakText(hintBox.textContent);
});
