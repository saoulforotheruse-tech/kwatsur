import { fr } from "./fr.js";

const dictionaries = { fr };
const activeDictionary = dictionaries[document.documentElement.lang] || fr;

// Traduit une clé et remplace les {paramètres}. Une clé absente s'affiche telle quelle.
export function t(key, params = {}) {
  const template = activeDictionary[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_match, name) => String(params[name] ?? ""));
}
