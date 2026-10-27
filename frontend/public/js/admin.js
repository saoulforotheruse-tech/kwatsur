import { createGallery } from "./components/images.js";
import { createElement, formatBoolean, formatDate, formatFcfa } from "./utils/format.js";
import { t } from "./i18n/index.js";
import { fetchAdminSubmissions, reviewSubmission } from "./services/api.js";

// Le jeton reste dans l'onglet (sessionStorage) : il n'est jamais écrit dans le code ni l'URL.
const TOKEN_STORAGE_KEY = "kwatsur.adminToken";
const FIELDS = [
  "title", "city", "neighborhood", "property_type", "monthly_rent", "bedrooms",
  "bathrooms", "furnished", "water_available", "electricity_available", "description",
  "location_description", "contact_information",
];
let busy = false;

const elements = {
  form: document.querySelector("#admin-login"),
  token: document.querySelector("#admin-token"),
  status: document.querySelector("#admin-status"),
  message: document.querySelector("#admin-message"),
  list: document.querySelector("#admin-list"),
  logout: document.querySelector("#admin-logout"),
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
    if (token) sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    else sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Stockage indisponible : le jeton reste dans le champ.
  }
}

function setBusy(value) {
  busy = value;
  for (const control of document.querySelectorAll(".admin-page input, .admin-page select, .admin-page button, .admin-page textarea")) {
    control.disabled = value;
  }
  elements.list.setAttribute("aria-busy", String(value));
}

function showMessage(message, isError = false) {
  elements.message.textContent = message;
  elements.message.classList.toggle("warning-text", isError);
}

function formatValue(name, value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  if (typeof value === "boolean") {
    return formatBoolean(value);
  }
  return name === "monthly_rent" ? `${formatFcfa(value)} / mois` : String(value);
}

function createSubmissionCard(submission) {
  const card = createElement("article", null, "admin-card");
  card.append(createElement("h2", submission.fields.title || t("admin.title", { id: submission.id })));
  card.append(createElement("p", `${t("admin.title", { id: submission.id })} · ${t(`submission.status.${submission.status}`)}`, "admin-card-status"));
  const dates = createElement("p", null, "muted-text");
  dates.textContent = [
    t("admin.created", { date: formatDate(submission.created_at) }),
    submission.submitted_at && t("admin.submitted", { date: formatDate(submission.submitted_at) }),
    submission.reviewed_at && t("admin.reviewed", { date: formatDate(submission.reviewed_at) }),
  ].filter(Boolean).join(" · ");
  card.append(dates);
  if (submission.approved_property_id !== null) {
    card.append(createElement("p", t("admin.published", { id: submission.approved_property_id }), "muted-text"));
  }

  const details = createElement("dl");
  for (const name of FIELDS) {
    const key = ["city", "neighborhood", "property_type", "monthly_rent", "bedrooms", "contact_information"].includes(name)
      ? `submission.field.${name}` : `admin.field.${name}`;
    const value = formatValue(name, submission.fields[name]);
    details.append(createElement("dt", t(key)), createElement("dd", value ?? t("card.unknown"), value === null ? "unknown" : null));
  }
  card.append(details);
  if (submission.images.length) {
    card.append(createGallery(submission.images));
  }
  if (submission.review_note) {
    card.append(createElement("p", t("admin.note", { note: submission.review_note }), "muted-text"));
  }

  if (submission.status === "pending") {
    const note = createElement("textarea");
    note.rows = 2;
    note.id = `review-note-${submission.id}`;
    note.maxLength = 500;
    const label = createElement("label", t("admin.noteLabel", { id: submission.id }));
    label.htmlFor = note.id;
    const approve = createElement("button", t("admin.approve"), "primary-button");
    const reject = createElement("button", t("admin.reject"), "ghost-button danger-button");
    for (const [button, action] of [[approve, "approve"], [reject, "reject"]]) {
      button.type = "button";
      button.addEventListener("click", () => review(submission.id, action, note.value));
    }
    const actions = createElement("div", null, "admin-actions");
    actions.append(approve, reject);
    card.append(label, note, actions);
  }
  return card;
}

async function loadSubmissions() {
  if (busy) return;
  if (!elements.token.value.trim()) {
    elements.list.replaceChildren();
    showMessage(t("admin.login"));
    return;
  }
  setBusy(true);
  showMessage(t("admin.loading"));
  try {
    const submissions = await fetchAdminSubmissions(elements.status.value, elements.token.value.trim());
    elements.list.replaceChildren(...submissions.map(createSubmissionCard));
    storeToken(elements.token.value.trim());
    showMessage(submissions.length ? t("admin.count", { count: submissions.length }) : t("admin.empty"));
  } catch (error) {
    elements.list.replaceChildren();
    if (error.status === 401 || error.status === 503) storeToken("");
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function review(submissionId, action, note) {
  if (busy) return;
  setBusy(true);
  showMessage(t("admin.reviewing"));
  try {
    await reviewSubmission(submissionId, action, note, elements.token.value.trim());
    elements.list.querySelector(`#review-note-${submissionId}`)?.closest("article").remove();
    showMessage(t(action === "approve" ? "admin.approved" : "admin.rejected", { id: submissionId }));
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  loadSubmissions();
});
elements.status.addEventListener("change", loadSubmissions);
elements.logout.addEventListener("click", () => {
  storeToken("");
  elements.token.value = "";
  elements.list.replaceChildren();
  showMessage(t("admin.loggedOut"));
  elements.token.focus();
});

elements.token.value = readToken();
if (elements.token.value) {
  loadSubmissions();
}
