import { t } from "../i18n/index.js";
import {
  createElement,
  createIcon,
  formatBedrooms,
  formatBoolean,
  formatDate,
  formatListingStatus,
  formatRent,
} from "../utils/format.js";
import { createImageFigure } from "./images.js";

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

// Une caractéristique : oui (vert), non (barrée) ou inconnue (pointillés, jamais devinée).
function createFact(iconName, label, value) {
  const state = value === null || value === undefined ? "unknown" : value ? "yes" : "no";
  const fact = createElement("li", null, `fact ${state}`);
  const suffix = state === "unknown" ? ` ${t("card.unknownShort")}` : "";
  fact.append(createIcon(iconName), document.createTextNode(`${label}${suffix}`));
  fact.title = `${label} : ${formatBoolean(value)}`;
  return fact;
}

function createFacts(property) {
  const facts = createElement("ul", null, "fact-list");
  const bedrooms = createElement("li", null, property.bedrooms == null ? "fact unknown" : "fact");
  bedrooms.append(createIcon("bed"), document.createTextNode(formatBedrooms(property.bedrooms)));
  const type = createElement("li", null, "fact");
  type.append(createIcon("home"), document.createTextNode(property.property_type || t("card.unknown")));
  facts.append(
    type,
    bedrooms,
    createFact("water", t("card.water"), property.water_available),
    createFact("power", t("card.electricity"), property.electricity_available),
    createFact("sofa", t("card.furnished"), property.furnished),
  );
  return facts;
}

// Barre relative au meilleur résultat de la liste : ordonne, ce n'est ni une note ni une probabilité.
function createMatchBar(result, bestPoints) {
  const match = createElement("div", null, "match");
  const label = createElement("div", null, "match-label");
  label.append(createElement("span", t("card.matchLabel")), createElement("span", t("card.points", { points: result.match_points })));
  const track = createElement("div", null, "match-track");
  const fill = createElement("div", null, "match-fill");
  const ratio = bestPoints > 0 ? Math.max(0.06, result.match_points / bestPoints) : 0;
  requestAnimationFrame(() => fill.style.setProperty("width", `${Math.round(ratio * 100)}%`));
  track.append(fill);
  match.append(label, track);
  return match;
}

function createExplanation(result) {
  const details = createElement("details", null, "property-detail");
  details.append(createElement("summary", t("card.details")));
  appendList(details, t("card.reasons"), result.reasons, "reason-list");
  appendList(details, t("card.tradeoffs"), result.tradeoffs, "tradeoff-list");
  appendList(details, t("card.toVerify"), result.to_verify, "verify-list");
  appendList(details, t("card.missing"), result.missing_information, "missing-list");
  return details;
}

function createSourceLabel(property) {
  const label = property.source_url ? createElement("a") : createElement("span");
  label.className = "property-source";
  const seen = property.last_seen_at
    ? t("card.lastSeen", { date: formatDate(property.last_seen_at) })
    : t("card.lastSeenUnknown");
  label.textContent = `${t("card.source", { name: property.source_name })} · ${seen}`;
  if (property.source_url) {
    label.href = property.source_url;
    label.target = "_blank";
    label.rel = "noopener noreferrer";
  }
  return label;
}

function createPropertyCard(result, handlers, bestPoints, index) {
  const { property } = result;
  const selected = handlers.isSelected(property.id);
  const card = createElement("article", null, selected ? "property-card selected" : "property-card");
  card.style.setProperty("animation-delay", `${Math.min(index, 8) * 0.05}s`);

  const top = createElement("div", null, "card-top");
  top.append(createElement("span", `N°${result.rank}`, "rank-badge"));
  const badges = createElement("div", null, "badges");
  if (property.source_is_demo) {
    badges.append(createElement("span", t("card.demo"), "badge demo"));
  }
  badges.append(createElement("span", formatListingStatus(property.listing_status), "badge status"));
  top.append(badges);
  card.append(top);

  if (result.images?.length) {
    // Première image du logement : photo du propriétaire si elle existe, sinon illustration IA.
    card.append(createImageFigure(result.images[0], { compact: true }));
  }
  card.append(createElement("h3", property.title));
  const location = createElement("p", null, "property-location");
  const area = [property.neighborhood, property.city].filter(Boolean).join(", ");
  location.append(createIcon("pin"), document.createTextNode(area || t("card.locationUnknown")));
  card.append(location);

  const rent = createElement("p", null, "property-rent");
  rent.append(document.createTextNode(formatRent(property).replace(" / mois", " ")), createElement("small", "/ mois"));
  card.append(rent);

  card.append(createFacts(property), createMatchBar(result, bestPoints));

  if (result.reasons.length) {
    card.append(createElement("p", result.reasons.slice(0, 2).join(" "), "property-summary"));
  }
  if (result.risk_signals.length) {
    const risks = createElement("div", null, "risk-box");
    appendList(risks, `⚠ ${t("card.risks")}`, result.risk_signals, "risk-list");
    card.append(risks);
  }
  card.append(createExplanation(result));

  const footer = createElement("div", null, "card-footer");
  const actions = createElement("div", null, "card-actions");
  const compareButton = createElement("button", selected ? t("card.compared") : t("card.compare"), "ghost-button toggle-button");
  compareButton.type = "button";
  compareButton.setAttribute("aria-pressed", String(selected));
  compareButton.disabled = !selected && !handlers.canSelectMore();
  compareButton.addEventListener("click", () => handlers.onToggleCompare(property, !selected));

  const contactButton = createElement("button", t("card.contact"), "ghost-button");
  contactButton.type = "button";
  contactButton.addEventListener("click", () => handlers.onContact(property));

  actions.append(compareButton, contactButton);
  footer.append(actions, createSourceLabel(property));
  card.append(footer);
  return card;
}

export function renderProperties(container, results, handlers) {
  const bestPoints = Math.max(0, ...results.map((result) => result.match_points));
  container.replaceChildren(
    ...results.map((result, index) => createPropertyCard(result, handlers, bestPoints, index)),
  );
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
    ["Chambres", (p) => (p.bedrooms == null ? null : formatBedrooms(p.bedrooms))],
    ["Salles de bain", (p) => p.bathrooms],
    ["Meublé", (p) => (p.furnished == null ? null : formatBoolean(p.furnished))],
    ["Eau", (p) => (p.water_available == null ? null : formatBoolean(p.water_available))],
    ["Électricité", (p) => (p.electricity_available == null ? null : formatBoolean(p.electricity_available))],
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
      const value = valueFor(property);
      const known = value !== null && value !== undefined && value !== "";
      row.append(createElement("td", known ? String(value) : t("card.unknown"), known ? null : "unknown"));
    }
  }
  container.append(table);
}
