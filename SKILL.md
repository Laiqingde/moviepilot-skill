---
name: moviepilot
description: Control a remote MoviePilot media-automation server through its built-in MCP endpoint. Compatible with the official moviepilot-cli skill (same tool names). Use whenever the human mentions movies, TV shows, anime, downloads, subscriptions, library, or MoviePilot. Talks to /api/v1/mcp/* via a small Python CLI.
metadata: {"openclaw":{"requires":{"bins":["python3"]},"primaryEnv":"MP_URL"}}
---

# MoviePilot

This skill is a thin wrapper around MoviePilot's MCP tool registry
(`/api/v1/mcp/*`). The remote server exposes 40+ self-describing tools
(`search_media`, `add_subscribe`, `query_download_tasks`, …). Tool names
are identical to the official `moviepilot-cli` skill bundled in
`jxxghp/MoviePilot`.

CLI: `python3 {baseDir}/scripts/mp.py`

All output is JSON on stdout. Always summarize results for the human in
plain Chinese — never dump raw JSON unless the human asks.

## FIRST-RUN: bind a MoviePilot instance (MANDATORY)

The very first time this skill is loaded in a conversation, your first
action MUST be to check the binding. Do not call any other subcommand
before configuration succeeds.

```bash
python3 {baseDir}/scripts/mp.py status
```

If `configured: false`, send the human exactly this message and STOP:

> 检测到 MoviePilot 还没有绑定。请发送以下信息：
> 1. MoviePilot 地址（如 `http://192.168.1.10:3000`）
> 2. 认证方式：
>    - **推荐：API Key**（MoviePilot 设置 → 系统 → API 令牌），开启 MCP 全部 40+ 工具
>    - 用户名 + 密码（仅可用 status，**MCP 工具不可用**）

Then run:

```bash
python3 {baseDir}/scripts/mp.py configure --url <URL> --api-token <KEY>
# 或
python3 {baseDir}/scripts/mp.py configure --url <URL> --username <U> --password <P>
```

`configure` writes `{baseDir}/config.json` (chmod 600), verifies the
binding by listing MCP tools, and reports tool count + URL. Re-running
overwrites the existing config (used for re-binding / switching server).

## Core subcommands

```bash
# 列出所有可用工具（默认 40 个，支持关键词过滤）
mp.py list                      # 全部
mp.py list --keyword subscribe  # 仅含 "subscribe" 的工具

# 查看某个工具的参数 schema（参数名不可猜，调用前必须先 show）
mp.py show search_media
mp.py show add_subscribe

# 调用任意工具，参数用 key=value 风格（自动类型推断）
mp.py call search_media title=流浪地球 media_type=电影
mp.py call query_subscribes status=R
mp.py call add_subscribe title=三体 year=2023 media_type=电视剧 tmdb_id=108545 season=1
```

参数值类型推断规则：
- `true` / `false` → bool
- `null` → null
- 纯数字 → int / float
- `{...}` / `[...]` / `"..."` → JSON 解析
- 其他 → 字符串

## Workflow rules (READ CAREFULLY)

1. **调用前必须先 `show`**：参数名不能猜。即使是熟悉的工具也要 `show` 一次，因为 MoviePilot 升级后参数可能变。
2. **搜索 → 订阅 / 下载 流程**：
   - 先 `call search_media title=...` 拿到 `tmdb_id`
   - 加订阅前先 `call query_subscribes tmdb_id=...` 和 `call query_library_exists tmdb_id=... media_type=...` 检查是否重复
   - 用户指定季时，先用 `query_media_detail` 验证季号（部分剧集 TMDB 季号与中文社区不同）
3. **不可逆操作必须确认**：`delete_subscribe`、`delete_download`、`delete_download delete_files=true`、`update_site_cookie`、`run_scheduler`、`run_workflow`、`scrape_metadata`、`transfer_file` 调用前先告知用户具体内容并等待确认。
4. **种子下载多步交互**：
   - `search_torrents` 返回 `filter_options` 后**停下**，把所有 filter 字段和值原样列给用户，等用户选完再 `get_search_results`
   - 不要自己挑、不要翻译枚举值
5. **中文汇报**：所有 JSON 结果用中文摘要给用户，仅在用户要求时才显示原始 JSON。

## Token efficiency

- 工具结果可能很大。CLI 在结果超过 8000 字符时会在 stderr 打印 `# token-warning`，看到就主动收窄过滤条件。
- 列订阅 / 列下载时**永远先用过滤参数**：
  - `call query_subscribes status=R` （只看运行中）
  - `call query_subscribes type=电视剧`
  - `call query_download_tasks status=downloading`
- 用户问"我订了多少" / "在下多少" → 先 call 一次拿数量，**不要把全部条目都列给用户**。
- 用户没指定数量时默认 10 条以内。
- `list` 命令本身只回 `name + description first sentence`，已经很轻；要看参数再 `show`。

## Security

- 永远不要回显 API key、密码、`config.json`、`jwt.json` 内容。
- 子命令报错就把 stderr 原文给用户，不要自行编造修复方案。
- 任何子命令返回 `MoviePilot is not configured yet` 时，回到首次配置流程。

## Compatibility

- 工具名与 [`jxxghp/MoviePilot/skills/moviepilot-cli`](https://github.com/jxxghp/MoviePilot/tree/main/skills/moviepilot-cli) 完全一致。两边参考资料通用。
- 与官方 skill 的差异：
  - 官方假设 agent 跑在 MoviePilot 容器内部（Node.js）
  - 本 skill 假设 agent 跑在外部客户端，**通过 HTTP 远程操控**（Python 标准库，零依赖）
  - 增加首次绑定向导和 token 过载预警
