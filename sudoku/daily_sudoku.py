#!/usr/bin/env python3
"""Dagelijkse Sudoku Generator met Cloudflare Tunnel"""

import json
import random
import requests
import subprocess
import re
import time
import os
from datetime import datetime

BOT_TOKEN = "8503543419:AAEegQ4TY-RM3U9zHphjyXZVMsTCd5QMcLQ"
CHAT_ID = "365354820"
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

def make_sudoku():
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
                    for n in range(1, 10):
                        if valid(b, i, j, n):
                            b[i][j] = n
                            if solve(b): return True
                            b[i][j] = 0
                    return False
        return True
    b = [[0]*9 for _ in range(9)]
    solve(b)
    sol = [r[:] for r in b]
    pos = [(i,j) for i in range(9) for j in range(9)]
    random.shuffle(pos)
    for i,j in pos[:35]: b[i][j] = 0
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
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no"><title>Sudoku</title><style>*{{box-sizing:border-box}}body{{font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;margin:0;padding:10px;display:flex;align-items:center;justify-content:center}}.c{{background:#fff;border-radius:20px;padding:15px;max-width:400px;width:100%}}h1{{text-align:center;margin:0 0 5px;font-size:1.4em}}.d{{text-align:center;color:#666;margin-bottom:15px}}.g{{display:grid;grid-template-columns:repeat(9,1fr);gap:1px;background:#000;border:3px solid #000;border-radius:8px;overflow:hidden;margin-bottom:15px}}.cell{{aspect-ratio:1;display:flex;align-items:center;justify-content:center;background:#fff;font-size:1.5em;font-weight:bold;cursor:pointer}}.fx{{background:#f0f0f0;color:#333}}.ed{{color:#0066cc}}.sel{{background:#bbdefb!important}}.err{{background:#ffcdd2!important}}.ok{{background:#c8e6c9!important}}.cell:nth-child(3n){{border-right:2px solid #000}}.cell:nth-child(n+19):nth-child(-n+27),.cell:nth-child(n+46):nth-child(-n+54){{border-bottom:2px solid #000}}.np{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:15px}}.nb{{padding:15px;font-size:1.3em;font-weight:bold;border:none;border-radius:10px;background:#e3f2fd;color:#1565c0;cursor:pointer}}.cl{{background:#ffebee;color:#c62828}}.btns{{display:grid;gap:10px}}.btn{{padding:12px;font-size:1em;font-weight:bold;border:none;border-radius:10px;cursor:pointer}}.bc{{background:#e8f5e9;color:#2e7d32}}.br{{background:#fce4ec;color:#c2185b}}.msg{{text-align:center;padding:10px;border-radius:10px;margin-top:10px;font-weight:bold;display:none}}.suc{{background:#c8e6c9;color:#2e7d32;display:block}}.inf{{background:#e3f2fd;color:#1565c0;display:block}}.save{{text-align:center;color:#666;font-size:.8em;margin-top:10px}}</style></head><body><div class="c"><h1>Sudoku</h1><div class="d">{d}</div><div class="g" id="g"></div><div class="np"><button class="nb" onclick="en(1)">1</button><button class="nb" onclick="en(2)">2</button><button class="nb" onclick="en(3)">3</button><button class="nb" onclick="en(4)">4</button><button class="nb" onclick="en(5)">5</button><button class="nb" onclick="en(6)">6</button><button class="nb" onclick="en(7)">7</button><button class="nb" onclick="en(8)">8</button><button class="nb" onclick="en(9)">9</button><button class="nb cl" onclick="en(0)">X</button></div><div class="btns"><button class="btn bc" onclick="chk()">Controleer</button><button class="btn br" onclick="clr()">Reset</button></div><div class="msg" id="m"></div><div class="save" id="sv">Voortgang opgeslagen</div></div><script>var p={json.dumps(p)},s={json.dumps(s)},k="sudoku_{d}";var u=load(),sc=null;function load(){{try{{var d=JSON.parse(localStorage.getItem(k));document.getElementById("sv").textContent="Hersteld van "+d.time;return d.grid}}catch(e){{}}return p.map(r=>r.slice())}function save(){{var n=new Date(),t=n.getHours()+":"+(n.getMinutes()<10?"0":"")+n.getMinutes();localStorage.setItem(k,JSON.stringify({grid:u,time:t}));document.getElementById("sv").textContent="Opgeslagen "+t}}function cg(){{var g=document.getElementById("g");g.innerHTML="";for(var r=0;r<9;r++)for(var c=0;c<9;c++){{var e=document.createElement("div");e.className="cell";if(p[r][c]!=0){{e.classList.add("fx");e.textContent=p[r][c]}}else{{e.classList.add("ed");if(u[r][c]!=0)e.textContent=u[r][c];e.onclick=((rr,cc)=>()=>{{sc={r:rr,c:cc};cg();sl(rr,cc)}})(r,c)}}g.appendChild(e)}}if(sc)document.querySelectorAll(".cell")[sc.r*9+sc.c].classList.add("sel")}}function sl(r,c){{sc={r:r,c:c};document.querySelectorAll(".cell").forEach(e=>e.classList.remove("sel"));document.querySelectorAll(".cell")[r*9+c].classList.add("sel")}}function en(n){{if(!sc)return;var r=sc.r,c=sc.c;if(p[r][c]!=0)return;u[r][c]=n;save();cg();sl(r,c);var e=document.querySelectorAll(".cell")[r*9+c];if(n!=0&&n!=s[r][c])e.classList.add("err");else if(n!=0)e.classList.add("ok")}}function chk(){{var c=0,t=0;for(var r=0;r<9;r++)for(var cl=0;cl<9;cl++)if(p[r][cl]==0){{t++;if(u[r][cl]==s[r][cl])c++}}var m=document.getElementById("m");if(c==t){{m.className="msg suc";m.textContent="Gefeliciteerd!"}}else{{m.className="msg inf";m.textContent=c+" van "+t+" goed"}}}}function clr(){{u=p.map(r=>r.slice());save();cg();document.getElementById("m").className="msg inf";document.getElementById("m").textContent="Reset!"}}cg();</script></body></html>"""

def send(msg):
    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    print("Verstuurd" if r.json().get("ok") else f"Fout: {r.json()}")

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== Sudoku {today} ===")

    # Oplossing van gisteren
    if os.path.exists(SOLUTION_FILE):
        with open(SOLUTION_FILE) as f: d = json.load(f)
        send(f"*Oplossing {d.get('date','gisteren')}:*\n\n```
{fmt_sol(d.get('solution',[]))}
```")

    # Start tunnel
    stop_tunnels()
    start_server()
    url = start_tunnel()
    if not url:
        send("FOUT: Geen tunnel!")
        return

    # Maak sudoku
    p, s = make_sudoku()
    with open(SUDOKU_FILE, "w") as f: f.write(make_html(p, s, today))
    with open(SOLUTION_FILE, "w") as f: json.dump({"date": today, "solution": s}, f)

    # Stuur link
    send(f"*Sudoku {today}*\n\n[Open in Safari]({url}/sudoku.html)\n\nVeel plezier!")
    print(f"=== Klaar: {url}/sudoku.html ===")

if __name__ == "__main__":
    main()
