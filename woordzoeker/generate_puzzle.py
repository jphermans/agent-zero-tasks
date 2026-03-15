#!/usr/bin/env python3
"""
Dagelijkse Woordzoeker Generator met woord tracking
"""

import random
import json
import os
from datetime import datetime

# Uitgebreide Nederlandse woorden lijsten per thema
WORD_LISTS = {
    "eten": ["APPEL", "BANAAN", "KERS", "PEER", "MELK", "KAAS", "BROOD", "BOTER", "THEE", "KOFFIE", "SAP", "EI", "SOEP", "RUST", "PASTA", "PIZZA", "TAART", "KOEK", "CHIPS", "SNOEP", "STEAK", "SALADE", "FRUIT", "NOTEN"],
    "dieren": ["HOND", "KAT", "PAARD", "KOE", "VARKEN", "SCHAAP", "KIP", "EEND", "GANS", "HAAN", "KONIJN", "MUIS", "RAT", "LEEUW", "TIIGER", "OLIFANT", "AAP", "BEER", "WOLF", "VOS", "HAAS", "EIKHOORN", "UIL", "ZWAAN"],
    "natuur": ["BOOM", "BOS", "BERG", "RIVIER", "MEER", "ZEE", "STRAND", "DUIN", "WOLK", "REGEN", "SNEEUW", "WIND", "ZON", "MAAN", "STER", "HEIDE", "WEIDE", "AKKER", "TUIN", "PARK", "ROTS", "VALLEI", "EILAND", "WOESTIJN"],
    "huis": ["KAMER", "KEUKEN", "SLAAPKAMER", "ZOLDER", "KELDER", "DAK", "MUUR", "VLOER", "DEUR", "RAAM", "TAFEL", "STOEL", "BANK", "BED", "KAST", "LAMP", "SPIEGEL", "KLOK", "TAPIJT", "VAAS", "SCHILDRIJ", "GORDIJN"],
    "school": ["PEN", "POTLOOD", "GOM", "LINIAAL", "SCHAAR", "LIJM", "PAPIER", "SCHRIFT", "BOEK", "ATLAS", "KAART", "BORD", "KRIJT", "LODSS", "TAS", "LES", "KLAS", "BAAN", "STUDIE", "TOETS", "LERAAR", "LEERLING"],
    "kleding": ["BROEK", "HEMD", "TRUI", "JAS", "ROK", "JURK", "SOK", "SCHOEN", "LAARS", "PET", "HOED", "SJAAL", "HANDSCHOEN", "RIEM", "DAS", "VEST", "MANTEL", "PONCHO", "SLIP", "MOUW", "KRAAG", "ZAK"],
    "vervoer": ["AUTO", "FIETS", "BUS", "TRAM", "TREIN", "VLIEGTUIG", "BOOT", "SCHIP", "VRACHT", "MOTOR", "SCOOTER", "STEP", "SKATE", "WAGEN", "KAR", "SLEE", "HELICOPTER", "RAKET", "DUIKBOOT", "ZEIL", "FIETS", "BROMMER"],
    "kleuren": ["ROOD", "BLAUW", "GEEL", "GROEN", "ORANJE", "PAARS", "ROZE", "BRUIN", "ZWART", "WIT", "GRIJS", "GOUD", "ZILVER", "BEIGE", "CREME", "MINT", "OKER", "TURKOOIS", "INDIGO", "KARMJN", "LILA", "ROOD"],
    "weer": ["REGEN", "SNEEUW", "HAGEL", "ONWEER", "BUI", "MIST", "WIND", "STORM", "ZON", "WOLK", "VOCHT", "DOOI", "VORST", "WARMTE", "KOELTE", "DROOGTE", "NEERSLAG", "STRAAL", "DONDER", "BLIKSEM", "REGENBOOG"],
    "sport": ["VOETBAL", "HOCKEY", "TENNIS", "ZWEMMEN", "HARDLOPEN", "FIETS", "SKI", "SCHAATS", "TURNEN", "JUDO", "BOKSEN", "WORSTELEN", "VOLLEYBAL", "BADMINTON", "GOLF", "RUGBY", "BASKETBAL", "HANDBAL", "TAFELTENNIS", "ATLETIEK", "ZWEFVLIEG", "DUIKEN"]
}

GRID_SIZE = 12
USED_WORDS_FILE = "/a0/usr/projects/task_script/woordzoeker/used_words.json"

def load_used_words():
    """Laad lijst van eerder gebruikte woorden"""
    if os.path.exists(USED_WORDS_FILE):
        try:
            with open(USED_WORDS_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_used_words(used_words):
    """Bewaar lijst van gebruikte woorden"""
    with open(USED_WORDS_FILE, 'w') as f:
        json.dump(list(used_words), f)

def get_all_words():
    """Krijg alle woorden uit alle thema's"""
    all_words = []
    for theme_words in WORD_LISTS.values():
        all_words.extend(theme_words)
    return list(set(all_words))  # Verwijder duplicaten

def select_words_for_today(used_words, count=10):
    """Selecteer woorden voor vandaag, met voorkeur voor ongebruikte woorden"""
    all_words = get_all_words()
    
    # Filter naar ongebruikte woorden
    unused_words = [w for w in all_words if w not in used_words]
    
    # Als er niet genoeg ongebruikte woorden zijn, reset de lijst deels
    if len(unused_words) < count:
        print(f"Niet genoeg nieuwe woorden ({len(unused_words)}), reset lijst...")
        # Houd laatste 20 woorden, reset de rest
        recent_words = list(used_words)[-20:] if len(used_words) > 20 else list(used_words)
        used_words = set(recent_words)
        unused_words = [w for w in all_words if w not in used_words]
    
    # Selecteer willekeurig uit ongebruikte woorden
    today = datetime.now().strftime("%Y-%m-%d")
    seed = hash(today) % (10 ** 8)
    random.seed(seed)
    
    selected = random.sample(unused_words, min(count, len(unused_words)))
    
    # Update gebruikte woorden
    used_words.update(selected)
    save_used_words(used_words)
    
    return selected, seed, today

def create_grid(words):
    """Maak de grid en plaats woorden"""
    grid = [['' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    placed_words = {}
    
    directions = [(1, 0), (0, 1), (1, 1), (1, -1), (-1, 0), (0, -1), (-1, -1), (-1, 1)]
    
    # Sorteer woorden op lengte (langste eerst)
    words_sorted = sorted(words, key=len, reverse=True)
    
    for word in words_sorted:
        placed = False
        attempts = 0
        while not placed and attempts < 200:
            dx, dy = random.choice(directions)
            start_x = random.randint(0, GRID_SIZE - 1)
            start_y = random.randint(0, GRID_SIZE - 1)
            if can_place(grid, word, start_x, start_y, dx, dy):
                positions = place_word(grid, word, start_x, start_y, dx, dy)
                placed_words[word] = positions
                placed = True
            attempts += 1
        
        if not placed:
            print(f"WAARSCHUWING: Kon '{word}' niet plaatsen!")
    
    # Vul lege cellen
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            if grid[i][j] == '':
                grid[i][j] = random.choice(letters)
    
    return grid, placed_words

def can_place(grid, word, start_x, start_y, dx, dy):
    for i, letter in enumerate(word):
        x = start_x + i * dx
        y = start_y + i * dy
        if x < 0 or x >= GRID_SIZE or y < 0 or y >= GRID_SIZE:
            return False
        if grid[y][x] != '' and grid[y][x] != letter:
            return False
    return True

def place_word(grid, word, start_x, start_y, dx, dy):
    positions = []
    for i, letter in enumerate(word):
        x = start_x + i * dx
        y = start_y + i * dy
        grid[y][x] = letter
        positions.append({"x": x, "y": y})
    return positions

def generate_html(words, grid, placed_words, date_str):
    grid_json = json.dumps(grid)
    words_json = json.dumps(words)
    placed_json = json.dumps(placed_words)
    
    html = f'''<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Woordzoeker - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 20px; padding: 30px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }}
        h1 {{ text-align: center; color: #333; margin-bottom: 10px; font-size: 2.5em; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; font-size: 1.1em; }}
        .date-badge {{ display: inline-block; background: #667eea; color: white; padding: 5px 15px; border-radius: 15px; font-size: 0.9em; }}
        .game-area {{ display: flex; flex-wrap: wrap; gap: 30px; justify-content: center; }}
        .grid-container {{ flex: 1; min-width: 300px; max-width: 500px; }}
        #grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 2px; background: #e0e0e0; padding: 10px; border-radius: 10px; user-select: none; }}
        .cell {{ aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-size: 1.2em; font-weight: bold; background: white; border-radius: 5px; cursor: pointer; transition: all 0.2s; text-transform: uppercase; }}
        .cell:hover {{ background: #e8f4fd; transform: scale(1.05); }}
        .cell.selected {{ background: #ffd700; color: #333; }}
        .cell.found {{ background: #4CAF50; color: white; }}
        .words-container {{ flex: 0 0 250px; background: #f5f5f5; padding: 20px; border-radius: 10px; }}
        .words-title {{ font-size: 1.3em; color: #333; margin-bottom: 15px; text-align: center; }}
        .words-list {{ list-style: none; display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
        .word-item {{ padding: 8px 12px; background: white; border-radius: 5px; font-weight: 500; text-transform: uppercase; font-size: 0.9em; transition: all 0.3s; text-align: center; }}
        .word-item.found {{ text-decoration: line-through; background: #c8e6c9; color: #2e7d32; }}
        .controls {{ margin-top: 30px; display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }}
        button {{ padding: 12px 30px; font-size: 1.1em; border: none; border-radius: 25px; cursor: pointer; transition: all 0.3s; font-weight: 600; }}
        .btn-secondary {{ background: #f5f5f5; color: #333; }}
        .score {{ text-align: center; margin-top: 20px; font-size: 1.2em; color: #333; }}
        .score span {{ font-weight: bold; color: #667eea; }}
        .message {{ text-align: center; margin-top: 20px; padding: 15px; border-radius: 10px; font-weight: 600; display: none; }}
        .message.success {{ background: #c8e6c9; color: #2e7d32; display: block; }}
        .instructions {{ background: #fff3e0; padding: 15px; border-radius: 10px; margin-bottom: 20px; font-size: 0.95em; color: #e65100; }}
        .progress-info {{ text-align: center; margin-top: 10px; font-size: 0.85em; color: #888; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Woordzoeker</h1>
        <p class="subtitle">Vind alle 10 Nederlandse woorden! <span class="date-badge">{date_str}</span></p>
        <div class="instructions"><strong>Instructies:</strong> Klik en sleep over letters om woorden te selecteren. Woorden kunnen horizontaal, verticaal en diagonaal verborgen zijn.<br><strong>✨ Je voortgang wordt automatisch bewaard!</strong></div>
        <div class="game-area">
            <div class="grid-container"><div id="grid"></div></div>
            <div class="words-container"><h3 class="words-title">📝 Te zoeken woorden:</h3><ul class="words-list" id="wordsList"></ul></div>
        </div>
        <div class="score">Gevonden: <span id="foundCount">0</span> / <span id="totalCount">0</span> woorden</div>
        <div class="progress-info" id="progressInfo"></div>
        <div class="message" id="message"></div>
        <div class="controls">
            <button class="btn-secondary" onclick="resetProgress()">🔄 Reset Voortgang</button>
            <button class="btn-secondary" onclick="showHint()">💡 Hint</button>
        </div>
    </div>
    <script>
        const GRID_SIZE = 12, STORAGE_KEY = 'woordzoeker_{date_str}';
        const grid = {grid_json}, words = {words_json}, placedWordPositions = {placed_json};
        let foundWords = [], isSelecting = false, selectedCells = [], startCell = null;
        
        console.log('Woorden in deze puzzle:', words);
        console.log('Aantal woorden:', words.length);
        
        function loadProgress() {{ const saved = localStorage.getItem(STORAGE_KEY); if (saved) {{ try {{ const data = JSON.parse(saved); foundWords = data.foundWords || []; return true; }} catch (e) {{ foundWords = []; }} }} return false; }}
        function saveProgress() {{ localStorage.setItem(STORAGE_KEY, JSON.stringify({{ foundWords: foundWords }})); }}
        function resetProgress() {{ if (confirm('Weet je zeker dat je je voortgang wilt resetten?')) {{ localStorage.removeItem(STORAGE_KEY); foundWords = []; renderGrid(); renderWordsList(); updateScore(); document.getElementById('message').className = 'message'; document.getElementById('progressInfo').textContent = ''; }} }}
        function init() {{ loadProgress(); renderGrid(); renderWordsList(); updateScore(); if (foundWords.length > 0) document.getElementById('progressInfo').textContent = '✅ Je hebt al ' + foundWords.length + ' woord(en) gevonden!'; checkWin(); }}
        function renderGrid() {{ const gridElement = document.getElementById('grid'); gridElement.innerHTML = ''; for (let i = 0; i < GRID_SIZE; i++) {{ for (let j = 0; j < GRID_SIZE; j++) {{ const cell = document.createElement('div'); cell.className = 'cell'; cell.textContent = grid[i][j]; cell.dataset.row = i; cell.dataset.col = j; for (const word of foundWords) {{ if (placedWordPositions[word]) {{ for (const pos of placedWordPositions[word]) {{ if (pos.x === j && pos.y === i) cell.classList.add('found'); }} }} }} cell.addEventListener('mousedown', handleMouseDown); cell.addEventListener('mouseenter', handleMouseEnter); cell.addEventListener('touchstart', handleTouchStart, {{passive: false}}); cell.addEventListener('touchmove', handleTouchMove, {{passive: false}}); gridElement.appendChild(cell); }} }} document.addEventListener('mouseup', handleMouseUp); document.addEventListener('touchend', handleTouchEnd); }}
        function renderWordsList() {{ const wordsList = document.getElementById('wordsList'); wordsList.innerHTML = ''; words.forEach(word => {{ const li = document.createElement('li'); li.className = 'word-item' + (foundWords.includes(word) ? ' found' : ''); li.textContent = word; li.id = 'word-' + word; wordsList.appendChild(li); }}); document.getElementById('totalCount').textContent = words.length; }}
        function handleMouseDown(e) {{ isSelecting = true; startCell = {{row: parseInt(e.target.dataset.row), col: parseInt(e.target.dataset.col)}}; selectedCells = [startCell]; updateSelection(); }}
        function handleMouseEnter(e) {{ if (!isSelecting) return; const currentCell = {{row: parseInt(e.target.dataset.row), col: parseInt(e.target.dataset.col)}}; updateSelectedPath(currentCell); }}
        function handleMouseUp() {{ if (!isSelecting) return; isSelecting = false; checkSelection(); }}
        function handleTouchStart(e) {{ e.preventDefault(); const touch = e.touches[0]; const cell = document.elementFromPoint(touch.clientX, touch.clientY); if (cell && cell.classList.contains('cell')) {{ isSelecting = true; startCell = {{row: parseInt(cell.dataset.row), col: parseInt(cell.dataset.col)}}; selectedCells = [startCell]; updateSelection(); }} }}
        function handleTouchMove(e) {{ e.preventDefault(); if (!isSelecting) return; const touch = e.touches[0]; const cell = document.elementFromPoint(touch.clientX, touch.clientY); if (cell && cell.classList.contains('cell')) {{ const currentCell = {{row: parseInt(cell.dataset.row), col: parseInt(cell.dataset.col)}}; updateSelectedPath(currentCell); }} }}
        function handleTouchEnd() {{ if (!isSelecting) return; isSelecting = false; checkSelection(); }}
        function updateSelectedPath(endCell) {{ if (!startCell) return; selectedCells = []; const dx = Math.sign(endCell.col - startCell.col), dy = Math.sign(endCell.row - startCell.row); const colDiff = Math.abs(endCell.col - startCell.col), rowDiff = Math.abs(endCell.row - startCell.row); if (colDiff !== 0 && rowDiff !== 0 && colDiff !== rowDiff) return; const steps = Math.max(colDiff, rowDiff); for (let i = 0; i <= steps; i++) selectedCells.push({{ row: startCell.row + i * dy, col: startCell.col + i * dx }}); updateSelection(); }}
        function updateSelection() {{ document.querySelectorAll('.cell').forEach(cell => {{ if (!cell.classList.contains('found')) cell.classList.remove('selected'); }}); selectedCells.forEach(pos => {{ const cell = document.querySelector('.cell[data-row="' + pos.row + '"][data-col="' + pos.col + '"]'); if (cell && !cell.classList.contains('found')) cell.classList.add('selected'); }}); }}
        function checkSelection() {{ const selectedWord = selectedCells.map(pos => grid[pos.row][pos.col]).join(''); const reversedWord = selectedWord.split('').reverse().join(''); let foundWord = null; if (words.includes(selectedWord) && !foundWords.includes(selectedWord)) foundWord = selectedWord; else if (words.includes(reversedWord) && !foundWords.includes(reversedWord)) foundWord = reversedWord; if (foundWord) {{ foundWords.push(foundWord); saveProgress(); markWordAsFound(foundWord); updateScore(); checkWin(); }} selectedCells = []; document.querySelectorAll('.cell.selected').forEach(cell => cell.classList.remove('selected')); }}
        function markWordAsFound(word) {{ const positions = placedWordPositions[word]; if (positions) {{ positions.forEach(pos => {{ const cell = document.querySelector('.cell[data-row="' + pos.y + '"][data-col="' + pos.x + '"]'); if (cell) {{ cell.classList.add('found'); cell.classList.remove('selected'); }} }}); }} const wordItem = document.getElementById('word-' + word); if (wordItem) wordItem.classList.add('found'); document.getElementById('progressInfo').textContent = '✅ Voortgang bewaard!'; }}
        function updateScore() {{ document.getElementById('foundCount').textContent = foundWords.length; }}
        function checkWin() {{ console.log('Checking win:', foundWords.length, '/', words.length); if (foundWords.length === words.length && words.length > 0) {{ const message = document.getElementById('message'); message.textContent = '🎉 Gefeliciteerd! Je hebt alle ' + words.length + ' woorden gevonden!'; message.className = 'message success'; }} }}
        function showHint() {{ const unFoundWords = words.filter(w => !foundWords.includes(w)); if (unFoundWords.length > 0) {{ const hintWord = unFoundWords[0]; const positions = placedWordPositions[hintWord]; if (positions && positions.length > 0) {{ const firstPos = positions[0]; const cell = document.querySelector('.cell[data-row="' + firstPos.y + '"][data-col="' + firstPos.x + '"]'); if (cell) {{ cell.style.background = '#ff9800'; setTimeout(() => {{ if (!cell.classList.contains('found')) cell.style.background = ''; }}, 2000); }} }} }} }}
        init();
    </script>
</body>
</html>'''
    return html

if __name__ == "__main__":
    used_words = load_used_words()
    words, seed, date_str = select_words_for_today(used_words, 10)
    print(f"Geselecteerde woorden voor {date_str}: {words}")
    print(f"Aantal woorden: {len(words)}")
    
    grid, placed_words = create_grid(words)
    html = generate_html(words, grid, placed_words, date_str)
    
    with open('/a0/usr/projects/task_script/woordzoeker/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ Nieuwe woordzoeker gegenereerd voor {date_str}")
    print(f"📝 Woorden: {', '.join(words)}")
