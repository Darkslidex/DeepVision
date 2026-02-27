"""
Telegram Bot notification service for DeepVision.

Setup (one-time, ~5 minutes):
  1. Open Telegram, search @BotFather → /newbot → copy the token.
  2. Send a message to your bot, then open:
       https://api.telegram.org/bot<TOKEN>/getUpdates
     Copy the "id" field inside "chat" → that is your CHAT_ID.
  3. Paste both values in the DeepVision Config → Telegram section.
"""

import logging
import os
import requests

logger = logging.getLogger("DeepVision.Telegram")


class TelegramService:
    """
    Thin wrapper around the Telegram Bot API.
    Sends text messages and photos to a single chat / supervisor.
    """

    def __init__(self, token: str = "", chat_id: str = ""):
        self.token = token
        self.chat_id = chat_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _base_url(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    def is_configured(self) -> bool:
        """Returns True only when both token and chat_id look valid."""
        return bool(
            self.token
            and self.chat_id
            and len(self.token) > 20          # real tokens are ~46 chars
            and "YOUR" not in self.token.upper()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_message(self, text: str) -> bool:
        """Sends a plain-text (HTML) message to the configured chat."""
        if not self.is_configured():
            logger.warning("Telegram not configured — skipping sendMessage.")
            return False
        try:
            resp = requests.post(
                f"{self._base_url}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=6,
            )
            resp.raise_for_status()
            logger.info("Telegram message sent.")
            return True
        except Exception as exc:
            logger.error(f"Telegram sendMessage failed: {exc}")
            return False

    def send_photo(self, image_path: str, caption: str = "") -> bool:
        """Sends a JPEG image with an optional HTML caption."""
        if not self.is_configured():
            logger.warning("Telegram not configured — skipping sendPhoto.")
            return False
        if not os.path.exists(image_path):
            logger.warning(f"Evidence file not found: {image_path}")
            return self.send_message(caption)  # fallback to text
        try:
            with open(image_path, "rb") as photo_file:
                resp = requests.post(
                    f"{self._base_url}/sendPhoto",
                    data={"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"},
                    files={"photo": photo_file},
                    timeout=15,
                )
            resp.raise_for_status()
            logger.info("Telegram photo sent.")
            return True
        except Exception as exc:
            logger.error(f"Telegram sendPhoto failed: {exc}")
            # Try to at least send the text so the supervisor is notified
            return self.send_message(caption)

    def send_test_message(self) -> bool:
        """Sends a connectivity test message. Used from ConfigDialog."""
        return self.send_message(
            "✅ <b>DeepVision — Conexión exitosa</b>\n"
            "Las notificaciones de alerta llegarán a este chat."
        )
