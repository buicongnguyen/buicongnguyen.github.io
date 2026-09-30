import {VI} from './vi.mjs';

export const LANGUAGE_KEY = 'petal-cafe-language';
let language = navigator.language.toLowerCase().startsWith('vi') ? 'vi' : 'en';
try { language = localStorage.getItem(LANGUAGE_KEY) || language; } catch { /* browser-language default */ }
if (!['en', 'vi'].includes(language)) language = 'en';
export const getLanguage = () => language;
export function setLanguage(value) {
  language = value === 'vi' ? 'vi' : 'en';
  try { localStorage.setItem(LANGUAGE_KEY, language); } catch { /* session preference still works */ }
}

// English is the source language. Tagged messages preserve whole-sentence grammar.
export function t(source, ...values) {
  const key = Array.isArray(source) ? source.reduce((s, part, i) => s + (i ? `{${i - 1}}` : '') + part, '') : source;
  const template = language === 'vi' ? VI[key] ?? key : key;
  return String(template).replace(/\{(\d+)\}/g, (_, i) => String(values[i] ?? ''));
}
export function localizePage() {
  document.documentElement.lang = language;
  document.title = 'Petal Café · ' + t('Lantern Street');
  for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = t(el.dataset.i18n);
  for (const [data, attr] of [['i18nAria', 'aria-label'], ['i18nAlt', 'alt']]) {
    for (const el of document.querySelectorAll(`[data-${data === 'i18nAria' ? 'i18n-aria' : 'i18n-alt'}]`)) el.setAttribute(attr, t(el.dataset[data]));
  }
  for (const select of document.querySelectorAll('[data-language]')) {
    select.value = language;
    select.setAttribute('aria-label', t('Language'));
  }
}
