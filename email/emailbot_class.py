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

# Initialisiere das Logging, um Status- und Fehlerinformationen in die Konsole auszugeben
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class EmailBot:
    """
    EmailBot bietet Funktionen zum Senden, Empfangen und Verwalten von E-Mails über SMTP und IMAP.
    """

    def __init__(self, smtp_server: str, smtp_port: int, imap_server: str, imap_port: int, 
                 email_address: str, password: str):
        """
        Initialisiert den EmailBot mit den Serverinformationen und Benutzerdaten.
        
        :param smtp_server: Adresse des SMTP-Servers
        :param smtp_port: Port des SMTP-Servers
        :param imap_server: Adresse des IMAP-Servers
        :param imap_port: Port des IMAP-Servers
        :param email_address: E-Mail-Adresse des Benutzers
        :param password: Passwort des E-Mail-Kontos
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.email_address = email_address
        self.password = password

    def _connect_smtp(self, retries=20, delay=1):
        """
        Stellt eine Verbindung zum SMTP-Server her.
        
        :param retries: Anzahl der Verbindungsversuche
        :param delay: Verzögerung zwischen den Versuchen in Sekunden
        :return: SMTP-Verbindung, wenn erfolgreich
        """
        return self._connect(retries, delay, "smtp")

    def _connect_imap(self, retries=20, delay=1):
        """
        Stellt eine Verbindung zum IMAP-Server her.
        
        :param retries: Anzahl der Verbindungsversuche
        :param delay: Verzögerung zwischen den Versuchen in Sekunden
        :return: IMAP-Verbindung, wenn erfolgreich
        """
        return self._connect(retries, delay, "imap")

    def _connect(self, retries, delay, protocol):
        """
        Universelle Verbindungsmethode für SMTP und IMAP mit Wiederholungslogik.
        
        :param retries: Anzahl der Verbindungsversuche
        :param delay: Verzögerung zwischen den Versuchen in Sekunden
        :param protocol: Protokolltyp ("smtp" oder "imap")
        :return: Verbindung zum entsprechenden Server oder None bei Fehlschlag
        """
        for attempt in range(retries):
            try:
                if protocol == "smtp":
                    # Erstelle eine Verbindung zum SMTP-Server und authentifiziere den Benutzer
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                    server.starttls()
                    server.login(self.email_address, self.password)
                    logging.info(f"Erfolgreich mit dem {protocol.upper()}-Server verbunden.")
                    return server
                elif protocol == "imap":
                    # Erstelle eine Verbindung zum IMAP-Server und authentifiziere den Benutzer
                    mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
                    mail.login(self.email_address, self.password)
                    logging.info(f"Erfolgreich mit dem {protocol.upper()}-Server verbunden.")
                    return mail
            except Exception as e:
                logging.error(f"Fehler beim Verbinden mit dem {protocol.upper()}-Server: {e}")
                if attempt < retries - 1:
                    logging.info(f"Erneuter Verbindungsversuch in {delay} Sekunden...")
                    time.sleep(delay)
                else:
                    logging.error(f"Maximale Anzahl der Verbindungsversuche für {protocol.upper()} erreicht.")
        return None

    def send_email(self, recipient: str, subject: str, body: str, cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None):
        """
        Sendet eine einfache E-Mail.
        
        :param recipient: Empfänger der E-Mail
        :param subject: Betreff der E-Mail
        :param body: Inhalt der E-Mail
        :param cc: Optionale Liste von CC-Empfängern
        :param bcc: Optionale Liste von BCC-Empfängern
        """
        server = self._connect_smtp()
        if not server:
            return
        # Verwende eine Hilfsmethode zum Senden der Nachricht
        self._send_message(server, recipient, subject, body, cc, bcc)
        server.quit()

    def _send_message(self, server, recipient, subject, body, cc, bcc):
        """
        Hilfsmethode zum Erstellen und Senden einer E-Mail-Nachricht.
        
        :param server: SMTP-Server-Objekt
        :param recipient: Empfänger der E-Mail
        :param subject: Betreff der E-Mail
        :param body: Inhalt der E-Mail
        :param cc: Optionale Liste von CC-Empfängern
        :param bcc: Optionale Liste von BCC-Empfängern
        """
        try:
            msg = EmailMessage()
            msg["From"] = self.email_address
            msg["To"] = recipient
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ', '.join(cc)
            if bcc:
                msg["Bcc"] = ', '.join(bcc)
            msg.set_content(body)
            # Sende die E-Mail über den SMTP-Server
            server.send_message(msg)
            logging.info(f"E-Mail an {recipient} gesendet.")
        except Exception as e:
            logging.error(f"Fehler beim Senden der E-Mail: {e}")

    def fetch_emails(self, folder: str = "inbox", search_criteria: str = 'ALL', save_attachments: bool = True, attachment_dir: str = "./attachments") -> List[dict]:
        """
        Holt E-Mails aus einem bestimmten Ordner und speichert Anhänge, falls angegeben.
        
        :param folder: Ordner, aus dem die E-Mails abgerufen werden sollen
        :param search_criteria: IMAP-Suchkriterien (z.B. "ALL" oder "UNSEEN")
        :param save_attachments: Gibt an, ob Anhänge gespeichert werden sollen
        :param attachment_dir: Verzeichnis zum Speichern der Anhänge
        :return: Liste von E-Mail-Daten
        """
        mail = self._connect_imap()
        if not mail:
            return []
        emails_with_details = self._search_and_fetch_emails(mail, folder, search_criteria, save_attachments, attachment_dir)
        mail.logout()
        return emails_with_details

    def _search_and_fetch_emails(self, mail, folder, search_criteria, save_attachments, attachment_dir):
        """
        Sucht und holt E-Mails aus einem IMAP-Ordner basierend auf den Suchkriterien.
        
        :param mail: IMAP-Verbindung
        :param folder: Name des Ordners
        :param search_criteria: Suchkriterien für IMAP
        :param save_attachments: Gibt an, ob Anhänge gespeichert werden sollen
        :param attachment_dir: Verzeichnis zum Speichern der Anhänge
        :return: Liste der E-Mail-Daten
        """
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
                # Parsen der E-Mail und Speicherung der Anhänge
                email_info = self._parse_email(msg_data[0][1], uid, save_attachments, attachment_dir)
                emails_with_details.append(email_info)
            logging.info(f"{len(emails_with_details)} E-Mails aus dem Ordner {folder} geholt.")
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der E-Mails: {e}")
        return emails_with_details

    def _parse_email(self, raw_email, uid, save_attachments, attachment_dir):
        """
        Parst die E-Mail und extrahiert die Informationen sowie Anhänge.
        
        :param raw_email: Rohdaten der E-Mail
        :param uid: UID der E-Mail
        :param save_attachments: Gibt an, ob Anhänge gespeichert werden sollen
        :param attachment_dir: Verzeichnis zum Speichern der Anhänge
        :return: Dictionary mit E-Mail-Daten
        """
        msg = email.message_from_bytes(raw_email)
        email_info = {
            "uid": uid.decode(),
            "subject": msg["subject"],
            "from": msg["from"],
            "to": msg["to"],
            "date": msg["date"],
            "text": "",
            "attachments": []
        }
        # Extrahiert den Text und speichert die Anhänge
        self._extract_email_text_and_attachments(msg, email_info, save_attachments, attachment_dir)
        return email_info

    def _extract_email_text_and_attachments(self, msg, email_info, save_attachments, attachment_dir):
        """
        Extrahiert den Text der E-Mail und speichert Anhänge, falls erforderlich.
        
        :param msg: E-Mail-Nachricht
        :param email_info: Dictionary, in dem die extrahierten Daten gespeichert werden
        :param save_attachments: Gibt an, ob Anhänge gespeichert werden sollen
        :param attachment_dir: Verzeichnis zum Speichern der Anhänge
        """
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = part.get_content_disposition()

                # Textinhalt extrahieren
                if content_disposition is None and (content_type == "text/plain" or content_type == "text/html"):
                    email_info["text"] += self._decode_payload(part)

                # Anhänge speichern
                if save_attachments and content_disposition == 'attachment':
                    self._save_attachments(part, email_info, attachment_dir)
        else:
            email_info["text"] = self._decode_payload(msg)

    def _decode_payload(self, part):
        """
        Dekodiert den Inhalt der E-Mail-Nachricht.
        
        :param part: Nachrichtenteil der E-Mail
        :return: Dekodierter Textinhalt der E-Mail
        """
        try:
            return part.get_payload(decode=True).decode('utf-8')
        except UnicodeDecodeError:
            try:
                return part.get_payload(decode=True).decode('latin-1')
            except UnicodeDecodeError:
                return part.get_payload(decode=True).decode('ISO-8859-1', errors='replace')

    def _save_attachments(self, part, email_info, attachment_dir):
        """
        Speichert den Anhang einer E-Mail im angegebenen Verzeichnis.
        
        :param part: Nachrichtenteil, der den Anhang enthält
        :param email_info: Dictionary mit den E-Mail-Daten, das um die Anhänge ergänzt wird
        :param attachment_dir: Verzeichnis zum Speichern der Anhänge
        """
        filename = part.get_filename()
        if filename:
            email_info["attachments"].append(filename)
            if not os.path.exists(attachment_dir):
                os.makedirs(attachment_dir)
            with open(os.path.join(attachment_dir, filename), "wb") as f:
                f.write(part.get_payload(decode=True))
            logging.info(f"Anhang {filename} gespeichert.")

    def list_folders(self) -> List[str]:
        """
        Listet alle Ordner des IMAP-Postfachs auf.
        
        :return: Liste der Ordnernamen
        """
        mail = self._connect_imap()
        if not mail:
            return []
        folders = self._get_folders(mail)
        mail.logout()
        return folders

    def _get_folders(self, mail):
        """
        Hilfsmethode zum Abrufen der Ordner aus dem IMAP-Postfach.
        
        :param mail: IMAP-Verbindung
        :return: Liste der Ordnernamen
        """
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
        return folders

    def move_email_to_folder(self, uid: str, target_folder: str):
        """
        Verschiebt eine E-Mail in einen anderen Ordner.
        
        :param uid: UID der zu verschiebenden E-Mail
        :param target_folder: Zielordner, in den die E-Mail verschoben werden soll
        """
        mail = self._connect_imap()
        if not mail:
            return
        self._move_email(mail, uid, target_folder)
        mail.logout()

    def _move_email(self, mail, uid, target_folder):
        """
        Hilfsmethode zum Verschieben einer E-Mail.
        
        :param mail: IMAP-Verbindung
        :param uid: UID der zu verschiebenden E-Mail
        :param target_folder: Zielordner
        """
        try:
            result, data = mail.list()
            folder_names = [folder.decode().split(' "/" ')[-1] for folder in data]
            if target_folder not in folder_names:
                logging.error(f"Der Zielordner '{target_folder}' existiert nicht.")
                return
            mail.select('inbox')
            result = mail.uid('COPY', uid, target_folder)
            if result[0] == 'OK':
                mail.uid('STORE', uid, '+FLAGS', '(\Deleted)')
                mail.expunge()
                logging.info(f"E-Mail {uid} erfolgreich nach {target_folder} verschoben.")
            else:
                logging.error(f"Fehler beim Kopieren der E-Mail {uid} nach {target_folder}.")
        except Exception as e:
            logging.error(f"Fehler beim Verschieben der E-Mail {uid}: {e}")

    def reply_to_email(self, original_email: email.message.EmailMessage, reply_body: str):
        """
        Antwortet auf eine empfangene E-Mail.
        
        :param original_email: Die E-Mail, auf die geantwortet wird
        :param reply_body: Inhalt der Antwort
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
            server.send_message(reply)
            logging.info(f"Antwort an {original_email['From']} gesendet.")
        except Exception as e:
            logging.error(f"Fehler beim Antworten auf die E-Mail: {e}")
        finally:
            server.quit()

    def get_conversation_with_contact(self, contact_email: str, folder: str = "inbox") -> List[dict]:
        """
        Holt den E-Mail-Verlauf mit einer bestimmten Kontakt-E-Mail-Adresse.
        
        :param contact_email: E-Mail-Adresse des Kontakts
        :param folder: Ordner, aus dem die E-Mails geholt werden sollen
        :return: Liste der E-Mail-Daten
        """
        mail = self._connect_imap()
        if not mail:
            return []
        conversations = self._search_and_fetch_emails(mail, folder, f'(OR FROM "{contact_email}" TO "{contact_email}")', False, "")
        mail.logout()
        return conversations

    def send_email_with_attachment(self, recipient: str, subject: str, body: str, attachments: Optional[List[str]] = None, cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None):
        """
        Sendet eine E-Mail mit Anhängen.
        
        :param recipient: Empfänger der E-Mail
        :param subject: Betreff der E-Mail
        :param body: Inhalt der E-Mail
        :param attachments: Liste von Pfaden der anzuhängenden Dateien
        :param cc: Optionale Liste von CC-Empfängern
        :param bcc: Optionale Liste von BCC-Empfängern
        """
        server = self._connect_smtp()
        if not server:
            return
        self._send_message_with_attachments(server, recipient, subject, body, attachments, cc, bcc)
        server.quit()

    def _send_message_with_attachments(self, server, recipient, subject, body, attachments, cc, bcc):
        """
        Hilfsmethode zum Versenden von E-Mails mit Anhängen.
        
        :param server: SMTP-Verbindung
        :param recipient: Empfänger der E-Mail
        :param subject: Betreff der E-Mail
        :param body: Inhalt der E-Mail
        :param attachments: Liste von Pfaden der Anhänge
        :param cc: Optionale Liste von CC-Empfängern
        :param bcc: Optionale Liste von BCC-Empfängern
        """
        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = recipient
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ', '.join(cc)
            if bcc:
                msg["Bcc"] = ', '.join(bcc)
            msg.attach(MIMEText(body, "plain"))
            if attachments:
                self._attach_files(msg, attachments)
            server.send_message(msg)
            logging.info(f"E-Mail mit Anhang an {recipient} gesendet.")
        except Exception as e:
            logging.error(f"Fehler beim Senden der E-Mail mit Anhang: {e}")

    def _attach_files(self, msg, attachments):
        """
        Hängt Dateien an eine E-Mail an.
        
        :param msg: E-Mail-Nachricht, an die Anhänge angefügt werden
        :param attachments: Liste der Dateipfade, die angehängt werden
        """
        for file_path in attachments:
            if os.path.isfile(file_path):
                with open(file_path, "rb") as file:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(file.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(file_path)}")
                    msg.attach(part)
            else:
                logging.warning(f"Anhang '{file_path}' existiert nicht oder ist kein gültiger Dateipfad.")
