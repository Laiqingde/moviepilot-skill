---
name: moviepilot
description: Control a MoviePilot media-automation server. Use whenever the human asks to search a movie or TV show, subscribe/unsubscribe, check active downloads, or check what was recently organized into the library. Wraps the MoviePilot v2 REST API via a small Python CLI.
metadata: {"openclaw":{"requires":{"bins":["python3"]},"primaryEnv":"MP_URL"}}
---

# MoviePilot

You can control a MoviePilot server through the CLI at
`{baseDir}/scripts/mp.py`. All commands print JSON to stdout — always parse
and summarize results for the human in plain Chinese, do not dump raw JSON
unless asked.

## FIRST-RUN: configure binding (MANDATORY)

**The very first time this skill is loaded in a conversation, your first
action MUST be to check the binding and, if missing, ask the human to
provide their MoviePilot connection.** Do not call any other subcommand
before configuration succeeds.

Step 1 — check status:
```bash
python3 {baseDir}/scripts/mp.py status
```

Step 2 — if `configured: false`, send the human exactly this message in
Chinese and then STOP and wait for their reply:

> 检测到 MoviePilot 还没有绑定。请发送以下信息完成绑定：
> 1. MoviePilot 地址（例如 `http://192.168.1.10:3000`）
> 2. 认证方式二选一：
>    - **API Token**（在 MoviePilot 设置 → 系统 → API 令牌 中获取），或
>    - **用户名 + 密码**

Step 3 — once the human replies with the URL and either an api-token OR
username+password, run ONE of:

```bash
# 方式 A: API token
python3 {baseDir}/scripts/mp.py configure --url <URL> --api-token <TOKEN>

# 方式 B: 用户名 / 密码
python3 {baseDir}/scripts/mp.py configure --url <URL> --username <U> --password <P>
```

`configure` writes `{baseDir}/config.json` (chmod 600) and verifies the
binding by calling `/dashboard/statistic`. On success, report to the human
in Chinese: 绑定成功 + 服务器统计（电影/电视剧/集数/用户数）。On failure,
show the exact error and ask the human to re-check URL and credentials.

If the human asks to re-bind / change server / 重新配置, just run
`configure` again — it overwrites the existing config.

## When to use this skill

- 用户提到电影、电视剧、番剧、动漫、纪录片，并希望搜索 / 订阅 / 下载 / 整理
- 用户问"最近下载了什么 / 下载进度 / 入库情况"
- 用户想查看或取消现有订阅
- 用户提到 MoviePilot / mp / 媒体服务器订阅
- 用户想绑定 / 重新绑定 / 更换 MoviePilot 实例

## Commands (require an existing binding)

```bash
# 0. 查看绑定状态（不会暴露凭据）
python3 {baseDir}/scripts/mp.py status

# 1. 搜索
python3 {baseDir}/scripts/mp.py search "流浪地球" [--type movie|tv] [--limit 10]

# 2. 订阅 (tmdbid 来自 search 结果)
python3 {baseDir}/scripts/mp.py subscribe-add 535167 --type movie
python3 {baseDir}/scripts/mp.py subscribe-add 218642 --type tv --season 1

# 3. 订阅列表 / 删除（默认每页 30，支持过滤，避免一次拉爆 context）
python3 {baseDir}/scripts/mp.py subscribe-list [--limit 30] [--page 1] \
    [--type movie|tv] [--keyword 三体] [--state R]
python3 {baseDir}/scripts/mp.py subscribe-del 29

# 4. 当前下载任务（默认 limit 20，支持按状态/关键词过滤）
python3 {baseDir}/scripts/mp.py downloads [--limit 20] \
    [--state downloading|stalledDL|pausedDL] [--keyword 三体]

# 5. 入库 / 整理历史
python3 {baseDir}/scripts/mp.py history [--page 1] [--count 20]

# 6. 已安装插件列表
python3 {baseDir}/scripts/mp.py plugins

# 7. 万能逃生口 (任意 MoviePilot API)
python3 {baseDir}/scripts/mp.py raw GET /dashboard/statistic
python3 {baseDir}/scripts/mp.py raw POST /subscribe/ --json '{"name":"x","tmdbid":1,"type":"电影"}'
```

## Token efficiency

- `subscribe-list` 和 `downloads` 都是分页的。**永远不要为了"看全部"而把 limit 调到很大**——
  先用默认 limit 看 `total`，再按需 `--keyword` / `--type` / `--state` 过滤，或翻 `--page`。
- 用户问"我订了什么《三体》" → `subscribe-list --keyword 三体`，不要全量拉。
- 用户问"现在在下什么" → `downloads --state downloading`，不要全量拉。
- 用户问"全部订阅有多少" → 直接看返回里的 `total` 字段，不要为了数数翻完所有页。

## Workflow rules

1. **订阅前必须先 search**，拿到准确的 `tmdb_id` 和 `type`，再调用 `subscribe-add`，避免订错条目。
2. 用户说“订阅 X 第 2 季”时，`--type tv --season 2`。不指定季时不要加 `--season`。
3. 调用 `subscribe-del` 这类不可逆操作前，向用户确认（显示将要删除的订阅名+id）。
4. 不要把 API token、密码、`config.json` 或 `jwt.json` 内容回显给用户或写入日志。
5. 报错时把 stderr 原文展示给用户，不要自行编造修复方案。
6. 如果任何子命令返回 `MoviePilot is not configured yet`，回到首次配置流程。
