import { t } from "../i18n/index.js";
import { createElement, formatFcfa } from "../utils/format.js";

function criterionLabels(criteria) {
  const labels = [];
  for (const field of ["city", "neighborhood", "property_type"]) {
    if (criteria[field]) {
      labels.push(`${t(`criteria.${field}`)} : ${criteria[field]}`);
    }
  }
  for (const field of ["min_rent", "max_rent"]) {
    if (criteria[field] !== null && criteria[field] !== undefined) {
      labels.push(`${t(`criteria.${field}`)} : ${formatFcfa(criteria[field])}`);
    }
  }
  if (criteria.bedrooms !== null && criteria.bedrooms !== undefined) {
    labels.push(`${t("criteria.bedrooms")} : ${criteria.bedrooms}`);
  }
  for (const field of ["water_available", "electricity_available"]) {
    if (criteria[field]) {
      labels.push(t(`criteria.${field}`));
    }
  }
  if (criteria.furnished !== null && criteria.furnished !== undefined) {
    labels.push(`${t("criteria.furnished")} : ${criteria.furnished ? "oui" : "non"}`);
  }
  for (const preference of criteria.preferences || []) {
    labels.push(`${t("criteria.preferences")} : ${preference}`);
  }
  return labels;
}

export function renderCriteria(container, criteria) {
  container.replaceChildren();
  const labels = criteria ? criterionLabels(criteria) : [];
  if (!labels.length) {
    container.append(createElement("p", t("criteria.empty"), "muted-text"));
    return;
  }
  const list = createElement("ul", null, "chip-list");
  for (const label of labels) {
    list.append(createElement("li", label, "chip"));
  }
  container.append(list);
}
