/**
 * 版本更新检查：对比本地版本和 npm registry 上的最新版本
 */

const PACKAGE_NAME = "liteyuki-local-agent";

// 从 package.json 获取当前版本（构建时内联）
export const CURRENT_VERSION: string = "__VERSION__"; // tsup 会替换，fallback 在下方

/** 获取 npm 上的最新版本号 */
async function fetchLatestVersion(): Promise<string | null> {
  try {
    const res = await fetch(`https://registry.npmjs.org/${PACKAGE_NAME}/latest`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { version?: string };
    return data.version || null;
  } catch {
    return null;
  }
}

/** 简单的 semver 比较：a < b 返回 true */
function isNewer(latest: string, current: string): boolean {
  const parse = (v: string) => v.replace(/^v/, "").split(".").map(Number);
  const l = parse(latest);
  const c = parse(current);
  for (let i = 0; i < 3; i++) {
    if ((l[i] || 0) > (c[i] || 0)) return true;
    if ((l[i] || 0) < (c[i] || 0)) return false;
  }
  return false;
}

export interface UpdateInfo {
  current: string;
  latest: string;
  command: string;
}

/** 检查更新，有新版本返回 UpdateInfo，否则返回 null */
export async function checkUpdate(currentVersion: string): Promise<UpdateInfo | null> {
  const latest = await fetchLatestVersion();
  if (!latest) return null;
  if (!isNewer(latest, currentVersion)) return null;
  return {
    current: currentVersion,
    latest,
    command: `npm install -g ${PACKAGE_NAME}@${latest}`,
  };
}
