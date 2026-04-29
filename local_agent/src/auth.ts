/**
 * 认证模块：快速浏览器认证（默认）+ Device Code（无浏览器环境回退）
 *
 * 快速模式：CLI 启动临时 HTTP server → 打开浏览器 → 用户登录点确认 →
 *          浏览器 redirect 到 localhost 回调 → CLI 拿到 token
 *
 * Device Code：CLI 获取验证码 → 用户手动打开 URL 输入验证码 → CLI 轮询
 */
import { createServer } from "node:http";
import { exec, execSync } from "node:child_process";
import { hostname as osHostname, release } from "node:os";
import { platform } from "node:os";
import { URL } from "node:url";
import { existsSync, readFileSync } from "node:fs";

const DEFAULT_SERVER = "https://flow.liteyuki.org";
const POLL_INTERVAL = 2000;
const MAX_POLL_TIME = 600000;

/** 规范化 base URL：去掉尾部斜杠 */
export function normalizeUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

/** 从 base URL 构造 API URL */
export function apiUrl(baseUrl: string, path: string): string {
  return `${normalizeUrl(baseUrl)}${path}`;
}

/** 从 base URL 构造 WebSocket URL，附带 query 参数 */
export function wsUrl(baseUrl: string, path: string): string {
  const base = normalizeUrl(baseUrl);
  return base.replace(/^http/, "ws") + path;
}

/** 获取友好的设备名称（macOS ComputerName / Linux hostname） */
export function getDeviceName(): string {
  // macOS: 优先用 ComputerName（用户友好名称，如"远野千束的MacBook Pro"）
  if (platform() === "darwin") {
    try {
      const name = execSync("scutil --get ComputerName", { encoding: "utf-8" }).trim();
      if (name) return name;
    } catch {
      // fallback
    }
  }

  // Linux: 优先用 /etc/hostname 或 hostnamectl 的 pretty hostname
  if (platform() === "linux") {
    try {
      const pretty = execSync("hostnamectl --static 2>/dev/null || hostname", { encoding: "utf-8" }).trim();
      if (pretty) return pretty;
    } catch {
      // fallback
    }
  }

  return osHostname().replace(/\.local$/, "");
}

/**
 * 获取操作系统标识，用于前端显示对应图标。
 * 返回值：macos, windows, ubuntu, debian, fedora, arch, centos, linux, unknown
 */
export function getOsType(): string {
  const p = platform();
  if (p === "darwin") return "macos";
  if (p === "win32") return "windows";
  if (p === "linux") {
    // 尝试读取 /etc/os-release 判断发行版
    try {
      if (existsSync("/etc/os-release")) {
        const content = readFileSync("/etc/os-release", "utf-8").toLowerCase();
        if (content.includes("ubuntu")) return "ubuntu";
        if (content.includes("debian")) return "debian";
        if (content.includes("fedora")) return "fedora";
        if (content.includes("arch")) return "arch";
        if (content.includes("centos")) return "centos";
        if (content.includes("alpine")) return "alpine";
        if (content.includes("opensuse") || content.includes("suse")) return "suse";
        if (content.includes("manjaro")) return "manjaro";
        if (content.includes("mint")) return "mint";
        if (content.includes("redhat") || content.includes("rhel")) return "redhat";
      }
    } catch {
      // fallback
    }
    return "linux";
  }
  return "unknown";
}

function openBrowser(url: string): void {
  const cmd =
    platform() === "darwin"
      ? `open "${url}"`
      : platform() === "win32"
        ? `start "${url}"`
        : `xdg-open "${url}"`;
  exec(cmd, () => {});
}

export interface LoginResult {
  token: string;
  baseUrl: string;
}

// ---------------------------------------------------------------------------
// 快速浏览器认证（默认）
// ---------------------------------------------------------------------------

export async function browserLogin(
  baseUrl: string = DEFAULT_SERVER,
  onStatus: (msg: string) => void,
): Promise<LoginResult | null> {
  const base = normalizeUrl(baseUrl);
  const name = getDeviceName();

  return new Promise((resolve) => {
    const server = createServer((req, res) => {
      if (!req.url) {
        res.writeHead(400);
        res.end("Bad request");
        return;
      }

      const url = new URL(req.url, "http://localhost");

      if (url.pathname === "/callback") {
        const token = url.searchParams.get("token");
        const error = url.searchParams.get("error");

        if (token) {
          res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
          res.end(`
            <html><body style="font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;margin:0">
              <div style="text-align:center">
                <h1 style="color:#22c55e">\u2713 授权成功</h1>
                <p>你可以关闭此页面，回到终端继续操作。</p>
              </div>
            </body></html>
          `);
          server.close();
          resolve({ token, baseUrl: base });
        } else {
          res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
          res.end(`
            <html><body style="font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;margin:0">
              <div style="text-align:center">
                <h1 style="color:#ef4444">\u2717 授权失败</h1>
                <p>${error || "Unknown error"}</p>
              </div>
            </body></html>
          `);
          server.close();
          resolve(null);
        }
      }
    });

    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      if (!addr || typeof addr === "string") {
        resolve(null);
        return;
      }
      const port = addr.port;
      const callbackUrl = `http://127.0.0.1:${port}/callback`;
      const authUrl = `${base}/auth/cli?callback=${encodeURIComponent(callbackUrl)}&hostname=${encodeURIComponent(name)}`;

      onStatus(`Opening browser...`);
      openBrowser(authUrl);
      onStatus(`Waiting for authorization... (localhost:${port})`);
    });

    setTimeout(() => {
      server.close();
      resolve(null);
      onStatus("Browser auth timed out.");
    }, 300000);
  });
}

// ---------------------------------------------------------------------------
// Device Code 认证（无浏览器环境回退）
// ---------------------------------------------------------------------------

interface DeviceCodeResponse {
  device_code: string;
  user_code: string;
  verification_url: string;
  expires_in: number;
}

interface DeviceTokenResponse {
  status: "pending" | "approved" | "expired";
  token?: string;
}

export async function deviceLogin(
  baseUrl: string = DEFAULT_SERVER,
  onStatus: (msg: string) => void,
): Promise<LoginResult | null> {
  const base = normalizeUrl(baseUrl);

  onStatus("Requesting device code...");
  const codeRes = await fetch(apiUrl(base, "/api/v1/auth/device/code"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ server_url: base }),
  });

  if (!codeRes.ok) {
    onStatus(`Failed to request device code: ${codeRes.status}`);
    return null;
  }

  const codeData = (await codeRes.json()) as DeviceCodeResponse;
  onStatus(`Verification code: ${codeData.user_code}`);
  onStatus(`Open: ${codeData.verification_url}`);
  openBrowser(codeData.verification_url);

  const startTime = Date.now();
  while (Date.now() - startTime < MAX_POLL_TIME) {
    await new Promise((r) => setTimeout(r, POLL_INTERVAL));
    try {
      const tokenRes = await fetch(apiUrl(base, "/api/v1/auth/device/token"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_code: codeData.device_code }),
      });
      if (!tokenRes.ok) continue;
      const tokenData = (await tokenRes.json()) as DeviceTokenResponse;
      if (tokenData.status === "approved" && tokenData.token) {
        return { token: tokenData.token, baseUrl: base };
      }
      if (tokenData.status === "expired") {
        onStatus("Authorization expired.");
        return null;
      }
    } catch {
      // Network error, continue
    }
  }
  onStatus("Authorization timed out.");
  return null;
}
