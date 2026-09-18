import os
from azure.communication.email import EmailClient
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.connection_string = os.getenv("ACS_CONNECTION_STRING")
        self.sender_address = os.getenv("ACS_SENDER_ADDRESS")
        self.client = EmailClient.from_connection_string(self.connection_string)

    def send_approval_email(self, recipient: str, subject: str, body: str):
        message = {
            "content": {
                "subject": subject,
                "html": body,
            },
            "recipients": {
                "to": [{"address": recipient}],
            },
            "senderAddress": self.sender_address
        }

        try:
            poller = self.client.begin_send(message)
            result = poller.result()
            return result
        except Exception as e:
            raise Exception(f"ACS Email Error: {str(e)}")

    def send_approval_notification(self, subject: str, body: str, custom_recipient: str = None):
        """Asynchronous notification wrapper"""
        recipient = custom_recipient or os.getenv("APPROVAL_RECIPIENT", "Raghavendra.Lakkamaraju@valuemomentum.com")
        try:
            self.send_approval_email(recipient, subject, body)
        except Exception as e:
            print(f"WARN: Failed to send email: {e}")

email_service = EmailService()
