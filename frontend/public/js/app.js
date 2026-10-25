import {
  renderComparison,
  renderProperties,
} from "./components/property_cards.js";

const searchForm = document.querySelector("#search-form");
const resultsContainer = document.querySelector("#property-results");
const statusMessage = document.querySelector("#status-message");
const resultCount = document.querySelector("#result-count");
const comparisonSection = document.querySelector("#comparison");
const comparisonTable = document.querySelector("#comparison-table");
const clearComparisonButton = document.querySelector("#clear-comparison");
const selectedProperties = new Map();
let currentResults = [];

function readSearchCriteria(form) {
  const formData = new FormData(form);
  const query = new URLSearchParams();

  for (const field of ["city", "neighborhood", "min_rent", "max_rent", "bedrooms"]) {
    const value = formData.get(field)?.toString().trim();
    if (value) {
      query.set(field, value);
    }
  }

  for (const field of ["water_available", "electricity_available", "furnished"]) {
    if (formData.has(field)) {
      query.set(field, "true");
    }
  }

  return query;
}

function updateComparison() {
  comparisonSection.hidden = selectedProperties.size === 0;
  renderComparison(comparisonTable, [...selectedProperties.values()]);
}

function refreshComparison() {
  updateComparison();
  renderProperties(
    resultsContainer,
    currentResults,
    selectedProperties,
    refreshComparison,
  );
}

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = searchForm.querySelector('button[type="submit"]');
  const query = readSearchCriteria(searchForm);

  submitButton.disabled = true;
  statusMessage.textContent = "Recherche des logements…";
  statusMessage.classList.remove("error");
  resultCount.textContent = "";
  resultsContainer.replaceChildren();

  try {
    const response = await fetch(`/api/properties?${query.toString()}`);
    if (!response.ok) {
      throw new Error("La recherche n’a pas pu aboutir. Réessayez dans un instant.");
    }

    const data = await response.json();
    currentResults = data.results;
    renderProperties(resultsContainer, currentResults, selectedProperties, refreshComparison);
    resultCount.textContent = `${data.total} résultat${data.total === 1 ? "" : "s"}`;
    statusMessage.textContent = data.total
      ? "Les résultats sont classés par quartier demandé, informations connues, puis loyer."
      : "Aucun logement ne correspond à ces filtres. Essayez d’assouplir un critère.";
  } catch (error) {
    statusMessage.textContent = error instanceof Error
      ? error.message
      : "Une erreur inattendue est survenue.";
    statusMessage.classList.add("error");
  } finally {
    submitButton.disabled = false;
  }
});

clearComparisonButton.addEventListener("click", () => {
  selectedProperties.clear();
  refreshComparison();
});
