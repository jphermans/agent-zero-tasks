# E-Ink Dashboard for Raspberry Pi

A multi-view dashboard for the **Pimoroni Inky Impression 7.3"** (PIM773) e-ink display.
Shows clock, calendar, weather, tasks, email, smart home status, and crypto prices on a beautiful 800x480 six-color display.

![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%2F5-green)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Display](https://img.shields.io/badge/Display-Inky%20Impression%207.3%22-orange)

## Features

- **7 switchable views** with button navigation
- **Auto-refresh** every 15 minutes (configurable)
- **Kiosk mode** - auto-cycle through all views
- **Offline fallback** - cached data when APIs are down
- **Simulation mode** - develop without hardware
- **Systemd service** - runs automatically on boot

## Dashboard Views

| # | View | Source | API Required |
|---|------|--------|-------------|
| 0 | Clock & Date | System clock | None |
| 1 | Calendar | Google Calendar API | Google OAuth |
| 2 | Weather | OpenWeatherMap | Free API key |
| 3 | Tasks | Local JSON file | None |
| 4 | Email | IMAP | Email credentials |
| 5 | Smart Home | Home Assistant REST API | HA URL + token |
| 6 | Finance | CoinGecko | None (free) |

## Button Controls

| Button | Action |
|--------|--------|
| A | Previous view |
| B | Next view |
| C | Force refresh |
| D | Toggle kiosk mode |

## Hardware Requirements

- Raspberry Pi 4 or 5 (Pi 3 works but slower refresh)
- [Pimoroni Inky Impression 7.3"](https://shop.pimoroni.com/products/inky-impression-7-3) (PIM773)
- SPI enabled on Raspberry Pi
- 4 side-mount buttons (built into Inky Impression)

## Quick Start

### 1. Hardware Setup

Connect the Inky Impression to your Raspberry Pi:
- Plug the Inky directly onto the GPIO header
- Ensure SPI is enabled: `sudo raspi-config` > Interface Options > SPI > Enable

### 2. Software Installation

```bash
# Clone the repository
git clone <your-repo-url> eink-dashboard
cd eink-dashboard

# Run the setup script
chmod +x install.sh
./install.sh
```

Or install manually:

```bash
# Install system packages
sudo apt-get update
sudo apt-get install python3-pip python3-venv python3-pil fonts-dejavu-core

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# For Raspberry Pi hardware support:
pip install inky gpiozero
```

### 3. Configuration

```bash
# Copy the example config
cp config.example.yaml config.yaml

# Edit with your settings
nano config.yaml
```

### 4. Run

```bash
# Simulation mode (no hardware needed, saves images to cache/)
python main.py -s -r

# Run on Raspberry Pi with display
python main.py

# Start in kiosk mode
python main.py -k

# Start on a specific view
python main.py -v 2

# Debug mode
python main.py -l DEBUG
```

## API Setup Guides

### Weather (OpenWeatherMap)

1. Sign up at [openweathermap.org](https://openweathermap.org/)
2. Go to API Keys and generate a free key
3. Add to `config.yaml`:
   ```yaml
   weather:
     enabled: true
     api_key: "your-api-key-here"
     location: "YourCity,CountryCode"
     units: "metric"
   ```

### Google Calendar

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Calendar API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the credentials JSON file
6. Save as `credentials.json` in the project directory
7. First run will open a browser for authorization
8. Token is saved automatically for future use

```yaml
google:
  enabled: true
  credentials_file: "credentials.json"
```

### Email (IMAP)

#### Gmail
1. Enable 2-Factor Authentication
2. Generate an App Password: Google Account > Security > App passwords
3. Enable IMAP in Gmail settings

#### Fastmail / Other
1. Generate an app-specific password in your provider settings
2. Note the IMAP server address

```yaml
email:
  enabled: true
  server: "imap.gmail.com"
  port: 993
  user: "your-email@gmail.com"
  password: "your-app-password"
```

### Home Assistant

1. Open Home Assistant
2. Go to Profile > Security > Long-Lived Access Tokens
3. Create a new token
4. Add your entity IDs:

```yaml
homeassistant:
  enabled: true
  url: "http://homeassistant.local:8123"
  token: "your-long-lived-token"
  entities:
    - "sensor.living_room_temperature"
    - "sensor.outdoor_humidity"
    - "light.living_room"
```

### Finance / Crypto

No setup needed! Uses the free CoinGecko API.

```yaml
finance:
  enabled: true
  coins:
    - "bitcoin"
    - "ethereum"
    - "solana"
  currency: "usd"
```

## Running as a Service

The install script can set this up automatically, or manually:

```bash
# Create systemd service
sudo tee /etc/systemd/system/eink-dashboard.service << EOF
[Unit]
Description=E-Ink Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/eink-dashboard
ExecStart=/home/pi/eink-dashboard/venv/bin/python main.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable eink-dashboard
sudo systemctl start eink-dashboard

# Check status
sudo systemctl status eink-dashboard

# View logs
journalctl -u eink-dashboard -f
```

## Project Structure

```
eink-dashboard/
├── main.py              # Entry point
├── display.py           # Display manager, buttons, view switching
├── renderer.py          # Base rendering utilities
├── config.yaml          # Your configuration (gitignored)
├── config.example.yaml  # Configuration template
├── requirements.txt     # Python dependencies
├── install.sh           # Setup script
├── views/
│   ├── clock.py         # Clock & date view
│   ├── calendar.py      # Google Calendar view
│   ├── weather.py       # Weather forecast view
│   ├── tasks.py         # Task list view
│   ├── email.py         # Email overview view
│   ├── home.py          # Home Assistant view
│   └── finance.py       # Crypto/finance view
├── services/
│   ├── google_cal.py    # Google Calendar API
│   ├── weather.py       # OpenWeatherMap API
│   ├── imap_email.py    # IMAP email service
│   ├── homeassistant.py # Home Assistant API
│   └── crypto.py        # CoinGecko API
├── fonts/               # Custom fonts (optional)
├── icons/               # Weather/status icons
└── cache/               # Cached API responses + logs
```

## Development

### Simulation Mode

Develop and test without any hardware:

```bash
python main.py -s -r   # Render all views to PNG files
python main.py -s       # Run in simulation mode
```

Images are saved to `cache/simulation_output.png` and individual view PNGs.

### Adding a New View

1. Create a new file in `views/` with a class that has a `render()` method:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from renderer import create_canvas, draw_header, draw_footer, get_font
from PIL import Image

class MyView:
    def __init__(self, config, service=None):
        self.config = config
        self.service = service

    def render(self) -> Image.Image:
        img, draw = create_canvas()
        draw_header(draw, "My View")
        # ... draw your content ...
        draw_footer(draw)
        return img
```

2. Register it in `views/__init__.py` and `main.py`

## Troubleshooting

### Display not detected
- Check SPI is enabled: `ls /dev/spidev*`
- Check Inky is seated properly on GPIO header
- Try: `python -c "from inky.auto import auto; print(auto())"`

### Buttons not responding
- Verify gpiozero is installed: `pip install gpiozero`
- Check GPIO pins are not in use by another service

### Fonts look wrong
- Install DejaVu fonts: `sudo apt install fonts-dejavu-core`
- Or place TTF files in the `fonts/` directory

### API errors
- Check your API keys in `config.yaml`
- Cached data will be used as fallback
- Check logs: `cache/dashboard.log`

## License

MIT License - see LICENSE file.
