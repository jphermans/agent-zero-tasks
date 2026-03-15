#!/usr/bin/env python3
"""
Invoice Checker Script
Checks Fastmail for invoice emails, extracts PDF data, sends Telegram notification
"""

import imaplib
import email
from email.header import decode_header
import os
import re
import fitz  # PyMuPDF
import requests
from datetime import datetime, timedelta
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
                today = datetime.now().date()
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
    processed[msg_id] = datetime.now().strftime('%Y-%m-%d')
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

def search_invoice_emails(mail: imaplib.IMAP4_SSL) -> List[Tuple[str, email.message.Message]]:
    """Search for emails containing invoice keywords from today only"""
    print("🔍 Searching for invoice emails from today...")
    mail.select("INBOX")
    
    invoice_emails = []
    
    # Get today's date in IMAP format (02-Mar-2026)
    search_date = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")  # Search last 3 days
    print(f"   📅 Filtering for date: {search_date} (last 3 days)")
    
    # Load already processed email IDs
    processed_ids = load_processed_ids()
    print(f"   📋 Already processed today: {len(processed_ids)} email(s)")
    
    # Search for each keyword with today's date filter
    for keyword in INVOICE_KEYWORDS:
        try:
            # SINCE filters emails from today onwards
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
                            date = msg.get("Date", "")
                            
                            # Check if not already added
                            if msg_id_str not in [e[0] for e in invoice_emails]:
                                invoice_emails.append((msg_id_str, msg))
                                print(f"   📧 Found NEW: {subject[:50]}... from {sender[:30]}")
        except Exception as e:
            print(f"   ⚠️ Error searching for '{keyword}': {e}")
    
    print(f"📬 Found {len(invoice_emails)} invoice email(s)")
    return invoice_emails

def extract_pdf_attachments(msg: email.message.Message) -> List[Tuple[str, bytes]]:
    """Extract PDF attachments from an email"""
    pdf_attachments = []
    
    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition", ""))
        content_type = part.get_content_type()
        
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
        # Save to temp file and open with PyMuPDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_data)
            tmp_path = tmp.name
        
        doc = fitz.open(tmp_path)
        full_text = ""
        
        for page in doc:
            full_text += page.get_text()
        
        doc.close()
        os.unlink(tmp_path)
        
        result["raw_text"] = full_text[:500]  # Store first 500 chars for debugging
        
        # Extract patterns
        text_lower = full_text.lower()
        
        # Try to find amount (various currency formats)
        amount_patterns = [
            r'(?:total|totaal|betrag|amount|summe)[:\s]*[€$£]?\s*([\d.,]+\s*(?:EUR|USD|GBP|€|\$|£)?)',
            r'[€$£]\s*([\d.,]+)',
            r'([\d.,]+)\s*(?:EUR|USD|GBP)',
            r'(?:bedrag|amount)[:\s]*[€$£]?\s*([\d.,]+)',
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                result["amount"] = match.group(1).strip()
                break
        
        # Try to find due date
        date_patterns = [
            r'(?:due|payable|payment due|verval|uiterlijke|betaaltermijn)[:\s]*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
            r'(?:due|payable|payment due|verval)[:\s]*(\d{4}[./-]\d{1,2}[./-]\d{1,2})',
            r'(?:vervaldatum)[:\s]*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
            r'(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches:
                # Take the last date found (usually due date)
                result["due_date"] = matches[-1]
                break
        
        # Try to find sender/company name (usually at the top of the document)
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        if lines:
            # First non-empty lines often contain sender info
            for line in lines[:10]:
                if len(line) > 3 and not re.match(r'^(invoice|faktuur|factuur|rechnung|date|page)\b', line.lower()):
                    result["sender"] = line[:50]
                    break
        
    except Exception as e:
        print(f"      ⚠️ Error extracting PDF data: {e}")
    
    return result

def send_telegram_message(invoices: List[Dict]) -> bool:
    """Send formatted Telegram message with invoice info - ALWAYS sends a message"""
    
    if not invoices:
        # No invoices found - still send notification
        message = "🧾 *Invoice Checker Report*\n\n"
        message += "📭 Geen nieuwe facturen gevonden vandaag\n\n"
        message += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    else:
        # Group invoices by sender domain
        by_sender = defaultdict(list)
        for inv in invoices:
            sender = inv.get('email_sender', 'Unknown')
            # Extract domain or company name
            if '<' in sender:
                domain = sender.split('@')[-1].split('>')[0].split('.')[0]
            else:
                domain = sender.split()[0] if sender.split() else 'Unknown'
            by_sender[domain].append(inv)
        
        # Build compact summary message
        message = "🧾 *Invoice Checker Report*\n\n"
        message += f"📊 Found *{len(invoices)}* invoices with PDFs\n\n"
        
        # Group summary
        message += "*By Provider:*\n"
        for sender, invs in sorted(by_sender.items(), key=lambda x: -len(x[1]))[:10]:
            message += f"• {sender.title()}: {len(invs)} invoice(s)\n"
        
        # Calculate total (try to extract numeric amounts)
        total = 0.0
        currency = "€"
        for inv in invoices:
            amt = inv.get('amount', '')
            if amt:
                # Try to extract number
                nums = re.findall(r'[\d.]+', str(amt).replace(',', '.'))
                if nums:
                    try:
                        total += float(nums[0])
                    except:
                        pass
                if 'EUR' in str(amt) or '€' in str(amt):
                    currency = "€"
                elif 'USD' in str(amt) or '$' in str(amt):
                    currency = "$"
        
        message += f"\n💰 *Total detected:* {currency}{total:.2f}\n"
        
        # Recent/upcoming due dates
        due_dates = []
        for inv in invoices:
            if inv.get('due_date'):
                due_dates.append((inv.get('due_date'), inv.get('sender', 'Unknown')[:20]))
        
        if due_dates:
            message += f"\n📅 *Due dates found:* {len(due_dates)}\n"
            message += "Recent: " + ", ".join([d[0] for d in due_dates[-3:]])
        
        message += f"\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # Send via Telegram API
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_USER_ID,
        "text": message,
        "parse_mode": "Markdown"
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
                    
                    # Mark this email as processed
                    save_processed_id(msg_id)
                    print(f"   ✅ Marked as processed")
                else:
                    print("   ⚠️ No PDF attachments found in this email")
                    # Still mark as processed to avoid re-checking
                    save_processed_id(msg_id)
        
        # Send Telegram notification - ALWAYS, even if no invoices
        print("\n" + "-"*50)
        send_telegram_message(invoices_found)
        
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
