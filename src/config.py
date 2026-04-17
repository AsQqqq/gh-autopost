import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        logger.error(f"Required env var {name!r} is not set")
        sys.exit(1)
    return value


def _list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logger.warning(f"Invalid int value for {name!r}, using default {default}")
        return default


def _bool(name: str, default: bool = True) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


class Config:
    def __init__(self):
        self.github_token: str = _require("GITHUB_TOKEN")
        self.telegram_bot_token: str = _require("TELEGRAM_BOT_TOKEN")
        self.telegram_channel_id: str = _require("TELEGRAM_CHANNEL_ID")
        self.telegram_topic_id: int = _int("TELEGRAM_TOPIC_ID", 0)
        self.repos: list[str] = _list("REPOS")
        self.branches: list[str] = _list("BRANCHES", "main")
        self.admin_ids: list[int] = [int(x) for x in _list("ADMIN_IDS")]
        self.db_path: str = os.getenv("DB_PATH", "./data/commits.db")
        self.poll_interval: int = _int("POLL_INTERVAL", 30)
        self.signature: str = os.getenv("SIGNATURE", "🤖 GH AutoPost")
        self.filter_merge_commits: bool = _bool("FILTER_MERGE_COMMITS", True)
        self.batch_threshold: int = _int("BATCH_THRESHOLD", 3)
        self.max_commits_per_run: int = _int("MAX_COMMITS_PER_RUN", 100)

        if not self.repos:
            logger.error("REPOS is not set — provide at least one repo as 'owner/repo'")
            sys.exit(1)


config = Config()
