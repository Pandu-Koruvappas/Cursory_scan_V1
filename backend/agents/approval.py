import os
from services.email_service import EmailService

class ApprovalAgent:
    def __init__(self):
        self.email = EmailService()
        self.recipient = os.getenv("APPROVAL_RECIPIENT")

    def prepare_approval_package(self, trd: str, backlog: dict):
        """
        Prepares and sends the approval email.
        """
        subject = "Action Required: BA Agent Pro Approval Package"
        body = f"""
        Hello,
        
        The BA Agent Pro has generated a new Technical Requirements Document and Backlog.
        
        TRD Summary:
        {trd[:500]}...
        
        Please review and approve the synchronization to Azure DevOps.
        
        Regards,
        BA Agent Pro
        """
        
        try:
            self.email.send_approval_email(self.recipient, subject, body)
            return {
                "status": "Email Sent",
                "recipient": self.recipient,
                "email_subject": subject,
                "email_body": body
            }
        except Exception as e:
            return { "status": "Failed to send email", "error": str(e) }
        
