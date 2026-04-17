#!/usr/bin/env python3
"""
GH AutoPost — tracks new commits in private GitHub repos
and publishes them to a Telegram channel topic.

Usage:
  python main.py          # Normal mode: poll & publish
  python main.py --save   # Init mode: save existing commits WITHOUT posting
"""

import argparse
import logging
import sys
import time

# ------------------------------------------------------------------ #
#  Logging setup (before importing config so errors are visible)      #
# ------------------------------------------------------------------ #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("gh_autopost")


def main():
    parser = argparse.ArgumentParser(description="GitHub → Telegram AutoPost")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Init mode: record existing commits without posting to Telegram",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Late imports so logging is configured first
    from config import config
    from storage import Storage
    from github_client import GitHubClient
    from telegram_client import TelegramClient
    from processor import CommitProcessor

    storage = Storage(config.db_path)
    github = GitHubClient(config.github_token)
    telegram = TelegramClient(
        config.telegram_bot_token,
        config.telegram_channel_id,
        config.telegram_topic_id,
    )
    processor = CommitProcessor(github, storage, telegram, config)

    # ---------------------------------------------------------------- #
    #  Init mode                                                         #
    # ---------------------------------------------------------------- #
    if args.save:
        logger.info("=== INIT MODE (--save): recording existing commits, no Telegram posts ===")
        processor.run(save_only=True)
        logger.info("Init complete. Run without --save to start normal operation.")
        return

    # ---------------------------------------------------------------- #
    #  Normal polling loop                                               #
    # ---------------------------------------------------------------- #
    logger.info(
        f"=== Starting GH AutoPost ===\n"
        f"  Repos   : {config.repos}\n"
        f"  Branches: {config.branches}\n"
        f"  Interval: {config.poll_interval}s\n"
        f"  DB      : {config.db_path}"
    )

    while True:
        try:
            processor.run(save_only=False)
        except KeyboardInterrupt:
            logger.info("Interrupted by user, shutting down.")
            break
        except Exception as exc:
            logger.error(f"Unexpected error in main loop: {exc}", exc_info=True)

        logger.debug(f"Sleeping {config.poll_interval}s until next poll…")
        time.sleep(config.poll_interval)


if __name__ == "__main__":
    main()
