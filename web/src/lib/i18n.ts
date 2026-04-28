import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import enAdmin from '@/locales/en/admin.json'
import enAuth from '@/locales/en/auth.json'
import enChat from '@/locales/en/chat.json'
import enCommon from '@/locales/en/common.json'
import enSettings from '@/locales/en/settings.json'
import jaAdmin from '@/locales/ja/admin.json'
import jaAuth from '@/locales/ja/auth.json'
import jaChat from '@/locales/ja/chat.json'
import jaCommon from '@/locales/ja/common.json'
import jaSettings from '@/locales/ja/settings.json'
import zhAdmin from '@/locales/zh/admin.json'
import zhAuth from '@/locales/zh/auth.json'
import zhChat from '@/locales/zh/chat.json'
import zhCommon from '@/locales/zh/common.json'
import zhSettings from '@/locales/zh/settings.json'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      zh: { common: zhCommon, auth: zhAuth, chat: zhChat, settings: zhSettings, admin: zhAdmin },
      en: { common: enCommon, auth: enAuth, chat: enChat, settings: enSettings, admin: enAdmin },
      ja: { common: jaCommon, auth: jaAuth, chat: jaChat, settings: jaSettings, admin: jaAdmin },
    },
    defaultNS: 'common',
    fallbackLng: 'zh',
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'lang',
    },
    interpolation: {
      escapeValue: false,
    },
  })

export default i18n
