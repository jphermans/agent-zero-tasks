#!/usr/bin/env python3
"""
Invoice Checker Script
Checks Fastmail for invoice emails, extracts PDF data and links, sends Telegram notification
"""

import imaplib
import email
from email.header import decode_header
import os
import re
import fitz  # PyMuPDF
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
# Belgische tijdzone
def get_be_time():
    return datetime.now(ZoneInfo("Europe/Brussels"))
import tempfile
from typing import Optional, Tuple, List, Dict
from collections import defaultdict
import json

# File to store processed email IDs
PROCESSED_FILE = "/a0/usr/workdir/scripts/python/processed_invoices.json"

def load_processed_ids() -> set:
    """Load already processed email Message-IDs"""
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, 'r') as f:
                data = json.load(f)
                # Clean old entries (older than 7 days)
                today = get_be_time().date()
                cleaned = {k: v for k, v in data.items()
                          if (today - datetime.strptime(v, '%Y-%m-%d').date()).days < 7}
                return set(cleaned.keys())
        except:
            pass
    return set()

def save_processed_id(msg_id: str):
    """Save a processed email Message-ID"""
    processed = {}
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, 'r') as f:
                processed = json.load(f)
        except:
            pass
    processed[msg_id] = get_be_time().strftime('%Y-%m-%d')
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(processed, f)

# Configuration - will be set externally or use defaults
FASTMAIL_USER = None
FASTMAIL_PASSWORD = None
IMAP_SERVER = "imap.fastmail.com"
IMAP_PORT = 993

TELEGRAM_BOT_TOKEN = None
TELEGRAM_USER_ID = None

def configure(fastmail_user, fastmail_password, telegram_token, telegram_user_id):
    """Configure credentials externally"""
    global FASTMAIL_USER, FASTMAIL_PASSWORD, TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID
    FASTMAIL_USER = fastmail_user
    FASTMAIL_PASSWORD = fastmail_password
    TELEGRAM_BOT_TOKEN = telegram_token
    TELEGRAM_USER_ID = telegram_user_id

# Keywords to search for in email subjects - uitgebreid met NL termen
INVOICE_KEYWORDS = ["invoice", "invoices", "factuur", "facturen", "faktuur", "rechnung", "facture", "factura"]

def decode_mime_words(s: str) -> str:
    """Decode MIME encoded words in email headers"""
    if s is None:
        return ""
    decoded_list = decode_header(s)
    result = []
    for content, encoding in decoded_list:
        if isinstance(content, bytes):
            try:
                result.append(content.decode(encoding or "utf-8", errors="ignore"))
            except:
                result.append(content.decode("utf-8", errors="ignore"))
        else:
            result.append(str(content))
    return "".join(result)

def connect_to_imap() -> imaplib.IMAP4_SSL:
    """Connect to Fastmail IMAP server"""
    print("🔌 Connecting to Fastmail IMAP...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(FASTMAIL_USER, FASTMAIL_PASSWORD)
    print("✅ Connected successfully!")
    return mail

def extract_email_body(msg: email.message.Message) -> str:
    """Extract text body from email"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    body += payload.decode(charset, errors="ignore")
                except:
                    pass
            elif content_type == "text/html" and not body:
                # Fallback to HTML if no plain text
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    html = payload.decode(charset, errors="ignore")
                    # Simple HTML to text conversion
                    body += re.sub(r'<[^>]+>', ' ', html)
                except:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="ignore")
        except:
            pass
    return body

def extract_links_from_email(body: str) -> List[Dict]:
    """Extract relevant links from email body"""
    links = []
    
    # URL pattern
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    
    # Find all URLs
    urls = re.findall(url_pattern, body)
    
    # Filter for relevant invoice/billing links
    invoice_keywords = ['invoice', 'factuur', 'billing', 'payment', 'pay', 'order', 'receipt', 
                       'bestelling', 'betaal', 'rekening', 'view', 'download', 'document']
    
    for url in urls:
        # Clean URL (remove trailing punctuation)
        url = url.rstrip('.,;:')
        
        # Check if URL contains invoice-related keywords
        url_lower = url.lower()
        is_relevant = any(kw in url_lower for kw in invoice_keywords)
        
        # Also check context around URL in body
        if not is_relevant:
            idx = body.find(url)
            if idx > 0:
                context = body[max(0, idx-50):idx+len(url)+50].lower()
                is_relevant = any(kw in context for kw in invoice_keywords)
        
        if is_relevant and len(url) < 200:  # Skip very long URLs
            links.append({"url": url, "type": "invoice_link"})
    
    # Remove duplicates
    seen = set()
    unique_links = []
    for link in links:
        if link["url"] not in seen:
            seen.add(link["url"])
            unique_links.append(link)
    
    return unique_links[:5]  # Max 5 links

def search_invoice_emails(mail: imaplib.IMAP4_SSL) -> List[Tuple[str, email.message.Message]]:
    """Search for emails containing invoice keywords from last 3 days"""
    print("🔍 Searching for invoice emails...")
    mail.select("INBOX")
    
    invoice_emails = []
    
    # Search last 3 days
    search_date = (get_be_time() - timedelta(days=2)).strftime("%d-%b-%Y")
    print(f"   📅 Filtering for date: {search_date} (last 3 days)")
    
    # Load already processed email IDs
    processed_ids = load_processed_ids()
    print(f"   📋 Already processed: {len(processed_ids)} email(s)")
    
    # Search for each keyword with date filter
    for keyword in INVOICE_KEYWORDS:
        try:
            status, messages = mail.search(None, f'(SUBJECT "{keyword}" SINCE {search_date})')
            if status != "OK":
                continue
                
            for msg_id in messages[0].split():
                msg_id_str = msg_id.decode()
                
                # Skip already processed emails
                if msg_id_str in processed_ids:
                    continue
                
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status == "OK":
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subject = decode_mime_words(msg.get("Subject", ""))
                            sender = decode_mime_words(msg.get("From", ""))
                            
                            # Check if not already added
                            if msg_id_str not in [e[0] for e in invoice_emails]:
                                invoice_emails.append((msg_id_str, msg))
                                print(f"   📧 Found: {subject[:50]}... from {sender[:30]}")
        except Exception as e:
            print(f"   ⚠️ Error searching for '{keyword}': {e}")
    
    print(f"📬 Found {len(invoice_emails)} invoice email(s)")
    return invoice_emails

def extract_pdf_attachments(msg: email.message.Message) -> List[Tuple[str, bytes]]:
    """Extract PDF attachments from an email"""
    pdf_attachments = []
    
    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition", ""))
        
        if "attachment" in content_disposition:
            filename = part.get_filename()
            if filename:
                filename = decode_mime_words(filename)
                if filename.lower().endswith(".pdf"):
                    pdf_data = part.get_payload(decode=True)
                    pdf_attachments.append((filename, pdf_data))
                    print(f"      📎 Found PDF: {filename}")
    
    return pdf_attachments

def extract_invoice_data(pdf_data: bytes) -> Dict:
    """Extract sender, amount, and due date from PDF"""
    result = {
        "sender": None,
        "amount": None,
        "due_date": None,
        "raw_text": ""
    }
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_data)
            tmp_path = tmp.name
        
        doc = fitz.open(tmp_path)
        full_text = ""
        
        for page in doc:
            full_text += page.get_text()
        
        doc.close()
        os.unlink(tmp_path)
        
        result["raw_text"] = full_text[:500]
        
        # Extract amount
        amount_patterns = [
            r'(?:total|totaal|betrag|amount|summe)[:\s]*[€$£]?\s*([\d.,]+\s*(?:EUR|USD|GBP|€|\$|£)?)',
            r'[€$£]\s*([\d.,]+)',
            r'([\d.,]+)\s*(?:EUR|USD|GBP)',
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                result["amount"] = match.group(1).strip()
                break
        
        # Extract due date
        date_patterns = [
            r'(?:due|verval|uiterlijke)[:\s]*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
            r'(?:vervaldatum)[:\s]*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches:
                result["due_date"] = matches[-1]
                break
        
        # Extract sender
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        if lines:
            for line in lines[:10]:
                if len(line) > 3 and not re.match(r'^(invoice|faktuur|factuur|rechnung|date|page)\b', line.lower()):
                    result["sender"] = line[:50]
                    break
        
    except Exception as e:
        print(f"      ⚠️ Error extracting PDF data: {e}")
    
    return result

def send_telegram_message(invoices: List[Dict], emails_without_pdf: List[Dict]) -> bool:
    """Send formatted Telegram message - ALWAYS sends"""
    
    total_items = len(invoices) + len(emails_without_pdf)
    
    if total_items == 0:
        message = "🧾 *Invoice Checker Report*\n\n"
        message += "📭 Geen nieuwe facturen gevonden\n\n"
        message += f"⏰ {get_be_time().strftime('%Y-%m-%d %H:%M')}"
    else:
        message = "🧾 *Invoice Checker Report*\n\n"
        
        # Invoices with PDFs
        if invoices:
            message += f"📊 *{len(invoices)} facturen met PDF:*\n\n"
            
            for inv in invoices[:5]:  # Max 5
                sender = inv.get('email_sender', 'Unknown').split('<')[0].strip()[:25]
                amount = inv.get('amount', 'N/A')
                message += f"• {sender}\n"
                if amount and amount != 'N/A':
                    message += f"  💰 {amount}\n"
            
            if len(invoices) > 5:
                message += f"  _... en nog {len(invoices)-5} meer_\n"
        
        # Emails without PDF but with invoice keywords
        if emails_without_pdf:
            message += f"\n📧 *{len(emails_without_pdf)} emails zonder PDF:*\n\n"
            
            for email_info in emails_without_pdf[:5]:  # Max 5
                sender = email_info.get('sender', 'Unknown').split('<')[0].strip()[:25]
                subject = email_info.get('subject', 'No subject')[:40]
                message += f"• *{sender}*\n"
                message += f"  📝 {subject}\n"
                
                # Add links if found
                links = email_info.get('links', [])
                if links:
                    for link in links[:2]:  # Max 2 links per email
                        # Shorten URL for display
                        url_short = link['url'][:50] + '...' if len(link['url']) > 50 else link['url']
                        message += f"  🔗 [Link]({link['url']})\n"
            
            if len(emails_without_pdf) > 5:
                message += f"  _... en nog {len(emails_without_pdf)-5} meer_\n"
        
        message += f"\n⏰ {get_be_time().strftime('%Y-%m-%d %H:%M')}"
    
    # Send via Telegram API
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_USER_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    try:
        print("📤 Sending Telegram notification...")
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        print("✅ Telegram message sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        return False

def main():
    print("\n" + "="*50)
    print("   📊 INVOICE CHECKER")
    print("="*50 + "\n")
    
    mail = None
    invoices_found = []
    emails_without_pdf = []
    
    try:
        # Connect to IMAP
        mail = connect_to_imap()
        
        # Search for invoice emails
        invoice_emails = search_invoice_emails(mail)
        
        if not invoice_emails:
            print("\nℹ️ No invoice emails found.")
        else:
            print(f"\n📥 Processing {len(invoice_emails)} email(s)...\n")
            
            for msg_id, msg in invoice_emails:
                subject = decode_mime_words(msg.get("Subject", "Unknown"))
                sender = decode_mime_words(msg.get("From", "Unknown"))
                
                print(f"\n📧 Processing: {subject[:50]}...")
                print(f"   From: {sender}")
                
                # Get PDF attachments
                pdfs = extract_pdf_attachments(msg)
                
                if pdfs:
                    for pdf_name, pdf_data in pdfs:
                        print(f"   📄 Extracting data from {pdf_name}...")
                        
                        invoice_data = extract_invoice_data(pdf_data)
                        invoice_data['email_subject'] = subject
                        invoice_data['email_sender'] = sender
                        invoice_data['pdf_filename'] = pdf_name
                        
                        invoices_found.append(invoice_data)
                        
                        print(f"      ✓ Sender: {invoice_data.get('sender', 'N/A')}")
                        print(f"      ✓ Amount: {invoice_data.get('amount', 'N/A')}")
                        print(f"      ✓ Due: {invoice_data.get('due_date', 'N/A')}")
                    
                    save_processed_id(msg_id)
                    print(f"   ✅ Marked as processed")
                else:
                    # No PDF - extract links from email body
                    print("   ⚠️ No PDF attachments - extracting links from body...")
                    body = extract_email_body(msg)
                    links = extract_links_from_email(body)
                    
                    email_info = {
                        'subject': subject,
                        'sender': sender,
                        'links': links
                    }
                    emails_without_pdf.append(email_info)
                    
                    if links:
                        print(f"   🔗 Found {len(links)} relevant link(s)")
                    
                    save_processed_id(msg_id)
        
        # Send Telegram notification - ALWAYS
        print("\n" + "-"*50)
        send_telegram_message(invoices_found, emails_without_pdf)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
                print("\n🔌 Disconnected from IMAP")
            except:
                pass
    
    print("\n" + "="*50)
    print("   ✅ Done!")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
