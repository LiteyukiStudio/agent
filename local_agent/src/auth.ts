/**
 * 认证模块：快速浏览器认证（默认）+ Device Code（无浏览器环境回退）
 *
 * 快速模式：CLI 启动临时 HTTP server → 打开浏览器 → 用户登录点确认 →
 *          浏览器 redirect 到 localhost 回调 → CLI 拿到 token
 *
 * Device Code：CLI 获取验证码 → 用户手动打开 URL 输入验证码 → CLI 轮询
 */
import { createServer } from "node:http";
import { exec } from "node:child_process";
import { hostname as osHostname } from "node:os";
import { platform } from "node:os";
import { URL } from "node:url";

const DEFAULT_SERVER = "https://flow.liteyuki.org";
const POLL_INTERVAL = 2000;
const MAX_POLL_TIME = 600000;

export function getHostname(): string {
  return osHostname().replace(/\.local$/, "");
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
  serverUrl: string;
}

// ---------------------------------------------------------------------------
// 快速浏览器认证（默认）
// ---------------------------------------------------------------------------

/**
 * 启动临时 HTTP server，打开浏览器到云端认证页，接收回调传回的 token。
 */
export async function browserLogin(
  serverUrl: string = DEFAULT_SERVER,
  onStatus: (msg: string) => void,
): Promise<LoginResult | null> {
  const host = getHostname();

  return new Promise((resolve) => {
    // 启动临时 HTTP server 监听回调
    const server = createServer((req, res) => {
      if (!req.url) {
        res.writeHead(400);
        res.end("Bad request");
        return;
      }

      const url = new URL(req.url, `http://localhost`);

      if (url.pathname === "/callback") {
        const token = url.searchParams.get("token");
        const error = url.searchParams.get("error");

        if (token) {
          // 返回成功页面
          res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
          res.end(`
            <html><body style="font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;margin:0">
              <div style="text-align:center">
                <h1 style="color:#22c55e">✓ 授权成功</h1>
                <p>你可以关闭此页面，回到终端继续操作。</p>
              </div>
            </body></html>
          `);
          server.close();
          resolve({ token, serverUrl });
        } else {
          res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
          res.end(`
            <html><body style="font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;margin:0">
              <div style="text-align:center">
                <h1 style="color:#ef4444">✗ 授权失败</h1>
                <p>${error || "Unknown error"}</p>
              </div>
            </body></html>
          `);
          server.close();
          resolve(null);
        }
      }
    });

    // 监听随机端口
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      if (!addr || typeof addr === "string") {
        resolve(null);
        return;
      }
      const port = addr.port;
      const callbackUrl = `http://127.0.0.1:${port}/callback`;
      const authUrl = `${serverUrl}/auth/cli?callback=${encodeURIComponent(callbackUrl)}&hostname=${encodeURIComponent(host)}`;

      onStatus(`Opening browser: ${authUrl}`);
      openBrowser(authUrl);
      onStatus(`Waiting for browser authorization... (localhost:${port})`);
    });

    // 超时 5 分钟
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
  serverUrl: string = DEFAULT_SERVER,
  onStatus: (msg: string) => void,
): Promise<LoginResult | null> {
  const apiBase = serverUrl.replace(/\/+$/, "");

  onStatus("Requesting device code...");
  const codeRes = await fetch(`${apiBase}/api/v1/auth/device/code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ server_url: serverUrl }),
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
      const tokenRes = await fetch(`${apiBase}/api/v1/auth/device/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_code: codeData.device_code }),
      });
      if (!tokenRes.ok) continue;
      const tokenData = (await tokenRes.json()) as DeviceTokenResponse;
      if (tokenData.status === "approved" && tokenData.token) {
        return { token: tokenData.token, serverUrl };
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
