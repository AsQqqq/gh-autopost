import logging

from github_client import GitHubClient
from storage import Storage
from telegram_client import TelegramClient
import formatter
from config import Config

logger = logging.getLogger(__name__)


class CommitProcessor:
    def __init__(
        self,
        github: GitHubClient,
        storage: Storage,
        telegram: TelegramClient,
        cfg: Config,
    ):
        self.github = github
        self.storage = storage
        self.telegram = telegram
        self.cfg = cfg

    # ------------------------------------------------------------------ #

    def _find_new_commits(self, repo: str, branch: str) -> list[dict]:
        commits = self.github.get_commits(repo, branch, per_page=self.cfg.max_commits_per_run)
        new = [c for c in commits if not self.storage.is_processed(repo, branch, c["sha"])]
        return new

    def _filter_merge(self, commits: list[dict]) -> list[dict]:
        filtered = []
        for c in commits:
            msg = c.get("commit", {}).get("message", "")
            if formatter.is_merge_commit(msg):
                logger.debug(f"Skipping merge commit {c['sha'][:8]}")
            else:
                filtered.append(c)
        return filtered

    # ------------------------------------------------------------------ #

    def process_repo(self, repo: str, branch: str, save_only: bool = False):
        logger.info(f"Checking {repo}/{branch}")
        new_commits = self._find_new_commits(repo, branch)

        if not new_commits:
            logger.info(f"  No new commits for {repo}/{branch}")
            return

        logger.info(f"  Found {len(new_commits)} new commit(s) for {repo}/{branch}")

        if save_only:
            # Init mode: just persist, no Telegram
            for c in new_commits:
                self.storage.save_commit(repo, branch, c["sha"])
            logger.info(f"  Saved {len(new_commits)} commits (init mode)")
            return

        # Filter merge commits if configured
        if self.cfg.filter_merge_commits:
            before = len(new_commits)
            new_commits = self._filter_merge(new_commits)
            skipped = before - len(new_commits)
            if skipped:
                logger.info(f"  Filtered {skipped} merge commit(s)")

        if not new_commits:
            return

        # Publish oldest first
        new_commits = list(reversed(new_commits))

        if len(new_commits) >= self.cfg.batch_threshold:
            self._publish_batch(repo, branch, new_commits)
        else:
            for c in new_commits:
                self._publish_single(repo, branch, c["sha"])

    def _publish_single(self, repo: str, branch: str, sha: str):
        if self.storage.is_processed(repo, branch, sha):
            return  # guard against race

        detail = self.github.get_commit_detail(repo, sha)
        if detail is None:
            logger.error(f"  Could not fetch details for {sha[:8]}, skipping")
            return

        text = formatter.format_commit_message(repo, branch, detail, self.cfg.signature)
        ok = self.telegram.publish_commit(text)

        if ok:
            self.storage.save_commit(repo, branch, sha)
            author = detail.get("commit", {}).get("author", {}).get("name", "?")
            notif = formatter.format_admin_notification(repo, branch, author, sha)
            self.telegram.notify_admins(self.cfg.admin_ids, notif)
            logger.info(f"  Published {sha[:8]}")
        else:
            logger.error(f"  Failed to publish {sha[:8]}, will retry next run")

    def _publish_batch(self, repo: str, branch: str, commits: list[dict]):
        text = formatter.format_batch_message(repo, branch, commits, self.cfg.signature)
        ok = self.telegram.publish_commit(text)

        if ok:
            for c in commits:
                self.storage.save_commit(repo, branch, c["sha"])

            authors = {c.get("commit", {}).get("author", {}).get("name", "?") for c in commits}
            first_sha = commits[0]["sha"]
            notif = formatter.format_admin_notification(
                repo, branch,
                f"batch {len(commits)} commits ({', '.join(sorted(authors))})",
                first_sha,
            )
            self.telegram.notify_admins(self.cfg.admin_ids, notif)
            logger.info(f"  Published batch of {len(commits)} commits")
        else:
            logger.error("  Failed to publish batch, will retry next run")

    # ------------------------------------------------------------------ #

    def run(self, save_only: bool = False):
        for repo in self.cfg.repos:
            for branch in self.cfg.branches:
                try:
                    self.process_repo(repo, branch, save_only=save_only)
                except Exception as exc:
                    logger.error(
                        f"Unhandled error processing {repo}/{branch}: {exc}",
                        exc_info=True,
                    )
