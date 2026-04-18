# gh-autopost

Monitors GitHub repositories for new commits and publishes them to a Telegram channel topic. Supports multiple repos, branches, batch publishing, merge filtering, and Conventional Commits classification.

## Features

- Monitors multiple repositories and branches simultaneously
- Posts to a specific topic (thread) in a Telegram supergroup/channel
- Notifies admins after each publish
- Deduplication via PostgreSQL — survives container restarts
- Batches multiple commits into a single message (configurable threshold)
- Filters merge commits
- Classifies commits by Conventional Commits prefixes with emoji labels
- Timestamps in Moscow time (MSK)
- Retry with exponential backoff on GitHub API and Telegram errors
- GitHub rate-limit handling

## Message format

```
🔔 New commit

📦 Repo: `backend`
🌿 Branch: `main`
✨ Feature
👤 Author: Ivan Ivanov
📅 Date: 17.04.2026 14:32:10 МСК

💬 feat: add OAuth authorization

📊 Stats:
• Files changed: 5
• Added: +120
• Removed: -34

🔗 Open commit — `a1b2c3d4`

🤖 GH AutoPost
```

## Quick start

### Prerequisites

- Docker & Docker Compose
- PostgreSQL instance (can be a shared one)
- GitHub Personal Access Token
- Telegram bot token from [@BotFather](https://t.me/BotFather)

### 1. Clone and configure

```bash
git clone https://github.com/your-username/gh-autopost.git
cd gh-autopost
cp .env.example .env
# Fill in all variables in .env
```

### 2. Prepare PostgreSQL

Create a database for the service:

```sql
CREATE DATABASE gh_autopost;
```

Then set `DATABASE_URL` in `.env`:

```
DATABASE_URL=postgresql://user:password@hostname:5432/gh_autopost
```

If PostgreSQL runs in Docker on the same host, make sure both containers share the same network (see [Docker network](#docker-network) below).

### 3. Init mode — first run only

Saves all existing commits to the database **without posting to Telegram**.  
Run this once so the channel isn't flooded with historical commits.

```bash
docker compose run --rm gh-autopost --save
```

### 4. Start

```bash
docker compose up -d
```

The service will poll GitHub every `POLL_INTERVAL` seconds and publish only new commits.

---

## Configuration

All settings are via environment variables. Copy `.env.example` to `.env` and fill in the values.

| Variable               | Description                                                         | Required      |
|------------------------|---------------------------------------------------------------------|---------------|
| `GITHUB_TOKEN`         | GitHub Personal Access Token (classic), scope: `repo`              | Yes           |
| `REPOS`                | Comma-separated repos: `owner/repo1,owner/repo2`                   | Yes           |
| `BRANCHES`             | Comma-separated branches to monitor                                 | No (main)     |
| `TELEGRAM_BOT_TOKEN`   | Bot token from @BotFather                                           | Yes           |
| `TELEGRAM_CHANNEL_ID`  | Channel/supergroup ID (e.g. `-1001234567890`)                       | Yes           |
| `TELEGRAM_TOPIC_ID`    | Topic (thread) ID inside the channel (`0` = no topic)              | No (0)        |
| `ADMIN_IDS`            | Comma-separated Telegram user IDs to notify after each publish     | No            |
| `DATABASE_URL`         | PostgreSQL DSN: `postgresql://user:pass@host:5432/dbname`           | Yes           |
| `POLL_INTERVAL`        | Poll interval in seconds                                            | No (30)       |
| `BATCH_THRESHOLD`      | Commit count that triggers batched message instead of individual   | No (3)        |
| `FILTER_MERGE_COMMITS` | Skip merge commits (`true`/`false`)                                 | No (true)     |
| `MAX_COMMITS_PER_RUN`  | Max commits fetched per repo/branch per run                         | No (100)      |
| `SIGNATURE`            | Text appended to every published message                            | No            |

---

## Docker network

If your PostgreSQL runs in another Docker Compose project, connect both containers to a shared external network.

**Create the network once:**

```bash
docker network create postgres_net
```

**Add your PostgreSQL container to it** (in its `docker-compose.yml`):

```yaml
networks:
  postgres_net:
    external: true
    name: postgres_net
```

**`gh-autopost` is already configured** to join `postgres_net` — see `docker-compose.yml`.

Then use the Postgres container name as the hostname in `DATABASE_URL`:

```
DATABASE_URL=postgresql://user:password@postgres:5432/gh_autopost
```

---

## How to get required values

**GitHub Token** — GitHub → Settings → Developer settings → Personal access tokens → Classic token, scope `repo`.

**Telegram Bot** — create via [@BotFather](https://t.me/BotFather), add to the channel as admin with permission to post messages.

**TELEGRAM_CHANNEL_ID** — forward a message from the channel to [@userinfobot](https://t.me/userinfobot), or use `getUpdates` via Bot API.

**TELEGRAM_TOPIC_ID** — open the topic in Telegram Web; the ID is visible in the URL.

**ADMIN_IDS** — get your Telegram user ID via [@userinfobot](https://t.me/userinfobot).

---

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python src/main.py --save    # init mode
python src/main.py           # normal mode
python src/main.py --debug   # verbose logging
```

Requires Python 3.12+.

## Project structure

```
gh-autopost/
├── src/
│   ├── main.py             # Entry point + polling loop
│   ├── config.py           # Config from environment variables
│   ├── storage.py          # PostgreSQL storage
│   ├── github_client.py    # GitHub API client
│   ├── formatter.py        # Telegram message formatting
│   ├── telegram_client.py  # Telegram Bot API client
│   └── processor.py        # Commit processing orchestration
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── .gitignore
```
