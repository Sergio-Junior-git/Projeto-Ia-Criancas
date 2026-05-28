const shell = document.querySelector(".study-shell");
const csrfToken = document.querySelector("meta[name='csrf-token']").content;
const state = {
    requestId: null,
    hint: "",
    selectedOption: "",
    currentType: "short_answer",
    activityNumber: 1,
    isAnswering: false,
    seenQuestions: [],
};

let soundContext = null;

let availableVoices = [];

function refreshVoices() {
    if ("speechSynthesis" in window) {
        availableVoices = window.speechSynthesis.getVoices();
    }
}

refreshVoices();
if ("speechSynthesis" in window) {
    window.speechSynthesis.addEventListener("voiceschanged", refreshVoices);
}

function speakText(text) {
    if (!("speechSynthesis" in window)) {
        alert("Este navegador nao consegue ler o texto em voz alta.");
        return;
    }

    const voice = new SpeechSynthesisUtterance(text);
    voice.lang = "pt-BR";
    voice.voice = getSoftVoice();
    voice.rate = 0.78;
    voice.pitch = 1.05;
    voice.volume = 1;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(voice);
}

function getSoftVoice() {
    const preferredNames = ["Google português", "Google portugues", "Microsoft Francisca", "Francisca", "Maria", "Luciana"];
    return availableVoices.find((voice) => preferredNames.some((name) => voice.name.toLowerCase().includes(name.toLowerCase())))
        || availableVoices.find((voice) => voice.lang === "pt-BR")
        || availableVoices.find((voice) => voice.lang.startsWith("pt"))
        || null;
}

function playSound(type) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) {
        return;
    }
    soundContext = soundContext || new AudioContext();
    if (soundContext.state === "suspended") {
        soundContext.resume();
    }
    const notes = type === "success"
        ? [523.25, 659.25, 783.99, 1046.5]
        : [220, 196];
    const duration = type === "success" ? 0.14 : 0.18;
    const volume = type === "success" ? 0.12 : 0.08;

    notes.forEach((frequency, index) => {
        const oscillator = soundContext.createOscillator();
        const gain = soundContext.createGain();
        oscillator.type = type === "success" ? "triangle" : "sine";
        oscillator.frequency.value = frequency;
        gain.gain.setValueAtTime(0, soundContext.currentTime + index * duration);
        gain.gain.linearRampToValueAtTime(volume, soundContext.currentTime + index * duration + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.001, soundContext.currentTime + (index + 1) * duration);
        oscillator.connect(gain);
        gain.connect(soundContext.destination);
        oscillator.start(soundContext.currentTime + index * duration);
        oscillator.stop(soundContext.currentTime + (index + 1) * duration);
    });
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

const imageDrawings = {
    casa: `
        <svg viewBox="0 0 240 180" role="img" aria-label="casa">
            <rect x="54" y="78" width="132" height="78" rx="8" fill="#ffd166"/>
            <path d="M38 88 120 24l82 64" fill="#ff5c8a"/>
            <rect x="103" y="112" width="34" height="44" rx="4" fill="#7c5cff"/>
            <rect x="70" y="98" width="28" height="24" rx="4" fill="#eaf6ff"/>
            <rect x="146" y="98" width="28" height="24" rx="4" fill="#eaf6ff"/>
        </svg>`,
    bola: `
        <svg viewBox="0 0 240 180" role="img" aria-label="bola">
            <circle cx="120" cy="90" r="62" fill="#ffffff" stroke="#2477ff" stroke-width="10"/>
            <path d="M72 90h96M120 28c-28 24-28 100 0 124M120 28c28 24 28 100 0 124" fill="none" stroke="#ff5c8a" stroke-width="8"/>
        </svg>`,
    sol: `
        <svg viewBox="0 0 240 180" role="img" aria-label="sol">
            <circle cx="120" cy="90" r="42" fill="#ffb703"/>
            <g stroke="#ffb703" stroke-width="12" stroke-linecap="round">
                <path d="M120 20v22M120 138v22M50 90H28M212 90h-22M70 40l16 16M170 124l16 16M170 56l16-16M70 140l16-16"/>
            </g>
        </svg>`,
    livro: `
        <svg viewBox="0 0 240 180" role="img" aria-label="livro">
            <path d="M40 42h74c16 0 28 12 28 28v78H68c-16 0-28-12-28-28z" fill="#7c5cff"/>
            <path d="M126 42h74v78c0 16-12 28-28 28h-74V70c0-16 12-28 28-28z" fill="#21c4a8"/>
            <path d="M120 52v96" stroke="#fff" stroke-width="8"/>
        </svg>`,
    lapis: `
        <svg viewBox="0 0 240 180" role="img" aria-label="lapis">
            <rect x="48" y="78" width="116" height="28" rx="8" fill="#ffb703"/>
            <path d="M164 78 202 92l-38 14z" fill="#f4a261"/>
            <path d="M194 89 210 92l-16 3z" fill="#243047"/>
            <rect x="34" y="78" width="20" height="28" rx="5" fill="#ff5c8a"/>
        </svg>`,
    gato: `
        <svg viewBox="0 0 240 180" role="img" aria-label="gato">
            <circle cx="120" cy="92" r="50" fill="#ffd166"/>
            <path d="M84 56 72 26l34 18M156 44l34-18-12 30" fill="#ffd166"/>
            <circle cx="102" cy="88" r="6" fill="#243047"/>
            <circle cx="138" cy="88" r="6" fill="#243047"/>
            <path d="M116 106h8l-4 6zM96 118h48" stroke="#243047" stroke-width="6" stroke-linecap="round"/>
        </svg>`,
    default: `
        <svg viewBox="0 0 240 180" role="img" aria-label="estrela">
            <path d="m120 24 22 45 50 7-36 35 8 49-44-23-44 23 8-49-36-35 50-7z" fill="#ffb703"/>
        </svg>`,
};

function setGameMode(mode) {
    shell.dataset.gameMode = mode;
}

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

async function generateQuestion(attempt = 1) {
    setGameMode("playing");
    feedbackBox.hidden = true;
    hintBox.hidden = true;
    retryButton.hidden = true;
    optionsBox.innerHTML = "";
    answerInput.value = "";
    state.selectedOption = "";
    state.requestId = null;
    state.isAnswering = false;

    newQuestionButton.disabled = true;
    sendAnswerButton.disabled = true;
    activityBox.replaceChildren(createVisualCard("...", "Preparando..."));

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
    difficultyLabel.textContent = `Atividade ${state.activityNumber} | Nivel ${activity.difficulty}`;
    const cleanQuestion = cleanQuestionText(activity.question);
    if (state.seenQuestions.includes(cleanQuestion) && attempt < 4) {
        await generateQuestion(attempt + 1);
        return;
    }
    state.seenQuestions.push(cleanQuestion);
    state.seenQuestions = state.seenQuestions.slice(-12);
    activityBox.replaceChildren(createVisualCard(getVisualText(cleanQuestion), cleanQuestion));

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
                setTimeout(sendAnswer, 450);
            });
            optionsBox.appendChild(button);
        });
    } else {
        answerLabel.hidden = false;
        answerInput.focus();
    }

    speakText(cleanQuestion);
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
    if (visual.trim().startsWith("<svg")) {
        visualText.classList.add("has-image");
        visualText.innerHTML = visual;
    } else {
        visualText.textContent = visual;
    }

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

function cleanQuestionText(text) {
    return String(text || "")
        .replace(/^(fase|jogo|desafio rapido|atividade|questao de revisao|exercicio guiado|pratica do assunto)\s*:\s*/i, "")
        .trim();
}

function getVisualText(question) {
    const text = `${shell.dataset.topic} ${question}`.toLowerCase();
    const imageKey = Object.keys(imageDrawings).find((key) => key !== "default" && text.includes(key));
    if (imageKey) {
        return imageDrawings[imageKey];
    }
    if (["figuras e palavras", "nomes de objetos", "animais", "objetos"].includes(shell.dataset.topic)) {
        return imageDrawings.default;
    }
    return topicVisuals[shell.dataset.topic] || shell.dataset.topic.toUpperCase();
}

async function sendAnswer() {
    if (state.isAnswering) {
        return;
    }
    if (!state.requestId) {
        await generateQuestion();
        return;
    }

    const answer = state.currentType === "multiple_choice" ? state.selectedOption : answerInput.value;
    if (!answer.trim()) {
        feedbackBox.hidden = false;
        feedbackBox.className = "feedback-box error";
        feedbackBox.textContent = "Escolha uma resposta para continuar.";
        speakText(feedbackBox.textContent);
        return;
    }

    state.isAnswering = true;
    sendAnswerButton.disabled = true;
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
    state.isAnswering = false;
    sendAnswerButton.disabled = false;
    if (!response.ok) {
        feedbackBox.hidden = false;
        feedbackBox.className = "feedback-box error";
        feedbackBox.textContent = result.error || "Nao foi possivel corrigir a resposta.";
        return;
    }
    if (result.correct) {
        showSuccessScreen(result.next_difficulty);
        return;
    }

    feedbackBox.hidden = false;
    feedbackBox.className = "feedback-box error";
    feedbackBox.textContent = "Quase! Tente mais uma vez.";
    window.speechSynthesis?.cancel();
    playSound("error");
    retryButton.hidden = false;
}

function showSuccessScreen(nextDifficulty) {
    setGameMode("success");
    optionsBox.innerHTML = "";
    answerInput.value = "";
    answerLabel.hidden = true;
    hintBox.hidden = true;
    feedbackBox.hidden = true;
    retryButton.hidden = true;

    const screen = document.createElement("div");
    screen.className = "success-screen";

    const badge = document.createElement("div");
    badge.className = "success-badge";
    badge.textContent = "OK";

    const title = document.createElement("h2");
    title.textContent = "Voce acertou!";

    const text = document.createElement("p");
    text.textContent = `Proximo nivel: ${nextDifficulty}`;

    const actions = document.createElement("div");
    actions.className = "success-actions";

    const continueButton = document.createElement("button");
    continueButton.className = "primary-button big-action";
    continueButton.type = "button";
    continueButton.textContent = "Continuar";
    continueButton.addEventListener("click", async () => {
        continueButton.disabled = true;
        state.activityNumber += 1;
        await generateQuestion();
    });

    const homeLink = document.createElement("a");
    homeLink.className = "home-button";
    homeLink.href = "/dashboard";
    homeLink.textContent = "Inicio";

    actions.append(continueButton, homeLink);
    screen.append(badge, title, text, actions);
    activityBox.replaceChildren(screen);
    window.speechSynthesis?.cancel();
    playSound("success");
}

newQuestionButton.addEventListener("click", generateQuestion);
sendAnswerButton.addEventListener("click", sendAnswer);
document.querySelector("#retryButton").addEventListener("click", () => {
    feedbackBox.hidden = true;
    retryButton.hidden = true;
    if (state.currentType === "short_answer") {
        answerInput.focus();
    }
});
hintButton.addEventListener("click", () => {
    hintBox.hidden = false;
    hintBox.textContent = state.hint || "Gere uma questao primeiro para receber uma dica.";
    speakText(hintBox.textContent);
});
