import { t } from "../i18n/index.js";
import {
  createElement,
  formatBedrooms,
  formatBoolean,
  formatDate,
  formatListingStatus,
  formatRent,
} from "../utils/format.js";

export const MAX_COMPARISON_ITEMS = 3;

function appendList(parent, title, items, className) {
  if (!items?.length) {
    return;
  }
  parent.append(createElement("h4", title));
  const list = createElement("ul", null, className);
  for (const item of items) {
    list.append(createElement("li", item));
  }
  parent.append(list);
}

function createFacts(property) {
  const facts = createElement("ul", null, "property-facts");
  for (const fact of [
    property.property_type,
    formatBedrooms(property.bedrooms),
    `Eau : ${formatBoolean(property.water_available, "oui", "non")}`,
    `Électricité : ${formatBoolean(property.electricity_available, "oui", "non")}`,
    `Meublé : ${formatBoolean(property.furnished, "oui", "non")}`,
    formatListingStatus(property.listing_status),
  ]) {
    facts.append(createElement("li", fact));
  }
  return facts;
}

function createExplanation(result) {
  const details = createElement("details", null, "property-detail");
  details.append(createElement("summary", t("card.details")));
  details.append(createElement("p", t("card.points", { points: result.match_points }), "muted-text"));
  appendList(details, t("card.reasons"), result.reasons, "reason-list");
  appendList(details, t("card.tradeoffs"), result.tradeoffs, "tradeoff-list");
  appendList(details, t("card.toVerify"), result.to_verify, "verify-list");
  appendList(details, t("card.missing"), result.missing_information, "missing-list");
  return details;
}

function createSourceLabel(property) {
  const label = property.source_url ? createElement("a") : createElement("span");
  label.className = "property-source";
  label.textContent = t("card.source", { name: property.source_name });
  if (property.source_url) {
    label.href = property.source_url;
    label.target = "_blank";
    label.rel = "noopener noreferrer";
  }
  return label;
}

function createPropertyCard(result, handlers) {
  const { property } = result;
  const card = createElement("article", null, "property-card");

  const header = createElement("div", null, "property-card-header");
  header.append(createElement("span", `#${result.rank}`, "rank-badge"));
  header.append(createElement("h3", property.title));
  if (property.source_is_demo) {
    header.append(createElement("span", t("card.demo"), "demo-badge"));
  }
  card.append(header);

  const area = [property.neighborhood, property.city].filter(Boolean).join(", ");
  card.append(createElement("p", area || "Localisation non renseignée", "property-location"));
  card.append(createElement("p", formatRent(property), "property-rent"));
  card.append(createFacts(property));

  if (result.reasons.length) {
    card.append(createElement("p", result.reasons.slice(0, 2).join(" "), "property-summary"));
  }
  if (result.risk_signals.length) {
    const risks = createElement("div", null, "risk-box");
    appendList(risks, t("card.risks"), result.risk_signals, "risk-list");
    card.append(risks);
  }
  card.append(
    createElement(
      "p",
      property.last_seen_at
        ? t("card.lastSeen", { date: formatDate(property.last_seen_at) })
        : t("card.lastSeenUnknown"),
      "property-source",
    ),
  );
  card.append(createExplanation(result));

  const actions = createElement("div", null, "card-actions");
  const compareLabel = createElement("label", null, "compare-label");
  const compareInput = document.createElement("input");
  compareInput.type = "checkbox";
  compareInput.checked = handlers.isSelected(property.id);
  compareInput.disabled = !compareInput.checked && !handlers.canSelectMore();
  compareInput.addEventListener("change", () => handlers.onToggleCompare(property, compareInput.checked));
  compareLabel.append(compareInput, document.createTextNode(t("card.compare")));

  const contactButton = createElement("button", t("card.contact"), "text-button");
  contactButton.type = "button";
  contactButton.addEventListener("click", () => handlers.onContact(property));

  actions.append(compareLabel, contactButton, createSourceLabel(property));
  card.append(actions);
  return card;
}

export function renderProperties(container, results, handlers) {
  container.replaceChildren(...results.map((result) => createPropertyCard(result, handlers)));
}

export function renderComparison(container, properties) {
  container.replaceChildren();
  if (!properties.length) {
    return;
  }
  const rows = [
    ["Lieu", (p) => [p.neighborhood, p.city].filter(Boolean).join(", ")],
    ["Loyer mensuel", formatRent],
    ["Type", (p) => p.property_type],
    ["Chambres", (p) => formatBedrooms(p.bedrooms)],
    ["Salles de bain", (p) => p.bathrooms ?? t("card.unknown")],
    ["Meublé", (p) => formatBoolean(p.furnished)],
    ["Eau", (p) => formatBoolean(p.water_available)],
    ["Électricité", (p) => formatBoolean(p.electricity_available)],
    ["Disponibilité", (p) => formatListingStatus(p.listing_status)],
    ["Source", (p) => `${p.source_name}${p.source_is_demo ? " (fictive)" : ""}`],
  ];

  const table = createElement("table", null, "comparison-table");
  const head = table.createTHead().insertRow();
  head.append(createElement("th", "Critère"));
  for (const property of properties) {
    head.append(createElement("th", property.title));
  }
  const body = table.createTBody();
  for (const [label, valueFor] of rows) {
    const row = body.insertRow();
    row.append(createElement("th", label));
    for (const property of properties) {
      row.append(createElement("td", String(valueFor(property) || t("card.unknown"))));
    }
  }
  container.append(table);
}
