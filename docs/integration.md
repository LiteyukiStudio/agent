# Liteyuki Flow — 第三方 Agent 接入文档

本文档面向想要将自己的 Agent 或应用通过 WebSocket 接入 Liteyuki Flow 云端平台的开发者。

## 概览

```
你的 Agent/应用                          Liteyuki Flow
┌──────────────┐    WebSocket    ┌─────────────────┐
│ Your Agent   │ ──────────────▶│ flow.liteyuki.org│
│              │◀────────────── │                 │
│ 执行工具     │   指令 / 结果   │ AI Agent        │
└──────────────┘                └─────────────────┘
```

你的 Agent 作为**工具执行器**，通过 WebSocket 连接到云端。云端 AI 下发指令，你的 Agent 执行后返回结果。

---

## 1. 认证

### 获取 API Token

有两种方式获取 Token：

#### 方式一：Web 界面手动创建

1. 登录 https://flow.liteyuki.org/settings
2. 在「API Tokens」区域点击「创建 Token」
3. 设置名称和可选过期时间
4. 复制生成的 `lys_...` 格式 Token

#### 方式二：Device Code Flow（适合无浏览器环境）

```
POST https://flow.liteyuki.org/api/v1/auth/device/code
Content-Type: application/json

{"server_url": "https://flow.liteyuki.org"}
```

响应：
```json
{
  "device_code": "abc123...",
  "user_code": "XYZW-1234",
  "verification_url": "https://flow.liteyuki.org/device?code=XYZW-1234",
  "expires_in": 600
}
```

引导用户在浏览器打开 `verification_url` 并授权，然后轮询：

```
POST https://flow.liteyuki.org/api/v1/auth/device/token
Content-Type: application/json

{"device_code": "abc123..."}
```

响应（未授权时）：
```json
{"status": "pending", "token": null}
```

响应（已授权）：
```json
{"status": "approved", "token": "lys_xxxxxxxx..."}
```

---

## 2. WebSocket 连接

### 端点

```
wss://flow.liteyuki.org/ws/local-agent?token=<TOKEN>&device_id=<DEVICE_ID>&device_name=<NAME>&os=<OS>&version=<VERSION>
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `token` | ✅ | API Token（`lys_...`） |
| `device_id` | ❌ | 设备唯一 ID（UUID 格式，首次连接自动生成并持久化） |
| `device_name` | ❌ | 设备显示名称（如 "My Server"） |
| `os` | ❌ | 操作系统标识（`linux`/`macos`/`windows`/`unknown`） |
| `version` | ❌ | Agent 版本号（如 `0.2.0`） |

### 连接生命周期

```
连接 → 认证校验 → accept → 心跳保活 → 接收指令/发送结果 → 断开
```

### 错误码

| Code | 含义 | 是否应重连 |
|------|------|-----------|
| 4001 | Token 无效 | ❌ 不要重连，需重新认证 |
| 4002 | 同一 device_id 新连接挤掉旧连接 | ❌ 不要重连 |
| 4003 | 设备被用户移除/Token 被吊销 | ❌ 不要重连 |
| 其他 | 网络问题等 | ✅ 3-5 秒后重连 |

---

## 3. 协议格式

所有消息均为 JSON 格式。

### 3.1 心跳（保活）

服务端每 **10 秒**发送一次 ping：

```json
{"type": "ping"}
```

客户端**必须**回复：

```json
{"type": "pong"}
```

> ⚠️ 如果不回复 pong，连接可能被中间代理判定空闲并断开。

### 3.2 接收指令（Server → Agent）

云端 AI 调用工具时，你的 Agent 会收到：

```json
{
  "id": "request-uuid-xxx",
  "tool": "run_command",
  "args": {
    "command": "ls -la /home/user",
    "cwd": "/home/user",
    "timeout": 30000
  }
}
```

### 3.3 返回结果（Agent → Server）

执行成功：

```json
{
  "id": "request-uuid-xxx",
  "result": "total 8\ndrwxr-xr-x 2 user user 4096 ..."
}
```

执行失败：

```json
{
  "id": "request-uuid-xxx",
  "error": "Permission denied: /root/secret"
}
```

### 3.4 危险操作确认（Agent → Server → Web 前端 → Server → Agent）

如果你的 Agent 判断某个操作是危险的，可以发起确认请求：

```json
{
  "type": "confirm_request",
  "id": "request-uuid-xxx",
  "tool": "run_command",
  "args": {"command": "rm -rf /tmp/old"}
}
```

服务端会推送给 Web 前端，用户审批后返回：

```json
{
  "type": "confirm_response",
  "id": "request-uuid-xxx",
  "approved": true,
  "always": false
}
```

| 字段 | 说明 |
|------|------|
| `approved: true` | 允许执行 |
| `approved: false` | 拒绝 |
| `always: true` | 始终允许（该会话内相同命令不再询问） |

---

## 4. 支持的工具

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `run_command` | `command`, `cwd?`, `timeout?` | 执行 shell 命令 |
| `read_file` | `path` | 读取文件内容 |
| `write_file` | `path`, `content` | 写入文件 |
| `list_files` | `path?` | 列出目录内容 |

你可以只实现部分工具，对不支持的返回 error：

```json
{
  "id": "xxx",
  "error": "Unsupported tool: write_file"
}
```

---

## 5. 实现示例

### Python

```python
import asyncio
import json
import subprocess
import uuid

import websockets

SERVER = "wss://flow.liteyuki.org/ws/local-agent"
TOKEN = "lys_your_token_here"
DEVICE_ID = str(uuid.uuid4())  # 首次生成后应持久化
DEVICE_NAME = "My Python Agent"


async def execute_tool(request: dict) -> dict:
    """执行云端下发的工具指令。"""
    tool = request["tool"]
    args = request["args"]
    req_id = request["id"]

    if tool == "run_command":
        try:
            result = subprocess.run(
                args["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=args.get("timeout", 30000) / 1000,
                cwd=args.get("cwd"),
            )
            output = result.stdout + result.stderr
            return {"id": req_id, "result": output[:50000]}
        except subprocess.TimeoutExpired:
            return {"id": req_id, "error": "Command timed out"}
        except Exception as e:
            return {"id": req_id, "error": str(e)}

    elif tool == "read_file":
        try:
            with open(args["path"], "r") as f:
                content = f.read(100000)
            return {"id": req_id, "result": content}
        except Exception as e:
            return {"id": req_id, "error": str(e)}

    elif tool == "write_file":
        try:
            with open(args["path"], "w") as f:
                f.write(args["content"])
            return {"id": req_id, "result": f"Written {len(args['content'])} bytes"}
        except Exception as e:
            return {"id": req_id, "error": str(e)}

    elif tool == "list_files":
        import os
        try:
            path = args.get("path", ".")
            entries = []
            for name in os.listdir(path):
                full = os.path.join(path, name)
                stat = os.stat(full)
                entries.append({
                    "name": name,
                    "type": "dir" if os.path.isdir(full) else "file",
                    "size": stat.st_size,
                })
            return {"id": req_id, "result": json.dumps(entries)}
        except Exception as e:
            return {"id": req_id, "error": str(e)}

    return {"id": req_id, "error": f"Unsupported tool: {tool}"}


async def main():
    url = (
        f"{SERVER}?token={TOKEN}"
        f"&device_id={DEVICE_ID}"
        f"&device_name={DEVICE_NAME}"
        f"&os=linux&version=1.0.0"
    )

    while True:
        try:
            async with websockets.connect(url) as ws:
                print("✅ Connected to Liteyuki Flow")
                async for raw in ws:
                    msg = json.loads(raw)

                    # 心跳
                    if msg.get("type") == "ping":
                        await ws.send(json.dumps({"type": "pong"}))
                        continue

                    # 确认响应（如果你实现了确认机制）
                    if msg.get("type") == "confirm_response":
                        # 处理确认结果...
                        continue

                    # 工具调用
                    if "id" in msg and "tool" in msg:
                        response = await execute_tool(msg)
                        await ws.send(json.dumps(response))

        except websockets.ConnectionClosedError as e:
            if e.code in (4001, 4002, 4003):
                print(f"❌ Connection closed ({e.code}): {e.reason}")
                break  # 不重连
            print(f"⚠ Disconnected ({e.code}), reconnecting in 3s...")
        except Exception as e:
            print(f"⚠ Error: {e}, reconnecting in 3s...")

        await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
```

### Go

```go
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"os/exec"
	"time"

	"github.com/gorilla/websocket"
)

const (
	server     = "wss://flow.liteyuki.org/ws/local-agent"
	token      = "lys_your_token_here"
	deviceID   = "your-persistent-uuid"
	deviceName = "My Go Agent"
)

type Request struct {
	ID   string                 `json:"id"`
	Type string                 `json:"type,omitempty"`
	Tool string                 `json:"tool,omitempty"`
	Args map[string]interface{} `json:"args,omitempty"`
}

type Response struct {
	ID     string `json:"id,omitempty"`
	Type   string `json:"type,omitempty"`
	Result string `json:"result,omitempty"`
	Error  string `json:"error,omitempty"`
}

func executeTool(req Request) Response {
	switch req.Tool {
	case "run_command":
		cmd := req.Args["command"].(string)
		out, err := exec.Command("sh", "-c", cmd).CombinedOutput()
		if err != nil {
			return Response{ID: req.ID, Error: err.Error()}
		}
		return Response{ID: req.ID, Result: string(out)}
	default:
		return Response{ID: req.ID, Error: fmt.Sprintf("Unsupported tool: %s", req.Tool)}
	}
}

func main() {
	u, _ := url.Parse(server)
	q := u.Query()
	q.Set("token", token)
	q.Set("device_id", deviceID)
	q.Set("device_name", deviceName)
	q.Set("os", "linux")
	q.Set("version", "1.0.0")
	u.RawQuery = q.Encode()

	for {
		c, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
		if err != nil {
			log.Printf("Connect failed: %v, retrying...", err)
			time.Sleep(3 * time.Second)
			continue
		}
		log.Println("✅ Connected")

		for {
			_, message, err := c.ReadMessage()
			if err != nil {
				log.Printf("Read error: %v", err)
				break
			}

			var req Request
			json.Unmarshal(message, &req)

			// 心跳
			if req.Type == "ping" {
				c.WriteJSON(Response{Type: "pong"})
				continue
			}

			// 工具调用
			if req.ID != "" && req.Tool != "" {
				resp := executeTool(req)
				c.WriteJSON(resp)
			}
		}

		c.Close()
		log.Println("Disconnected, reconnecting in 3s...")
		time.Sleep(3 * time.Second)
	}
}
```

---

## 6. 最佳实践

### 安全
- **持久化 device_id**：首次生成 UUID 后存储到本地文件，避免每次启动都创建新设备
- **Token 安全**：不要硬编码 Token，使用环境变量或配置文件
- **命令过滤**：对危险命令实现确认机制或拒绝执行

### 稳定性
- **心跳必须响应**：收到 `{"type":"ping"}` 后立即回 `{"type":"pong"}`
- **自动重连**：非致命断开后等 3-5 秒重连
- **不重连的情况**：close code 4001/4002/4003 表示认证问题，不应重连
- **超时处理**：命令执行设置合理超时，避免阻塞

### 性能
- **结果截断**：大输出应截断到合理长度（建议 50KB 以内）
- **并发执行**：如果需要并行处理多个指令，注意每个 request 的 `id` 是独立的

---

## 7. 调试

### 检查连接状态

```
GET https://flow.liteyuki.org/api/v1/local-agent/status?token=lys_xxx
```

响应：
```json
{
  "connected": true,
  "devices": [
    {"device_id": "xxx", "device_name": "My Agent", "os_type": "linux", "version": "1.0.0"}
  ]
}
```

### 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 连接后立即断开 | Token 无效 | 检查 Token 是否正确、是否过期 |
| 每隔几秒断开重连 | 未回复 ping | 确保处理 `{"type":"ping"}` |
| 同一设备互相踢 | 两个进程使用相同 device_id | 确保 device_id 唯一，或停止旧进程 |
| 收不到指令 | AI 未指定该设备 | 在 AI 对话中提到设备名或只有一个设备时自动选中 |
