import { t } from "../i18n/index.js";

// Mode vocal façon ChatGPT, avec les API du navigateur (Web Speech) : aucune clé, aucun serveur.
// Écoute → transcription écrite dans la zone de message (masquée) → envoi au silence
// → lecture de la réponse → nouvelle écoute, jusqu'à « Terminer ».
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const LANGUAGE = "fr-FR";

export const voiceSupported = Boolean(SpeechRecognition && window.speechSynthesis);

// Le texte lu à voix haute : sans gras Markdown ni puces, pour une lecture naturelle.
function speakableText(reply) {
  return reply.replace(/\*\*/g, "").replace(/^\s*[-•]\s*/gm, "").replace(/\s+/g, " ").trim();
}

function frenchVoice() {
  return window.speechSynthesis.getVoices().find((voice) => voice.lang?.startsWith("fr")) || null;
}

export class VoiceMode {
  // `ui` : { overlay, status, transcript, orb } ; `input` : zone de message (masquée pendant le vocal) ;
  // `sendMessage(text)` : envoie au chatbot et renvoie la réponse (texte) ou null en cas d'erreur.
  constructor(ui, input, sendMessage, onVisibilityChange) {
    this.ui = ui;
    this.input = input;
    this.sendMessage = sendMessage;
    this.onVisibilityChange = onVisibilityChange;
    this.active = false;
    this.recognition = null;
  }

  start() {
    if (!voiceSupported || this.active) {
      return;
    }
    this.active = true;
    this.ui.overlay.hidden = false;
    this.onVisibilityChange(true);
    this.#listen();
  }

  stop() {
    this.active = false;
    this.recognition?.abort();
    this.recognition = null;
    window.speechSynthesis.cancel();
    this.ui.overlay.hidden = true;
    this.input.value = "";
    this.onVisibilityChange(false);
  }

  #setState(state, message) {
    this.ui.overlay.dataset.state = state;
    this.ui.status.textContent = message;
  }

  #listen() {
    if (!this.active) {
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = LANGUAGE;
    recognition.interimResults = true;
    // Une phrase par écoute : le navigateur s'arrête tout seul quand la personne se tait.
    recognition.continuous = false;
    this.recognition = recognition;
    this.input.value = "";
    this.ui.transcript.textContent = "";
    this.#setState("listening", t("voice.listening"));

    recognition.onresult = (event) => {
      const text = Array.from(event.results, (result) => result[0].transcript).join(" ").trim();
      // La transcription s'écrit dans la zone de message, comme si on la tapait.
      this.input.value = text;
      this.ui.transcript.textContent = text;
    };
    recognition.onerror = (event) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        this.#setState("error", t("voice.denied"));
        this.active = false;
      } else if (event.error === "no-speech") {
        this.#setState("listening", t("voice.noSpeech"));
      }
    };
    recognition.onend = () => this.#onSilence();
    recognition.start();
  }

  async #onSilence() {
    this.recognition = null;
    if (!this.active) {
      return;
    }
    const text = this.input.value.trim();
    if (!text) {
      this.#listen();
      return;
    }
    this.#setState("thinking", t("voice.thinking"));
    const reply = await this.sendMessage(text);
    this.input.value = "";
    if (!this.active) {
      return;
    }
    if (!reply) {
      this.#setState("error", t("voice.error"));
      setTimeout(() => this.#listen(), 1500);
      return;
    }
    this.#speak(reply);
  }

  #speak(reply) {
    const utterance = new SpeechSynthesisUtterance(speakableText(reply));
    utterance.lang = LANGUAGE;
    const voice = frenchVoice();
    if (voice) {
      utterance.voice = voice;
    }
    this.ui.transcript.textContent = speakableText(reply);
    this.#setState("speaking", t("voice.speaking"));
    // Fin de la lecture (ou erreur) : on écoute de nouveau, comme une vraie conversation.
    utterance.onend = () => this.#listen();
    utterance.onerror = () => this.#listen();
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }
}
