from emailbot_class import EmailBot, EmailMessage
import time
def main():
    while True:
        # Initialisiere den EmailBot mit SMTP- und IMAP-Serverdaten und Benutzeranmeldeinformationen
        smtp_server = "smtp-mail.outlook.com" #for outllok
        smtp_port = 25
        imap_server = "outlook.office365.com" #for outllok
        imap_port = 993
        email_address = "xxx"
        password = "xxx"

        # Erstelle eine Instanz des EmailBot
        email_bot = EmailBot(smtp_server, smtp_port, imap_server, imap_port, email_address, password)

        # Test: Senden einer E-Mail
        print("Senden einer Test-E-Mail...")
        email_bot.send_email(
            recipient="xxx",
            subject="Test E-Mail",
            body="Dies ist eine Test-E-Mail, gesendet durch den EmailBot.",
            cc=[""],
            bcc=[""]
        )

        # Test: Auflisten aller verfügbaren Ordner
        print("\nAuflisten der E-Mail-Ordner...")
        folders = email_bot.list_folders()
        print(f"Verfügbare Ordner: {folders}")

        # Test: Abrufen aller E-Mails aus dem Posteingang
        print("\nAbrufen von E-Mails aus dem Posteingang...")
        inbox_emails = email_bot.fetch_emails(folder="inbox", search_criteria="ALL")
        print(f"Anzahl der E-Mails im Posteingang: {len(inbox_emails)}")
        print(inbox_emails)
        # Test: Anzeigen des E-Mail-Verlaufs mit test.email@xx.com in allen Ordnern
        print("\nNachrichtenverlauf mit testemail abrufen...")
        all_conversations = []
        for folder in folders:
            print(f"Nachrichtenverlauf im Ordner '{folder}' abrufen...")
            conversation = email_bot.get_conversation_with_contact(contact_email="xxx", folder=folder)
            all_conversations.extend(conversation)
            
        print(f"Anzahl der E-Mails im Verlauf mit xxx: {len(all_conversations)}")
        print(all_conversations)
        # Test: Verschieben einer E-Mail (nehmen wir an, dass die erste E-Mail im Posteingang verschoben wird)
        if inbox_emails:
            print("\nVerschieben der ersten E-Mail aus dem Posteingang in einen anderen Ordner...")
            email_id = inbox_emails[0]["uid"]
            target_folder = "Archiv"  # Beispielzielordner
            email_bot.move_email_to_folder(uid=email_id, target_folder=target_folder)
        
        # Test: Antworten auf die erste E-Mail im Verlauf mit test.email@xx.com
        if all_conversations:
            print("\nAntwort auf die erste E-Mail im Verlauf mit test.email@xx.com...")
            original_email = all_conversations[0]
            email_bot.reply_to_email(original_email=original_email, reply_body="Danke für Ihre Nachricht!")
        
        print("\nAlle Tests abgeschlossen.")
        time.sleep(5)
if __name__ == "__main__":
    main()
