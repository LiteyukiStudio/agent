/**
 * 本地工具执行器：在用户电脑上执行云端下发的操作
 */
import { spawn } from "node:child_process";
import { constants, privateDecrypt } from "node:crypto";
import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { resolve, join } from "node:path";
import { homedir } from "node:os";

export interface ToolRequest {
  id: string;
  tool: string;
  args: Record<string, unknown>;
}

export interface ToolResponse {
  id: string;
  result?: string;
  error?: string;
}

interface CommandResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
  timedOut: boolean;
  durationMs: number;
  truncated: boolean;
}

/** 需要用户确认的高危操作 */
const DANGEROUS_PATTERNS = [
  // ---- 直接危险命令 ----
  /\brm\s+(-[a-z]*)?.*\//i,             // rm 任何带路径的操作
  /\brm\s+-rf?\b/i,                      // rm -r / rm -rf
  /\bsudo\b/i,                           // 提权
  /\bmkfs\b/i,                           // 格式化文件系统
  /\bdd\s+if=/i,                         // 磁盘操作
  /\bformat\b/i,                         // Windows 格式化
  />\s*\/dev\//,                          // 写入设备文件
  /\bshutdown\b/i,                       // 关机
  /\breboot\b/i,                         // 重启
  /\bsystemctl\s+(stop|disable|mask)\b/i, // 停服务
  /\bkill\s+-9\b/i,                      // 强制杀进程
  /\bkillall\b/i,                        // 杀所有进程
  /\bchmod\s+[0-7]*7[0-7]*\b/,          // 危险权限（含 7）
  /\bchown\b/i,                          // 改文件属主
  /\bcrontab\s+-r\b/i,                   // 删除 crontab
  /\bcurl\b.*\|\s*(ba)?sh\b/i,          // curl pipe to sh
  /\bwget\b.*\|\s*(ba)?sh\b/i,          // wget pipe to sh
  /\beval\b/i,                           // shell eval
  // ---- 防 AI 绕过：通过脚本语言调用系统命令 ----
  /\bpython[23]?\b.*\b(os\.system|os\.popen|subprocess|shutil\.rmtree|shutil\.move)\b/i,
  /\bpython[23]?\b.*-c\b/i,             // python -c（任意代码执行）
  /\bnode\b.*-e\b/i,                     // node -e（任意代码执行）
  /\bruby\b.*-e\b/i,                     // ruby -e
  /\bperl\b.*-e\b/i,                     // perl -e
  /\bos\.system\s*\(/i,                  // os.system() 即使不带 python 前缀
  /\bsubprocess\.(run|call|Popen)\s*\(/i, // subprocess 调用
  /\bshutil\.(rmtree|move)\s*\(/i,      // shutil 危险操作
  /\bexec\s*\(/i,                        // exec()
  // ---- 包管理器的全局/危险操作 ----
  /\bnpm\s+(exec|x)\b/i,                // npx 执行任意包
  /\bpip\s+install\b.*--break-system/i,  // 破坏系统包
  // ---- 网络下载执行 ----
  /\bcurl\b.*-[a-z]*o\b/i,              // curl 下载到文件
  /\bwget\b/i,                           // wget 下载
  // ---- 危险重定向 ----
  />\s*\/etc\//,                          // 写 /etc 配置
  />\s*~\//,                              // 覆盖 home 目录文件
  // ---- 敏感凭据路径 ----
  /(?:^|\s)(?:~\/|\/[^\s]+\/)?\.ssh(?:\/|\s|$)/i,
  /(?:^|\s)(?:~\/|\/[^\s]+\/)?\.gnupg(?:\/|\s|$)/i,
  /(?:^|\s)(?:~\/|\/[^\s]+\/)?\.aws(?:\/|\s|$)/i,
  /(?:^|\s)(?:~\/|\/[^\s]+\/)?\.kube(?:\/|\s|$)/i,
  /(?:^|\s)(?:~\/|\/[^\s]+\/)?\.docker(?:\/|\s|$)/i,
  /(?:^|\s)(?:~\/|\/[^\s]+\/)?\.env(?:\.[^\s]+)?(?:\s|$)/i,
  /(?:^|\s)(?:~\/|\/[^\s]+\/)?(?:id_rsa|id_ed25519)(?:\s|$)/i,
];

export function isDangerous(command: string): boolean {
  return DANGEROUS_PATTERNS.some((p) => p.test(command));
}

const SENSITIVE_PATH_PATTERNS = [
  /^\/etc(?:\/|$)/,
  /^\/var(?:\/|$)/,
  /^\/usr(?:\/|$)/,
  /^\/bin(?:\/|$)/,
  /^\/sbin(?:\/|$)/,
  /^\/System(?:\/|$)/,
  /^\/Library(?:\/|$)/,
  /(?:^|\/)\.ssh(?:\/|$)/,
  /(?:^|\/)\.gnupg(?:\/|$)/,
  /(?:^|\/)\.aws(?:\/|$)/,
  /(?:^|\/)\.kube(?:\/|$)/,
  /(?:^|\/)\.docker(?:\/|$)/,
  /(?:^|\/)\.config\/gh(?:\/|$)/,
  /(?:^|\/)\.config\/liteyuki-local-agent(?:\/|$)/,
  /(?:^|\/)(?:\.env|\.env\..*|id_rsa|id_ed25519|known_hosts)$/,
];

export function isSensitivePath(path: string): boolean {
  const expanded = expandPath(path);
  return SENSITIVE_PATH_PATTERNS.some((pattern) => pattern.test(expanded));
}

/** 将路径中的 ~ 展开为 home 目录 */
export function expandPath(p: string): string {
  if (p.startsWith("~/") || p === "~") {
    return join(homedir(), p.slice(1));
  }
  return resolve(p);
}

function formatCommandResult(result: CommandResult): string {
  const lines = [
    `exit_code: ${result.exitCode ?? "signal"}`,
    `duration_ms: ${result.durationMs}`,
    `timed_out: ${result.timedOut}`,
    `truncated: ${result.truncated}`,
  ];
  if (result.stdout) {
    lines.push("", "stdout:", result.stdout);
  }
  if (result.stderr) {
    lines.push("", "stderr:", result.stderr);
  }
  return lines.join("\n").slice(0, 100000);
}

function runCommand(cmd: string, options: {
  cwd: string;
  timeout: number;
  input?: string;
  maxBuffer?: number;
}): Promise<CommandResult> {
  return new Promise((resolveCommand) => {
    const startedAt = Date.now();
    const maxBuffer = options.maxBuffer ?? 4 * 1024 * 1024;
    let stdout = "";
    let stderr = "";
    let truncated = false;
    let timedOut = false;

    const child = spawn(cmd, {
      cwd: options.cwd,
      shell: true,
      stdio: ["pipe", "pipe", "pipe"],
    });

    const append = (kind: "stdout" | "stderr", chunk: Buffer) => {
      const text = chunk.toString("utf-8");
      const currentSize = Buffer.byteLength(stdout) + Buffer.byteLength(stderr);
      const remaining = maxBuffer - currentSize;
      if (remaining <= 0) {
        truncated = true;
        return;
      }
      const next = Buffer.byteLength(text) > remaining ? text.slice(0, remaining) : text;
      if (next.length < text.length) truncated = true;
      if (kind === "stdout") stdout += next;
      else stderr += next;
    };

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGTERM");
      setTimeout(() => {
        child.kill("SIGKILL");
      }, 2000).unref();
    }, options.timeout);

    child.stdout?.on("data", (chunk: Buffer) => append("stdout", chunk));
    child.stderr?.on("data", (chunk: Buffer) => append("stderr", chunk));
    child.on("error", (err) => {
      clearTimeout(timer);
      resolveCommand({
        exitCode: null,
        stdout,
        stderr: stderr ? `${stderr}\n${err.message}` : err.message,
        timedOut,
        durationMs: Date.now() - startedAt,
        truncated,
      });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolveCommand({
        exitCode: code,
        stdout,
        stderr,
        timedOut,
        durationMs: Date.now() - startedAt,
        truncated,
      });
    });

    if (options.input) {
      child.stdin?.write(options.input);
    }
    child.stdin?.end();
  });
}

export async function executeTool(request: ToolRequest): Promise<ToolResponse> {
  const { id, tool, args } = request;

  try {
    switch (tool) {
      case "run_command": {
        const cmd = args.command as string;
        if (typeof cmd !== "string" || !cmd.trim()) {
          return { id, error: "run_command requires a non-empty string command" };
        }
        const cwd = args.cwd
          ? expandPath(args.cwd as string)
          : process.cwd();
        const timeout = Math.min(Math.max((args.timeout as number) || 60000, 1000), 10 * 60 * 1000);
        const result = await runCommand(cmd, {
          cwd,
          timeout,
        });
        const output = formatCommandResult(result);
        return result.exitCode === 0 && !result.timedOut
          ? { id, result: output }
          : { id, error: output };
      }

      case "read_file": {
        if (typeof args.path !== "string" || !args.path) {
          return { id, error: "read_file requires a string path" };
        }
        const path = expandPath(args.path);
        const content = readFileSync(path, "utf-8");
        return { id, result: content.slice(0, 100000) };
      }

      case "write_file": {
        if (typeof args.path !== "string" || !args.path) {
          return { id, error: "write_file requires a string path" };
        }
        const content = args.content as string;
        if (typeof content !== "string") {
          return { id, error: "write_file requires string content" };
        }
        const path = expandPath(args.path);
        writeFileSync(path, content, "utf-8");
        return { id, result: `Written ${content.length} bytes to ${path}` };
      }

      case "list_files": {
        if (args.path !== undefined && typeof args.path !== "string") {
          return { id, error: "list_files path must be a string when provided" };
        }
        const dir = expandPath((args.path as string) || ".");
        const entries = readdirSync(dir).map((name) => {
          const fullPath = join(dir, name);
          try {
            const stat = statSync(fullPath);
            return {
              name,
              type: stat.isDirectory() ? "dir" : "file",
              size: stat.size,
            };
          } catch {
            return { name, type: "unknown", size: 0 };
          }
        });
        return { id, result: JSON.stringify(entries, null, 2) };
      }

      default:
        return { id, error: `Unknown tool: ${tool}` };
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { id, error: msg.slice(0, 5000) };
  }
}

/**
 * 用 sudo -S 执行命令（通过 stdin 传入密码，密码不会出现在进程列表中）。
 * 密码仅在内存中使用，绝不写盘/不打日志。
 */
export async function executeSudoTool(request: ToolRequest, password: string): Promise<ToolResponse> {
  const { id, args } = request;
  const cmd = args.command as string;
  const cwd = args.cwd ? expandPath(args.cwd as string) : process.cwd();
  const timeout = Math.min(Math.max((args.timeout as number) || 60000, 1000), 10 * 60 * 1000);

  try {
    // 将 sudo 替换为 sudo -S（从 stdin 读密码），避免终端交互
    const sudoCmd = cmd.replace(/\bsudo(?!\s+-S)\b/, "sudo -S -p ''");
    const result = await runCommand(sudoCmd, {
      cwd,
      timeout,
      input: password + "\n",  // 通过 stdin 传密码
    });
    const output = formatCommandResult(result);
    return result.exitCode === 0 && !result.timedOut
      ? { id, result: output }
      : { id, error: output };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { id, error: msg.slice(0, 5000) };
  }
}

export function decryptPassword(encryptedPassword: string, privateKeyPem: string): string {
  return privateDecrypt(
    {
      key: privateKeyPem,
      padding: constants.RSA_PKCS1_OAEP_PADDING,
      oaepHash: "sha256",
    },
    Buffer.from(encryptedPassword, "base64"),
  ).toString("utf-8");
}
