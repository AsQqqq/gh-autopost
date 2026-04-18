import logging
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._init_db()

    def _connect(self):
        return psycopg2.connect(self._dsn)

    def _init_db(self):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS commits (
                        id           SERIAL PRIMARY KEY,
                        repo         TEXT    NOT NULL,
                        branch       TEXT    NOT NULL,
                        sha          TEXT    NOT NULL,
                        processed_at TIMESTAMPTZ NOT NULL,
                        UNIQUE (repo, branch, sha)
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_commits_repo_branch_sha
                    ON commits (repo, branch, sha)
                """)
        logger.debug("Storage initialised (PostgreSQL)")

    def is_processed(self, repo: str, branch: str, sha: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM commits WHERE repo=%s AND branch=%s AND sha=%s",
                    (repo, branch, sha),
                )
                return cur.fetchone() is not None

    def save_commit(self, repo: str, branch: str, sha: str) -> bool:
        """Returns True if inserted, False if already existed."""
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO commits (repo, branch, sha, processed_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (repo, branch, sha) DO NOTHING
                        """,
                        (repo, branch, sha, datetime.now(timezone.utc)),
                    )
                    return cur.rowcount == 1
        except psycopg2.Error as exc:
            logger.error(f"DB error saving commit {sha[:8]}: {exc}")
            return False

    def get_processed_count(self, repo: str, branch: str) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM commits WHERE repo=%s AND branch=%s",
                    (repo, branch),
                )
                return cur.fetchone()[0]
