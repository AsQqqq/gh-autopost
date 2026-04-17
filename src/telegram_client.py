import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(
        self,
        token: str,
        channel_id: str,
        topic_id: int,
        max_retries: int = 5,
    ):
        self._base = f"https://api.telegram.org/bot{token}"
        self.channel_id = channel_id
        self.topic_id = topic_id
        self.max_retries = max_retries

    # ------------------------------------------------------------------ #
    #  Core sender                                                         #
    # ------------------------------------------------------------------ #

    def _send_message(
        self,
        chat_id: str | int,
        text: str,
        thread_id: Optional[int] = None,
        parse_mode: str = "Markdown",
    ) -> bool:
        payload: dict = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if thread_id:
            payload["message_thread_id"] = thread_id

        url = f"{self._base}/sendMessage"

        for attempt in range(self.max_retries):
            try:
                resp = requests.post(url, json=payload, timeout=30)
            except requests.RequestException as exc:
                logger.error(f"Telegram network error [{attempt+1}/{self.max_retries}]: {exc}")
                time.sleep(5 * (attempt + 1))
                continue

            if resp.status_code == 429:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 10)
                logger.warning(f"Telegram flood control — waiting {retry_after}s")
                time.sleep(retry_after)
                continue

            if not resp.ok:
                logger.error(
                    f"Telegram error [{attempt+1}/{self.max_retries}] "
                    f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
                time.sleep(5 * (attempt + 1))
                continue

            return True

        logger.error(f"Failed to send Telegram message after {self.max_retries} attempts")
        return False

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def publish_commit(self, text: str) -> bool:
        """Post to the configured channel + topic."""
        return self._send_message(self.channel_id, text, thread_id=self.topic_id or None)

    def notify_admin(self, admin_id: int, text: str) -> bool:
        return self._send_message(admin_id, text)

    def notify_admins(self, admin_ids: list[int], text: str):
        for admin_id in admin_ids:
            self.notify_admin(admin_id, text)
