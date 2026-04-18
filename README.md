# gh-autopost

Monitors GitHub repositories for new commits and publishes them to a Telegram channel topic. Supports multiple repos, branches, batch publishing, merge filtering, and Conventional Commits classification.

## Features

- Monitors multiple repositories and branches simultaneously
- Posts to a specific topic (thread) in a Telegram supergroup/channel
- Notifies admins after each publish
- Deduplication via PostgreSQL — survives container restarts
- Batches multiple commits into chunks (configurable threshold)
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

---

## Quick start

### Prerequisites

- Docker & Docker Compose
- PostgreSQL instance (can be a shared one in another container)
- GitHub Personal Access Token
- Telegram bot token from [@BotFather](https://t.me/BotFather)

---

### 1. Clone and configure

```bash
git clone https://github.com/AsQqqq/gh-autopost.git
cd gh-autopost
cp .env.example .env
```

---

### 2. Prepare PostgreSQL

#### Create a database and dedicated user

Connect to your PostgreSQL container (replace `admin` with your superuser):

```bash
docker exec -it postgres psql -U admin -d postgres
```

Then run:

```sql
CREATE USER gh_autopost WITH PASSWORD 'your_strong_password';
CREATE DATABASE gh_autopost OWNER gh_autopost;
GRANT ALL PRIVILEGES ON DATABASE gh_autopost TO gh_autopost;
```

Then connect to the new database and grant schema access:

```bash
docker exec -it postgres psql -U admin -d gh_autopost -c "GRANT ALL ON SCHEMA public TO gh_autopost;"
```

#### Connect to the same Docker network

Find the network your PostgreSQL container is on:

```bash
docker inspect postgres --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}'
```

The `docker-compose.yml` is configured to join an external network. Update the network name if yours differs from `server_server-net`:

```yaml
networks:
  your_network_name:
    external: true
```

---

### 3. Fill in `.env`

```bash
nano .env
```

The minimum required variables:

```env
GITHUB_TOKEN=ghp_...
REPOS=owner/repo1,owner/repo2
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHANNEL_ID=-1001234567890
DATABASE_URL=postgresql://gh_autopost:your_strong_password@postgres:5432/gh_autopost
```

See [Configuration](#configuration) for the full list.

---

### 4. Build

```bash
docker compose build
```

---

### 5. Init mode — first run only

Saves all existing commits to the database **without posting to Telegram**.
Run this once so the channel isn't flooded with historical commits.

```bash
docker compose run --rm gh-autopost-init
```

---

### 6. Start

```bash
docker compose up -d
```

The service will poll GitHub every `POLL_INTERVAL` seconds and publish only new commits.

---

## Configuration

All settings via environment variables. Copy `.env.example` to `.env` and fill in the values.

| Variable               | Description                                                        | Required    |
|------------------------|--------------------------------------------------------------------|-------------|
| `GITHUB_TOKEN`         | GitHub Personal Access Token (classic), scope: `repo`             | Yes         |
| `REPOS`                | Comma-separated repos: `owner/repo1,owner/repo2`                  | Yes         |
| `BRANCHES`             | Comma-separated branches to monitor                                | No (main)   |
| `TELEGRAM_BOT_TOKEN`   | Bot token from @BotFather                                          | Yes         |
| `TELEGRAM_CHANNEL_ID`  | Channel/supergroup ID (e.g. `-1001234567890`)                      | Yes         |
| `TELEGRAM_TOPIC_ID`    | Topic (thread) ID inside the channel (`0` = no topic)             | No (0)      |
| `ADMIN_IDS`            | Comma-separated Telegram user IDs to notify after each publish    | No          |
| `DATABASE_URL`         | PostgreSQL DSN: `postgresql://user:pass@host:5432/dbname`          | Yes         |
| `POLL_INTERVAL`        | Poll interval in seconds                                           | No (30)     |
| `BATCH_THRESHOLD`      | Commit count that triggers batched message instead of individual  | No (3)      |
| `FILTER_MERGE_COMMITS` | Skip merge commits (`true`/`false`)                                | No (true)   |
| `MAX_COMMITS_PER_RUN`  | Max commits fetched per repo/branch per run                        | No (100)    |
| `SIGNATURE`            | Text appended to every published message                           | No          |

---

## How to get required values

**GitHub Token** — GitHub → Settings → Developer settings → Personal access tokens → Classic, scope `repo`.

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

Requires Python 3.12+. Requires a reachable PostgreSQL instance with `DATABASE_URL` set in `.env`.

---

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
