import { t } from "../i18n/index.js";

// Mode vocal façon ChatGPT, avec les API du navigateur (Web Speech) : aucune clé, aucun serveur.
// Écoute → transcription écrite dans la zone de message (masquée) → envoi au silence
// → lecture de la réponse phrase par phrase → nouvelle écoute, jusqu'à « Terminer ».
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const LANGUAGE = "fr-FR";
// Chrome coupe sans prévenir une lecture d'environ 15 s avec ses voix en ligne
// (« Google français ») : on lit donc la réponse par morceaux courts.
const MAX_CHUNK_LENGTH = 150;
// Filet de sécurité si le navigateur ne signale jamais la fin d'un morceau.
const SPEECH_TIMEOUT_MS_PER_CHAR = 120;
const SPEECH_TIMEOUT_MIN_MS = 6000;

export const voiceSupported = Boolean(SpeechRecognition && window.speechSynthesis);

function debug(message, ...details) {
  console.info(`[Kwatsur voix] ${message}`, ...details);
}

// Le texte lu à voix haute : sans gras Markdown ni puces, pour une lecture naturelle.
function speakableText(reply) {
  return reply.replace(/\*\*/g, "").replace(/^\s*[-•]\s*/gm, "").replace(/\s+/g, " ").trim();
}

// Découpe en phrases, regroupées tant qu'elles tiennent dans MAX_CHUNK_LENGTH caractères.
export function splitIntoChunks(text) {
  const sentences = text.match(/[^.!?;:]+[.!?;:]*\s*/g) || [text];
  const chunks = [];
  let current = "";
  for (const sentence of sentences) {
    for (const piece of sentence.length > MAX_CHUNK_LENGTH ? sentence.split(/,\s*/) : [sentence]) {
      if ((current + piece).length > MAX_CHUNK_LENGTH && current) {
        chunks.push(current.trim());
        current = "";
      }
      current += `${piece} `;
    }
  }
  if (current.trim()) {
    chunks.push(current.trim());
  }
  return chunks;
}

function frenchVoice() {
  return window.speechSynthesis.getVoices().find((voice) => voice.lang?.startsWith("fr")) || null;
}

export class VoiceMode {
  // `ui` : { overlay, status, transcript } ; `input` : zone de message (masquée pendant le vocal) ;
  // `sendMessage(text)` : envoie au chatbot et renvoie la réponse (texte) ou null en cas d'erreur.
  constructor(ui, input, sendMessage, onVisibilityChange) {
    this.ui = ui;
    this.input = input;
    this.sendMessage = sendMessage;
    this.onVisibilityChange = onVisibilityChange;
    this.active = false;
    this.recognition = null;
    // Références gardées : sinon Chrome peut libérer la lecture en cours et ne jamais finir.
    this.currentUtterance = null;
    this.speechTimer = null;
  }

  // Appelé directement par le clic sur le micro : ce clic autorise aussi la lecture à voix haute.
  start() {
    if (!voiceSupported || this.active) {
      return;
    }
    this.active = true;
    this.#unlockSpeech();
    this.ui.overlay.hidden = false;
    this.onVisibilityChange(true);
    this.#listen();
  }

  stop() {
    this.active = false;
    this.recognition?.abort();
    this.recognition = null;
    clearTimeout(this.speechTimer);
    window.speechSynthesis.cancel();
    this.currentUtterance = null;
    this.ui.overlay.hidden = true;
    this.input.value = "";
    this.onVisibilityChange(false);
  }

  // Chrome refuse speak() (« not-allowed ») s'il n'est pas lié à un geste de l'utilisateur :
  // une lecture vide pendant le clic débloque la synthèse pour la suite de la conversation.
  #unlockSpeech() {
    const silent = new SpeechSynthesisUtterance(" ");
    silent.volume = 0;
    window.speechSynthesis.speak(silent);
    window.speechSynthesis.getVoices();
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
      debug("erreur de reconnaissance :", event.error);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        this.#setState("error", t("voice.denied"));
        this.active = false;
      } else if (event.error === "no-speech") {
        this.#setState("listening", t("voice.noSpeech"));
      } else if (event.error === "network") {
        this.#setState("error", t("voice.network"));
        this.active = false;
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
    debug("envoi :", text);
    this.#setState("thinking", t("voice.thinking"));
    const reply = await this.sendMessage(text);
    this.input.value = "";
    if (!this.active) {
      return;
    }
    if (!reply) {
      this.#setState("error", t("voice.error"));
      setTimeout(() => this.#listen(), 2500);
      return;
    }
    debug("réponse reçue, lecture de", reply.length, "caractères");
    this.#speakChunks(splitIntoChunks(speakableText(reply)));
  }

  #speakChunks(chunks) {
    // La réponse reste affichée pendant toute la lecture (et après une erreur).
    this.ui.transcript.textContent = chunks.join(" ");
    this.#setState("speaking", t("voice.speaking"));
    this.#speakNext(chunks, 0);
  }

  #speakNext(chunks, index) {
    clearTimeout(this.speechTimer);
    if (!this.active) {
      return;
    }
    if (index >= chunks.length) {
      this.currentUtterance = null;
      this.#listen();
      return;
    }
    const utterance = new SpeechSynthesisUtterance(chunks[index]);
    utterance.lang = LANGUAGE;
    const voice = frenchVoice();
    if (voice) {
      utterance.voice = voice;
    }
    let finished = false;
    const next = () => {
      if (!finished) {
        finished = true;
        this.#speakNext(chunks, index + 1);
      }
    };
    utterance.onend = next;
    utterance.onerror = (event) => {
      debug("erreur de lecture :", event.error);
      if (event.error === "not-allowed") {
        // Lecture bloquée par le navigateur : la réponse reste à l'écran, on réécoute.
        finished = true;
        this.#setState("error", t("voice.speechBlocked"));
        setTimeout(() => this.#listen(), 4000);
        return;
      }
      next();
    };
    this.currentUtterance = utterance;
    this.speechTimer = setTimeout(() => {
      debug("fin de lecture non signalée, morceau suivant");
      next();
    }, Math.max(SPEECH_TIMEOUT_MIN_MS, chunks[index].length * SPEECH_TIMEOUT_MS_PER_CHAR));
    window.speechSynthesis.speak(utterance);
  }
}
