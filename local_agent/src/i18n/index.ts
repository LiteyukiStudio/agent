/**
 * 轻量 i18n 模块：根据系统 locale 加载翻译。
 *
 * Locale 检测优先级：
 *   1. 环境变量 LITEYUKI_LANG（用户强制覆盖）
 *   2. 环境变量 LANG / LC_ALL / LC_MESSAGES
 *   3. Fallback: zh-CN（默认中文）
 */
import { execFileSync } from "node:child_process";
import { platform } from "node:os";
import type enMessages from "./en.js";
import en from "./en.js";
import zhCN from "./zh-CN.js";

type Messages = typeof enMessages;

const locales: Record<string, Messages> = {
  en,
  "zh-CN": zhCN as unknown as Messages,
  zh: zhCN as unknown as Messages,
};

function normalizeLocale(raw: string | undefined): string | null {
  if (!raw)
    return null;
  const value = raw.trim();
  if (!value || value === "C" || value === "POSIX")
    return null;

  // LANGUAGE 可能是 "zh_CN:zh:en_US"，逐个候选尝试。
  for (const candidate of value.split(":")) {
    const locale = candidate.split(".")[0]?.replace("_", "-");
    const match = locale?.match(/^([a-z]{2,3})(?:-([a-zA-Z]{2}|Hans|Hant))?/i);
    if (!match)
      continue;

    const lang = match[1].toLowerCase();
    const region = match[2];
    if (lang === "zh")
      return "zh";
    if (region) {
      const full = `${lang}-${region.toUpperCase()}`;
      if (full in locales)
        return full;
    }
    if (lang in locales)
      return lang;
  }
  return null;
}

function detectMacOSLocale(): string | null {
  if (platform() !== "darwin")
    return null;
  try {
    const output = execFileSync("defaults", ["read", "-g", "AppleLanguages"], {
      encoding: "utf-8",
      timeout: 1000,
      stdio: ["ignore", "pipe", "ignore"],
    });
    return normalizeLocale(output);
  }
  catch {
    return null;
  }
}

/** 检测当前系统语言 */
function detectLocale(): string {
  // 用户强制覆盖
  const override = normalizeLocale(process.env.LITEYUKI_LANG);
  if (override)
    return override;

  // Ubuntu/GNOME 常用 LANGUAGE 表示界面语言，例如 zh_CN:zh。
  const language = normalizeLocale(process.env.LANGUAGE);
  if (language)
    return language;

  // macOS 的 LANG 经常是 en_US.UTF-8，即使系统界面是中文；优先读取 AppleLanguages。
  const macLocale = detectMacOSLocale();
  if (macLocale)
    return macLocale;

  // 从 POSIX locale 环境变量检测。
  for (const envLang of [process.env.LC_ALL, process.env.LC_MESSAGES, process.env.LANG]) {
    const locale = normalizeLocale(envLang);
    if (locale)
      return locale;
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
