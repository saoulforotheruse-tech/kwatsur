import { t } from "../i18n/index.js";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// Appel JSON commun : transforme les erreurs HTTP en messages lisibles.
async function requestJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(t("error.network"), 0);
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : t("error.generic");
    throw new ApiError(detail, response.status);
  }
  return body;
}

export function sendChatMessage(message, conversationId) {
  return requestJson("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
}

export function fetchConversation(conversationId) {
  return requestJson(`/api/conversations/${encodeURIComponent(conversationId)}`);
}

export function searchProperties(queryParameters) {
  return requestJson(`/api/properties?${queryParameters.toString()}`);
}

export function createContactDraft(propertyId) {
  return requestJson(`/api/properties/${propertyId}/contact-draft`, { method: "POST" });
}
