# RenderDoc MCP Server

作为 RenderDoc UI 扩展运行的 MCP 服务器。AI 助手可以访问 RenderDoc 捕获数据，辅助进行图形调试。

## 架构

```
Claude/AI Client (stdio)
        │
        ▼
MCP Server Process (Python + FastMCP 2.0)
        │ File-based IPC (%TEMP%/renderdoc_mcp/)
        ▼
RenderDoc Process (Extension)
```

由于 RenderDoc 内置的 Python 不包含 socket 模块，因此通过基于文件的 IPC 进行通信。

## 安装

### 1. 安装 RenderDoc 扩展

```bash
python scripts/install_extension.py
```

扩展将安装到 `%APPDATA%\qrenderdoc\extensions\renderdoc_mcp_bridge`。

### 2. 在 RenderDoc 中启用扩展

1. 启动 RenderDoc
2. 打开 Tools > Manage Extensions
3. 启用“RenderDoc MCP Bridge”

### 3. 安装 MCP 服务器

```bash
uv tool install
uv tool update-shell  # 添加到 PATH
```

重启 shell 后即可使用 `renderdoc-mcp` 命令。

> **提示**：使用 `--editable` 后，源码修改会立即生效，适合开发时使用。
> 如果需要以稳定版方式安装，请使用 `uv tool install .`。

### 4. 配置 MCP 客户端

#### Claude Desktop

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "renderdoc": {
      "command": "renderdoc-mcp"
    }
  }
}
```

#### Claude Code

在 `.mcp.json` 中添加：

```json
{
  "mcpServers": {
    "renderdoc": {
      "command": "renderdoc-mcp"
    }
  }
}
```

## 使用方法

1. 启动 RenderDoc 并打开捕获文件（.rdc）
2. 通过 MCP 客户端（如 Claude）访问 RenderDoc 数据

## MCP 工具一览

| 工具 | 说明 |
|--------|------|
| `get_capture_status` | 查看捕获文件的加载状态 |
| `get_draw_calls` | 以层级结构获取 Draw Call 列表 |
| `get_draw_call_details` | 获取指定 Draw Call 的详细信息 |
| `get_shader_info` | 获取 Shader 源码和常量缓冲区的值 |
| `get_buffer_contents` | 获取缓冲区内容（Base64） |
| `get_texture_info` | 获取纹理元数据 |
| `get_texture_data` | 获取纹理像素数据（Base64） |
| `get_pipeline_state` | 获取渲染管线状态 |
| `run_python_shell` | 在 RenderDoc 扩展进程中执行 Python 代码片段 |
| `run_python_script` | 在 RenderDoc 扩展进程中执行 Python 脚本文件 |

## 使用示例

### 获取 Draw Call 列表

```
get_draw_calls(include_children=true)
```

### 获取 Shader 信息

```
get_shader_info(event_id=123, stage="pixel")
```

### 获取渲染管线状态

```
get_pipeline_state(event_id=123)
```

### 执行 Python Shell

```
run_python_shell(code="ctx.CurSelectedEvent()")
```

```
run_python_shell(
    code="print(ctx.GetCaptureFilename())\nctx.CurSelectedEvent()",
    run_on_replay_thread=false,
)
```

Shell 会在会话期间保留状态，并可使用 `ctx` / `facade` / `invoke` / `rd` / `qrd`。

### 执行 Python 脚本

```
run_python_script(
    script_path="D:/GPU/scripts/renderdoc_probe.py",
    script_args=["--event", "123"],
)
```

脚本通过 `script_args` 接收参数；设置 `__mcp_result__` 或 `result` 后，其值会作为结构化结果返回。

### 获取纹理数据

```
# 获取 2D 纹理的 mip 0
get_texture_data(resource_id="ResourceId::123")

# 获取指定的 mip 级别
get_texture_data(resource_id="ResourceId::123", mip=2)

# 获取立方体纹理的指定面（0=X+, 1=X-, 2=Y+, 3=Y-, 4=Z+, 5=Z-）
get_texture_data(resource_id="ResourceId::456", slice=3)

# 获取 3D 纹理的指定深度切片
get_texture_data(resource_id="ResourceId::789", depth_slice=5)
```

### 获取部分缓冲区数据

```
# 获取整个缓冲区
get_buffer_contents(resource_id="ResourceId::123")

# 从偏移量 256 处获取 512 字节
get_buffer_contents(resource_id="ResourceId::123", offset=256, length=512)
```

## 要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- RenderDoc 1.20+

> **提示**：目前仅在 Windows + DirectX 11 环境中验证过。
> 理论上也可能在 Linux/macOS + Vulkan/OpenGL 环境中运行，但尚未验证。

## 许可证

MIT
