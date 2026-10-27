import { t } from "../i18n/index.js";

const numberFormatter = new Intl.NumberFormat("fr-FR");
const dateFormatter = new Intl.DateTimeFormat("fr-FR");

// Crée un élément avec du texte brut : jamais d'innerHTML pour les données reçues.
export function createElement(tagName, text, className) {
  const element = document.createElement(tagName);
  if (text !== undefined && text !== null) {
    element.textContent = text;
  }
  if (className) {
    element.className = className;
  }
  return element;
}

// Icônes dessinées en SVG (tracés constants du code, jamais de données reçues).
const ICON_PATHS = {
  pin: ["M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z", "M12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z"],
  bed: ["M3 18V7", "M3 12h18v6", "M21 18v-4a3 3 0 0 0-3-3h-7v1", "M7 11.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"],
  water: ["M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"],
  power: ["M13 2 4 14h7l-1 8 9-12h-7z"],
  sofa: ["M4 11V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v3", "M2 13a2 2 0 0 1 4 0v2h12v-2a2 2 0 0 1 4 0v5H2z", "M5 18v2", "M19 18v2"],
  home: ["M3 11 12 4l9 7", "M5 10v10h14V10"],
};

export function createIcon(name) {
  const namespace = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(namespace, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  for (const definition of ICON_PATHS[name] || []) {
    const path = document.createElementNS(namespace, "path");
    path.setAttribute("d", definition);
    svg.append(path);
  }
  return svg;
}

export function formatFcfa(amount) {
  return `${numberFormatter.format(amount)} FCFA`;
}

export function formatRent(property) {
  const currency = property.currency === "XAF" ? "FCFA" : property.currency;
  return `${numberFormatter.format(property.monthly_rent)} ${currency} / mois`;
}

export function formatBoolean(value, trueLabel = "Oui", falseLabel = "Non") {
  if (value === null || value === undefined) {
    return t("card.unknown");
  }
  return value ? trueLabel : falseLabel;
}

export function formatDate(isoDate) {
  return dateFormatter.format(new Date(isoDate));
}

export function formatBedrooms(bedrooms) {
  if (bedrooms === null || bedrooms === undefined) {
    return "Chambres non renseignées";
  }
  return bedrooms === 0 ? "Studio" : `${bedrooms} chambre(s)`;
}

export function formatListingStatus(status) {
  const key = `status.${status}`;
  const label = t(key);
  return label === key ? t("status.unknown") : label;
}
