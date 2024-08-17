import smtplib
import imaplib
import email as email_lib
from email.message import EmailMessage, Message
from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional
import re
import logging
from dotenv import load_dotenv
import os

class EmailSettings(BaseModel):
    email_address: EmailStr
    password: str
    smtp_server: str
    imap_server: str

    @field_validator('password')
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value


class EmailContent(BaseModel):
    uid: str
    subject: Optional[str] = "No Subject"
    sender: EmailStr
    content: str


class EmailClient:
    def __init__(self, settings: EmailSettings):
        self.settings = settings
        self.imap_connection = None

    @staticmethod
    def get_email_servers(email_address: str) -> dict:
        domain = email_address.split('@')[-1]
        servers = {
            'gmail.com': ('smtp.gmail.com', 'imap.gmail.com'),
            'yahoo.com': ('smtp.mail.yahoo.com', 'imap.mail.yahoo.com'),
            'outlook.com': ('smtp-mail.outlook.com', 'outlook.office365.com'),
            'outlook.de': ('smtp-mail.outlook.com', 'outlook.office365.com'),
            'hotmail.com': ('smtp-mail.outlook.com', 'outlook.office365.com')
        }
        if domain not in servers:
            raise ValueError(f"Unsupported email provider for domain: {domain}")
        return {'smtp_server': servers[domain][0], 'imap_server': servers[domain][1]}

    def _connect_imap(self):
        if not self.imap_connection:
            self.imap_connection = imaplib.IMAP4_SSL(self.settings.imap_server)
            self.imap_connection.login(self.settings.email_address, self.settings.password)

    def _disconnect_imap(self):
        if self.imap_connection:
            try:
                self.imap_connection.logout()
            except imaplib.IMAP4.abort:
                logging.warning("IMAP connection was already closed.")
            finally:
                self.imap_connection = None

    def _fetch_emails(self, criteria: str, folder: str = 'inbox') -> List[EmailContent]:
        self._connect_imap()
        self.imap_connection.select(folder)

        status, data = self.imap_connection.search(None, criteria)
        if status != 'OK':
            logging.error("Failed to search emails.")
            return []

        mail_ids = data[0].split()
        emails = []

        for i in mail_ids:
            status, data = self.imap_connection.fetch(i, '(UID RFC822)')
            if status != 'OK':
                logging.error(f"Failed to fetch email with ID {i.decode()}.")
                continue

            for response_part in data:
                if isinstance(response_part, tuple):
                    uid_match = re.search(r'UID (\d+)', response_part[0].decode())
                    if not uid_match:
                        logging.warning(f"Could not extract UID for email ID {i.decode()}. Skipping this email.")
                        continue

                    uid = uid_match.group(1)
                    msg = email_lib.message_from_bytes(response_part[1])
                    mail_from = msg['from']
                    mail_subject = msg['subject']
                    mail_content = self.decode_email_content(msg)

                    email = EmailContent(
                        uid=uid,
                        sender=mail_from,
                        subject=mail_subject,
                        content=mail_content
                    )
                    emails.append(email)

        return emails


    def send_email(self, recipient: EmailStr, subject: str, body: str):
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.settings.email_address
        msg['To'] = recipient
        msg.set_content(body)

        with smtplib.SMTP(self.settings.smtp_server, 587) as smtp:
            smtp.starttls()
            smtp.login(self.settings.email_address, self.settings.password)
            smtp.send_message(msg)
        print("Email sent successfully.")

    def decode_email_content(self, msg: Message) -> str:
        mail_content = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        charset = part.get_content_charset() or "utf-8"
                        mail_content += part.get_payload(decode=True).decode(charset, errors="replace")
                    except Exception:
                        mail_content += "[Error decoding content]"
        else:
            try:
                charset = msg.get_content_charset() or "utf-8"
                mail_content = msg.get_payload(decode=True).decode(charset, errors="replace")
            except Exception:
                mail_content = "[Error decoding content]"

        return mail_content

    def receive_emails(self) -> List[EmailContent]:
        return self._fetch_emails(criteria='ALL')

    def get_email_history(self, contact: EmailStr, folder: str = 'inbox') -> List[EmailContent]:
        criteria = f'(OR FROM "{contact}" TO "{contact}")'
        return self._fetch_emails(criteria=criteria, folder=folder)

    def move_email(self, uid: str, destination_folder: str, source_folder: str = 'inbox'):
        self._connect_imap()
        self.imap_connection.select(source_folder)

        result = self.imap_connection.uid('COPY', uid, destination_folder)
        if result[0] == 'OK':
            self.imap_connection.uid('STORE', uid, '+FLAGS', '(\Deleted)')
            self.imap_connection.expunge()
            print(f"Email {uid} moved to {destination_folder} successfully.")
        else:
            print(f"Failed to move email {uid} to {destination_folder}.")

    def __del__(self):
        self._disconnect_imap()


# Example usage:
if __name__ == "__main__":
    load_dotenv()
    email_address = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    
    servers = EmailClient.get_email_servers(email_address)
    settings = EmailSettings(email_address=email_address, password=password, smtp_server=servers['smtp_server'], imap_server=servers['imap_server'])

    client = EmailClient(settings)
    
    # Beispiel zum Senden einer E-Mail
    #client.send_email("d.trebis@outlook.de", "Test Subject", "This is a test email sent from Python.")
    
    # Beispiel zum Empfangen von E-Mails
    emails = client.receive_emails()
    for email in emails:
        print(f"UID='{email.uid}' sender='{email.sender}' subject='{email.subject}'  content='{email.content}'")
    
    # Beispiel zum Abrufen des E-Mail-Verlaufs
    history = client.get_email_history("d.trebis@outlook.de", folder='Inbox')
    for email in history:
        print(f"UID='{email.uid}' sender='{email.sender}' subject='{email.subject}'  content='{email.content}'")
    
    # Beispiel zum Verschieben einer E-Mail
    if emails:
        first_email_uid = emails[0].uid
        client.move_email(first_email_uid, destination_folder='Archiv')
