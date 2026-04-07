# moviepilot-skill

一个 [OpenClaw](https://github.com/openclaw/openclaw) 原生 skill，让你的 OpenClaw agent 可以直接操控 [MoviePilot](https://github.com/jxxghp/MoviePilot) 媒体自动化服务器：搜索影视、添加/管理订阅、查看下载进度、检查入库历史、调用任意 MoviePilot API。

> 装上之后，你可以直接对 OpenClaw agent 说：
> - "帮我订阅《三体》第二季"
> - "现在 MoviePilot 在下什么？"
> - "今天入库了哪些剧集？"
> - "把师兄啊师兄的订阅取消掉"

agent 会自动调用本 skill 完成对应操作，并用中文向你汇报。

---

## ✨ 功能特性

| 能力 | 子命令 | 说明 |
| --- | --- | --- |
| 🔐 首次绑定 | `configure` | 支持 API Token 或 用户名+密码 两种认证方式，凭据本地保存（chmod 600） |
| 🩺 状态自检 | `status` | 查看当前绑定 + 服务器可达性，不暴露凭据 |
| 🔍 搜索影视 | `search` | 走 TMDB / 豆瓣聚合搜索，可按电影/电视剧过滤 |
| ➕ 添加订阅 | `subscribe-add` | 支持指定季 (`--season`)，自动补全名称/海报 |
| 📋 订阅列表 | `subscribe-list` | 精简输出：id、名称、年份、季、状态 |
| ❌ 取消订阅 | `subscribe-del` | 不可逆操作，agent 会先和你确认 |
| ⬇️ 下载任务 | `downloads` | 当前所有下载任务的进度、速度、大小、状态 |
| 📦 入库历史 | `history` | 最近整理/入库的剧集和电影记录 |
| 🧩 已装插件 | `plugins` | 列出 MoviePilot 已安装的插件 |
| 🛠 任意 API | `raw` | 万能逃生口，调用任何 MoviePilot v2 REST API |

零外部依赖，仅使用 Python 3 标准库。

---

## 📦 安装

### 1. 克隆到 OpenClaw skills 目录

```bash
git clone https://github.com/Laiqingde/moviepilot-skill.git ~/.openclaw/skills/moviepilot
```

### 2. 重启 OpenClaw agent

```bash
openclaw agent --message "测试 moviepilot skill"
```

第一次触发本 skill 时，agent 会自动检测到尚未绑定，并主动向你索要 MoviePilot 连接信息。

### 3. 系统要求

- macOS / Linux
- Python 3.8+（系统自带即可，无需 `pip install` 任何东西）
- 一台可访问的 MoviePilot v2 实例

---

## 🚀 首次使用

### 方式 A：让 agent 引导你（推荐）

直接告诉 agent："帮我配置 moviepilot"或者直接发起一个媒体相关请求。agent 会发出如下提示：

> 检测到 MoviePilot 还没有绑定。请发送以下信息完成绑定：
> 1. MoviePilot 地址（例如 `http://192.168.1.10:3000`）
> 2. 认证方式二选一：
>    - **API Token**（在 MoviePilot 设置 → 系统 → API 令牌 中获取），或
>    - **用户名 + 密码**

你只需要回复这些信息，agent 就会自动调用 `configure`、验证连通性，并汇报服务器统计（电影数 / 电视剧数 / 集数 / 用户数）。

### 方式 B：手动命令行绑定

```bash
# 用 API Token 绑定（推荐，权限可控）
python3 ~/.openclaw/skills/moviepilot/scripts/mp.py configure \
  --url http://YOUR_HOST:3000 \
  --api-token YOUR_API_TOKEN

# 或者用用户名 / 密码绑定
python3 ~/.openclaw/skills/moviepilot/scripts/mp.py configure \
  --url http://YOUR_HOST:3000 \
  --username YOUR_USERNAME \
  --password YOUR_PASSWORD
```

绑定成功后会输出类似：

```json
{
  "ok": true,
  "mode": "api_token",
  "url": "http://YOUR_HOST:3000",
  "stats": {
    "movie_count": 16084,
    "tv_count": 7581,
    "episode_count": 305802,
    "user_count": 4270
  }
}
```

### 重新绑定 / 切换实例

直接再次运行 `configure`，会覆盖原有 `config.json`。也可以让 agent 帮你做："换一台 MoviePilot 服务器"。

---

## 🔐 凭据安全

- 凭据保存在 `~/.openclaw/skills/moviepilot/config.json`，文件权限为 `600`（仅当前用户可读写）
- 用户名/密码模式下，登录拿到的 JWT 缓存在 `jwt.json`，遇到 401 自动重新登录
- `config.json` / `jwt.json` 已加入 `.gitignore`，**不会被 commit 到任何 git 仓库**
- skill 在 `SKILL.md` 中明确告诉 agent：**永远不要回显 token、密码或这两个文件的内容**

如需手动清除绑定：

```bash
rm ~/.openclaw/skills/moviepilot/config.json ~/.openclaw/skills/moviepilot/jwt.json
```

---

## 📖 命令速查

所有命令都通过 `python3 ~/.openclaw/skills/moviepilot/scripts/mp.py <子命令>` 调用，输出为 JSON。

### 配置管理

```bash
mp.py status                                       # 查看绑定状态
mp.py configure --url URL --api-token TOKEN        # 绑定 (token 模式)
mp.py configure --url URL --username U --password P  # 绑定 (账号模式)
```

### 搜索

```bash
mp.py search "流浪地球"                # 综合搜索
mp.py search "三体" --type tv          # 只看电视剧
mp.py search "复仇者" --type movie --limit 5
```

### 订阅

```bash
mp.py subscribe-add 535167 --type movie              # 订阅电影
mp.py subscribe-add 218642 --type tv --season 1      # 订阅电视剧第 1 季
mp.py subscribe-list                                 # 默认每页 30
mp.py subscribe-list --keyword 三体                   # 按名字过滤
mp.py subscribe-list --type tv --page 2 --limit 20   # 翻页
mp.py subscribe-del 29                               # 取消订阅 id=29
```

> tmdbid 来自 `search` 结果中的 `tmdb_id` 字段。建议先 search、再 subscribe-add，避免订错条目。

### 下载与入库

```bash
mp.py downloads                              # 默认 limit 20
mp.py downloads --state downloading          # 只看正在下的
mp.py downloads --keyword 三体                # 按关键词过滤
mp.py history --page 1 --count 20            # 最近 20 条入库记录
```

### 插件

```bash
mp.py plugins                                # 列出已安装插件
```

### 万能逃生口

任何上面没封装的接口，都可以用 `raw` 直接调用 MoviePilot 的 v2 REST API：

```bash
# GET 请求
mp.py raw GET /dashboard/statistic

# POST 请求 + JSON body
mp.py raw POST /subscribe/ --json '{"name":"流浪地球","tmdbid":535167,"type":"电影"}'
```

---

## 🗂 项目结构

```
moviepilot/
├── SKILL.md            # OpenClaw skill 清单 + 给 agent 的中文使用规则
├── README.md           # 本文件
├── .gitignore          # 排除 config.json / jwt.json
└── scripts/
    └── mp.py           # 主 CLI（零依赖，Python 标准库）
```

运行时还会生成（被 .gitignore 忽略）：

```
├── config.json         # 你的连接信息（chmod 600）
└── jwt.json            # JWT 缓存（仅账号密码模式下生成）
```

---

## 🤖 Agent 行为约束

`SKILL.md` 中已经写入以下规则，OpenClaw agent 会严格遵守：

1. **首次必须先绑定**：未配置时不会执行任何其他子命令
2. **订阅前必须先 search**：拿到准确的 `tmdb_id` 再调用 `subscribe-add`，避免订错
3. **不可逆操作必须确认**：例如 `subscribe-del` 会先告知你要删的订阅名+id 再执行
4. **凭据零回显**：永远不会把 token / 密码 / config.json 内容贴回对话或日志
5. **报错原文展示**：遇到错误把 stderr 直接给你，不会编造修复方案
6. **结果中文汇报**：JSON 结果会被翻译为中文摘要，不会刷屏

---

## 🐛 常见问题

**Q: 提示 `MoviePilot is not configured yet`？**
A: 还没有绑定。运行 `mp.py configure ...` 或者让 agent 引导你绑定。

**Q: 用账号密码登录失败？**
A: MoviePilot 默认要求用户名而非邮箱。可以先在浏览器登录验证一下凭据正确，再用 `mp.py configure` 重试。

**Q: token 模式 401？**
A: 在 MoviePilot 设置 → 系统 → API 令牌 重新生成一个并重新 `configure`。

**Q: 怎么看子命令完整帮助？**
A: `python3 mp.py <子命令> --help`

**Q: agent 没触发这个 skill？**
A: 确认目录在 `~/.openclaw/skills/moviepilot/` 且 `SKILL.md` 存在，然后重启 openclaw agent。

---

## 🛣 路线图

- [ ] 手动触发整理 / 重新刮削
- [ ] 站点签到状态查询
- [ ] 订阅日历视图
- [ ] 批量订阅（从豆瓣片单导入）
- [ ] 支持 HTTPS 自签证书的 MoviePilot 实例

欢迎提 issue / PR。

---

## 📄 License

MIT
