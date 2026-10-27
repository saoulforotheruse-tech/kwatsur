import { t } from "../i18n/index.js";
import { createElement } from "../utils/format.js";

// Une image est toujours affichée avec son étiquette : une illustration IA n'est jamais
// présentée comme une photo réelle du logement.
export function createImageFigure(image, { compact = false } = {}) {
  const figure = createElement("figure", null, image.is_ai_generated ? "image-figure ai" : "image-figure photo");
  if (compact) {
    figure.classList.add("compact");
  }
  const picture = document.createElement("img");
  picture.src = image.url;
  picture.alt = image.label;
  picture.loading = "lazy";
  picture.decoding = "async";

  const badge = createElement(
    "span",
    image.is_ai_generated ? t("image.badgeAi") : t("image.badgePhoto"),
    image.is_ai_generated ? "image-badge ai" : "image-badge photo",
  );
  figure.append(picture, badge);

  if (!compact) {
    const caption = createElement("figcaption", image.label);
    if (image.caption) {
      caption.append(createElement("small", image.caption));
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
