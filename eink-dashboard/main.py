#!/usr/bin/env python3
"""
E-Ink Dashboard - Main entry point for Raspberry Pi with Pimoroni Inky Impression 7.3"

Usage:
    python main.py                 # Run with default config
    python main.py -c config.yaml  # Specify config file
    python main.py -s              # Simulation mode (no hardware)
    python main.py -v 2            # Start on view index 2
"""

import argparse
import logging
import os
import signal
import sys
import time

import yaml

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def setup_logging(level: str = "INFO"):
    """Configure logging for the application."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Also log to file
    log_dir = os.path.join(PROJECT_ROOT, "cache")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(log_dir, "dashboard.log"))
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logging.getLogger().addHandler(file_handler)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        logger = logging.getLogger(__name__)
        logger.warning(f"Config file not found: {config_path}")
        logger.info("Using default configuration")
        return get_default_config()
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}
    
    # Merge with defaults
    defaults = get_default_config()
    merged = deep_merge(defaults, config)
    return merged


def get_default_config() -> dict:
    """Get default configuration values."""
    return {
        "refresh_interval": 900,  # 15 minutes
        "kiosk_interval": 30,     # 30 seconds per view in kiosk mode
        "default_view": 0,
        "simulation": False,
        "weather": {
            "api_key": "",
            "location": "London,UK",
            "units": "metric",
            "enabled": True,
        },
        "google": {
            "credentials_file": "credentials.json",
            "token_file": "token.json",
            "enabled": False,
        },
        "email": {
            "server": "",
            "port": 993,
            "user": "",
            "password": "",
            "enabled": False,
        },
        "homeassistant": {
            "url": "",
            "token": "",
            "entities": [],
            "enabled": False,
        },
        "finance": {
            "coins": ["bitcoin", "ethereum"],
            "currency": "usd",
            "enabled": True,
        },
        "tasks_file": "tasks.json",
    }


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries. Override values take precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def create_views(config: dict) -> list:
    """Create and return all view instances based on config."""
    from views import (
        ClockView,
        CalendarView,
        WeatherView,
        TasksView,
        EmailView,
        HomeView,
        FinanceView,
    )
    
    # Initialize services
    services = create_services(config)
    
    views = [
        ClockView(config),
        CalendarView(config, services.get("calendar")),
        WeatherView(config, services.get("weather")),
        TasksView(config),
        EmailView(config, services.get("email")),
        HomeView(config, services.get("homeassistant")),
        FinanceView(config, services.get("crypto")),
    ]
    
    return views


def create_services(config: dict) -> dict:
    """Initialize and return service instances."""
    services = {}
    logger = logging.getLogger(__name__)
    
    # Weather service
    if config.get("weather", {}).get("enabled") and config.get("weather", {}).get("api_key"):
        try:
            from services.weather import WeatherService
            services["weather"] = WeatherService(config)
            logger.info("Weather service initialized")
        except Exception as e:
            logger.error(f"Failed to init weather service: {e}")
    else:
        logger.info("Weather service disabled or no API key")
    
    # Google Calendar service
    if config.get("google", {}).get("enabled"):
        try:
            from services.google_cal import GoogleCalendarService
            services["calendar"] = GoogleCalendarService(config)
            logger.info("Calendar service initialized")
        except Exception as e:
            logger.error(f"Failed to init calendar service: {e}")
    else:
        logger.info("Calendar service disabled")
    
    # Email service
    email_cfg = config.get("email", {})
    if email_cfg.get("enabled") and email_cfg.get("server") and email_cfg.get("user"):
        try:
            from services.imap_email import EmailService
            services["email"] = EmailService(config)
            logger.info("Email service initialized")
        except Exception as e:
            logger.error(f"Failed to init email service: {e}")
    else:
        logger.info("Email service disabled")
    
    # Home Assistant service
    ha_cfg = config.get("homeassistant", {})
    if ha_cfg.get("enabled") and ha_cfg.get("url") and ha_cfg.get("token"):
        try:
            from services.homeassistant import HomeAssistantService
            services["homeassistant"] = HomeAssistantService(config)
            logger.info("Home Assistant service initialized")
        except Exception as e:
            logger.error(f"Failed to init HA service: {e}")
    else:
        logger.info("Home Assistant service disabled")
    
    # Crypto service
    if config.get("finance", {}).get("enabled", True):
        try:
            from services.crypto import CryptoService
            services["crypto"] = CryptoService(config)
            logger.info("Crypto service initialized")
        except Exception as e:
            logger.error(f"Failed to init crypto service: {e}")
    else:
        logger.info("Finance service disabled")
    
    return services


def create_sample_tasks(config: dict):
    """Create a sample tasks.json if missing."""
    tasks_file = os.path.join(PROJECT_ROOT, config.get("tasks_file", "tasks.json"))
    if not os.path.exists(tasks_file):
        import json
        sample_tasks = [
            {"text": "Set up e-ink dashboard", "done": True, "priority": "high"},
            {"text": "Configure weather API key", "done": False, "priority": "high"},
            {"text": "Add Google Calendar credentials", "done": False, "priority": "medium"},
            {"text": "Set up IMAP email access", "done": False, "priority": "medium"},
            {"text": "Connect Home Assistant", "done": False, "priority": "low"},
            {"text": "Customize dashboard layout", "done": False, "priority": "low"},
        ]
        with open(tasks_file, "w") as f:
            json.dump(sample_tasks, f, indent=2)
        logging.getLogger(__name__).info(f"Created sample tasks file: {tasks_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="E-Ink Dashboard for Raspberry Pi with Inky Impression 7.3"
    )
    parser.add_argument(
        "-c", "--config",
        default=os.path.join(PROJECT_ROOT, "config.yaml"),
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "-s", "--simulation",
        action="store_true",
        help="Force simulation mode (no hardware required)",
    )
    parser.add_argument(
        "-v", "--view",
        type=int,
        default=None,
        help="Start on specific view index (0-6)",
    )
    parser.add_argument(
        "-k", "--kiosk",
        action="store_true",
        help="Start in kiosk mode (auto-cycle views)",
    )
    parser.add_argument(
        "-l", "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "-r", "--render-once",
        action="store_true",
        help="Render all views once and exit (for testing)",
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("E-Ink Dashboard Starting")
    logger.info("=" * 50)

    # Load configuration
    config = load_config(args.config)
    
    # Force simulation mode if requested
    if args.simulation:
        config["simulation"] = True
        logger.info("Simulation mode forced via command line")

    # Ensure cache directory exists
    os.makedirs(os.path.join(PROJECT_ROOT, "cache"), exist_ok=True)

    # Create sample tasks if needed
    create_sample_tasks(config)

    # Create views
    logger.info("Initializing views...")
    views = create_views(config)
    logger.info(f"Created {len(views)} views")

    # Render-once mode for testing
    if args.render_once:
        logger.info("Render-once mode: rendering all views")
        for i, view in enumerate(views):
            try:
                img = view.render()
                out_path = os.path.join(
                    PROJECT_ROOT, "cache", f"view_{i}_{type(view).__name__}.png"
                )
                img.save(out_path)
                logger.info(f"  View {i} ({type(view).__name__}) -> {out_path}")
            except Exception as e:
                logger.error(f"  View {i} ({type(view).__name__}) failed: {e}")
        logger.info("All views rendered. Exiting.")
        return

    # Create display manager
    from display import DisplayManager
    dm = DisplayManager(views, config)

    # Set initial view
    if args.view is not None:
        dm.switch_to(args.view)
    elif config.get("default_view", 0) != 0:
        dm.switch_to(config["default_view"])

    # Enable kiosk mode if requested
    if args.kiosk:
        dm.kiosk_mode = True
        dm._start_kiosk_timer()
        logger.info("Kiosk mode enabled via command line")

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        dm.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Log status
    status = dm.get_status()
    logger.info(f"Display: {'Inky' if status['inky_available'] else 'Simulation'}")
    logger.info(f"Buttons: {status['buttons_available']}")
    logger.info(f"Views: {status['total_views']}")
    logger.info(f"Refresh interval: {status['refresh_interval']}s")

    # Run main loop
    logger.info("Starting dashboard...")
    try:
        dm.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
