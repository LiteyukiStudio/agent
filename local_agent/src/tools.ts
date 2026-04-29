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
  /\brm\s+-rf?\b/i,
  /\bsudo\b/i,
  /\bmkfs\b/i,
  /\bdd\s+if=/i,
  /\bformat\b/i,
  /\b>\s*\/dev\//i,
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
