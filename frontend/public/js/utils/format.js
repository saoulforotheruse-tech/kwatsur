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
