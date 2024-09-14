import asyncio
import aiosmtplib
import aioimaplib
import email
from email.message import EmailMessage
from typing import List, Optional
import logging
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from contextlib import asynccontextmanager
import imaplib
from email.mime.text import MIMEText


# Initialisiere das Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class EmailBot:
    """
    EmailBot bietet asynchrone Funktionen zum Senden, Empfangen und Verwalten von E-Mails über SMTP und IMAP.
    """

    def __init__(self, smtp_server: str, smtp_port: int, imap_server: str, imap_port: int,
                 email_address: str, password: str):
        """
        Initialisiert den EmailBot mit den Serverinformationen und Benutzerdaten.
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.email_address = email_address
        self.password = password

    @asynccontextmanager
    async def _smtp_connection(self):
        """
            Asynchroner Kontextmanager für die SMTP-Verbindung.
        """
        server = None
        try:
                server = aiosmtplib.SMTP(hostname=self.smtp_server, port=self.smtp_port, start_tls=True)
                await server.connect()
                # Entfernen Sie den folgenden Aufruf, da TLS bereits gestartet wurde
                # await server.starttls()
                await server.login(self.email_address, self.password)
                logging.info("Erfolgreich mit dem SMTP-Server verbunden.")
                yield server
        except Exception as e:
                logging.error(f"Fehler beim Verbinden mit dem SMTP-Server: {e}")
                # Kein yield hier!
        finally:
                if server:
                    await server.quit()



    @asynccontextmanager
    async def _imap_connection(self):
        """
        Asynchroner Kontextmanager für die IMAP-Verbindung.
        """
        try:
            mail = aioimaplib.IMAP4_SSL(host=self.imap_server, port=self.imap_port)
            await mail.wait_hello_from_server()
            login_response = await mail.login(self.email_address, self.password)
            if login_response.result != 'OK':
                logging.error(f"Fehler beim Anmelden am IMAP-Server: {login_response.result}")
                yield None
            else:
                logging.info("Erfolgreich mit dem IMAP-Server verbunden.")
                yield mail
                await mail.logout()
        except Exception as e:
            logging.error(f"Fehler beim Verbinden mit dem IMAP-Server: {e}")
            yield None

    async def send_email(self, recipient: str, subject: str, body: str,
                         cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None):
        """
        Sendet eine einfache E-Mail asynchron.
        """
        async with self._smtp_connection() as server:
            if server is None:
                return
            msg = EmailMessage()
            msg["From"] = self.email_address
            msg["To"] = recipient
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ', '.join(cc)
            if bcc:
                msg["Bcc"] = ', '.join(bcc)
            msg.set_content(body)
            try:
                await server.send_message(msg)
                logging.info(f"E-Mail an {recipient} gesendet.")
            except Exception as e:
                logging.error(f"Fehler beim Senden der E-Mail: {e}")

    async def fetch_emails(self, folder: str = "INBOX", search_criteria: str = 'ALL',
                           save_attachments: bool = True, attachment_dir: str = "./attachments") -> List[dict]:
        return await asyncio.to_thread(self._fetch_emails_sync, folder, search_criteria, save_attachments, attachment_dir)

    def _fetch_emails_sync(self, folder, search_criteria, save_attachments, attachment_dir):
        emails_with_details = []
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            result, data = mail.select(folder)
            if result != 'OK':
                logging.error(f"Fehler beim Auswählen des Ordners {folder}: {data}")
                return []
            result, data = mail.search(None, search_criteria)
            if result != 'OK':
                logging.error(f"Fehler beim Durchsuchen der E-Mails im Ordner {folder}: {data}")
                return []
            for num in data[0].split():
                result, msg_data = mail.fetch(num, '(RFC822)')
                if result != 'OK':
                    logging.error(f"Fehler beim Abrufen der Nachricht {num}")
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                email_info = self._parse_email(msg, save_attachments, attachment_dir)
                emails_with_details.append(email_info)
            mail.logout()
            logging.info(f"{len(emails_with_details)} E-Mails aus dem Ordner {folder} geholt.")
            return emails_with_details
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der E-Mails: {e}")
            return []


    def _parse_email(self, msg, save_attachments, attachment_dir):
        """
        Parst die E-Mail und extrahiert die Informationen sowie Anhänge.
        """
        email_info = {
            "subject": msg.get("Subject", ""),
            "from": msg.get("From", ""),
            "to": msg.get("To", ""),
            "date": msg.get("Date", ""),
            "text": "",
            "attachments": []
        }
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = part.get_content_disposition()
            if content_disposition is None:
                if content_type == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    email_info["text"] += part.get_payload(decode=True).decode(charset, errors='replace')
            elif save_attachments and content_disposition == 'attachment':
                filename = part.get_filename()
                if filename:
                    if not os.path.exists(attachment_dir):
                        os.makedirs(attachment_dir)
                    filepath = os.path.join(attachment_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    email_info["attachments"].append(filepath)
                    logging.info(f"Anhang {filename} gespeichert.")
        return email_info

    async def list_folders(self) -> List[str]:
        """
        Listet alle Ordner des IMAP-Postfachs asynchron auf.
        """
        async with self._imap_connection() as mail:
            if mail is None:
                return []
            try:
                list_response = await mail.list('""', '*')
                if list_response.result == 'OK':
                    folders = []
                    for line in list_response.lines:
                        parts = line.decode().split(' "/" ')
                        if len(parts) == 2:
                            folder_name = parts[1].strip('"')
                            folders.append(folder_name)
                    logging.info("Ordner erfolgreich aufgelistet.")
                    return folders
                else:
                    logging.error("Fehler beim Auflisten der Ordner.")
                    return []
            except Exception as e:
                logging.error(f"Fehler beim Abrufen der Ordnerliste: {e}")
                return []

    async def move_email_to_folder(self, email_id: str, target_folder: str):
        """
        Verschiebt eine E-Mail in einen anderen Ordner asynchron.
        """
        async with self._imap_connection() as mail:
            if mail is None:
                return
            try:
                await mail.select("Inbox")
                copy_response = await mail.copy(email_id, target_folder)
                if copy_response.result == 'OK':
                    await mail.store(email_id, '+FLAGS', '\\Deleted')
                    await mail.expunge()
                    logging.info(f"E-Mail {email_id} erfolgreich nach {target_folder} verschoben.")
                else:
                    logging.error(f"Fehler beim Kopieren der E-Mail {email_id} nach {target_folder}.")
            except Exception as e:
                logging.error(f"Fehler beim Verschieben der E-Mail {email_id}: {e}")

    async def reply_to_email(self, original_email: email.message.EmailMessage, reply_body: str):
        """
        Antwortet auf eine empfangene E-Mail asynchron.
        """
        async with self._smtp_connection() as server:
            if server is None:
                return
            reply = EmailMessage()
            reply["From"] = self.email_address
            reply["To"] = original_email.get("Reply-To", original_email.get("From"))
            reply["Subject"] = "Re: " + original_email.get("Subject", "")
            reply["In-Reply-To"] = original_email.get("Message-ID", "")
            reply["References"] = original_email.get("References", "") + " " + original_email.get("Message-ID", "")
            reply.set_content(reply_body)
            try:
                await server.send_message(reply)
                logging.info(f"Antwort an {reply['To']} gesendet.")
            except Exception as e:
                logging.error(f"Fehler beim Antworten auf die E-Mail: {e}")

    async def get_conversation_with_contact(self, contact_email: str, folder: str = "INBOX") -> List[dict]:
        """
        Holt den E-Mail-Verlauf mit einer bestimmten Kontakt-E-Mail-Adresse asynchron.
        """
        search_criteria = f'(OR FROM "{contact_email}" TO "{contact_email}")'
        return await self.fetch_emails(folder=folder, search_criteria=search_criteria, save_attachments=False)

    async def send_email_with_attachment(self, recipient: str, subject: str, body: str,
                                         attachments: Optional[List[str]] = None,
                                         cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None):
        """
        Sendet eine E-Mail mit Anhängen asynchron.
        """
        async with self._smtp_connection() as server:
            if server is None:
                return
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = recipient
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ', '.join(cc)
            if bcc:
                msg["Bcc"] = ', '.join(bcc)
            # Verwenden Sie MIMEText direkt
            msg.attach(MIMEText(body, "plain"))
            if attachments:
                for file_path in attachments:
                    if os.path.isfile(file_path):
                        with open(file_path, "rb") as file:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(file.read())
                            encoders.encode_base64(part)
                            part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(file_path)}"')
                            msg.attach(part)
                    else:
                        logging.warning(f"Anhang '{file_path}' existiert nicht.")
            try:
                await server.send_message(msg)
                logging.info(f"E-Mail mit Anhang an {recipient} gesendet.")
            except Exception as e:
                logging.error(f"Fehler beim Senden der E-Mail mit Anhang: {e}")