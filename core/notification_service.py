import logging
import datetime

# Configure a specific logger for notifications
logger = logging.getLogger("NotificationService")
logger.setLevel(logging.INFO)

class NotificationService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
        return cls._instance

    def send_alert(self, level, type, message):
        """
        Sends an alert to external systems (Telegram, Email, etc.).
        For now, this is a mock that logs to console.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] [NOTIFICATION] [{level}] {type}: {message}"
        
        # 1. Log to console/file
        print(f"📡 SENDING NOTIFICATION: {formatted_msg}")
        logger.info(formatted_msg)
        
        # 2. TODO: Implement actual Telegram/Email API integration here
        # if self.telegram_enabled:
        #     self.send_telegram(formatted_msg)
            
        return True
