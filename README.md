# moviepilot-skill

一个 [OpenClaw](https://github.com/openclaw/openclaw) 原生 skill，让你的 OpenClaw agent 通过 **MoviePilot 内置的 MCP 端点**远程操控 [MoviePilot](https://github.com/jxxghp/MoviePilot) 媒体自动化服务器。

> **与 MoviePilot 官方 `moviepilot-cli` skill 完全工具兼容**：使用同一套自描述的 40+ 工具（`search_media` / `add_subscribe` / `query_download_tasks` …），但用 Python 标准库零依赖实现，并增加了首次绑定向导、远程访问支持和 token 过载预警。

装上之后，你可以直接对 OpenClaw agent 说：

- "帮我搜《流浪地球》并加入订阅"
- "现在 MoviePilot 在下什么？只看正在下载的"
- "今天入库了哪些剧集？"
- "把师兄啊师兄的订阅取消掉"
- "搜下《沙丘 2》能不能下，找 1080p 免费的"

agent 会自动用中文向你汇报。

---

## ✨ 设计理念

| | 本 skill | 官方 `moviepilot-cli` |
| --- | --- | --- |
| 运行时 | Python 3 标准库（零依赖） | Node.js |
| 工具来源 | MoviePilot `/api/v1/mcp/tools`（自描述，40+ 工具） | 同上 |
| 工具命名 | 与官方完全一致 | — |
| 部署位置 | OpenClaw 客户端本机，**远程操控**任意 MP 实例 | 假设跑在 MP 容器内部 |
| 首次绑定 | **交互式向导**（agent 主动问你要 URL + Key） | CLI 参数 |
| 多实例切换 | 重新 `configure` 即可 | — |
| Token 过载预警 | ✅ 单次结果超 8k 字符自动 stderr 警告 | ❌ |
| 认证 | API Key（推荐） / 用户名密码 | API Key |

---

## 🧩 工具一览

skill 本身不内置业务命令，只提供 4 个发现/调用入口；所有 40+ 业务工具来自 MoviePilot 自身：

| 子命令 | 说明 |
| --- | --- |
| `configure` | 首次绑定 MoviePilot 实例 |
| `status` | 查看当前绑定 + 可达性 + MCP 工具数 |
| `list [--keyword X]` | 列出全部 MCP 工具（关键词过滤） |
| `show <tool>` | 显示某工具的参数 schema |
| `call <tool> [k=v ...]` | 调用任意 MCP 工具 |

调用前 agent 会先 `show <tool>` 自动发现参数名，永远不会瞎猜。

### MoviePilot 提供的工具分类（实例不同数量略有差异）

| 类别 | 示例工具 |
| --- | --- |
| 媒体搜索 | `search_media`、`recognize_media`、`query_media_detail`、`get_recommendations`、`search_person` |
| 种子搜索 | `search_torrents`、`get_search_results` |
| 下载管理 | `add_download`、`query_download_tasks`、`delete_download`、`query_downloaders` |
| 订阅管理 | `add_subscribe`、`query_subscribes`、`update_subscribe`、`delete_subscribe`、`search_subscribe` |
| 媒体库 | `query_library_exists`、`query_library_latest`、`transfer_file`、`scrape_metadata`、`query_transfer_history` |
| 文件 | `list_directory`、`query_directory_settings` |
| 站点 | `query_sites`、`query_site_userdata`、`test_site`、`update_site_cookie` |
| 系统 | `query_schedulers`、`run_scheduler`、`query_workflows`、`run_workflow`、`query_episode_schedule`、`send_message` |

---

## 📦 安装

### 1. 克隆到 OpenClaw skills 目录

```bash
git clone https://github.com/Laiqingde/moviepilot-skill.git ~/.openclaw/skills/moviepilot
```

### 2. 重启 OpenClaw agent

```bash
openclaw agent --message "帮我配置一下 MoviePilot"
```

第一次触发本 skill 时，agent 会自动检测到尚未绑定，并主动向你索要连接信息。

### 3. 系统要求

- macOS / Linux
- Python 3.8+（系统自带，**无需 pip install 任何东西**）
- 一台可访问的 **MoviePilot v2** 实例，且开启了 MCP 端点（默认开启）

---

## 🚀 首次使用

### 方式 A：让 agent 引导你（推荐）

直接说"帮我配置 moviepilot"，agent 会发出：

> 检测到 MoviePilot 还没有绑定。请发送以下信息：
> 1. MoviePilot 地址（如 `http://192.168.1.10:3000`）
> 2. 认证方式：
>    - **推荐：API Key**（MoviePilot 设置 → 系统 → API 令牌），开启全部 40+ MCP 工具
>    - 用户名 + 密码（仅可用 status，**MCP 工具不可用**）

回复后 agent 自动完成绑定、验证 MCP 可达，并汇报工具数量。

### 方式 B：手动 CLI 绑定

```bash
# 推荐：API Key（开启 MCP 全部工具）
python3 ~/.openclaw/skills/moviepilot/scripts/mp.py configure \
  --url http://YOUR_HOST:3000 --api-token YOUR_API_KEY

# 仅有用户密码（MCP 不可用）
python3 ~/.openclaw/skills/moviepilot/scripts/mp.py configure \
  --url http://YOUR_HOST:3000 --username U --password P
```

成功输出示例：

```json
{
  "ok": true,
  "mode": "api_token",
  "url": "http://YOUR_HOST:3000",
  "mcp_tools_count": 40,
  "mcp_supported": true
}
```

### 重新绑定 / 切换实例

直接再次运行 `configure`，会覆盖原有 `config.json`。

---

## 🔐 凭据安全

- 凭据保存在 `~/.openclaw/skills/moviepilot/config.json`，权限 `600`
- 用户名/密码模式下 JWT 缓存到 `jwt.json`，401 自动重新登录
- `config.json` / `jwt.json` 已加入 `.gitignore`，不会被 commit
- SKILL.md 明确指示 agent **永远不要回显 token / 密码 / 这两个文件的内容**

清除绑定：

```bash
rm ~/.openclaw/skills/moviepilot/config.json ~/.openclaw/skills/moviepilot/jwt.json
```

---

## 📖 命令速查

```bash
# === 配置 ===
mp.py status                                        # 查看绑定
mp.py configure --url URL --api-token KEY           # 绑定 (推荐)
mp.py configure --url URL --username U --password P # 绑定 (仅 status 可用)

# === 工具发现 ===
mp.py list                                          # 列出全部 40+ 工具
mp.py list --keyword subscribe                      # 关键词过滤

# === 查参数 ===
mp.py show search_media
mp.py show add_subscribe

# === 调用 ===
mp.py call search_media title=流浪地球 media_type=电影
mp.py call query_subscribes status=R
mp.py call query_download_tasks status=downloading
mp.py call add_subscribe title=三体 year=2023 media_type=电视剧 tmdb_id=108545 season=1
mp.py call delete_subscribe subscribe_id=29
```

### 参数类型自动推断

| 写法 | 推断为 |
| --- | --- |
| `key=true` / `key=false` | bool |
| `key=null` | null |
| `key=42` / `key=3.14` | int / float |
| `key=[1,2,3]` / `key={"a":1}` | JSON |
| `key=任意文本` | string |

---

## 🤖 Agent 行为约束

`SKILL.md` 中已写入以下规则，OpenClaw agent 会严格遵守：

1. **首次必须先绑定**：未配置时不会调用任何 MCP 工具
2. **调用前必须先 `show`**：参数名不能猜，每次调用前都查 schema
3. **搜索 → 检查 → 订阅/下载**：加订阅或下载前先查库存和已有订阅，避免重复
4. **不可逆操作必须确认**：`delete_*`、`update_site_cookie`、`run_scheduler` 等先告知再执行
5. **种子下载多步交互**：`search_torrents` 后停下让用户选 filter，不自作主张
6. **凭据零回显**：永远不会把 API key / 密码 / config 内容贴回对话或日志
7. **结果中文汇报**：JSON 结果会被翻译为中文摘要，不会刷屏

---

## 💡 Token 优化

本 skill 在多个层面控制 context 消耗：

1. **`list` 输出精简**：每个工具只回 `name + 描述首句`（截到 140 字），40 个工具一次拉取约 2.5k tokens
2. **`show` 按需调用**：只在 agent 真要用某工具前查参数，单次约 600 tokens
3. **过载预警**：`call` 返回的结果超过 8000 字符时，stderr 自动打印 `# token-warning`，agent 看到会自动收窄过滤条件
4. **指导 agent 优先用过滤参数**：`status=`、`type=`、`keyword=` 等，避免一次拉全量
5. **数量类问题先看 total**：用户问"我订了多少"时，agent 只读 total 字段而不是把全部条目列出来

实测：常见对话稳定在 **2 – 5k tokens / 轮次**。

---

## 🐛 常见问题

**Q: 提示 `MoviePilot is not configured yet`？**
A: 还没绑定。运行 `mp.py configure ...` 或让 agent 引导你。

**Q: 提示 `MCP tools require an API key`？**
A: 你用的是用户密码模式。重新运行 `mp.py configure --url ... --api-token ...`。MCP 端点只接受 API Key 认证。

**Q: 我的 MoviePilot 没有 `/api/v1/mcp/tools` 端点？**
A: 升级到支持 MCP 的 MoviePilot v2 版本。绝大多数近期版本都支持。

**Q: 工具数量比官方少？**
A: 不同 MoviePilot 版本/插件配置下数量略有差异。运行 `mp.py list` 查看你这台实例的实际数量。

**Q: 怎么看某个工具支持哪些参数？**
A: `mp.py show <tool_name>`，会列出每个参数的类型、是否必需、描述、枚举值和默认值。

---

## 🛣 路线图

- [ ] 添加 `call --json '{...}'` 一次性传完整参数体
- [ ] 添加 `call --dry-run` 只显示请求不执行
- [ ] 内置常见 workflow 别名（"search-and-subscribe"、"daily-digest"）
- [ ] 多实例支持（一次绑多台 MP）

欢迎提 issue / PR。

---

## 📄 License

MIT
