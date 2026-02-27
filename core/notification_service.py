import logging
import datetime

from services.telegram import TelegramService

logger = logging.getLogger("DeepVision.Notifications")


class NotificationService:
    """
    Singleton notification dispatcher.
    Routes alerts to the supervisor via Telegram (photo + text).
    Falls back to text-only if no evidence image is available.
    Always logs to the Python logger regardless of Telegram status.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
        return cls._instance

    def send_alert(
        self,
        level: str,
        type_str: str,
        message: str,
        evidence_path: str = None,
    ) -> bool:
        """
        Sends an alert to the supervisor.

        Parameters
        ----------
        level        : "WARNING", "ALARM" or "CRITICAL"
        type_str     : Short event label, e.g. "CELULAR", "ABANDONO"
        message      : Human-readable description
        evidence_path: Optional path to a JPEG screenshot
        """
        from config.settings import Settings
        settings = Settings()

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{timestamp}] [{level}] {type_str}: {message}")

        # Read credentials fresh every call so ConfigDialog changes take effect
        # without restarting the application.
        telegram = TelegramService(
            token=getattr(settings, "telegram_token", ""),
            chat_id=getattr(settings, "telegram_chat_id", ""),
        )

        if not telegram.is_configured():
            logger.debug("Telegram not configured — notification skipped.")
            return False

        # Build HTML caption
        level_emoji = {
            "CRITICAL": "🚨",
            "ALARM": "⚠️",
            "WARNING": "🟡",
        }.get(level, "ℹ️")

        caption = (
            f"{level_emoji} <b>DeepVision — {level}</b>\n"
            f"<b>Evento:</b> {type_str}\n"
            f"<b>Detalle:</b> {message}\n"
            f"<i>{timestamp}</i>"
        )

        if evidence_path:
            return telegram.send_photo(evidence_path, caption)
        else:
            return telegram.send_message(caption)
