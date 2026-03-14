#!/usr/bin/env python3
"""Dagelijkse Sudoku Generator - Stuurt elke dag een nieuwe sudoku via Telegram"""

import json
import random
import requests
from datetime import datetime
import os

# Config
BOT_TOKEN = "8503543419:AAEegQ4TY-RM3U9zHphjyXZVMsTCd5QMcLQ"
CHAT_ID = "365354820"
BASE_DIR = "/a0/usr/workdir/sudoku_data"
SUDOKU_FILE = f"{BASE_DIR}/sudoku.html"  # Nu maar één bestand!
SOLUTION_FILE = f"{BASE_DIR}/latest_solution.json"
TEMPLATE_FILE = f"{BASE_DIR}/sudoku_template.html"
TUNNEL_URL_FILE = f"{BASE_DIR}/tunnel_url.txt"

def generate_sudoku(difficulty='easy'):
    """Genereer een sudoku puzzle en oplossing"""
    def is_valid(board, row, col, num):
        for i in range(9):
            if board[row][i] == num or board[i][col] == num:
                return False
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if board[i][j] == num:
                    return False
        return True

    def solve(board):
        for i in range(9):
            for j in range(9):
                if board[i][j] == 0:
                    for num in range(1, 10):
                        if is_valid(board, i, j, num):
                            board[i][j] = num
                            if solve(board):
                                return True
                            board[i][j] = 0
                    return False
        return True

    board = [[0] * 9 for _ in range(9)]
    solve(board)

    solution = [row[:] for row in board]

    cells_to_remove = 35 if difficulty == 'easy' else 45
    positions = [(i, j) for i in range(9) for j in range(9)]
    random.shuffle(positions)

    for i, j in positions[:cells_to_remove]:
        board[i][j] = 0

    return board, solution

def format_solution_text(solution):
    """Format de oplossing als tekst"""
    lines = []
    lines.append("┌─────┬─────┬─────┐")
    for i, row in enumerate(solution):
        if i == 3 or i == 6:
            lines.append("├─────┼─────┼─────┤")
        line = "│"
        for j, num in enumerate(row):
            if j == 3 or j == 6:
                line += " │"
            line += f" {num}"
        line += " │"
        lines.append(line)
    lines.append("└─────┴─────┴─────┘")
    return "
".join(lines)

def main():
    today = datetime.now().strftime("%Y-%m-%d")

    # Lees tunnel URL
    tunnel_url = ""
    if os.path.exists(TUNNEL_URL_FILE):
        with open(TUNNEL_URL_FILE, 'r') as f:
            tunnel_url = f.read().strip()

    # Stap 1: Stuur oplossing van gisteren indien beschikbaar
    if os.path.exists(SOLUTION_FILE):
        with open(SOLUTION_FILE, 'r') as f:
            data = json.load(f)
        yesterday = data.get('date', 'gisteren')
        solution = data.get('solution', [])

        solution_text = format_solution_text(solution)
        msg = f"📋 **Oplossing van {yesterday}:**

```
{solution_text}
```"

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
        print(f"Oplossing van {yesterday} verstuurd")

    # Stap 2: Genereer nieuwe sudoku
    puzzle, solution = generate_sudoku()

    # Lees template en maak HTML
    with open(TEMPLATE_FILE, 'r') as f:
        template = f.read()

    html_content = template.replace('{{PUZZLE}}', json.dumps(puzzle))
    html_content = html_content.replace('{{SOLUTION}}', json.dumps(solution))
    html_content = html_content.replace('{{DATE}}', today)

    # Overschrijf het sudoku.html bestand
    with open(SUDOKU_FILE, 'w') as f:
        f.write(html_content)
    print(f"Nieuwe sudoku opgeslagen: {SUDOKU_FILE}")

    # Stap 3: Bewaar oplossing voor morgen
    with open(SOLUTION_FILE, 'w') as f:
        json.dump({"date": today, "solution": solution}, f)
    print("Oplossing bewaard voor morgen")

    # Stap 4: Stuur nieuwe sudoku link
    if tunnel_url:
        sudoku_url = f"{tunnel_url}/sudoku.html"
        msg = f"🧩 **Sudoku van {today}**

📱 [Open in Safari]({sudoku_url})

✨ Je kunt direct invullen op je iPhone!"

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
        print(f"Nieuwe sudoku link verstuurd: {sudoku_url}")
    else:
        print("Waarschuwing: Geen tunnel URL bekend")

if __name__ == "__main__":
    main()
