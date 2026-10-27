import { t } from "../i18n/index.js";
import { createElement } from "../utils/format.js";

// Trois sortes d'images, toujours étiquetées : photo du propriétaire, photo d'exemple
// (licence libre, ne montre pas ce logement) et illustration IA (jamais une photo réelle).
function imageVariant(image) {
  if (image.is_ai_generated) {
    return "ai";
  }
  return image.kind === "sample_photo" ? "sample" : "photo";
}

export function createImageFigure(image, { compact = false } = {}) {
  const variant = imageVariant(image);
  const figure = createElement("figure", null, `image-figure ${variant}`);
  if (compact) {
    figure.classList.add("compact");
  }
  const picture = document.createElement("img");
  picture.src = image.url;
  picture.alt = image.label;
  picture.loading = "lazy";
  picture.decoding = "async";

  const badge = createElement("span", t(`image.badge.${variant}`), `image-badge ${variant}`);
  figure.append(picture, badge);

  if (!compact) {
    const caption = createElement("figcaption", image.label);
    if (image.caption) {
      caption.append(createElement("small", image.caption));
    }
    // Crédit des photos sous licence libre : lien vers la page d'origine (https seulement).
    if (image.source_url?.startsWith("https://")) {
      const link = createElement("a", t("image.source"));
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
