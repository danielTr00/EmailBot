import smtplib
import imaplib
import email
from email.message import EmailMessage
from typing import List, Optional
import logging
import os
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
import time

# Initialisiere Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class EmailBot:
    """
    EmailBot ermöglicht das Senden und Empfangen von E-Mails über verschiedene E-Mail-Anbieter,
    die SMTP und IMAP unterstützen. Es können E-Mails gesendet, empfangen und verwaltet werden.
    """

    def __init__(self, smtp_server: str, smtp_port: int, imap_server: str, imap_port: int, 
                 email_address: str, password: str):
        """
        Initialisiert den EmailBot mit den SMTP- und IMAP-Serverinformationen sowie den
        Zugangsdaten des Benutzers.
        
        :param smtp_server: SMTP-Server-Adresse des Anbieters
        :param smtp_port: SMTP-Port des Anbieters
        :param imap_server: IMAP-Server-Adresse des Anbieters
        :param imap_port: IMAP-Port des Anbieters
        :param email_address: Die E-Mail-Adresse des Benutzers
        :param password: Das Passwort des E-Mail-Kontos (oder ein App-spezifisches Passwort)
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.email_address = email_address
        self.password = password

    def _connect_smtp(self, retries=20, delay=1):
        """
        Stellt eine Verbindung zum SMTP-Server her und gibt die Serverinstanz zurück.
        Es wird eine Retry-Logik verwendet, um die Verbindung stabiler zu machen.
        :param retries: Anzahl der Versuche, eine Verbindung herzustellen
        :param delay: Wartezeit in Sekunden zwischen den Versuchen
        :return: SMTP-Verbindung oder None bei Fehler
        """
        for attempt in range(retries):
            try:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
                server.login(self.email_address, self.password)
                logging.info("Erfolgreich mit dem SMTP-Server verbunden.")
                return server
            except Exception as e:
                logging.error(f"Fehler beim Verbinden mit dem SMTP-Server: {e}")
                if attempt < retries - 1:
                    logging.info(f"Erneuter Verbindungsversuch in {delay} Sekunden...")
                    time.sleep(delay)
                else:
                    logging.error("Maximale Anzahl der Verbindungsversuche erreicht.")
        return None

    def _connect_imap(self, retries=20, delay=1):
        """
        Stellt eine Verbindung zum IMAP-Server her und gibt die Mailbox-Instanz zurück.
        Es wird eine Retry-Logik verwendet, um die Verbindung stabiler zu machen.
        :param retries: Anzahl der Versuche, eine Verbindung herzustellen
        :param delay: Wartezeit in Sekunden zwischen den Versuchen
        :return: IMAP-Verbindung oder None bei Fehler
        """
        for attempt in range(retries):
            try:
                mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
                mail.login(self.email_address, self.password)
                logging.info("Erfolgreich mit dem IMAP-Server verbunden.")
                return mail
            except Exception as e:
                logging.error(f"Fehler beim Verbinden mit dem IMAP-Server: {e}")
                if attempt < retries - 1:
                    logging.info(f"Erneuter Verbindungsversuch in {delay} Sekunden...")
                    time.sleep(delay)
                else:
                    logging.error("Maximale Anzahl der Verbindungsversuche erreicht.")
        return None

    def send_email(self, recipient: str, subject: str, body: str, cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None):
        """
        Sendet eine E-Mail an einen oder mehrere Empfänger.
        
        :param recipient: E-Mail-Adresse des Empfängers
        :param subject: Betreff der E-Mail
        :param body: Textinhalt der E-Mail
        :param cc: Optional: Liste von CC-Empfängern
        :param bcc: Optional: Liste von BCC-Empfängern
        """
        server = self._connect_smtp()
        if not server:
            return
        
        try:
            # Erstellen der E-Mail-Nachricht
            msg = EmailMessage()
            msg["From"] = self.email_address
            msg["To"] = recipient
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ', '.join(cc)
            if bcc:
                msg["Bcc"] = ', '.join(bcc)
            msg.set_content(body)
            
            # E-Mail senden
            server.send_message(msg)
            logging.info(f"E-Mail an {recipient} gesendet.")
        except Exception as e:
            logging.error(f"Fehler beim Senden der E-Mail: {e}")
        finally:
            server.quit()

    def fetch_emails(self, folder: str = "inbox", search_criteria: str = 'ALL', save_attachments: bool = True, attachment_dir: str = "./attachments") -> List[dict]:
        """
        Holt E-Mails aus einem bestimmten Ordner, speichert Anhänge und gibt Infos aus.
        
        :param folder: Der IMAP-Ordner
        :param search_criteria: Suchkriterien für die E-Mails
        :param save_attachments: Ob Anhänge gespeichert werden sollen
        :param attachment_dir: Ordner zum Speichern der Anhänge
        :return: Liste von E-Mails mit UID, Betreff, Empfangsdatum, Text und Anhangsnamen
        """
        mail = self._connect_imap()
        if not mail:
            return []

        emails_with_details = []
        try:
            mail.select(folder)
            result, data = mail.uid('search', None, search_criteria)
            if result != "OK":
                logging.error(f"Fehler beim Durchsuchen der E-Mails im Ordner {folder}")
                return []
            
            for uid in data[0].split():
                result, msg_data = mail.uid('fetch', uid, "(RFC822)")
                if result != "OK":
                    logging.error(f"Fehler beim Abrufen der Nachricht mit UID {uid}")
                    continue
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # E-Mail Infos extrahieren
                email_info = {
                    "uid": uid.decode(),
                    "subject": msg["subject"],
                    "from": msg["from"],
                    "to": msg["to"],
                    "date": msg["date"],
                    "text": "",
                    "attachments": []
                }

                # Textinhalt der E-Mail extrahieren
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = part.get_content_disposition()

                        # Textinhalt extrahieren (Text)
                        if content_disposition is None:  # Nicht-Anhang
                            if content_type == "text/plain":
                                email_info["text"] += part.get_payload(decode=True).decode('utf-8', errors='replace').strip()

                        # Anhänge speichern
                        if save_attachments == True:
                            if content_disposition == 'attachment':
                                filename = part.get_filename()
                                if filename:
                                    email_info["attachments"].append(filename)
                                    if not os.path.exists(attachment_dir):
                                        os.makedirs(attachment_dir)
                                    with open(os.path.join(attachment_dir, filename), "wb") as f:
                                        f.write(part.get_payload(decode=True))
                                    logging.info(f"Anhang {filename} gespeichert.")
                        else:
                            logging.info(f"Anhang {filename} nicht gespeichert.")
                else:
                    # Falls die E-Mail nicht multipart ist (einfacher Text)
                    email_info["text"] = msg.get_payload(decode=True).decode('utf-8', errors='replace').strip()

                emails_with_details.append(email_info)
            
            logging.info(f"{len(emails_with_details)} E-Mails aus dem Ordner {folder} geholt.")
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der E-Mails: {e}")
        finally:
            mail.logout()

        return emails_with_details

    def list_folders(self) -> List[str]:
        """
        Listet alle verfügbaren Ordner (Mailboxen) auf dem IMAP-Server auf.
        
        :return: Liste der Ordnernamen
        """
        mail = self._connect_imap()
        if not mail:
            return []

        folders = []
        try:
            result, data = mail.list()
            if result == 'OK':
                folders = [folder.decode().split(' "/" ')[-1] for folder in data]
                logging.info("Ordner erfolgreich aufgelistet.")
            else:
                logging.error("Fehler beim Auflisten der Ordner.")
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Ordnerliste: {e}")
        finally:
            mail.logout()
        
        return folders

    def move_email_to_folder(self, uid: str, target_folder: str):
        """
        Verschiebt eine E-Mail in einen anderen Ordner, basierend auf der UID.
        
        :param uid: Die UID der zu verschiebenden E-Mail
        :param target_folder: Zielordner, in den die E-Mail verschoben werden soll
        """
        mail = self._connect_imap()
        if not mail:
            return
        
        try:
            # Sicherstellen, dass der Zielordner existiert
            result, data = mail.list()
            folder_names = [folder.decode().split(' "/" ')[-1] for folder in data]
            if target_folder not in folder_names:
                logging.error(f"Der Zielordner '{target_folder}' existiert nicht.")
                return
            
            # Wählen des Posteingangs (oder eines anderen Quellordners)
            mail.select('inbox')
            
            # Kopieren der E-Mail in den Zielordner
            result = mail.uid('COPY', uid, target_folder)
            if result[0] == 'OK':
                # Markieren der E-Mail als gelöscht im Quellordner
                mail.uid('STORE', uid, '+FLAGS', '(\Deleted)')
                mail.expunge()  # Löscht alle Nachrichten, die als gelöscht markiert sind
                logging.info(f"E-Mail {uid} erfolgreich nach {target_folder} verschoben.")
            else:
                logging.error(f"Fehler beim Kopieren der E-Mail {uid} nach {target_folder}.")
        
        except imaplib.IMAP4.error as e:
            logging.error(f"IMAP-Fehler: {e}")
        except Exception as e:
            logging.error(f"Fehler beim Verschieben der E-Mail {uid}: {e}")
        finally:
            mail.logout()


    def reply_to_email(self, original_email: email.message.EmailMessage, reply_body: str):
        """
        Antwortet auf eine empfangene E-Mail.
        
        :param original_email: Die E-Mail, auf die geantwortet werden soll
        :param reply_body: Der Text der Antwort
        """
        server = self._connect_smtp()
        if not server:
            return

        try:
            reply = EmailMessage()
            reply["From"] = self.email_address
            reply["To"] = original_email["From"]
            reply["Subject"] = "Re: " + original_email["Subject"]
            reply.set_content(reply_body)

            # Antwort senden
            server.send_message(reply)
            logging.info(f"Antwort an {original_email['From']} gesendet.")
        except Exception as e:
            logging.error(f"Fehler beim Antworten auf die E-Mail: {e}")
        finally:
            server.quit()

    def get_conversation_with_contact(self, contact_email: str, folder: str = "inbox") -> List[dict]:
        """
        Holt den Nachrichtenverlauf mit einer bestimmten E-Mail-Adresse aus einem bestimmten Ordner.
        Gibt zusätzlich den Text, das Empfangsdatum und die Anhänge jeder E-Mail an.
        
        :param contact_email: Die E-Mail-Adresse des Kontakts
        :param folder: Der IMAP-Ordner
        :return: Liste von E-Mails mit Betreff, Empfangsdatum, Text und Anhängen
        """
        mail = self._connect_imap()
        if not mail:
            return []

        conversations = []
        try:
            mail.select(folder)
            search_criteria = f'(OR FROM "{contact_email}" TO "{contact_email}")'
            result, data = mail.search(None, search_criteria)
            if result != "OK":
                logging.error(f"Fehler beim Suchen des Verlaufs mit {contact_email} im Ordner {folder}")
                return []
            
            for num in data[0].split():
                result, msg_data = mail.fetch(num, "(RFC822)")
                if result != "OK":
                    logging.error(f"Fehler beim Abrufen der Nachricht mit ID {num}")
                    continue
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extrahiere E-Mail-Details
                email_info = {
                    "subject": msg["subject"],
                    "from": msg["from"],
                    "to": msg["to"],
                    "date": msg["date"],
                    "text": "",
                    "attachments": []
                }

                # Überprüfen auf Anhänge und Textinhalt extrahieren
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = part.get_content_disposition()

                        # Nur "text/plain"-Inhalt extrahieren, HTML wird ignoriert
                        if content_disposition is None and content_type == "text/plain":  
                            email_info["text"] += part.get_payload(decode=True).decode('utf-8', errors='replace').strip()

                        # Anhänge extrahieren
                        if content_disposition == 'attachment':
                            filename = part.get_filename()
                            if filename:
                                email_info["attachments"].append(filename)
                else:
                    # Falls die E-Mail nicht multipart ist (einfacher Text)
                    email_info["text"] = msg.get_payload(decode=True).decode('utf-8', errors='replace').strip()

                conversations.append(email_info)
            
            logging.info(f"{len(conversations)} Nachrichten mit {contact_email} aus dem Ordner {folder} abgerufen.")
        except Exception as e:
            logging.error(f"Fehler beim Abrufen des Verlaufs mit {contact_email}: {e}")
        finally:
            mail.logout()

        return conversations

    def send_email_with_attachment(self, recipient: str, subject: str, body: str, attachments: Optional[List[str]] = None, cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None):
        """
        Sendet eine E-Mail mit einem oder mehreren Anhängen.
        
        :param recipient: E-Mail-Adresse des Empfängers
        :param subject: Betreff der E-Mail
        :param body: Textinhalt der E-Mail
        :param attachments: Liste von Dateipfaden zu den Anhängen
        :param cc: Optional: Liste von CC-Empfängern
        :param bcc: Optional: Liste von BCC-Empfängern
        """
        server = self._connect_smtp()
        if not server:
            return

        try:
            # Erstellen der E-Mail-Nachricht mit MIMEMultipart (für Anhänge)
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = recipient
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ', '.join(cc)
            if bcc:
                msg["Bcc"] = ', '.join(bcc)
            
            # Füge den Nachrichtentext hinzu
            msg.attach(MIMEText(body, "plain"))
            
            # Anhänge hinzufügen
            if attachments:
                for file_path in attachments:
                    if os.path.isfile(file_path):
                        with open(file_path, "rb") as file:
                            # Erstellen des MIMEBase Objekts für den Anhang
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(file.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                "Content-Disposition", f"attachment; filename= {os.path.basename(file_path)}"
                            )
                            msg.attach(part)
                    else:
                        logging.warning(f"Anhang '{file_path}' existiert nicht oder ist kein gültiger Dateipfad.")
            
            # E-Mail senden
            server.send_message(msg)
            logging.info(f"E-Mail mit Anhang an {recipient} gesendet.")
        
        except Exception as e:
            logging.error(f"Fehler beim Senden der E-Mail mit Anhang: {e}")
        finally:
            server.quit()