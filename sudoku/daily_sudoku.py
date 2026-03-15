#!/usr/bin/env python3
"""Dagelijkse Sudoku Generator met Cloudflare Tunnel"""

import json
import random
import requests
import subprocess
import re
import time
import os
import glob
from datetime import datetime

# Haal tokens uit omgevingsvariabelen (veiliger dan hardcoden)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_USERID", "")
BASE_DIR = "/a0/usr/workdir/sudoku_data"
SUDOKU_FILE = f"{BASE_DIR}/sudoku.html"
SOLUTION_FILE = f"{BASE_DIR}/latest_solution.json"
HTTP_PORT = 8765

def stop_tunnels():
    subprocess.run(["pkill", "-f", "cloudflared"], capture_output=True)
    subprocess.run(["pkill", "-f", f"http.server {HTTP_PORT}"], capture_output=True)
    time.sleep(2)
    print("Tunnels gestopt")

def start_server():
    subprocess.Popen(["python", "-m", "http.server", str(HTTP_PORT), "--bind", "0.0.0.0"],
        cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    print(f"Server op {HTTP_PORT}")

def start_tunnel():
    proc = subprocess.Popen(["cloudflared", "tunnel", "--url", f"http://localhost:{HTTP_PORT}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(30):
        line = proc.stdout.readline()
        if "trycloudflare.com" in line:
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if m:
                print(f"Tunnel: {m.group(0)}")
                return m.group(0)
        time.sleep(1)
    return None

def make_sudoku(date_str):
    """Genereer een unieke sudoku gebaseerd op de datum"""
    # Gebruik datum als seed voor reproduceerbare maar dagelijkse variatie
    seed = int(date_str.replace("-", ""))
    random.seed(seed)
    
    def valid(b, r, c, n):
        for i in range(9):
            if b[r][i] == n or b[i][c] == n: return False
        br, bc = 3*(r//3), 3*(c//3)
        for i in range(br, br+3):
            for j in range(bc, bc+3):
                if b[i][j] == n: return False
        return True
    
    def solve(b):
        for i in range(9):
            for j in range(9):
                if b[i][j] == 0:
                    for n in random.sample(range(1, 10), 9):  # Random volgorde
                        if valid(b, i, j, n):
                            b[i][j] = n
                            if solve(b): return True
                            b[i][j] = 0
                    return False
        return True
    
    # Start met leeg bord en vul het op
    b = [[0]*9 for _ in range(9)]
    solve(b)
    sol = [r[:] for r in b]
    
    # Verwijder cellen voor de puzzle - minder verwijderen = makkelijker
    # 28-30 lege cellen = makkelijk, 35 = gemiddeld, 40+ = moeilijk
    pos = [(i,j) for i in range(9) for j in range(9)]
    random.shuffle(pos)
    for i,j in pos[:28]:  # 28 lege cellen = makkelijker puzzle
        b[i][j] = 0
    
    # Reset random seed voor toekomstige random operaties
    random.seed()
    return b, sol

def fmt_sol(s):
    l = ["+-----+-----+-----+"]
    for i,r in enumerate(s):
        if i in [3,6]: l.append("+-----+-----+-----+")
        line = "|"
        for j,n in enumerate(r):
            if j in [3,6]: line += " |"
            line += f" {n}"
        l.append(line + " |")
    l.append("+-----+-----+-----+")
    return "\n".join(l)

def make_html(p, s, d):
    template_file = f"{BASE_DIR}/sudoku_template.html"
    with open(template_file, "r") as f:
        html = f.read()
    html = html.replace("__DATE__", d)
    html = html.replace("__PUZZLE__", json.dumps(p))
    html = html.replace("__SOLUTION__", json.dumps(s))
    html = html.replace("__SOLUTION_BTN__", '<button class="btn bs" onclick="sol()">Oplossing</button>')
    return html

def send(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("Waarschuwing: TELEGRAM_BOT_TOKEN of TELEGRAM_USERID niet ingesteld")
        return
    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    print("Verstuurd" if r.json().get("ok") else f"Fout: {r.json()}")

def cleanup_old_sudokus(today):
    """Verwijder oude sudoku bestanden behalve die van vandaag
    Alleen datum-formaat: sudoku_YYYY-MM-DD.html"""
    import re
    date_pattern = re.compile(r'sudoku_\d{4}-\d{2}-\d{2}\.html$')
    
    for f in os.listdir(BASE_DIR):
        if date_pattern.match(f):
            if f != f"sudoku_{today}.html":
                try:
                    os.remove(os.path.join(BASE_DIR, f))
                    print(f"Oude sudoku verwijderd: {f}")
                except Exception as e:
                    print(f"Kon niet verwijderen {f}: {e}")

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== Sudoku {today} ===")

    # Oplossing van gisteren
    if os.path.exists(SOLUTION_FILE):
        with open(SOLUTION_FILE) as f: d = json.load(f)
        if d.get('date') != today:  # Alleen sturen als het niet vandaag is
            sol_msg = f"*Oplossing {d.get('date','gisteren')}:*\n\n```\n{fmt_sol(d.get('solution',[]))}\n```"
            send(sol_msg)

    # Controleer of er al een sudoku is voor vandaag
    today_file = f"{BASE_DIR}/sudoku_{today}.html"
    if os.path.exists(today_file):
        print(f"Sudoku voor {today} bestaat al")
        # Kopieer naar sudoku.html voor de server
        with open(today_file, "r") as f:
            html = f.read()
        with open(SUDOKU_FILE, "w") as f:
            f.write(html)
    else:
        # Maak nieuwe sudoku voor vandaag
        p, s = make_sudoku(today)
        html = make_html(p, s, today)
        
        # Sla datum-specifiek bestand op
        with open(today_file, "w") as f:
            f.write(html)
        
        # Sla actieve sudoku op
        with open(SUDOKU_FILE, "w") as f:
            f.write(html)
        
        # Sla oplossing op
        with open(SOLUTION_FILE, "w") as f:
            json.dump({"date": today, "solution": s}, f)
        
        print(f"Nieuwe sudoku gegenereerd voor {today}")
        
        # Verwijder oude sudoku bestanden na succesvolle generatie
        cleanup_old_sudokus(today)

    # Start tunnel
    stop_tunnels()
    start_server()
    url = start_tunnel()
    if not url:
        send("FOUT: Geen tunnel!")
        return

    # Stuur link
    link_msg = f"*Sudoku {today}*\n\n[Open in Safari]({url}/sudoku.html)\n\nVeel plezier!"
    send(link_msg)
    print(f"=== Klaar: {url}/sudoku.html ===")

if __name__ == "__main__":
    main()
