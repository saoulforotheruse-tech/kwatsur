const currencyFormatter = new Intl.NumberFormat("fr-FR");
const MAX_COMPARISON_ITEMS = 3;

function addTextElement(parent, tagName, text, className) {
  const element = document.createElement(tagName);
  element.textContent = text;
  if (className) {
    element.className = className;
  }
  parent.append(element);
  return element;
}

function formatBoolean(value, trueLabel, falseLabel) {
  if (value === null || value === undefined) {
    return "Non renseigné";
  }
  return value ? trueLabel : falseLabel;
}

function formatRent(property) {
  const currency = property.currency === "XAF" ? "FCFA" : property.currency;
  return `${currencyFormatter.format(property.monthly_rent)} ${currency} / mois`;
}

function formatListingStatus(status) {
  const labels = {
    active: "Annoncée active par la source",
    unconfirmed: "Disponibilité à confirmer",
    withdrawn: "Annonce retirée",
  };
  return labels[status] || "Statut à vérifier";
}

function createPropertyCard(result, selectedProperties, onComparisonChange) {
  const property = result.property;
  const card = document.createElement("article");
  card.className = "property-card";
  card.dataset.property = JSON.stringify(property);

  const header = document.createElement("div");
  header.className = "property-card-header";
  addTextElement(header, "h3", property.title);
  if (property.source_is_demo) {
    addTextElement(header, "span", "Démo fictive", "demo-badge");
  }
  card.append(header);

  const area = [property.neighborhood, property.city].filter(Boolean).join(", ");
  addTextElement(card, "p", area || "Localisation non renseignée", "property-location");
  addTextElement(
    card,
    "p",
    formatRent(property),
    "property-rent",
  );

  const facts = document.createElement("ul");
  facts.className = "property-facts";
  for (const fact of [
    property.property_type,
    property.bedrooms === null
      ? "Chambres non renseignées"
      : property.bedrooms === 0
        ? "Studio"
        : `${property.bedrooms} chambre(s)`,
    `Eau : ${formatBoolean(property.water_available, "oui", "non")}`,
    `Électricité : ${formatBoolean(property.electricity_available, "oui", "non")}`,
    `Meublé : ${formatBoolean(property.furnished, "oui", "non")}`,
    formatListingStatus(property.listing_status),
  ]) {
    addTextElement(facts, "li", fact);
  }
  card.append(facts);
  addTextElement(
    card,
    "p",
    property.last_seen_at
      ? `Dernière observation : ${new Intl.DateTimeFormat("fr-FR").format(new Date(property.last_seen_at))}`
      : "Date de dernière observation non renseignée.",
    "property-source",
  );
  if (property.verification_status !== "verified") {
    addTextElement(card, "p", "Les informations de cette annonce ne sont pas vérifiées.", "property-source");
  }
  if (property.contact_information) {
    addTextElement(card, "p", `Contact fourni par la source : ${property.contact_information}`);
  }

  if (property.description) {
    addTextElement(card, "p", property.description, "property-description");
  }

  const details = document.createElement("details");
  details.className = "property-detail";
  addTextElement(details, "summary", "Voir les raisons et les informations manquantes");
  const reasonsHeading = addTextElement(details, "h4", "Pourquoi ce résultat");
  const reasons = document.createElement("ul");
  for (const reason of result.reasons) {
    addTextElement(reasons, "li", reason);
  }
  details.append(reasonsHeading, reasons);

  if (result.missing_information.length) {
    const missingHeading = addTextElement(details, "h4", "Informations à vérifier");
    const missing = document.createElement("ul");
    for (const item of result.missing_information) {
      addTextElement(missing, "li", item);
    }
    details.append(missingHeading, missing);
  }
  card.append(details);

  const actions = document.createElement("div");
  actions.className = "card-actions";
  const compareLabel = document.createElement("label");
  compareLabel.className = "compare-label";
  const compareInput = document.createElement("input");
  compareInput.type = "checkbox";
  compareInput.checked = selectedProperties.has(property.id);
  compareInput.disabled = !compareInput.checked && selectedProperties.size >= MAX_COMPARISON_ITEMS;
  compareInput.addEventListener("change", () => {
    if (compareInput.checked) {
      selectedProperties.set(property.id, property);
    } else {
      selectedProperties.delete(property.id);
    }
    onComparisonChange();
  });
  compareLabel.append(compareInput, document.createTextNode("Comparer"));
  actions.append(compareLabel);

  const sourceLabel = property.source_url
    ? document.createElement("a")
    : document.createElement("span");
  sourceLabel.className = "property-source";
  sourceLabel.textContent = `Source : ${property.source_name}`;
  if (property.source_url) {
    sourceLabel.href = property.source_url;
    sourceLabel.target = "_blank";
    sourceLabel.rel = "noopener noreferrer";
  }
  actions.append(sourceLabel);
  card.append(actions);
  return card;
}

export function renderProperties(container, results, selectedProperties, onComparisonChange) {
  container.replaceChildren();
  for (const result of results) {
    container.append(createPropertyCard(result, selectedProperties, onComparisonChange));
  }
}

export function renderComparison(container, properties) {
  container.replaceChildren();
  if (!properties.length) {
    return;
  }

  const table = document.createElement("table");
  table.className = "comparison-table";
  const rows = [
    ["Logement", (property) => property.title],
    ["Lieu", (property) => [property.neighborhood, property.city].filter(Boolean).join(", ")],
    ["Loyer mensuel", formatRent],
    ["Chambres", (property) => property.bedrooms ?? "Non renseigné"],
    ["Eau", (property) => formatBoolean(property.water_available, "Oui", "Non")],
    ["Électricité", (property) => formatBoolean(property.electricity_available, "Oui", "Non")],
    ["Disponibilité", (property) => formatListingStatus(property.listing_status)],
    ["Source", (property) => `${property.source_name}${property.source_is_demo ? " (fictive)" : ""}`],
  ];

  const head = table.createTHead().insertRow();
  addTextElement(head, "th", "Critère");
  for (const property of properties) {
    addTextElement(head, "th", property.title);
  }

  const body = table.createTBody();
  for (const [label, valueForProperty] of rows) {
    const row = body.insertRow();
    addTextElement(row, "th", label);
    for (const property of properties) {
      addTextElement(row, "td", String(valueForProperty(property) || "Non renseigné"));
    }
  }
  container.append(table);
}
