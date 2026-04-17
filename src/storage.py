import sqlite3
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo         TEXT    NOT NULL,
                    branch       TEXT    NOT NULL,
                    sha          TEXT    NOT NULL,
                    processed_at TEXT    NOT NULL,
                    UNIQUE(repo, branch, sha)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_repo_branch_sha ON commits(repo, branch, sha)")
        logger.debug(f"Storage initialised at {self.db_path}")

    def is_processed(self, repo: str, branch: str, sha: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT 1 FROM commits WHERE repo=? AND branch=? AND sha=?",
                (repo, branch, sha),
            )
            return cur.fetchone() is not None

    def save_commit(self, repo: str, branch: str, sha: str) -> bool:
        """Returns True if inserted, False if already existed."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO commits (repo, branch, sha, processed_at) VALUES (?, ?, ?, ?)",
                    (repo, branch, sha, datetime.now(timezone.utc).isoformat()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def get_processed_count(self, repo: str, branch: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM commits WHERE repo=? AND branch=?",
                (repo, branch),
            )
            return cur.fetchone()[0]
