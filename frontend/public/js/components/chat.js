import { t } from "../i18n/index.js";
import { createElement } from "../utils/format.js";

// Fil de conversation : affichage des messages et indicateur de chargement.
export class ChatThread {
  constructor(container) {
    this.container = container;
    this.loadingMessage = null;
  }

  reset() {
    this.container.replaceChildren();
    this.addAssistantMessage(t("chat.welcome"));
  }

  addUserMessage(text) {
    this.#append(createElement("div", text, "message message-user"));
  }

  addAssistantMessage(text, metadata = []) {
    const message = createElement("div", null, "message message-assistant");
    // Les réponses peuvent contenir des retours à la ligne : on les préserve en texte brut.
    message.append(createElement("p", text, "message-text"));
    if (metadata.length) {
      message.append(createElement("p", metadata.join(" · "), "message-meta"));
    }
    this.#append(message);
  }

  addErrorMessage(text) {
    this.#append(createElement("div", text, "message message-error"));
  }

  showLoading() {
    this.loadingMessage = createElement("div", t("chat.thinking"), "message message-assistant loading");
    this.#append(this.loadingMessage);
  }

  hideLoading() {
    this.loadingMessage?.remove();
    this.loadingMessage = null;
  }

  #append(element) {
    this.container.append(element);
    this.container.scrollTop = this.container.scrollHeight;
  }
}

// Métadonnées affichées sous une réponse : qui l'a rédigée, d'où viennent les annonces
// et ce qu'a décidé le moteur Scout Intent (intention, confiance, risque, contrat, modèle).
export function describeResponse(response) {
  const metadata = [t(`chat.author.${response.reply_generated_by}`)];
  if (response.data_source) {
    metadata.push(t(`chat.source.${response.data_source}`));
  }
  const scout = response.scout;
  if (scout) {
    metadata.push(
      t("chat.scout", {
        intent: t(`scout.intent.${scout.intent}`),
        confidence: Math.round(scout.confidence * 100),
        risk: t(`scout.risk.${scout.risk_level}`),
      }),
    );
    if (scout.contract_id) {
      metadata.push(t("chat.contract", { id: scout.contract_id.slice(-6) }));
    }
    if (scout.model && response.reply_generated_by !== "template") {
      metadata.push(t("chat.model", { model: scout.model }));
    }
  }
  return [...metadata, ...response.notices];
}
