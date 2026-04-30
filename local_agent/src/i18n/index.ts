/**
 * 轻量 i18n 模块：根据系统 locale 加载翻译。
 *
 * Locale 检测优先级：
 *   1. 环境变量 LITEYUKI_LANG（用户强制覆盖）
 *   2. 环境变量 LANG / LC_ALL / LC_MESSAGES
 *   3. Fallback: zh-CN（默认中文）
 */
import type enMessages from "./en.js";
import en from "./en.js";
import zhCN from "./zh-CN.js";

type Messages = typeof enMessages;

const locales: Record<string, Messages> = {
  en,
  "zh-CN": zhCN as unknown as Messages,
  zh: zhCN as unknown as Messages,
};

/** 检测当前系统语言 */
function detectLocale(): string {
  // 用户强制覆盖
  const override = process.env.LITEYUKI_LANG;
  if (override && override in locales) return override;

  // 从系统环境变量检测
  const envLang = process.env.LC_ALL || process.env.LC_MESSAGES || process.env.LANG || "";
  // 解析如 "zh_CN.UTF-8" → "zh-CN"
  const match = envLang.match(/^([a-z]{2})(?:[_-]([A-Z]{2}))?/i);
  if (match) {
    const lang = match[1].toLowerCase();
    const region = match[2]?.toUpperCase();
    // 精确匹配 zh-CN
    if (region) {
      const full = `${lang}-${region}`;
      if (full in locales) return full;
    }
    // 语言码 fallback
    if (lang in locales) return lang;
  }

  return "zh";
}

const currentLocale = detectLocale();
const messages: Messages = locales[currentLocale] || en;

/** 获取当前 locale */
export function getLocale(): string {
  return currentLocale;
}

/** 获取翻译消息对象（用于直接访问嵌套属性） */
export function getMessages(): Messages {
  return messages;
}

/**
 * 模板字符串替换：将 {key} 替换为 params 中的值。
 * @example fmt("Hello {name}", { name: "world" }) → "Hello world"
 */
export function fmt(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => String(params[key] ?? `{${key}}`));
}

// 直接导出消息对象，方便 import { t } from './i18n/index.js'
export const t = messages;
