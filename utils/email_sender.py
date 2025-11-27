import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import re

def validate_email(email):
    """Simple email validation using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None

def send_email(recipient_list, subject, body_html, attachment_df=None, recipient_names=None):
    """
    Sends an email to the list of recipients.
    Returns a tuple: (overall_success, message, detailed_results)
    
    Args:
        recipient_list: List of email addresses
        subject: Email subject
        body_html: Email body HTML template (can contain {recipient_name} placeholder)
        attachment_df: Optional DataFrame to attach as CSV
        recipient_names: Optional dict mapping email -> name for personalization
    """
    # Validate all emails first
    valid_recipients = []
    invalid_recipients = []
    
    for email in recipient_list:
        if validate_email(email):
            valid_recipients.append(email.strip())
        else:
            invalid_recipients.append(email.strip())
    
    if not valid_recipients:
        return False, "Nessun indirizzo email valido trovato.", {"invalid": invalid_recipients}
    
    # Track results
    successful = []
    failed = []
    
    try:
        smtp_config = st.secrets["email"]
        sender_email = smtp_config["sender_email"]
        sender_password = smtp_config["sender_password"]
        smtp_server = smtp_config["smtp_server"]
        smtp_port = smtp_config["smtp_port"]

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            
            for recipient in valid_recipients:
                try:
                    # Personalize body for this recipient
                    recipient_name = "Utente"
                    if recipient_names and recipient in recipient_names:
                        recipient_name = recipient_names[recipient]
                    
                    personalized_body = body_html.replace("{recipient_name}", recipient_name)
                    
                    # Create message for this recipient
                    msg = MIMEMultipart()
                    msg["From"] = sender_email
                    msg["To"] = recipient
                    msg["Subject"] = subject
                    
                    msg.attach(MIMEText(personalized_body, "html"))

                    # Optional: Attach DataFrame as CSV
                    if attachment_df is not None:
                        csv_data = attachment_df.to_csv(index=False)
                        part = MIMEBase('application', "octet-stream")
                        part.set_payload(csv_data)
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', 'attachment; filename="calendario.csv"')
                        msg.attach(part)
                    
                    server.sendmail(sender_email, recipient, msg.as_string())
                    successful.append(recipient)
                except Exception as e:
                    failed.append((recipient, str(e)))
        
        # Build result message
        results = {
            "successful": successful,
            "failed": failed,
            "invalid": invalid_recipients
        }
        
        if successful and not failed and not invalid_recipients:
            recipient_word = "destinatario" if len(successful) == 1 else "destinatari"
            return True, f"Email inviate con successo a {len(successful)} {recipient_word}!", results
        elif successful:
            msg_parts = [f"✅ Inviate: {len(successful)}"]
            if failed:
                msg_parts.append(f"❌ Fallite: {len(failed)}")
            if invalid_recipients:
                msg_parts.append(f"⚠️ Non valide: {len(invalid_recipients)}")
            return True, " | ".join(msg_parts), results
        else:
            return False, "Invio fallito per tutti i destinatari.", results
            
    except Exception as e:
        return False, f"Errore di connessione: {str(e)}", {"successful": successful, "failed": failed, "invalid": invalid_recipients}
