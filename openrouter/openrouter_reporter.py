#!/usr/bin/env python3
"""Daily OpenRouter Cheapest Coding Models Reporter

Configuratie:
- API key in /a0/usr/workdir/openrouter_api_key.txt
- Email via FASTMAIL_USER en FASTMAIL_APP_PASSWORD env vars
- Telegram via TELEGRAM_BOT_TOKEN en TELEGRAM_USERID env vars
"""

import requests
import json
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

API_KEY_FILE = "/a0/usr/workdir/openrouter_api_key.txt"
FASTMAIL_USER = os.environ.get("FASTMAIL_USER", "")
FASTMAIL_PASSWORD = os.environ.get("FASTMAIL_APP_PASSWORD", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_USER_ID = os.environ.get("TELEGRAM_USERID", "")
EMAIL_TO = "jphermans@gmail.com"

def get_api_key():
    with open(API_KEY_FILE, "r") as f:
        return f.read().strip()

def fetch_credits(api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.get("https://openrouter.ai/api/v1/credits", headers=headers, timeout=10)
    data = r.json()["data"]
    remaining = data["total_credits"] - data["total_usage"]
    return {"total": data["total_credits"], "used": data["total_usage"], "remaining": remaining}

def fetch_cheapest_models():
    r = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
    data = r.json()
    models = []
    for model in data.get("data", []):
        name = model.get("id", "")
        pricing = model.get("pricing", {})
        input_price = float(pricing.get("prompt", 0)) * 1000000
        output_price = float(pricing.get("completion", 0)) * 1000000
        if input_price > 0 and any(kw in name.lower() for kw in ["code", "coder", "gpt", "claude", "llama"]):
            models.append({"name": name, "provider": name.split("/")[0] if "/" in name else "unknown", "input_price": input_price, "output_price": output_price})
    models.sort(key=lambda x: x["input_price"])
    return models[:5]

def generate_html(date, top_model, top5, credits):
    rows = ""
    for i, m in enumerate(top5):
        row_class = " class='champ'" if i == 0 else ""
        rows += f"<tr{row_class}><td>{m['name']}</td><td>{m['provider']}</td><td>${m['input_price']:.4f}</td><td>${m['output_price']:.4f}</td></tr>\n"
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{{font-family:Arial;max-width:600px;margin:0 auto;padding:20px;background:#f5f5f5}}table{{width:100%;border-collapse:collapse;margin:20px 0;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.15)}}th{{padding:15px;background:#4CAF50;color:white}}td{{padding:12px;border-bottom:1px solid #eee}}.champ{{background:#FFD700!important;font-weight:bold}}</style></head><body><h1>🏆 OpenRouter Update {date}</h1><h2>🥇 Cheapest: {top_model['name']}</h2><p>Input: ${top_model['input_price']:.4f}/M | Output: ${top_model['output_price']:.4f}/M</p><h3>Top 5</h3><table><tr><th>Model</th><th>Provider</th><th>Input $/M</th><th>Output $/M</th></tr>{rows}</table><h3>Credits: ${credits['remaining']:.2f} remaining</h3></body></html>"""

def send_email(html, date):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily OpenRouter Update - {date}"
    msg["From"] = FASTMAIL_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.fastmail.com", 465) as server:
        server.login(FASTMAIL_USER, FASTMAIL_PASSWORD)
        server.sendmail(FASTMAIL_USER, EMAIL_TO, msg.as_string())
    print("Email verstuurd")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_USER_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    print("Telegram verstuurd")

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== OpenRouter Report {today} ===")
    api_key = get_api_key()
    credits = fetch_credits(api_key)
    top5 = fetch_cheapest_models()
    if not top5:
        print("Geen modellen!")
        return
    html = generate_html(today, top5[0], top5, credits)
    with open(f"/a0/usr/workdir/documents/html/openrouter_report_{today}.html", "w") as f:
        f.write(html)
    send_email(html, today)
    send_telegram(f"🏆 *Cheapest:* {top5[0]['name']} ${top5[0]['input_price']:.4f}/M. Credits: ${credits['remaining']:.2f}")
    print("=== Klaar! ===")

if __name__ == "__main__":
    main()
