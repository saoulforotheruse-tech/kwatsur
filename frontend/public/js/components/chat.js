import { t } from "../i18n/index.js";
import { createElement } from "../utils/format.js";

// Le modèle met parfois du gras Markdown (**texte**) : on le rend en <strong>, sans jamais
// interpréter de HTML (texte découpé et inséré avec textContent).
function createRichText(text) {
  const paragraph = createElement("p", null, "bubble");
  text.split(/\*\*(.+?)\*\*/g).forEach((part, index) => {
    if (part) {
      paragraph.append(index % 2 ? createElement("strong", part) : document.createTextNode(part));
    }
  });
  return paragraph;
}

function createAvatar() {
  const avatar = createElement("span", "K", "agent-avatar");
  avatar.setAttribute("aria-hidden", "true");
  return avatar;
}

// Fil de conversation : bulles, métadonnées sous les réponses et indicateur « l'agent écrit ».
export class ChatThread {
  constructor(container) {
    this.container = container;
    this.loadingRow = null;
  }

  reset() {
    this.container.replaceChildren();
    this.addAssistantMessage(t("chat.welcome"));
  }

  addUserMessage(text) {
    const row = createElement("div", null, "message-row user");
    const body = createElement("div", null, "message-body");
    body.append(createElement("p", text, "bubble"));
    row.append(body);
    this.#append(row);
  }

  // `metadata` : liste de { text, kind } (kind : ai, scout, notice ou vide).
  addAssistantMessage(text, metadata = []) {
    const row = createElement("div", null, "message-row assistant");
    const body = createElement("div", null, "message-body");
    // Les retours à la ligne sont préservés par le CSS (white-space: pre-wrap).
    body.append(createRichText(text));
    if (metadata.length) {
      const list = createElement("ul", null, "meta-list");
      for (const item of metadata) {
        list.append(createElement("li", item.text, `meta-pill ${item.kind || ""}`.trim()));
      }
      body.append(list);
    }
    row.append(createAvatar(), body);
    this.#append(row);
  }

  addErrorMessage(text) {
    const row = createElement("div", null, "message-row assistant error");
    const body = createElement("div", null, "message-body");
    body.append(createElement("p", text, "bubble"));
    row.append(createAvatar(), body);
    this.#append(row);
  }

  showLoading() {
    this.loadingRow = createElement("div", null, "message-row assistant");
    const bubble = createElement("p", null, "bubble typing");
    bubble.setAttribute("aria-label", t("chat.thinking"));
    bubble.append(createElement("span"), createElement("span"), createElement("span"));
    this.loadingRow.append(createAvatar(), bubble);
    this.#append(this.loadingRow);
  }

  hideLoading() {
    this.loadingRow?.remove();
    this.loadingRow = null;
  }

  #append(element) {
    this.container.append(element);
    this.container.scrollTop = this.container.scrollHeight;
  }
}

// Métadonnées affichées sous une réponse : qui l'a rédigée, d'où viennent les annonces
// et ce qu'a décidé le moteur Scout Intent (intention, confiance, risque, contrat, modèle).
export function describeResponse(response) {
  const author = response.reply_generated_by;
  const metadata = [{ text: t(`chat.author.${author}`), kind: author === "template" ? "" : "ai" }];
  if (response.data_source) {
    metadata.push({ text: t(`chat.source.${response.data_source}`) });
  }
  const scout = response.scout;
  if (scout) {
    // Bande « reject » : aucune intention reconnue, Scout s'est replié sur l'aide générale.
    const scoutKey = scout.band === "reject" ? "chat.scoutFallback" : "chat.scout";
    metadata.push({
      text: t(scoutKey, {
        intent: t(`scout.intent.${scout.intent}`),
        confidence: Math.round(scout.confidence * 100),
        risk: t(`scout.risk.${scout.risk_level}`),
      }),
      kind: "scout",
    });
    if (scout.contract_id) {
      metadata.push({ text: t("chat.contract", { id: scout.contract_id.slice(-6) }), kind: "scout" });
    }
    if (scout.model && author !== "template") {
      metadata.push({ text: t("chat.model", { model: scout.model }), kind: "ai" });
    }
  }
  for (const notice of response.notices) {
    metadata.push({ text: notice, kind: "notice" });
  }
  return metadata;
}
