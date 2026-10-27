import { createGallery } from "./components/images.js";
import { createElement, formatFcfa } from "./utils/format.js";

// Le jeton reste dans l'onglet (sessionStorage) : il n'est jamais écrit dans le code ni l'URL.
const TOKEN_STORAGE_KEY = "kwatsur.adminToken";
const FIELDS = [
  ["title", "Titre"],
  ["city", "Ville"],
  ["neighborhood", "Quartier"],
  ["property_type", "Type"],
  ["monthly_rent", "Loyer mensuel"],
  ["bedrooms", "Chambres"],
  ["bathrooms", "Salles de bain"],
  ["furnished", "Meublé"],
  ["water_available", "Eau"],
  ["electricity_available", "Électricité"],
  ["description", "Description"],
  ["location_description", "Repères"],
  ["contact_information", "Contact"],
];

const elements = {
  form: document.querySelector("#admin-login"),
  token: document.querySelector("#admin-token"),
  status: document.querySelector("#admin-status"),
  message: document.querySelector("#admin-message"),
  list: document.querySelector("#admin-list"),
};

function readToken() {
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

function storeToken(token) {
  try {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // Stockage indisponible : le jeton reste dans le champ.
  }
}

async function adminRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Admin-Token": elements.token.value, ...options.headers },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(typeof body?.detail === "string" ? body.detail : `Erreur ${response.status}`);
  }
  return body;
}

function formatValue(name, value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  if (typeof value === "boolean") {
    return value ? "Oui" : "Non";
  }
  return name === "monthly_rent" ? `${formatFcfa(value)} / mois` : String(value);
}

function createSubmissionCard(submission) {
  const card = createElement("article", null, "admin-card");
  card.append(createElement("h2", `Proposition n°${submission.id}`));

  const details = createElement("dl");
  for (const [name, label] of FIELDS) {
    const value = formatValue(name, submission.fields[name]);
    details.append(createElement("dt", label), createElement("dd", value ?? "Non renseigné", value ? null : "unknown"));
  }
  card.append(details);
  if (submission.images.length) {
    card.append(createGallery(submission.images));
  }
  if (submission.review_note) {
    card.append(createElement("p", `Note : ${submission.review_note}`, "muted-text"));
  }

  if (submission.status === "pending") {
    const note = createElement("textarea");
    note.rows = 2;
    note.placeholder = "Note pour la décision (facultative)";
    const approve = createElement("button", "Approuver et publier", "primary-button");
    const reject = createElement("button", "Refuser", "ghost-button danger-button");
    for (const [button, action] of [[approve, "approve"], [reject, "reject"]]) {
      button.type = "button";
      button.addEventListener("click", () => review(submission.id, action, note.value));
    }
    const actions = createElement("div", null, "admin-actions");
    actions.append(approve, reject);
    card.append(note, actions);
  }
  return card;
}

async function loadSubmissions() {
  elements.message.textContent = "Chargement…";
  try {
    const submissions = await adminRequest(`/api/admin/submissions?status=${elements.status.value}`);
    elements.list.replaceChildren(...submissions.map(createSubmissionCard));
    elements.message.textContent = submissions.length
      ? `${submissions.length} proposition(s).`
      : "Aucune proposition dans ce statut.";
  } catch (error) {
    elements.list.replaceChildren();
    elements.message.textContent = error.message;
  }
}

async function review(submissionId, action, note) {
  try {
    await adminRequest(`/api/admin/submissions/${submissionId}/${action}`, {
      method: "POST",
      body: JSON.stringify({ note: note.trim() || null }),
    });
    await loadSubmissions();
  } catch (error) {
    elements.message.textContent = error.message;
  }
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  storeToken(elements.token.value);
  loadSubmissions();
});
elements.status.addEventListener("change", loadSubmissions);

elements.token.value = readToken();
if (elements.token.value) {
  loadSubmissions();
}
