/**
 * 本地工具执行器：在用户电脑上执行云端下发的操作
 */
import { execSync } from "node:child_process";
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
];

export function isDangerous(command: string): boolean {
  return DANGEROUS_PATTERNS.some((p) => p.test(command));
}

/** 将路径中的 ~ 展开为 home 目录 */
function expandPath(p: string): string {
  if (p.startsWith("~/") || p === "~") {
    return join(homedir(), p.slice(1));
  }
  return resolve(p);
}

export function executeTool(request: ToolRequest): ToolResponse {
  const { id, tool, args } = request;

  try {
    switch (tool) {
      case "run_command": {
        const cmd = args.command as string;
        const cwd = args.cwd
          ? expandPath(args.cwd as string)
          : process.cwd();
        const timeout = (args.timeout as number) || 30000;
        const output = execSync(cmd, {
          cwd,
          timeout,
          encoding: "utf-8",
          maxBuffer: 1024 * 1024,
          stdio: ["pipe", "pipe", "pipe"],
        });
        return { id, result: output.slice(0, 50000) };
      }

      case "read_file": {
        const path = expandPath(args.path as string);
        const content = readFileSync(path, "utf-8");
        return { id, result: content.slice(0, 100000) };
      }

      case "write_file": {
        const path = expandPath(args.path as string);
        const content = args.content as string;
        writeFileSync(path, content, "utf-8");
        return { id, result: `Written ${content.length} bytes to ${path}` };
      }

      case "list_files": {
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
