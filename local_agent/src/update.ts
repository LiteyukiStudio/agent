/**
 * 版本更新检查：对比本地版本和 npm registry 上的最新版本，
 * 并从 GitHub Releases 获取 changelog。
 */

const PACKAGE_NAME = "liteyuki-local-agent";
const GITHUB_REPO = "LiteyukiStudio/agent";
const RELEASE_TAG_PREFIX = "l"; // tag 格式: l0.1.0

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

/** 从 GitHub Releases 获取指定版本及之后的 changelog */
async function fetchChangelog(currentVersion: string, latestVersion: string): Promise<string[]> {
  try {
    // 获取最近 10 个 release，筛选出比当前版本新的
    const res = await fetch(
      `https://api.github.com/repos/${GITHUB_REPO}/releases?per_page=10`,
      {
        headers: { Accept: "application/vnd.github+json" },
        signal: AbortSignal.timeout(8000),
      },
    );
    if (!res.ok) return [];
    const releases = (await res.json()) as Array<{
      tag_name: string;
      name: string;
      body: string;
    }>;

    const lines: string[] = [];
    for (const rel of releases) {
      // 解析 tag: l0.1.0 → 0.1.0
      const tagVersion = rel.tag_name.startsWith(RELEASE_TAG_PREFIX)
        ? rel.tag_name.slice(RELEASE_TAG_PREFIX.length)
        : rel.tag_name.replace(/^v/, "");

      // 只展示比当前版本新的 release
      if (!isNewer(tagVersion, currentVersion)) break;

      // 从 release body 中提取「更新日志」部分
      const changelog = extractChangelog(rel.body);
      if (changelog) {
        lines.push(`**${tagVersion}**`);
        lines.push(...changelog.split("\n").filter(Boolean));
        lines.push("");
      }
    }
    return lines;
  } catch {
    return [];
  }
}

/** 从 release body 中提取更新日志段落 */
function extractChangelog(body: string): string {
  if (!body) return "";
  // 尝试提取 "### 更新日志" 后面的内容
  const match = body.match(/###\s*更新日志\s*\n([\s\S]*?)(?=\n###|\n##|$)/i)
    || body.match(/###\s*Changelog\s*\n([\s\S]*?)(?=\n###|\n##|$)/i);
  if (match) return match[1].trim();
  // fallback: 如果 body 里只有 commit list，直接返回
  const commitLines = body.split("\n").filter((l) => l.startsWith("- "));
  if (commitLines.length > 0) return commitLines.join("\n");
  return "";
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
  /** Markdown 格式的 changelog 行列表 */
  changelog: string[];
}

/** 检查更新，有新版本返回 UpdateInfo（含 changelog），否则返回 null */
export async function checkUpdate(currentVersion: string): Promise<UpdateInfo | null> {
  const latest = await fetchLatestVersion();
  if (!latest) return null;
  if (!isNewer(latest, currentVersion)) return null;

  // 异步获取 changelog（不阻塞主流程）
  const changelog = await fetchChangelog(currentVersion, latest);

  return {
    current: currentVersion,
    latest,
    command: `npm install -g ${PACKAGE_NAME}@${latest}`,
    changelog,
  };
}
