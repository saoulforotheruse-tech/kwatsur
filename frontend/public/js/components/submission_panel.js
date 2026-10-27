import { t } from "../i18n/index.js";
import { createElement, formatFcfa } from "../utils/format.js";
import { createImageFigure } from "./images.js";

const DISPLAYED_FIELDS = ["city", "neighborhood", "property_type", "monthly_rent", "bedrooms", "contact_information"];

function fieldText(name, value) {
  if (name === "monthly_rent") {
    return `${formatFcfa(value)} / mois`;
  }
  return String(value);
}

// Affiche la proposition d'annonce du propriétaire : statut, informations réunies, photos.
export function renderSubmission(panel, submission) {
  panel.root.hidden = !submission;
  if (!submission) {
    return;
  }
  panel.status.textContent = t(`submission.status.${submission.status}`);
  panel.status.dataset.status = submission.status;

  const list = createElement("ul", null, "chip-list");
  for (const name of DISPLAYED_FIELDS) {
    const value = submission.fields[name];
    if (value !== null && value !== undefined) {
      list.append(createElement("li", `${t(`submission.field.${name}`)} : ${fieldText(name, value)}`, "chip"));
    }
  }
  const missing = submission.missing_fields.map((name) => t(`submission.field.${name}`));
  const summary = missing.length
    ? createElement("p", t("submission.missing", { fields: missing.join(", ") }), "muted-text")
    : createElement("p", t("submission.complete"), "muted-text");
  panel.fields.replaceChildren(list, summary);

  panel.photos.replaceChildren(...submission.images.map((image) => createImageFigure(image, { compact: true })));
  // On ne peut plus ajouter de photo une fois la proposition traitée.
  panel.form.hidden = !["draft", "pending"].includes(submission.status);
}
