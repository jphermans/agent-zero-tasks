#!/usr/bin/env python3
"""Dagelijkse Sudoku Generator met GitHub Pages"""

import json
import random
import requests
import subprocess
import os
import hashlib
from datetime import datetime

# Haal tokens uit omgevingsvariabelen
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_USERID", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

BASE_DIR = "/a0/usr/workdir/sudoku_data"
REPO_DIR = "/a0/usr/workdir/agent-zero-tasks"
SUDOKU_FILE = f"{BASE_DIR}/sudoku.html"
SOLUTION_FILE = f"{BASE_DIR}/latest_solution.json"
PREVIOUS_SOLUTION_FILE = f"{BASE_DIR}/previous_solution.json"
GITHUB_PAGES_URL = "https://jphermans.github.io/agent-zero-tasks/"

def make_sudoku(date_str):
    """Genereer een unieke sudoku gebaseerd op de datum"""
    # Combineer datum met extra entropie voor uniciteit
    base_seed = int(date_str.replace("-", ""))
    # Voeg microseconden toe voor extra willekeurigheid
    extra_entropy = int(datetime.now().microsecond)
    seed = base_seed + extra_entropy
    random.seed(seed)

    print(f"Generating sudoku with seed: {seed} (date: {date_str})")

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
                    for n in random.sample(range(1, 10), 9):
                        if valid(b, i, j, n):
                            b[i][j] = n
                            if solve(b): return True
                            b[i][j] = 0
                    return False
        return True

    b = [[0]*9 for _ in range(9)]
    solve(b)
    sol = [r[:] for r in b]

    # Reset random voor het verwijderen van cellen
    random.seed(seed + 1000)
    pos = [(i,j) for i in range(9) for j in range(9)]
    random.shuffle(pos)
    for i,j in pos[:38]:  # 38 lege cellen = moeilijker
        b[i][j] = 0

    random.seed()
    return b, sol

def get_sudoku_hash(solution):
    """Genereer een hash van de oplossing voor vergelijking"""
    return hashlib.md5(json.dumps(solution).encode()).hexdigest()

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
        return False
    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    if r.json().get("ok"):
        print("Verstuurd")
        return True
    else:
        print(f"Fout: {r.json()}")
        return False

def cleanup_old_sudokus(today):
    """Verwijder oude sudoku bestanden"""
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

def push_to_github():
    """Push sudoku naar GitHub Pages"""
    try:
        docs_dir = f"{REPO_DIR}/docs"
        os.makedirs(docs_dir, exist_ok=True)

        subprocess.run(["cp", SUDOKU_FILE, f"{docs_dir}/index.html"], check=True)

        subprocess.run(["git", "add", "docs/"], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "commit", "-m", f"Sudoku update {datetime.now().strftime('%Y-%m-%d')}"],
                      cwd=REPO_DIR, capture_output=True)
        subprocess.run(["git", "push"], cwd=REPO_DIR, capture_output=True, check=True)

        print("Gepusht naar GitHub Pages")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git fout: {e}")
        return False
    except Exception as e:
        print(f"Fout bij pushen: {e}")
        return False

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== Sudoku {today} ===")

    # Oplossing van gisteren sturen
    if os.path.exists(SOLUTION_FILE):
        with open(SOLUTION_FILE) as f: d = json.load(f)
        if d.get('date') != today:
            sol_msg = f"*Oplossing {d.get('date','gisteren')}:*\n\n```\n{fmt_sol(d.get('solution',[]))}\n```"
            send(sol_msg)

    # Controleer of er al een sudoku is voor vandaag
    today_file = f"{BASE_DIR}/sudoku_{today}.html"
    if os.path.exists(today_file):
        print(f"Sudoku voor {today} bestaat al")
        with open(today_file, "r") as f:
            html = f.read()
        with open(SUDOKU_FILE, "w") as f:
            f.write(html)
    else:
        # Laad vorige oplossing voor vergelijking
        previous_solution = None
        if os.path.exists(SOLUTION_FILE):
            with open(SOLUTION_FILE) as f:
                prev_data = json.load(f)
                previous_solution = prev_data.get('solution')
                # Sla op als previous_solution
                with open(PREVIOUS_SOLUTION_FILE, "w") as pf:
                    json.dump(prev_data, pf)

        # Maak nieuwe sudoku met uniciteitscontrole
        max_attempts = 10
        for attempt in range(max_attempts):
            p, s = make_sudoku(today)

            if previous_solution:
                current_hash = get_sudoku_hash(s)
                previous_hash = get_sudoku_hash(previous_solution)

                if current_hash == previous_hash:
                    print(f"WAARSCHUWING: Zelfde sudoku gegenereerd! Poging {attempt + 1}/{max_attempts}")
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        print(f"Kon geen unieke sudoku genereren na {max_attempts} pogingen")
                else:
                    print(f"Unieke sudoku gegenereerd (hash: {current_hash[:8]}...)")
                    break
            else:
                print("Eerste sudoku gegenereerd")
                break

        html = make_html(p, s, today)

        with open(today_file, "w") as f:
            f.write(html)
        with open(SUDOKU_FILE, "w") as f:
            f.write(html)
        with open(SOLUTION_FILE, "w") as f:
            json.dump({"date": today, "solution": s, "hash": get_sudoku_hash(s)}, f)

        print(f"Nieuwe sudoku gegenereerd voor {today}")
        cleanup_old_sudokus(today)

    # Push naar GitHub Pages
    if push_to_github():
        link_msg = f"Sudoku {today} - Open: {GITHUB_PAGES_URL}"
        send(link_msg)
        print(f"=== Klaar: {GITHUB_PAGES_URL} ===")
    else:
        link_msg = f"Sudoku {today} - Open: {GITHUB_PAGES_URL} (GitHub Pages update kan even duren)"
        send(link_msg)
        print(f"=== Klaar (met waarschuwing): {GITHUB_PAGES_URL} ===")

if __name__ == "__main__":
    main()
