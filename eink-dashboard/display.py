"""
Display manager for the e-ink dashboard.
Handles Inky Impression display output, view switching, button input,
and automatic refresh cycling.
"""

import logging
import time
import threading
from datetime import datetime

from PIL import Image, ImageDraw

from renderer import WIDTH, HEIGHT, COLORS

logger = logging.getLogger(__name__)

INKY_AVAILABLE = False
GPIO_AVAILABLE = False

try:
    from inky.auto import auto as inky_auto
    INKY_AVAILABLE = True
except ImportError:
    pass

try:
    from gpiozero import Button
    GPIO_AVAILABLE = True
except ImportError:
    pass

BUTTON_PINS = {
    "A": 5,
    "B": 6,
    "C": 16,
    "D": 24,
}


class DisplayManager:
    """Manages the e-ink display, views, and button input."""

    def __init__(self, views, config):
        self.views = views
        self.config = config
        self.current_index = 0
        self.kiosk_mode = False
        self.kiosk_interval = config.get("kiosk_interval", 30)
        self.refresh_interval = config.get("refresh_interval", 900)
        self._last_refresh = 0
        self._running = False
        self._buttons = {}
        self._kiosk_timer = None
        self.inky = None
        self._init_display()
        self._init_buttons()

    def _init_display(self):
        if INKY_AVAILABLE:
            try:
                self.inky = inky_auto()
                logger.info(f"Inky display: {self.inky.width}x{self.inky.height}")
            except Exception as e:
                logger.error(f"Inky init failed: {e}")
                self.inky = None
        else:
            logger.info("Simulation mode (no Inky)")

    def _init_buttons(self):
        if GPIO_AVAILABLE:
            try:
                for name, pin in BUTTON_PINS.items():
                    btn = Button(pin, pull_up=True, bounce_time=0.1)
                    btn.when_pressed = lambda n=name: self._on_button(n)
                    self._buttons[name] = btn
                logger.info(f"{len(self._buttons)} buttons initialized")
            except Exception as e:
                logger.error(f"Button init failed: {e}")
        else:
            logger.info("Buttons not available")

    def _on_button(self, button_name):
        logger.info(f"Button {button_name} pressed")
        if button_name == "A":
            self.previous_view()
        elif button_name == "B":
            self.next_view()
        elif button_name == "C":
            self.refresh_current()
        elif button_name == "D":
            self.toggle_kiosk()

    def previous_view(self):
        self.current_index = (self.current_index - 1) % len(self.views)
        logger.info(f"-> View {self.current_index}")
        self.update_display()

    def next_view(self):
        self.current_index = (self.current_index + 1) % len(self.views)
        logger.info(f"-> View {self.current_index}")
        self.update_display()

    def switch_to(self, index):
        if 0 <= index < len(self.views):
            self.current_index = index
            self.update_display()

    def refresh_current(self):
        logger.info("Force refresh")
        self.update_display(force=True)

    def toggle_kiosk(self):
        self.kiosk_mode = not self.kiosk_mode
        logger.info(f"Kiosk: {'ON' if self.kiosk_mode else 'OFF'}")
        if self.kiosk_mode:
            self._start_kiosk_timer()
        else:
            self._stop_kiosk_timer()
        self.update_display()

    def _start_kiosk_timer(self):
        self._stop_kiosk_timer()
        self._kiosk_timer = threading.Timer(self.kiosk_interval, self._kiosk_advance)
        self._kiosk_timer.daemon = True
        self._kiosk_timer.start()

    def _stop_kiosk_timer(self):
        if self._kiosk_timer:
            self._kiosk_timer.cancel()
            self._kiosk_timer = None

    def _kiosk_advance(self):
        if self.kiosk_mode and self._running:
            self.next_view()
            self._start_kiosk_timer()

    def update_display(self, force=False):
        try:
            view = self.views[self.current_index]
            logger.info(f"Rendering: {type(view).__name__}")
            image = view.render()
            if image is None:
                image = self._render_error("View render failed")
            if self.kiosk_mode:
                image = self._add_kiosk_indicator(image)
            self._show_image(image)
            self._last_refresh = time.time()
        except Exception as e:
            logger.error(f"Display error: {e}", exc_info=True)
            self._show_image(self._render_error(str(e)))

    def _show_image(self, image):
        if self.inky is not None:
            try:
                if image.size != (self.inky.width, self.inky.height):
                    image = image.resize((self.inky.width, self.inky.height))
                if image.mode != "RGB":
                    image = image.convert("RGB")
                self.inky.set_image(image, saturation=0.5)
                self.inky.show()
                logger.info("Display updated")
            except Exception as e:
                logger.error(f"Inky error: {e}")
                self._save_simulation(image)
        else:
            self._save_simulation(image)

    def _save_simulation(self, image):
        try:
            sim_path = os.path.join(os.path.dirname(__file__), "cache", "simulation_output.png")
            os.makedirs(os.path.dirname(sim_path), exist_ok=True)
            image.save(sim_path)
            logger.info(f"Saved: {sim_path}")
        except Exception as e:
            logger.error(f"Save error: {e}")

    def _render_error(self, message):
        from renderer import create_canvas, draw_header, draw_centered_text, get_font
        img, draw = create_canvas()
        draw_header(draw, "Error")
        draw_centered_text(draw, "Something went wrong", 120, get_font(24, bold=True))
        draw_centered_text(draw, message[:60], 170, get_font(18))
        draw_centered_text(draw, "Press C to refresh", 220, get_font(18))
        return img

    def _add_kiosk_indicator(self, image):
        from renderer import get_font
        img = image.copy()
        draw = ImageDraw.Draw(img)
        draw.text((WIDTH - 70, 55), "AUTO", fill=COLORS["GREEN"], font=get_font(10))
        return img

    def _auto_refresh_loop(self):
        while self._running:
            elapsed = time.time() - self._last_refresh
            if elapsed >= self.refresh_interval:
                logger.info("Auto-refresh")
                self.update_display(force=True)
            time.sleep(10)

    def run(self):
        self._running = True
        logger.info("Display manager started")
        self.update_display()
        refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
        refresh_thread.start()
        try:
            while self._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.stop()

    def stop(self):
        self._running = False
        self._stop_kiosk_timer()
        logger.info("Stopped")

    def get_status(self):
        from renderer import view_label
        return {
            "current_view": view_label(self.current_index),
            "current_index": self.current_index,
            "total_views": len(self.views),
            "kiosk_mode": self.kiosk_mode,
            "inky_available": self.inky is not None,
            "buttons_available": len(self._buttons),
            "last_refresh": datetime.fromtimestamp(self._last_refresh).isoformat() if self._last_refresh else None,
            "refresh_interval": self.refresh_interval,
        }

import os
