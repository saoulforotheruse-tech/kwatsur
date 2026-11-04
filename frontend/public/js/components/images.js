import { t } from "../i18n/index.js";
import { createElement } from "../utils/format.js";

// Trois sortes d'images, toujours étiquetées : photo du propriétaire, photo d'exemple
// (licence libre, ne montre pas ce logement) et illustration IA (jamais une photo réelle).
function imageVariant(image) {
  if (image.is_ai_generated) {
    return "ai";
  }
  if (image.kind === "source_photo") {
    return "source";
  }
  return image.kind === "sample_photo" ? "sample" : "photo";
}

function createUnavailablePhoto(image) {
  const box = createElement("div", t("image.unavailable"), "image-unavailable");
  if (image.source_url?.startsWith("https://")) {
    const link = createElement("a", t("image.listing"));
    link.href = image.source_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    box.append(document.createElement("br"), link);
  }
  return box;
}

export function createImageFigure(image, { compact = false } = {}) {
  const variant = imageVariant(image);
  const figure = createElement("figure", null, `image-figure ${variant}`);
  if (compact) {
    figure.classList.add("compact");
  }
  const picture = document.createElement("img");
  picture.alt = image.label;
  picture.loading = "lazy";
  picture.decoding = "async";
  if (image.kind === "source_photo") {
    // Photo hébergée par un site tiers : chargée sans référent ; s'il la refuse, on le dit.
    picture.referrerPolicy = "no-referrer";
    picture.addEventListener("error", () => picture.replaceWith(createUnavailablePhoto(image)), { once: true });
  }
  picture.src = image.url;

  const badge = createElement("span", t(`image.badge.${variant}`), `image-badge ${variant}`);
  figure.append(picture, badge);

  if (!compact) {
    const caption = createElement("figcaption", image.label);
    if (image.caption) {
      caption.append(createElement("small", image.caption));
    }
    // Crédit des photos sous licence libre : lien vers la page d'origine (https seulement).
    if (image.source_url?.startsWith("https://")) {
      const link = createElement("a", t(image.kind === "source_photo" ? "image.listing" : "image.source"));
      link.href = image.source_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      caption.append(link);
    }
    figure.append(caption);
  }
  return figure;
}

export function createGallery(images) {
  const gallery = createElement("div", null, "image-gallery");
  gallery.append(...images.map((image) => createImageFigure(image)));
  return gallery;
}
