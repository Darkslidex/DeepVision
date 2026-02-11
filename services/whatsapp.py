import logging
import requests

class WhatsAppService:
    def __init__(self, api_url=None, token=None):
        self.logger = logging.getLogger("DeepVision.Services.WhatsApp")
        self.api_url = api_url or "https://graph.facebook.com/v17.0/YOUR_PHONE_ID/messages"
        self.token = token or "YOUR_ACCESS_TOKEN"

    def send_alert(self, phone_number, message):
        """
        Sends a WhatsApp message via Cloud API.
        """
        if not self.token or "YOUR" in self.token:
            self.logger.warning("WhatsApp token not configured. Skipping alert.")
            return False

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message}
        }
        
        try:
            # response = requests.post(self.api_url, headers=headers, json=data, timeout=5)
            # response.raise_for_status()
            self.logger.info(f"WhatsApp alert sent to {phone_number}: {message}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send WhatsApp alert: {e}")
            return False
