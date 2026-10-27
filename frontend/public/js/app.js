import { renderCriteria } from "./components/criteria_chips.js";
import { ChatThread, describeResponse } from "./components/chat.js";
import {
  MAX_COMPARISON_ITEMS,
  renderComparison,
  renderProperties,
} from "./components/property_cards.js";
import { createImageFigure } from "./components/images.js";
import { renderSubmission } from "./components/submission_panel.js";
import { VoiceMode, voiceSupported } from "./components/voice_mode.js";
import { t } from "./i18n/index.js";
import {
  createContactDraft,
  fetchConversation,
  fetchHealth,
  fetchImageStatus,
  fetchSubmission,
  generateImage,
  searchProperties,
  sendChatMessage,
  uploadSubmissionPhoto,
} from "./services/api.js";

const CONVERSATION_STORAGE_KEY = "kwatsur.conversationId";

const elements = {
  chatForm: document.querySelector("#chat-form"),
  chatInput: document.querySelector("#chat-input"),
  chatMessages: document.querySelector("#chat-messages"),
  newConversationButton: document.querySelector("#new-conversation"),
  exampleButtons: document.querySelectorAll("[data-example]"),
  criteria: document.querySelector("#criteria"),
  filterForm: document.querySelector("#search-form"),
  results: document.querySelector("#property-results"),
  resultsDisclosure: document.querySelector("#results-disclosure"),
  resultCount: document.querySelector("#result-count"),
  statusMessage: document.querySelector("#status-message"),
  statusText: document.querySelector("#status-text"),
  systemStatus: document.querySelector("#system-status"),
  systemStatusText: document.querySelector("#system-status-text"),
  compareTray: document.querySelector("#compare-tray"),
  compareTrayText: document.querySelector("#compare-tray-text"),
  compareTrayButton: document.querySelector("#compare-tray-button"),
  photoInput: document.querySelector("#photo-input"),
  photoForm: document.querySelector("#photo-form"),
  photoMessage: document.querySelector("#photo-message"),
  generateForm: document.querySelector("#generate-form"),
  generatorStatus: document.querySelector("#generator-status"),
  generatorResult: document.querySelector("#generator-result"),
  voiceButton: document.querySelector("#voice-button"),
  voiceStop: document.querySelector("#voice-stop"),
  chatPanel: document.querySelector(".chat-panel"),
  comparisonSection: document.querySelector("#comparison"),
  comparisonTable: document.querySelector("#comparison-table"),
  clearComparisonButton: document.querySelector("#clear-comparison"),
  contactDialog: document.querySelector("#contact-dialog"),
  contactMessage: document.querySelector("#contact-message"),
  contactNotice: document.querySelector("#contact-notice"),
  contactDetails: document.querySelector("#contact-details"),
  copyContactButton: document.querySelector("#copy-contact"),
};

const state = {
  conversationId: readStoredConversationId(),
  results: [],
  selected: new Map(),
  submission: null,
};
const submissionPanel = {
  root: document.querySelector("#submission-panel"),
  status: document.querySelector("#submission-status"),
  fields: document.querySelector("#submission-fields"),
  photos: document.querySelector("#submission-photos"),
  form: document.querySelector("#photo-form"),
};
const chat = new ChatThread(elements.chatMessages);

// --- Mémorisation locale de la conversation (facultative, peut être bloquée) ---
function readStoredConversationId() {
  try {
    return sessionStorage.getItem(CONVERSATION_STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeConversationId(conversationId) {
  try {
    if (conversationId) {
      sessionStorage.setItem(CONVERSATION_STORAGE_KEY, conversationId);
    } else {
      sessionStorage.removeItem(CONVERSATION_STORAGE_KEY);
    }
  } catch {
    // Stockage indisponible : la conversation reste valable tant que la page est ouverte.
  }
}

// --- Résultats et comparaison ---
const cardHandlers = {
  isSelected: (propertyId) => state.selected.has(propertyId),
  canSelectMore: () => state.selected.size < MAX_COMPARISON_ITEMS,
  onToggleCompare(property, checked) {
    if (checked) {
      state.selected.set(property.id, property);
    } else {
      state.selected.delete(property.id);
    }
    refreshResults();
  },
  onContact: openContactDraft,
};

function refreshResults() {
  renderProperties(elements.results, state.results, cardHandlers);
  const count = state.selected.size;
  elements.comparisonSection.hidden = count === 0;
  renderComparison(elements.comparisonTable, [...state.selected.values()]);
  elements.compareTray.hidden = count === 0;
  elements.compareTrayText.textContent = t("compare.tray", { count });
}

function setStatus(message, isError = false) {
  elements.statusMessage.hidden = !message;
  elements.statusText.textContent = message;
  elements.statusMessage.classList.toggle("error", isError);
}

function showResults(results, total) {
  state.results = results;
  elements.resultCount.textContent = t("results.count", { count: total });
  setStatus(total ? "" : t("results.empty"));
  refreshResults();
}

function showResultsError(message) {
  setStatus(message, true);
  elements.resultsDisclosure.open = true;
}

// --- Bandeau d'état : source des annonces et fournisseur IA réellement configurés ---
async function showSystemStatus() {
  const pill = elements.systemStatus;
  try {
    const health = await fetchHealth();
    const data = t(`status.source.${health.listing_source}`);
    const demo = health.llm_provider === "rules" || health.llm_provider === "none";
    pill.classList.add(demo ? "demo" : "live");
    elements.systemStatusText.textContent = demo
      ? t("status.demo", { data })
      : t("status.live", { data, model: t(`status.model.${health.llm_provider}`) });
  } catch {
    pill.classList.add("down");
    elements.systemStatusText.textContent = t("status.down");
  }
}

// La zone de saisie grandit avec le texte, jusqu'à la hauteur maximale fixée par le CSS.
function resizeComposer() {
  const input = elements.chatInput;
  input.style.setProperty("height", "auto");
  input.style.setProperty("height", `${input.scrollHeight}px`);
}

// --- Conversation avec l'agent ---
async function submitChatMessage(message) {
  const submitButton = elements.chatForm.querySelector('button[type="submit"]');
  chat.addUserMessage(message);
  chat.showLoading();
  submitButton.disabled = true;
  elements.chatInput.disabled = true;

  try {
    const response = await sendChatMessage(message, state.conversationId);
    state.conversationId = response.conversation_id;
    storeConversationId(state.conversationId);
    chat.hideLoading();
    chat.addAssistantMessage(response.reply, describeResponse(response), response.images);
    renderCriteria(elements.criteria, response.criteria);
    if (response.submission) {
      state.submission = response.submission;
      renderSubmission(submissionPanel, state.submission);
    }
    if (response.searched) {
      showResults(response.results, response.total);
    }
    return response.reply;
  } catch (error) {
    chat.hideLoading();
    if (error.status === 404) {
      // Conversation expirée ou inconnue : on repart de zéro.
      resetConversation();
    }
    chat.addErrorMessage(error.message);
    return null;
  } finally {
    submitButton.disabled = false;
    elements.chatInput.disabled = false;
    elements.chatInput.focus();
  }
}

function resetConversation() {
  state.conversationId = null;
  state.submission = null;
  renderSubmission(submissionPanel, null);
  storeConversationId(null);
  chat.reset();
  renderCriteria(elements.criteria, null);
}

async function restoreConversation() {
  chat.reset();
  renderCriteria(elements.criteria, null);
  if (!state.conversationId) {
    return;
  }
  try {
    const conversation = await fetchConversation(state.conversationId);
    for (const message of conversation.messages) {
      if (message.role === "user") {
        chat.addUserMessage(message.content);
      } else {
        chat.addAssistantMessage(message.content);
      }
    }
    renderCriteria(elements.criteria, conversation.criteria);
  } catch {
    resetConversation();
  }
}

// --- Recherche manuelle par filtres (fonctionne sans IA) ---
function readFilterQuery(form) {
  const formData = new FormData(form);
  const query = new URLSearchParams();
  for (const field of ["city", "neighborhood", "property_type", "min_rent", "max_rent", "bedrooms"]) {
    const value = formData.get(field)?.toString().trim();
    if (value) {
      query.set(field, value);
    }
  }
  for (const field of ["water_available", "electricity_available"]) {
    if (formData.has(field)) {
      query.set(field, "true");
    }
  }
  return query;
}

async function submitFilterSearch(event) {
  event.preventDefault();
  const submitButton = elements.filterForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  setStatus(t("results.loading"));
  try {
    const data = await searchProperties(readFilterQuery(elements.filterForm));
    showResults(data.results, data.total);
  } catch (error) {
    showResultsError(error.message);
  } finally {
    submitButton.disabled = false;
  }
}

// --- Brouillon de prise de contact ---
async function openContactDraft(property) {
  try {
    const draft = await createContactDraft(property.id);
    elements.contactMessage.value = draft.message;
    elements.contactNotice.textContent = draft.notice;
    elements.contactDetails.textContent = draft.contact_information
      ? `Coordonnées fournies par la source : ${draft.contact_information}`
      : "";
    elements.contactDialog.showModal();
  } catch (error) {
    showResultsError(error.message);
  }
}

async function copyContactMessage() {
  try {
    await navigator.clipboard.writeText(elements.contactMessage.value);
    elements.contactNotice.textContent = t("contact.copied");
  } catch {
    elements.contactMessage.select();
    elements.contactNotice.textContent = t("contact.copyFailed");
  }
}

// --- Photos de l'annonce proposée par le propriétaire ---
async function uploadPhoto() {
  const file = elements.photoInput.files[0];
  if (!file || !state.submission || !state.conversationId) {
    return;
  }
  const room = new FormData(elements.photoForm).get("room");
  elements.photoMessage.textContent = t("submission.uploading");
  try {
    await uploadSubmissionPhoto(state.submission.id, state.conversationId, file, room);
    state.submission = await fetchSubmission(state.submission.id, state.conversationId);
    renderSubmission(submissionPanel, state.submission);
    elements.photoMessage.textContent = t("submission.uploaded");
  } catch (error) {
    elements.photoMessage.textContent = error.message;
  } finally {
    elements.photoInput.value = "";
  }
}

// --- Génération d'une image illustrative (jamais présentée comme une photo) ---
async function showGeneratorStatus() {
  try {
    const status = await fetchImageStatus();
    elements.generatorStatus.textContent = status.available
      ? t("generator.remaining", { count: status.remaining_today })
      : t("generator.unavailable");
  } catch {
    elements.generatorStatus.textContent = t("generator.unavailable");
  }
}

async function submitGeneration(event) {
  event.preventDefault();
  const submitButton = elements.generateForm.querySelector('button[type="submit"]');
  const formData = new FormData(elements.generateForm);
  submitButton.disabled = true;
  elements.generatorStatus.textContent = t("generator.loading");
  try {
    const image = await generateImage(formData.get("description").toString().trim(), formData.get("room"));
    elements.generatorResult.replaceChildren(createImageFigure(image));
    elements.generatorStatus.textContent = t("generator.done");
    showGeneratorStatus();
  } catch (error) {
    elements.generatorStatus.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
}

// --- Branchement des événements ---
elements.chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = elements.chatInput.value.trim();
  if (message) {
    elements.chatInput.value = "";
    resizeComposer();
    submitChatMessage(message);
  }
});

elements.chatInput.addEventListener("input", resizeComposer);

elements.chatInput.addEventListener("keydown", (event) => {
  // Entrée envoie, Maj+Entrée ajoute une ligne.
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.chatForm.requestSubmit();
  }
});

for (const button of elements.exampleButtons) {
  button.addEventListener("click", () => {
    elements.chatInput.value = button.dataset.example;
    resizeComposer();
    elements.chatInput.focus();
  });
}

elements.newConversationButton.addEventListener("click", () => {
  resetConversation();
  state.results = [];
  state.selected.clear();
  showResults([], 0);
  setStatus(t("results.idle"));
  elements.resultCount.textContent = "";
  elements.resultsDisclosure.open = false;
});

elements.filterForm.addEventListener("submit", submitFilterSearch);
elements.clearComparisonButton.addEventListener("click", () => {
  state.selected.clear();
  refreshResults();
});
elements.copyContactButton.addEventListener("click", copyContactMessage);
elements.compareTrayButton.addEventListener("click", () => {
  elements.resultsDisclosure.open = true;
  elements.comparisonSection.scrollIntoView({ behavior: "smooth", block: "start" });
});

// --- Conversation vocale : l'interface de message est masquée pendant le vocal ---
const voiceMode = new VoiceMode(
  {
    overlay: document.querySelector("#voice-overlay"),
    status: document.querySelector("#voice-status"),
    transcript: document.querySelector("#voice-transcript"),
  },
  elements.chatInput,
  (text) => {
    // Même chemin qu'un message tapé : il apparaît dans le fil (masqué) et la réponse aussi.
    elements.chatInput.value = "";
    return submitChatMessage(text);
  },
  (voiceActive) => elements.chatPanel.classList.toggle("voice-active", voiceActive),
);
elements.voiceButton.hidden = !voiceSupported;
elements.voiceButton.addEventListener("click", () => voiceMode.start());
elements.voiceStop.addEventListener("click", () => voiceMode.stop());

elements.photoInput.addEventListener("change", uploadPhoto);
elements.generateForm.addEventListener("submit", submitGeneration);

showSystemStatus();
showGeneratorStatus();
restoreConversation();
