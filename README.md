# moviepilot-skill

An [OpenClaw](https://github.com/openclaw/openclaw) skill that lets your agent control a [MoviePilot](https://github.com/jxxghp/MoviePilot) media-automation server: search titles, manage subscriptions, watch download progress, and inspect what was organized into the library.

## Install

```bash
git clone https://github.com/Laiqingde/moviepilot-skill.git ~/.openclaw/skills/moviepilot
```

Restart your OpenClaw agent. The first time the skill is invoked it will ask you for your MoviePilot URL and credentials.

## First-run binding

The skill stores nothing until you bind it. On first use the agent will prompt you for:

1. MoviePilot URL, e.g. `http://192.168.1.10:3000`
2. One of:
   - **API token** (MoviePilot → 设置 → 系统 → API 令牌), or
   - **Username + password**

You can also bind manually:

```bash
# API token
python3 ~/.openclaw/skills/moviepilot/scripts/mp.py configure \
  --url http://YOUR_HOST:3000 --api-token YOUR_TOKEN

# Username / password
python3 ~/.openclaw/skills/moviepilot/scripts/mp.py configure \
  --url http://YOUR_HOST:3000 --username U --password P
```

Credentials are written to `config.json` (chmod 600) next to the skill. JWTs (when using user/pass) are cached in `jwt.json` and refreshed automatically on 401. Both files are gitignored.

## Commands

| Command | Purpose |
| --- | --- |
| `status` | Show current binding + reachability |
| `configure` | Bind / re-bind a MoviePilot instance |
| `search <q> [--type movie\|tv] [--limit N]` | Search media |
| `subscribe-add <tmdbid> --type movie\|tv [--season N]` | Add a subscription |
| `subscribe-list` | List subscriptions |
| `subscribe-del <id>` | Delete a subscription |
| `downloads` | Show active downloads |
| `history [--page N --count N]` | Library transfer history |
| `plugins` | List installed MoviePilot plugins |
| `raw <METHOD> <path> [--json BODY]` | Escape hatch for any MoviePilot API |

All output is JSON on stdout. The skill instructs the agent to summarize results in Chinese for the human.

## Requirements

- `python3` (stdlib only, no pip dependencies)
- A reachable MoviePilot v2 instance

## License

MIT
